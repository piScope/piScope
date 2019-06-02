from __future__ import print_function
import wx
from ifigure.utils.cbook import parseStr
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
import os
import re
import string
import numpy
from collections import OrderedDict
import idlsave

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
module_name = 'gfile_subs'
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
module_evt_handler = [("Load File", "onLoadFile", True)]
#
#   A function called when py_module is initialized
#
module_init = None
######################################################


def expand_recarray(top, var):
    for name in var.dtype.names:
        print((name,  type(var.field(name))))

        if isinstance(var.field(name), numpy.recarray):
            child = PyData()
            top.add_child(name, child)
            expand_recarray(child, var.field(name))
        else:
            top.setvar(name, var.field(name))


def read_sav_file(this):
    file = this.getvar("filename")
    s = idlsave.read(file)
    for key in s:
        if isinstance(s[key], numpy.recarray):
            child = PyData()
            this.add_child(key, child)
            expand_recarray(child, s[key])
        else:
            this.setvar(key, s[key])


def onLoadFile(self_obj):
    open_dlg = wx.FileDialog(None, message="Select .sav file",
                             wildcard='*.*',
                             style=wx.FD_OPEN)
    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return False
    file = open_dlg.GetPath()
    open_dlg.Destroy()
    for name, child in self_obj.get_children():
        child.destroy()
    self_obj.setvar("filename", file)
    read_sav_file(self_obj)


def onWriteFile(self_obj):
    pass
