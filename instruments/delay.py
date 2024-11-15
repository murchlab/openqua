from .instrument import Instrument
# from . import dg535, agilent_33220a

class Delay(Instrument):
    def __init__(self, instru_type='delay', name=None, address=None, options=None):
        super().__init__(instru_type, name, address, options)
        
    def set_rep_rate(self, rate_Hz):
        pass
    
    def set_state(self, on_flag):
        pass
        
        
class DummyDelay(Delay):
    pass


# class DG535(Delay):
#     def __init__(self, name=None, address=None, options=None):
#         super().__init__('dg535', name, address, options)
        
#     def initialize(self):
#         dg535.initialize_dg535(self.address)
        
#     def set_rep_rate(self, rate_Hz):
#         dg535.set_rep_rate(self.address, rate_Hz)
    
#     def set_state(self, on_flag):
#         dg535.set_state(self.address, on_flag)


# class Agilent_33220A(Delay):
#     def __init__(self, name=None, address=None, options=None):
#         super().__init__('agilent_33220a', name, address, options)
        
#     def initialize(self):
#         agilent_33220a.initialize_agilent(self.address)
        
#     def set_rep_rate(self, rate_Hz):
#         agilent_33220a.set_rep_rate(self.address, rate_Hz)
    
#     def set_state(self, on_flag):
#         agilent_33220a.set_state(self.address, on_flag)
