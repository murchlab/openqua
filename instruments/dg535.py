# -*- coding: utf-8 -*-
"""
Created on Fri Jul  3 14:04:16 2020

@author: J. Monroe
"""
import numpy as np
import pyvisa
# manual: https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf

## constants
# see table in manual p13, RHS column.
# 0 corresponds to trigger input
T0 = 1
A  = 2
B  = 3
AB = 4 # also !AB ??
# !AB = 4
C  = 5
D  = 6
CD = 7

## calibrate the signal power from I/Q voltage:
cavity_on_amp_V = 0.3
qubit_on_amp_V = 0.5

dg535_address = 'GPIB0::15::INSTR'


def initialize_dg535(dg535_address):
    rm = pyvisa.ResourceManager()
    dg_handle = rm.open_resource( dg535_address )
    
    dg_handle.write("CL")

    ## trigger one at a time.
    dg_handle.write("TM 0") # trigger mode to internal (0)
    dg_handle.write("TR 0, 2e3") # 10 kHz trigger rate
    
    ## prep all outputs for variable signaling
    #  allows variable amplitudes.
    dg_handle.write(f"OM {T0}, 3")
    dg_handle.write(f"OM {A}, 3") # 3 is VARiable mode
    dg_handle.write(f"OM {B}, 3")
    dg_handle.write(f"OM {AB}, 3")
    dg_handle.write(f"OM {C}, 3")
    dg_handle.write(f"OM {D}, 3") 
    dg_handle.write(f"OM {CD}, 3") 
    
    ## set channel impedences to 50 Ohms
    dg_handle.write(f"TZ {A}, 0")
    dg_handle.write(f"TZ {B}, 0")
    dg_handle.write(f"TZ {AB}, 0") # 0 is 50 Ohms, 1 is 'high Z'.
    dg_handle.write(f"TZ {C}, 0")
    dg_handle.write(f"TZ {D}, 0")
    dg_handle.write(f"TZ {CD}, 0")
    dg_handle.write(f"TZ {T0}, 0")
#    
#    ## turn output off while setting commands
    dg_handle.write(f"TM 1")
    dg_handle.write(f"OA {T0}, 4")
    dg_handle.write(f"OO {T0}, -2")

    dg_handle.write(f"OA {A}, 4")
    dg_handle.write(f"OO {A}, -2")

    dg_handle.write(f"OA {B}, 4")
    dg_handle.write(f"OO {B}, -2")
    
    # following commands are for using AB as trigger port (via Proteus AWG)
    dg_handle.write(f"OA {AB}, 4")
    dg_handle.write(f"OO {AB}, -2")
#         dg_handle.write(f"DT {B}, {A}, 3E-6")
    dg_handle.write(f"DT {A},{T0}, 0")
    dg_handle.write(f"DT {B}, {A}, 10E-9")
    
    dg_handle.write(f"OA {CD}, 4")
    dg_handle.write(f"OO {CD}, -2")
#         dg_handle.write(f"DT {B}, {A}, 3E-6")
    dg_handle.write(f"DT {D}, {C}, 10E-9")
    
    ## channel offsets
    # ensure these are set to zero (offset is tuned with DC supply)
    dg_handle.write(f"OO {CD}, 0") # cavity
    dg_handle.write(f"OO {AB}, 0") # qubit
    
    ## set delays
    # apparently, if any channel has not been given a delay then the joint
    #   channels (eg CD) won't generate pulses. (Have not checked directly.)
    # dg_handle.write(f"DT {A},{T0}, 0")
    # dg_handle.write(f"DT {B},{A}, 0") # no idea why this must be set for CD to pulse
    dg_handle.write(f"DT {C},{T0}, 0")
    # dg_handle.write(f"DT {D},{C}, 0")
    
    output = dg_handle.query("ES")
    dg_handle.close()
    
    return output
##END initialize_dg535
    

def set_rep_rate(dg535_address, rate_Hz):
    rm = pyvisa.ResourceManager()
    dg_handle = rm.open_resource(dg535_address)
    dg_handle.write(f"TR 0, {rate_Hz}") 
    
    output = dg_handle.query("ES")
    dg_handle.close()
    return output
##END set_clock_rate


def set_state(dg535_address, on_flag):
    rm = pyvisa.ResourceManager()
    dg_handle = rm.open_resource(dg535_address)
    
    if on_flag:
         dg_handle.write(f"TM 0")
        
        # testing on 20/07/25 showed the alazar triggered on the rising edge
        # with the preceeding settings. Otherwise, triggering doesn't occur (timeout)
        # or the falling edge of the previous T0 triggers the card.
    else:
        dg_handle.write(f"TM 1")
        
    ## check for errors
    output = dg_handle.query("ES")
    dg_handle.close()
    return output
##END start_dg535

