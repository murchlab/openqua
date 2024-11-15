from .instrument import Instrument
# from . import proteus
# from . import wx2184c
import numpy as np
import time
import matplotlib.pyplot as plt


class AWG(Instrument):
    def __init__(self, instru_type='awg', name=None, address=None, options=None):
        super().__init__(instru_type, name, address, options)
        self.num_analog_channels = 8
        self.num_digital_channels = 8
        self.amp_range = [0.025, 0.65]  # half of Vp-p in Volts
        self.amp_resolution = 0.0005  # in Volts
        self.offset_range = [-0.5, 0.5]  # in Volts
        self.offset_resolution = 0.01  # in Volts
    
    def autorange(self, data, verbose=False):
        def scaling(volt_min, volt_max):
            offset = int((volt_max + volt_min) / 2 / self.offset_resolution) * self.offset_resolution
            if offset < self.offset_range[0]:
                offset = self.offset_range[0]
            if offset > self.offset_range[1]:
                offset = self.offset_range[1]
                
            volt_min -= offset
            volt_max -= offset
            
            amp = np.ceil(max(np.abs(volt_min), np.abs(volt_max)) / self.amp_resolution) * self.amp_resolution
            if amp < self.amp_range[0]:
                amp = self.amp_range[0]
            if amp > self.amp_range[1]:
                amp = self.amp_range[1]
                
            return amp, offset
            
        amps = [1.0] * self.num_analog_channels
        offsets = [0.0] * self.num_analog_channels
        for channel in data['analog']:
            volt_min = np.inf
            volt_max = -np.inf
            for task in data['analog'][channel]:
                task_volt_min = np.min(task)
                task_volt_max = np.max(task)
                if task_volt_min < volt_min:
                    volt_min = task_volt_min
                if task_volt_max > volt_max:
                    volt_max = task_volt_max
                    
            amp, offset = scaling(volt_min, volt_max)
            if volt_max - volt_min > amp:
                print(f'Warning: analog output CH{channel} is clipping.')
            data['analog'][channel] = [(task - offset) / amp for task in data['analog'][channel]]
            amps[channel - 1] = amp
            offsets[channel - 1] = offset
                
        if verbose:
            print(f'amps = {amps}, offsets = {offsets}')
            for channel in data['analog']:
                volt_min = np.inf
                volt_max = -np.inf
                for task in data['analog'][channel]:
                    task_volt_min = np.min(task)
                    task_volt_max = np.max(task)
                    if task_volt_min < volt_min:
                        volt_min = task_volt_min
                    if task_volt_max > volt_max:
                        volt_max = task_volt_max
                print(channel, volt_min, volt_max)
