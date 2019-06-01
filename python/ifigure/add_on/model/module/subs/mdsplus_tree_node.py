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
module_name = 'mdsplus_tree_node'
class_name = 'mdsplus_tree_node'
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
method = ['isMdsNode', '_getitem_',
          'dim_of', 'call_mdsvalue']

icon = 'data.png'
can_have_child = True
######################################################


def isMdsNode(self):
    return True


def _getitem_(self, key):
    txt = self.td.getvar("node")
    print(txt)
    return self.call_mdsvalue(txt)


def dim_of(self, num=0):
    print(self)
    print(self.td)
    node = self.td.getvar("node")
    txt = 'dim_of('+node.strip()+','+str(num)+')'
    return self.call_mdsvalue(txt)


def call_mdsvalue(self, str):
        # parent should be the top of tree
        # such as "cmod", "analysis", "xtomo"

    try:
        parent = self.td
        while parent.get_parent()._obj.isMdsNode():
            parent = parent.get_parent()
    except Exception:
        pass

    tree = parent.getvar("tree")
    shot = parent.getvar("shot")
    server = parent.getvar("server")
    port = parent.getvar("port")
    mds.port = port
    mds.server = server
    print((tree, shot, port, server, str))
    try:
        res = mds.open(tree, shot)
        print(res)
        return mds.value(str)
    except Exception:
        print("!!!!!! Error in evaluating the following node  !!!!!!")
        print(("TREE/SHOT", tree, shot))
        print(("NODE", str))
        print(sys.exc_info())
    return None
