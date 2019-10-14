from __future__ import print_function
from ifigure.utils.edit_list import DialogEditListTab
import ifigure.widgets.dialog as dialog
import wx
pkeys = ['experiment', 'default_node', 'x', 'y', 'z',
         'xerr', 'yerr', 'title']


def MDS_setting(parent, setting,  gwparam, mds_server, thread_main):
    def make_gs_arr(gs, s):
        return [gs[key][s] for key in pkeys]

    gs = gwparam.getvar('globalsets')
    gv = gwparam.getvar()
    tab = ['Set1', 'Set2', 'Set3', 'Set4', 'config', 'more']

    list1 = [[None, make_gs_arr(gs, 0), 118, None]]
    list2 = [[None, make_gs_arr(gs, 1), 118, None]]
    list3 = [[None, make_gs_arr(gs, 2), 118, None]]
    list4 = [[None, make_gs_arr(gs, 3), 118, None]]

    txt = "on" if parent.mpanalysis else "off"
    txt2 = "on" if gv['use_shot_global'] else "off"
    txt7 = "on" if parent.init_beginning else "off"
    txt6 = "on" if parent.init_sec else "off"
    txt5 = "on" if parent.init_page else "off"

    list5 = [["MDSconnect", mds_server, 204, None],
             ["Update", gv['event'], 0, None],
             ["Common vars", gv['shot_global'], 0, None],
             ["Use common vars",  txt2,  1, {"values": ["on", "off"]}],
             ["Global setting", gv['global_choice'], 21, None],
             ["Multipage mode",  txt, 1, {"values": ["on", "off"]}],
             #            ["Color Order", gv['color_order'], 22, {}],]
             ]

    tmp2 = [[None,  parent.parallel_sec, 3,
             {"text": 'Parallelize Panels', "noindent": True}], ]
    tmp = [[None,  (parent.parallel_shot, [parent.parallel_sec]), 27,
            ({"text": 'Parallelize Pages'}, {"elp": tmp2})]]
    list6 = [[None, "MDSplus session parallelization",  102, None],
             [None,  (parent.parallel_page,
                      [(parent.parallel_shot, [parent.parallel_sec])]),
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

    value = DialogEditListTab(tab, l, modal=False, tip=tip, parent=parent,
                              title='Global Setting',
                              style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

    if value[0]:
        for m in range(4):
            for i, v in enumerate(value[1][m][0]):
                gs[pkeys[i]][m] = str(v[1])
        gv['event'] = str(value[1][4][1])
        gv['shot_global'] = str(value[1][4][2])
        gv['use_shot_global'] = (value[1][4][3] == 'on')
        gv['global_choice'] = value[1][4][4]
        parent.mpanalysis = (value[1][4][5] == "on")
#      gv['color_order'] = value[1][4][5]

#      parent.init_beginning = (value[1][5][3] == "on")
#      parent.init_page = (value[1][5][4] == "on")
#      parent.init_sec = (value[1][5][5] == "on")

        if not value[1][5][1][0]:
            parent.parallel_page = False
            parent.parallel_shot = False
            parent.parallel_sec = False
        else:
            parent.parallel_page = True
            if not value[1][5][1][1][0][0]:
                parent.parallel_shot = False
                parent.parallel_sec = False
            else:
                parent.parallel_shot = True
                parent.parallel_sec = value[1][5][1][1][0][1][0]

        parent.book.setvar('mdsscript_main',
                           value[1][5][2])
        parent.book.setvar('mdsplus_server',
                           str(value[1][4][0]))

    from ifigure.utils.setting_parser import iFigureSettingParser as SettingParser
    p = SettingParser()
    v = p.read_setting('mdsplus.default_mdsserver')
    if str(v['server']) != str(value[1][4][0]):
        ret = dialog.message(parent,
                             '\n'.join(['Selected MDS+ server is different from your default setting',
                                        'Do you want to use this server as your default server?']),
                             'MDS+ server setting',
                             2, icon=wx.ICON_QUESTION)
        print(ret)
        if ret == 'ok':
            v['server'] = str(value[1][4][0])
            p.write_setting('mdsplus.default_mdsserver', v)

    return value


def pref_setting(parent, setting):
    pass