#
#def always_on_seq(flag_qubit=1):
#    rm = pyvisa.ResourceManager()
#    dg_handle = rm.open_resource(dg535_address )
#    
##    seq_len_s = 100E-6 # 10 kHz rep rate --> 100 us.
#    
#    ## amplitudes
#    # NOTE: 0.1 is minimum value; returns error "4" =0B0100 = bit 2 = value outside range
#    # NOTE: 0.01 is increment.
#    '''
#    cavity_amp_V = amp_V
#    qubit_amp_V = amp_V
#    '''
#    if flag_qubit:
#        cavity_amp_V = cavity_on_amp_V # units: volts
#        qubit_amp_V  = qubit_on_amp_V # units: volts
#        print(f"cavity on {cavity_amp_V}, qubit on {qubit_amp_V}")
#    else:
#        cavity_amp_V = 0.1
#        qubit_amp_V = 0.1
#        print("all off")
#
#    ## cavity on
##    dg_handle.write(f"DT {C}, {T0}, {0.0}E-6")
##    dg_handle.write(f"DT {D}, {C}, {seq_len_s-1E-6}") 
##    dg_handle.write(f"OA {CD}, {cavity_amp_V}") 
#    dg_handle.write(f"DT {C}, {T0}, 0")
#    dg_handle.write(f"DT {D}, {T0}, 0") 
#    dg_handle.write(f"OA {CD}, 0.1") 
#    dg_handle.write(f"OO {CD}, {cavity_amp_V}")
#    #dg_handle.write(f"DT {B}, {A}, 9.7E-5")
#
#    ## qubit pulse
##    dg_handle.write(f"DT {A}, {T0}, {0}")
##    dg_handle.write(f"DT {B}, {A}, {seq_len_s-1E-6}")
##    dg_handle.write(f"OA {AB}, {qubit_amp_V}")
#    dg_handle.write(f"DT {A}, {T0}, 0")
#    dg_handle.write(f"DT {B}, {T0}, 0") 
#    dg_handle.write(f"OA {AB}, 0.1") 
#    dg_handle.write(f"OO {AB}, {qubit_amp_V}")
#    ## check for errors
#    output =  dg_handle.query("ES")
#    dg_handle.close()
#    
#    return output
###END always_on
#
#    
#def single_pulse(flag_qubit_on=0,verbose=True,cavity_amp_V=cavity_on_amp_V):
#    
#    ## setup VISA session
#    rm = pyvisa.ResourceManager()
#    dg_handle = rm.open_resource('GPIB0::15::INSTR' )
#    
#    ## amplitudes
#    # NOTE: 0.1 is minimum value; returns error "4" =0B0100 = bit 2 = value outside range
#    # NOTE: 0.01 is increment.
#    if flag_qubit_on:
#        #cavity_amp_V = cavity_on_amp_V # units: volts
#        qubit_amp_V  = qubit_on_amp_V # units: volts
#        if verbose: print(f"qubit on {qubit_amp_V}V , cavity pulse {cavity_amp_V} V")
#    else:
#        qubit_amp_V = 0.1
#        if verbose: print(f"qubit off, cavity pulse {cavity_amp_V} V")
#
#    ## cavity pulse
#    start_us = 2
#    dur_us = 3
#    if verbose: print( f"Pulse starts, dur: {start_us}, {dur_us} us")
#    dg_handle.write(f"DT {C}, {T0}, {start_us*1E-6}")
#    dg_handle.write(f"DT {D}, {C}, {dur_us*1E-6}") 
#    dg_handle.write(f"OA {CD}, {cavity_amp_V}") 
#    dg_handle.write(f"OO {CD}, 0") # reset offset (set by always_on())
#
#    ## qubit pulse
#    dg_handle.write(f"DT {A}, {T0}, {0.01*1E-6}")
#    dg_handle.write(f"DT {B}, {A}, {97E-6}")
#    dg_handle.write(f"OA {AB}, {qubit_amp_V}")
#    dg_handle.write(f"OO {AB}, 0") # reset offset (set by always_on())
#    
#    ## check for errors
#    output =  dg_handle.query("ES")
#    dg_handle.close()
#    
#    return output
###END single_pulse
#
#
#def rabi_seq(step_num, total_steps=51, cavity_amp_V=cavity_on_amp_V):
#    rm = pyvisa.ResourceManager()
#    dg_handle = rm.open_resource('GPIB0::15::INSTR' )
#    
#    rabi_time_us = 0.200 
#    buffer_time_us = 10E-3 #delay between rabi end and readout start
#    
#    ## cavity pulse
#    cavity_pulse_dur_us = 4
#    cavity_pulse_start_us = 2
#    dg_handle.write(f"DT {C}, {T0}, {cavity_pulse_start_us*1E-6}")
#    dg_handle.write(f"DT {D}, {C}, {cavity_pulse_dur_us*1E-6}")
#    dg_handle.write(f"OA {CD}, {cavity_amp_V}") 
#    dg_handle.write(f"OO {CD}, 0") # reset offset (set by always_on())
#    
#    ## qubit pulse
#    qubit_amp = qubit_on_amp_V
#    pulse_length_us = np.round( step_num/total_steps* rabi_time_us, 3)
#    pulse_start_us = cavity_pulse_start_us - pulse_length_us  - buffer_time_us
#    dg_handle.write(f"DT {A}, {T0}, {pulse_start_us}E-6")  # T0 to A delay is 1 us.
#    dg_handle.write(f"DT {B}, {A}, {pulse_length_us}E-6" ) # A to B delay is step's rabi length
#    dg_handle.write(f"OA {AB}, {qubit_amp}")
#    dg_handle.write(f"OO {AB}, 0") # reset offset (set by always_on())
#    
#    ## beginnning of seqeunce: turn from -0.1 V to +1V.
#    ## enable output on A, B
#    
#    ## check for errors
#    output =  dg_handle.query("ES")
#    dg_handle.close()
#    
#    return output
###END rabi_seq