import json
import os
import numpy as np

config_folder = os.path.dirname(os.path.realpath(__file__))
std_vals_filename = 'standard_values.json'

with open(os.path.join(config_folder, std_vals_filename), 'r') as f:
    std_vals = json.load(f)

# Controller name
cname = 'dummycontroller'

# Resonator
# #Frequencies
lo_res1 = std_vals['QPUs']['Muninn']['res1']['lo_frequency']
if_res1 = std_vals['QPUs']['Muninn']['res1']['intermediate_frequency']

lo_res2 = std_vals['QPUs']['Muninn']['res2']['lo_frequency']
if_res2 = std_vals['QPUs']['Muninn']['res2']['intermediate_frequency']

# #Measure pulse
amp_meas_res1 = std_vals['QPUs']['Muninn']['res1']['pulses']['meas_pulse']['amp']
len_meas_res1 = std_vals['QPUs']['Muninn']['res1']['pulses']['meas_pulse']['len(ns)']

amp_meas_res2 = std_vals['QPUs']['Muninn']['res2']['pulses']['meas_pulse']['amp']
len_meas_res2 = std_vals['QPUs']['Muninn']['res2']['pulses']['meas_pulse']['len(ns)']

# Muninn1
# #Frequencies
lo_muninn1_ge = std_vals['QPUs']['Muninn']['muninn1_ge']['lo_frequency']
if_muninn1_ge = std_vals['QPUs']['Muninn']['muninn1_ge']['intermediate_frequency']

# #Pi-pulse
amp_pi_muninn1_ge = std_vals['QPUs']['Muninn']['muninn1_ge']['pulses']['pi_pulse']['amp']
len_pi_muninn1_ge = std_vals['QPUs']['Muninn']['muninn1_ge']['pulses']['pi_pulse']['len(ns)']

# Muninn2
# #Frequencies
lo_muninn2_ge = std_vals['QPUs']['Muninn']['muninn2_ge']['lo_frequency']
if_muninn2_ge = std_vals['QPUs']['Muninn']['muninn2_ge']['intermediate_frequency']

# #Pi-pulse
amp_pi_muninn2_ge = std_vals['QPUs']['Muninn']['muninn2_ge']['pulses']['pi_pulse']['amp']
len_pi_muninn2_ge = std_vals['QPUs']['Muninn']['muninn2_ge']['pulses']['pi_pulse']['len(ns)']

# configuration

config = {
    'controllers': {
        cname: {
            'type': 'dummycontroller',
            'analog_outputs': {
                1: {},
                2: {},
                3: {},
                4: {},
                5: {},
                6: {},
                7: {},
                8: {}
            },
            'digital_outputs': {
                1: {},
                2: {},
                3: {},
                4: {},
                5: {},
                6: {},
                7: {},
                8: {}
            },
            'analog_inputs': {
                1: {},
                2: {},
            },
        }
    },
    'elements': {
        'res1': {
            'mixInputs': {
                'I': (cname, 3),
                'Q': (cname, 4),
                'lo_frequency': lo_res1,
                'mixer': 'mixer_LO',
            },
            'intermediate_frequency': if_res1,
            'digitalInputs': {
                'alazar_trigger': {
                    'port': (cname, 3),
                    'delay': -1000,
                    'buffer': 0,
                }
            },
            'pulses': [
                'meas_pulse_res1'
            ],
            'time_of_flight': std_vals['QPUs']['Muninn']['res1']['time_of_flight'],
            'outputs': {
                'out1': ('alazar', 1)
            }
        },
        'res2': {
            'mixInputs': {
                'I': (cname, 3),
                'Q': (cname, 4),
                'lo_frequency': lo_res2,
                'mixer': 'mixer_LO',
            },
            'intermediate_frequency': if_res2,
            'digitalInputs': {
                'alazar_trigger': {
                    'port': (cname, 3),
                    'delay': -1000,
                    'buffer': 0,
                }
            },
            'pulses': [
                'meas_pulse_res2'
            ],
            'time_of_flight': std_vals['QPUs']['Muninn']['res2']['time_of_flight'],
            'outputs': {
                'out1': ('alazar', 1)
            }
        },
        'muninn1_ge': {
            'mixInputs': {
                'I': (cname, 7),
                'Q': (cname, 8),
                'lo_frequency': lo_muninn1_ge,
                'mixer': 'mixer_munnin1',
            },
            'intermediate_frequency': if_muninn1_ge,
            'pulses': [
                'pi_pulse_muninn1_ge'
            ],
        },
        'muninn2_ge': {
            'mixInputs': {
                'I': (cname, 5),
                'Q': (cname, 6),
                'lo_frequency': lo_muninn2_ge,
                'mixer': 'mixer_munnin2',
            },
            'intermediate_frequency': if_muninn2_ge,
            'pulses': [
                'pi_pulse_muninn2_ge'
            ],
        }
    },
    'pulses': {
        'meas_pulse_res1': {
            'operation': 'measurement',
            'length': len_meas_res1,
            'waveforms': {
                'I': 'meas_wf_res1_I',
                'Q': 'meas_wf_res1_Q'
            },
            'integration_weights': {
                'integ_w_c': 'integ_w_cosine',
                'integ_w_s': 'integ_w_sine'
            },
            'digital_marker': 'marker1'
        },
        'meas_pulse_res2': {
            'operation': 'measurement',
            'length': len_meas_res2,
            'waveforms': {
                'I': 'meas_wf_res2_I',
                'Q': 'meas_wf_res2_Q'
            },
            'integration_weights': {
                'integ_w_c': 'integ_w_cosine',
                'integ_w_s': 'integ_w_sine'
            },
            'digital_marker': 'marker1'
        },
        'pi_pulse_muninn1_ge': {
            'operation': 'control',
            'length': len_pi_muninn1_ge,
            'waveforms': {
                'I': 'pi_wf_muninn1_ge',
                'Q': 'zero_wf'
            }
        },
        'pi_pulse_muninn2_ge': {
            'operation': 'control',
            'length': len_pi_muninn2_ge,
            'waveforms': {
                'I': 'pi_wf_muninn2_ge',
                'Q': 'zero_wf'
            }
        }
    },
    'waveforms': {
        'zero_wf': {
            'type': 'constant',
            'sample': 0.0
        },
        'meas_wf_res1_I': {
            'type': 'constant',
            'sample': amp_meas_res1
        },
        'meas_wf_res1_Q': {
            'type': 'constant',
            'sample': 0.0
        },
        'meas_wf_res2_I': {
            'type': 'constant',
            'sample': amp_meas_res2
        },
        'meas_wf_res2_Q': {
            'type': 'constant',
            'sample': 0.0
        },
        'pi_wf_muninn1_ge': {
            'type': 'constant',
            'sample': amp_pi_muninn1_ge
        },
        'pi_wf_muninn2_ge': {
            'type': 'constant',
            'sample': amp_pi_muninn2_ge
        }
    },
    'digital_waveforms': {
        'marker1': {
            'samples': [(1, 500), (0, 0)]
        }
    },
    'integration_weights': {
        'integ_w_cosine': {
            'cosine': [(1, len_meas_res1)],
            'sine': [(0, len_meas_res1)],
        },
        'integ_w_sine': {
            'cosine': [(0, len_meas_res1)],
            'sine': [(1, len_meas_res1)],
        },
        'integ_w_cosine': {
            'cosine': [(1, len_meas_res2)],
            'sine': [(0, len_meas_res2)],
        },
        'integ_w_sine': {
            'cosine': [(0, len_meas_res2)],
            'sine': [(1, len_meas_res2)],
        }
    }
}
