'''
mini frame with window list

   support accelerator so that F1, F2 key works
   on miniframe
'''

import wx

class MiniFrameWithWindowList(wx.MiniFrame):
    def __init__(self, *args, **kargs):
        super(MiniFrameWithWindowList, self).__init__(*args, **kargs)

        frame = self.GetParent()
        self._atable = []
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))   
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)
        self.Bind(wx.EVT_MENU, lambda evt: frame.ProcessEvent(evt))

class DialogWithWindowList(wx.Dialog):
    def __init__(self, *args, **kargs):
        style = kargs.pop('style', wx.DEFAULT_DIALOG_STYLE)
#        kargs['style'] = style|wx.STAY_ON_TOP
        kargs['style'] = style
        super(DialogWithWindowList, self).__init__(*args, **kargs)

        frame = self.GetParent()
        self._atable = []
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))   
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)
        self.Bind(wx.EVT_MENU, lambda evt: frame.ProcessEvent(evt))
#        wx.CallAfter(self.Fit)        
        


