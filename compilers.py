# Todos:
#   Solve the warning: Missing module docstring
import numbers
import numpy as np
from scipy.interpolate import interp1d


class Element:
    def __init__(self, element_data):
        self.default_intermediate_frequence = element_data[
            'intermediate_frequency']
        self.intermediate_frequency = self.default_intermediate_frequence
        self.phase = 0.0
        self.time = 0

        if 'singleInput' in element_data:
            self.analogInputs = SingleInput(element_data['singleInput'])
        elif 'mixInputs' in element_data:
            self.analogInputs = MixInputs(element_data['mixInputs'])
        else:
            self.analogInputs = None

        if 'digitalInputs' in element_data:
            self.digitalInputs = []
            for _input_name, port_data in element_data[
                    'digitalInputs'].items():
                controller, port = port_data['port']

                if 'delay' in port_data:
                    delay = port_data['delay']
                else:
                    delay = 0

                if 'buffer' in port_data:
                    buffer = port_data['buffer']
                else:
                    buffer = 0

                self.digitalInputs.append(
                    DigitalInput(
                        controller, port,
                        delay=delay, buffer=buffer
                    )
                )
        else:
            self.digitalInputs = []
            
    def reset(self):
        self.intermediate_frequency = self.default_intermediate_frequence
        self.phase = 0.0
        self.time = 0

    def frame_rotate(self, angle):
        self.phase += angle

    def update_frequency(self, new_frequency, keep_phase=False):
        if keep_phase:
            self.phase += 2 * np.pi\
                * (self.intermediate_frequency - new_frequency) * self.time
        self.intermediate_frequency = new_frequency

    def generate(self, pulse, amplitude=None, offsets=None, duration=None,
                 truncate=None, time=None):
        if time is None:
            time = self.time
        waveforms = {}
        if self.analogInputs is not None:
            waveforms['analog'] = self.analogInputs.generate(pulse, self.intermediate_frequency, time, self.phase, amplitude, offsets, duration, truncate)

        for digitalInput in self.digitalInputs:
            waveforms['digital'] = digitalInput.generate(pulse)

        return waveforms
    
    def generate_demod(self, pulse, output, time=None):
        if time is None:
            time = self.time
        return pulse.generate_demod(output, self.intermediate_frequency, time, self.phase)

    def ports(self):
        ports = set()
        if self.analogInputs is not None:
            ports.update(self.analogInputs.ports())

        for digitalInput in self.digitalInputs:
            ports.add(digitalInput.output_port)

        return ports
    
    def _digital_inputs_pad_clock(self, pulse):
        if pulse.digital_marker is not None:
            if (self.digitalInputs[0].delay - self.digitalInputs[0].buffer + self.time) % 2:
                self.time += 1
            


class SingleInput:
    def __init__(self, singleInput_data):
        port_data = singleInput_data['port']
        self.output_port = (port_data[0], port_data[1])

    def ports(self):
        return {self.output_port}

    def generate(self, pulse, intermediate_frequency, time, phase=0.0, amplitude=None, offset=None, duration=None, truncate=None):
        if pulse.single_waveform is None:
            return {}
        return {self.output_port: pulse.generate_single(intermediate_frequency, time, phase, amplitude, offset, duration, truncate)}


class MixInputs:
    def __init__(self, mixInput_data):
        self.I_output_port = mixInput_data['I']
        self.Q_output_port = mixInput_data['Q']
        self.lo_frequency = mixInput_data['lo_frequency']
        self.mixer = mixInput_data['mixer']

    def ports(self):
        return {self.I_output_port, self.Q_output_port}

    def generate(self, pulse, intermediate_frequency, time, phase=0.0, amplitude=None, offsets=None, duration=None, truncate=None):
        if pulse.IQ_waveforms is None:
            return {}
        IQ_waveforms = pulse.generate_IQ(intermediate_frequency, time, phase, amplitude, offsets, duration, truncate)
        return {
            self.I_output_port: IQ_waveforms[0],
            self.Q_output_port: IQ_waveforms[1]
        }


class DigitalInput:
    def __init__(self, controller, port, delay=0, buffer=0):
        self.output_port = (controller, port)
        self.delay = delay
        self.buffer = buffer

    def generate(self, pulse):
        if pulse.digital_marker is None:
            return {}
        return {self.output_port: pulse.generate_digital(self.delay, self.buffer)}


