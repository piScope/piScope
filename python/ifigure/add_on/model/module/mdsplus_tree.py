from __future__ import print_function
import wx
import ifigure
from ifigure.utils.cbook import parseStr
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
from ifigure.mto.py_module import PyModule
from ifigure.mto.py_contents import MDSPlusTree
#from ifigure.add_on.data.mdsplus_tree import MdsplusTreeNode
import wx
import sys
import os
import re
import string
from numpy import *
from collections import OrderedDict
#import ifigure.utils.mdsplusr as mds
from ifigure.utils.edit_list import DialogEditList
from ifigure.mdsplus.mdsscope import print_threaderror

######################################################
#         Setting for module file for py_module
#
#   General rule:
#      This file will be automatically loaded when
#      py_module object is created. Also, py_module
#      keeps track the file modification time. If
#      the file is updated, it will be automaticaaly
#      reloaded.


#      Strong recommendation : make module "independent".

#      Py_Modules does not check the dependency of
#      modules.
#      If moduels used in Py_Modules depends on
#      each other by for example module variable,
#      it will cause complicate  module loading
#      order-dependency problem.
#
#   name of module
module_name = 'mdsplus_tree'
class_name = 'mdsplus_tree'
#   module_evt_handler
#   functions which can be called from project tree
#
#    (menu name, function name, a flat to call skip()
#     after running function)
#
#   By default these function should return None
#   or True
#   if it return False, ifigure stops exectuion at
#   this module
#
menu = [("Open Tree", "onOpenTree", True)]

#
#   method lists module functions which will
#   be registered as method
#
#   spceical methods:
#      init  : called when mto will be made and
#              this module is first loaded.
#      clean : called when mto will be killed
#
method = ['onOpenTree', 'OpenTreeDone', 'init']

icon = 'data.png'
can_have_child = True
has_private_owndir = True
######################################################


def split_str(s, pattern):
    ret = re.split(pattern, s)

    ret2 = []
    for s in ret:
        s = s.strip()
        if s != '':
            ret2 = ret2+[s]
    return ret2


def make_treedicts(tree, this):
    arr = split_str(tree[0], '[\:.]')

    treename = arr[0][1:]

    top = PyData()
    top.set_can_have_child(False)
    this.add_child(treename, top)
    dicttop = MDSPlusTree()
    top.setvar0(dicttop)

    print(("tree nodes :", len(tree)))

    for k in range(len(tree)-1):
        arr = split_str(tree[k+1], '[\:.]')
        p = dicttop
        for key in arr[1:]:
            p.setdefault(key, MDSPlusTree())
            p = p[key]

        p.mds_path = tree[k+1]
    return top


def ask_mdssetting(this=None):
    if this is not None:
        server = this.getvar("server")
        port = str(this.getvar("port"))
    else:
        server = "localhost"
        port = "10002"
    tree = "ANALYSIS"
    shot = "-1"
    list = [["", " " * 50, 2],
            #           ["Server", server, 0],
            #           ["Port", port, 0],
            ["MDSconnect", this.getvar('mdsplus_server'), 204, None],
            ["Tree", tree, 4, {"choices": ["ANALYSIS", "ELECTRONS",
                                           "SPECTROSCOPY", "XTOMO", "DNB", "RF",
                                           ]}],
            ["Shot", shot, 0]]

    flag, value = DialogEditList(list, parent=this.get_app())

    if flag:
        this.setvar('mdsplus_server', str(value[1]))
        this.setvar("tree", str(value[2]))
        this.setvar("shot", str(value[3]))
    return flag, value


def init(self, src=None):
    td = self.td
    proj = self.td.get_root_parent()
    if proj.setting.has_child('mdsplus_worker'):
        workers = proj.setting.mdsplus_worker
    else:
        file = os.path.join(ifigure.__path__[0], 'add_on',
                            'setting', 'module', 'mdsplus_worker.py')

        workers = proj.setting.add_absmodule(file)
        workers.rename('mdsplus_worker')
    workers.call_method('onStartWorker')
    if not td.hasvar('mdsplus_server'):
        td.setvar('mdsplus_server', 'direct::CMOD')

#    if src is None:
#       flag, value = ask_mdssetting()
#       td._name='mdsplus'
#       self.onOpenTree(tree =value[1],
#                       shot =long(value[2]))


def OpenTreeDone(self, ana):

    if not 'list' in ana.result:
        return
    this = self.td
    treelist = ana.result['list']
    if treelist is None:
        return

    top = make_treedicts(treelist, this)
    top.setvar("tree", ana.tree)
    top.setvar("shot", ana.shot)
    ifigure.events.SendChangedEvent(self.td,
                                    useProcessEvent=False)


def onOpenTree(self, ev=None,
               server=None,
               port=None,
               tree=None,
               shot=None,):
    this = self.td
    if (server is None and
        port is None and
        tree is None and
            shot is None):
        # this is when "open tree" was chosen
        # in popup menu of varviwer
        flag, value = ask_mdssetting(this)
        if flag is False:
            return

    if server is None:
        server = this.getvar('mdsplus_server')
    if tree is None:
        tree = this.getvar("tree")
    if shot is None:
        shot = int(this.getvar("shot"))

    from ifigure.mdsplus.fig_mds import MDSsession
    from ifigure.mdsplus.mds_job import MDSjob
    from ifigure.mdsplus.mdsscope import start_mds_threads, message

    ana = MDSsession()
    job0 = MDSjob('connection_mode', server)
    job1 = MDSjob('open', tree, shot)
    job2 = MDSjob('value', 'getnci("***", "FULLPATH")')
    ana.add_job([job0], 'connection_mode')
    ana.add_job([job1], 'connection')
    ana.add_job([job2], 'list')
    ana.isec = 0
    ana.ishot = 0
    ana.ipage = 0
    ana.shot = shot
    ana.do_title = False
    ana.tree = tree

    sr = start_mds_threads()  # sr = session_runner
    c = message('run', ([ana], wx.GetApp().TopWindow,
                        self.OpenTreeDone, False))
    sr.queue.put(c)
