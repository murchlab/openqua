import openqua
import json
from numbers import Number

json_indent = 2

from typing import List, Dict, Any

class Variable:
    def __init__(self, dtype='INT', size=1):
        self.name = None
        self.dtype = dtype
        self.size = size
        openqua.current_context.add_variable(self)
        
    def to_dict(self):
        return {
            self.name: {
                'dtype': self.dtype,
                'size': self.size
            }
        }
    
    def to_dict_short(self):
        return {
            'variable': 'name'
        }
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
    
    
class Stream:
    def __init__(self):
        self.name = None
        self.tag = None
        self.save = 'last'
        openqua.current_context.add_stream(self)
        
    def save(self, tag):
        self.tag = tag
        self.save = 'last'
        
    def save_all(self, tag):
        self.tag = tag
        self.save = 'all'
        
    def to_dict(self):
        return {
            self.name: {
                'tag': self.tag,
                'save': self.save
            }
        }
    
    def to_dict_short(self):
        return {
            'stream': 'name'
        }
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
        
        
class Literal:
    def __init__(self, value):
        self.name = 'literal'
        self.value = value
        
    def to_dict(self):
        return {'literal': {'value': self.value}}
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
    
    def __mul__(self, other):
        if other is None:
            return self
        elif isinstance(other, str):
            return Pulse(other, amp=self)
        elif isinstance(other, Pulse):
            other.amp *= self
            other.offsets *= self
            return other
        elif isinstance(other, Literal):
            return Literal(self.value * other.value)
        elif isinstance(other, Offsets):
            return other * self
        else:
            print(other)
            raise Exception(f"Unsupported type 1'{type(other)}'.")
            
    def __neg__(self):
        self.value = -self.value
        return self

    __rmul__ = __mul__
    
    
class Offsets:
    def __init__(self, offset_values):
        if len(offset_values) == 1:
            self.name = 'single'
            self.single = offset_values[0]
        elif len(offset_values) == 2:
            self.name = 'IQ'
            self.I = offset_values[0]
            self.Q = offset_values[1]
        else:
            raise Exception('Too many offset values.')
            
    def to_dict(self):
        if self.name == 'single':
            return {'single': self.single.to_dict()}
        else:  # IQ
            return {'I': self.I.to_dict(), 'Q': self.Q.to_dict()}
        
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
        
    def __add__(self, other):
        if other is None:
            return self
        if isinstance(other, Offsets):
            if self.name == 'single':  # single + ?
                if other.name == 'single':  # single + single
                    return Offsets(self.single + other.single)
                else:  # single + IQ
                    return Offsets((self.single + other.I, self.single + other.Q))
            else:  # IQ + ?
                if other.name == 'single':  # IQ + single
                    return Offsets((self.I + other.single, self.Q + other.single))
                else:    # IQ + IQ
                    return Offsets((self.I + other.I, self.Q + other.Q))
        elif isinstance(other, str):
            return Pulse(other, offsets=self)
        elif isinstance(other, Pulse):
            other.offsets += self
            return other
        else:
            raise Exception(f"Unsupported type 2'{type(other)}'.")
            
    def __rsub__(self, other):
        return other + (-self)
    
    def __mul__(self, other):
        if isinstance(other, Literal):
            if self.name == 'single':
                return Offsets(self.single * other)
            else:  # IQ
                return Offsets((self.I * other, self.Q * other))
        else:
            raise Exception(f"Unsupported type 3'{type(other)}'.")
            
    def __neg__(self):
        if self.name == 'single':
            self.single = -self.single
        else:  # IQ
            self.I = -self.I
            self.Q = -self.Q
        return self

    __radd__ = __add__
    __rmul__ = __mul__
    
def eval_literal(expr):
    if expr is None:
        return
    if isinstance(expr, Number):
        return Literal(expr)
    else:
        return expr
        
        
class Element:
    def __init__(self, name):
        self.name = name
    
    
class Pulse:
    def __init__(self, pulse, amp=None, offsets=None):
        if isinstance(pulse, Pulse):
            self.name = pulse.name
            self.amp = pulse.amp
            self.offsets = pulse.offsets
        else:
            self.name = pulse
            self.amp = amp
            self.offsets = offsets
        
    def to_dict(self):
        dict_repr = {self.name: {}}
        if self.amp is not None:
            dict_repr[self.name]['amp'] = self.amp.to_dict()
        if self.offsets is not None:
            dict_repr[self.name]['offsets'] = self.offsets.to_dict()
        return dict_repr
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
    
    
class IntegrationWeights:
    def __init__(self, iw):
        self.name = iw
        
    def to_dict(self):
        return {self.name: {}}
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
        
        
class Statement:
    def __init__(self, name=''):
        self.name = name
        openqua.current_context.add_instruct(self)
        
    def _content_dict(self):
        return {}
        
    def to_dict(self):
        return {self.name: self._content_dict()}
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
        
        
        
class Align(Statement):
    def __init__(self, elements):
        super().__init__('align')
        self.elements = elements
        
    def _content_dict(self):
        return {
            'elements': [element.name for element in self.elements]
        }
    
    
