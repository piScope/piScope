from __future__ import print_function

"""

  class:FigureCanvasWxMod

      A subclass of FigureCanvas to draw figures managed
      by figobj efficiently. This class provides...

      1) off-screen bitmap data storage to update highlight
         and other user interaction without drawing whole
         figure
      2) bitmap buffer for each axes to allow for updating
         one axes in figure screen without drawing all other
         axes


"""

# uncomment the following to use wx rather than wxagg
import matplotlib
import wx
from matplotlib.backends.backend_wx import FigureCanvasWx as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as CanvasAgg
from matplotlib.backends.backend_wx import RendererWx
from ifigure.utils.cbook import EraseBitMap
from operator import itemgetter


class CanvasMod(object):
    '''
    CanvasMod provides modification to Wx and WxAgg
    '''

    def __init__(self, *args, **kargs):
        #        super(FigureCanvasWxMod, self).__init__(*args, **kargs)
        self.frame_bitmap = None
        self.others_bitmap = None
        self.figure_bitmap = None
        self.empty_bytes = []

    def draw_by_bitmap(self, *args, **kargs):
        print('draw bitmap')
        self.renderer = self.make_renderer()
#       gc = self.renderer.new_gc()
#       gc.select()
#        self.renderer.handle_clip_rectangle(gc)
        gc = None
        self.frame_bitmap = self.make_bitmap(self.figure.draw_frame, gc)
        self.make_axes_bitmap(gc)
        self.others_bitmap = self.make_bitmap(self.figure.draw_others, gc)
#        gc.unselect()

        self.erase_bitmap()
#        EraseBitMap(self.bitmap)

        bmplist = self.make_bmp_list()
        self.draw_from_bitmap(bmplist)
        self._isDrawn = True
        self.figure_bitmap = self.bitmap.GetSubBitmap(
            (0, 0,
             self.bitmap.GetWidth(),
             self.bitmap.GetHeight()))

    def draw(self, drawDC=None):
        self.draw_by_bitmap()
        self.gui_repaint(drawDC=drawDC)

#    def draw_all(self, drawDC=None):
#        pass

    def sorted_axes_list(self):
        # a list of (zorder, func_to_call, list_of_args)
        dsu = []
        for a in self.figure.axes:
            if (hasattr(a, 'figobj') and
                    a.figobj is not None):
                dsu.append((a.get_zorder(), a))
        dsu.sort(key=itemgetter(0))
        return dsu

    def make_bmp_list(self):
        bmplist = []
        bmplist.append((self.frame_bitmap, 0, 0))

        dsu = self.sorted_axes_list()
        for zorder, a in dsu:
            bmplist.append(a.figobj.get_bmp())
            # bmplist.append(a.figobj.get_bmp())
        bmplist.append((self.others_bitmap, 0, 0))
        return bmplist

    def erase_bitmap_by_copyfrombuffer(self):
        # erase bitmap by 0,0,0,0 to prepare
        # transparent empty screen
        import array
        bpp = 4  # bytes per pixel
        w = self.bitmap.GetWidth()
        h = self.bitmap.GetHeight()

        if (len(self.empty_bytes) !=
                self.bitmap.GetWidth()*self.bitmap.GetHeight()*bpp):
            self.empty_bytes = array.array('B', [0] * w*h*bpp)

        self.bitmap.CopyFromBufferRGBA(self.empty_bytes)

        return
#        self.renderer = RendererWx(self.bitmap, self.figure.dpi)
#        gc = self.renderer.new_gc()
#        gc.select()
#        gc.dc.SetBackground(wx.TRANSPARENT_BRUSH)
#        gc.dc.SetBackground(wx.TRANSPARENT_BRUSH)
#        gc.dc.Clear()
#        gc.unselect()
#        return
#        dc = wx.MemoryDC()
        dc = self.renderer.gc.dc
#        dc.SelectObject(self.bitmap)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 255)))
#        dc.SetBackground(wx.Brush('white'))
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetLogicalFunction(wx.CLEAR)
        dc.Clear()
#        dc.SetBrush(wx.Brush(wx.Colour(125,0,0,125)))
        dc.SetLogicalFunction(wx.COPY)
#        dc.SetBackground(wx.Brush('white'))
#        dc.DrawRectangle(0,0, self.bitmap.GetWidth(),self.bitmap.GetHeight()/2)

#        dc.DrawRectangle(0,0, 100,100)
#        dc.SelectObject(wx.NullBitmap)
#        del dc
        # self.bitmap.SetMaskColour('black')

    def erase_bitmap(self):
        self.erase_bitmap_by_copyfrombuffer()
        return

    def make_bitmap(self, func, gc):
        '''
        prepare renderer.bitmap 
        '''
        self.erase_buffer()
#        gc = self.renderer.new_gc()
#        self.renderer.handle_clip_rectangle(gc)
#        gc.select()
        func(self.renderer)
#        gc.unselect()
        self.prepare_bitmap()
        bitmap = self.bitmap.GetSubBitmap(
            (0, 0,
             self.bitmap.GetWidth(),
             self.bitmap.GetHeight()))
        return bitmap  # self.make_true_bitmap_copy(bitmap)

    def make_axes_bitmap(self, gc):
        #        gc = self.renderer.new_gc()
        #        gc.select()
        dsu = self.sorted_axes_list()
        for zorder, a in dsu:
            if not a.figobj.get_bmp_update():
                self.erase_buffer()
                self.figure.draw_axes(self.renderer, a)
                self.prepare_bitmap()
                box = a.figobj.get_axesartist_extent(renderer=self.renderer)
                h = self.renderer.bitmap.GetHeight()
