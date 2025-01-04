import os
import wx
from ifigure.utils.wx3to4 import GridSizer


class FindPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id,
                          style=wx.FRAME_FLOAT_ON_PARENT | wx.CLOSE_BOX)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(hsizer)

        self.btn_cl = wx.Button(self, wx.ID_CLOSE, 'x', style=wx.BU_EXACTFIT)
        sizer0 = wx.BoxSizer(wx.VERTICAL)

        hsizer.Add(sizer0, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        hsizer.Add(self.btn_cl, 0, wx.ALL | wx.ALIGN_TOP)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer0.Add(sizer, 1, wx.EXPAND | wx.ALL, 1)
        sizer0.Add(sizer2, 1, wx.EXPAND | wx.ALL, 1)
        label = wx.StaticText(self)
        label.SetLabel('Find : ')
        label2 = wx.StaticText(self)
        label2.SetLabel('Replace : ')
        from ifigure.utils.edit_list import TextCtrlCopyPasteGeneric
        self.txt = TextCtrlCopyPasteGeneric(self, wx.ID_ANY, '',
                                            style=wx.TE_PROCESS_ENTER)
        self.txt2 = TextCtrlCopyPasteGeneric(self, wx.ID_ANY, '',
                                             style=wx.TE_PROCESS_ENTER)
        self.btn_bw = wx.Button(self, wx.ID_ANY, 'Backward')
        self.btn_fw = wx.Button(self, wx.ID_ANY, 'Forward')
        gsizer = GridSizer(1, 2)
        gsizer.Add(self.btn_bw, wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        gsizer.Add(self.btn_fw, wx.ALL | wx.ALIGN_CENTER_VERTICAL)

        #from ifigure.ifigure_config import icondir
        #imageFile =os.path.join(icondir, '16x16', 'close.png')
        # bitmap=wx.Bitmap(imageFile)
        #self.btn_cl = wx.BitmapButton(self, bitmap=bitmap)

        self.Bind(wx.EVT_BUTTON, parent.onHitFW, self.btn_fw)
        self.Bind(wx.EVT_BUTTON, parent.onHitBW, self.btn_bw)
        self.Bind(wx.EVT_BUTTON, parent.onHitCL, self.btn_cl)
        self.Bind(wx.EVT_TEXT_ENTER, parent.onRunFind, self.txt)

        self.btn_replace = wx.Button(self, wx.ID_ANY, 'Replace')
        self.btn_replaceall = wx.Button(self, wx.ID_ANY, 'Replace All')
        self.Bind(wx.EVT_BUTTON, parent.onReplace, self.btn_replace)
        self.Bind(wx.EVT_BUTTON, parent.onReplaceAll, self.btn_replaceall)

        sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.txt, 1, wx.ALL | wx.EXPAND)
        sizer.Add(gsizer, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(label2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sizer2.Add(self.txt2, 1, wx.ALL | wx.EXPAND)
        sizer2.Add(self.btn_replace, 0, wx.ALL | wx.EXPAND)
        sizer2.Add(self.btn_replaceall, 0, wx.ALL | wx.EXPAND)

        self.Layout()
        self.Fit()

    def get_find_text(self):
        return str(self.txt.GetValue())

    def get_replace_text(self):
        return str(self.txt2.GetValue())


class PanelWithFindPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.find_panel = FindPanel(self, wx.ID_ANY)
        self._find_shown = False
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self._find_mode = 'forward'

    def ToggleFindPanel(self):
        if self._find_shown:
            nb = self.GetChildren()[1]
            stc = nb.GetCurrentPage()
            stc.SetFocus()
            self.GetSizer().Detach(self.find_panel)
            self._find_shown = False
        else:
            self.GetSizer().Add(self.find_panel, 0, wx.EXPAND)
            self._find_shown = True
        self.Layout()

    def get_findpanel_shown(self):
        return self._find_shown

    def onHitCL(self, evt):
        self.ToggleFindPanel()

    def find_forward(self):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        txt = self.find_panel.get_find_text()

        l1, l2 = stc.GetSelection()
        for i in range(l2-l1):
            stc.CharRight()
        stc.SearchAnchor()
        flag = stc.SearchNext(0, txt)
        if flag != -1:
            l1, l2 = stc.GetSelection()
            stc.SetCurrentPos(l2)
            stc.SetSelection(l1, l2)
        return flag

    def find_backward(self):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        txt = self.find_panel.get_find_text()

        stc.SearchAnchor()
        flag = stc.SearchPrev(0, txt)
        if flag != -1:
            l1, l2 = stc.GetSelection()
            stc.SetCurrentPos(l1)
            stc.SetSelection(l1, l2)
        return flag

    def onHitFW(self, evt):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        flag = self.find_forward()
        stc.EnsureCaretVisible()
        self._find_mode = 'forward'
        evt.Skip()

    def onHitBW(self, evt):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        flag = self.find_backward()
        stc.EnsureCaretVisible()
        self._find_mode = 'backward'
        evt.Skip()

    def onRunFind(self, evt):
        self.onHitFW(evt)
        evt.Skip()

    def replace_once(self):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        txt = self.find_panel.get_replace_text()
        if len(txt) != 0:
            l1, l2 = stc.GetSelection()
            if l1 == l2:
                return False
            stc.Replace(l1, l2, txt)
            if self._find_mode == 'forward':
                flag = self.find_forward()
            else:
                flag = self.find_backward()
            stc.EnsureCaretVisible()
            return flag != -1
        return False

    def onReplace(self, evt):
        flag2 = self.replace_once()
        evt.Skip()

    def onReplaceAll(self, evt):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()

        pos = stc.GetCurrentPos()

        txt = self.find_panel.get_find_text()
        rtxt = self.find_panel.get_replace_text()
        while 1:
            stc.SetCurrentPos(0)
            stc.SearchAnchor()
            flag = stc.SearchNext(0, txt)
            if flag == -1:
                break
            stc.ReplaceSelection(rtxt)

        stc.EnsureCaretVisible()
        evt.Skip()
