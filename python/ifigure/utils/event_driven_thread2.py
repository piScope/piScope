from __future__ import print_function
import time
import weakref
import threading
from six.moves import queue as Queue


lock = threading.Lock()
queues = []


def get_thread(return_queue=None):
    lock.acquire()
    new_queue = Queue.Queue()
    queues.append(new_queue)
    lock.release()
    return EventDrivenThread(queues[-1], return_queue), new_queue


def send_event(event):
    lock.acquire()
    for q in queues:
        q.put(event)
    lock.release()


def remove_queue(q):
    lock.acquire()
    if q in queues:
        queues.remove(q)
    lock.release()


class EventDrivenThread(threading.Thread):
    def __init__(self, queue, rqueue, *args, **kargs):
        super(EventDrivenThread, self).__init__(*args, **kargs)
        self._verbose = False
        self.queue = queue
        self.rqueue = rqueue
        self.events = {}
        self.start_event = self.name + 'start_action'
        self.finish_event = self.name + 'finish_action'
#        self.quit_event   = 'quit_thread'

    def bind(self, event, method):
        if event in self.events:
            self.events[event].append(method)
        else:
            self.events[event] = [method]

    def unbind(self, event, method):
        if event in self.events:
            if method in self.events[event]:
                self.events[event].remove(method)
            if len(self.events[event]) == 0:
                del(self.events[event])

    def bind_init(self, work, method):
        self.bind(work.get_full_path() + '.start', method)
        return work.get_full_path() + '.start'

    def run(self, *args, **kagrs):
        send_event(self.start_event)
        self.flag = True
        while (self.flag):
            if self.queue.empty():
                time.sleep(0.1)
            else:
                event = self.queue.get(False)
#               print event, self.name
#               print self.events
                if event in self.events:
                    methods = [m for m in self.events[event]]
                    for m in methods:
                        m(event)
#                       print 'unbind', event, m
                        self.unbind(event, m)
#                   print self.events
#                           print event, ' finished method  (', m.__name__,',', m.__self__.name, ') in ', self.name
#                       else:
#                           print event, ' attempted to perform method  (', m.__name__,',', m.__self__.name, ') in ', self.name

#                       print self.events
                time.sleep(0.1)
            if len(self.events) == 0:
                self.flag = False
        remove_queue(self.queue)
        send_event(self.finish_event)
        self.queue = None
        self.events = None
        if self.rqueue is not None:
            self.rqueue.put(self.name)
        self.rqueue = None
        print(('Exiting...', self.name))
