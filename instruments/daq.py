from .instrument import Instrument
# from .alazar import daq_ats9870
from queue import Queue
import numpy as np
from threading import Thread
from itertools import cycle
import time

class Daq(Instrument):
    def __init__(self, instru_type='daq', name=None, address=None, options=None):
        super().__init__(instru_type, name, address, options)
        self.rec_raw_queue = Queue()
        self.streams = {}
        self.flags_queue = Queue()
        self.post_trigger_samples_default = 8192
        
    def clear_rec_raw(self):
        self.rec_raw_queue.queue.clear()
        
    def clear_streams(self):
        for stream, q in self.streams.items():
            q.queue.clear()
        self.streams.clear()
        
    def clear_flags(self):
        self.flags_queue.queue.clear()
        
    def acquire_data(self, num_records, demod_list=None):
        print(f"Acquiring {num_records} records...")
        self.stream_data(num_records, demod_list)
        print("Finished")
        rec = {}
        for stream, q in self.streams.items():
            rec[stream] = list(q.queue)
        return rec
    
    def stream_data_raw(self, num_records, post_trigger_samples, options=None):
        self.clear_flags()
        self.self.flags_queue.put('start_acquisition')
        self.waiting_for_trigger = True
        self.self.flags_queue.put('stop_acquisition')
    
    def stream_data(self, num_records, demod_list=None, clear_streams=True, options=None):
        if demod_list is None:
            demod_list = [[('rawIQ', ['I', 'Q'], self.post_trigger_samples_default)]]
            
        def stream_data_fun():
            self.clear_rec_raw()
            self.clear_flags()
            if clear_streams:
                self.clear_streams()
            demod_len_max = 0
            for demod_rec in demod_list:
                for demod_type, streams, params in demod_rec:
                    for stream in streams:
                        if stream not in self.streams:
                            self.streams[stream] = Queue()
                    if demod_type == 'raw_IQ':
                        demod_len = params
                    elif demod_type == 'IQ':
                        weights = np.array(params)
                        demod_len = weights.shape[-1]
                    else:
                        raise Exception(f'Unknown demod type "{demod_type}".')
                    if demod_len > demod_len_max:
                        demod_len_max = demod_len

            post_trigger_samples = demod_len_max
            t_raw = Thread(target=self.stream_data_raw, args=(num_records, post_trigger_samples, options))
            self.flags_queue.put('start_acquisition')
            t_raw.start()
            
            demod_iter = cycle(demod_list)
            for _ in range(num_records):
                rec_raw = self.rec_raw_queue.get()
                for demod_type, streams, params in next(demod_iter):
                # for demod_type, streams, params in demod_list[num_records % len(demod_list)]:
                    if demod_type == 'raw_IQ':
                        self.streams[streams[0]].put(rec_raw[0])
                        self.streams[streams[1]].put(rec_raw[1])
                    elif demod_type == 'IQ':
                        # print(demod_list[0][0])
                        demod_sum = np.dot(params.ravel(), rec_raw.ravel())
                        # demod_sum = np.dot(demod_list[0][0][2].ravel(), rec_raw.ravel())
                        self.streams[streams[0]].put(demod_sum)

            self.flags_queue.put('stop_acquisition')
        t = Thread(target=stream_data_fun)
        t.start()
        return self.streams
        
        
        
class DummyDaq(Daq):
    def stream_data_raw(self, num_records, post_trigger_samples):
        self.flags_queue.put('start_acquisition')
        self.waiting_for_trigger = True
        for i in range(num_records):
            self.rec_raw_queue.put(np.full((2, post_trigger_samples), i))
        self.flags_queue.put('stop_acquisition')
        

# class ATS9870(Daq):
#     def __init__(self, name=None, address=None, options=None):
#         super().__init__('ats9870', name, address, options)
    
#     def stream_data_raw(self, num_records, post_trigger_samples, options=None):
#         if options is None:
#             options = {}
            
#         if 'coupling' in options:
#             coupling = options['coupling']
#         else:
#             coupling = 'AC'
            
#         if 'input_range' in options:
#             input_range = options['input_range']
#         else:
#             input_range = 2.0

#         if 'trig_level' in options:
#             trig_level = options['trig_level']
#         else:
#             trig_level = 0.0
            
#         alazar_params = daq_ats9870.get_alazar_parameters(num_records, post_trigger_samples, coupling, input_range)
#         while True:
#             try:
#                 board = daq_ats9870.configure_board(alazar_params, None, trig_level)
#                 break
#             except Exception as e:
#                 print(e)
#                 time.sleep(1)
#         daq_ats9870.stream_data(alazar_params, board, self.rec_raw_queue)