class Pulse:
    def __init__(self, pulse_data, waveforms, digital_waveforms, integration_weights):
        self.operation = pulse_data['operation']
        self.length = pulse_data['length']
        self.IQ_waveforms = None
        self.single_waveform = None
        self.digital_marker = None
        self.integration_weights = None
        
        if 'waveforms' in pulse_data:
            pulse_waveforms = pulse_data['waveforms']
            if 'single' in pulse_data['waveforms']:
                self.single_waveform = SingleWaveform(waveforms[pulse_waveforms['single']])

            elif 'I' in pulse_data['waveforms'] and 'Q' in pulse_data['waveforms']:
                I_waveform = waveforms[pulse_waveforms['I']]
                Q_waveform = waveforms[pulse_waveforms['Q']]
                self.IQ_waveforms = IQWaveforms(I_waveform, Q_waveform)

        if 'digital_marker' in pulse_data:
            self.digital_marker = digital_waveforms[pulse_data['digital_marker']]
            
        if 'integration_weights' in pulse_data:
            self.integration_weights = (
                integration_weights[pulse_data['integration_weights']['integ_w_c']],
                integration_weights[pulse_data['integration_weights']['integ_w_s']]
            )

    def generate_single(self, intermediate_frequency, time, phase=0.0, amplitude=None, offset=None, duration=None, truncate=None):
        waveform = self.single_waveform.generate(self.length, intermediate_frequency, time, phase, duration, truncate)
        if amplitude is not None:
            waveform *= amplitude
        if offset is not None:
            waveform += offset
        return waveform

    def generate_IQ(self, intermediate_frequency, time, phase=0.0, amplitude=None, offsets=None, duration=None, truncate=None):
        waveform = self.IQ_waveforms.generate(self.length, intermediate_frequency, time, phase, duration, truncate)
        if amplitude is not None:
            waveform *= amplitude
        if offsets is not None:
            if isinstance(offsets, numbers.Number):
                waveform += offsets
            else:
                waveform += np.reshape(np.array(offsets), (2, 1))
        return waveform

    def generate_digital(self, delay=0, buffer=0):
        return (delay - buffer, self.digital_marker.generate(self.length, buffer))
    
    def generate_demod(self, output, intermediate_frequency, time, phase=0.0):
        if output.name == 'raw_IQ':
            length = max(self.integration_weights[0].length, self.integration_weights[1].length)
            return [
                ('raw_IQ', ['unsaved_I'], length),
                ('raw_IQ', ['unsaved_Q'], length)
            ]
        
        elif output.name == 'IQ':
            iw_I = self.integration_weights[0].generate(intermediate_frequency, time, phase)
            iw_Q = self.integration_weights[1].generate(intermediate_frequency, time, phase)
            return [
                ('IQ', ['unsaved_I'], iw_I),
                ('IQ', ['unsaved_Q'], iw_Q)
            ]
            

class SingleWaveform:
    def __init__(self, waveform):
        self.waveform = waveform

    def generate(self, length, intermediate_frequency, time, phase=0.0, duration=None, truncate=None):
        waveform = self.waveform.generate(length, duration, truncate)

        if truncate is not None:
            length = truncate

        t = (np.arange(length) + time) * 1E-9
        R_cos = np.cos(2 * np.pi * intermediate_frequency * t + phase)
        return waveform * R_cos


class IQWaveforms:
    def __init__(self, I_waveform, Q_waveform):
        self.I = I_waveform
        self.Q = Q_waveform

    def generate(self, length, intermediate_frequency, time, phase=0.0, duration=None, truncate=None, switch_IQ=False):
        I_waveform = self.I.generate(length, duration, truncate)
        Q_waveform = self.Q.generate(length, duration, truncate)
        IQ_waveforms = np.vstack((I_waveform, Q_waveform))

        if truncate is not None:
            length = truncate
        elif duration is not None:
            length = duration

        t = (np.arange(length) + time) * 1E-9
        phi = 2 * np.pi * intermediate_frequency * t + phase
        R_cos = np.cos(phi)
        R_sin = np.sin(phi)
        
        if switch_IQ:
            R = np.array([
                [R_cos, -R_sin],
                [R_sin, R_cos]
            ])
        else:
            R = np.array([
                [R_cos, R_sin],
                [-R_sin, R_cos]
            ])
            
        IQ_waveforms = np.einsum('ijt,jt->it', R, IQ_waveforms)
        return IQ_waveforms


