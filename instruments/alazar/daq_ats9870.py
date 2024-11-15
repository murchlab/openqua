# -*- coding: utf-8 -*-
"""
Created on Sat Jan 25 12:43:51 2020

@author: P. M. Harrington, 25 January 2020

Modified by Xingrui Song, 8 November 2022
"""

from __future__ import division
import ctypes
import numpy as np
import os, sys
import time
import numbers
from . import atsapi as ats
from threading import Thread
from queue import Queue


class Nop():
    def __init__(self):
        self.name = None
        pass
    
    
def get_alazar_parameters(num_records, post_trigger_samples=8192, coupling='AC', input_range=1.0, verbose=False):
    alazar_params = Nop()
    
    #
    alazar_params.post_trigger_samples = post_trigger_samples
    alazar_params.samples_per_sec = 1e9
    alazar_params.buffer_count = 64 # 64 for ATS9870, found in SDK manual
    
    #
    alazar_params.num_total_records = num_records    
    alazar_params.records_per_buffer = min(1024, alazar_params.num_total_records)    
    alazar_params.samples_per_buffer = alazar_params.post_trigger_samples * alazar_params.records_per_buffer    
    alazar_params.buffers_per_acquisition = int(np.ceil(alazar_params.num_total_records/alazar_params.records_per_buffer))
    
    if isinstance(coupling, str):
        alazar_params.coupling_A = coupling
        alazar_params.coupling_B = coupling
    else:
        alazar_params.coupling_A = coupling[0]
        alazar_params.coupling_B = coupling[1]
        
    if isinstance(input_range, numbers.Number):
        alazar_params.input_range_A = input_range
        alazar_params.input_range_B = input_range
    else:
        alazar_params.input_range_A = input_range[0]
        alazar_params.input_range_B = input_range[1]
    
    if verbose:
        print("Total records: {}".format(alazar_params.num_total_records))
        print("Buffers per acquistion: {}".format(alazar_params.buffers_per_acquisition))
        print("DAQ samples per record: {}".format(alazar_params.post_trigger_samples))
        
    return alazar_params
    

# Configures a board for acquisition
def configure_board(alazar_params, board=None, trig_level=0.0):
    # Select clock parameters as required to generate this
    # sample rate
    #
    # For example: if samples_per_sec is 100e6 (100 MS/s), then you can
    # either:
    #  - select clock source INTERNAL_CLOCK and sample rate
    #    SAMPLE_RATE_100MSPS
    #  - or select clock source FAST_EXTERNAL_CLOCK, sample rate
    #    SAMPLE_RATE_USER_DEF, and connect a 100MHz signal to the
    #    EXT CLK BNC connector
    
    def select_coupling(coupling):
        # print(coupling)
        if coupling == 'AC':
            return ats.AC_COUPLING
        elif coupling == 'DC':
            return ats.DC_COUPLING
        else:
            raise Exception(f"Unknown coupling '{coupling}'.")
            
    def select_input_range(input_range):
        if input_range == 0.04:
            return ats.INPUT_RANGE_PM_40_MV
        elif input_range == 0.1:
            return ats.INPUT_RANGE_PM_100_MV
        elif input_range == 0.2:
            return ats.INPUT_RANGE_PM_200_MV
        elif input_range == 0.4:
            return ats.INPUT_RANGE_PM_400_MV
        elif input_range == 1:
            return ats.INPUT_RANGE_PM_1_V
        elif input_range == 2:
            return ats.INPUT_RANGE_PM_2_V
        elif input_range == 4:
            return ats.INPUT_RANGE_PM_4_V
        else:
            raise Exception(f"Unsupported input_range '{input_range}'.")
    
    if board is None:
        board = ats.Board(systemId = 1, boardId = 1)
        
    samples_per_sec = alazar_params.samples_per_sec #1000000000.0
    board.setCaptureClock(ats.INTERNAL_CLOCK,
                          ats.SAMPLE_RATE_1000MSPS,
                          ats.CLOCK_EDGE_RISING,
                          0)
    
    # Select channel A input parameters as required.
        
    board.inputControlEx(ats.CHANNEL_A,
                         select_coupling(alazar_params.coupling_A),
                         select_input_range(alazar_params.input_range_A),
                         ats.IMPEDANCE_50_OHM)
    
    # Select channel A bandwidth limit as required.
    board.setBWLimit(ats.CHANNEL_A, 0)
    
    
    # Select channel B input parameters as required.
    board.inputControlEx(ats.CHANNEL_B,
                         select_coupling(alazar_params.coupling_B),
                         select_input_range(alazar_params.input_range_B),
                         ats.IMPEDANCE_50_OHM)
    # Select channel B bandwidth limit as required.
    board.setBWLimit(ats.CHANNEL_B, 0)
    
    # Select trigger inputs and levels as required.
    level1 = int(trig_level / 5.0  * 128) + 128
    board.setTriggerOperation(ats.TRIG_ENGINE_OP_J,
                              ats.TRIG_ENGINE_J, # engine1
                              ats.TRIG_EXTERNAL, # source1
                              ats.TRIGGER_SLOPE_POSITIVE, #slope1
                              level1, # level1  # was 135
                              ats.TRIG_ENGINE_K,
                              ats.TRIG_DISABLE,
                              ats.TRIGGER_SLOPE_POSITIVE,
                              level1)
