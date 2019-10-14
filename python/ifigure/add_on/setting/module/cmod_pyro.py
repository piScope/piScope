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
module_name = 'cmod_pyro'
class_name = 'cmod_pyro'
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
menu = [("Launch NS", "onLaunchNS", True),
        ("Launch DM", "onLaunchDM", True)]


method = ['init', 'clean', 'onLaunchNS', 'onLaunchDM']

icon = 'world_link.png'
can_have_child = False
has_private_owndir = False
######################################################


def init(self):
    self.td.setvar("daemons",
                   (("proxy_efit", True, "cmodws60.psfc.mit.edu", -1),
                    ("proxy_nete", True, "cmodws60.psfc.mit.edu", -1)))
    self.td.setvar("pyronshost", "cmodws30.psfc.mit.edu")


def clean(self):
    # clean is a special process called when td is deleted
    if hasattr(self, 'p'):
        self.p.terminate()
        del self.p


def onLaunchNS(self, e):
    pass


def onLaunchDM(self, e):
    pass
