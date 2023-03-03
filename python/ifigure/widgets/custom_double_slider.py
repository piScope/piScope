from __future__ import print_function
import wx
import os
import numpy as np
import ifigure
from ifigure.utils.wx3to4 import wxBitmapFromImage, wxEmptyBitmapRGBA

CDS_CHANGED = wx.NewEventType()
EVT_CDS_CHANGED = wx.PyEventBinder(CDS_CHANGED, 1)
CDS_CHANGING = wx.NewEventType()
EVT_CDS_CHANGING = wx.PyEventBinder(CDS_CHANGING, 1)


def window_to_bitmap(window):
    w, h = window.GetClientSize()
    bitmap = wxEmptyBitmapRGBA(w, h)
    wdc = wx.ClientDC(window)
    mdc = wx.MemoryDC(bitmap)
    mdc.Blit(0, 0, w, h, wdc, 0, 0)
    data = np.fromstring(bitmap.ConvertToImage().GetData(), np.uint8)
    print(data.reshape((h, w, 3))[0, 0, :])
    return bitmap


class CustomPanel(wx.Panel):
    def OnMCLost(self, evt):
        evt2 = wx.PyCommandEvent(CDS_CHANGED, wx.ID_ANY)
        evt2.SetEventObject(self)
        self.Unbind(wx.EVT_MOTION)
        self.ReleaseMouse()
        wx.PostEvent(self, evt2)

    def MotionEvent(self, val):
        self._generate_motion_event = val

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        self.DoDrawing(dc)

    def OnSize(self, evt):
        self.Refresh(eraseBackground=False)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        self.Refresh()

    def Disable(self):
        wx.Panel.Disable(self)
        self.Refresh()


class CustomSingleSlider(CustomPanel):
    def __init__(self, parent, id,  *args, **kargs):
        wx.Panel.__init__(self, parent, id, *args, **kargs)
        self.parent = parent
        self.font = wx.Font(9, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL,
                            False, 'Courier 10 Pitch')

        from ifigure.ifigure_config import icondir
        path = os.path.join(icondir, 'image', 'slider.png')

        self._bbmp = wxBitmapFromImage(wx.Image(path, wx.BITMAP_TYPE_PNG))
        self._value = [0.5]
        self._range = [0, 1]
        self._sheight = 6
        self._hmargin = 10
        self._vmargin = 3
        self._bheight = self._vmargin*2 + self._sheight
        self._bwidth = 6

        w, h = self._bbmp.GetSize()
        self._bheight = h
        self._bwidth = w
        self._vmargin = (h - self._sheight)/2
        self._b = None
        self._isDrawn = False
        self._generate_motion_event = False
        self.SetMinSize((w*5, h))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE,  self.OnSize)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

    def SetValue(self, value):
        self._value[0] = value
        self.Refresh()

    def GetValue(self):
        return self._value[0]

    def SetRange(self, vrange):
        self._range = vrange
        self.Refresh()

    def GetRange(self):
        return self._range

    def SetSlotHeight(self, h):
        self._sheight = h

    def GetSlotHeight(self, h):
        return self._sheight

    def SetHorizontalMargin(self, h):
        self._hmargin = h

    def GetHorizontalMargin(self):
        return self._hmargin

    def OnMouseEvent(self, evt):
        if not self.IsEnabled():
            return
        if evt.LeftDown():
            x, y = evt.GetPosition()
            w, h = self.GetSize()
            if (abs(y - h/2) > self._sheight):
                return

            w1 = self._calc_w1()
            self._hit = -1
            if abs(x-w1) < self._bwidth:
                self._hit = 0
            if self._hit > -1:
                self.CaptureMouse()
                self.Bind(wx.EVT_MOTION, self.OnMotion)
                self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMCLost)
#              self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        elif evt.LeftUp():
            if self.HasCapture():
                evt2 = wx.PyCommandEvent(CDS_CHANGED, wx.ID_ANY)
                evt2.SetEventObject(self)
                self.Unbind(wx.EVT_MOTION)
                self.ReleaseMouse()
                wx.PostEvent(self, evt2)

    def OnMotion(self, evt):
        if not self.IsEnabled():
            return
        bmw, bmh = self._bbmp.GetSize()
        x, y = evt.GetPosition()
        w, h = self.GetSize()

        delta = abs(self._range[1]-self._range[0])
        dx = (w-2*self._hmargin-bmw)

        new_v = float(x - self._hmargin - bmw/2)/dx*delta + self._range[0]
