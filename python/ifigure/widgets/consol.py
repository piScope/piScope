import wx
from ifigure.widgets.redirect_output import RedirectOutput


class Consol(wx.Panel):
    def __init__(self, parent, *args, **kargs):
        super(Consol, self).__init__(parent, *args, **kargs)
        self.log = wx.TextCtrl(
            self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log, 1, wx.EXPAND)
        self.SetSizer(sizer)
