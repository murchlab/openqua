# -*- coding: utf-8 -*-
"""
Created on Fri Jul 7 16:58:00 2023

@author: Xingrui Song
"""
import numpy as np
import pyvisa

agilent_address = 'GPIB0::10::INSTR'


def initialize_agilent(agilent_address):
    rm = pyvisa.ResourceManager()
    agilent_handle = rm.open_resource(agilent_address)
    
    agilent_handle.write("*RST")
    agilent_handle.write("OUTP OFF")
    agilent_handle.write("FUNC PULS")

    ## set voltages
    agilent_handle.write("VOLT 2")
    agilent_handle.write("VOLT:OFFS 0.7")

    ## set pulse paramters
    agilent_handle.write("FUNC:PULS:WIDT 2E-8")
    
    ## check for errors
    output = agilent_handle.query("SYST:ERR?")
    agilent_handle.close()
    return output
##END initialize_agilent
    

def set_rep_rate(agilent_address, rate_Hz):
    rm = pyvisa.ResourceManager()
    agilent_handle = rm.open_resource(agilent_address)
    agilent_handle.write(f"FREQ {rate_Hz}")
    
    ## check for errors
    output = agilent_handle.query("SYST:ERR?")
    agilent_handle.close()
    return output
##END set_clock_rate


def set_state(agilent_address, on_flag):
    rm = pyvisa.ResourceManager()
    agilent_handle = rm.open_resource(agilent_address)
    
    if on_flag:
         agilent_handle.write(f"OUTP ON")
        
    else:
        agilent_handle.write(f"OUTP OFF")
        
    ## check for errors
    output = agilent_handle.query("SYST:ERR?")
    agilent_handle.close()
    return output
##END set_state