#    # Select external trigger parameters as required.
    board.setExternalTrigger(ats.DC_COUPLING,
                            ats.ETR_5V)
    # Set trigger delay as required.
    triggerDelay_sec = 0
    triggerDelay_samples = int(triggerDelay_sec * samples_per_sec + 0.5)
    board.setTriggerDelay(triggerDelay_samples)

    # Set trigger timeout as required.
    #
    # NOTE: The board will wait for a for this amount of time for a
    # trigger event.  If a trigger event does not arrive, then the
    # board will automatically trigger. Set the trigger timeout value
    # to 0 to force the board to wait forever for a trigger event.
    #
    # IMPORTANT: The trigger timeout value should be set to zero after
    # appropriate trigger parameters have been determined, otherwise
    # the board may trigger if the timeout interval expires before a
    # hardware trigger event arrives.
    triggerTimeout_sec = 0
    triggerTimeout_clocks = int(triggerTimeout_sec / 10e-6 + 0.5)
    board.setTriggerTimeOut(triggerTimeout_clocks)

    # Configure AUX I/O connector as required
    board.configureAuxIO(ats.AUX_OUT_TRIGGER,
                         0)
    return board


def stream_data(alazar_params, board, rec_queue, verbose=False):
    # No pre-trigger samples in NPT mode
    #print("\ndaq_alazar Troubleshoot stuck at this step 1")
    preTriggerSamples = 0

    # Select the number of samples per record.
    #print("\ndaq_alazar Troubleshoot stuck at this step 2")
    post_trigger_samples = alazar_params.post_trigger_samples

    # Select the number0 of records per DMA buffer.
    #print("\ndaq_alazar Troubleshoot stuck at this step 3")
    records_per_buffer = alazar_params.records_per_buffer #2**10 # up to 2**14

    # Select the number of buffers per acquisition.
    #print("\ndaq_alazar Troubleshoot stuck at this step 4")
    buffers_per_acquisition = alazar_params.buffers_per_acquisition
    
    #print("\ndaq_alazar Troubleshoot stuck at this step 5")
    records_per_acquisition = records_per_buffer * buffers_per_acquisition
    
    # Select the active channels.
    #print("\ndaq_alazar Troubleshoot stuck at this step 6")
    channels = ats.CHANNEL_A | ats.CHANNEL_B
    channelCount = 0
    
    #print("\ndaq_alazar Troubleshoot stuck at this step 7")
    for c in ats.channels:
        channelCount += (c & channels == c)

    # Should data be saved to file?
    saveData = False
    dataFile = None
    #print("\ndaq_alazar Troubleshoot stuck at this step 8")
    if saveData:
        dataFile = open(os.path.join(os.path.dirname(__file__),
                                     "data.bin"), 'wb')
    #print("\ndaq_alazar Troubleshoot stuck at this step 9")
    # Compute the number of bytes per record and per buffer 
    memorySize_samples, bitsPerSample = board.getChannelInfo()
    bytesPerSample = (bitsPerSample.value + 7) // 8
    samplesPerRecord = preTriggerSamples + post_trigger_samples
    bytesPerRecord = bytesPerSample * samplesPerRecord
    bytesPerBuffer = bytesPerRecord * records_per_buffer * channelCount

    # Select number of DMA buffers to allocate
    buffer_count = alazar_params.buffer_count

    # Allocate DMA buffers
    #print("\ndaq_alazar Troubleshoot stuck at this step 10")
    sample_type = ctypes.c_uint8
    #print("B")
    if bytesPerSample > 1:
        sample_type = ctypes.c_uint16

    buffers = []
    for i in range(buffer_count):
        buffers.append(ats.DMABuffer(board.handle, sample_type, bytesPerBuffer))
    #print("\ndaq_alazar Troubleshoot stuck at this step 11")
    # Set the record size
    board.setRecordSize(preTriggerSamples, post_trigger_samples)
    # Configure the board to make an NPT AutoDMA acquisition
    board.beforeAsyncRead(channels,
                          -preTriggerSamples,
                          samplesPerRecord,
                          records_per_buffer,
                          records_per_acquisition,
                          ats.ADMA_EXTERNAL_STARTCAPTURE | ats.ADMA_NPT)
    
    #print("\ndaq_alazar Troubleshoot stuck at this step 12")
    
    #print("\ndaq_alazar Troubleshoot stuck at this step 14")
    # Post DMA buffers to board
    for buffer in buffers:
        board.postAsyncBuffer(buffer.addr, buffer.size_bytes)

    start = time.time() # Keep track of when acquisition started

    buffer_queue = Queue()

    def buffer_copy():
        buffersCompleted = 0
        while (buffersCompleted < buffers_per_acquisition and not ats.enter_pressed()):
            buffer = buffers[buffersCompleted % len(buffers)]
            board.waitAsyncBufferComplete(buffer.addr, timeout_ms=10000)
            buffer_queue.put(np.array(buffer.buffer, dtype=np.float32))
            board.postAsyncBuffer(buffer.addr, buffer.size_bytes)
            buffersCompleted += 1
    
    try:
        board.startCapture() # Start the acquisition
        
        if verbose:
            print("Capturing %d buffers. Press <enter> to abort" %
                  buffers_per_acquisition)
            
        buffer_copy_t = Thread(target=buffer_copy)
        buffer_copy_t.start()
        
        buffersCompleted = 0
        while (buffersCompleted < buffers_per_acquisition and not ats.enter_pressed()):
            # Wait for the buffer at the head of the list of available
            # buffers to be filled by the board.
            # buffer = buffers[buffersCompleted % len(buffers)]
            # board.waitAsyncBufferComplete(buffer.addr, timeout_ms=5000)
            # rec_raw = (np.array(buffer.buffer, dtype=np.float32) / 128) - 1
            # board.postAsyncBuffer(buffer.addr, buffer.size_bytes)

            rec_raw = (buffer_queue.get() / 128) - 1

            rec_raw = np.reshape(rec_raw, (2, records_per_buffer, post_trigger_samples))
            rec_raw[0, :, :] *= alazar_params.input_range_A
            rec_raw[1, :, :] *= alazar_params.input_range_B
            rec_raw = np.swapaxes(rec_raw, 0, 1)


            buffersCompleted += 1
            if buffersCompleted < buffers_per_acquisition:
                for rec_i in rec_raw:
                    rec_queue.put(rec_i)
            else:
                for rec_i in rec_raw[:(alazar_params.num_total_records - records_per_buffer * (buffers_per_acquisition - 1))]:
                    rec_queue.put(rec_i)
            
            
            # NOTE:
            #print("ff")
            #
            # While you are processing this buffer, the board is already
            # filling the next available buffer(s).
            #
            # You MUST finish processing this buffer and post it back to the
            # board before the board fills all of its available DMA buffers
            # and on-board memory.
            #
            # Samples are arranged in the buffer as follows:
            # S0A, S0B, ..., S1A, S1B, ... 
            # with SXY the sample number X of channel Y.
            #
            # Sample code are stored as 8-bit values.
            #
            # Sample codes are unsigned by default. As a result:
            # - 0x00 represents a negative full scale input signal.
            # - 0x80 represents a ~0V signal.
            # - 0xFF represents a positive full scale input signal.
            # Optionaly save data to file
            #print("\ng")
            if dataFile:
                buffer.buffer.tofile(dataFile)

            # Add the buffer to the end of the list of available buffers.
            # board.postAsyncBuffer(buffer.addr, buffer.size_bytes)
    finally:
        board.abortAsyncRead()
#        generator.proteus_close()
    #print("\ndaq_alazar Troubleshoot stuck at this step 16")
