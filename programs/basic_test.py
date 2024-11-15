import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openqua as q
import numpy as np
from config.config_dummy import config

cf = config

m = q.Manager(cf)
with q.program() as test:
    for i in range(10):
        q.align('muninn1_ge', 'res1')
        q.wait(100, "res1")
        q.align('muninn1_ge', 'res1')
        q.play('pi_pulse_muninn1_ge' * q.amp(0.5), 'muninn1_ge', duration=100, truncate=50)
        q.update_frequency('muninn1_ge', 3.9E6, keep_phase=False)
        q.frame_rotation(np.pi / 2, 'muninn1_ge')
        q.frame_rotation_2pi(1 / 4, 'muninn1_ge')
        q.measure('pi_pulse_muninn1_ge', 'res1')
        q.reset()

m.execute(test, verbose=True)
