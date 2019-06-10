from ifigure.utils.edit_list import DialogEditListTab
import ifigure.widgets.dialog as dialog
import wx
from ifigure.widgets.book_viewer import FrameWithWindowList
from ifigure.widgets.miniframe_with_windowlist import DialogWithWindowList
from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED
from ifigure.widgets.script_editor import Notebook
from ifigure.utils.wx3to4 import GridSizer

pkeys = ['experiment', 'default_node', 'x', 'y', 'z',
         'xerr', 'yerr', 'title', '_flag']


def make_gs_arr(gs, s):
    return {key: gs[key][s] for key in gs}
# class DlgMdsSetting(FrameWithWindowList):


class DlgMdsSetting(DialogWithWindowList):
    def __init__(self, parent, setting,  gwparam, mds_server, thread_main, cb=None):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.CLOSE_BOX
        super(DlgMdsSetting, self).__init__(parent, wx.ID_ANY, style=style)
#      super(DlgMdsSetting, self).__init__(parent, wx.ID_ANY)
        self.cb = cb
        gs = gwparam.getvar('globalsets')
        gv = gwparam.getvar()
        tabs = ['Set1', 'Set2', 'Set3', 'Set4', 'config', 'more']

        list1 = [[None, make_gs_arr(gs, 0), 118, None]]
        list2 = [[None, make_gs_arr(gs, 1), 118, None]]
        list3 = [[None, make_gs_arr(gs, 2), 118, None]]
        list4 = [[None, make_gs_arr(gs, 3), 118, None]]

        txt = "on" if parent.mpanalysis else "off"
        txt2 = "on" if gv['use_shot_global'] else "off"
        txt3 = "on" if parent.book._use_global_tdi else "off"
        txt4 = parent.book.getvar('global_tdi')
        txt8 = parent.book.getvar('global_tdi_event')
        txt7 = "on" if parent.init_beginning else "off"
        txt6 = "on" if parent.init_sec else "off"
        txt5 = "on" if parent.init_page else "off"

        list5 = [["MDSconnect", mds_server, 204, None],
                 ["Update", gv['event'], 0, None],
                 ["Global(title) TDI",  txt4,  200, None],
                 ["Global(title) event",  txt8,  200, None],
                 ["Use global TDI",  txt3,  1, {"values": ["on", "off"]}],
                 ["Common vars", gv['shot_global'], 0, None],
                 ["Use common vars",  txt2,  1, {"values": ["on", "off"]}],
                 ["Global setting", gv['global_choice'], 21, None],
                 ["Multipage mode",  txt, 1, {"values": ["on", "off"]}],
                 #            ["Color Order", gv['color_order'], 22, {}],]
                 ]

        tmp2 = [[None,  parent.book._parallel_sec, 3,
                 {"text": 'Parallelize Panels', "noindent": True}], ]
        tmp = [[None,  (parent.book._parallel_shot, [parent.book._parallel_sec]), 27,
                ({"text": 'Parallelize Pages'}, {"elp": tmp2})]]
        list6 = [[None, "MDSplus session parallelization",  102, None],
                 [None,  (parent.book._parallel_page,
                          [(parent.book._parallel_shot, [parent.book._parallel_sec])]),
                  27,
                  ({"text": 'Parallelize Shots', "space": 15}, {"elp": tmp})],
                 #["At session start",txt7, 1, {"values":["on", "off"]}],
                 #["At every page",   txt5, 1, {"values":["on", "off"]}],
                 #["At every panel",  txt6, 1, {"values":["on", "off"]}],
                 [None, thread_main,  3,
                  {"text": "Run python script in main thread",
                   "noindent": None}],
                 [None, "(!) MDS+ connection is initialized when opening new tree",  102, None], ]
        tip1 = None
        tip2 = None
        tip3 = None
        tip4 = None
        tip5 = ['MDSplus server and default Tree',
                'Update event',
                'Global TDI expression, which runs before panels are evaulated',
                'Event for Global TDI expression',
                'Show result of global tdi in window title',
                'MDS command called at the begining of page',
                'MDS command called at the begining of section',
                'Global setting selection for shots',
                'Use the same shot numbers for all pages. (shot numbers after semi-colon are ignored)', ]

        tip6 = [None,
                'Parallelization of MDS session',
                None,
                #'Initialize global/local variables when analysis loop starts',
                #'Initialize global/local variables when analyzing a new panel',
                #'Initialize global/local variables when analyzing a new page',
                None, ]

        l = [list1, list2, list3, list4, list5, list6]
        tip = [tip1, tip2, tip3, tip4, tip5, tip6]

        self.nb = wx.Notebook(self)
        self.elp = []
        for tab, ll, t in zip(tabs, l, tip):
            self.elp.append(EditListPanel(self.nb, ll, tip=t))
            self.nb.AddPage(self.elp[-1], tab)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.nb, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(vbox)

        self.SetTitle('Global Setting('+parent.GetTitle().split(':')[0]+')')

        bt_apply = wx.Button(self, wx.ID_ANY, 'Apply')
        bt_save = wx.Button(self, wx.ID_ANY, 'Save')

        bsizer = GridSizer(1, 5)
        self.GetSizer().Add(bsizer, 0, wx.EXPAND | wx.ALL, 1)
        bsizer.AddStretchSpacer()
        bsizer.Add(bt_save, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)
        bsizer.AddStretchSpacer()
        bsizer.Add(bt_apply, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 3)
        bsizer.AddStretchSpacer()

        self.Bind(wx.EVT_BUTTON, self.onSave, bt_save)