#         print(f'amps = {amps}, offsets = {offsets}')
        return data, amps, offsets
        
    def display(self, data):
        num_colors = 12
        num_time_samples = 1024
        
        def display_ad(ad):
        # ad = 'analog' or 'digital'
            num_tasks = len(data[ad][1])
            len_max = 0
            for channel in data[ad]:
                for task in data[ad][channel]:
                    if len(task) > len_max:
                        len_max = len(task)

            val = np.zeros((num_tasks, num_time_samples, self.num_analog_channels), dtype=bool)
            delta_time_sample = len_max / num_time_samples
            for channel in data[ad]:
                task_index = 0
                for task in data[ad][channel]:
                    t_samples = np.array(np.arange(0, len(task), delta_time_sample), dtype=int)
                    task_samples = task[t_samples]
                    val[task_index, :len(task_samples), channel - 1] = (task_samples != 0)
                    task_index += 1

            scale = 3
            def fill_point(val_point):
                n = np.unpackbits(val_point.view('uint8')).sum()
                if n == 0:
                    return np.full(self.num_analog_channels * scale, np.nan, dtype=np.float64)
                seg = np.array(np.linspace(0, self.num_analog_channels * scale, n + 1), dtype=int)
                i = 0
                fill_val = np.empty(self.num_analog_channels * scale, dtype=int)
                for channel_index in range(self.num_analog_channels):
                    if val_point[channel_index]:
                        fill_val[seg[i]:seg[i + 1]] = channel_index + 1
                        i += 1
                return fill_val

            img = np.full((num_tasks, self.num_analog_channels * scale, num_time_samples), np.nan, dtype=np.float64)
            for task_index in range(num_tasks):
                for t_sample in range(num_time_samples):
                    img[task_index, :, t_sample] = fill_point(val[task_index, t_sample])

            img = img.reshape((num_tasks * self.num_analog_channels * scale, num_time_samples))
            img = np.flip(img, axis=0)
            fig = plt.figure(figsize=(8, num_tasks * 0.05), dpi=150)
            extent = [-0.5, len_max - 0.5, -0.5, num_tasks - 0.5]
            pos = plt.imshow(img, aspect='auto', vmin=0.5, vmax=num_colors + 0.5, extent=extent, cmap='Set3')
            ticks = np.arange(1, self.num_analog_channels + 1)
            boundaries = np.arange(0.5, self.num_analog_channels + 1.5)
    #         ticks = [f"CH{v}" for v in values]
            label = 'channels'
            if ad == 'analog':
                label = 'Analog ' + label
            elif ad == 'digital':
                label = 'Digital ' + label
            fig.colorbar(pos, ticks=ticks, boundaries=boundaries, label=label)
            plt.xlabel('Time (ns)')
            plt.ylabel('Task index')
            plt.show()
            
        display_ad('analog')
        display_ad('digital')

    def send_scpi(self, command):
        print(command)

    def load_sequence(self, data, display=False, options=None):
        if display:
            self.display(data)
            
    def start_from(self, step_index):
        pass
            
    def set_amplitudes(self, amps=[1, 1, 1, 1, 1, 1, 1, 1]):
        pass
    
    def set_offsets(self, offsets=[0, 0, 0, 0, 0, 0, 0, 0]):
        pass
        
        
class Dummy8CH(AWG):
    def load_sequence(self, data, display=False):
        if True:
            self.display(data)
        


# class Proteus8CH(AWG):
#     def __init__(self, name=None, address=None, options=None):
#         super().__init__('proteus8ch', name, address, options)
#         self.num_analog_channels = 8
#         self.num_digital_channels = 8
#         self.amp_range = [0.025, 0.65]  # half of Vp-p in Volts
#         self.amp_resolution = 0.0005  # in Volts
#         self.offset_range = [-0.5, 0.5]  # in Volts
#         self.offset_resolution = 0.01  # in Volts

#         self.amps = [0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65]
#         self.coarse_offsets = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
#         self.fine_offsets = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

#     def send_scpi(self, command):
#         print(command)

#     def load_sequence(self, data, display=False, options=None):
#         if display:
#             self.display(data)
#         # if autorange:
#         #     data, amps, offsets = self.autorange(data)
        
#         for ch_index in range(8):
#             ch_options = options['analog'][ch_index + 1]
#             if 'amplitude' in ch_options:
#                 self.amps[ch_index] = ch_options['amplitude']
#             if 'coarse_offset' in ch_options:
#                 self.coarse_offsets[ch_index] = ch_options['coarse_offset']
#             if 'fine_offset' in ch_options:
#                 self.fine_offsets[ch_index] = ch_options['fine_offset']
        
#         t = time.time()
#         print(f"Loading sequence...")
#         self.set_amplitudes(self.amps)
#         self.set_coarse_offsets(self.coarse_offsets)
#         self.set_fine_offsets(self.fine_offsets)
#         rep = proteus.daemon.load_sequence(data)
#         self.set_amplitudes(self.amps)
#         self.set_coarse_offsets(self.coarse_offsets)
#         self.set_fine_offsets(self.fine_offsets)
#         print(f"Finished in {time.time() - t} seconds.")
#         return rep.decode('utf-8')
        
#     def start_from(self, step_index):
#         proteus.daemon.start_from(step_index)
        
#     def set_amplitudes(self, amps=[0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65]):
#         # Proteus api uses a different definition for amplitudes
#         rep = proteus.set_amplitudes([2 * amp for amp in amps])
#         self.amps = amps
#         return rep.decode('utf-8')
    
#     def set_coarse_offsets(self, offsets=[0, 0, 0, 0, 0, 0, 0, 0]):
#         rep = proteus.set_coarse_offsets(offsets)
#         self.coarse_offsets = coarse_offsets
#         return rep.decode('utf-8')
    
