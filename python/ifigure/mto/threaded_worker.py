from __future__ import print_function
#
#   Threaded worker
#      A utility class to support thread-based parallelism
#      in model execution.
#

import time
import ifigure
import wx
from six.moves import queue as Queue
import threading
from ifigure.utils.event_driven_thread2 import get_thread, send_event


def c_thread():
    import threading
    return threading.current_thread()


class ThreadedWorker(object):
    def __init__(self):
        self._waitlist1 = {}
        self._waitlist2 = {}
        self._background = False
        self._run_after = ''
        self._restart = False
        self._run_mode = False
        self._run_verbose = False
        self._return_queue = None

    def get_background(self):
        return self._background

    def set_background(self, value=True):
        self._background = value
        return self

    def _initialize_waitlist(self):
        self._waitlist1 = {}
        self._waitlist2 = {}
        self._restart = False

        for c in self.walk_model():
            c._initialize_waitlist()

    def Run(self, event=None, wait=None, return_queue=None):
        '''
        setup thread
        event combination
        '''
        self._initialize_waitlist()

        if wait is not None:
            return_queue = Queue.Queue()
        t, queue = get_thread(return_queue)
        t._verbose = self._run_verbose
        trigger = t.bind_init(self, self._doJob1)
        t_list = self.set_background(False)._setup_jobchain(t, [t])

        if event is not None:
            w = event.GetEventObject()
        else:
            w = self.get_app()
        for t in t_list:
            ifigure.events.SendThreadStartEvent(self, w=w, thread=t)
        # print 'thread list', t_list

        send_event(trigger)

        if wait is not None:
            t = threading.current_thread()
            if t.name == 'MainThread':
                while return_queue.empty():
                    wx.Yield()
            else:
                return_queue.get()
        if return_queue is not None:
            return [t.name for t in t_list]
#            if hasattr(wait, 'put'): wait.put(self)

    def _setup_jobchain(self, current_thread, thread_list):
        from ifigure.mto.py_code import PyModel

        for name in self._run_after.split(','):
            if isinstance(self._parent, PyModel):
                work = self._parent.eval_setting_str(name.strip())
                if work is not None:
                    self._add_waittostart(work)

        name = self.get_full_path()
        if self._background:
            t, queue = get_thread()
            t._verbose = self._run_verbose
            t.bind(name+'.job1_done', self._doJob2)
            self._bind_waitlist1(t)
            thread_list.append(t)
            if not self._run_mode:
                for c in self.walk_model():
                    if c.is_suppress():
                        continue
                    c._add_waittostart(self, 'job1_done')
                    thread_list = c._setup_jobchain(t, thread_list)
                    self._add_waittofinish(c)
            self._bind_waitlist2(t)
        else:
            current_thread.bind(name+'.job1_done', self._doJob2)
            self._bind_waitlist1(current_thread)
            if not self._run_mode:
                for c in self.walk_model():
                    if c.is_suppress():
                        continue
                    c._add_waittostart(self, 'job1_done')
                    thread_list = c._setup_jobchain(
                        current_thread, thread_list)
                    self._add_waittofinish(c)
            self._bind_waitlist2(current_thread)
        return thread_list

    def _bind_waitlist2(self, t):
        for e in self._waitlist2:
            t.bind(e, self._doJob2)

    def _bind_waitlist1(self, t):
        for e in self._waitlist1:
            t.bind(e, self._doJob1)

    def _add_waittostart(self, work, m='job2_done'):
        name = work.get_full_path()
        self._waitlist1[name + '.' + m] = False

    def _add_waittofinish(self, work):
        name = work.get_full_path()
        self._waitlist2[name + '.job2_done'] = False

    def _doJob1(self, event):
        # check conditions
        if event in self._waitlist1:
            self._waitlist1[event] = True
        v = True
        for key in self._waitlist1:
            v = v and self._waitlist1[key]
        if not v:
            return False

        name = self.get_full_path()
        if self._run_verbose:
            print('performing ' + name + '.job1 in ' + c_thread().name)
        self._status = 'running...'
        app = wx.GetApp().TopWindow
#        print 'in do job1', self, threading.current_thread().name
        wx.CallAfter(app.proj_tree_viewer.update_widget_request2)

        self.do_run()
        send_event(name + '.job1_done')

#        for key in self._waitlist1: self._waitlist1[key] = False
        return True

    def _doJob2(self, event):
        if event in self._waitlist2:
            self._waitlist2[event] = True
        v = True
        for key in self._waitlist2:
            v = v and self._waitlist2[key]

        if not v:
            return False

        name = self.get_full_path()
        if self._run_verbose:
            print('performing ' + name + '.job2 in ' + c_thread().name)

        send_event(name + '.job2_done')

        self._status = ''
#        print 'in do job2', self, threading.current_thread().name
#        if self._return_queue is not None: self._return_queue.put('done')
        app = wx.GetApp().TopWindow
        wx.CallAfter(app.proj_tree_viewer.update_widget_request2)

#        for key in self._waitlist2: self._waitlist2[key] = False
        return True
