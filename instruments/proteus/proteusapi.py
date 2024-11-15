import os
import sys
import clr
from System import Array, Byte
import numpy as np
import threading
import time


winpath = os.environ['WINDIR'] + "\\System32\\"
clr.AddReference(winpath + R'TEPAdmin.dll')
from TaborElec.Proteus.CLI.Admin import CProteusAdmin
from TaborElec.Proteus.CLI.Admin import IProteusInstrument
from TaborElec.Proteus.CLI.Admin import TaskInfo
from TaborElec.Proteus.CLI import TaskStateType, IdleWaveform
from TaborElec.Proteus.CLI import EnableSignalType, AbortSignalType
from TaborElec.Proteus.CLI import ReactMode, TaskCondJump


maxScpiResponse = 65535
amp_range = [0.05, 1.3]
coarse_offset_range = [-0.5, 0.5]


class Proteus:
    def __init__(self):
        self.slotIds = [3, 5]
        self.insts = {}
        self.admin = None
        self.error = ''
        
        self.coarse_offsets = [0.0] * 8
        self.fine_offsets = [0.0] * 8
        self.amps = [1.3] * 8
        
        self.admin = CProteusAdmin()
        self.admin.Open()
        
        self.insts = {(i + 1): self.proteus_init(self.slotIds[i]) for i in range(len(self.slotIds))}
        
    def status(self):
        return f"{{insts[1]: {self.insts[1]}, insts[2]: {self.insts[2]}, error: {self.error}}}"
        
    def proteus_init(self, slotId):
        return self.admin.OpenInstrument(slotId)
            
    def proteus_close(self, slotId, close_admin=True):
        self.admin.CloseInstrument(slotId)
        if close_admin:
            self.admin.Close()
            
    def close(self):
        self.proteus_close(self.slotIds[0], close_admin=False)
        self.proteus_close(self.slotIds[1], close_admin=True)

    def handler(self, args):
        if args['command'] == 'send_scpi':
            inst = self.insts[int(args['inst'])]
            scpi_command = args['scpi_command']
            res = inst.SendScpi(scpi_command)
            return f"{{ErrCode: {res.ErrCode}, RespStr: {res.RespStr}}}"
            
        if args['command'] == 'load_sequence':
            seq_data = args['seq_data']
            seq_data_1 = {
                'analog': {
                    channel: seq_data['analog'][channel] for channel in range(1, 5)
                },
                'digital': {
                    channel: seq_data['digital'][channel] for channel in range(1, 5)
                },
            }
            seq_data_2 = {
                'analog': {
                    channel: seq_data['analog'][channel + 4] for channel in range(1, 5)
                },
                'digital': {
                    channel: seq_data['digital'][channel + 4] for channel in range(1, 5)
                },
            }
            load_sequence(self.insts[1], seq_data_1, num_offset=0, amps=self.amps[:4], coarse_offsets=self.coarse_offsets[:4], fine_offsets=self.fine_offsets[:4])
            load_sequence(self.insts[2], seq_data_2, num_offset=0, amps=self.amps[4:], coarse_offsets=self.coarse_offsets[4:], fine_offsets=self.fine_offsets[4:])
            # load_sequence_4ch(self.insts[1], seq_data_1)
            # load_sequence_4ch(self.insts[2], seq_data_2)
            return 'done'
        
        elif args['command'] == 'start_from':
            step_index = args['step_index']
            rep1 = start_from(self.insts[1], step_index)
            rep2 = start_from(self.insts[2], step_index)
            return str(rep1) + str(rep2)
        
        elif args['command'] == 'set_amplitudes':
            amps = args['amps']
            
            for i in range(8):
                if amps[i] < amp_range[0]:
                    amps[i] = amp_range[0]
                elif amps[i] > amp_range[1]:
                    amps[i] = amp_range[1]
                    
            self.amps = amps
            rep1 = set_amplitudes(self.insts[1], amps[:4])
            rep2 = set_amplitudes(self.insts[2], amps[4:])
            return f'{{{rep1}, {rep2}}}'
        
        elif args['command'] == 'set_coarse_offsets':
            offsets = args['offsets']
            
            for i in range(8):
                if offsets[i] < coarse_offset_range[0]:
                    offsets[i] = coarse_offset_range[0]
                elif offsets[i] > coarse_offset_range[1]:
                    offsets[i] = coarse_offset_range[1]
            
            self.coarse_offsets = offsets
            rep1 = set_coarse_offsets(self.insts[1], offsets[:4])
            rep2 = set_coarse_offsets(self.insts[2], offsets[4:])
            return f'{{{rep1}, {rep2}}}'
        
        elif args['command'] == 'set_fine_offsets':
            offsets = args['offsets']
            
            for i in range(8):
                if offsets[i] > self.amps[i] / 2:
                    offsets[i] = self.amps[i] / 2
            
            self.fine_offsets = offsets
            rep1 = set_fine_offsets(self.insts[1], offsets[:4], self.amps[:4])
            rep2 = set_fine_offsets(self.insts[2], offsets[4:], self.amps[4:])
            return f'{{{rep1}, {rep2}}}'
            
        else:
            return 'Unknown proteus command.'