#
# The class for analog waveforms.
#
class Waveform:
    # Initialization
    # Parameters:
    #   waveform_data: A dictionary containing the analog waveform
    #       specification. This parameter contains all the necessary
    #       information to define and construct a waveform. It must include a
    #       key 'type' that specifies the waveform's nature, determining how
    #       the waveform is generated and what additional data is required.
    #       The waveform_data dictionary supports the following keys
    #       'type': A string that indicates the type of the waveform. It
    #           defines how the waveform will be constructed and what
    #           additional keys are expected in the waveform_data dictionary.
    #           Possible values are:
    #           'constant': Specifies that the waveform is a constant waveform,
    #               meaning it will produce a sequence of samples where each
    #               sample has the same value.
    #           'arbitrary': Indicates that the waveform is defined by an
    #               arbitrary sequence of samples, allowing for custom
    #               waveform shapes.
    #       For 'constant' type:
    #       'sample': A numerical value representing the constant value for
    #           each sample in the waveform.
    #       For 'arbitrary' type:
    #       'samples': An array or list of numerical values representing the
    #           waveform's shape. Each element in this array corresponds to a
    #           sample value in the generated waveform.
    def __init__(self, waveform_data):
        # Initialize the Waveform object with waveform data.
        # The waveform data must specify the type of waveform ('constant' or
        # 'arbitrary').
        self.type = waveform_data['type']  # Type of waveform, either
        # 'constant' or 'arbitrary'.

        # For 'constant' waveforms, store the constant value to be used for
        # the waveform sample.
        if self.type == 'constant':
            self.sample = waveform_data['sample']  # The constant value for
            # every sample in the waveform.

        # For 'arbitrary' waveforms, store the array of samples defining the
        # waveform shape.
        elif self.type == 'arbitrary':
            self.samples = waveform_data['samples']  # Array of samples
            # defining the arbitrary waveform shape.

        # Raise an exception if an unknown waveform type is provided.
        else:
            raise Exception(f"Unknown waveform type '{self.type}'.")

    # Generating the waveform
    # Parameters:
    #    length: The desired length of the generated waveform. This is the
    #            number of samples in the waveform.
    #    duration: (optional): If provided, the waveform is interpolated to
    #              fit this new duration. This effectively changes the
    #              sampling rate or stretches/compresses the waveform in time.
    #    truncate: (optional): If provided, the waveform is truncated to this
    #              number of samples. Useful for cutting off the waveform
    #              after a certain point.
    # Returns: The method returns a numpy array representing the generated
    #          waveform. This waveform can be a constant array (if the type is
    #          'constant'), an array of provided samples (if the type is
    #          'arbitrary'), or an interpolated/truncated version of these,
    #          depending on the provided duration and truncate parameters.
    # Todos:
    #   Solve the warning: raising too general exception
    #   Solve the warning: missing function or method docstring
    def generate(self, length, duration=None, truncate=None):
        # Generate the waveform based on its type and provided parameters.

        # For 'constant' waveforms, create an array of the specified length
        # filled with the constant sample value.
        if self.type == 'constant':
            waveform = np.full(length, self.sample)  # Array filled with 'sample' value, of size 'length'.

        # For 'arbitrary' waveforms, use the provided samples as the waveform.
        # An exception is raised if the provided sample array does not match
        # the expected length.
        elif self.type == 'arbitrary':
            if len(self.samples) != length:
                raise Exception(
                    f"Length of the waveform ({len(self.samples)}) does not "
                    f"match the expected length ({length})."
                    )
            waveform = self.samples  # Use the provided samples directly as
            # the waveform.

        # Raise an exception if an unexpected waveform type is encountered.
        else:
            raise Exception(f"Unknown waveform type '{self.type}'.")

        # If a 'duration' is provided, interpolate the waveform to fit the new
        # duration. This is useful for adjusting the waveform's sampling rate
        # or stretching/compressing its time base.
        if duration is not None:
            t = np.linspace(0, length - 1, duration)  # Create a time vector
            # for the new duration.
            f = interp1d(np.arange(length), waveform)  # Create an
            # interpolation function based on the original waveform.
            waveform = f(t)  # Interpolate the waveform to fit the new
            # duration.

        # If a 'truncate' value is provided, truncate the waveform to the
        # specified length. This is useful for cutting off the waveform after
        # a certain number of samples.
        if truncate is not None:
            if truncate > len(waveform):
                raise Exception(
                    f"Truncate value ({truncate}) is larger than the waveform "
                    f"length ({len(waveform)})."
                    )
            waveform = waveform[:truncate]  # Truncate the waveform to the
            # specified length.

        return waveform  # Return the generated (and possibly interpolated or
        # truncated) waveform.


