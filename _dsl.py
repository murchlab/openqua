import openqua
from . import ast
import queue
import numpy as np

current_context = None


fixed = 'REAL'


def program():
    return ast.Program()


def declare(dtype=int, size=1):
    if dtype == int:
        dtype = 'INT'
    elif dtype == bool:
        dtype = 'BOOL'
    elif dtype == fixed:
        dtype = 'REAL'
    else:
        raise TypeError
    return ast.Variable(dtype, size)


def declare_stream():
    return ast.Stream()


def align(*elements):
    elements = [ast.Element(element) for element in elements]
    return ast.Align(elements)
    
    
def wait(duration, *elements):
    duration = ast.eval_literal(duration)
    elements = [ast.Element(element) for element in elements]
    return ast.Wait(duration, elements)
    
    
def play(pulse, element, duration=None, truncate=None):
    pulse = ast.Pulse(pulse)
    element = ast.Element(element)
    duration = ast.eval_literal(duration)
    truncate = ast.eval_literal(truncate)
    return ast.Play(pulse, element, duration, truncate)
    
    
def measure(pulse, element, *outputs):
    pulse = ast.Pulse(pulse)
    element = ast.Element(element)
    return ast.Measure(pulse, element, outputs)


def save(variable, stream):
    return ast.Save(variable, stream)
    
    
def amp(amplitude):
    return ast.eval_literal(amplitude)


def offsets(*offset_values):
    return ast.Offsets(tuple(ast.eval_literal(offset_value) for offset_value in offset_values))


def frame_rotation(angle, element):
    angle = ast.eval_literal(angle)
    element = ast.Element(element)
    return ast.FrameRotation(angle, element)
    
    
def frame_rotation_2pi(angle, element):
    return frame_rotation(2 * np.pi * angle, element)
    
    
def update_frequency(element, new_frequency, keep_phase=False):
    element = ast.Element(element)
    new_frequency = ast.eval_literal(new_frequency)
    keep_phase = ast.eval_literal(keep_phase)
    return ast.UpdateFrequency(element, new_frequency, keep_phase)
    
    
def reset():
    return ast.Reset()


class demod:
    @staticmethod
    def raw_IQ(I, Q):
        return ast.Output.RawIQ(I, Q)
    
    @staticmethod
    def IQ(iw_I, iw_Q, I, Q):
        iw_I = ast.IntegrationWeights(iw_I)
        iw_Q = ast.IntegrationWeights(iw_Q)
        return ast.Output.IQ(iw_I, iw_Q, I, Q)