#        return str(type(data))


def loadSegmentData(inst, segNum, segData, query_err=False, verbose=True):
    seg_len = int(len(segData) / 2)
    inst.SendScpi(f":TRACe:DEF {segNum},{seg_len}")
    inst.SendScpi(f":TRACe:SEL {segNum}")
    inDatLength = len(segData)
    inDatOffset = 0
    if isinstance(segData, np.ndarray):
        segData = segData.tolist()
    segData = bytearray(segData)
    res = inst.WriteBinaryData(":TRAC:DATA 0,#", segData, inDatLength, inDatOffset)

    if (res.ErrCode != 0):
        print("Error {0} ".format(res.ErrCode))

    if len(res.RespStr) > 0:
        print("{0}".format(res.RespStr))

    if query_err:
        err = inst.SendScpi(':SYST:ERR?')
        if not err.RespStr.startswith('0'):
            print(err.RespStr)
            err = inst.SendScpi('*CLS')


def loadMarkData(inst, markData, query_err=False):
    inDatLength = len(markData)
    inDatOffset = 0
    if isinstance(markData, np.ndarray):
        markData = markData.tolist()
    markData = bytearray(markData)
    res = inst.WriteBinaryData(":MARK:DATA 0,#", markData, inDatLength, inDatOffset)

    if (res.ErrCode != 0):
        print("Error {0} ".format(res.ErrCode))

    if len(res.RespStr) > 0:
        print("{0}".format(res.RespStr))

    if query_err:
        err = inst.SendScpi(':SYST:ERR?')
        if not err.RespStr.startswith('0'):
            print(err.RespStr)
            err = inst.SendScpi('*CLS')


