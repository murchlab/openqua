import instruments
from .compilers import awg_compiler
import numpy as np
import time
from threading import Thread


progress_interval = 0.1  # seconds
progress_timeout = 20  # seconds

# 
# Managing job compilation, execution, status & progress
# 
class Manager:
    def __init__(self, config):
        self.config = config
        self.controllers = {
            controller: instruments.load(controller_data['type'], controller)
            for controller, controller_data in config['controllers'].items()
        }

    # Job execution
    # Parameters:
    #    program: defined in ast format
    #    num_avg: number of experiments to perform average
    #    verbose: debug flag
    #    display: whether to display the graphics from the simulator
    #    jobqueue: (optional) reuse an existing jobqueue
    # Returns: data streams from the DAQ
    def execute(self, program, num_avg=20, verbose=False, display=False, jobqueue=None):
        controller_seq_data = awg_compiler(program, self.config)
        controller, seq_data = list(controller_seq_data.items())[0]
        total_saves = seq_data['num_saves'] * num_avg
        if jobqueue is not None:
            jobqueue.set_total(total_saves)
        
        options = self.config['controllers'][next(iter(self.controllers))]
        streams = self.controllers[controller].execute(
            seq_data, num_avg=num_avg, display=display, options=options
        )
        
        def update_progress():
            qsize = 0
            qsize_old = 0
            t = 0
            first_update = True
            while qsize < total_saves:
                if t > progress_timeout:
                    print('Measurement timeout.')
                    break
                qsize = np.sum([stream.qsize() for _, stream in streams.items()])
                if qsize == qsize_old:
                    t += progress_interval
                elif first_update and qsize:
                    jobqueue.set_total(total_saves)
                    # jobqueue.set_finished(total_saves)
                    
                    first_update = False
                else:
                    jobqueue.set_finished(qsize)
                time.sleep(progress_interval)
                
        if jobqueue is not None:
            thread = Thread(target=update_progress)
            thread.start()
            thread.join()
        return streams
