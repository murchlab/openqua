class Instrument:
    def __init__(self, instr_type=None, name=None, address=None, options=None):
        self.instr_type = instr_type
        self.name = name
        self.address = address
        self.options = options
        
    def __repr__(self):
        return f'instr_type = {self.instr_type}, name = {self.name}, address = {self.address}'
    
    def initialize(self):
        pass
