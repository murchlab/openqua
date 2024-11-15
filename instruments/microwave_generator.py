from .instrument import Instrument
from . import dg535

class MicrowaveGenerator(Instrument):
    def __init__(self, instru_type='microwave_generator', name=None, address=None):
        super().__init__(instru_type, name, address)
        
    def get_frequency(self):
        pass
        
    def set_frequency(self, frequency):
        pass
    
    def get_power(self):
        pass
        
    def set_power(self, frequency):
        pass
        
        
class DummyDelay(Delay):
    pass


class DG535(Delay):
    def __init__(self, name=None, address=None):
        super().__init__('dg535', name, address)
        
    def initialize(self):
        dg535.initialize_dg535(self.address)
        
    def set_rep_rate(self, rate_Hz):
        dg535.set_rep_rate(self.address, rate_Hz)
    
    def set_state(self, on_flag):
        dg535.set_state(self.address, on_flag)