#
# The class for digital waveforms.
#
class DigitalWaveform:
    def __init__(self, digital_waveform_data):
        # Initialize the DigitalWaveform object with provided waveform data.
        self.samples = np.empty(0, dtype=bool)  # Start with an empty array
        # for digital waveform samples.

        # Determine the final value of the waveform based on the last sample
        # value and its duration. If the duration of the last sample is 0, the
        # final value is set to the value of that sample. Otherwise, the final
        # value is set to False (indicating a low signal by default).
        if digital_waveform_data['samples'][-1][1] == 0:
            self.final_value = digital_waveform_data['samples'][-1][0]
        else:
            self.final_value = False

        # Construct the digital waveform by appending samples according to the
        # specified values and lengths.
        for val, length in digital_waveform_data['samples']:
            self.samples = np.pad(
                self.samples, (0, length), 'constant', constant_values=val)

    def generate(self, length, buffer=0):
        # Generate the digital waveform based on the specified length and
        # buffer.

        # If the requested length is longer than the current waveform, pad the
        # waveform to the desired length using the final value to fill the
        # extra space.
        if length > len(self.samples):
            waveform = np.pad(
                self.samples, (0, length - len(self.samples)), 'constant',
                constant_values=self.final_value)
        else:
            # If the requested length is shorter or equal to the current
            # waveform, truncate the waveform to the desired length.
            waveform = self.samples[:length]

        # If a buffer is specified, apply a convolution operation to the
        # waveform to simulate the effect of a digital buffer. This
        # effectively broadens the transitions in the digital signal.
        if buffer:
            # Convolve the waveform with a kernel of ones of width
            # '2 * buffer + 1' to simulate the buffer effect. The resulting
            # waveform is a logical operation, where True indicates a high
            # signal wherever the convolution result is nonzero.
            return np.convolve(waveform, np.full(2 * buffer + 1, 1)) != 0
        else:
            # If no buffer is specified, return the waveform as is.
            return waveform

        
        
class IntegrationWeight:
    def __init__(self, integration_weight_data):
        self.cosine = np.empty(0, dtype=np.float64)
        self.sine = np.empty(0, dtype=np.float64)
        for val, length in integration_weight_data['cosine']:
            self.cosine = np.pad(self.cosine, (0, length), 'constant', constant_values=val)
        for val, length in integration_weight_data['sine']:
            self.sine = np.pad(self.sine, (0, length), 'constant', constant_values=val)
        
        if len(self.cosine) > len(self.sine):
            self.length = len(self.cosine)
            self.sine = np.pad(self.sine, (0, self.length - len(self.sine)), 'constant', constant_values=0)
        else:
            self.length = len(self.sine)
            self.cosine = np.pad(self.cosine, (0, self.length - len(self.cosine)), 'constant', constant_values=0)

        norm = np.linalg.norm(self.cosine + 1j * self.sine)
        self.cosine /= norm
        self.sine /= norm

    def generate(self, intermediate_frequency, time, phase=0.0, switch_IQ=False):
        t = (np.arange(self.length) + time) * 1E-9
        phi = 2 * np.pi * intermediate_frequency * t + phase
        R_cos = np.cos(phi)
        R_sin = np.sin(phi)
        
        if switch_IQ:
            R = np.array([
                [R_cos, -R_sin],
                [R_sin, R_cos]
            ])
        else:
            R = np.array([
                [R_cos, R_sin],
                [-R_sin, R_cos]
            ])
            
        iw = np.einsum('ijt,jt->it', R, [self.cosine, self.sine])
        return iw


