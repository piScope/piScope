import wx

class FindPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id, style = wx.FRAME_FLOAT_ON_PARENT|wx.CLOSE_BOX)

        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        sizer = self.GetSizer()
        label = wx.StaticText(self)
        label.SetLabel('Find : ')
        from ifigure.utils.edit_list import TextCtrlCopyPasteGeneric    
        self.txt = TextCtrlCopyPasteGeneric(self, wx.ID_ANY, '', 
                               style=wx.TE_PROCESS_ENTER)

        self.btn_bw = wx.Button(self, wx.ID_ANY, '<', size = (30, -1))
        self.btn_fw = wx.Button(self, wx.ID_ANY, '>', size = (30, -1))        
        self.btn_cl = wx.Button(self, wx.ID_ANY, 'x', size = (30, -1))                               
       
        self.Bind(wx.EVT_BUTTON, parent.onHitFW, self.btn_fw)
        self.Bind(wx.EVT_BUTTON, parent.onHitBW, self.btn_bw)
        self.Bind(wx.EVT_BUTTON, parent.onHitCL, self.btn_cl)        
        self.Bind(wx.EVT_TEXT_ENTER, parent.onRunFind, self.txt)
        
        sizer.Add(label, 0, wx.ALL)        
        sizer.Add(self.txt, 1, wx.ALL|wx.EXPAND)
        sizer.Add(self.btn_bw, 0, wx.ALL)
        sizer.Add(self.btn_fw, 0, wx.ALL)        
        sizer.Add(self.btn_cl, 0, wx.ALL)        
        self.Layout()
    def get_find_text(self):
        return str(self.txt.GetValue())
   
class PanelWithFindPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.find_panel = FindPanel(self, wx.ID_ANY)
        self._find_shown = False
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        
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
        
    def onHitCL(self, evt):
        self.ToggleFindPanel()

    def onHitFW(self, evt):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        txt = self.find_panel.get_find_text()

        l1, l2 = stc.GetSelection()        
        for i in range(l2-l1): stc.CharRight()        
        stc.SearchAnchor() 
        flag = stc.SearchNext(0, txt)
        if flag != -1:
            l1, l2 = stc.GetSelection()
            stc.SetCurrentPos(l2)
            stc.SetSelection(l1, l2)            
        stc.EnsureCaretVisible()
        evt.Skip()
        
    def onHitBW(self, evt):
        nb = self.GetChildren()[1]
        stc = nb.GetCurrentPage()
        txt = self.find_panel.get_find_text()

        stc.SearchAnchor()         
        flag = stc.SearchPrev(0, txt)
        if flag != -1:
            l1, l2 = stc.GetSelection()
            stc.SetCurrentPos(l1)
            stc.SetSelection(l1, l2)
        stc.EnsureCaretVisible()

        
        evt.Skip()
        
    def onRunFind(self, evt):
        self.onHitFW(evt)
        evt.Skip()
        
        

