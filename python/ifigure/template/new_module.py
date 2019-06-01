from __future__ import print_function
import numpy as np
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
module_name = 'sample_module'
class_name = 'sample_module'
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
menu = [("MenuName", "onMenu", True)]
method = ['test', 'onMenu']

icon = 'cog.png'
######## Do not chage this field ####################
can_have_child = True
has_private_owndir = True
######################################################


def test(self):
    print(self)
    pass


def onMenu(self, e):
    print(self)
    print(e)
    pass
