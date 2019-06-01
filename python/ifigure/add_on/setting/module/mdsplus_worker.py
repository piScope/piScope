from __future__ import print_function

'''
   setting add-on for mds mp/sp workers.
 
   2014 02 worker type setting is removed. it uses always "mp" worker.

'''

from ifigure.mdsplus.mdsscope import MDSWorkerPool
from ifigure.mdsplus.mds_sp_worker_pool import MDSSPWorkerPool
from ifigure.mdsplus.mds_mpth_worker_pool import MDSMPWorkerPool
from ifigure.utils.setting_parser import iFigureSettingParser as SettingParser
from ifigure.utils.edit_list import DialogEditList
import wx
import subprocess
import wx
import os
import shlex
import socket

module_name = 'MDSplusWorker'
class_name = 'MDSplusWorker'
menu = []  # this will be filled in method below
method = ['onReset', 'onSetting', 'onShowStatus', 'onActivate',
          'onStartWorker', 'init', 'run_job', 'clean',
          'tree_viewer_menu']

icon = 'world_link.png'
can_have_child = False
has_private_owndir = False
allow_only_one_active = True


def init(self, *args, **kargs):
    #    if not kargs.has_key('src'):
    self.td._pool = MDSWorkerPool()
    p = SettingParser()
    p.set_rule('connection', {}, nocheck=True)
    self.td.setvar('setting', p.read_setting('mdsplus.connection_setting'))
#    self.onStartWorker()


def tree_viewer_menu(self):
    if not self.td.is_suppress():
        menu = [
            ("Show Status", "onShowStatus",  False),
            ("Start Worker", "onStartWorker",  False),
            ("Stop Worker",    "onReset",    False),
            ("Setting...", "onSetting",  False)]
    else:
        menu = [("Activate", "onActivate",  False), ]
    return menu


def onActivate(self, evt):
    self.td.activate()
    self.td._pool.reset()
    self.onStartWorker()
    evt.Skip()


def clean(self, *args, **kargs):
    self.td._pool.reset()
    p = SettingParser()
    p.write_setting('mdsplus.connection_setting',
                    self.td.getvar('setting'))


def run_job(self, a):
    from ifigure.mdsplus.mdsscope import print_threaderror
    #self.pool = MDSWorkerPool.pool
    if self.td._pool is None:
        wx.CallAfter(print_threaderror, [
                     'can not run job. worker pool is not ready'])
        return

    maxwait = 25
    wait = 0
    import time
    while(wait < maxwait):
        time.sleep(0.5)
        w, w_id = self.td._pool.get_worker()
        if w is not None:
            a.start_job(self.td._pool, w_id)
            return
        wait = wait+1
    else:
        wx.CallAfter(print_threaderror, [
                     'can not run job. waiting time exceeded max time'])
        return


def onReset(self, e=None):
    self.td._pool.reset()


def onStartWorker(self, e=None):
    s = self.td.getvar('setting')
    c_type = s['connection_type']
    w_type = s['worker']
    if c_type == 'proxy':
        host = s['connection'][0]['server']
        port = s['connection'][0]['port']
        c_type = ('proxy', host, port)
    else:
        c_type = (c_type,)
    t_type = self.td.getvar('translater')
    if t_type is None:
        t_type = 'default'
#    def func(a=c_type, b=w_type):
    self.td._pool.start(c_type, w_type, t_type)


def onShowStatus(self, e=None):
    pool = self.td._pool.pool
    print(pool)
    if isinstance(pool, MDSSPWorkerPool):
        print(pool.pch)
    elif isinstance(pool, MDSMPWorkerPool):
        for w in pool.workers:
            print(w)
    else:  # isinstance(pool, MDSTHWorkerPool):
        for w in pool.workers:
            print(w)


def onSetting(self, e=None):
    import ifigure.mdsplus.mdsscope
    s = self.td.getvar('setting')
    host = s['connection'][0]['server']
    port = s['connection'][0]['port']

    if s['connection_type'] == 'direct':
        txt = 'off'
    else:
        txt = 'on'

    list6 = [["Use Proxy", txt, 1, {"values": ["on", "off"]}],
             ["Root Tree", "cmod", 0, None],
             ["Proxy Server", str(host), 0, None],
             ["Port", str(port), 0, None],
             ["NumWorker", str(
                 ifigure.mdsplus.mdsscope.mds_num_worker), 0, None],
             #           ["Worker", s['worker'], 4, {'style':wx.CB_READONLY, 'choices':['mp', 'th', 'sp']}]]
             ["Worker", s['worker'], 4, {'style': wx.CB_READONLY, 'choices': ['mp', 'th']}]]

    value = DialogEditList(list6, modal=True,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                           tip=None,
                           parent=self.td.get_app())

    if value[0]:
        v = value[1]
    else:
        return
    if str(v[0]) == 'on':
        t = 'proxy'
    else:
        t = 'direct'
    onum = ifigure.mdsplus.mdsscope.mds_num_worker
    ifigure.mdsplus.mdsscope.mds_num_worker = int(v[4])
    w = str(v[5])
#    w = 'mp' ## always use mp worker
    port = str(v[3])
    host = str(v[2])
    restart = False
    if (s['connection_type'] != t or
        s['worker'] != w or
        onum != ifigure.mdsplus.mdsscope.mds_num_worker or
        s['connection'][0]['server'] != host or
            int(s['connection'][0]['port']) != int(port)):
        restart = True
    s['connection_type'] = t
    s['worker'] = w
    s['connection'][0]['server'] = host
    s['connection'][0]['port'] = int(port)
    if restart:
        self.onReset()
        self.onStartWorker()

    self.td.setvar('setting', s)
