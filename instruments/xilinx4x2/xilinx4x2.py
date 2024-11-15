from qick import *

# Main controller for the Xilinx4x2 FPGA. Acts as both a data acquisition
# device and arbitrary waveform generator
class Xilinx4x2():
    def __init__(self, name=None, address=None, options=None):
        super().__init__('xilinx4x2', name, address, options)
        self.num_analog_channels = 2
        self.num_digital_channels = 2
        self.amp_range = [0.05, 2.0]  # half of Vp-p in Volts
        self.amp_resolution = 0.001  # in Volts
        self.offset_range = [-1.0, 1.0]  # in Volts
        self.offset_resolution = 0.001  # in Volts

        self.amps = [2.0, 2.0, 2.0, 2.0]
        self.coarse_offsets = [0.0, 0.0, 0.0, 0.0]
        self.fine_offsets = [0.0, 0.0, 0.0, 0.0]

    def send_scpi(self, command):
        # Not supported by Xilinx
        pass

    """
    Start from a specified step index
    """
    def start_from(self, step_index):
        pass

    """
    Set output waveform amplitudes
    """
    def set_amplitudes(self, amps=[2.0, 2.0, 2.0, 2.0]):
        # TODO
        self.amps = amps

    def set_coarse_offsets(self, offsets=[0.0, 0.0, 0.0, 0.0]):
        # TODO
        self.coarse_offsets = offsets

    def set_fine_offsets(self, offsets=[0.0, 0.0, 0.0, 0.0]):
        # Not implemented
        self.fine_offsets = offsets

    def set_ch_amplitudes(self, ch, amp):
        # TODO
        self.amps[ch - 1] = amp
    
    def set_ch_coarse_offset(self, ch, offset):
        # TODO
        self.coarse_offsets[ch - 1] = offset
    
    def set_ch_fine_offset(self, ch, offset):
        # Not implemented
        self.fine_offsets[ch - 1] = offset
        self.set_fine_offsets(self.fine_offsets)

    def load_sequence(self, data, display=False, options=None):
        if display:
            self.display(data)
        # if autorange:
        #     data, amps, offsets = self.autorange(data)
        
        for ch_index in range(4):
            ch_options = options['analog'][ch_index + 1]
            if 'amplitude' in ch_options:
                self.amps[ch_index] = ch_options['amplitude']
            if 'coarse_offset' in ch_options:
                self.coarse_offsets[ch_index] = ch_options['coarse_offset']
            if 'fine_offset' in ch_options:
                self.fine_offsets[ch_index] = ch_options['fine_offset']

        for ch_index in range(4):
            data['analog'][ch_index + 1] = [
                (task - self.coarse_offsets[ch_index]) / self.amps[ch_index] for task in
                data['analog'][ch_index + 1]
            ]

        # if volt_max - volt_min > amp:
        #     print(f'Warning: analog output CH{channel} is clipping.')
        
        t = time.time()
        print(f"Loading sequence...")
        rep = xilinx4x2.load_sequence(self.address, data)
        self.set_amplitudes(self.amps)
        self.set_coarse_offsets(self.coarse_offsets)
        self.set_fine_offsets(self.fine_offsets)
        print(f"Finished in {time.time() - t} seconds.")
        
    
