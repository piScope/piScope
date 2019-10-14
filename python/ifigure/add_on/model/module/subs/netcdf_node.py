from __future__ import print_function
import wx
from ifigure.utils.cbook import parseStr
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
#from ifigure.add_on.data.mdsplus_tree import MdsplusTreeNode
import wx
import sys
import os
import re
import string
from numpy import *
from collections import OrderedDict
import ifigure.utils.mdsplusr as mds
from ifigure.utils.edit_list import DialogEditList
from netCDF4 import Dataset

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
module_name = 'netcdf_node'
class_name = 'netcdf_node'
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
menu = []
#
#   method lists module functions which will
#   be registered as method
#
#   spceical methods:
#      init  : called when mto will be made and
#              this module is first loaded.
#      clean : called when mto will be killed
#
method = ['isNetCDFNode', '_getitem_']

icon = 'data.png'
can_have_child = True
######################################################


def isNetCDFNode(self):
    return True


def _getitem_(self, key):
    print(key)

    def find_root(obj):
        root = obj
        while root is not None:
            try:
                if root.get_parent()._obj.isNetCDFNode():
                    root = root.get_parent()
            except Exception:
                return root.get_parent()

    obj = self.td
    root = find_root(obj)
    fpath = root.path2fullpath(pathmode='nc_pathmode',
                               path='nc_path')

    g = Dataset(fpath, 'r', format='NETCDF4')

    p = obj
    names = []
    while p != root:
        names.append(str(p.name))
        p = p.get_parent()

    for i in range(len(names)-1):
        g = getattr(g0, names[len(names)-i-1])
    g0.close()
    return g[names[0]][:]