#     def set_fine_offsets(self, offsets=[0, 0, 0, 0, 0, 0, 0, 0]):
#         rep = proteus.set_fine_offsets(offsets)
#         self.fine_offsets = fine_offsets
#         return rep.decode('utf-8')
    
#     def set_ch_amplitudes(self, ch, amp):
#         self.amps[ch - 1] = amp
#         rep = proteus.set_amplitudes([2 * amp for amp in self.amps])
#         return rep.decode('utf-8')
    
#     def set_ch_coarse_offset(self, ch, offset):
#         self.offsets[ch - 1] = offset
#         rep = proteus.set_coarse_offsets(self.offsets)
#         return rep.decode('utf-8')
    
#     def set_ch_fine_offset(self, ch, offset):
#         self.offsets[ch - 1] = offset
#         rep = proteus.set_fine_offsets(self.offsets)
#         return rep.decode('utf-8')


# class WX2184C(AWG):
#     def __init__(self, name=None, address=None, options=None):
#         super().__init__('wx2184c', name, address, options)
#         self.num_analog_channels = 4
#         self.num_digital_channels = 4
#         self.amp_range = [0.05, 2.0]  # half of Vp-p in Volts
#         self.amp_resolution = 0.001  # in Volts
#         self.offset_range = [-1.0, 1.0]  # in Volts
#         self.offset_resolution = 0.001  # in Volts

#         self.amps = [2.0, 2.0, 2.0, 2.0]
#         self.coarse_offsets = [0.0, 0.0, 0.0, 0.0]
#         self.fine_offsets = [0.0, 0.0, 0.0, 0.0]

#     def send_scpi(self, command):
#         wx2184c.send_scpi(self.address, self.address, command)

#     def start_from(self, step_index):
#         wx2184c.start_from(self.address, step_index)

#     def set_amplitudes(self, amps=[2.0, 2.0, 2.0, 2.0]):
#         wx2184c.set_amplitudes(self.address, amps)
#         self.amps = amps

#     def set_coarse_offsets(self, offsets=[0.0, 0.0, 0.0, 0.0]):
#         wx2184c.set_offsets(self.address, offsets)
#         self.coarse_offsets = offsets

#     def set_fine_offsets(self, offsets=[0.0, 0.0, 0.0, 0.0]):
#         # Not implemented
#         self.fine_offsets = offsets

#     def set_ch_amplitudes(self, ch, amp):
#         self.amps[ch - 1] = amp
#         self.set_amplitudes(self.amps)
    
#     def set_ch_coarse_offset(self, ch, offset):
#         self.coarse_offsets[ch - 1] = offset
#         self.set_coarse_offsets(self.coarse_offsets)
    
#     def set_ch_fine_offset(self, ch, offset):
#         # Not implemented
#         self.fine_offsets[ch - 1] = offset
#         self.set_fine_offsets(self.fine_offsets)

#     def load_sequence(self, data, display=False, options=None):
#         if display:
#             self.display(data)
#         # if autorange:
#         #     data, amps, offsets = self.autorange(data)
        
#         for ch_index in range(4):
#             ch_options = options['analog'][ch_index + 1]
#             if 'amplitude' in ch_options:
#                 self.amps[ch_index] = ch_options['amplitude']
#             if 'coarse_offset' in ch_options:
#                 self.coarse_offsets[ch_index] = ch_options['coarse_offset']
#             if 'fine_offset' in ch_options:
#                 self.fine_offsets[ch_index] = ch_options['fine_offset']

#         for ch_index in range(4):
#             data['analog'][ch_index + 1] = [
#                 (task - self.coarse_offsets[ch_index]) / self.amps[ch_index] for task in
#                 data['analog'][ch_index + 1]
#             ]

#         # if volt_max - volt_min > amp:
#         #     print(f'Warning: analog output CH{channel} is clipping.')
        
#         t = time.time()
#         print(f"Loading sequence...")
#         rep = wx2184c.load_sequence(self.address, data)
#         self.set_amplitudes(self.amps)
#         self.set_coarse_offsets(self.coarse_offsets)
#         self.set_fine_offsets(self.fine_offsets)
#         print(f"Finished in {time.time() - t} seconds.")