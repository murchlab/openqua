import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openqua as q
import numpy as np

from config.config_dummy import config

cf = config

m = q.Manager(cf)
with q.program() as program:
    I = q.declare(q.fixed)
    Q = q.declare(q.fixed)
    stream_i = q.declare_stream()
    stream_q = q.declare_stream()

    for i in range(101):
        q.align('muninn1_ge', 'muninn2_ge', 'res1', 'res2')
        q.play('pi_pulse_muninn1_ge' * q.amp(0.121), 'muninn1_ge', duration=i)
        q.play('pi_pulse_muninn2_ge' * q.amp(0.121), 'muninn2_ge', duration=i)
        q.align('muninn1_ge', 'muninn2_ge', 'res1', 'res2')
        q.measure('meas_pulse_res1' * q.amp(0.121), 'res1',
                  q.demod.IQ('integ_w_res1_cosine', 'integ_w_res1_sine', I, Q)
                 )
        q.measure('meas_pulse_res2' * q.amp(0.121), 'res2',
                  q.demod.IQ('integ_w_res2_cosine', 'integ_w_res2_sine', I, Q)
                 )

        q.save(I, stream_i)
        q.save(Q, stream_q)
        q.reset()

    stream_i.save_all('I')
    stream_q.save_all('Q')

m.execute(program, verbose=True)