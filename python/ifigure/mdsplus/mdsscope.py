from __future__ import print_function
#
#         dwscope implementation on piscope
#
#         2014 02 02  version 1-beta
#              02 09  shot number, shot number histroy save
#                     fig_mdsbook is made.
#                     any book opend by mdsscope is converted
#                     to fig_mdsbook so that save data does not
#                     make a huge file. Also, when mdsscoe
#                     closes a book, it delete all plot data.
#              02 15  rewritting mdssession. goal is
#                     * eliminate a loop to poll mp.queue
#                     * run mds part of global analysis in parallel.
#                     * allow to accept jobs from multiple viewer
#
#        Note: MDSScope uses SR(session runner), PP(post processing),
#              JD(job done) threads + mpworkers
#
#              These thread always wait for one queue.
#              This is normal flow of messages between threads
#
#              Main thread
#    (apply/abort) |
#                  |
#                  ---->     SR thread --------> workers
#                  |                        |       |
#                  |              (cleaning)|       |
#        (pp done) |                        |       |(ana done)
#                  --------- PP thread  <-----------|
#
#
#         TODO : evaluate range by TDI?
#                clean up variable reset routine
#                optimize session runner loop
#
#
# *******************************************
#     Copyright(c) 2012- S.Shiraiwa
# *******************************************
__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "1.0"
__maintainer__ = "Syun'ichi Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

from collections import deque
import wx
import sys
import time
import weakref
import logging
import threading
from six.moves import queue as Queue
import os
import shutil
import numpy
import traceback
import collections
import multiprocessing as mp
#import wx.aui as aui
import ifigure
import ifigure.events
import ifigure.utils.cbook as cbook

#from ifigure.widgets.canvas.ifigure_canvas import ifigure_canvas
from ifigure.widgets.property_editor import property_editor
from ifigure.widgets.panel_checkbox import PanelCheckbox
from ifigure.widgets.statusbar import StatusBar, StatusBarSimple
import ifigure.widgets.dialog as dialog

#from ifigure.mto.fig_book import FigBook
#from ifigure.mto.fig_page import FigPage
#from ifigure.mto.fig_axes import FigAxes
from ifigure.mdsplus.fig_mds import FigMds, MDSJobSet
from ifigure.mdsplus.fig_mdsdata import FigMdsData
from ifigure.mto.figobj_param import FigobjParam, FigobjData
from ifigure.widgets.book_viewer import BookViewerFrame

import ifigure.mdsplus.mdsplusr as remote_mds

from ifigure.utils.setting_parser import iFigureSettingParser as SettingParser
from ifigure.mdsplus.mds_sp_worker_pool import MDSSPWorkerPool
from ifigure.mdsplus.mds_mpth_worker_pool import MDSMPWorkerPool, MDSTHWorkerPool
#from ifigure.mdsplus.fig_mds import build_init_local_global_session
from ifigure.mdsplus.fig_mds import build_current_shot_session
from ifigure.mdsplus.fig_mds import add_connect_session
from ifigure.mdsplus.event_listener import MDSSCOPE_EVT_MDSEVENT

from ifigure.widgets.at_wxthread import at_wxthread

from .utils import parse_server_string
from ifigure.utils.wx3to4 import (menu_Append,
                                  menu_AppendSubMenu,
                                  menu_AppendItem)

#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('MDSScope')

# number of global config
n_global = 4

# session_runner
mds_thread = None
mds_num_worker = 5
lock = threading.Lock()
aglock = threading.Lock()

bitmap_names = ['resetrange_all.png']
bitmaps = {}

# data for recent items
RECENT_FILE = deque(['']*10, 10)

def print_threaderror(txt):
    for line in txt:
        dprint1(str(line)+'\n')


def print_threadoutput(txt):
    print(txt)


def start_mds_threads():
    if globals()['mds_thread'] is None:
        lock.acquire()
        queue = Queue.Queue()
        globals()['mds_thread'] = SessionRunner(queue)
        globals()['mds_thread'].start()
        lock.release()
    return globals()['mds_thread']


call_after_queue = None


def set_call_after_queue(m):
    globals()['call_after_queue'] = m


def CallAfter(callable, *args, **kargs):
    if call_after_queue is None:
        wx.CallAfter(callable, *args, **kargs)
    else:
        call_after_queue.put((callable, args, kargs))


class MDSWorkerPool(object):
    '''
    A layer to absorb the difference bretween
    subprocessing worker and multiprocessing worker
    '''
    pool = None
    c_type = None
    w_type = None
    t_type = None
    @classmethod
    def __init__(self, *args):
        object.__init__(self)
        self.start(*args)
#      def start(self, c_type, w_type):
    @classmethod
    def start(self, *args):
        # c_type = direct|proxy
        # w_type = subprocess|multiprocessing
        if self.pool is None:
            if len(args) == 2:
                c_type = args[0]
                w_type = args[1]
                t_type = 'default'
            elif len(args) == 3:
                c_type = args[0]
                w_type = args[1]
                t_type = args[2]
            else:
                return
            if (self.c_type == c_type and
                self.w_type == w_type and
                    self.t_type == t_type):
                return
            num_worker = mds_num_worker
            print('starting ' + str(num_worker) + ' ' + w_type + ' workers')
            kwargs = {'translater': t_type}
            if w_type == 'mp':
                self.pool = MDSMPWorkerPool(num_worker,
                                            *c_type, **kwargs)
            elif w_type == 'th':
                self.pool = MDSTHWorkerPool(num_worker,
                                            *c_type, **kwargs)
            else:  # w_type == 'sp':
                self.pool = MDSSPWorkerPool(num_worker,
                                            *c_type, **kwargs)
            self.c_type = c_type
            self.w_type = w_type
            self.t_type = t_type

    @classmethod
    def reset(self):
        if self.pool is not None:
            self.pool.terminate_all()
            self.pool = None
            self.c_type = None
            self.w_type = None
            self.t_type = None

    @classmethod
    def is_any_worker_alive(self):
        if self.pool is not None:
            return self.pool.is_any_alive()
        return False

    @classmethod
    def is_workerstarted(self):
        return self.pool is not None


# def CleanMDSWorkerPool():
#    MDSWorkerPool().reset()

class AnaGroup(list):
    def __init__(self, x, *args, **kargs):
        list.__init__(self, *args, **kargs)
        self.isglobal = x
        self.func = None
        self.aborted = False
        self.postprocess_done = False
        self.nomode_change = False  # if change 'apply/abort' button label
        self.global_tdi = None


class GlobalCounter(object):
    '''
    an object to count
    how many globals are done. this object will 
    be shared among ana_groups, so that all ana_group
    will see the correct number
    '''

    def __init__(self, x, book, *args, **kargs):
        object.__init__(self, *args, **kargs)
        self.c = x
        self.book = str(book.get_full_path())

    def __call__(self, x=None):
        if x is not None:
            self.c = x
        return self.c


class SessionRunner(threading.Thread):
    '''
    this thread runs mds session

    '''

    def __init__(self, queue,  *args, **kargs):
        '''
        queue : message queue used to communicate with main thread
        type : subprocess | multiprocessing
        '''
        super(SessionRunner, self).__init__(*args, **kargs)
        self.queue = queue
        self._time = 0
        self._nextthread = None

    def start_next_thread(self):
        while MDSWorkerPool.pool is None:
            time.sleep(0.3)
        self.ana_groups = weakref.WeakKeyDictionary()
        self.pool = MDSWorkerPool.pool
        self._nextthread = PostProcessRunner(self)
        self._nextthread.start()

    def run(self, *args, **kargs):
        # note : this makes next thread launched from
        # this thread. is it okay?
        self.start_next_thread()

        while True:
            job = self.queue.get(True)
            if job.n == 'stop':
                if MDSWorkerPool().pool is not None:
                    MDSWorkerPool().pool.results.put('stop')
                    self.queue.task_done()
                break
            if self.pool is not MDSWorkerPool.pool:
                self.start_next_thread()
            if job.n == 'run':
                lock.acquire()
                self.run_session(job.p[0], job.p[1], job.p[2], job.p[3])
                lock.release()
            elif job.n == 'abort':
                pool = MDSWorkerPool.pool
                viewer = job.p[0]
#               print self.ana_groups
                if viewer in self.ana_groups:
                    #                    aglock.acquire()
                    ana_groups = pool.abort_job()
                    tmp = self.ana_groups[viewer][:]
                    for ana in self.ana_groups[viewer]:
                        ana.aborted = True
                        if ana in ana_groups:
                            ana_groups.remove(ana)
                            tmp.remove(ana)
                    self.ana_groups[viewer] = tmp  # this is the jobs which has
                    # already started
                    dprint1('aborting job, ' +
                            str(len(tmp)) + ' job(s) are already submitted')
#                    aglock.release()
                    # resubmit jobs for other viewers
                    for ana_group in ana_groups:
                        self.pool.submit_ana_group(ana_group)
                    # let's do this immidately.
                    del self.ana_groups[viewer]
                    MDSWorkerPool().pool.results.put(str(viewer.book.get_full_path()))
                    CallAfter(viewer.eval_mdsdata_done)
            elif job.n == 'ppdone':
                ana_group = job.p[0]
                done, viewer = self.check_job_done(ana_group)
                if done and not ana_group.nomode_change:
                    self.do_finishing_job(viewer, ana_group)
                # if it is global analysis, subtract 1 from gc counter
                # and send gc to queue, which will trigger post-processing
                # of normal panel analysis.
                if ana_group.isglobal:
                    ana_group.gc(ana_group.gc()-1)
                    if ana_group.gc() == 0:
                        MDSWorkerPool().pool.results.put(ana_group.gc)
            elif job.n == 'ppabort':
                #               ana_group = job.p[0]
                #               done, viewer = self.check_job_done(ana_group)
                #               if done:
                #                     self.do_finishing_job(viewer, ana_group)
                wx.CallAfter(dprint1, 'aborted job returned\n')
                # if it is global analysis, subtract 1 from gc counter
                # and send gc to queue, which will trigger post-processing
                # of normal panel analysis.
#               if ana_group.isglobal:
#                   ana_group.gc(ana_group.gc()-1)
#                   if ana_group.gc() == 0:
#                       MDSWorkerPool().pool.results.put(ana_group.gc)
            self.queue.task_done()

    def run_session(self, ana,  viewer, func, nomode_change):
        def group_analysis(ana, flag, viewer, gc):
            ana_groups = collections.OrderedDict()
            ana2 = ana[:]
            for ig, a in enumerate(ana2):
                #               if hasattr(a, 'fig_mds'):
                #                   print a.shot,  a.fig_mds()._shot, a.ishot, a.can_skip
                #                   print a.shot in a.fig_mds()._shot
                #                   if a.shot in a.fig_mds()._shot:
                #                       print a.fig_mds()._shot[a.shot] == a.ishot
                if (hasattr(a, 'fig_mds') and
                    (a.shot in a.fig_mds()._shot and
                     a.fig_mds()._shot[a.shot] == a.ishot and
                     a.can_skip)) or a.shot < -1:
                    # run only title evaluation
                    if a.do_title and len(a.jobs) > 3:
                        # the second cond. is for fake runner (to test iscope
                        #  w/o network...)
                        if a.jobnames[1] == 'def_node':
                            idx = [0, 1, -2, -1]
                        else:
                            idx = [0,  -2, -1]
                        b = [a.jobs[i] for i in idx]
                        bname = [a.jobnames[i] for i in idx]
                        a.jobs = MDSJobSet()
                        a.jobs.extend(b)
                        a.jobnames = bname
#                          b = [a.jobs[0], a.jobs[-2], a.jobs[-1]]
#                          a.jobs = MDSJobSet()
#                          a.jobs.extend(b)
#                          a.jobnames = [a.jobnames[0], a.jobnames[-2], a.jobnames[-1]]
                        a.skipped = True
