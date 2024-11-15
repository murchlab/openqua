from instruments.xilinx4x2.xilinx4x2_api import Xilinx4x2QP
from .instrument import Instrument
from queue import Queue
from threading import Thread
import time


class Controller(Instrument):
    def __init__(self, instru_type='controller', name=None, address=None, options=None):
        super().__init__(instru_type, name, address, options)
        self.num_analog_outputs = 8
        self.num_digital_outputs = 8
        self.num_analog_inputs = 2
        self.rep_rate = 1000
        self.streams = Queue()
        self.flags_queue = Queue()
        
    def display(self, data):
        pass
    
    def load_sequence(self, awg_data, display=False, awg_options=None):
        pass
    
    def start_from(self, step_index):
        pass
    
    def stream_data(self, num_records, demod_list=None, coupling='AC', input_range=1):
        print(input_range)
        self.flags_queue.put('start_acquisition')
        self.flags_queue.put('stop_acquisition')
    
    def set_rep_rate(self, rate):
        pass
    
    def set_state(self, on_flag):
        pass
    
    def switch_state(self):
        self.flags_queue.get()
        time.sleep(2)
        self.set_state(1)
        self.flags_queue.get()
        self.set_state(0)
        time.sleep(2)
    
    def execute(self, seq_data, num_avg=1, display=False, options=None):
        if options is None:
            options = {
                'analog_outputs': {},
                'digital_outputs': {},
                'analog_inputs': {}
            }
        
        if 'rep_rate' not in options:
            rep_rate = self.rep_rate
        else:
            rep_rate = options['rep_rate']
            
        awg_data = {'analog': seq_data['analog_outputs'], 'digital': seq_data['digital_outputs']}
        awg_options = {'analog': options['analog_outputs'], 'digital': options['digital_outputs']}
        self.load_sequence(awg_data, display, awg_options)
        
        demod_list = seq_data['demod_list']
            
        self.set_rep_rate(rep_rate)
            
        num_tasks = len(seq_data['analog_outputs'][1])

        max_avgs_single_run = int(2 ** 18 / num_tasks) + 1

        time.sleep(2)

        def avg_runs():
            remaining_avgs = num_avg
            first_run = True
            print('Acquisition started.')
            while remaining_avgs > 0:
                if first_run:
                    self.set_state(0)
                    time.sleep(2)
                if remaining_avgs > max_avgs_single_run:
                    self.start_from(0)
                    time.sleep(2)
                    self.stream_data(num_tasks * max_avgs_single_run, demod_list, clear_streams=first_run, daq_options=options['analog_inputs'])
                    self.switch_state()
                    remaining_avgs -= max_avgs_single_run
                else:
                    self.start_from(0)
                    time.sleep(2)
                    self.stream_data(num_tasks * remaining_avgs, demod_list, clear_streams=first_run, daq_options=options['analog_inputs'])
                    self.switch_state()
                    remaining_avgs = 0
                first_run = False
            self.set_state(0)
            print('Acquisition stopped.')
        
        t = Thread(target=avg_runs)
        t.start()
        return self.streams
        
        
class DummyController(Controller):
    def __init__(self, name=None, address=None, options=None):
        super().__init__('dummycontroller', name, address, options)
        self.num_analog_channels = 8
        self.num_digital_channels = 8
        self.rep_rate_Hz = 1000
        self.amps = [1.2,1.2,0.27,0.27,0.88,0.90,0.54,0.55]
        self.offsets = [0, 0, 0, 0, 0, 0, 0, 0]
        
        self.streams = {}
        
        
        from .instrument_manager import load
        self.awg = load('dummy8ch')
        self.daq = load('dummydaq')
        
    def load_sequence(self, seq_data, display=False, autorange=True):
        awg_data = {'analog': seq_data['analog_outputs'], 'digital': seq_data['digital_outputs']}
        self.awg.load_sequence(awg_data, display)
        
    def execute(self, seq_data, num_avg=1, display=False):
        self.load_sequence(seq_data, display, autorange=True)
        import numpy as np


class RedFridgeController(Controller):
    def __init__(self, name=None, address=None, options=None):
        super().__init__('redfridgecontroller', name, address, options)
        self.num_analog_outputs = 8
        self.num_digital_outputs = 8
        self.num_analog_inputs = 2
        self.rep_rate = 10000
        self.amps = [0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65]
        self.offsets = [0, 0, 0, 0, 0, 0, 0, 0]
        
        from .instrument_manager import load
        self.awg = load('proteus8ch')
        self.delay = load('agilent_33220a', address='GPIB0::10::INSTR')
        self.daq = load('ats9870')
        self.streams = self.daq.streams
        self.flags_queue = self.daq.flags_queue
        
    def load_sequence(self, awg_data, display=False, awg_options=None):
        self.delay.initialize()
        self.awg.load_sequence(awg_data, display, awg_options)
        
    def start_from(self, step_index):
        self.awg.start_from(step_index)

    def stream_data(self, num_records, demod_list=None, clear_streams=True, daq_options=None):
        if daq_options is None:
            daq_options = {}
        daq_options['trig_level'] = 0.6
        return self.daq.stream_data(num_records, demod_list, clear_streams, daq_options)
        
    def set_rep_rate(self, rate):
        self.delay.set_rep_rate(rate)
    
    def set_state(self, on_flag):
        self.delay.set_state(on_flag)
        
    def execute(self, seq_data, num_avg=1, display=False, options=None):
        return super().execute(seq_data, num_avg, display, options)


