from __future__ import print_function

from ifigure.utils.cbook import Write2Main
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
import wx
import os
import re
import string
import sys
from numpy import *
from collections import OrderedDict

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
module_name = 'dwscope_subs'
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


def import_dwscope(file):

    f = open(file, 'r')

    d = {}
    while 1:
        line = f.readline()
        if not line:
            break
        line = line.rstrip("\r\n")

        pos = line.find(':')
        command = line[:pos]
        data = line[pos+1:]
        print(line)
        arr = command.split('.')
        if len(arr) == 3:
            if arr[1] not in d:
                d[arr[1]] = {}
            d[arr[1]][arr[2]] = data
        if len(arr) == 2:
            if arr[1] not in d:
                d[arr[1]] = {}
            d[arr[1]] = data

    f.close()

    num_c = int(d["columns"])
    num_r = [0]*num_c
    return d
    for i in range(num_c)+1:
        key = 'rows_in_column_'+str(i)
        num_r[i-1] = int(d[key])

    d2 = {"num_c": num_c,
          "num_r": num_r}

    for key in d:
        if key[:4] == 'plot':
            d2[key[5:]] = d[key]
        if key[:6] == 'global':
            d2["global"] = d[key]

    d2["title"] = d["title"]
    d2["title_event"] = d["title_event"]
    return d2


def onLoadFile(self_obj):
    open_dlg = wx.FileDialog(None, message="Select DWscope",
                             wildcard='*.dat', style=wx.FD_OPEN)
    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return False

    file = open_dlg.GetPath()
    open_dlg.Destroy()
    for name, child in self_obj.get_children():
        child.destroy()
    self_obj.setvar("filename", file)

    value = import_dwscope(file)
    self_obj.setvar("value", value)