#                       print 'title only job'
                    else:
                        ana.remove(a)
                        a.skipped = True
                        a.postprocess_done = True
                        CallAfter(viewer.postprocess_skipped_data,
                                  a.fig_mds(), a)
#                       print 'skipped entire job'
                        continue
#               else:
#                   print 'normal job'
                for key in ana_groups:
                    # find if a should go into an existing group
                    if (a.ipage == -1):
                        continue  # global analsys has always its own group
                    if ((a.ipage == key[0] and  # same shot same page same panel
                         a.ishot == key[1] and  # runs by same worker
                         a.isec == key[2]) or
                        (a.ipage == key[0] and  # same shot same page runs by same worker
                         a.ishot == key[1] and  # if not parallelizing panels
                         not flag[2]) or
                        (a.ishot == key[1] and  # same shot runs by same worker
                         # if not parallelizing panels and pages
                         not flag[1] and
                         not flag[2]) or
                        (not flag[0] and
                         not flag[1] and
                         not flag[2])):
                        ana_groups[key].append(a)
                        break
                else:
                    ana_groups[(a.ipage, a.ishot, a.isec, ig)
                               ] = AnaGroup(a.ipage == -1, [a])

            ret = []
#           print len(ana2)
            for key in ana_groups:
                ana_groups[key].gc = gc
                ret.append(ana_groups[key])

            new_ret = []
            for k, ana_group in enumerate(ret):
                # for a in ana_group:
                #    print a.ipage, a.ishot, a.isec

                tmp = sorted([(a.ishot, a)
                              for a in ana_group], key=lambda x: x[0])
                new_group = AnaGroup(ana_group.isglobal, [x[1] for x in tmp])
                new_group.gc = ana_group.gc
                new_ret.append(new_group)
                # for a in new_group:
                #    print a.ipage, a.ishot, a.isec
#           print len(ret)
#           return ret
            return new_ret

        if isinstance(viewer, ScopeEngine):
            parallel_flag = (viewer.book._parallel_page,
                             viewer.book._parallel_shot,
                             viewer.book._parallel_sec)
            init_flag = (viewer.init_page,
                         viewer.init_shot,
                         viewer.init_sec)
            book = viewer.book
        else:
            parallel_flag = (True, True, True)
            init_flag = (False, False, False)
            book = wx.GetApp().TopWindow.proj

        #
        #  group analysis (returned ana does not have skipped analysis)
        #
        global_ana = []
        for a in ana:
            if (a.ipage == -1):
                global_ana.append(a)

        gc = GlobalCounter(len(global_ana), book)
        ana_groups = group_analysis(ana, parallel_flag, viewer, gc)

        #
        #  append connection
        #  each worker needs to judge if it really need to redo connection
        #  and initalization
        #  global_tdi(title_tdi) is also added at this step
        #
        if isinstance(viewer, ScopeEngine):
            for ana_group in ana_groups:
                add_connect_session(viewer.book, ana_group)

#       aglock.acquire()
        if not viewer in self.ana_groups:
            self.ana_groups[viewer] = []
        self.ana_groups[viewer].extend(ana_groups)
#       aglock.release()
        if len(self.ana_groups[viewer]) == 0:
            self.do_finishing_job(viewer)

        MDSWorkerPool().pool.results.put(gc.book)
        for ana_group in self.ana_groups[viewer]:
            ana_group.func = func
            ana_group.aborted = False
            ana_group.nomode_change = nomode_change
            self.pool.submit_ana_group(ana_group)
        viewer._mdsjob_count = len(self.ana_groups[viewer])

        if hasattr(viewer, 'show_mdsjob_count'):
            CallAfter(viewer.show_mdsjob_count)

    def do_finishing_job(self, viewer, ana_group=None):
        if hasattr(viewer, 'eval_mdsdata_done'):
            CallAfter(viewer.eval_mdsdata_done)
            if isinstance(viewer, MDSScope):
                ifigure.events.SendChangedEvent(
                    viewer.book, w=viewer, useProcessEvent=True)
        # request cleaning of waiting list in pp thread
        if ana_group is not None:
            MDSWorkerPool().pool.results.put(ana_group.gc.book)

    def check_job_done(self, ana_group):
        ###
        ###
        done_flag = False
        viewer = None
#       aglock.acquire()
        d = self.ana_groups

        for key in d:
            #          if hasattr(ana_group[0],'fig_mds'):
            #              print 'check job done', ana_group[0].fig_mds()
            if ana_group in d[key]:
                try:
                    d[key].remove(ana_group)
                    viewer = key
                    viewer._mdsjob_count = len(d[key])
                    if hasattr(viewer, 'show_mdsjob_count'):
                        CallAfter(viewer.show_mdsjob_count)
                    if len(d[key]) == 0:
                        del d[key]
                        done_flag = True
                    break
                except:
                    dprint1(traceback.format_exc())
#       aglock.release()
        return done_flag, viewer


class PostProcessRunner(threading.Thread):
    '''
    this thread run postprocessing (updating figure data or
    run script)

    TODO: delay triggering postprocessing until global done
    '''

    def __init__(self, parent, *args, **kargs):
        super(PostProcessRunner, self).__init__(*args, **kargs)
        self.session_runner = parent
#       self._nextqueue = Queue.Queue()
#       self._nextthread = JobDoneThread(self._nextqueue, parent)
#       self._nextthread.start()
        self._waitinglist = dict()
        ###

    def run(self, *args, **kargs):
        while MDSWorkerPool().pool is None:
            time.sleep(0.3)
        self.pool = MDSWorkerPool().pool
        while True:
            #           t = time.time()
            task = self.pool.check_ana_group_done()
            if task is None:
                continue
            isempty = self.pool.has_noresult()
            # print 'got data', time.time(), isempty
            # print 'task recieved in pp thread', task
            # print isinstance(task, str), type(task)

            if task == 'stop':
                #               self._nextqueue.put('stop')
                break
            elif isinstance(task, str):
                if task in self._waitinglist:
                    del self._waitinglist[task]
                continue
            elif isinstance(task, GlobalCounter):
                if not task.book in self._waitinglist:
                    continue
                for x in self._waitinglist[task.book]:
                    idx = [k for k, ana in enumerate(x) if ana.done]
                    if x.aborted:
                        self.goto_next(x, m='abort')
                        continue
                    self.run_pp(x, idx, allow_draw=False)
                    self.request_gui_update(x, idx)
            else:  # task is ana with results stored
                ana_group, idx = task
                if ana_group.aborted:
                    # case 1) abort during reciving current shot number
                    # it skippes the steps to construct MDSsessions
                    # for panels
                    # case 2) abort during normal panels
                    # it skippes panel update (+ scripts in main thread)
                    self.goto_next(ana_group, m='abort')
                else:
                    if not hasattr(ana_group, 'gc'):
                        print('ana_group has no gc')
                        continue
                    gc = ana_group.gc
                    if gc() > 0:
                        if not gc.book in self._waitinglist:
                            self._waitinglist[gc.book] = []
                        if not ana_group.isglobal:
                            if not ana_group in self._waitinglist[gc.book]:
                                self._waitinglist[gc.book].append(ana_group)
                            continue
                    self.run_pp(ana_group, [idx], isempty=isempty)
        self.session_runner = None
        self._waitinglist = None

    def run_pp(self, ana_group, idx, allow_draw=True, isempty=False):
        call_draw = False
        viewer = None
        for k in idx:
            a = ana_group[k]
            # print a.postprocess_done,  a.status,  hasattr(a, 'fig_mds')
            if a.postprocess_done:
                # this flag may on if analysis does not
                # require postprocessing (such as init_variabls..)
                continue
            if a.status:
                if not hasattr(a, 'fig_mds'):
                    # this is for current shot number query
                    # it triggers following mdssessions
                    CallAfter(ana_group.func, a)
                    a.postprocess_done = True
                    continue

                fig_mds = a.fig_mds()
#               if a.skipped and    if viewer is not None:
#                       CallAfter(viewer.postprocess_skipped_data, fig_mds, a)
#               else:
                #ana_group.func(fig_mds, a)
                CallAfter(ana_group.func, fig_mds, a, ana_group=ana_group)
#                  try:
#                       ana_group.func(fig_mds, a)
#                  except:
#                       wx.CallAfter(dprint1, 'Error during post processing\n'+
#                                    traceback.format_exc())
#                       continue
                if (fig_mds.get_parent() is not None and
                        a.isec != -1):
                    # None when getting current shot number
                    # wx.CallAfter(fig_mds.get_figaxes().adjust_axes_range)
                    #CallAfter(fig_mds.call_refresh_artist, a.ishot)
                    if a.result['worker output'].strip() != '':
                        CallAfter(print_threadoutput,
                                  a.result['worker output'])

            else:
                if hasattr(a, 'fig_mds'):
                    fig_mds = a.fig_mds()
                    if fig_mds.get_parent() is not None:
                        # None when getting current shot number
                        CallAfter(fig_mds.suppress_ishot,
                                  a.ishot)
                else:
                    # this is for current shot number query
                    # it triggers following mdssessions
                    CallAfter(ana_group.func, a)
                    a.postprocess_done = True
                    continue
                if ('error message' in a.result and
                        len(a.result['error message']) > 0):
                    #                    CallAfter(print_threaderror
                    #                              a.result['error message'])
                    #                    print 'error message',
                    txt = ['']
                    for item in a.result['error message']:
                        txt.append(str(item))
                    CallAfter(dprint1, '\n'.join(txt))
                a.postprocess_done = True
        if allow_draw and self.pool.has_noresult():
            self.request_gui_update(ana_group, idx)
        self.goto_next(ana_group)

    def request_gui_update(self, ana_group, idx):
        flag = False
        for k in idx:
            a = ana_group[k]
            if not hasattr(a, 'fig_mds'):
                continue
            fig_mds = a.fig_mds()
            if fig_mds is None:
                continue
            viewer = wx.GetApp().TopWindow.find_bookviewer(fig_mds.get_figbook())
            if viewer is None:
                continue
            if viewer.ipage == a.ipage:
                flag = True
                break
        # call draw only when no more result is available
        CallAfter(wx.GetApp().TopWindow.proj_tree_viewer.update_widget_request)
        if (flag and isinstance(viewer, ScopeEngine) and
                globals()['call_after_queue'] is None):
            #              print 'here'
            if not viewer.canvas._drawing:
                #                  viewer.canvas._drawing = True
                #                  wx.CallAfter(viewer.canvas.draw_later)
                viewer.canvas.draw_later(delay=1.0)

    def goto_next(self, ana_group, m='done'):
        #       if m == 'abort' or all([a.done for a in ana_group]):
        if m == 'abort' or all([a.postprocess_done for a in ana_group]):
            #           self._nextqueue.put((m, ana_group ))
            self.session_runner.queue.put(message('pp'+m, (ana_group,)))


class message(object):
    def __init__(self, n, p):
        self.n = n
        self.p = p


class ScopeEngine(object):
    scope_count = 0

    def __init__(self, no_window=False):
        self._no_window = no_window
        self._mode = 'apply'
        self._engine_open = False

    def open_engine(self):
        ScopeEngine.scope_count = ScopeEngine.scope_count + 1
        self._engine_open = True

    def close_engine(self):
        if not self._engine_open:
            return
        ScopeEngine.scope_count = ScopeEngine.scope_count - 1
        if ScopeEngine.scope_count == 0:
            lock.acquire()
            mds_thread = globals()['mds_thread']
            if mds_thread is not None:
                c = message('stop', None)
                mds_thread.queue.put(c)
                #self.queue.put(message('stop', None))
                mds_thread.join()
