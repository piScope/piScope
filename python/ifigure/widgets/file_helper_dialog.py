import wx
from ifigure.utils.setting_parser import iFigureSettingParser as SP
from ifigure.utils.edit_list import EditListPanel
import ifigure.widgets.dialog as dialog

pref = 'pref.file_helper'


class FileHelperDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="File Action Setting"):

        p = SP().set_rule('file',
                          {'name': '', 'ext': '', 'action': '',
                           'action_txt': '', 'use': False})
        self.var = p.read_setting(pref)

        wx.Dialog.__init__(self, parent, id, title,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.mainSizer)

        self.cb = wx.ComboBox(self, wx.ID_ANY,
                              size=(-1, -1),
                              style=wx.CB_READONLY,
                              choices=[x['name'] for x in self.var['file']])
        self.mainSizer.Add(self.cb, 0, wx.ALL, 3)

        l = [["rule",   '', 200, None],
             ["action", '', 235, {'nlines': 3}],
             ["note", '', 0, None],
             [None, False, 3,  {'text': 'Use'}], ]

        self.elp = EditListPanel(self, l, edge=0, call_sendevent=self)
        self.elp.GetSizer().AddGrowableRow(1)

        self.mainSizer.Add(self.elp, 1, wx.ALL | wx.EXPAND, 2)

        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bnew = wx.Button(self, label="New...", id=wx.ID_ANY)
        self.bdel = wx.Button(self, label="Delete...", id=wx.ID_ANY)
        self.bok = wx.Button(self, label="OK", id=wx.ID_OK)

        self.buttonSizer.Add(self.bnew, 0, wx.ALL, 7)
        self.buttonSizer.Add(self.bdel, 0, wx.ALL, 7)
        self.buttonSizer.AddStretchSpacer(1)
        self.buttonSizer.Add(self.bok, 0, wx.ALL, 7)
        self.mainSizer.Add(self.buttonSizer, 0, wx.ALL | wx.EXPAND, 0)
        self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onNew, self.bnew)
        self.Bind(wx.EVT_BUTTON, self.onDel, self.bdel)
        self.cb.Bind(wx.EVT_COMBOBOX, self.onCBHit)
        wx.CallAfter(self.Layout)

        self.set_panels_2_index0()

    def send_event(self, elp, evt0):
        for v in self.var['file']:
            if v['name'] == str(self.cb.GetValue()):
                value = self.elp.GetValue()
                v['ext'] = value[0]
                v['action'] = value[1]
                v['action_txt'] = value[2]
                v['use'] = value[3]
                break

    def set_elp(self):
        vv = self.var['file']
        for v in vv:
            if v['name'] == str(self.cb.GetValue()):
                self.elp.SetValue((str(v['ext']),
                                   str(v['action']),
                                   str(v['action_txt']), v['use']))
                break

    def update_cb(self):
        names = self.get_names()
        self.cb.Clear()
        for x in names:
            self.cb.Append(x)

    def get_names(self):
        names = [x['name'] for x in self.var['file']]
        return names

    def onCBHit(self, evt):
        for v in self.var['file']:
            if v['name'] == self._cb_value:
                value = self.elp.GetValue()
                v['ext'] = value[0]
                v['action'] = value[1]
                v['action_txt'] = value[2]
                v['use'] = value[3]
        self.set_elp()
        self._cb_value = str(self.cb.GetValue())

    def onOk(self, evt):
        for v in self.var['file']:
            if v['name'] == self._cb_value:
                value = self.elp.GetValue()
                v['ext'] = value[0]
                v['action'] = value[1]
                v['action_txt'] = value[2]
                v['use'] = value[3]
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def onDel(self, evt):
        vv = self.var['file']
        self.var['file'] = [v for v in vv if v['name']
                            != str(self.cb.GetValue())]
        self.set_panels_2_index0()

    def set_panels_2_index0(self):
        names = self.get_names()
        self.update_cb()
        self.cb.SetValue(names[0])
        self._cb_value = names[0]
        self.set_elp()

    def onNew(self, evt):
        ret, new_name = dialog.textentry(self,
                                         "Enter the name of file type",
                                         "Add New FileType", '')
        if not ret:
            return
        if not new_name in self.get_names():
            v = {'name': new_name, 'ext': '*.*',
                 'action': '', 'action_txt': '', 'use': True}
        self.var['file'].append(v)
        self.update_cb()
        self.cb.SetValue(new_name)
        self._cb_value = new_name
        self.set_elp()


class Handler(object):
    def __init__(self, parent):
        pass

    def on_button(self, ev):
        parent_window = ev.GetEventObject().GetTopLevelParent()
        dlg = FileHelperDialog(parent_window)
        a = dlg.ShowModal()
        if a == wx.ID_OK:
            p = SP().set_rule('file',
                              {'name': '', 'ext': '', 'action': '',
                               'action_txt': '', 'use': False})
            p.write_setting(pref, dlg.var)

    def get_value(self):
        return None

    def set_value(self, v):
        pass


def get_handler(parent):
    return Handler(parent)
