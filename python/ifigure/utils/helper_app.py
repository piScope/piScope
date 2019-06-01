from ifigure.widgets.dlg_preference import PrefComponent
from ifigure.utils.setting_parser import iFigureSettingParser as SP
import wx
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('HelperApp')


def config_name():
    if wx.Platform == '__WXMAC__':
        return 'pref.helperapp_mac_config'
    else:
        return 'pref.helperapp_config'


class HelperApp(PrefComponent):
    def __init__(self):
        PrefComponent.__init__(self, 'HelperApp')
        p = SP()

        self.setting = p.read_setting(config_name())

    def save_setting(self):
        p = SP()
        p.write_setting(config_name(), self.setting)

    def get_dialoglist(self):
        txt = 'yes' if self.setting["use_editor"] else 'no'

        list1 = [["Pdf",         str(self.setting["pdf"]), 200, None],
                 ["PostScript",  str(self.setting["ps"]), 200, None],
                 ["Editor",      str(self.setting["editor"]), 200, None],
                 ["ghostscript", str(self.setting["gs"]), 200, None],
                 ["ps2pdf",      str(self.setting["ps2pdf"]), 200, None],
                 ["convert",     str(self.setting["convert"]), 200, None],
                 ["Use external editor",  txt, 1, {"values": ["yes", "no"]}],
                 [None, "Replacement rule: {bin} -> piscope_sourcer/bin, {0} -> file path"+" "*30, 2], ]
        hint1 = ['PDF viewer', 'Postscript viewer', 'Externail Editor',
                 'gs', 'ps2pdf(used in fig_eps)', None, None]
        return list1, hint1

    def set_dialog_result(self, value):
        self.setting["pdf"] = str(value[0])
        self.setting["ps"] = str(value[1])
        self.setting["editor"] = str(value[2])
        self.setting["gs"] = str(value[3])
        self.setting["ps2pdf"] = str(value[4])
        self.setting["convert"] = str(value[5])
        self.setting["use_editor"] = (str(value[6]) == 'yes')