#                while self.mds_thread.isAlive():
#                    time.sleep(0.1)
#                    wx.GetApp().Yield(True)
#                    dprint1('waiting ...')
                #self.mds_thread = None
                globals()['mds_thread'] = None
            lock.release()
            from ifigure.mdsplus.event_listener import stop_listener
            print('stopping listener')
            stop_listener()
            print('listener stopped')
        self._engine_open = False

    def prepare_dwglobal(self, book):
        from ifigure.mdsplus.fig_mdsbook import prepare_dwglobal
        prepare_dwglobal(book)
        return book.dwglobal

    def eval_mdsdata(self, allshot=True, figaxes='all'):
        from ifigure.ifigure_config import canvas_scratch_page as csp
        shot_set = self.eval_mdsshot(allshot=allshot, figaxes=figaxes)

    def eval_mdsdata_step2(self, shot_set, allshot, figaxes):
        # prepare pages
        from ifigure.ifigure_config import canvas_scratch_page as csp
        num_page = self.book.num_page()
        if len(shot_set) > num_page:
            # add pages
            fig_page = self.get_page(0)
            self._duplicate_page(len(shot_set) - num_page, fig_page)
        elif len(shot_set) < num_page:
            # remove pages
            self.show_page(0)
            for junk in range(num_page-len(shot_set)):
                self.del_page(self.book.num_page()-1)

        # set suppress
        for i in range(len(shot_set)):
            l = len(shot_set[i])
            fig_page = self.get_page(i)
            for ax in fig_page.walk_axes():
                for name, child in ax.get_children():
                    if isinstance(child, FigMds):
                        child.active_plots(l)
        # build shot number index (horrible four for loops)
#        prevshot = self._cur_shot
        ushot_list = []
        prevshot0 = self._cur_shot
        for k, page in enumerate(self.book.walk_page()):
            self.set_index_col_row_page(k)
            for ax in page.walk_axes():
                prevshot = prevshot0
                shots = shot_set[k]
                if not (figaxes == 'all' or ax in figaxes):
                    continue
                for name, child in ax.get_children():
                    if not isinstance(child, FigMds):
                        continue
                    for s in shots:
                        ss, prevshot = child.eval_shotstr(s, prevshot,
                                                          self._cur_shot)
                        if ss is None:
                            self.eval_mdsdata_done(status=-2)
                            return
                        if ss == 'm' or ss == 'n':
                            ushot_list.append(-1)
                        else:
                            if ss > 0:
                                ushot_list.append(ss)
        ushot_list = [x for x in set(ushot_list)]

        # make a ana array for globals. for now, it runs global analysis for all shots
        # could be improved...
        # this global does not read global sets
        # this global never skips..

        ana_all = self.eval_mdsglobaldata_inner([], ushot_list)

        prevshot = self._cur_shot
        for k, shots in enumerate(shot_set):
            #           prevshots = ([] if k >= len(self.previous_shot_set) else
            #                        [long(s) for s in self.previous_shot_set[k]])
            ana_all, prevshot = self.eval_mdsdata_inner(shots, k,
                                                        ana_all,
                                                        prevshot, allshot,
                                                        ushot_list,
                                                        figaxes=figaxes)
            if ana_all is None:
                self.eval_mdsdata_done(status=-3)
                return

        c = message('run', (ana_all,  self, self.postprocess_data, False))
        globals()['mds_thread'].queue.put(c)
        # self.queue.put(c)  ### should use callafter?
        self.previous_shot_set = shot_set

    def eval_mdsglobaldata_inner(self, ana, ushot_list):
        if not self.book.dwglobal.getvar('use_shot_global'):
            return ana
        for name in self._get_common_var_names():
            child = self.book.get_child(name=name)
            for ss in ushot_list:
                ana.append(child.mdssession_job(shot=ss,
                                                dwglobal=None,
                                                startup=self.startup_script))
                ana[-1].fig_mds = weakref.ref(child)
                ana[-1].isec = -1
                ana[-1].ishot = -1
                ana[-1].uishot = ushot_list.index(ss)
                ana[-1].ipage = -1
                ana[-1].shot = ss
                ana[-1].can_skip = False
                ana[-1].do_title = False
        return ana

    def eval_mdsdata_inner(self, shots, ipage, ana,
                           prevshot0, allshot, ushot_list, figaxes='all'):

        init_param = (self.init_page,
                      self.init_sec)
        fig_page = self.get_page(ipage)
        app = fig_page.get_app()
#        fig_page0 = self.get_page(0)
        global_choice = self.book.dwglobal.getvar('global_choice')
        gs0 = self.book.dwglobal.getvar('globalsets')

        # build array of all analysis
        for isec, ax in enumerate(fig_page.walk_axes()):
            prevshot = prevshot0
            if not (figaxes == 'all' or ax in figaxes):
                continue
            for name, child in ax.get_children():
                if isinstance(child, FigMds):
                    child.reset_shots_expr()
                    for k, s in enumerate(shots):
                        ss, prevshot = child.eval_shotstr(s, prevshot,
                                                          self._cur_shot)
                        if ss is None and prevshot is None:
                            return None
                        if ss == 'm' or ss == 'n':
                            child.append_shots_expr(-1)
                        elif ss > 0:
                            child.append_shots_expr(ss)
                        if ss is None:
                            continue

                        gs = {key: gs0[key][global_choice[k]-1] for key in gs0}
                        ana.append(child.mdssession_job(shot=ss,
                                                        dwglobal=gs,
                                                        startup=self.startup_script))
                        ana[-1].fig_mds = weakref.ref(child)
                        ana[-1].isec = isec
                        ana[-1].ishot = k
                        if ss == 'm':
                            ana[-1].uishot = ushot_list.index(-1)
                        elif ss == 'n':
                            ana[-1].uishot = -100
                        else:
                            if ss > 0:
                                ana[-1].uishot = ushot_list.index(ss)
                            else:
                                ana[-1].uishot = -100
                        ana[-1].ipage = ipage
                        ana[-1].shot = ss
                        ana[-1].can_skip = (not allshot and
                                            ss != 'm' and ss != 'n')
                        ana[-1].do_title = False
                    for k, s in enumerate(shots):
                        if ana[-1-k].shot >= 0:
                            #                             'm'>0 = True, 'n'>0 = True
                            #                              print ana[-1-k].shot, 'do_title = True'
                            ana[-1-k].do_title = True
                            break
        return ana, prevshot

    def erase_mdsdata(self):
        fig_page = self.get_page()
        app = fig_page.get_app()

        # build array of all analysis
        ana = []
        for ax in fig_page.walk_axes():
            for name, child in ax.get_children():
                if isinstance(child, FigMds):
                    child.erase_mdsdata()
        ifigure.events.SendChangedEvent(fig_page, w=app)

    def postprocess_data(self, child, ana, ana_group=None):
        #       postprocessing after data is loaded from MDSplus

        fig_page = self.get_page()

        color_order = self.book.dwglobal.getvar('color_order')
        flag = child.postprocess_data(ana, self, color_order)
        for key in child._shot:
            if child._shot[key] == ana.ishot:
                del child._shot[key]
                break
        if flag:
            child._shot[ana.shot] = ana.ishot
        ana.postprocess_done = True

        if ana_group is not None and all([a.postprocess_done for a in ana_group]):
            c = message('ppdone', (ana_group,))
            globals()['mds_thread'].queue.put(c)
            # self.queue.put(c)

        if self._no_window:
            return
        if self.book.getvar('mdsscope_autogrid'):
            fig_ax = child.get_figaxes()
            if fig_ax is None:
                return
            flag = True
            for name, cc in fig_ax.get_children():
                if isinstance(cc, FigMds):
                    flag = flag and cc.is_all_suppressed()

            # skip if it is not yet realized.
            if len(fig_ax._artists) != 0:
                if flag:
                    fig_ax._artists[0].get_xaxis().grid(False, which='Major')
                    fig_ax._artists[0].get_yaxis().grid(False, which='Major')
                else:
                    fig_ax._artists[0].get_xaxis().grid(True, which='Major')
                    fig_ax._artists[0].get_yaxis().grid(True, which='Major')
        # print child, ana.ishot
        child.call_refresh_artist(ana.ishot)

    def postprocess_skipped_data(self, child, ana):
        #       postprocessing when data was NOT loaded from MDSplus
        p = child.get_child(ana.ishot)
        if p is not None:
            if (ana.ishot in child._analysis_flag and
                    child._analysis_flag[ana.ishot]):
                child.change_suppress(ana.shot < 0, p)
            elif (ana.ishot in child._analysis_flag and
                  not child._analysis_flag[ana.ishot]):
                child.change_suppress(True, p)
            else:
                child.change_suppress(False, p)
        child.get_figaxes().set_bmp_update(False)

    def store_shotnumber(self, ana=None, allshot=None, figaxes=None):
        # print 'store shot number'
        if allshot is None:
            txt = ana.shot_txt
            allshot = ana.allshot
            figaxes = ana.figaxes
            if ('shot' in ana.result and
                    ana.result['shot'] is not None):
                self._cur_shot = ana.result['shot']
            else:
                self._cur_shot = 0
            dprint1('current shot ' + str(self._cur_shot))
        else:
            txt = ana.shot_txt

        if self.mpanalysis:
            arr = txt.split(';')
            txt = ';'.join([arr[0]]*self.book.num_page())
        arr = txt.split(';')
        shot_set = []
        for t in arr:
            shot_set.append([x.strip() for x in t.split(',')])
        self.eval_mdsdata_step2(shot_set, allshot, figaxes)

    def set_mdsshot(self, shot):
        self.txt_shot.SetValue(str(shot))

    def eval_mdsshot(self, allshot=True, figaxes='all'):
        '''
        pre-process shot number field.
        if it starts from '='. do eval
        if it containes 'c', get the late shot number
        then split it, and return
        '''
        txt = self._run_eval_mdsshot()

        flag = False
        try:
            x = int(txt.split(';')[0].split(',')[0])
            flag = abs(x) < 1000
        except:
            flag = False
        if (txt.find('c') == -1 and txt.find('m') == -1 and
                txt.find('n') == -1 and not flag):
            ana = None
        else:
            ana = build_current_shot_session(self.book)
#        ana = None
        if ana is None:
            self._cur_shot = 0  # anything is ok just to transfer txt
            ana = AnaGroup([])
            ana.shot_txt = txt
            self.store_shotnumber(ana=ana, allshot=allshot, figaxes=figaxes)
        else:
            ana.allshot = allshot
            ana.figaxes = figaxes
            ana.shot_txt = txt
            ana_all = [ana]
            c = message('run', (ana_all, self, self.store_shotnumber, True))
            globals()['mds_thread'].queue.put(c)
            # self.queue.put(c)

    def set_index_col_row_page(self, ipage):
        '''
        set col row to fig_mds (it uses left_top conner coods.)
        '''
        p = self.get_page(ipage)
        l = [(int((a.getp('area')[0])*10),
              int((a.getp('area')[1] + a.getp('area')[3])*10),
              a) for a in p.walk_axes()]
        col = [int((a.getp('area')[0])*10)
               for a in p.walk_axes()]

        for col, c in enumerate(sorted(set(col))):
            el = [item[2] for item in l if item[0] == c]
            l2 = [(int((a.getp('area')[1] + a.getp('area')[3])*30),
                   a) for a in el]
            for row, item in enumerate(reversed(sorted(l2))):
                idx = p.get_iaxes(item[1])
                self._set_index_row_col_page(item[1], ipage, col, row, idx)

    def _set_index_row_col_page(self, a, ipage, col, row, idx):
        # a : fig_axes
        for name, child in a.get_children():
            if isinstance(child, FigMds):
                child.setvar('posvars', '_page=' + str(ipage) + ';' +
                                        '_column=' + str(col) + ';' +
                                        '_row=' + str(row) + ';' +
                                        '_index=' + str(idx))

    #
    #  methods for pool
    #
    def start_pool(self):
        #        ifigure.events.SendWorkerStartRequest(self.book, w=self, workers=self.workers)
        wx.CallAfter(self.workers.call_method, 'onStartWorker')

    def restart_worker(self):
        wx.CallAfter(self.workers.call_method, 'onReset')
        wx.CallAfter(self.workers.call_method, 'onStartWorker')
