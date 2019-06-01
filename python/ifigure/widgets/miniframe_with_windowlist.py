'''
mini frame with window list

   support accelerator so that F1, F2 key works
   on miniframe
'''

import wx


class WithWindowList_MixIn(object):
    def __init__(self):
        super(WithWindowList_MixIn, self).__init__()

        frame = self.GetParent()
        self._atable = []
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)
        self.Bind(wx.EVT_MENU, lambda evt: frame.ProcessEvent(evt))


class MiniFrameWithWindowList(wx.MiniFrame, WithWindowList_MixIn):
    def __init__(self, *args, **kargs):
        super(MiniFrameWithWindowList, self).__init__(*args, **kargs)
        WithWindowList_MixIn.__init__(self)
        '''
        frame = self.GetParent()
        self._atable = []
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))   
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)
        self.Bind(wx.EVT_MENU, lambda evt: frame.ProcessEvent(evt))
        '''


class DialogWithWindowList(wx.Dialog, WithWindowList_MixIn):
    def __init__(self, *args, **kargs):
        style = kargs.pop('style', wx.DEFAULT_DIALOG_STYLE)
        kargs['style'] = style
        super(DialogWithWindowList, self).__init__(*args, **kargs)
        WithWindowList_MixIn.__init__(self)

        '''
        frame = self.GetParent()
        self._atable = []
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self._atable.append((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))   
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)
        self.Bind(wx.EVT_MENU, lambda evt: frame.ProcessEvent(evt))
        '''
