from __future__ import print_function
from ifigure.utils.edit_list import TextCtrlCopyPaste
import wx
import numpy as np
GTC_ENTER = wx.NewEventType()
EVT_GTC_ENTER = wx.PyEventBinder(GTC_ENTER, 1)


class GrowableTextCtrl(TextCtrlCopyPaste):
    def __init__(self, *args, **kargs):
        #        kargs['style']=wx.TE_PROCESS_ENTER|wx.TE_MULTILINE
        kargs['style'] = wx.TE_MULTILINE
        super(GrowableTextCtrl, self).__init__(*args, **kargs)
        self.SetBackgroundColour('yellow')
        self._use_escape = False
        if len(args) > 2:
            self.setText(args[2])
        else:
            self.setText('')

    def onKeyPressed(self, evt):
        super(GrowableTextCtrl, self).onKeyPressed(evt)

        def check_length(evt, obj=self):
            try:
                ttt = obj.GetValue()
            except ValueError:
                obj.Unbind(wx.EVT_IDLE)
                return
            obj.setText(ttt)
            obj.Layout()
            obj.Unbind(wx.EVT_IDLE)
        self.Bind(wx.EVT_IDLE, check_length)

    def setText(self, txt):
        def screen_size(xx):
            pos = np.array(xx.GetPosition())
            size = np.array(xx.GetSize())
            return pos[0], pos[1], pos[0]+size[0], pos[1]+size[1]

        l = self.GetInsertionPoint()
        self.SetValue(txt)
        self.SetInsertionPoint(l)

        num = self.GetNumberOfLines()
        length = max(self.GetLineLength(x) for x in range(num))
        s = self.GetFullTextExtent('A')
        ss = np.array([self.GetFullTextExtent(self.GetLineText(x))
                       for x in range(num)])

        self.SetSize(
            (np.max(ss[:, 0])+25, np.max([np.max(ss[:, 1]), s[1]])*num+10))

        x0, y0, x1, y1 = screen_size(self)
        x0p, y0p, x1p, y1p = screen_size(self.GetParent())

        # moves control so that it stays inside the parent object
        # it takes care of running out of the parent box toward right.
        # it doesn't do anything if it is exceeding toweard lef too.
        if x1p < x1:
            dx = x1 - x1p + 1
            if x0 > dx:
                self.SetPosition((x0 - dx, y0))

    def onEnter(self, evt):
        evt2 = wx.PyCommandEvent(GTC_ENTER, wx.ID_ANY)
        evt2.SetEventObject(self)
        wx.PostEvent(self, evt2)


class test_frame(wx.Frame):
    def __init__(self, *args, **kargs):
        wx.Frame.__init__(self, *args, **kargs)
        panel = wx.Panel(self, wx.ID_ANY)
        panel.SetSize((350, 550))
        # self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        #self.GetSizer().Add(panel, 1, wx.ALL, 0)
        #self.txt = TransparentTextCtrlPanel(self, wx.ID_ANY)
        self.txt = GrowableTextCtrl(panel, wx.ID_ANY, '')
        self.txt.SetPosition((120, 10))
        self.txt.SetSize((3, 3))
        self.Layout()
        self.Show()
        self.Bind(EVT_GTC_ENTER, self.onEnter)

    def onEnter(self, evt):
        print('hit enter')


if __name__ == '__main__':
    app = wx.App(False)
    frame = test_frame(None, wx.ID_ANY, "test")
    app.MainLoop()