#        dprint1('restarting workers')
#        self.start_pool()

    def onResetWorker(self, evt):
        self.restart_worker()

    def eval_mdsdata_done(self, status=0):
        self._mode = 'apply'
        self._mds_exit_status = status
        if not self._no_window:
            self.bt_apply.SetLabel('Apply')
            self.bt_apply.Refresh()
            self.canvas.draw()
            self.SetStatusText('', 0)
        mds_thread = globals()['mds_thread']
        dprint1('Elapsed time since the last apply/abort req. ' +
                '{:.2f}'.format(time.time() - mds_thread._time) + 's')

    def _start_mds_threads(self):
        if globals()['mds_thread'] is None:
            start_mds_threads()
        #self.queue = globals()['mds_thread'].queue
        #self.mds_thread = globals()['mds_thread']
        from ifigure.mdsplus.event_listener import launch_listener
        launch_listener()
#        ifigure.events.SendThreadStartEvent(self.book, w=self, thread=self.mds_thread)

    def _run_eval_mdsshot(self):
        '''
        pre-process shot number field.
        if it starts from '='. do eval
        if it containes 'c', get the late shot number
        then split it, and return
        '''
        txt = str(self.txt_shot.GetValue())
        self.book.dwglobal.setvar('shot', txt)
        if txt.startswith('='):
            try:
                txt = eval(txt[1:], globals(), self._shot_dict)
            except:
                print(('Failed to evaluate string', txt[1:]))
                print(traceback.format_exc())
                raise
        return txt

    def get_globals_for_figmds(self, shot):
        vars = {}
        if not self.book.dwglobal.getvar('use_shot_global'):
            return vars
        for n in self._get_common_var_names():
            obj = self.book.get_child(name=n)
            for name, child in obj.get_children():
                if child.getvar('shot') == shot:
                    data = child.getvar('global_data')
                    for key in data:
                        vars[key] = data[key]
                    break
        return vars

    def _get_common_var_names(self):
        g_name = self.book.dwglobal.getvar('shot_global')
        return [name.strip() for name in g_name.split(',')]


class MDSScope(BookViewerFrame, ScopeEngine):
    ID_LISTENEVENT = wx.NewIdRef(count=1)
    ID_EXPORTBOOK_AS_NODATA = wx.NewIdRef(count=1)
    ID_EXPORTBOOK_NODATA = wx.NewIdRef(count=1)

    def __init__(self, *args, **kargs):
        parent = args[0]
        title = args[2]
        kargs["style"] = (wx.CAPTION |
                          wx.CLOSE_BOX |
                          wx.MINIMIZE_BOX |
                          wx.MAXIMIZE_BOX |
                          wx.RESIZE_BORDER)
        # |wx.FRAME_FLOAT_ON_PARENT)

        if "show_prop" in kargs:
            show_prop = kargs["show_prop"]
            del kargs["show_prop"]
        else:
            show_prop = False

        if "worker" in kargs:
            self.workers = kargs['worker']
            del kargs["worker"]
        else:
            self.workers = None

        # this is added not to have windows "always on parent"
        args2 = [x for x in args]
        args2[0] = None
        args = tuple(args2)
        ###

        kargs['isattachable'] = False
        kargs['isinteractivetarget'] = False
        super(MDSScope, self).__init__(*args, **kargs)
        ScopeEngine.__init__(self, no_window=False)

        if self.book is not None:
            from ifigure.mdsplus.fig_mdsbook import convert2figmdsbook2
            convert2figmdsbook2(self.book)
            self._make_all_nomargin()

        self.g = {}  # global variabls for mainthread scripting
        self._setting_dlg = None  # setting dialog
        self._title_mdsjob_count = 0
        self._mdsjob_count = 0
        self._cur_shot = 0
        self._mds_exit_status = 0
        self._figmds_list = []
        self._nticks = (10, 10)    # global ticks
        self._ID_RECENT=-1
        self.mpanalysis = False
        self._mpanalysis_mode = True
#        self.parallel_page = True
#        self.parallel_shot = True
#        self.parallel_sec = True
        self.init_beginning = True
        self.init_page = False
        self.init_shot = False
        self.init_sec = False
        self.debug_mode = False
        self.timer = None
        self.ipage = 0

        self.previous_shot_set = [[]]
        self.event_dict = {}

        self.InitUI(parent, title, show_prop)
        self.BindTreeDictEvents()
        self.adjust_frame_size()
        self.SetPosition((50, 50))
        from numpy import linspace
        self._shot_dict = {'linspace': linspace}
#        self.Thaw()

        proj = self.book.get_root_parent()
        if self.workers is None:
            #            print 'here', self.book._worker
            tmp_worker = self.book.find_by_full_path(self.book._worker)
            if tmp_worker is not None:
                self.workers = tmp_worker
            else:
                if proj.setting.has_child('mdsplus_worker'):
                    self.workers = proj.setting.mdsplus_worker
                else:
                    file = os.path.join(ifigure.__path__[0], 'add_on',
                                        'setting', 'module', 'mdsplus_worker.py')

                    workers = proj.setting.add_absmodule(file)
                    workers.rename('mdsplus_worker')
                    self.workers = workers
        self.book._worker = self.workers.get_full_path()

        p = SettingParser()
        p.set_rule('global_set', {}, nocheck=True)
        self.scope_setting = p.read_setting('mdsplus.scope_setting')
        if 'recent_file' in self.scope_setting:
            for item in self.scope_setting['recent_file'].split('\t'):
                RECENT_FILE.append(item)
        from ifigure.ifigure_config import rcdir, ifiguredir
        mname = 'mdsplus.fig_mds_startup_script'
        def_file = os.path.join(*([ifiguredir] + mname.split('.')))
        user_file = os.path.join(*([rcdir] + mname.split('.')))+'.py'
        if not os.path.exists(user_file):
            shutil.copy(def_file, user_file)
        self.startup_script = user_file
        dc = {}
        dg = {}
        from ifigure.mdsplus.fig_mds import read_scriptfile
        exec(read_scriptfile(self.startup_script), dg, dc)
        self.startup_values = dc

        self._start_mds_threads()  # start session runner and event listener

        self.start_pool()

        self.Bind(MDSSCOPE_EVT_MDSEVENT, self.onMDSEvent)
        self.open_engine()

        self.txt_shot.set_color_style(self.book.dwglobal.getvar('color_order'))
        self.make_event_dict()
        self.use_book_scope_param()

        if len(bitmaps) == 0:
            for icon in bitmap_names:
                from ifigure.ifigure_config import icondir as path
                path = os.path.join(path, '16x16', icon)
                if icon[-3:] == 'png':
                    im = wx.Image(path, wx.BITMAP_TYPE_PNG)
                    bitmaps[icon[:-4]] = im.ConvertToBitmap()
        self.Layout()
        self.Show()

    def InitUI(self, parent, title, show_prop):
        # A Statusbar in the bottom of the window
        self.sb = StatusBarSimple(self)
        self.SetStatusBar(self.sb)

        # define splitter panel tree

        # valid panel p1, p22, p121, p122
        self.gui_tree_panel = wx.Panel(self)
        self.shot_field_panel = wx.Panel(self)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL), 1)
        self.GetSizer().Add(self.gui_tree_panel, 1, wx.EXPAND)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.shot_field_panel, 1, wx.EXPAND)
        self.GetSizer().Add(hsizer, 0, wx.EXPAND, 2)

        self.gui_tree = PanelCheckbox(self.gui_tree_panel, wx.HORIZONTAL)
#        p1, p2 = self.gui_tree.add_splitter('v', 'h')

        # make all panels
        self.panel1 = self.gui_tree.add_panel(wx.Panel,
                                              "Figure", "Figure", 0)
        self.gui_tree.set_primary(self.panel1)
        self.gui_tree.hide_toggle_menu(self.panel1)
        self.property_editor = self.gui_tree.add_panel(property_editor,
                                                       "Property", "Property",
                                                       1, 'r', 0, wx.ALL | wx.EXPAND, 0)

        # self.script_editor.Hide()
        self.canvas = None
        self._rebuild_ifigure_canvas()
        self._link_canvas_property_editor()
        self.gui_tree.primary_client(self.canvas)
        from ifigure.mdsplus.mdsscope_canvas import MDSScopeCanvas
        self.canvas.__class__ = MDSScopeCanvas

        self.shot_field_panel.SetSizer(wx.BoxSizer(wx.HORIZONTAL), 1)

        txt = wx.StaticText(self.shot_field_panel, wx.ID_ANY, 'Shot:')
        txt._help_name = 'MDSscope.ShotField'
#        from ifigure.utils.edit_list import TextCtrlCopyPasteGenericHistory
#        self.txt_shot = TextCtrlCopyPasteGenericHistory(self.shot_field_panel,
#                                          wx.ID_ANY,
#                                          'c',
#                                          style=wx.TE_PROCESS_ENTER)
        from ifigure.mdsplus.shot_number_ctrl import ShotNumberCtrl
        self.txt_shot = ShotNumberCtrl(self.shot_field_panel,
                                       wx.ID_ANY)

        self.txt_shot._help_name = 'MDSscope.ShotField'
        self.bt_apply = wx.Button(self.shot_field_panel, wx.ID_ANY, 'Apply')

        self.shot_field_panel.GetSizer().Add(txt, 0, wx.ALIGN_CENTER)
        self.shot_field_panel.GetSizer().Add(self.txt_shot, 1,
                                             wx.EXPAND | wx.ALL, 0)
        self.shot_field_panel.GetSizer().Add(self.bt_apply, 0,
                                             wx.ALL, 1)

        # left button analyze a new shot
        self.bt_apply.Bind(wx.EVT_LEFT_UP, self.onApplyN)
        # right button allows user to select
        self.bt_apply.Bind(wx.EVT_RIGHT_UP, self.onApplyR)
        self.Bind(wx.EVT_TEXT_ENTER, self.onShot, self.txt_shot)
        # File Menu
        newmenu = wx.Menu()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "New Scope",
                      "Create a new book and open it in a scope",
                      self.onNewScope)
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "New Book",
                      "Create a new book and open it in a bookviewer",
                      self.onNewBook)
        self.add_menu(newmenu, wx.ID_ANY,
                      "Import DWSscope...", "Import DWScope file",
                      self.onImportDW)
        openmenu = wx.Menu()
        menu_AppendSubMenu(self.filemenu, wx.ID_ANY, 'Open', openmenu)
        self.add_menu(openmenu, wx.ID_OPEN,
                      "Book...",
                      "Import Book file (.bfz). Current book is deleted from project",
                      self.onLoadBook)
        self.add_menu(openmenu, wx.ID_ANY,
                      "Book in new window...",
                      "Import Book file (.bfz), New book data will be added to project",
                      self.onLoadBookNew)
        self.add_menu(openmenu, wx.ID_ANY,
                      "Import DWSscope...", "Import DWScope file",
                      self.onImportDW)
        self._recentmenu = wx.Menu()
        item = openmenu.AppendSubMenu(self._recentmenu, "Recent Import...")
        self._ID_RECENT = item.GetId()
        #menu_Append(openmenu, ID_RECENT,
        #            "Recent Import...", self._recentmenu)
        self.filemenu.AppendSeparator()
        self.append_save_project_menu(self.filemenu)
        self.export_book_menu = self.add_menu(self.filemenu, BookViewerFrame.ID_EXPORTBOOK,
                                              "Export Book", "Export Book",
                                              self.onExportBook)
        self.export_book_menu1 = self.add_menu(self.filemenu, MDSScope.ID_EXPORTBOOK_NODATA,
                                               "Export Book (w/o data)", "Export Book (data is not stored)",
                                               self.onExportBook1)
        self.export_book_menu.Enable(False)
        self.export_book_menu1.Enable(False)
        self.exportas_book_menu = self.add_menu(self.filemenu,
                                                BookViewerFrame.ID_EXPORTBOOK_AS,
                                                "Export Book As...", "Export Book",
                                                self.onExportBookAs)
        self.exportas_book_menu1 = self.add_menu(self.filemenu,
                                                 MDSScope.ID_EXPORTBOOK_AS_NODATA,
                                                 "Export Book As (w/o data)...",
                                                 "Export Book (data is not stored)",
                                                 self.onExportBookAs1)