class Task:
    def __init__(self, analog_outputs, digital_outputs):
        self.start_time = 0
        self.analog_outputs = analog_outputs
        self.digital_outputs = digital_outputs
        
        self.analog_output_tasks = {}
        self.digital_output_tasks = {}
        
        self.tasks_init()

    def tasks_init(self):
        for port in self.analog_outputs:
            self.analog_output_tasks[port] = np.empty(0, dtype=np.float64)
        for port in self.digital_outputs:
            self.digital_output_tasks[port] = np.empty(0, dtype=bool)
            
    def offset_start_time(self, delta):  # delta > 0
        for port in self.analog_outputs:
            self.analog_output_tasks[port] = np.pad(self.analog_output_tasks[port], (delta, 0), 'constant')
        for port in self.digital_outputs:
            self.digital_output_tasks[port] = np.pad(self.digital_output_tasks[port], (delta, 0), 'constant')
        self.start_time -= delta

    def len_max(self):
        len_max_val = 0
        for _, task in self.analog_output_tasks.items():
            if len(task) > len_max_val:
                len_max_val = len(task)
        for _, task in self.digital_output_tasks.items():
            if len(task) > len_max_val:
                len_max_val = len(task)
        return len_max_val
    
    def align_analog_output(self, port, time_wf_start, time_wf_end):
        len_wf = len(self.analog_output_tasks[port])
        if time_wf_end - self.start_time > len_wf:
            self.analog_output_tasks[port] = np.pad(
                self.analog_output_tasks[port],
                (0, time_wf_end - self.start_time - len_wf),
                'constant'
            )
        if time_wf_start < self.start_time:
            self.offset_start_time(abs(time_wf_start - self.start_time))
            
            
    def align_digital_output(self, port, time_wf_start, time_wf_end):
        len_wf = len(self.digital_output_tasks[port])
        if time_wf_end - self.start_time > len_wf:
            self.digital_output_tasks[port] = np.pad(
                self.digital_output_tasks[port],
                (0, time_wf_end - self.start_time - len_wf),
                'constant'
            )
        if time_wf_start < self.start_time:
            self.offset_start_time(abs(time_wf_start - self.start_time))
        
    def pad_mul(self, mul=256):
        for port in self.analog_outputs:
            pad = mul - (len(self.analog_output_tasks[port]) % mul)
            self.analog_output_tasks[port] = np.pad(self.analog_output_tasks[port], (0, pad), 'constant')
        for port in self.digital_outputs:
            pad = mul - (len(self.digital_output_tasks[port]) % mul)
            self.digital_output_tasks[port] = np.pad(self.digital_output_tasks[port], (0, pad), 'constant')

    def align(self):
        len_max = self.len_max()
        for port in self.analog_outputs:
            len_wf = len(self.analog_output_tasks[port])
            self.analog_output_tasks[port] = np.pad(self.analog_output_tasks[port], (0, len_max - len_wf), 'constant')
        for port in self.digital_outputs:
            len_wf = len(self.digital_output_tasks[port])
            self.digital_output_tasks[port] = np.pad(self.digital_output_tasks[port], (0, len_max - len_wf), 'constant')

    def play_analog(self, port, waveform, time):
        if isinstance(waveform, tuple):
            time_wf_start = time + waveform[0]
            waveform = waveform[1]
        else:
            time_wf_start = time
        time_wf_end = time_wf_start + len(waveform)
        self.align_analog_output(port, time_wf_start, time_wf_end)
        time_wf_start -= self.start_time
        time_wf_end -= self.start_time
        self.analog_output_tasks[port][time_wf_start: time_wf_end] += waveform
        
    def play_digital(self, port, waveform, time):
        if isinstance(waveform, tuple):
            time_wf_start = time + waveform[0]
            waveform = waveform[1]
        else:
            time_wf_start = time
        time_wf_end = time_wf_start + len(waveform)
        self.align_digital_output(port, time_wf_start, time_wf_end)
        time_wf_start -= self.start_time
        time_wf_end -= self.start_time
        self.digital_output_tasks[port][time_wf_start: time_wf_end] |= waveform

    def play(self, waveforms, time):
        if 'analog' in waveforms:
            for port, waveform in waveforms['analog'].items():
                self.play_analog(port, waveform, time)
        if 'digital' in waveforms:
            for port, waveform in waveforms['digital'].items():
                self.play_digital(port, waveform, time)
                
    def display(self):
        print('analog_outputs:')
        for port, task in self.analog_output_tasks.items():
            print(f"{port}: (length = {len(task)}, data = {task})")
        print('digital_outputs:')
        for port, task in self.digital_output_tasks.items():
            print(f"{port}: (length = {len(task)}, data = {task})")

            
