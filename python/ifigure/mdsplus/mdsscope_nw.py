from __future__ import print_function
#
#   MDSScope no-window
#
#       no window version of scope.
#       a user can load data without opening book
#       on a screen. Internally it uses exact same
#       ScopeEngine to process MDSplus sessions
#
#   example:
#     >> o =scopenw(proj.lh_scope)
#     >> o.SetShot(1101119004)
#     >> o.LoadShot(verbose = False)
#     >> o.close()
#     >> from ifigure.widgets.book_viewer import BookViewer
#     >> proj.lh_scope.Open(BookViewer)
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
from ifigure.mdsplus.mdsscope import ScopeEngine, message, set_call_after_queue

#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('MDSScope')


class FakeTextCtrl(object):
    def __init__(self, *args, **kargs):
        self._value = ''

    def SetValue(self, value):
        self._value = value

    def GetValue(self):
        return self._value


class FakeBookViewerFrame(object):
    def __init__(self, *args, **kargs):
        self._title = ''
        self._parent = ''
        self._status_txt = ['']*10
        self._print_status = True
        if "book" in kargs:
            self.book = kargs["book"]
            del kargs["book"]
  #          self.book.set_open(True)
        else:
            self.book = None

        self.ipage = 0

    def SetTitle(self, title):
        self._title = title
        print(('title: ', title))

    def GetTitle(self):
        return self._title

    def SetStatusText(self, txt, idx):
        self._status_txt[idx] = txt
        if self._print_status:
            print(('status: ', txt))

    def get_page(self, ipage=None):
        if ipage is None:
            f_page = self.book.get_page(self.ipage)
        else:
            f_page = self.book.get_page(ipage)
        return f_page


class MDSScopeNW(FakeBookViewerFrame,  ScopeEngine):
    def __init__(self, *args, **kargs):
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

        super(MDSScopeNW, self).__init__(*args, **kargs)
        ScopeEngine.__init__(self, no_window=True)

        if self.book is not None:
            #            for page in self.book.walk_page():
            self.prepare_dwglobal(self.book)
            if not self.book.hasvar('mdsplus_server'):
                p = SettingParser()
                v = p.read_setting('mdsplus.default_mdsserver')
                self.book.setvar('mdsplus_server',
                                 v['server'])
#                                 'direct::CMOD')
            if not self.book.hasvar('mdsscript_main'):
                self.book.setvar('mdsscript_main',
                                 True)
            if not self.book.hasvar('mdsscope_autogrid'):
                self.book.setvar('mdsscope_autogrid',
                                 True)
            if not self.book.hasvar('mdsscope_listenevent'):
                self.book.setvar('mdsscope_listenevent',
                                 True)
            if not self.book.hasvar('dwscope_filename'):
                self.book.setvar('dwscope_filename', '')
            from ifigure.mdsplus.fig_mdsbook import convert2figmdsbook
            convert2figmdsbook(self.book)

        self.g = {}  # global variabls for mainthread scripting
        self._title_mdsjob_count = 0
        self._mdsjob_count = 0
        self._cur_shot = 0
        self._mds_exit_status = 0
        self._figmds_list = []
        self.mpanalysis = False
        self._mpanalysis_mode = True
        self.parallel_page = True
        self.parallel_shot = True
        self.parallel_sec = True
        self.init_beginning = True
        self.init_page = False
        self.init_shot = False
        self.init_sec = False
        self.debug_mode = False
        self.timer = None

        self.previous_shot_set = [[]]
        self.event_dict = {}
        self.InitUI()
        from numpy import linspace
        self._shot_dict = {'linspace': linspace}
#        self.Thaw()

        proj = self.book.get_root_parent()
        proj = self.book.get_root_parent()
        if self.workers is None:
            if proj.setting.has_child('mdsplus_worker'):
                self.workers = proj.setting.mdsplus_worker
            else:
                file = os.path.join(ifigure.__path__[0], 'add_on',
                                    'setting', 'module', 'mdsplus_worker.py')

                workers = proj.setting.add_absmodule(file)
                workers.rename('mdsplus_worker')
                self.workers = workers

        p = SettingParser()
        p.set_rule('global_set', {}, nocheck=True)
        self.scope_setting = p.read_setting('mdsplus.scope_setting')

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

        self.workers.call_method('onStartWorker')
#        self.start_pool()
        self.open_engine()

    def __del__(self):
        self.close_engine()

    def close(self):
        self.close_engine()

    def InitUI(self):
        self.txt_shot = FakeTextCtrl()

    def show_page(self, ipage=0, last=False, first=False):
        self.ipage = ipage
        self.prepare_dwglobal(self.book)

    def _handle_apply_abort(self, allshot=True, figaxes='all',
                            do_apply=False):
        from ifigure.mdsplus.mdsscope import mds_thread
        #mds_thread = globals()['mds_thread']
        mds_thread._time = time.time()
        if self._mode == 'apply' or do_apply:
            self._mode = 'abort'
            try:
                self.eval_mdsdata(allshot, figaxes=figaxes)
            except:
                dprint1('Error happend while evaluating mdsplus data')
                dprint1(traceback.format_exc())
                self.eval_mdsdata_done(status=-1)
        else:
            c = message('abort', (self,))
            mds_thread.queue.put(c)

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

    def SetShot(self, number):
        '''
        Set Shot Number
        '''
        self.txt_shot.SetValue(str(number))

    def LoadData(self, blocking=True, allshot=True, figaxes='all',
                 do_apply=True, verbose=True):
        '''
        LoadData() 
        LoadData(False) : no blocking mode
        '''
        o_printstatus = self._print_status
        self._print_status = verbose
        if blocking:
            m = Queue.Queue()
            set_call_after_queue(m)
        self._handle_apply_abort(allshot=allshot,
                                 figaxes=figaxes,
                                 do_apply=do_apply)
        if not blocking:
            return
        while True:
            v = m.get(True)
            callable, args, kargs = v
            callable(*args, **kargs)
            if callable == self.eval_mdsdata_done:
                break
        set_call_after_queue(None)
        self._print_status = o_printstatus
        return
