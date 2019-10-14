import wx
import wx.stc as stc


class Tipwindow(wx.MiniFrame):
    def __init__(self, *args, **kargs):
        wx.MiniFrame.__init__(self, *args,
                              style=wx.CAPTION |
                              wx.CLOSE_BOX |
                              wx.MINIMIZE_BOX |
                              wx.RESIZE_BORDER |
                              wx.FRAME_FLOAT_ON_PARENT)
        vbox = wx.BoxSizer(wx.VERTICAL)

        panel = wx.Panel(self, wx.ID_ANY)
        panel.SetSizer(vbox)
       # self.tip = wx.StaticText(panel, -1,
       #                          style=wx.TE_MULTILINE)#|wx.TE_READONLY|wx.VSCROLL)
       # self.tip.SetBackgroundColour((255,255,0))
        self.tip = stc.StyledTextCtrl(panel, -1)
        self.tip.SetMarginWidth(0, 0)
        self.tip.SetMarginWidth(1, 0)
        self.tip.SetMarginWidth(2, 0)
        self.tip.SetReadOnly(True)
        self.tip.StyleSetBackground(wx.stc.STC_STYLE_DEFAULT, (255, 255, 0))

        vbox.Add(self.tip, 1, wx.EXPAND | wx.ALL, 5)
        self.Bind(wx.EVT_CLOSE, self.onWindowClose)
        self.Bind(wx.EVT_ACTIVATE, self.onActivate)
        #panel.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
        #panel.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
        #self.tip.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
        #self.tip.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
        self.Hide()

#    def update(self, func):
    def update(self, name, argspec, tip):
        #        if hasattr(func, '__doc__'):
        try:
            #                self.tip.SetLabel(func.__doc__)
            self.tip.SetReadOnly(False)
            self.tip.SetText(tip)
            self.tip.StyleClearAll()
            self.tip.SetReadOnly(True)
        except:
            pass

    def onActivate(self, e):
        return
        if e.GetActive():
            self.SetTransparent(255)
        else:
            self.SetTransparent(120)

    def onWindowClose(self, e):
        self.Hide()
        e.Veto()