#        self.exportas_book_menu.Enable(False)
        self.add_saveimage_menu(self.filemenu)
        self.filemenu.AppendSeparator()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Preference...", "Piescope preference...",
                      self.onAppPreference)

        self.filemenu.AppendSeparator()
        self.add_closemenu(self.filemenu)
        self.add_quitemenu(self.filemenu)

        # Edit Menu
        self.append_undoredo_menu(self.editmenu)
        self.editmenu.AppendSeparator()
        self.add_cutpaste_menu(self.editmenu)

        # plot menu
        self.add_std_plotmenu(self.plotmenu)
        self._lock_scale_mni = self.add_menu(self.plotmenu,
                                             BookViewerFrame.ID_LOCKSCALE,
                                             "Lock scale", "",
                                             self.onLockScale, kind=wx.ITEM_CHECK)
        self._lock_scale_mni.Check(False)

        # scope menu
        self.scopemenu = wx.Menu()
        self.menuBar.Append(self.scopemenu, "Scope")
        toolmenu = wx.Menu()
        menu_AppendSubMenu(self.scopemenu, wx.ID_ANY, 'Tools', toolmenu)
        self.add_menu(toolmenu, wx.ID_ANY,
                      "Generate multiple pages...", "Generate multiple pages from current page",
                      self.onGenerateMultipage)
        self.commonvar_menu = wx.Menu()
        menu_AppendSubMenu(toolmenu, wx.ID_ANY,
                    "Edit common variabls", self.commonvar_menu)
        self.add_menu(toolmenu, wx.ID_ANY,
                      "Reset MDSplus Workers", "Reset MDS session workers",
                      self.onResetWorker)
        self.add_menu(toolmenu, wx.ID_ANY,
                      "Reset Position Variables",
                      "Manual reset of position variables (_idx, _page, _col, _row)",
                      self.onResetPosvar)
        self.add_menu(self.scopemenu, wx.ID_ANY,
                      "Global setting...", "Global setting for mdsplus sessions...",
                      self.onSetting)
        self.add_menu(self.scopemenu, wx.ID_ANY,
                      "Scope Preference...", "Configuration...",
                      self.onScopePreference)
        self.add_menu(self.scopemenu, MDSScope.ID_LISTENEVENT,
                      "Listen Update Event", "listen mdsevent to update graphics",
                      self.onToggleListenEvent,
                      kind=wx.ITEM_CHECK)

        # help menu
        self.append_help_menu()

        # Help menu
        self.helpmenu.AppendSeparator()
        self.add_menu(self.helpmenu, wx.ID_HELP,
                      "About MDSScope...", "About MDSScope",
                      self.onAbout)

        self.gui_tree.append_menu(self.viewmenu)
        self.viewmenu.AppendSeparator()
        self.gui_tree.update_check()
        self.gui_tree.bind_handler(self)

#        if property_editor.screen_width is not None:
#           self.gui_tree.set_showhide([True, False])
        self.gui_tree.set_splitters()

        self.editmenu.AppendSeparator()
        self.add_bookmenus(self.editmenu, self.viewmenu)
        # add full screen to view menu
        self.viewmenu.AppendSeparator()
        self.add_menu(self.viewmenu, wx.ID_ANY,
                      "Full Screen", "switch to full screen mode",
                      self.onFullScreen)
        self.append_std_viewmenu2(self.viewmenu)

#        self.SetMenuBar(self.menuBar)

        self.property_editor.set_sizehint()
        self.gui_tree.toggle_panel(self.property_editor, show_prop)
        self.SetSize([600, 400])
        self.Layout()
        self.update_commonvar_menu()
        self.Show(True)
        self.set_accelerator_table()

        btn = ('reset_all', 'resetrange_all.png', 0,
               'reset to default range', self.onDefaultXYAll)
        self.canvas.toolbar.add_extra_group1_button(10, btn)
        # self.deffered_force_layout()

    def onUpdateUI(self, evt):
        if evt.GetId() in [MDSScope.ID_LISTENEVENT,
                           MDSScope.ID_EXPORTBOOK_AS_NODATA,
                           MDSScope.ID_EXPORTBOOK_NODATA]:
            if self.book is None:
                evt.Enable(False)
                return

        if evt.GetId() == MDSScope.ID_LISTENEVENT:
            evt.Enable(True)
            if self.book.getvar('mdsscope_listenevent'):
                evt.Check(True)
            else:
                evt.Check(False)
        elif evt.GetId() == MDSScope.ID_EXPORTBOOK_AS_NODATA:
            evt.Enable(True)
        elif evt.GetId() == MDSScope.ID_EXPORTBOOK_NODATA:
            if self.book.hasvar("original_filename"):
                fname = self.book.getvar("original_filename")
                if (os.path.exists(fname) and
                        os.access(fname, os.W_OK)):
                    evt.Enable(True)
                else:
                    evt.Enable(False)
            else:
                evt.Enable(False)
        elif evt.GetId() == self._ID_RECENT:
            m = self._recentmenu
            for item in m.GetMenuItems():
                m.DestroyItem(item)
            evt.Enable(True)
            mm = []
            for item in RECENT_FILE:
                if item == '':
                    continue

                def dummy(evt, file=item):
                    self.onImportDW(None, file=file)
                    evt.Skip()
                mm.append((item,
                           'Import ' + item,
                           dummy))
            if len(mm) > 0:
                for a, b, c in mm:
                    mmi = self.add_menu(m, wx.ID_ANY, a, b, c)
                m.AppendSeparator()
                mmi = self.add_menu(m, wx.ID_ANY, 'Reset Menu',
                                    'Reset recent file menu', self.onResetRecent)
            else:
                evt.Enable(False)
        else:
            super(MDSScope, self).onUpdateUI(evt)

    def update_exportas_menu(self):
        if self.export_book_menu is None:
            return
        if self.book is None:
            self.export_book_menu.Enable(False)
            self.export_book_menu1.Enable(False)
            return
        if self.book.hasvar("original_filename"):
            fname = self.book.getvar("original_filename")
            if (os.path.exists(fname) and
                    os.access(fname, os.W_OK)):
                self.export_book_menu.Enable(True)
                self.export_book_menu1.Enable(True)
        else:
            self.export_book_menu.Enable(False)
            self.export_book_menu1.Enable(False)

    def update_commonvar_menu(self):
        clabels = [mmi.GetItemLabelText() for mmi
                   in self.commonvar_menu.GetMenuItems()]
        if not self.book.dwglobal.getvar('use_shot_global'):
            nlabels = ['<common variabls is not used>']
        else:
            nlabels = self._get_common_var_names()
        if clabels == nlabels:
            return

        for mmi in self.commonvar_menu.GetMenuItems():
            self.commonvar_menu.DestroyItem(mmi)
