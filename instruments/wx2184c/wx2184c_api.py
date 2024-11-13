from . import tewx
import numpy as np


def send_scpi(instr_addr, command):
    inst = tewx.TEWXAwg(instr_addr, paranoia_level=1)
    inst.send_cmd(command)
    inst.close()


def start_from(instr_addr, step_index=0):
    # Only starting from the beginning of the sequence is supported.
    inst = tewx.TEWXAwg(instr_addr, paranoia_level=1)
    inst.send_cmd('*CLS') # Clear errors
    #inst.send_cmd('*RST') # Reset the device
    inst.send_cmd(":FREQ:RAST 1000000001.000000", paranoia_level=1)
    inst.send_cmd(":FREQ:RAST 1000000000.000000", paranoia_level=1)
    inst.close()


def set_amplitudes(instr_addr, amps=[2.0, 2.0, 2.0, 2.0]):
    print(instr_addr)
    inst = tewx.TEWXAwg(instr_addr, paranoia_level=1)
    for ch_index in range(4):
        inst.send_cmd(f':INST:SEL {ch_index + 1}')
        inst.send_cmd(f':VOLT {amps[ch_index]}')
    inst.close()


def set_offsets(instr_addr, offsets=[0.0, 0.0, 0.0, 0.0]):
    inst = tewx.TEWXAwg(instr_addr, paranoia_level=1)
    for ch_index in range(4):
        inst.send_cmd(f':INST:SEL {ch_index + 1}')
        inst.send_cmd(f':VOLT:OFFS {offsets[ch_index]}')
    inst.close()


def load_sequence(instr_addr, data):
    num_steps = len(data['analog'][1])

    # Generating waveform binaries
    waveform_bin_list = [[], [], [], []]
    for ch_index in range(4):
        for analog_waveform in data['analog'][ch_index + 1]:
            # The analog waveform was normalized to [-1, +1] volt
            waveform_bin = np.round((2 ** 13) * analog_waveform + 8191.5)
            waveform_bin = waveform_bin.clip(0, (2 ** 14) - 1)
            waveform_bin = waveform_bin.astype('uint16')
            waveform_bin_list[ch_index].append(waveform_bin)

    for ch_index in range(4):
        step_index = 0
        ch_mark_index = 2 * (ch_index // 2)
        if ch_index % 2:
            for digital_waveform in data['digital'][ch_index + 1]:
                waveform_bin_list[ch_mark_index][step_index] += np.uint16(2 ** 15) * digital_waveform
                step_index += 1
        else:
            for digital_waveform in data['digital'][ch_index + 1]:
                waveform_bin_list[ch_mark_index][step_index] += np.uint16(2 ** 14) * digital_waveform
                waveform_bin_list[ch_mark_index][step_index] += np.uint16(2 ** 15) * digital_waveform
                step_index += 1
    
    # Initializing the instrument
    inst = tewx.TEWXAwg(instr_addr, paranoia_level=1)
    inst.send_cmd('*CLS') # Clear errors
    inst.send_cmd('*RST') # Reset the device #need to add several commands to set up device to use markers and other configurations
    inst.send_cmd(':OUTP:ALL 0')
    seg_quantum = inst.get_dev_property('seg_quantum', 16)

    # Downloading the wave data
    seg_len = np.array([len(waveform) for waveform in data['analog'][1]], dtype=np.uint32)
    pseudo_seg_len = np.sum(seg_len) + (num_steps - 1) * seg_quantum
    wav_dat = np.zeros(2 * pseudo_seg_len, 'uint16')

    for ch_index in range(4):
        if ch_index % 2:
            continue
        offs = 0
        for wav1, wav2 in zip(waveform_bin_list[ch_index], waveform_bin_list[ch_index + 1]):
            offs = inst.make_combined_wave(wav1, wav2, wav_dat, dest_array_offset=offs, add_idle_pts=(0!=offs))

        # select channel:
        inst.send_cmd(':INST:SEL {0}'.format(ch_index + 1))
        
        inst.send_cmd('MARK:SEL 1')
        inst.send_cmd('MARK:SOUR USER')
        inst.send_cmd('MARK:VOLT:HIGH {}'.format(1.2))
        inst.send_cmd('MARK:STAT ON')
        inst.send_cmd('MARK:SEL 2')
        inst.send_cmd('MARK:SOUR USER')
        inst.send_cmd('MARK:VOLT:HIGH {}'.format(1.2))
        inst.send_cmd('MARK:STAT ON')
        # select user-mode (arbitrary-wave):
        inst.send_cmd(':FUNC:MODE FIX')
        # delete all segments (just to be sure):
        inst.send_cmd(':TRAC:DEL:ALL')
        inst.send_cmd('SEQ:DEL:ALL')
        # set combined wave-downloading-mode:
        inst.send_cmd(':TRAC:MODE COMB')
        # define the pseudo segment:
        inst.send_cmd(':TRAC:DEF 1,{0}'.format(np.uint32(pseudo_seg_len)))
        # select segment 1:
        inst.send_cmd(':TRAC:SEL 1')
        # download binary data:
        
        inst.send_binary_data(':TRAC:DATA', wav_dat)
        
        # ---------------------------------------------------------------------
        # Write the *appropriate* segment-table
        # (array of 'uint32' values holding the segments lengths)
        # ---------------------------------------------------------------------
        inst.send_binary_data(':SEGM:DATA', seg_len)
        # Setting up sequence mode
        for step in range(1, num_steps + 1):
            inst.send_cmd(':SEQ:DEF {},{},1,0'.format(step, step))
        inst.send_cmd(':FUNC:MODE SEQ')
        inst.send_cmd(':SEQ:ADV STEP')
        # Setting up the triggers
        inst.send_cmd(':TRIG:SOUR EVEN')
        inst.send_cmd(':TRIG:COUN 1')
        # Turn channels on:
        inst.send_cmd(':INIT:CONT 0')

    inst.send_cmd(':INST:COUP:STAT ON')
    inst.send_cmd(':OUTP:ALL 1')

    # query system error
    syst_err = inst.send_query(':SYST:ERR?')
    print(syst_err)
    inst.close()