def loadTaskTable(inst, num_steps, DcVals=[32768, 32768, 32768, 32768], dummy_header=True, query_err=False, verbose=True):
    
    segNum_offset = 256
    
    dummy_offset = 0
    if dummy_header:
        dummy_offset = 1
    
    for ch_index in range(4):
        inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        
        taskTableLen = num_steps + dummy_offset
        taskTableRow = TaskInfo()
        rowBinarySize = taskTableRow.SerializedSize
        #tableBinDat = np.zeros(taskTableLen * rowBinarySize, dtype=np.uint8)
        tableBinDat = bytearray(taskTableLen * rowBinarySize)
        tableBinDat = Array[Byte](tableBinDat)

        if (ch_index % 2 == 0):
            step_index_start = 1 + segNum_offset
        else:
            step_index_start = num_steps + 1 + segNum_offset
        
        if dummy_header:
            taskTableRow.SegNb = 1
            taskTableRow.TaskState = TaskStateType.Single
            taskTableRow.TaskLoopCount = 1
            taskTableRow.SeqLoopCount = 1
            taskTableRow.TaskIdleWaveform = IdleWaveform.DC
            # taskTableRow.TaskDcVal = DcVals[ch_index]
            taskTableRow.TaskDcVal = DcVals[ch_index]
            taskTableRow.TaskEnableSignal = EnableSignalType(0)
            taskTableRow.TaskAbortSignal = AbortSignalType(0)
            taskTableRow.TaskAbortJump = ReactMode.Eventually
            taskTableRow.TaskCondJumpDest = TaskCondJump.Next1Task
            taskTableRow.NextTask1 = 1
            taskTableRow.NextTask2 = 1
            taskTableRow.NextTaskDelay = 0
            taskTableRow.TaskLoopTrigEnable = False
            taskTableRow.Serialize(tableBinDat, 0)
        
        for step_index in range(num_steps):
            taskTableRow.SegNb = step_index + step_index_start + dummy_offset
            #
            #% TaskState is either
            #%  TaskStateType.Single, 
            #%  TaskStateType.StartSequence,
            #%  TaskStateType.EndSequence or
            #%  TaskStateType.InsideSequence
            taskTableRow.TaskState = TaskStateType.Single
            #
            taskTableRow.TaskLoopCount = 1
            taskTableRow.SeqLoopCount = 1
            #
            #% TaskIdleWaveform is either
            #%  IdleWaveform.DC,
            #%  IdleWaveform.FirstPoint or
            #%  IdleWaveform.CurrentSeg
            taskTableRow.TaskIdleWaveform = IdleWaveform.DC
            #
            taskTableRow.TaskDcVal = DcVals[ch_index]
            #
            #% TaskEnableSignal is (currently) either
            #%   EnableSignalType.None,
            #%   EnableSignalType.ExternTrig1,
            #%   EnableSignalType.ExternTrig2,
            #%   EnableSignalType.InternTrig,
            #%   EnableSignalType.CPU,
            #%   EnableSignalType.FeedbackTrig or
            #%   EnableSignalType.HwControl
            taskTableRow.TaskEnableSignal = EnableSignalType.ExternTrig1
                
            #
            #% TaskAbortSignal is (currently) either
            #%   AbortSignalType.None,
            #%   AbortSignalType.ExternTrig1,
            #%   AbortSignalType.ExternTrig2,
            #%   AbortSignalType.InternTrig,
            #%   AbortSignalType.CPU,
            #%   AbortSignalType.FeedbackTrig or
            #%   AbortSignalType.AnyExternTrig
            taskTableRow.TaskAbortSignal = AbortSignalType(0)
            #
            #% TaskAbortJump is either
            #%   ReactMode.Eventually or
            #%   ReactMode.Immediately
            taskTableRow.TaskAbortJump = ReactMode.Eventually
            #
            #% TaskCondJumpDest is either
            #%   TaskCondJump.Next1Task
            #%   TaskCondJump.FeedbackTrigValue
            #%   TaskCondJump.SwitchNext1Next2
            #%   TaskCondJump.NextTaskSel
            #%   TaskCondJump.NextScenario
            taskTableRow.TaskCondJumpDest = TaskCondJump.Next1Task
                
            taskTableRow.NextTask1 = (step_index + 1) % num_steps + 1 + dummy_offset
#                taskTableRow.NextTask1 = (step_index)%num_steps + 1
            taskTableRow.NextTask2 = (step_index + 1) % num_steps + 1 + dummy_offset
            #
            # These two lines seem to be extra.
            taskTableRow.NextTaskDelay = 0
            taskTableRow.TaskLoopTrigEnable = False #(this does not matter for single loop tasks)
            #
            ##% The offset of the n-th row is: (n-1)*rowBinarySize
            taskTableRow.Serialize(tableBinDat, (step_index + dummy_offset) * rowBinarySize)
        res = inst.WriteBinaryData(':TASK:DATA 0,#', tableBinDat)
    
    if (res.ErrCode != 0):
        print("Error {0} ".format(res.ErrCode))

    if len(res.RespStr) > 0:
        print("{0}".format(res.RespStr))

    if query_err:
        err = inst.SendScpi(':SYST:ERR?')
        if not err.RespStr.startswith('0'):
            print(err.RespStr)
            err = inst.SendScpi('*CLS')
            

