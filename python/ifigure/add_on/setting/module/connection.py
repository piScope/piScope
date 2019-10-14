from ifigure.mto.py_connection import PyConnection
import numpy as np
import wx
import ifigure.widgets.dialog as dialog
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
module_name = 'connection_module'
class_name = 'connection_module'
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
menu = [("New Connection...", "onNewConnection", True)]
method = ['onNewConnection', 'add_connection']
icon = 'world_link.png'
######## Do not chage this field ####################
can_have_child = True
has_private_owndir = True
######################################################


def add_connection(self, new_name):
    child = PyConnection()
    imodel = self.td.add_child(new_name, child)
    child.setvar('server', new_name)


def onNewConnection(self, e):

    app = self.td.get_app()
    ret, new_name = dialog.textentry(app,
                                     "Enter the name of new connection", "Add Connection", "")
    if ret:
        self.add_connection(new_name)