#        self.commonvar_menu.Unbind(wx.EVT_MENU)
        for l in nlabels:
            def f(evt, self=self, label=l):
                self.onCommonVarEditMenu(evt, label)
            mmi = wx.MenuItem(self.commonvar_menu,
                              wx.ID_ANY, l)
            menu_AppendItem(self.commonvar_menu, mmi)
            if not self.book.dwglobal.getvar('use_shot_global'):
                mmi.Enable(False)
            self.Bind(wx.EVT_MENU, f, mmi)

    def onAbout(self, evt):
        dlg = wx.MessageDialog(self, "MDSScope \n"
                               "PieScope extention for MDSplus (v0.3)\n",
                               "about", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onResetRecent(self, evt):
        for i in range(len(RECENT_FILE)):
            RECENT_FILE.append('')

    def onNewScope(self, evt, veiwer=None):
        #        super(MDSScope, self).onNewBook(evt,
        #                                        viewer = MDSScope,
        #                                        basename='scope', worker=self.workers)
        book = self.book.get_root_parent().onAddBook(basename='scope')
        i_page = book.add_page()
        page = book.get_page(i_page)
        page.add_axes()
        page.realize()
        page.set_area([[0, 0, 1, 1]])
        book.setvar('mdsplus_server', self.book.getvar('mdsplus_server'))
        ifigure.events.SendOpenBookEvent(book, w=self,
                                         viewer=MDSScope, worker=self.workers)
        ifigure.events.SendChangedEvent(book, w=self)

    def onNewBook(self, evt, veiwer=None):
        from ifigure.widgets.book_viewer import BookViewer
        super(MDSScope, self).onNewBook(evt,
                                        viewer=BookViewer)

    def onLoadBook(self, evt, mode=0, proj=None, file=''):
        import time
        super(MDSScope, self).onLoadBook(evt,
                                         mode=mode, proj=proj, file=file)
        self.prepare_dwglobal(self.book)
        self.txt_shot.SetValue(self.book.dwglobal.getvar('shot'))
        self.mpanalysis = self.book.dwglobal.getvar('mpanalysis')
        self.update_commonvar_menu()
        for page in self.book.walk_page():
            for obj in page.walk_tree():
                if isinstance(obj, FigMds):
                    obj.set_suppress_all(True)
        self.make_event_dict()
        from ifigure.mdsplus.fig_mdsbook import convert2figmdsbook
        convert2figmdsbook(self.book)
        self.use_book_scope_param()
        self._figmds_list = []
        wx.CallAfter(self.book.realize)
        wx.CallAfter(self.draw)

    def onLoadBookNew(self, evt):
        super(MDSScope, self).onLoadBookNew(evt,
                                            viewer=MDSScope, worker=self.workers)

    def onEditSignal(self, evt):
        pass

    def add_page(self, *argc, **kargs):
        ret = super(MDSScope, self).add_page(*argc, **kargs)
        self._make_all_nomargin()
        return ret

    def show_page(self, ipage=0, last=False, first=False):
        super(MDSScope, self).show_page(ipage=ipage, last=last, first=first)
#        for page in self.book.walk_page():
        self.prepare_dwglobal(self.book)
        self.make_event_dict()
#        from ifigure.mdsplus.fig_mdsbook import convert2figmdsbook
#        convert2figmdsbook(self.book)

    def make_event_dict(self):
        from ifigure.mdsplus.event_listener import connect_listener, disconnect_listener
        server = self.book.getvar('mdsplus_server')
        s, p, t = parse_server_string(server)

        event_dict = {}
        # no event if connection is not direct
#        if s == 'direct' and self.book.getvar('mdsscope_listenevent'):
        if self.book.getvar('mdsscope_listenevent'):
            g_event = self.book.dwglobal.getvar('event')
            if (g_event is not None and g_event != ''):
                event_dict[g_event] = []
            for k, page in enumerate(self.book.walk_page()):
                for ax in page.walk_axes():
                    for name, child in ax.get_children():
                        if not isinstance(child, FigMds):
                            continue
                        event_name = child.getvar('event')
                        if (event_name is not None and event_name != ''):
                            if not event_name in event_dict:
                                event_dict[event_name] = []
                            event_dict[event_name].append(weakref.ref(ax))
                        elif (g_event is not None and g_event != ''):
                            event_dict[g_event].append(weakref.ref(ax))

        for key in self.event_dict:
            if not key in event_dict:
                disconnect_listener(self, key)
        for key in event_dict:
            if not key in self.event_dict:
                connect_listener(self, key)
        self.event_dict = event_dict

    def onResetPosvar(self, evt):
        for ipage, p in enumerate(self.book.walk_page()):
            self.set_index_col_row_page(ipage)

    #
    #  methods for pool
    #
    def start_pool(self):
        #        ifigure.events.SendWorkerStartRequest(self.book, w=self, workers=self.workers)
        wx.CallAfter(self.workers.call_method, 'onStartWorker')

    def restart_worker(self):
        wx.CallAfter(self.workers.call_method, 'onReset')
        wx.CallAfter(self.workers.call_method, 'onStartWorker')
#        dprint1('restarting workers')
#        self.start_pool()

    def onResetWorker(self, evt):
        self.restart_worker()

    def use_proxy(self):
        return self.workers.eval('setting')['connection_type'] == 'proxy'
    #
    #  GUI event handler
    #

    def onImportDW(self, evt, file=''):
        def merge_globals(param, globals):
            keys = ('title', 'experiment', 'default_node', 'x', 'y')
            gs = param.getvar('globalsets')
            for key in keys:
                if key in globals:
                    gs[key][0] = globals[key]
                    del globals[key]
                else:
                    gs[key][0] = ''
            for key in globals:
                param.setvar(key, globals[key])

        from ifigure.mdsplus.import_dw import import_dw
        setting, global_param, plots, filename, geom = import_dw(file=file)
        if setting is None:
            return

        if not filename in RECENT_FILE:
            RECENT_FILE.append(filename)
        self.book.setvar('global_tdi', setting['title'])
        self.book.setvar('global_tdi_event', setting['title_event'])
        self.book._show_tdi_title = False
        if self._setting_dlg is not None:
            self._setting_dlg.Destroy()
            self._setting_dlg = None
        cr = [len(p) for p in plots]
        ps = []
        for p in plots:
            ps = ps + p

        if self.book.has_child('dwglobal'):
            param = self.book.get_child(name='dwglobal')
            param.destroy()
        param = self.prepare_dwglobal(self.book)
        merge_globals(param, global_param)

        param.setvar('setting', setting)

        fig_page = self.get_page()
        for ax in fig_page.walk_axes():
            ax.destroy()
        self.set_section(cr)

#        fig_page.set_nomargin(True)
        self._make_all_nomargin()
        for iax in range(sum(cr)):
            ax = self.get_axes(ipage=None, iaxes=iax)
            ax._yaxis[0].mode = [False, False, True]
            figmds = FigMds(dwplot=ps[iax])
            ax.add_child(ax.get_next_name('mds'), figmds)
#           ax.apply_nomargin_mode()
            figmds.realize()
            if 'x.grid_lines' in ps[iax] and int(ps[iax]['x.grid_lines']) != 0:
                for x in ax._xaxis:
                    x.ticks = ps[iax]['x.grid_lines']
            if 'y.grid_lines' in ps[iax] and int(ps[iax]['y.grid_lines']) != 0:
                for y in ax._yaxis:
                    y.ticks = ps[iax]['y.grid_lines']
            if 'global_defaults' in ps[iax]:
                bit = int(ps[iax]['global_defaults'])
                if bit & 2**10 != 0:
                    figmds._var_mask.append('x')
                if bit & 2**11 != 0:
                    figmds._var_mask.append('y')
                # set grid
                v = ax.get_grid()
                v[0] = bit & 2**5 != 0
                ax.set_grid(v)
                v = ax.get_grid()
                v[1] = bit & 2**6 != 0
                ax.set_grid(v)

#        self._handle_apply_abort()
        self.draw()
        ax = self.get_axes(ipage=None, iaxes=None)

        # change filename...
        name = str(os.path.basename(filename)[:-4])

        self.book.setvar('dwscope_filename', name)
        from ifigure.utils.cbook import is_safename
        if not is_safename(name):
            while not is_safename(name):
                ret, name = dialog.textentry(self,
                                             'Enter a new book name ( ' +
                                             name + ' is not valid name)',
                                             'DWscope file was imported', name)
                if not ret:
                    return
        if not self.book.get_parent().has_child(name):
            self.book.rename(name)
        else:
            name = self.book.get_parent().get_next_name(name+'_')
            ret = dialog.message(self,
                                 'Do you rename Book to '+name + '?',
                                 'DWscope file was imported',
                                 4, icon=wx.ICON_QUESTION)
            if ret == 'ok':
                self.book.rename(name)
        self.make_event_dict()
        self._figmds_list = []

        for ax in fig_page.walk_axes():
            ax.refresh_nticks()

        ifigure.events.SendChangedEvent(self.book, w=self)
        self.SetSize(geom)

    def onApply(self, evt):
        if not self.check_valid_worker_type():
            return
        self.debug_mode = False
        self._handle_apply_abort()
        evt.Skip()

    def onApplyN(self, evt):
        if not self.check_valid_worker_type():
            return
        self.debug_mode = False
        self._handle_apply_abort(allshot=False)
        evt.Skip()

    def onApplyD(self, evt):
        if not self.check_valid_worker_type():
            return
        self.debug_mode = True
#        wx.GetApp().TopWindow.open_editor_panel()
        self._handle_apply_abort()
        evt.Skip()

    def onApplyR(self, evt):
        if not self.check_valid_worker_type():
            return
        self.debug_mode = False
        menu = wx.Menu()
        f1 = menu.Append(wx.ID_ANY, 'Update All', 'update all shots')
        self.Bind(wx.EVT_MENU, self.onApply, f1)
        f2 = menu.Append(wx.ID_ANY, 'Update New Shots', '')
        self.Bind(wx.EVT_MENU, self.onApplyN, f2)
        f3 = menu.Append(wx.ID_ANY, 'Debug', '')
        self.Bind(wx.EVT_MENU, self.onApplyD, f3)
        evt.GetEventObject().PopupMenu(menu, evt.GetPosition())
        menu.Destroy()
        evt.Skip()

    def check_valid_worker_type(self):
        if self.workers.is_suppress():
            dlg = wx.MessageDialog(self, '\n'.join([
                "Workers are not active! ",
                "Please activate worker in project viewer."]),
                "Configuration Error", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False

        server = self.book.getvar('mdsplus_server')
        s, p, t = parse_server_string(server)
        if (isinstance(MDSWorkerPool.pool, MDSTHWorkerPool) and
            s.upper() == 'DIRECT' and not self.use_proxy() and
                MDSWorkerPool.pool.num != 1):
            dlg = wx.MessageDialog(self, '\n'.join([
                "Direct connection mode works only for Mulitprocessing MDSplus worker.",
                "Or. use MDSconnect with threaded MDSplus workers"]),
                "Configuration Error", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
#            self.book.setvar('mdsplus_server',
#                             'alcdata.psfc.mit.edu::CMOD')

            return False
        return True

    def onShot(self, evt):
        if self._mode == 'apply':
            self.debug_mode = False
            self._handle_apply_abort(allshot=False)

    def eval_mdsdata_done(self, status=0):

        self._mode = 'apply'
        self._mds_exit_status = status
        self.bt_apply.SetLabel('Apply')
        self.bt_apply.Refresh()
        # Yield is here to perform deffered drawing
        # before calculate elapsed time
#        wx.GetApp().Yield(True)
        self.canvas.draw()
        self.SetStatusText('', 0)
        mds_thread = globals()['mds_thread']
        dprint1('Elapsed time since the last apply/abort req. ' +
                '{:.2f}'.format(time.time() - mds_thread._time) + 's')

    def _handle_apply_abort(self, allshot=True, figaxes='all', do_apply=False):
        if not self.check_valid_worker_type():
            return
        mds_thread = globals()['mds_thread']
        mds_thread._time = time.time()
        if self._mode == 'apply' or do_apply:
            self.bt_apply.SetLabel('Abort')
            self.bt_apply.Refresh()
#        self.erase_mdsdata()
            self._mode = 'abort'
            if (len(self.txt_shot._key_history_st1) == 0 or
                self.txt_shot._key_history_st1[-1] !=
                    str(self.txt_shot.GetValue())):
                self.txt_shot._key_history_st1.append(
                    str(self.txt_shot.GetValue()))
            try:
                self.eval_mdsdata(allshot, figaxes=figaxes)
            except:
                dprint1('Error happend while evaluating mdsplus data')
                dprint1(traceback.format_exc())
                self.eval_mdsdata_done(status=-1)
        else:
            #            dprint1('abort requested')
            c = message('abort', (self,))
            globals()['mds_thread'].queue.put(c)
#            self.queue.put(c)
#            while not self.mds_thread._finished:
#                time.sleep(0.1)

    def onSetting(self, evt):
        from ifigure.mdsplus.dlg_setting2 import DlgMdsSetting, callback

        if self._setting_dlg is None:
            dlg = DlgMdsSetting(self, self.scope_setting,
                                self.book.dwglobal,
                                self.book.getvar('mdsplus_server'),
                                self.book.getvar('mdsscript_main'),
                                cb=self.callback_setting)

            self._setting_dlg = dlg
            dlg.Fit()
        else:
            self._setting_dlg.Raise()

    def callback_setting(self, value):
        from ifigure.mdsplus.dlg_setting2 import DlgMdsSetting, callback
        callback(self, value,  self.scope_setting, self.book.dwglobal)
        self.book.dwglobal.setvar('mpanalysis', self.mpanalysis)

        if self.book.dwglobal.getvar('use_shot_global'):
            g_name = self.book.dwglobal.getvar('shot_global')
            if g_name.strip() == '':
                g_name = 'common_vars'
                self.book.dwglobal.setvar('shot_global', g_name)
            for name in self._get_common_var_names():
                flag = False
                if not self.book.has_child(name):
                    param = FigMdsData()
                    self.book.add_child(name, param)
                    flag = True
            if flag:
                ifigure.events.SendChangedEvent(self.book, w=self)
        self.update_commonvar_menu()
        self.make_event_dict()

    def set_nticks(self, *args):
        nxticks = args[0]
        nyticks = args[1]
        for p in self.book.walk_page():
            p.set_nticks(nxticks, nyticks)

    def onScopePreference(self, evt):
        from ifigure.utils.edit_list import DialogEditList

        auto_grid = self.book.getvar('mdsscope_autogrid')
        nticks = self.get_page().getp('nticks')
        nxticks = nticks[0]
        nyticks = nticks[1]
        defx, defy = self._get_page_default_range()

        def make_str(x):
            try:
                y = float(x)
                return str(x)
            except:
                return ''
        l = [["Lines Color Order", self.book.dwglobal.getvar()['color_order'], 22, {}],
             [None, auto_grid, 3,
              {"text": "Autoset grid", "noindent": None}],
             ["Min X", make_str(defx[0]), 0, {'noexpand': True}],
             ["Max X", make_str(defx[1]), 0, {'noexpand': True}],
             ["Min Y", make_str(defy[0]), 0, {'noexpand': True}],
             ["Max Y", make_str(defy[1]), 0, {'noexpand': True}],
             ["Max XTick Count", str(nxticks), 0, {'noexpand': True}],
             ["Max YTick Count", str(nyticks), 0, {'noexpand': True}],
             ]

        tips = ['Color order in plot',
                'Grid is set automatically in all panels',
                'Default X min',
                'Default X max',
                'Default Y min',
                'Default Y max',
                'Default maximum number of xticks',
                'Default maximum number of yticks', ]

        value = DialogEditList(l, parent=self,
                               title='Scope Preference', tip=tips,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if not value[0]:
            return
        self.book.dwglobal.getvar()['color_order'] = value[1][0]
        self.book.setvar('mdsscope_autogrid', value[1][1])
#        try:
        if (nxticks != int(value[1][6]) or
                nyticks != int(value[1][7])):
            nxticks = int(value[1][6])
            nyticks = int(value[1][7])
            self.set_nticks(nxticks, nyticks)
            wx.CallAfter(self.canvas.draw)
        self.book.setvar('mdsscope_nticks', [nxticks, nyticks])

#        except:
#           pass
        def make_str(x):
            try:
                y = float(x)
                return str(x)
            except:
                return None
        self.book.dwglobal.setvar('xmin', make_str(value[1][2]))
        self.book.dwglobal.setvar('xmax', make_str(value[1][3]))
        self.book.dwglobal.setvar('ymin', make_str(value[1][4]))
        self.book.dwglobal.setvar('ymax', make_str(value[1][5]))
        self.txt_shot.set_color_style(self.book.dwglobal.getvar('color_order'))
        self.txt_shot.Refresh()
    #
    #   ifigure event handler
    #

    def onTD_ShowPage(self, evt):
        if not evt.BookViewerFrame_Processed:
            super(MDSScope, self).onTD_ShowPage(evt)
            evt.BookViewerFrame_Processed = True
            evt.SetEventObject(self)
        evt.Skip()

    def viewer_canvasmenu(self):
        if self.canvas.axes_selection is None:
            return []
        if self.canvas.axes_selection() is None:
            return []
        m1 = [('Add MDS Session',  self.onAddFigMds, None), ]

        m2 = []
        figmdss = [child for name, child in self.canvas.axes_selection().figobj.get_children()
                   if isinstance(child, FigMds)]
        if len(figmdss) > 1:
            m2.append(('+Edit Session', None, None))
            tt = ''
        else:
            tt = 'Edit Session : '

        for child in figmdss:
            def f(evt, figmds=child, viewer=self):
                self.canvas.unselect_all()
                if len(figmds._artists) != 0:
                    self.canvas.add_selection(figmds._artists[0])

#                ifigure.events.SendSelectionEvent(figmds, viewer.canvas,
#                                                  viewer.canvas.selection
                    sel = [weakref.ref(figmds._artists[0])]
                    ifigure.events.SendSelectionEvent(figmds, self, sel)
                evt.SetEventObject(viewer)
                figmds.onDataSetting(evt)
            m2.append((tt + child.name, f, None))
        if len(figmdss) > 1:
            m2.append(('!', None, None))

        m3 = [('Update This Panel',  self.onUpdatePanel, None),
              ('---', None, None), ]
        return m2 + m1 + m3

    def extra_canvas_range_menu(self):
        if self.canvas.axes_selection() is None:
            #            return [('Use default X (all)', self.onDefaultXAll, None),
            #                   ('Use default Y (all)', self.onDefaultYAll, None),]
            return [('Reset all scale', self.onDefaultXYAll, None), ]
        else:
            #            return [('Use default X', self.onDefaultX, None),
            #                    ('Use default Y', self.onDefaultY, None),
            #                    ('Use default X (all)', self.onDefaultXAll, None),
            #                    ('Use default Y (all)', self.onDefaultYAll, None),]
            return [('Reset scale', self.onDefaultXY, None),
                    ('Reset all scale', self.onDefaultXYAll, None, bitmaps['resetrange_all']), ]

    def _find_first_figmds(self, axes=None):
        if axes is None:
            if self.canvas.axes_selection is None:
                return None, None
            if self.canvas.axes_selection() is None:
                return None, None
            axes = self.canvas.axes_selection().figobj
        for name, child in axes.get_children():
            if isinstance(child, FigMds):
                return child, axes
        return None, None

    def _apply_default_range(self, axes, name, range):
        v = axes.get_axrangeparam(axes._artists[0], name)
        v[1] = False
        v[2] = range
        requests = {axes: [(name, v)]}
        self.canvas.send_range_action(requests,
                                      menu_name='use default '+name+'range')

    def _get_page_default_range(self):
        try:
            x = [float(self.book.dwglobal.getvar('xmin')),
                 float(self.book.dwglobal.getvar('xmax'))]
        except:
            x = [None, None]
        try:
            y = [float(self.book.dwglobal.getvar('ymin')),
                 float(self.book.dwglobal.getvar('ymax'))]
        except:
            y = [None, None]
        return x, y

    def onDefaultX(self, evt):
        defx, defy = self._get_page_default_range()
        figmds, axes = self._find_first_figmds()
        if figmds is None:
            return
        range = figmds._default_xyrange['value'][0]
        if range[0] is None:
            range = defx
        if range[0] is None:
            return
        self._apply_default_range(axes, 'x', range)

    def onDefaultY(self, evt):
        defx, defy = self._get_page_default_range()
        figmds, axes = self._find_first_figmds()
        if figmds is None:
            return
        range = figmds._default_xyrange['value'][1]
        if range[0] is None:
            range = defy
        if range[0] is None:
            return
        self._apply_default_range(axes, 'y', range)

    def onDefaultXY(self, evt=None):
        defx, defy = self._get_page_default_range()
        figmds, axes = self._find_first_figmds()
        if figmds is None:
            return
        xrange = figmds._default_xyrange['value'][0]
        yrange = figmds._default_xyrange['value'][1]
        if xrange[0] is None:
            xrange = defx
        if yrange[1] is None:
            yrange = defy
        r = []
        if xrange[0] is not None:
            v = axes.get_axrangeparam(axes._artists[0], 'x')
            v[1] = False
            v[2] = xrange
            r.append(('x', v))
        if xrange[1] is not None:
            v = axes.get_axrangeparam(axes._artists[0], 'y')
            v[1] = False
            v[2] = yrange
            r.append(('y', v))
        if len(r) == 0:
            return
        requests = {axes: r}
        self.canvas.send_range_action(requests,
                                      menu_name='use default range')

    def onDefaultXAll(self, evt):
        defx, defy = self._get_page_default_range()
        figpage = self.canvas._figure.figobj
        requests = {}
        for axes in figpage.walk_axes():
            figmds, axes = self._find_first_figmds(axes=axes)
            if figmds is None:
                continue
            range = figmds._default_xyrange['value'][0]
            if range[0] is None:
                range = defx
            if range[0] is None:
                continue
            v = axes.get_axrangeparam(axes._artists[0], 'x')
            v[1] = False
            v[2] = range
            requests[axes] = [('x', v)]
        self.canvas.send_range_action(requests,
                                      menu_name='apply defaul xranges')

    def onDefaultYAll(self, evt):
        defx, defy = self._get_page_default_range()
        figpage = self.canvas._figure.figobj
        requests = {}
        for axes in figpage.walk_axes():
            figmds, axes = self._find_first_figmds(axes=axes)
            if figmds is None:
                continue
            range = figmds._default_xyrange['value'][1]
            if range[0] is None:
                range = defy
            if range[0] is None:
                continue
            v = axes.get_axrangeparam(axes._artists[0], 'y')
            v[1] = False
            v[2] = range
            requests[axes] = [('y', v)]
        self.canvas.send_range_action(requests,
                                      menu_name='apply default xyanges')

    def onDefaultXYAll(self, evt=None):
        defx, defy = self._get_page_default_range()
        figpage = self.canvas._figure.figobj
        requests = {}
        for axes in figpage.walk_axes():
            figmds, axes = self._find_first_figmds(axes=axes)
            if figmds is None:
                continue
            xrange = figmds._default_xyrange['value'][0]
            yrange = figmds._default_xyrange['value'][1]
            if xrange[0] is None:
                xrange = defx
            if yrange[0] is None:
                yrange = defy

            r = []
            for name, value in (('x', xrange), ('y', yrange)):
                if value[0] is None:
                    continue
                v = axes.get_axrangeparam(axes._artists[0], name)
                v[1] = False
                v[2] = value
                r.append((name, v))
            if len(r) != 0:
                requests[axes] = r
        self.canvas.send_range_action(requests,
                                      menu_name='apply default xyanges')

    def onUpdatePanel(self, evt):
        ax = self.canvas.axes_selection()
        if ax is None:
            return
        self._handle_apply_abort(allshot=True, figaxes=[ax.figobj])
        evt.Skip()

    def onAddFigMds(self, evt):
        if self.canvas.axes_selection is None:
            return []
        if self.canvas.axes_selection() is None:
            return []

        ax = self.canvas.axes_selection()
        obj = FigMds()
        name = ax.figobj.get_next_name(obj.get_namebase())
        ax.figobj.add_child(name, obj)
        obj.realize()
        ifigure.events.SendPVAddFigobj(ax.figobj, useProcessEvent=True)
        ifigure.events.SendChangedEvent(
            ax.figobj, w=self.canvas, useProcessEvent=True)
        self.canvas.unselect_all()
        if len(obj._artists) != 0:
            self.canvas.add_selection(obj._artists[0])
#                     figmds.onDataSetting(evt)
            ifigure.events.SendSelectionEvent(obj, self.canvas,
                                              self.canvas.selection)
        obj.onDataSetting(evt)
#        if len(obj._artists) != 0:
#            self.canvas.add_selection(obj._artists[0])
#            ifigure.events.SendSelectionEvent(obj, self.canvas,
#                                              self.canvas.selection)

    def set_window_title(self):
        super(MDSScope, self).set_window_title()
        if self.book is None:
            return
        title = self.GetTitle()
        name = self.book.getvar('original_filename')
        if name is None:
            name = self.book.getvar('dwscope_filename')
            if name == '' or name is None:
                name = self.book.name
            else:
                name = name + '.dat [Imported]'
        else:
            name = os.path.basename(name)
        title = name + ': ' + title
        self.SetTitle(title)

    def onGenerateMultipage(self, evt):
        from ifigure.utils.edit_list import DialogEditList

        txt = "on" if self.mpanalysis else "off"
        txt2 = '1' if not self._mpanalysis_mode else str(self.book.num_page())
        list6 = [["Use multipage analysis",
                  "on", 1, {"values": ["on", "off"]}],
                 #                 ["Duplicate from", str(self.ipage), 0, None],
                 ["Number of pages", txt2, 0, None],
                 [None, self._mpanalysis_mode,  3,
                  {"text": "Erase exiting pagesd",
                   "noindent": None}], ]

        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=self,)

        if value[0] is True:
            self.mpanalysis = (str(value[1][0]) == "on")
            self.book.dwglobal.setvar('mpanalysis', self.mpanalysis)
            ref_ipage = self.ipage
            nump = int(value[1][1])
        else:
            return
        if nump == 0:
            print('number of pages should be greater than 1')
            return
        self.canvas.unselect_all()
        self.canvasaxes_selection = cbook.WeakNone()
        self.show_page(0)
        p = self.get_page(ref_ipage)

        from ifigure.ifigure_config import rcdir
        fname = os.path.join(rcdir, 'mdsscope_'+str(os.getpid())+'_tmp.data')
        self._mpanalysis_mode = value[1][2]

        pgb = dialog.progressbar(self,
                                 'generating all page data.', 'Please wait...',
                                 nump)
        pgb.Update(0)
        if value[1][2]:
            if p.hasvar('group_id'):
                gid = p.getvar('group_id')
            else:
                gid = self._new_grp_id()
            d = self._set_save_mode(1)
            p.save_subtree(fname, compress=False)
            self._set_save_mode(0, d)
            pages = [child for child in self.book.walk_page()]
            for page in pages:
                page.destroy()
            for i in range(nump):
                obj = self.book.load_subtree(fname, compress=False)
                if obj.name != 'page'+str(i+1):
                    obj.rename('page'+str(i+1))
                # obj.realize()
                obj.setvar('group_id', gid)
                obj._status = 'group '+str(gid+1)
                pgb.Update(i)

        else:
            for child in self.book.walk_page():
                child.rename(child.name + 'tmp')
            d = self._set_save_mode(1)
            p.save_subtree(fname, compress=False)
            self._set_save_mode(0, d)
            if p.hasvar('group_id'):
                gid = p.getvar('group_id')
                pages = [child for child in self.book.walk_page()]
                for page in pages:
                    if (gid == page.getvar('group_id') and
                            page is not p):
                        page.destroy()
            else:
                gid = self._new_grp_id()
                p.setvar('group_id', gid)
                p._status = 'group '+str(gid+1)
            ip = p.get_ichild()
            for i in range(nump)-1:
                obj = self.book.load_subtree(fname, compress=False)
                obj.rename(obj.name + 'tmptmp')
                obj.setvar('group_id', gid)
                obj._status = 'group '+str(gid+1)
                ip2 = obj.get_ichild()
                self.book.move_child(ip2, ip+1)
                pgb.Update(i)
            for i, child in enumerate(self.book.walk_page()):
                child.rename('page'+str(i+1))
        pgb.Destroy()
        os.remove(fname)

        # realize all page except for reference page
        for ipage, page in enumerate(self.book.walk_page()):
            self.set_index_col_row_page(ipage)
            if page is not p:
                page.realize()

        ipage = self.book.i_page(obj)
#        self.show_page(ipage)
        self.show_page(0)
        ifigure.events.SendChangedEvent(self.book, w=self.canvas)
#        ifigure.events.SendShowPageEvent(obj, w=self.canvas)

    def _new_grp_id(self):
        id = [child.getvar('group_id') for child in
              self.book.walk_page() if child.hasvar('group_id')]
        id = [-1] + id
        return numpy.nanmax(id)+1

    def onCommonVarEditMenu(self, evt, label):
        evt.SetEventObject(self.canvas)
#        print label
        g = self.book.get_child(name=label)
        # print g
        g.onDataSetting(evt)

    def onExportBook(self, evt):
        self.onSaveBook(evt)

    def onExportBookAs(self, evt):
        self.onSaveBookAs(evt)

    def onExportBook1(self, evt):
        d = self._set_save_mode(1)
        self.onSaveBook(evt)
        self._set_save_mode(0, d)

    def onExportBookAs1(self, evt):
        d = self._set_save_mode(1)
        self.onSaveBookAs(evt)
        self._set_save_mode(0, d)

    def onWindowClose(self, evt=None):
        from ifigure.ifigure_config import iFigureConfig
        self.close_engine()
        self.scope_setting['recent_file'] = '\t'.join(list(RECENT_FILE))
        p = SettingParser()
        p.write_setting('mdsplus.scope_setting',
                        self.scope_setting)

        # below is the same as standard book viewer
        super(MDSScope, self).onWindowClose(evt)

    def onPaste(self, e):
        ret = super(MDSScope, self).onPaste(e)
        for name in ret:
            obj = self.book.find_by_full_path(name)
            if obj.hasp('loaded_dwglobal'):
                self.do_global_copy(obj)

    def do_global_copy(self, obj):
        param = obj.getp('loaded_dwglobal')
        if param is None:
            return

        d = param['globalsets']
        d2 = self.book.dwglobal.getvar('globalsets')
        for key in d:
            for a, b in zip(d[key], d2[key]):
                if a != b:
                    break
        else:
            return
        ret = dialog.message(self,
                             'Pasted object has different global setting.\n Do you overwrite the existing setting?\n',
                             'Pasting MDSplus object... ',
                             2, icon=wx.ICON_QUESTION)
        if ret == 'ok':
            self.book.dwglobal.setvar('globalsets', d)

    def onFullScreen(self, evt=None, value=True):
        '''
        Full Screen mode in MDSplus
           1) show tool palette
           2) does not use spacer (aspect ratio is not preserved)
        '''
        if value:
            if self.isPropShown():
                self.toggle_property()
            xd, yd = wx.GetDisplaySize()
            xc, yc = self.canvas.canvas.bitmap.GetSize()
            ratio = min([float(xd)/float(xc), float(yd)/float(yc)])
#             w = None
#             h = None
            for p in self.book.walk_page():
                p.set_figure_dpi(int(p.getp('dpi')*ratio))
#             self.canvas.show_spacer(w=0, h=0)
#             self.canvas.full_screen(True)
            self.ShowFullScreen(True)
            self.canvas.turn_on_key_press()
        else:
            for p in self.book.walk_page():
                p.set_figure_dpi(p.getp('dpi'))
#             self.canvas.hide_spacer()
#             self.canvas.full_screen(False)
            self.canvas.turn_off_key_press()
            self.ShowFullScreen(False)

    def get_globals_for_figmds(self, shot):
        vars = {}
        if not self.book.dwglobal.getvar('use_shot_global'):
            return vars
        for n in self._get_common_var_names():
            obj = self.book.get_child(name=n)
            for name, child in obj.get_children():
                if child.getvar('shot') == shot:
                    data = child.getvar('global_data')
                    for key in data:
                        vars[key] = data[key]
                    break
        return vars

    def onMDSEvent(self, e):
        txt = str(self.txt_shot.GetValue())
        print(('MDS event', e.mdsevent_name, self))
        self.check_valid_worker_type()

        if (txt.startswith('=') or
                txt.find('c') == -1):
            return
        if e.mdsevent_name in self.event_dict:

            objs = [r() for r in self.event_dict[e.mdsevent_name]]
            for x in objs:
                if not x in self._figmds_list:
                    self._figmds_list.append(x)
            wx.CallAfter(self.loadshot_after_mdsevent)

    def onToggleListenEvent(self, evt):
        v = self.book.getvar('mdsscope_listenevent')
        self.book.setvar('mdsscope_listenevent', (not v))
        self.make_event_dict()

    def loadshot_after_mdsevent(self):
        if self._mode == 'apply':
            mm = [x for x in self._figmds_list if x.get_figbook() is self.book]
            self._figmds_list = []
            print('updating '+str(len(mm)) + ' panels')
            self._handle_apply_abort(allshot=True,
                                     figaxes=mm)
        else:
            pass
#            if len(self._figmds_list) != 0:
#                print 'calling later'
#                wx.CallLater(0.1, self.loadshot_after_mdsevent)

    def show_mdsjob_count(self):
        if (self._title_mdsjob_count ==
                self._mdsjob_count):
            return

        if self._mdsjob_count != 0:
            txt = ' --'+'{:3d}'.format(self._mdsjob_count) + '--'
        else:
            txt = ''
        work_on_title = False
        if work_on_title:
            title = self.GetTitle()
            if self._title_mdsjob_count != 0:
                title = title[:-8]
            title = title + txt
            self.SetTitle(title)
        self._title_mdsjob_count = self._mdsjob_count
        self.SetStatusText(txt, 0)

    def set_book_scope_param(self):
        w = self.txt_shot
        v = (w.GetValue(),
             w._key_history_st1,
             w._key_history_st2,)
        self.book._scope_param = v

    def use_book_scope_param(self):
        if hasattr(self.book, '_scope_param'):
            param = self.book._scope_param
            w = self.txt_shot
            w.SetValue(param[0])
            w._key_history_st1.extend(param[1])
            w._key_history_st2.extend(param[2])

    def _get_common_var_names(self):
        g_name = self.book.dwglobal.getvar('shot_global')
        return [name.strip() for name in g_name.split(',')]

    def _set_save_mode(self, mode, ret=None):
        return self.book.set_compact_savemode(mode, ret=ret)

    def _make_all_nomargin(self):
        for page in self.book.walk_page():
            page.set_nomargin(True)
            for ax in page.walk_axes():
                ax.apply_nomargin_mode()

    def _duplicate_page(self, nump, p):
        # duplicate p nump times and insert
        # them after p
        for k, o in enumerate(self.book.walk_page()):
            o.rename('page'+str(k+1))
        ipage = self.book.i_page(p)+1
        while ipage < self.book.num_page():
            o = self.book.get_page(ipage)
            o.rename('tmp'+str(ipage))
            ipage = ipage + 1
        ipage = self.book.i_page(p)+1
        while ipage < self.book.num_page():
            o = self.book.get_page(ipage)
            o.rename('page'+str(ipage))
            ipage = ipage + 1

        pgb = dialog.progressbar(self,
                                 'generating all page data.', 'Please wait...',
                                 nump)
        pgb.Update(0)
        if p.hasvar('group_id'):
            gid = p.getvar('group_id')
        else:
            gid = self._new_grp_id()
            p.setvar('group_id', gid)
            p._status = 'group '+str(gid+1)

        from ifigure.ifigure_config import tempdir
        fname = os.path.join(tempdir, 'mdsscope_' +
                             p.get_full_path()+'_tmp.data')

        d = self._set_save_mode(1)
        p.save_subtree(fname, compress=False)
        self._set_save_mode(0, d)

        idx0 = p.get_ichild()
        new_obj = []
        for i in range(nump):
            obj = self.book.load_subtree(fname, compress=False)
            new_obj.append(obj)
            idx = obj.get_ichild()
            self.book.move_child(idx,  idx0+i+1)
            obj.setvar('group_id', gid)
            obj._status = 'group '+str(gid+1)
            pgb.Update(i)
        for k, o in enumerate(self.book.walk_page()):
            o.rename('page'+str(k+1))
        pgb.Destroy()
        os.remove(fname)

        for ipage, p in enumerate(self.book.walk_page()):
            self.set_index_col_row_page(ipage)
#           p.realize()
        # realize all page except for reference page
        for p in new_obj:
            p.realize()

        ifigure.events.SendChangedEvent(self.book, w=self.canvas)

    #
    #  user methods
    #
    @property
    def shot_dict(self):
        '''
        return locals() for shot string evaluation
        '''
        return self._shot_dict

    @shot_dict.setter
    def shot_dict(self, value):
        '''
        set locals() for shot string evaluation
        '''
        self._shot_dict = value

    @at_wxthread
    def SetShotNumber(self, number):
        self.txt_shot.SetValue(str(number))

    @at_wxthread
    def SetShot(self, number):
        '''
        Set Shot Number
        '''
        self.txt_shot.SetValue(str(number))

    @at_wxthread
    def LoadData(self, blocking=True, allshot=True, figaxes='all', do_apply=True):
        '''
        LoadData() 
        LoadData(False) : no blocking mode
        '''
        if blocking:
            m = Queue.Queue()
            globals()['call_after_queue'] = m
        self._handle_apply_abort(
            allshot=allshot, figaxes=figaxes, do_apply=do_apply)
        if not blocking:
            return
        while True:
            v = m.get(True)
            callable, args, kargs = v
            callable(*args, **kargs)
            if callable == self.eval_mdsdata_done:
                break
        globals()['call_after_queue'] = None
        self.canvas.draw()
        return
#        if wait:
#            while self._mds_exit_status == 1:
#                time.sleep(1)
    @at_wxthread
    def ImportDW(self, file):
        import os
        file = os.path.expanduser(file)
        self.onImportDW(None, file)

    @at_wxthread
    def OpenBook(self, file):
        import os
        file = os.path.expanduser(file)
        self.onLoadBook(None, file=file)

    from ifigure.widgets.book_viewer_interactive import allow_interactive_call

    import collections
    @allow_interactive_call
    def AddSignal(self, experiment='', default_node='', signals=None,
                  script=None):
        '''
        Add MDSplus singal to the current section.
             AddSignal(experiment = '', default_node='', signals=None, script=None)
             example : 
                signals = {'y':'\\ip'}
                script = '\n'.join(['x = np.arange(30)', 'y = np.arange(30)'])
                name of child
        '''
        fig_axes = self.get_axes()
        if fig_axes is None:
            return

        if signals is None:
            signals = collections.OrderedDict()
        else:
            signals = collections.OrderedDict(signals)
        obj = FigMds()
        obj.setvar('experiment', experiment)
        obj.setvar('default_node', default_node)
        obj.setvar('mdsvars', signals)

#        if name is None:
#             name = fig_axes.get_next_name('mds')
#        fig_axes.add_child(name, obj)
#        if script is not None:
#            obj.write_script(script)
        return obj

    from ifigure.widgets.book_viewer_interactive import allow_interactive_call2
    @allow_interactive_call2
    def AddSignalScript(self, script=None, kind='plot', **kargs):
        obj = self.AddSignal(**kargs)
        if script is not None:
            obj.write_script(script)
        obj.set_mdsfiguretype(kind)
        return obj
