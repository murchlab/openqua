from queue import Queue

from qick import *

from openqua.compilers import QickStream

def qick_execute(program: RAveragerProgram, ro_cfg: dict[str, dict[str, QickStream]], u_cfg):
    iq_list = program.acquire_decimated()

    # TODO: adjust this representation as needed
    return (iq_list, ro_cfg["streams"])