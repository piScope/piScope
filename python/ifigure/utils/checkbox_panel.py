'''
   CheckBoxs
     Show array of CheckBoxs to ask user to select 
     items.

     checkbox_panel(parent, col = 4, 
                   labels = ('label 1', 'label 2', 'label 3'),
                   values = (False, False, True),
                   message = 'head line message',
                   title = 'dialog title'):


     return value [(label1, True/False), ...]

'''
import wx
import math
import ifigure.utils.cbook as cbook
from ifigure.utils.wx3to4 import GridSizer


class CheckBoxs(wx.Panel):
    def __init__(self, *args, **kargs):
        setting = kargs['setting']
        del kargs['setting']
        wx.Panel.__init__(self, *args, **kargs)

        labels = setting['labels']
        row = math.ceil(float(len(labels))/setting['col'])

        sizer = GridSizer(row, setting['col'])
        self.SetSizer(sizer)

        self.child = []
        for k, label in enumerate(labels):
            p = wx.CheckBox(self, wx.ID_ANY, label)
            self.child.append(p)
            r = k/setting['col']
            c = k - r*setting['col']
#           print r, c
            sizer.Add(p, 1, wx.EXPAND)
            p.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
            p.Bind(wx.EVT_CHECKBOX, self.onHitCheck)
        self.Layout()
        self.labels = labels
        self._init = False

    def GetValue(self):
        return [(l, c.GetValue()) for l, c in zip(self.labels, self.child)]

    def SetValue(self, values):
        for k, v in enumerate(values):
            self.child[k].SetValue(v)
        if not self._init:
            self._init = True
            self._init_values = values

    def SelAll(self, evt=None):
        self.SetValue([True]*len(self.child))

    def UnselAll(self, evt=None):
        self.SetValue([False]*len(self.child))

    def ResetChecks(self, evt=None):
        self.SetValue(self._init_values)

    def onHitCheck(self, evt):
        evt.SetEventObject(self)
        if hasattr(self.GetParent(), "send_event"):
            self.GetParent().send_event(self, evt)
        
    def onRightUp(self, evt):
        l = [('Select all',   self.SelAll, None),
             ('Clear all',    self.UnselAll, None), ]
        menu = wx.Menu()
        f1 = menu.Append(wx.ID_ANY, 'Select All')
        self.Bind(wx.EVT_MENU, self.SelAll, f1)
        f2 = menu.Append(wx.ID_ANY, 'Clear All', '')
        self.Bind(wx.EVT_MENU, self.UnselAll, f2)
        f3 = menu.Append(wx.ID_ANY, 'Reset', '')
        self.Bind(wx.EVT_MENU, self.ResetChecks, f3)
        evt.GetEventObject().PopupMenu(menu, evt.GetPosition())
        menu.Destroy()
        evt.Skip()


CheckBoxes = CheckBoxs  # patch work to fix misspell ;D


class CheckboxsDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="CheckBoxDialg", col=4,
                 labels=['A', 'B', 'C'], values=None,
                 message=None, elp=None, blabel='OK'):
        if values is None:
            values = [False]*len(labels)
        self.ovalues = values

        wx.Dialog.__init__(self, parent, id, title)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        setting = {'col': col,
                   'labels': labels}
        if message is not None:
            m = wx.StaticText(self, wx.ID_ANY, message)
            mainSizer.Add(m,  0, wx.ALL, 0)
        self.checkboxs = CheckBoxs(self, wx.ID_ANY, setting=setting)
        sizer.Add(self.checkboxs,  1, wx.ALL | wx.EXPAND, 0)

        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        selall = wx.Button(self, label="Select All", id=wx.ID_ANY)
        selall.Bind(wx.EVT_BUTTON, self.onSelAll)
        unselall = wx.Button(self, label="Unselect All", id=wx.ID_ANY)
        unselall.Bind(wx.EVT_BUTTON, self.onUnselAll)
        reset = wx.Button(self, label="Reset", id=wx.ID_ANY)
        reset.Bind(wx.EVT_BUTTON, self.onReset)
        self.okbutton = wx.Button(self, label=blabel, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)

        self.buttonSizer.Add(reset, 1, wx.ALL | wx.EXPAND, 8)
        self.buttonSizer.Add(selall, 1, wx.ALL | wx.EXPAND, 8)
        self.buttonSizer.Add(unselall, 1, wx.ALL | wx.EXPAND, 8)
        self.buttonSizer.Add(self.okbutton, 1, wx.ALL | wx.EXPAND, 8)

        mainSizer.Add(sizer,  1, wx.ALL | wx.EXPAND, 5)
        mainSizer.Add(self.buttonSizer, 0, wx.ALL, 0)
        self.SetSizer(mainSizer)
        self.Fit()
        self.Centre()
        self.result = None
        self.SetValue(values)
        wx.CallAfter(self._myRefresh)

    def onSelAll(self, event):
        self.checkboxs.SelAll()

    def onUnselAll(self, event):
        self.checkboxs.UnselAll()

    def onReset(self, event):
        self.checkboxs.SetValue(self.ovalues)

    def onOK(self, event):
        self.result = self.GetValue()
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def SetValue(self, value):
        self.checkboxs.SetValue(value)

    def GetValue(self):
        return self.checkboxs.GetValue()

    def _myRefresh(self):
        win = self.GetTopLevelParent()
#        win.SetSizeHints(win)
        win.Fit()
        win.Layout()


def checkbox_panel(parent, col=4,
                   labels=('label 1', 'label 2', 'label 3',
                           'label 4', 'label 5'),
                   values=(False, False, True, True, True),
                   message=None, title='', blabel='OK'):

    dig = CheckboxsDialog(parent, labels=labels, values=values, message=message,
                          title=title, col=col, blabel=blabel)
    dig.SetValue(values)
    a = dig.ShowModal()
    if a == wx.ID_OK:
        v = dig.GetValue()
    else:
        return None
    dig.Destroy()
    return v