#        if self._hit == 1 and new_v <= self._value[0]: return
        if new_v > self._range[1]:
            return
        if new_v < self._range[0]:
            return
        self._value[self._hit] = new_v
        self.Refresh()

        if self._generate_motion_event:
            evt2 = wx.PyCommandEvent(CDS_CHANGING, wx.ID_ANY)
            evt2.SetEventObject(self)
            wx.PostEvent(self, evt2)

    def DoDrawing(self, dc=None):

        if self.IsEnabled():
            col1 = '#000000'
            col2 = '#FFFFB8'
            col3 = '#ffafaf'
        else:
            col1 = '#7f7f7f'
            col2 = '#FFFFD8'
            col3 = '#ffdfdf'

        self.Unbind(wx.EVT_PAINT)
        if dc is None:
            dc = wx.ClientDC(self)

        w, h = self.GetSize()

        dc.SetFont(self.font)

        yy = int(h/2 - self._sheight/2 - self._vmargin)
        dc.SetDeviceOrigin(0, yy)


        def draw_box(self, w1, dc):
            dc.DrawBitmap(self._bbmp,
                          int(w1-self._bwidth/2),
                          0, True)
            return

        w1 = self._calc_w1()

        dc.SetPen(wx.Pen(col1))
        dc.SetBrush(wx.Brush(col2))
        dc.DrawRoundedRectangle(int(self._hmargin),
                                int(self._vmargin),
                                int(w-2*self._hmargin),
                                int(self._sheight),
                                2.0)
        dc.SetPen(wx.Pen(col1))
        dc.SetBrush(wx.Brush(col3))

        draw_box(self, w1, dc)
#        draw_box(self, w2, dc)

        self._isDrawn = True
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _calc_w1(self):
        bmw, bmh = self._bbmp.GetSize()
        w, h = self.GetSize()
        delta = abs(self._range[1]-self._range[0])
        w1 = ((w-2*self._hmargin-bmw) / delta * (self._value[0] - self._range[0]) +
              self._hmargin + bmw/2)
        return w1


class CustomDoubleSlider(CustomPanel):
    def __init__(self, parent, id,  *args, **kargs):
        wx.Panel.__init__(self, parent, id, *args, **kargs)
        self.parent = parent
        self.font = wx.Font(9, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL,
                            False, 'Courier 10 Pitch')

        from ifigure.ifigure_config import icondir
        path = os.path.join(icondir, 'image', 'slider.png')

        self._bbmp = wxBitmapFromImage(wx.Image(path, wx.BITMAP_TYPE_PNG))
        self._value = [0.1, 0.9]
        self._range = [0, 1]
        self._sheight = 6
        self._hmargin = 10
        self._vmargin = 3
        self._bheight = self._vmargin*2 + self._sheight
        self._bwidth = 6

        w, h = self._bbmp.GetSize()
        self._bheight = h
        self._bwidth = w
        self._vmargin = (h - self._sheight)/2
        self._b = None
        self._isDrawn = False
        self._generate_motion_event = False
        self.SetMinSize((w*5, h))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE,  self.OnSize)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

    def SetValue(self, value):
        self._value = value
        self.Refresh()

    def GetValue(self):
        return self._value

    def SetRange(self, vrange):
        self._range = vrange
        self.Refresh()

    def GetRange(self):
        return self._range

    def SetSlotHeight(self, h):
        self._sheight = h

    def GetSlotHeight(self, h):
        return self._sheight

    def SetHorizontalMargin(self, h):
        self._hmargin = h

    def GetHorizontalMargin(self):
        return self._hmargin

    def OnMouseEvent(self, evt):
        if not self.IsEnabled():
            return
        if evt.LeftDown():
            x, y = evt.GetPosition()
            w, h = self.GetSize()
            if (abs(y - h/2) > self._sheight):
                return

            w1, w2 = self._calc_w1_w2()
            self._hit = -1
            if abs(x-w1) < self._bwidth:
                self._hit = 0
            if abs(x-w2) < self._bwidth:
                self._hit = 1
            if self._hit > -1:
                self.Bind(wx.EVT_MOTION, self.OnMotion)
                self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMCLost)
                self.CaptureMouse()
