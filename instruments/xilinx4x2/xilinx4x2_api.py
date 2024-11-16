from queue import Queue
from . import tewx
import numpy as np

from qick import *

def qick_execute(program: RAveragerProgram, u_cfg):
    streams = Queue()

    program.acquire_decimated()
    
    return streams