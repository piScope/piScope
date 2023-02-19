from __future__ import print_function
import numpy as np
import scipy.io as sio
import wx
import os
import traceback
import shutil
import ifigure
from ifigure.mto.py_contents import Matfile, MatData
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
module_name = 'matlab_matfile'
class_name = 'matlab_matfile'
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
        ("Export...",   "onExportFile", True),
        ("Update File",   "onUpdateFile", True),
        ("Update Tree",   "onUpdateTree", True)]
method = ['onLoadFile', 'onExportFile',
          'onUpdateFile', 'onUpdateTree',
          'init', 'init_after_load']

icon = 'data.png'


modename = 'mat_pathmode'
pathname = 'mat_path'
extname = 'mat_ext'
wildcard = 'mat(*.mat)|*.mat|Any|*'
######## Do not chage this field ####################
can_have_child = False
has_private_owndir = False
nosave_var0 = True
######################################################


def init(self, *args, **kargs):
    #   a function called when py_module is initialized
    obj = self.td
    obj.mk_owndir()
    nm = Matfile()
    nm['data'] = MatData()
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

    nm0 = sio.loadmat(file)
    nm = Matfile()
    nm['data'] = MatData()
    obj.setvar0(nm)
    mtime = os.path.getmtime(file)
    obj.setvar('mat_mtime', mtime)

    if nm0 is None:
        return
    for key in nm0:
        nm['data'][key] = nm0[key]


def export_matfile(obj, file):
    nm = obj.getvar0()
    nm = sio.savemat(file, nm['data'])


def onUpdateFile(self, e):
    obj = self.td
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)
    file_check = os.path.join(obj.owndir(), obj.name)+'.mat'

    if file == '':
        file = file_check
        try:
            export_matfile(obj, file)
            obj.set_path_pathmode(file, modename, pathname, extname)
        except:
            print('file save failed')
            traceback.print_exc()
    else:
        if file_check != file:
            shutil.move(file, file_check)
            obj.set_path_pathmode(file_check, modename, pathname, extname)
            file = file_check
        try:
            export_matfile(obj, file)
        except:
            print('file save failed')
            traceback.print_exc()


def onUpdateTree(self, e):
    obj = self.td
    load_matfile(obj)


def onLoadFile(self, e=None, file='', checklist=None):
    from ifigure.utils.addon_utils import onLoadFile
    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname,
                                  checklist=checklist)
        ret = True
    else:
        ret = onLoadFile(self.td, message="Select .mat File",
                         modename=modename,
                         pathname=pathname,
                         extname=extname,
                         wildcard=wildcard,
                         ask_org_copy=True)
    if ret:
        load_matfile(self.td)
        ifigure.events.SendChangedEvent(self.td)


def onExportFile(self, e):
    from ifigure.utils.addon_utils import onWriteFile
    app = wx.GetApp().TopWindow
    obj = self.td
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    open_dlg = wx.FileDialog(app,
                             message='Save .mat file',
                             defaultDir=os.path.dirname(file),
                             defaultFile='untitled.mat',
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                             wildcard=wildcard)

    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return
    else:
        filename = str(open_dlg.GetPath())
        open_dlg.Destroy()
    export_matfile(obj, filename)


def init_after_load(self, olist, nlist):
    obj = self.td
    load_matfile(obj)
