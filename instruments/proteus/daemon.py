# -*- coding: utf-8 -*-
"""
Created on Thu Oct 27 14:04:16 2022

@author: Xingrui Song
"""

import subprocess
from subprocess import DEVNULL, DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP, CREATE_BREAKAWAY_FROM_JOB, CREATE_NO_WINDOW
import multiprocessing as mp
from multiprocessing import Process
import os
import sys
import time
import datetime
import pickle
import json
import zmq


PORT = 20678
REQUEST_TIMEOUT = 60000
verbose = True

client_context = None
socket = None
running = False
proteus = None
kill_signal = False


def logger(msg):
    if verbose:
        if isinstance(msg, bytes):
            try:
                msg = msg.decode('utf-8')
            except:
                pass
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def request(msg):
    global client_context
    global client_socket
    if not running and not is_running():
        start()
    is_str = isinstance(msg, str)
    if is_str:
        msg = msg.encode('utf-8')

    if client_context is None:
        client_context = zmq.Context()
    client_socket = client_context.socket(zmq.REQ)
    client_socket.RCVTIMEO = REQUEST_TIMEOUT
    client_socket.connect(f"tcp://localhost:{PORT}")
    client_socket.send(msg)

    try:
        rep = client_socket.recv()
        if is_str:
            rep = rep.decode('utf-8')
    except:
        rep = b'timeout'
        if is_str:
            rep = "timeout"
    finally:
        client_socket.close()
    return rep


def is_running():
    global running
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://127.0.0.1:{PORT}")
        socket.close()
        try:
            context.close()
        except:
            pass
        running = False
        return False
    except zmq.error.ZMQError:
        running = True
        return True


def reply(message):
    socket.send(message, zmq.NOBLOCK)


def parser(message):
    message = message.lstrip(b' ')
    space_start = 0
    space = b' '[0]
    for byte in message:
        if byte == space:
            break
        else:
            space_start += 1
    return message[:space_start], message[space_start:].lstrip(b' ')


def data_pack(data, method='pickle'):
    if method == 'pickle':
        data_pickle = pickle.dumps(data)
        return b'pickle=' + data_pickle
    elif method == 'json':
        data_json = json.dumps(data).encode('utf-8')
        return b'json=' + data_json
    else:
        return b''


def data_unpack(message):
    if message[:7] == b'pickle=':
        message = message.lstrip(b'pickle=')
        return pickle.loads(message)
    elif message[:5] == b'json=':
        message = message.lstrip(b'json=')
        return json.loads(message.decode('utf-8'))
    else:
        return {}


def handler(message):
    def stop_fun():
        global kill_signal
        kill_signal = True

    def proteus_fun(arg):
        try:
            # print(f'arg = {data_unpack(arg)}')
            rep = proteus.handler(data_unpack(arg))
            reply(rep.encode('utf-8'))
        except Exception as e:
            reply("error_code = " + str(e).encode('utf-8'))

    #        reply("no error.".encode('utf-8'))

    kw, arg = parser(message)

    try:
        if kw == b'stop':
            stop_fun()
        elif kw == b'status':
            status = proteus.status()
            rep = f'Proteus daemon running, status: {status}'
            reply(rep.encode('utf-8'))
        elif kw == b'proteus':
            proteus_fun(arg)
        else:
            reply(b'Unknown request.')
    except Exception as err:
        reply(str(err).encode('utf-8'))
        logger(str(err))


def daemon():
    global socket
    global verbose
    global proteus
    global running
    
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from proteusapi import Proteus
    from setup import check_setup
    
    check_setup()
    
    try:
        running = True
        context = zmq.Context()
        socket = context.socket(zmq.REP)
#        socket.RCVTIMEO = TIMEOUT
        socket.bind(f"tcp://127.0.0.1:{PORT}")
        logger('Proteus daemon started.')

        proteus = Proteus()
        verbose = False

        def mainloop():
            global kill_signal
            while not kill_signal:
                #  Wait for next request from client
                try:
                    message = socket.recv()
                    logger(f"Received request: {message[:40]}")
                    handler(message)
                    
                except:
                    kill_signal = True

        mainloop()
        proteus.close()
        reply(b"Proteus daemon stopped.")
        socket.close()
        logger("Proteus daemon stopped.")
    except zmq.error.ZMQError:
        logger(b'Proteus daemon is already running.')

        
def start_mp():
    mp.set_start_method('spawn', force=True)
    p = Process(target=daemon, daemon=True)
    p.start()
    time.sleep(10)
    os._exit(0)
    time.sleep(10)


def start():
    global running
    if not running and not is_running():
        logger("Proteus daemon starting...")
        
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        from setup import check_setup
        check_setup()
        
        def start_subprocess():
            flags = 0
            # flags |= DETACHED_PROCESS
            flags |= CREATE_NEW_PROCESS_GROUP
            flags |= CREATE_BREAKAWAY_FROM_JOB
            flags |= CREATE_NO_WINDOW
            
            file = os.path.abspath(__file__)
            python = os.path.join(os.path.dirname(file), r'python\python.exe')
            
            subprocess.Popen(
                [python, f'{os.path.abspath(__file__)}', 'start_mp'],
                close_fds=True, creationflags=flags, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, shell=True
            )
        
        start_subprocess()
        running = True
        rep = status()
    else:
        rep = b'Proteus daemon is already running.'
    logger(rep)
    return rep


def stop():
    global running
    if running or is_running():
        logger('Proteus daemon stopping...')
        rep = request(b'stop')
        running = False
    else:
        rep = b'Proteus daemon is not running.'
    logger(rep)
    return rep
        
        
def status():
    rep = request(b'status')
    return rep


def restart():
    stop()
    rep = start()
    return rep


def send_scpi(inst: int, scpi_command: str):
    header = b'proteus '
    data = {
        'command': 'send_scpi',
        'inst': inst,
        'scpi_command': scpi_command
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep
    
    
def load_sequence(seq_data):
    header = b'proteus '
    data = {
        'command': 'load_sequence',
        'seq_data': seq_data
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep


def start_from(step_index):
    header = b'proteus '
    data = {
        'command': 'start_from',
        'step_index': step_index
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep


def set_amplitudes(amps=[1.3, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3]):
    header = b'proteus '
    data = {
        'command': 'set_amplitudes',
        'amps': amps
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep


def set_coarse_offsets(offsets=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]):
    header = b'proteus '
    data = {
        'command': 'set_coarse_offsets',
        'offsets': offsets
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep


def set_fine_offsets(offsets=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]):
    header = b'proteus '
    data = {
        'command': 'set_fine_offsets',
        'offsets': offsets
    }
    rep = request(header + data_pack(data, method='pickle'))
    return rep


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == 'start':
            start()
        elif sys.argv[1] == 'stop':
            stop()
        elif sys.argv[1] == 'restart':
            restart()
        elif sys.argv[1] == 'status':
            status()
        elif sys.argv[1] == 'start_mp':
            start_mp()
        elif sys.argv[1] == 'daemon':
            daemon()
    else:
        daemon()
        # start()