def awg_compiler(program, config, verbose=False):
    controllers = set()
    analog_outputs = set()
    digital_outputs = set()
    analog_inputs = set()
    elements = {}
    pulse_dict = {}
    waveforms = {}
    digital_waveforms = {}
    integration_weights = {}
    measurements = []
    variable_indices = {}
    
    def load_ports():
        for controller, params in config['controllers'].items():
            controllers.add(controller)
            if 'analog_outputs' in params:
                for port, port_params in params['analog_outputs'].items():
                    analog_outputs.add((controller, port))
            if 'digital_outputs' in params:
                for port in params['digital_outputs']:
                    digital_outputs.add((controller, port))
            if 'analog_inputs' in params:
                for port in params['analog_inputs']:
                    analog_inputs.add((controller, port))

    def load_elements():
        for element_name, element_data in config['elements'].items():
            elements[element_name] = Element(element_data)

    def load_pulse_dict():
        for pulse_name, pulse_data in config['pulses'].items():
            pulse_dict[pulse_name] = Pulse(pulse_data, waveforms, digital_waveforms, integration_weights)

    def load_waveforms():
        for waveform_name, waveform_dict in config['waveforms'].items():
            waveforms[waveform_name] = Waveform(waveform_dict)

    def load_digital_waveforms():
        for digital_waveform_name, digital_waveform_dict in config['digital_waveforms'].items():
            digital_waveforms[digital_waveform_name] = DigitalWaveform(digital_waveform_dict)
            
    def load_integration_weights():
        for integration_weight_name, integration_weight_dict in config['integration_weights'].items():
            integration_weights[integration_weight_name] = IntegrationWeight(integration_weight_dict)
            
    def elements_time_max(element_list):
        time_max = 0
        for element in element_list:
            if element.time > time_max:
                time_max = element.time
        return time_max
    
    def elements_set_time(element_list, time):
        for element in element_list:
            element.time = time
            
    def evaluate(expression):
        if expression is None:
            return None
        if expression.name == 'literal':
            return expression.value
        else:
            raise TypeError
            
    def evaluate_offsets(offsets):
        if offsets is None:
            return None
        if offsets.name == 'single':
            return evaluate(offsets.single)
        else:  # IQ
            return (evaluate(offsets.I), evaluate(offsets.Q))
                    
    def variable_to_stream(variable, stream_tag):
        
        demod_list.append((variables[variable][0], stream_tag, variables[variable][2]))
        variables[variable] = None
            
    def statement_replace(statement):
        if statement.name == 'align':
            statement.elements = [elements[element.name] for element in statement.elements]
            
        elif statement.name == 'wait':
            statement.duration = evaluate(statement.duration)
            statement.elements = [elements[element.name] for element in statement.elements]
            
        elif statement.name == 'frame_rotation':
            statement.angle = evaluate(statement.angle)
            statement.element = elements[statement.element.name]
            
        elif statement.name == 'update_frequency':
            statement.new_frequency = evaluate(statement.new_frequency)
            statement.element = elements[statement.element.name]
            statement.keep_phase = evaluate(statement.keep_phase)
            
        elif statement.name == 'play':
            statement.pulse = pulse_dict[statement.pulse.name]
            statement.element = elements[statement.element.name]
            statement.amp = evaluate(statement.amp)
            statement.offsets = evaluate_offsets(statement.offsets)
            statement.duration = evaluate(statement.duration)
            statement.truncate = evaluate(statement.truncate)
            
        elif statement.name == 'measure':
            statement.pulse = pulse_dict[statement.pulse.name]
            statement.element = elements[statement.element.name]
            statement.amp = evaluate(statement.amp)
            statement.offsets = evaluate_offsets(statement.offsets)
            
    def statement_handler(statement, task):
            if verbose:
                print("------------------------------------------------")
                # print(statement)
            task_end = False
            
            if statement.name == 'align':
                time_max = elements_time_max(statement.elements)
                elements_set_time(statement.elements, time_max)

            elif statement.name == 'wait':
                for element in statement.elements:
                    element.time += statement.duration
                    
            elif statement.name == 'frame_rotation':
                statement.element.frame_rotate(statement.angle)
                
            elif statement.name == 'update_frequency':
                statement.element.update_frequency(statement.new_frequency, statement.keep_phase)
                
            elif statement.name == 'play':
                pulse = statement.pulse
                amplitude = statement.amp
                offsets = statement.offsets
                element = statement.element
                duration = statement.duration
                truncate = statement.truncate
                
                element._digital_inputs_pad_clock(pulse)
                waveforms = element.generate(pulse, amplitude, offsets, duration, truncate)
                
                task.play(waveforms, element.time)
                if statement.truncate is not None:
                    length = truncate
                elif statement.duration is not None:
                    length = duration
                else:
                    length = pulse.length
                element.time += length
                
            elif statement.name == 'measure':
                pulse = statement.pulse
                amplitude = statement.amp
                offsets = statement.offsets
                element = statement.element
                
                element._digital_inputs_pad_clock(pulse)
                waveforms = element.generate(pulse, amplitude, offsets)
                
                measurement = {}
                for output in statement.outputs:
                    demod_I, demod_Q = element.generate_demod(pulse, output)
                    measurement.update({
                        output.I.name: demod_I,
                        output.Q.name: demod_Q
                    })
                    variable_indices[output.I.name] = len(measurements)
                    variable_indices[output.Q.name] = len(measurements)
                measurements.append(measurement)
                task.play(waveforms, element.time)
                element.time += pulse.length
                
            elif statement.name == 'save':
                measurements[variable_indices[statement.variable.name]][statement.variable.name][1].append(statement.stream.tag)
                
            elif statement.name == 'reset':
                for _, element in elements.items():
                    element.reset()
                task.align()
                task.pad_mul(256)
                task_end = True