class NonHermitianController(Controller):
    def __init__(self, name=None, address=None, options=None):
        super().__init__('nonhermitian_controller', name, address, options)
        self.num_analog_outputs = 4
        self.num_digital_outputs = 4
        self.num_analog_inputs = 2
        self.rep_rate = 5000
        self.amps = [2.0, 2.0, 2.0, 2.0]
        self.offsets = [0.0, 0.0, 0.0, 0.0]
        
        from .instrument_manager import load
        self.awg = load('wx2184c', address='128.252.134.16')
        self.delay = load('dg535', address='GPIB0::8::INSTR')
        self.daq = load('ats9870')
        self.streams = self.daq.streams
        self.flags_queue = self.daq.flags_queue
        
    def load_sequence(self, awg_data, display=False, awg_options=None):
        self.delay.initialize()
        self.awg.load_sequence(awg_data, display, awg_options)
        
    def start_from(self, step_index):
        self.awg.start_from(step_index)

    def stream_data(self, num_records, demod_list=None, clear_streams=True, daq_options=None):
        if daq_options is None:
            daq_options = {}
        daq_options['trig_level'] = 0.6
        return self.daq.stream_data(num_records, demod_list, clear_streams, daq_options)
        
    def set_rep_rate(self, rate):
        self.delay.set_rep_rate(rate)
    
    def set_state(self, on_flag):
        self.delay.set_state(on_flag)
        
    def execute(self, seq_data, num_avg=1, display=False, options=None):
        return super().execute(seq_data, num_avg, display, options)


class Xilinx4x2(Controller):
    def __init__(self, name=None, address=None, options=None):
        super().__init__('xilinx4x2', name, address, options)
        self.num_analog_outputs = 2
        self.num_digital_outputs = 2
        self.num_analog_inputs = 2
        self.rep_rate = 10000
        self.amps = [0.65, 0.65]
        self.offsets = [0, 0]

        
        
        # This is how fridge controller works; will we need to split into
        # Daq and WFG?
        #
        # from .instrument_manager import load
        # self.awg = load('proteus8ch')
        # self.delay = load('agilent_33220a', address='GPIB0::10::INSTR')
        # self.daq = load('ats9870')
        # self.streams = self.daq.streams
        # self.flags_queue = self.daq.flags_queue
    
    # Loads a sequence into the AWG
    def load_sequence(self, awg_data, display=False, awg_options=None):
        # self.delay.initialize()
        # self.awg.load_sequence(awg_data, display, awg_options)

        if display:
            self.display(awg_data)
        
        for ch_index in range(4):
            ch_options = awg_options['analog'][ch_index + 1]
            if 'amplitude' in ch_options:
                self.amps[ch_index] = ch_options['amplitude']
            if 'coarse_offset' in ch_options:
                self.coarse_offsets[ch_index] = ch_options['coarse_offset']
            if 'fine_offset' in ch_options:
                self.fine_offsets[ch_index] = ch_options['fine_offset']

        for ch_index in range(4):
            awg_data['analog'][ch_index + 1] = [
                (task - self.coarse_offsets[ch_index]) / self.amps[ch_index] for task in
                awg_data['analog'][ch_index + 1]
            ]
        
        t = time.time()
        print(f"Loading sequence...")

        # TODO: why is this unused?
        rep = xilinx4x2.load_sequence(self.address, awg_data)

        self.set_amplitudes(self.amps)
        self.set_coarse_offsets(self.coarse_offsets)
        self.set_fine_offsets(self.fine_offsets)

        print(f"Finished in {time.time() - t} seconds.")
        
    def start_from(self, step_index):
        xilinx4x2.start_from(self.address, step_index)

    def stream_data(self, num_records, demod_list=None, clear_streams=True, daq_options=None):
        if daq_options is None:
            daq_options = {}
        daq_options['trig_level'] = 0.6
            
        if 'coupling' in daq_options:
            coupling = daq_options['coupling']
        else:
            coupling = 'AC'
            
        if 'input_range' in daq_options:
            input_range = daq_options['input_range']
        else:
            input_range = 2.0

        if 'trig_level' in daq_options:
            trig_level = daq_options['trig_level']
        else:
            trig_level = 0.0
            
        # TODO: actually intake data from board
        #
        # alazar_params = daq_ats9870.get_alazar_parameters(num_records, post_trigger_samples, coupling, input_range)
        # while True:
        #     try:
        #         board = daq_ats9870.configure_board(alazar_params, None, trig_level)
        #         break
        #     except Exception as e:
        #         print(e)
        #         time.sleep(1)
        # daq_ats9870.stream_data(alazar_params, board, self.rec_raw_queue)

        return xilinx4x2.stream_data(num_records, demod_list, clear_streams, daq_options)
        
    def set_rep_rate(self, rate):
        # self.delay.set_rep_rate(rate)
        pass
    
    def set_state(self, on_flag):
        # self.delay.set_state(on_flag)
        pass
        
    def execute(self, seq_data, num_avg=1, display=False, options=None):
        return super().execute(seq_data, num_avg, display, options)