#        self.Bind(wx.EVT_BUTTON, self.onCancel, bt_cancel)
        self.Bind(wx.EVT_BUTTON, self.onApply, bt_apply)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Layout()
        self.Show()
        # self.append_help_menu()
        # self.append_help2_menu(self.helpmenu)
        # self.set_accelerator_table()

        wx.GetApp().add_palette(self)

    def onApply(self, evt):
        value = [elp.GetValue() for elp in self.elp]
        self.cb(value)
        self.GetParent()._handle_apply_abort(allshot=True)

    def onSave(self, evt):
        value = [elp.GetValue() for elp in self.elp]
        self.cb(value)

    def onClose(self, evt):
        try:
            self.GetParent()._setting_dlg = None
        except:
            pass
        wx.GetApp().rm_palette(self)
        self.Destroy()
        evt.Skip()


def callback(parent, value, setting, gwparam):
    gs = gwparam.getvar('globalsets')
    gv = gwparam.getvar()

    if not '_flag' in gs:
        gs['_flag'] = [[], [], [], []]
    for m in range(4):
        for key in value[m][0]:
            if not key in gs:
                gs[key] = [None]*4
            gs[key][m] = value[m][0][key]
    gv['event'] = str(value[4][1])
    gv['shot_global'] = str(value[4][5])
    gv['use_shot_global'] = (value[4][6] == 'on')
    parent.book.setvar('global_tdi', str(value[4][2]))
    parent.book.setvar('global_tdi_event', str(value[4][3]))
    parent.book._use_global_tdi = value[4][4] == 'on'
    gv['global_choice'] = value[4][7]
    parent.mpanalysis = (value[4][8] == "on")

    if not value[5][1][0]:
        parent.book._parallel_page = False
        parent.book._parallel_shot = False
        parent.book._parallel_sec = False
    else:
        parent.book._parallel_page = True
        if not value[5][1][1][0][0]:
            parent.book._parallel_shot = False
            parent.book._parallel_sec = False
        else:
            parent.book._parallel_shot = True
            parent.book._parallel_sec = value[5][1][1][0][1][0]

    parent.book.setvar('mdsscript_main',
                       value[5][2])
    parent.book.setvar('mdsplus_server',
                       str(value[4][0]))

    from ifigure.utils.setting_parser import iFigureSettingParser as SettingParser
    p = SettingParser()
    v = p.read_setting('mdsplus.default_mdsserver')
    if str(v['server']) != str(value[4][0]):
        ret = dialog.message(parent,
                             '\n'.join(['Selected MDS+ server is different from your default setting',
                                        'Do you want to use this server as your default server?']),
                             'MDS+ server setting',
                             4, icon=wx.ICON_QUESTION)
#           print ret
        if ret == 'yes':
            v['server'] = str(value[4][0])
            p.write_setting('mdsplus.default_mdsserver', v)

#   def pref_setting(parent, setting):
#       pass
