# Very minimalist password entry dialogue
import wx
from ifigure.utils.wx3to4 import FlexGridSizer


class UsernamePasswordDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="Enter password", label="Enter Password;"):
        wx.Dialog.__init__(self, parent, id, title,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, label=label)

        sizer = FlexGridSizer(2, 2)
        sizer.AddGrowableCol(1, 1)
        st1 = wx.StaticText(self, label="Name")
        self.field = wx.TextCtrl(self, value="", size=(-1, -1))
        st2 = wx.StaticText(self, label="Password")
        self.field2 = wx.TextCtrl(
            self, value="", size=(-1, -1), style=wx.TE_PASSWORD)
        sizer.Add(st1, 0, wx.ALL, 2)
        sizer.Add(self.field, 1, wx.ALL | wx.EXPAND, 2)
        sizer.Add(st2, 0, wx.ALL, 2)
        sizer.Add(self.field2, 1, wx.ALL | wx.EXPAND, 2)

        self.okbutton = wx.Button(self, label="OK", id=wx.ID_OK)
        self.cancelbutton = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        self.mainSizer.Add(self.label, 0, wx.ALL, 8)
        self.mainSizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)
        self.buttonSizer.Add(self.okbutton, 0, wx.ALL, 8)
        self.buttonSizer.Add(self.cancelbutton, 0, wx.ALL, 8)
        self.mainSizer.Add(self.buttonSizer, 0, wx.ALL, 0)
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        #self.Bind(wx.EVT_TEXT_ENTER, self.onOK)
        self.SetSizer(self.mainSizer)
        self.Fit()
        self.Centre()
        self.result = None

#    def onClose(self):

    def onOK(self, event):
        self.result = [self.field.GetValue(), self.field2.GetValue()]
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def onCancel(self, event):
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()


class PasswordDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="Enter password", label="Enter Password;"):
        wx.Dialog.__init__(self, parent, id, title)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label = wx.StaticText(self, label=label)
        self.field = wx.TextCtrl(self, value="", size=(
            300, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        self.okbutton = wx.Button(self, label="OK", id=wx.ID_OK)
        self.cancelbutton = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        self.mainSizer.Add(self.label, 0, wx.ALL, 8)
        self.mainSizer.Add(self.field, 0, wx.ALL, 8)
        self.buttonSizer.Add(self.okbutton, 0, wx.ALL, 8)
        self.buttonSizer.Add(self.cancelbutton, 0, wx.ALL, 8)
        self.mainSizer.Add(self.buttonSizer, 0, wx.ALL, 0)
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_TEXT_ENTER, self.onOK)
        self.SetSizer(self.mainSizer)
        self.Fit()
        self.result = None

    def onOK(self, event):
        self.result = self.field.GetValue()
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def onCancel(self, event):
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()