def load_sequence(inst, seq_data, num_offset=0, amps=[1.3, 1.3, 1.3, 1.3], coarse_offsets=[0.0, 0.0, 0.0, 0.0], fine_offsets=[0.0, 0.0, 0.0, 0.0],\
                      dummy_header=True, master=False, slave=False, verbose=False):
    sclk = 1e9 #1.25e9 
    num_steps = len(seq_data['analog'][1])
    segNum_offset = 256
    query_syst_err = True
     
    dummy_offset = 0
    if dummy_header:
        dummy_offset = 1
     
    bin_queue = []
    np.set_printoptions(threshold=np.inf)
    
    def generate_bin():
        for ch_index in range(4):
            for step_index in range(num_steps):
                analog_data = (np.array(seq_data['analog'][ch_index + 1][step_index], dtype=np.float64) + fine_offsets[ch_index]) / (amps[ch_index] / 2)
                digital_data = np.array(seq_data['digital'][ch_index + 1][step_index], dtype=bool)
                 
                seg_data = (analog_data + 1) * 2**15
                #                        seg_data = np.array([ round(2**15 *val + 2**15) for val in channel[step_index]])
                seg_data = seg_data.clip(0, 2**16 - 1)
                #                        seg_data[seg_data < 0] = 0
                #                        seg_data[seg_data > 2**16 - 1] = 2**16 - 1
                
                seg_data = np.uint16(seg_data)
               
                #                        seg_data = np.array([ round(2**15 *val + 2**15) for val in channel[step_index] ])
                #                        seg_data = seg_data.clip(0, 2**16-1)
                #                        seg_data = seg_data.astype('uint16')
               
                # padding
                #                binary_data = np.hstack((np.ones(12, dtype=np.uint16)*2**15, binary_data))
                #                binary_data = np.hstack((binary_data, np.ones(500, dtype=np.uint16)*2**15))
               
                mark_mask = digital_data[::2]
                mark_mask = np.logical_or(mark_mask, digital_data[1::2])
                mark_data = np.zeros(int(len(mark_mask) / 2), dtype=np.uint8)
                mark_data[mark_mask[::2]] += 2**0
                mark_data[mark_mask[1::2]] += 2**4
                
