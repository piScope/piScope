import wx

# ----------------------------------------------------------------------


class ShowImageFrame(wx.Frame):
    def __init__(self, parent=None, bitmap=None):
        wx.Frame.__init__(self, parent, -1)
        self.bitmap = bitmap
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Layout()
        self.Show()

        bmp_obj = wx.BitmapDataObject()
        bmp_obj.SetBitmap(self.bitmap)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(bmp_obj)
        wx.TheClipboard.Close()
        wx.TheClipboard.Flush()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        dc.BeginDrawing()
        dc.Clear()
        dc.DrawBitmap(self.bitmap,  0, 0, True)
        dc.EndDrawing()
