from __future__ import print_function
import time
import weakref
import threading
from six.moves import queue as Queue

queues = []


def get_thread():
    queues.append(Queue.Queue())
    return EventDrivenThread(queues[-1]), queues[-1]


def send_event(event, t=None):
    if t is None:
        name = threading.current_thread().name
    else:
        name = t.name
    for q in queues:
        q.put(name+'_'+event)


def remove_queue(q):
    if q in queues:
        queues.remove(q)


class EventDrivenThread(threading.Thread):
    def __init__(self, queue, *args, **kargs):
        super(EventDrivenThread, self).__init__(*args, **kargs)
        self.queue = queue
        self.events = {}
        self.start_event = 'start_action'
        self.finish_event = 'finish_action'
        self.quit_event = 'quit_thread'

    def bind(self, event, method, t=None):
        ''' 
        bind an evnet from thread t to method 
        '''
        if t is None:
            t = self
        ename = t.name + '_' + event
        if ename in self.events:
            self.events[ename].append(method)
        else:
            self.events[ename] = [method]

    def unbind(self, event, method, t=None):
        if t is None:
            t = self
        ename = t.name + '_' + event
        if ename in self.events:
            if method in self.events[ename]:
                self.events[ename].remove(method)

    def bind_init(self, method):
        self.bind(self.start_event,  method)

    def bind_quit(self):
        self.bind(self.quit_event, self.onQuitThread)

    def run(self, *args, **kagrs):
        send_event(self.start_event)
        self.flag = True
        while (self.flag):
            if self.queue.empty():
                time.sleep(0.1)
            else:
                event = self.queue.get(False)
                print(event)
                print(self.events)
                if event in self.events:
                    print(('calling method for ', event))
                    for m in self.events[event]:
                        m(event)
        remove_queue(self.queue)
        send_event(self.finish_event)
        self.queue = None
        self.events = None
        print(('Exiting...', self.name))

    def onQuitThread(self, e):
        self.flag = False
