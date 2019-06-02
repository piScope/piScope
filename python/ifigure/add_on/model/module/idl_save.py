from __future__ import print_function
import numpy as np
import collections
from scipy.io.idl import readsav
import wx
import os
import traceback
import shutil
import ifigure
from ifigure.mto.py_contents import IDLfile, IDLData
from ifigure.utils.recarray import rec2dict
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
#   name of module/class
module_name = 'idl_savfile'
class_name = 'idl_savfile'
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
menu = [("Import...",   "onLoadFile", True),
        #      ("Export...",   "onExportFile", True),
        #      ("Update File",   "onUpdateFile", True),
        ("Update Tree",   "onUpdateTree", True)]
method = ['onLoadFile',
          'onUpdateTree',
          'init', 'init_after_load']

icon = 'data.png'

modename = 'idl_pathmode'
pathname = 'idl_path'
extname = 'idl_ext'
wildcard = 'idl(*.sav)|*.sav|Any|*'
######## Do not chage this field ####################
can_have_child = False
has_private_owndir = False
######################################################


def init(self, *args, **kargs):
    #   a function called when py_module is initialized
    obj = self.td
    obj.mk_owndir()
    nm = IDLfile()  # nm['data'] = IDLData()
    obj.setvar0(nm)
    if 'src' not in kargs:
        self.onLoadFile(None)
    # self.onLoadFile()


def load_matfile(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)
    if file == '':
        return
    # clean first
    for name, child in obj.get_children():
        child.destroy()

    def idl2dict(dd, cls=collections.OrderedDict):
        r = cls()
        for name in dd:
            print(name)
            print(isinstance(dd[name], np.recarray))
            if isinstance(dd[name], np.recarray):
                r[name] = rec2dict(dd[name], cls=cls)
            else:
                r._var0[name] = dd[name]
        return r

    nm0 = readsav(file)
    if nm0 is None:
        nm0 = IDLfile()
    else:
        nm0 = idl2dict(nm0, cls=IDLfile)
    nm = IDLfile()
    nm['data'] = nm0
    obj.setvar0(nm)

#   nm = IDLfile(nm0);nm['data'] = IDLData()
#   if nm0 is None: return
#   for key in nm0: nm['data'][key] = nm0[key]


def export_matfile(obj, file):
    nm = obj.getvar0()
    nm = sio.savemat(file, nm['data'])


def onUpdateTree(self, e):
    obj = self.td
    load_matfile(obj)


def onLoadFile(self, e):
    from ifigure.utils.addon_utils import onLoadFile

    ret = onLoadFile(self.td, message="Select .sav File",
                     modename=modename,
                     pathname=pathname,
                     extname=extname,
                     wildcard=wildcard,
                     ask_org_copy=False)
    if ret:
        load_matfile(self.td)
        ifigure.events.SendChangedEvent(self.td)


def init_after_load(self, olist, nlist):
    obj = self.td
    load_matfile(obj)
