import wx
import sys
import time
import wx.aui as aui
import ifigure
import ifigure.events


class HGDiffWindow(wx.MiniFrame):
    def __init__(self, result, *args, **kargs):
        wx.MiniFrame.__init__(self, *args,
                              style=wx.CAPTION |
                              wx.CLOSE_BOX |
                              wx.MINIMIZE_BOX |
                              wx.RESIZE_BORDER |
                              wx.FRAME_FLOAT_ON_PARENT)
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        vbox.Add(panel, 1, wx.EXPAND | wx.ALL, 5)

        self.nb = aui.AuiNotebook(panel)
        bpanel = wx.Panel(panel)
        button = wx.Button(bpanel, wx.ID_ANY, "Done")
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        panel.SetSizer(vbox)
        vbox.Add(self.nb, 1, wx.EXPAND)
        vbox.Add(bpanel, 0, wx.EXPAND | wx.ALL, 5)

        hbox.AddStretchSpacer()
        hbox.Add(button, 0, wx.EXPAND | wx.ALL, 2)
        bpanel.SetSizer(hbox)

        #sys.stdout = RedirectOutput(self.log)
        #sys.stderr = RedirectOutput(self.log)

        for k, r in enumerate(result):
            log = wx.TextCtrl(self.nb, -1,
                              style=wx.TE_MULTILINE | wx.TE_READONLY)
            log.AppendText(r['diff'])
            self.nb.AddPage(log,  r['filename'])

        button.Bind(wx.EVT_BUTTON, self.onClose)
        self.Show()
        self.SetTitle('HG diff result')

    def onClose(self, evt):
        self.Close()
        import ifigure.mto.hg_support
        ifigure.mto.hg_support.diffwindow = None
