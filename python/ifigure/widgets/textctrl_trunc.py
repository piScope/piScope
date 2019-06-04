import wx
from wx import TextCtrl
from ifigure.utils.edit_list import TextCtrlCopyPasteGeneric as TextCtrl

font_h = None
font_w = None
font = None


def set_default_font():
    size = 12
    globals()['font'] = wx.Font(pointSize=size, family=wx.DEFAULT,
                                style=wx.NORMAL,  weight=wx.NORMAL,
                                faceName='Consolas')
    globals()['font_label'] = wx.Font(pointSize=size, family=wx.DEFAULT,
                                      style=wx.NORMAL,  weight=wx.BOLD,
                                      faceName='Consolas')
    dc = wx.ScreenDC()
    dc.SetFont(font)
    w, h = dc.GetTextExtent('A')
    globals()['font_h'] = h*1.5
    globals()['font_w'] = w


def truncate_str(txt, l):
    l = int(l)
    if len(txt) < l:
        return txt
    if l > 8:
        return txt[:3]+'...'+txt[-(l-6):]
    elif l > 3:
        return txt[:l-3]+'...'
    elif l > 0:
        return txt[:l]
    else:
        return ''


class TextCtrlTrunc(TextCtrl):
    def __init__(self, *args, **kargs):
        set_default_font()
        TextCtrl.__init__(self, *args, **kargs)
        self.SetFont(font)
        self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self._data = ''
        self._mode = 'trunc'

    def SetValue(self, value):
        self._data = value
        if self._mode != 'trunc':
            return TextCtrl.SetValue(self, value)
        w, h = self.GetClientSize()
        if self.HasFocus():
            return TextCtrl.SetValue(self, value)
        else:
            value = truncate_str(value, w/font_w)
            TextCtrl.SetValue(self, value)

#    def GetValue(self):
#        return self._data

    def onSetFocus(self, evt):
        #        print 'set focus'
        self.SetValue(self._data)
        evt.Skip()

    def onKillFocus(self, evt):
        #        print 'kill focus'
        self._mode = 'trunc'
        evt.Skip()
        wx.CallAfter(self.SetValue, self._data)

    def onSize(self, evt):
        #        print 'kill focus'
        self.SetValue(self._data)
        evt.Skip()