#              self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        elif evt.LeftUp():
            if self.HasCapture():
                evt2 = wx.PyCommandEvent(CDS_CHANGED, wx.ID_ANY)
                evt2.SetEventObject(self)
                self.Unbind(wx.EVT_MOTION)
                self.ReleaseMouse()
                wx.PostEvent(self, evt2)
        if evt.RightUp():
            self.SetValue(self._range)
            evt2 = wx.PyCommandEvent(CDS_CHANGED, wx.ID_ANY)
            evt2.SetEventObject(self)
            wx.PostEvent(self, evt2)

    def OnMotion(self, evt):
        if not self.IsEnabled():
            return
        bmw, bmh = self._bbmp.GetSize()
        x, y = evt.GetPosition()
        w, h = self.GetSize()

        delta = abs(self._range[1]-self._range[0])
        dx = (w-2*self._hmargin-bmw)

        new_v = float(x - self._hmargin - bmw/2)/dx*delta + self._range[0]
        if self._hit == 0 and new_v >= self._value[1]:
            return
        if self._hit == 1 and new_v <= self._value[0]:
            return
        if new_v > self._range[1]:
            return
        if new_v < self._range[0]:
            return
        self._value[self._hit] = new_v
        self.Refresh()

        if self._generate_motion_event:
            evt2 = wx.PyCommandEvent(CDS_CHANGING, wx.ID_ANY)
            evt2.SetEventObject(self)
            wx.PostEvent(self, evt2)

    def DoDrawing(self, dc=None):
        if self.IsEnabled():
            col1 = '#000000'
            col2 = '#FFFFB8'
            col3 = '#ffafaf'
        else:
            col1 = '#7f7f7f'
            col2 = '#FFFFD8'
            col3 = '#ffdfdf'

        self.Unbind(wx.EVT_PAINT)
        if dc is None:
            dc = wx.ClientDC(self)

        w, h = self.GetSize()
        dc.SetFont(self.font)

        yy = int(h/2 - self._sheight/2 - self._vmargin)
        dc.SetDeviceOrigin(0, yy)

        def draw_box(self, w1, dc):
            dc.DrawBitmap(self._bbmp,
                          int(w1-self._bwidth/2),
                          0,
                          True)
            return

        w1, w2 = self._calc_w1_w2()

        dc.SetPen(wx.Pen(col1))
        dc.SetBrush(wx.Brush(col2))
        dc.DrawRoundedRectangle(int(self._hmargin),
                                int(self._vmargin),
                                int(w-2*self._hmargin),
                                int(self._sheight),
                                2.)
        dc.SetPen(wx.Pen(col1))
        dc.SetBrush(wx.Brush(col3))
        dc.DrawRectangle(int(w1),
                         int(self._vmargin),
                         int(w2-w1),
                         int(self._sheight))

        draw_box(self, w1, dc)
        draw_box(self, w2, dc)

        self._isDrawn = True
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _calc_w1_w2(self):
        bmw, bmh = self._bbmp.GetSize()
        w, h = self.GetSize()
        delta = abs(self._range[1]-self._range[0])
        w1 = ((w-2*self._hmargin-bmw) / delta * (self._value[0] - self._range[0]) +
              self._hmargin+bmw/2)
        w2 = ((w-2*self._hmargin-bmw) / delta * (self._value[1] - self._range[0]) +
              self._hmargin+bmw/2)
        return w1, w2


class test_frame(wx.Frame):
    def __init__(self, *args, **kargs):
        wx.Frame.__init__(self, *args, **kargs)
        self.ds = CustomDoubleSlider(self, wx.ID_ANY)
        self.ds.MotionEvent(True)
        self.Layout()
        self.Show()
        self.Bind(EVT_CDS_CHANGED, self.onCDS_CHANGED)
        self.Bind(EVT_CDS_CHANGING, self.onCDS_CHANGING)

    def onCDS_CHANGED(self, evt):
        print(evt.GetEventObject().GetValue())

    def onCDS_CHANGING(self, evt):
        print(evt.GetEventObject().GetValue())


if __name__ == '__main__':
    app = wx.App(False)
    frame = test_frame(None, wx.ID_ANY, "test")
    app.MainLoop()
