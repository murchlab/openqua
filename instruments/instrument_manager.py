from . import awg
from . import daq
from . import delay
from . import controller

instrument_dict = {
    # 'proteus8ch': awg.Proteus8CH,
    # 'wx2184c': awg.WX2184C,
    'dummy8ch': awg.Dummy8CH,
    # 'dg535': delay.DG535,
    # 'agilent_33220a': delay.Agilent_33220A,
    # 'ats9870': daq.ATS9870,
    'dummydaq': daq.DummyDaq,
    'dummycontroller': controller.DummyController,
    # 'redfridgecontroller': controller.RedFridgeController,
    # 'nonhermitian_controller': controller.NonHermitianController
}


def load(instr_type, name=None, address=None, options=None):
    driver = instrument_dict[instr_type](name=name, address=address, options=options)
    return driver