class Wait(Statement):
    def __init__(self, duration, elements):
        super().__init__('wait')
        self.duration = duration
        self.elements = elements
        
    def _content_dict(self):
        return {
            'duration': self.duration.to_dict(),
            'elements': [element.name for element in self.elements]
        }
    
    
class Play(Statement):
    def __init__(self, pulse, element, duration=None, truncate=None):
        super().__init__('play')
        self.pulse = pulse
        self.element = element
        self.amp = pulse.amp
        self.offsets = pulse.offsets
        self.duration = duration
        self.truncate = truncate
        
    def _content_dict(self):
        content_dict = {
            'pulse': self.pulse.to_dict(),
            'element': self.element.name,
        }
        if self.duration is not None:
            content_dict['duration'] = self.duration.to_dict()
        if self.truncate is not None:
            content_dict['truncate'] = self.truncate.to_dict()
        return content_dict
    
    
class Measure(Statement):
    def __init__(self, pulse, element, outputs):
        super().__init__('measure')
        self.pulse = pulse
        self.element = element
        self.amp = pulse.amp
        self.offsets = pulse.offsets
        self.outputs = outputs
        
    def _content_dict(self):
        content_dict = {
            'pulse': self.pulse.to_dict(),
            'element': self.element.name,
            'outputs': [output.to_dict() for output in self.outputs]
        }
        return content_dict
    
    
class Save(Statement):
    def __init__(self, variable, stream):
        super().__init__('save')
        self.variable = variable
        self.stream = stream
        
    def _content_dict(self):
        content_dict = {
            'variable': self.variable.name,
            'stream': self.stream.name,
        }
        return content_dict

    
class FrameRotation(Statement):
    def __init__(self, angle, element):
        super().__init__('frame_rotation')
        self.angle = angle
        self.element = element
        
    def _content_dict(self):
        return {
            'angle': self.angle.to_dict(),
            'element': self.element.name
        }

    
class UpdateFrequency(Statement):
    def __init__(self, element, new_frequency, keep_phase):
        super().__init__('update_frequency')
        self.element = element
        self.new_frequency = new_frequency
        self.keep_phase = keep_phase
        
    def _content_dict(self):
        return {
            'element': self.element.name,
            'new_frequency': self.new_frequency.to_dict(),
            'keep_phase': self.keep_phase.to_dict()
        }
    
    
class Reset(Statement):
    def __init__(self):
        super().__init__('reset')
        
        
class Output:
    class RawIQ():
        def __init__(self, I, Q):
            self.name = 'raw_IQ'
            self.I = I
            self.Q = Q

        def to_dict(self):
            return {
                'raw_IQ':{
                    'I': self.I.name,
                    'Q': self.Q.name,
                }
            }
        
    class IQ():
        def __init__(self, iw_I, iw_Q, I, Q):
            self.name = 'IQ'
            self.iw_I = iw_I
            self.iw_Q = iw_Q
            self.I = I
            self.Q = Q

        def to_dict(self):
            return {
                'IQ':{
                    'iw_I': self.iw_I.name,
                    'iw_Q': self.iw_Q.name,
                    'I': self.I.name,
                    'Q': self.Q.name,
                }
            }
    

class Script:
    def __init__(self):
        self.variables = []
        self.body: List[Statement] = []

    def add_variable(self, variable):
        self.variables.append(variable)
        
    def add_instruct(self, instruct: Statement):
        self.body.append(instruct)
        
    def to_dict(self):
        variables_dict = {}
        for variable in self.variables:
            variables_dict.update(variable.to_dict())
        return {
            'variables': variables_dict,
            'body': [instruct.to_dict() for instruct in self.body]
        }
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
        
        
class ResultAnalysis:
    def __init__(self):
        self.streams = []
        
    def add_stream(self, stream):
        self.streams.append(stream)
        
    def to_dict(self):
        streams_dict = {}
        for stream in self.streams:
            streams_dict.update(stream.to_dict())
        return {
            'streams': streams_dict
        }


class Program:
    def __init__(self):
        self.script = Script()
        self.result_analysis = ResultAnalysis()
        self._num_variables = 0
        self._num_streams = 0
        
    def add_variable(self, variable):
        self._num_variables += 1
        variable.name = f'v{self._num_variables}'
        self.script.add_variable(variable)
        
    def add_stream(self, stream):
        self._num_streams += 1
        stream.name = f'r{self._num_streams}'
        self.result_analysis.add_stream(stream)
        
    def add_instruct(self, instruct):
        self.script.add_instruct(instruct)
        
    def to_dict(self):
        return {'script': self.script.to_dict(), 'result_analysis': self.result_analysis.to_dict()}
        
    def _compile(self, config, verbose=False):
        from openqua.compilers import awg_compiler

        return awg_compiler(self, config, verbose)
        
    def __enter__(self):
        openqua.current_context = self
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        openqua.current_context = None
    
    def __repr__(self):
        return json.dumps(self.to_dict(), indent=json_indent)
