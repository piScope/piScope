import wx
import os
import weakref
import ifigure
from ifigure.utils.edit_list import DialogEditListTab
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('dlg_preference')


class PrefComponent(object):
    def __init__(self, cname='Sample'):
        self.name = cname

    def get_dialoglist(self):
        list1 = [["Sample", 'preferred setting', 0, None], ]
        hint1 = [None]
        return list1, hint1

    def set_dialog_result(self, data):
        dprint1('set_dialog_result should be overwritten')

    def save_setting(self):
        dprint1('save_setting should be overwritten')


def dlg_preference(components, parent):

    lists = []
    hints = []
    tabs = []
    for c in components:
        l, h = c.get_dialoglist()
        lists.append(l)
        hints.append(h)
        tabs.append(c.name)

    value = DialogEditListTab(tabs, lists, tip=hints, parent=parent,
                              style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

    if value[0]:
        for i, v in enumerate(value[1]):
            components[i].set_dialog_result(v)
