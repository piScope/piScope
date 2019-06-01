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

import MDSplus
from MDSplus import Connection
use_event_listener = True


class EventListenerProc(mp.Process):
    def __init__(self, task_queue, result_queue, *args, **kargs):
        super(EventListenerProc, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue

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
            elif jobcode == 'exit':
                #                print('exiting')
                break
            elif jobcode == 'disconnect':
                pass
            else:
                pass


class EventListener(threading.Thread):
    def __init__(self, *args, **kargs):
        super(EventListener, self).__init__(*args, **kargs)
        self.queue = mp.Queue()  # queue to receive message
        self.task_queue = mp.JoinableQueue()
        self.listener_proc = EventListenerProc(self.task_queue,
                                               self.queue)
        self.listener_proc.start()

    def run(self, *args, **kargs):
        while True:
            event_name = self.queue.get(True)
            if event_name == 'stop':
                #globals()['listener_thread'] = None
                return
            mds_event_listener_lock.acquire()
            check = False
            # do nothing
            mds_event_listener_lock.release()


if __name__ == '__main__':
    server = 'ssh://shiraiwa@alcdata.psfc.mit.edu'  # this makes a dead-lokc
#    server = 'alcdata.psfc.mit.edu'                # this works
    c = Connection(server)

    listener_thread = EventListener()
    listener_thread.task_queue.put(('exit', ''), False)
    listener_thread.queue.put('stop')

    print('good bye')