#               bmp =  self.make_subbitmap_copy(
#                            box[0], h-box[3],
#                            box[1]-box[0],
#                            box[3]-box[2])
                bmp = self.bitmap.GetSubBitmap(
                    (box[0], h-box[3],
                     box[1]-box[0],
                     box[3]-box[2]))
#               bmp = self.make_true_bitmap_copy(bmp)
                a.figobj.set_bmp(bmp, box[0], h-box[3])
#        gc.unselect()

    def draw_artist(self, drawDC=None, alist=None):
        """
        Render the figure using RendererWx instance renderer, or using a
        previously defined renderer if none is specified.
        """
        if alist is None:
            return
        if len(alist) == 0:
            return
        if drawDC is None:
            drawDC = wx.ClientDC(self)
        # print 'draw artist'
        self.erase_buffer()
        self.renderer = self.make_renderer()
        for a in alist:
            a.draw(self.renderer)
        self.prepare_bitmap()
        bitmap = self.bitmap.GetSubBitmap(
            (0, 0,
             self.bitmap.GetWidth(),
             self.bitmap.GetHeight()))
        self.erase_bitmap()
        self.canvas_draw_bitmap(self.figure_bitmap, 0, 0)
        self.canvas_draw_bitmap(bitmap, 0, 0)

        self.gui_repaint(drawDC=drawDC)

    def Copy_to_Clipboard_mod(self, event=None):
        "this is for debug purpose"
        "copy internal bitmaps of canvas to system clipboard"

        bmp_obj = wx.BitmapDataObject()
        bmp_obj.SetBitmap(self.figure_bitmap)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(bmp_obj)
        wx.TheClipboard.Close()
        wx.TheClipboard.Flush()

    def make_true_bitmap_copy(self, bitmap):
        bmp = bitmap.GetSubBitmap(
            (0, 0,
             bitmap.GetWidth(),
             bitmap.GetHeight()))
        img = bmp.ConvertToImage()
        img.SaveFile('saved.png', wx.BITMAP_TYPE_PNG)
        return wx.BitmapFromImage(img)


class FigureCanvasWxModAgg(CanvasMod, CanvasAgg):
    def __init__(self, *args, **kargs):
        CanvasAgg.__init__(self, *args, **kargs)
        CanvasMod.__init__(self, *args, **kargs)

#    def _onSize(self, evt):
#        print '!!!! onSize'
#        super(FigureCanvasWxModAgg, self)._onSize(evt)

    def draw_all(self, drawDC=None):
        ''' 
        draw everything from scratch 
        mostly debugging purpose
        '''
        print('draw_all')
        self.figure.figobj.reset_axesbmp_update()
        CanvasAgg.draw(self)

    def erase_buffer(self):
        if hasattr(self, '_lastKey'):
            del self._lastKey
            self.renderer = self.make_renderer()

    def make_renderer(self):
        return self.get_renderer()

    def prepare_bitmap(self):
        from matplotlib.backends.backend_wxagg import _convert_agg_to_wx_bitmap
        self.bitmap = _convert_agg_to_wx_bitmap(self.get_renderer(), None)
        self.renderer.bitmap = self.bitmap

    def draw_from_bitmap(self, bmplist):
        if not self.figure.get_visible():
            return
        self.figure.draw_from_bitmap(self.renderer)
        dc = wx.MemoryDC()
        dc.SelectObject(self.bitmap)
        gfx_ctx = wx.GraphicsContext.Create(dc)
        for bmp, x, y in bmplist:
            gfx_ctx.DrawBitmap(bmp, x, y,
                               bmp.GetWidth(),
                               bmp.GetHeight())
        dc.SelectObject(wx.NullBitmap)

    def canvas_draw_bitmap(self, bitmap, x, y):
        dc = wx.MemoryDC()
        dc.SelectObject(self.bitmap)
        dc.DrawBitmap(bitmap, x, y)
        dc.SelectObject(wx.NullBitmap)

#    def _onSize(self, event):
#        if hasattr(self, "_on_size"):
#            return self._on_size(event)
#        else:
#            return super(FigureCanvasWxModAgg, Canvas)._onSize(event)


class FigureCanvasWxMod(CanvasMod, Canvas):
    def __init__(self, *args, **kargs):
        Canvas.__init__(self, *args, **kargs)
        CanvasMod.__init__(self, *args, **kargs)

    def draw_all(self, drawDC=None):
        ''' 
        draw everything from scratch 
        mostly debugging purpose
        '''
        print('draw_all')
        self.figure.figobj.reset_axesbmp_update()
        Canvas.draw(self)

    def make_renderer(self):
        return RendererWx(self.bitmap, self.figure.dpi)

    def prepare_bitmap(self):
        pass

    def draw_from_bitmap(self, bmplist):
        if not self.figure.get_visible():
            return
        self.figure.draw_from_bitmap(self.renderer)
        gc = self.renderer.new_gc()
        self.renderer.handle_clip_rectangle(gc)
        gc.select()
        for bmp, x, y in bmplist:
            gc.gfx_ctx.DrawBitmap(bmp, x, y,
                                  bmp.GetWidth(),
                                  bmp.GetHeight())
        gc.unselect()

    def erase_buffer(self):
        self.erase_bitmap()

    def canvas_draw_bitmap(self, bitmap, x, y):
        gc = self.renderer.new_gc()
        gc.select()
#        self.renderer.handle_clip_rectangle(gc)
        # gc.gfx_ctx.ResetClip()
        gc.gfx_ctx.DrawBitmap(bitmap, x, y,
                              bitmap.GetWidth(),
                              bitmap.GetHeight())
        gc.unselect()

#    def _onSize(self, event):
#        if hasattr(self, "_on_size"):
#            return self._on_size(event)
#        else:
#            return super(FigureCanvasWxMod, Canvas)._onSize(event)