#                mark_data = np.full(3008, 0xff, dtype=np.uint8)
               
                # the 2nd marker (not for our devices)
                #                mark_mask = mark2[step_index][::2]
                #                mark_mask = np.logical_or(mark_mask, mark2[step_index][1::2])
                #                mark_data[mark_mask[::2]] += 2**1
                #                mark_data[mark_mask[1::2]] += 2**5
               
                mark_data = mark_data.astype('uint8')
                bin_queue.append((seg_data,mark_data))
   
    thread = threading.Thread(target=generate_bin)
    thread.start()
    # generate_bin()
   
    for ch_index in range(4):
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        # disable ouput
        res = inst.SendScpi(":OUTP OFF")
        # disable markers
        res = inst.SendScpi(":MARK:SEL 1")
        res = inst.SendScpi(":MARK:STAT OFF")
        res = inst.SendScpi(":MARK:SEL 2")
        res = inst.SendScpi(":MARK:STAT OFF")
            
    res = inst.SendScpi("*CLS")
    res = inst.SendScpi("*RST")
     
    for ch_index in range(4):
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        # set sampling DAC freq.
        res = inst.SendScpi(f":FREQ:RAST {sclk}")
        # delete all segments in RAM
        res = inst.SendScpi(":TRAC:DEL:ALL")
        # enable Arb mode
        res = inst.SendScpi(":SOUR:FUNC:MODE ARB")
        # common segment defs
        # inst.SendScpi(":TRAC:DEF:TYPE NORM")
        res = inst.SendScpi(":TRIG:STAT OFF")
    
    for ch_index in range(4):
        if(ch_index % 2 == 0):
            step_index_start = 1 + segNum_offset
            res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        
            if dummy_header:
                loadSegmentData(inst, 1, np.full(64, 32768, dtype=np.uint16).view(np.uint8), query_syst_err, verbose=verbose)

        else:
            step_index_start = num_steps + 1 + segNum_offset
  
        for step_index in range(num_steps):
            while not bin_queue:
                time.sleep(0.5)
            seg_data, mark_data = bin_queue.pop(0)
            loadSegmentData(inst, step_index_start + step_index + dummy_offset, seg_data.view(np.uint8), query_syst_err, verbose=verbose)
            loadMarkData(inst, mark_data, query_syst_err)

    DcVals = np.around(np.array(fine_offsets, dtype=np.float64) / amps * 65536).astype(int) + 32768
    DcVals = DcVals.clip(0, 65535).tolist()
    loadTaskTable(inst, num_steps, DcVals, dummy_header, query_syst_err, verbose=verbose)
    
    for ch_index in range(4):
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        res = inst.SendScpi(":TRIG:SOUR:ENAB TRG1")
        res = inst.SendScpi(":TRIG:SEL TRG1")
        res = inst.SendScpi(":TRIG:LEV 0.6")
        res = inst.SendScpi(":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
        res = inst.SendScpi(":TRIG:IDLE:LEV 0") # Set DC level in DAC value (CH specific)
        res = inst.SendScpi(":TRIG:STAT ON") # Enable trigger state (CH specific)
        res = inst.SendScpi(":INIT:CONT OFF") # Enable trigger mode (CH specific)
  
        # Setting up amplitudes and offsets
        res = inst.SendScpi(f":VOLT {amps[ch_index]}")
        res = inst.SendScpi(f":VOLT:OFFS {coarse_offsets[ch_index]}")
        res = inst.SendScpi(":SOUR:FUNC:MODE TASK")
      
        # enable ouput
        res = inst.SendScpi(":OUTP ON")
        # enable markers
        res = inst.SendScpi(":MARK:SEL 1")
        res = inst.SendScpi(":MARK:VOLT:PTOP 1.2")
        res = inst.SendScpi(":MARK:VOLT:OFFS 0.0")
        res = inst.SendScpi(":MARK:STAT ON")

        # # the 2nd marker (not for our devices)
        # inst.SendScpi(":MARK:SEL 2")
        # inst.SendScpi(":MARK:VOLT:PTOP 1.2")
        # inst.SendScpi(":MARK:VOLT:OFFS 0.0")
        # inst.SendScpi(":MARK:STAT ON")
        
        res = inst.SendScpi(":TASK:SEL 1")
        # start from the first task
        res = inst.SendScpi(":TASK:DEF:NEXT1 2")
     
    # if master:
    #     inst.SendScpi(":XINS:MODE MAST")
    #     inst.SendScpi(":XINS:SYNC:TYPE BOTH")
    #     inst.SendScpi(":XINS:SYNC:STAT 0")
     
    # if slave:
    #     inst.SendScpi(":XINS:MODE SLAV")
    #     inst.SendScpi(":XINS:SYNC:TYPE BOTH")
    #     inst.SendScpi(":XINS:SYNC:STAT 1")
    

def start_from(inst, step_index=0):
    for ch_index in range(4):
        res = inst.SendScpi(":INST:CHAN {}".format(ch_index + 1))
        res = inst.SendScpi(":TASK:SEL 1")
        res = inst.SendScpi(f":TASK:DEF:NEXT1 {2 + step_index}")
    return f"{{ErrCode: {res.ErrCode}, RespStr: {res.RespStr}}}"


def set_amplitudes(inst, amps=[1.3, 1.3, 1.3, 1.3]):
    for ch_index in range(4):
        if amps[ch_index] is None:
            continue
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        res = inst.SendScpi(f":VOLT {amps[ch_index]}")
    return f"{{ErrCode: {res.ErrCode}, RespStr: {res.RespStr}}}"

    
def set_coarse_offsets(inst, offsets=[0.0, 0.0, 0.0, 0.0]):
    for ch_index in range(4):
        if offsets[ch_index] is None:
            continue
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        res = inst.SendScpi(f":VOLT:OFFS {offsets[ch_index]}")
    return f"{{ErrCode: {res.ErrCode}, RespStr: {res.RespStr}}}"


def set_fine_offsets(inst, offsets=[0.0, 0.0, 0.0, 0.0], amps=[1.3, 1.3, 1.3, 1.3]):
    for ch_index in range(4):
        if offsets[ch_index] is None:
            continue
        DcVal = np.int64(np.around(offsets[ch_index] / amps[ch_index] * 65536)) + 32768
        DcVal = np.clip(DcVal, 0, 65535)
        res = inst.SendScpi(f":INST:CHAN {ch_index + 1}")
        res = inst.SendScpi(":TASK:SEL 1")
        res = inst.SendScpi(f":TASK:DEF:NEXT1 2")
        res = inst.SendScpi(":TASK:SEL 2")
        res = inst.SendScpi(f':TASK:DEF:IDLE:DC {DcVal}')
    return f"{{ErrCode: {res.ErrCode}, RespStr: {res.RespStr}}}"
