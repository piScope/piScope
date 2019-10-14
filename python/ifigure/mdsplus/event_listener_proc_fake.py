from __future__ import print_function

'''
fake listner thread for debugging
'''

import multiprocessing as mp
import threading
from six.moves import queue as Queue
import traceback
import time
from weakref import WeakKeyDictionary
import __future__

use_event_listener = True


class EventListenerProc(mp.Process):
    def __init__(self, task_queue, result_queue, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(EventListenerProc, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        #self.sub_queue = Queue.Queue()
        self.result_queue = result_queue
        self.event_threads = []
        self.event_list = []

    def run(self, *args, **kargs):
        while True:
            #            while True:
            try:
                jobcode, jobparam = self.task_queue.get(True)  # True, 0.1)

            except:
                continue
                pass
            # jobset
            ###   (jobcode, jobparam)
            # jobcode : 'wait' : launch thread if it is not waiting
            # jobcode : 'exit' : exit loop
            # jobcode : 'send' :  when event is recieved
            if jobcode == 'wait':
                pass
               # jobparam = event name

            elif jobcode == 'send':
                # jobparam = event thread
                self.result_queue.put(jobparam)
            elif jobcode == 'exit':
                for o in self.event_threads:
                    try:
                        o.cancel()
                    except:
                        traceback.print_exc()
                        print('MDSplus event cancel failed')
                        pass
#                print('exiting')
                break
            elif jobcode == 'disconnect':
                if jobparam in self.event_list:
                    o = EventThread(self.task_queue, jobparam)
                    for t in self.event_threads:
                        if t.event_name == jobparam:
                            t.cancel()
            else:
                pass
#            self.task_queue.task_done()
