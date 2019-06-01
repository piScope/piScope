from .event_listener_proc_fake import EventListenerProc, use_event_listener
from numpy import ndarray
import multiprocessing as mp
import threading
from six.moves import queue as Queue
import traceback
import time
import tempfile
import wx
import select
from weakref import WeakKeyDictionary
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('event_listener')

MDSEventReceived = wx.NewEventType()
MDSSCOPE_EVT_MDSEVENT = wx.PyEventBinder(MDSEventReceived, 1)

mds_event_listener_lock = threading.Lock()
listener_thread = None


class EventListener(threading.Thread):
    def __init__(self, *args, **kargs):
        super(EventListener, self).__init__(*args, **kargs)
        self.queue = mp.Queue()  # queue to receive message
        self.task_queue = mp.JoinableQueue()
        self.listener_proc = EventListenerProc(self.task_queue,
                                               self.queue)
        wx.CallAfter(self.listener_proc.start)
        self.viewers = WeakKeyDictionary()

    def run(self, *args, **kargs):
        while True:
            #            try:
            event_name = self.queue.get(True)
            if event_name == 'stop':
                #                from ifigure.mdsplus.mdsscope import scope_count
                #                if scope_count == 0:
                globals()['listener_thread'] = None
                return
            mds_event_listener_lock.acquire()
            check = False
            ll = list(self.viewers.items())  # protecting weakdictionary
            for v in self.viewers:
                if event_name in self.viewers[v]:
                    evt = wx.PyCommandEvent(MDSEventReceived,
                                            wx.ID_ANY)
                    evt.mdsevent_name = event_name
                    try:
                        wx.PostEvent(v, evt)
                    except:
                        check = True
                        pass
            del ll
            if check:
                del self.viewers[v]

            mds_event_listener_lock.release()


def launch_listener():
    if not use_event_listener:
        return
    if globals()['listener_thread'] is None:
        globals()['listener_thread'] = EventListener()
#        globals()['task_queue'] = mp.Queue()
        wx.CallAfter(globals()['listener_thread'].start)


def stop_listener():
    if not use_event_listener:
        return
    t = globals()['listener_thread']
    t.task_queue.put(('exit', ''), False)
    t.queue.put('stop')
    globals()['listener_thread'] = None


def disconnect_listener(viewer, event_name):
    if not use_event_listener:
        return
    t = globals()['listener_thread']
    if viewer in t.viewers:
        names = t.viewers[viewer]
        mds_event_listener_lock.acquire()
        if event_name in names:
            t.viewers[viewer].remove(event_name)

        # if noone is waiting for this event, stop event thread
        if not any([event_name in t.viewers[v]
                    for v in t.viewers]):
            t.task_queue.put(('disconnect', event_name))
        mds_event_listener_lock.release()


def connect_listener(viewer, event_name):
    if not use_event_listener:
        return
    launch_listener()
    t = globals()['listener_thread']
    t.task_queue.put(('wait', event_name))
    mds_event_listener_lock.acquire()
    if not viewer in t.viewers:
        t.viewers[viewer] = []
    if not event_name in t.viewers[viewer]:
        t.viewers[viewer].append(event_name)
    mds_event_listener_lock.release()
