import os
from ifigure.utils.add_sys_path import AddSysPath
from ifigure.widgets.dlg_preference import PrefComponent
from ifigure.utils.setting_parser import iFigureSettingParser as SP
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('HelperApp')

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
        list1 = [["Suppress/Delete Menu in TreeViewer", self.setting["show_suppress_menu"], 3, {"text": "Show"}],
                 ["Use 3D graphics (needs restart)",
                  self.setting["gl_use"], 3, {"text": "On"}],
                 ["OpenGL multisampling",
                     self.setting["gl_multisample"], 3, {"text": "On"}],
                 ["Use OpenGL 2.1 (instead of 3.2) (needs restart)",
                  self.setting["gl_use_12"], 3, {"text": "On"}],
                 ["Generate additional screen refresh",
                  self.setting["generate_more_refresh"], 3, {"text": "On"}],
                 ]

        hint1 = ['Show Suppress, Unsuppress, and Delete Menu in Project Tree Viewer',
                 'Use super reslution for smooth 3D graphics',
                 'Turn on OpenGL 3D graphics',
                 'OpenGL 3.2 runs only on newer computers',
                 'Refresh GUI more often for some remote client.',
                 ]

        return list1, hint1

    def set_dialog_result(self, value):
        self.setting["show_suppress_menu"] = value[0]
        self.setting["gl_use"] = value[1]
        self.setting["gl_multisample"] = value[2]
        self.setting["gl_use_12"] = value[3]
        self.setting["generate_more_refresh"] = value[4]
        import ifigure.matplotlib_mod.backend_wxagg_gl
        ifigure.matplotlib_mod.backend_wxagg_gl.multisample_init_done = False