#             else:
#                 raise Exception(f"Unknown statement {statement.name}")

            return task_end

    def sequence_formatter(tasks):
        seq_data = {
            controller: {
                'analog_outputs': {},
                'digital_outputs': {},
                'num_saves': 2 * len(tasks)
            } for controller in controllers
        }
        for controller, port in analog_outputs:
            seq_data[controller]['analog_outputs'][port] = []
        for controller, port in digital_outputs:
            seq_data[controller]['digital_outputs'][port] = []
        for task in tasks:
            for (controller, port), port_task in task.analog_output_tasks.items():
                seq_data[controller]['analog_outputs'][port].append(port_task)
            for (controller, port), port_task in task.digital_output_tasks.items():
                seq_data[controller]['digital_outputs'][port].append(port_task)
        return seq_data
    
    def demod_list_formatter(measurements):
        demod_list = []
        for measurement in measurements:
            saves = []
            save_raw = False
            raw_stream_I = 'unsaved_I'
            raw_stream_Q = 'unsaved_Q'
            raw_stream_length = 0
            for variable, demod in measurement.items():
                if demod[0] == 'IQ':
                    streams = demod[1]
                    if (len(streams) > 1) and (streams[0] == 'unsaved_I') or (streams[0] == 'unsaved_Q'):
                        for stream in streams[1:]:
                            saves.append(('IQ', [stream], demod[2]))
                elif demod[0] == 'raw_IQ':
                    save_raw = True
                    streams = demod[1]
                    if streams[0] == 'unsaved_I':
                        raw_stream_I = streams[-1]
                        raw_stream_length = demod[2]
                    elif streams[0] == 'unsaved_Q':
                        raw_stream_Q = streams[-1]
            if save_raw:
                saves.append(('raw_IQ', [raw_stream_I, raw_stream_Q], raw_stream_length))
            demod_list.append(saves)
        return demod_list
        
    
    load_ports()
    load_waveforms()
    load_digital_waveforms()
    load_integration_weights()
    load_pulse_dict()
    load_elements()
    
    task = None
    tasks = []
    last_task = False
    task_index = 1
    
    for statement in program.script.body:
        statement_replace(statement)
    
    for statement in program.script.body:
        if task is None:
            task = Task(analog_outputs, digital_outputs)
        task_end = statement_handler(statement, task)
        if task_end:
            if verbose:
                print(f"Task {task_index}")
                task.display()
            tasks.append(task)
            task = None
            task_index += 1
            
    if not task_end:
        task.align()
        task.pad_mul(256)
        if verbose:
            print(f"Task {task_index}")
            task.display()
        tasks.append(task)
        
    seq_data = sequence_formatter(tasks)
    seq_data[next(iter(controllers))]['demod_list'] = demod_list_formatter(measurements)
    return seq_data
