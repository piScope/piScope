from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED

import wx


def elp2dic(l, value):
    ret = {}
    for a, b in zip(l, value):
        if a[0] is None:
            continue
        ret[a[0]] = b
    return ret


def dict2elp(l, d):
    return [d[ll[0]] for ll in l]


class DialogSpineSetting(wx.Dialog):
    def __init__(self, parent, id, title='',
                 style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                 value_in=None,  choices=['normal', 'strange']):
        wx.Dialog.__init__(self, parent, id, title, style=style)

        s1 = {"style": wx.CB_READONLY,
              "choices": choices}
        s2 = {"style": wx.CB_READONLY,
              "choices": ['outward', 'axes', 'data']}
        s3 = {"style": wx.TE_PROCESS_ENTER,
              "choices": ["0.0", "1.0"]}

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.l0 = [["label",  s1["choices"][0], 4, s1, ], ]
        self.elp0 = EditListPanel(self, self.l0)
        self.nb = wx.Notebook(self)
        self.l2 = [
            ["loc. ref",  s2["choices"][0], 104, s2, ],
            ["loc. value",  s3["choices"][0],  4, s3, ],
            ["face", 'k', 206, {}],
            ["edge",   'k', 206, {}],
            ["width",    1.0, 107, {}],
            ["style",   'solid', 10, {}],
            ["alpha",   1.0, 105, {}], ]
        i = 0
        self.elp1 = EditListPanel(self.nb, self.l2)
        self.nb.AddPage(self.elp1, 'spine1')
        self.elp2 = EditListPanel(self.nb, self.l2)
        self.nb.AddPage(self.elp2, 'spine2')

        vbox.Add(self.elp0, 0, wx.EXPAND | wx.ALL, 1)
        vbox.Add(self.nb, 1, wx.EXPAND | wx.ALL, 10)
        sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if sizer is not None:
            vbox.Add(sizer, 0, wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(vbox)
        if 'label' in value_in:
            self.elp0.SetValue([value_in['label']])
            self.elp1.SetValue(dict2elp(self.l2, value_in['spine1']))
            self.elp2.SetValue(dict2elp(self.l2, value_in['spine2']))
        self.Layout()
        wx.CallAfter(self._myRefresh)

        self.Bind(EDITLIST_CHANGED, self.onELP_Changed)
        self.Bind(EDITLIST_CHANGED, self.onELP_Changed)

    def GetValue(self):
        ret = elp2dic(self.l0, self.elp0.GetValue())
        ret['spine1'] = elp2dic(self.l2, self.elp1.GetValue())
        ret['spine2'] = elp2dic(self.l2, self.elp2.GetValue())
        return ret

    def onELP_Changed(self, evt):
        value = evt.elp.GetValue()
        if evt.widget_idx == 6:  # alpha
            if value[6] is None:
                return
            v2 = [x for x in value[2]]
            v2[-1] = value[6]
            v3 = [x for x in value[3]]
            v3[-1] = value[6]
            value[2] = v2
            value[3] = v3
            evt.elp.SetValue(value)

        elif evt.widget_idx == 2:  # face
            if not any(value[2]):
                value[6] = None
            evt.elp.SetValue(value)
        elif evt.widget_idx == 3:  # edge
            if not any(value[3]):
                value[6] = None
            evt.elp.SetValue(value)
        pass

    def _myRefresh(self):
        win = self.GetTopLevelParent()
#        win.SetSizeHints(win)
        win.Fit()
        win.Layout()


def ask_setting(parent, value_in, choices):
    dia = DialogSpineSetting(parent, wx.ID_ANY, title='Spine Setting',
                             value_in=value_in,
                             choices=choices)
    val = dia.ShowModal()
    value = dia.GetValue()
    dia.Destroy()
    if val != wx.ID_OK:
        return False, None

    return True, value
