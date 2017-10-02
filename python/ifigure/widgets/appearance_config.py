from ifigure.widgets.dlg_preference import PrefComponent
from ifigure.utils.setting_parser import iFigureSettingParser as SP
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('HelperApp')
from ifigure.utils.add_sys_path import AddSysPath
import os

#
#  Plan is...
#      choice of button setting in plot
#      keyboard binding rule
#

class AppearanceConfig(PrefComponent):
    def __init__(self):
        PrefComponent.__init__(self, 'Appearance')
        p = SP()
        self.setting = p.read_setting('pref.appearance_config')

    def save_setting(self):
        p = SP()
        p.write_setting('pref.appearance_config', self.setting)

    def get_dialoglist(self):
        list1 = [["Suppress/Delete Menu in TreeViewer", self.setting["show_suppress_menu"], 3, {"text":"Show"}],
["OpenGL multisampling", self.setting["gl_multisample"], 3, {"text":"On"}],
                ]
        hint1  = ['Show Suppress, Unsuppress, and Delete Menu in Project Tree Viewer',
                 ]

        return list1, hint1

    def set_dialog_result(self, value):
        self.setting["show_suppress_menu"]  = value[0]
        self.setting["gl_multisample"]  = value[1]
        import ifigure.matplotlib_mod.backend_wxagg_gl
        ifigure.matplotlib_mod.backend_wxagg_gl.multisample_init_done = False
     




