"""

  class:FigureCanvasWxAgg

      A subclass of FigureCanvas to draw figures managed
      by figobj efficiently. This class provides...

      1) off-screen bitmap data storage to update highlight
         and other user interaction without drawing whole
         figure
      2) bitmap buffer for each axes to allow for updating
         one axes in figure screen without drawing all other
         axes
      3) active resize while window resize is done by scaling
         internally drawn image avoiding many call of draw funciton
         druing resize.


   history: 12.11.??  first version
               12.10  draw_event is added when draw is called
            13.01.??  speed up by eliminating stupid type conversions..
               02.23  fix iframe drawing timing
               03.15  add image scaling during active resize
            14.06.05  updated resize. during the resize it shows scaled
                      image to realize smooth window edge drag.
                      BookViewer detects the end of resize events and
                      issue draw_later (after adjusting tree objects)


"""
# uncomment the following to use wx rather than wxagg
from ifigure.utils.wx3to4 import image_SetAlpha, wxEmptyImage
from distutils.version import LooseVersion
import matplotlib
import wx
import weakref
import array
import sys
import gc

from matplotlib.backends.backend_wx import FigureCanvasWx as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as CanvasAgg
from matplotlib.backends.backend_wx import RendererWx
from ifigure.utils.cbook import EraseBitMap
from operator import itemgetter

try:
    from matplotlib._image import fromarray, frombyte
except:
    def frombyte(im, num): return im  # MPL2.0 accept numpy array directly
import numpy as np
import time
import ctypes

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigureCanvasWxAggMod')

isMPL_before_1_2 = LooseVersion(matplotlib.__version__) < LooseVersion("1.2")


class FigureCanvasWxAggMod(CanvasAgg):
    '''
    CanvasMod provides modification to Wx and WxAgg
    '''

    def __init__(self, *args, **kargs):
        self._width = 0
        self._height = 0
        self._isDrawn = False
        self._dsu_check = []
        self._auto_update_ax = []
        self._hl_color = (0, 0, 0,)

        super(FigureCanvasWxAggMod, self).__init__(*args, **kargs)

        # self.Unbind(wx.EVT_SIZE)
        self.iframe = None
        self.iothers = None
        self.axes_image = None
        self.figure_image = None
        self.resize_happend = False
        self.timer = wx.Timer(self)
        self.empty_bytes = []
#        self.Bind(wx.EVT_MOUSE_EVENTS, self.onMouseWheel)
        self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)
        self._wheel_cb = None
        self._pre_rot = 0

    def __del__(self):
        dprint2("FigureCanvasWxAggMod __del__")

    def onMouseWheel(self, evt):
        rot = evt.GetWheelRotation()
        x = evt.GetX()
        y = self.figure.bbox.height - evt.GetY()

        if rot != 0 and self._pre_rot == 0:
            # start wheel
            event = {'guiEvent': evt, 'start': True, 'x': x, 'y': y,
                     'end': False, 'direction': rot > 0}
        elif rot == 0 and self._pre_rot != 0:
            # end  wheel
            event = {'guiEvent': evt, 'start': False, 'x': x, 'y': y,
                     'end': True, 'direction': rot > 0}
        elif rot == 0:
            event = None
        else:
            event = {'guiEvent': evt, 'start': False, 'x': x, 'y': y,
                     'end': False, 'direction': rot > 0}
        self._pre_rot = rot
        try:
            if event is not None:
                self._wheel_cb(event)
        except:
            import traceback
            traceback.print_exc()
        evt.Skip()

    def set_wheel_cb(self, wheel_cb):
        self._wheel_cb = wheel_cb

    def _onPaint(self, evt):
        def scale_bitmap(figure_image, bitmap):
            h, w, d = figure_image.shape
            bitmapw, bitmaph = bitmap.GetSize()
            image = wxEmptyImage(w, h)
            image.SetData(figure_image[:, :, 0:3].tobytes())
            image_SetAlpha(image, figure_image[:, :, 3])
            return image.Scale(csize[0], csize[1]).ConvertToBitmap()

        csize = self.GetClientSize()
        if self.figure_image is not None:
            h, w, d = self.figure_image[0].shape
            if (csize[0] != w or
                    csize[1] != h):
                self.bitmap = scale_bitmap(self.figure_image[0], self.bitmap)
                self._isDrawn = True
        else:
            self._isDrawn = False

        if hasattr(self,  "_on_paint"):  # newer matplotlib renamed method
            CanvasAgg._on_paint(self, evt)
        else:
            CanvasAgg._onPaint(self, evt)

    def _onSize(self, evt=None, nocheck=False):
        if self.figure is None:
            evt.Skip()
            return
        if hasattr(CanvasAgg, "_on_size"):  # newer matplotlib renamed method
            CanvasAgg._on_size(self, evt)
        else:
            CanvasAgg._onSize(self, evt)
        return

    def _on_size(self, evt):
        if self.figure is None:
            evt.Skip()
            return

        CanvasAgg._on_size(self, evt)

    def draw(self, drawDC=None, nogui_reprint=False):
        #print("draw here")
        if self.figure is None:
            return
        if self.figure.figobj is None:
            return

        for fig_axes in self._auto_update_ax:
            fig_axes.set_bmp_update(False)

        #st =time.time()
        if not self.resize_happend:
            s = self.draw_by_bitmap()
            # this makes draw_event
            self.figure.draw_from_bitmap(self.renderer)
            self._isDrawn = True
            if not nogui_reprint:
                #print('draw calling gui_repaint')
                self.gui_repaint(drawDC=drawDC)

    def draw_all(self, drawDC=None):
        '''
        draw everything from scratch
        mostly debugging purpose
        '''
        self.figure.figobj.reset_axesbmp_update()
        self.draw()

    def draw_mpl(self, drawDC=None):
        # call super call draw directly for debug
        super(FigureCanvasWxAggMod, self).draw(drawDC)

    def draw_artist(self, drawDC=None, alist=None):
        """
        Render the figure using RendererWx instance renderer, or using a
        previously defined renderer if none is specified.
        """
        if self.figure is None:
            return
        if alist is None:
            return
        if drawDC is None:
            drawDC = wx.ClientDC(self)

        if self.figure_image is None:
            s = self.draw_by_bitmap()
            if not s:
                return

        self.renderer = self.get_renderer()
        gc = self.renderer.new_gc()
        self.renderer.clear()
        self.call_draw_image(gc,
                             self.figure_image[1], self.figure_image[2],
                             self.figure_image[0])

        for a in alist:
            a.draw(self.renderer)
        self._prepare_bitmap()

        self.gui_repaint(drawDC=drawDC)

    def capture_screen_rgba(self):
        img = self.bitmap.ConvertToImage()
        w, h = self.bitmap.GetSize()
        rgb = np.asarray(img.GetDataBuffer()).reshape(h, w, -1)
        a = np.asarray(img.GetAlphaBuffer()).reshape(h, w, -1)
        rgba = np.dstack((rgb, a))
        return rgba

    def copy_figure_image(self):
        return [self.figure_image[0].copy(), self.figure_image[1], self.figure_image[2]]

    def swap_figure_image(self, figure_image):
        b = self.figure_image
        self.figure_image = figure_image
        return b

    def swap_bitmap(self, bitmap):
        b = self.bitmap
        self.bitmap = bitmap
        return b

    def Copy_to_Clipboard_mod(self, event=None, bmp=None, pgbar=False):
        '''
         It does the same thing as Copy_to_Clipboard.
         It shows progress bar for user feed back
         But, this add progress bar and option to paste
         arbitray bitmap object
        '''
        # some routine to change self.bitmap
        # should come here...
        bmp_obj = wx.BitmapDataObject()
        if bmp is None:
            bmp_obj.SetBitmap(self.bitmap)
        else:
            bmp_obj.SetBitmap(bmp)

        def copy_to_cb(bmp_obj):
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(bmp_obj)
                wx.TheClipboard.Flush()
                wx.TheClipboard.Close()
            else:
                print('can not open clipboard')

        if pgbar:
            dialog = wx.ProgressDialog(
                'Progress...',
                'Coping bitmap image to System Clipboard.',
                maximum=10,
                parent=self.GetTopLevelParent())
            wx.CallLater(1000, dialog.Destroy)

        copy_to_cb(bmp_obj)


    def draw_by_bitmap(self):
        last_size = self.figure.figobj._last_draw_size
        if (self.GetClientSize()[0] != last_size[0] or
                self.GetClientSize()[1] != last_size[1]):
            self.figure.figobj.reset_axesbmp_update()

        self.figure.figobj._last_draw_size = self.GetClientSize()
        self.renderer = self.get_renderer()

#       psize = self.GetParent().GetSize()
#        self.resize_happend = False
        gc = None

        # prepare axes image
        self.iframe = self.make_buffer_image(self.figure.draw_frame)
        dsu, axes_darty = self.make_axes_image()

        dsu2 = []
        for obj in self.figure.figobj.walk_tree():
            if obj.get_figaxes() is None:
                continue
            if obj._floating and not obj.get_figaxes()._floating:
                dsu2.extend([(a.get_zorder(), a, a.draw, self.renderer)
                             for a in obj._artists])
        self.iothers = self.make_buffer_image(
            self.figure.draw_others, dsu=dsu2)

        # compose axes image
        gc = self.renderer.new_gc()
        self.renderer.clear()

        if len(dsu) == len(self._dsu_check):
            tmp = [x[1] for x in dsu]
            for x in self._dsu_check:
                if not x() in tmp:
                    axes_darty = True
        else:
            axes_darty = True
        if axes_darty or self.axes_image is None:
            for zorder, a in dsu:
                im, x, y = a.figobj.get_bmp()
                self.call_draw_image(gc, x, y, im)

            self.axes_image = self._bufferstring2image()
            self._dsu_check = [weakref.ref(x[1]) for x in dsu]

        # generate final image
        self.renderer.clear()
        self.call_draw_image(gc,
                             self.iframe[1], self.iframe[2], self.iframe[0])
        self.call_draw_image(gc,
                             self.axes_image[1], self.axes_image[2],
                             self.axes_image[0])
        self._draw_floating_axes()
        self.call_draw_image(gc,
                             self.iothers[1], self.iothers[2], self.iothers[0])

####    self.call_draw_image(gc, 0, 0, self.make_final_image())

        self._isDrawn = True

        self.figure_image = self._bufferstring2image()
        self._prepare_bitmap()

        return True

    def call_draw_image(self, gc, x, y, im):
        self.renderer.draw_image(gc, x, y, self._byte2image(im))

    def make_bmp_list(self):
        bmplist = []
        bmplist.append((self.frame_bitmap, 0, 0))

        dsu = self.sorted_axes_list()
        for zorder, a in dsu:
            bmplist.append(a.figobj.get_bmp())
            # bmplist.append(a.figobj.get_bmp())
        bmplist.append((self.others_bitmap, 0, 0))
        return bmplist

    def make_buffer_image(self, func, **kargs):
        '''
        prepare renderer.bitmap
        '''
        self.renderer.clear()

        try:
            func(self.renderer, **kargs)
        except:
            dprint1("make_buffer_image faield")

        return self._bufferstring2image()

    def make_axes_image(self):
        w, h = self.renderer.get_canvas_width_height()
        dsu = self._sorted_axes_list()
        axes_darty = False
        bg_color = self.iframe[0][0, 0, 0:3]
#        print 'drawing ax', len([a for zorder, a in dsu if not a.figobj.get_bmp_update()])

        for zorder, a in dsu:
            if not a.figobj.get_bmp_update():
                if hasattr(a, "isTwin"):
                    continue
                self.renderer.clear()
                draw_error = False
                for num, aa in enumerate(a.figobj._artists):
                    try:
                        #                       self.figure.draw_axes(self.renderer, aa,
                        #                                          noframe = num != 0)
                        self.figure.draw_axes(self.renderer, aa,
                                              noframe=True)

                    except:
                        import traceback
                        traceback.print_exc()
                        dprint1('drawing axes failed: ' + str(a.figobj))
                        draw_error = True
                        break
                if draw_error:
                    continue

                box = a.figobj.get_axesartist_extent(w, h,
                                                     renderer=self.renderer)

                image, x, y = self._bufferstring2image(box=box)

#               mask2 =  np.array((image[:,:,0] == bg_color[0]) &
#                                 (image[:,:,1] == bg_color[1]) &
#                                 (image[:,:,2] == bg_color[2]), np.uint8)
                mask2 = np.array((image[:, :, 3] == 0.0), np.uint8)
                mask = (mask2+255)/255

                for k in range(3):
                    image[:, :, k] = image[:, :, k]*mask + 255*mask2
                image[:, :, 3] = image[:, :, 3]*mask

                a.figobj.set_bmp(image.copy(), x, y)
                axes_darty = True

        return dsu, axes_darty

    def _draw_floating_axes(self):
        dsu = []
        for a in self.figure.axes:
            if (hasattr(a, 'figobj') and
                a.figobj is not None and
                    a.figobj._floating):
                dsu.append((a.get_zorder(), a))
        dsu.sort(key=itemgetter(0))
        o = self.figure.frameon
        self.figure.frameon = False
        for zorder, a in dsu:
            self.figure.draw_axes(self.renderer, a)
            a.figobj._bmp_update = True

        self.figure.frameon = o

    def _prepare_bitmap(self):
        try:   # MPL 3.6.1 and after
            from matplotlib.backends.backend_wxagg import _rgba_to_wx_bitmap
            self.bitmap = _rgba_to_wx_bitmap(self.get_renderer().buffer_rgba())
        except ImportError:
            from matplotlib.backends.backend_wxagg import _convert_agg_to_wx_bitmap
            self.bitmap = _convert_agg_to_wx_bitmap(self.get_renderer(), None)

    def _sorted_axes_list(self):
        # a list of (zorder, func_to_call, list_of_args)
        dsu = []
        for a in self.figure.axes:
            if (hasattr(a, 'figobj') and
                a.figobj is not None and
                    not a.figobj._floating):
                dsu.append((a.get_zorder(), a))
        dsu.sort(key=itemgetter(0))
        return dsu

    def _byte2image(self, img):
        image = frombyte(np.flipud(img), 1)
        # image.flipud_out()
        return image

    def _bufferstring2image(self, box=None):
        # print 'enterig buffer strin'
        #st = time.time()
        w, h = self.renderer.get_canvas_width_height()
        if isMPL_before_1_2:
            img = np.fromstring(self.renderer.buffer_rgba(0, 0), np.uint8)
        else:
            obj = self.renderer.buffer_rgba()
            if isinstance(obj, memoryview):
                img = np.asarray(obj, np.uint8).copy()
            else:
                img = np.fromstring(obj, np.uint8)

        # print h, w
        img = img.reshape((int(h), int(w), 4))

        if box is not None:
            a = int(max((np.floor(h-box[3]), 0)))
            b = int(min((np.floor(h-box[1])+2, h-1)))
            c = int(max((np.floor(box[0]), 0)))
            d = int(min((np.floor(box[2])+2, w-1)))
#           print w, h, a, b, c, d
#           img = img[round(h-box[3]):round(h-box[2]),
#                     round(box[0]):round(box[1]),:
            img1 = img[a:b, c:d, :]
            return img1, c, h-b
        else:
            return img, 0, 0

#    def _check_size(self, psize):
#        wx.Yield()
#        return self.resize_happend

    def make_final_image(self):

        im = np.ndarray(shape=self.iframe[0].shape, dtype=np.uint8)

        da = (self.iframe[0][:, :, 3]).astype(np.float64)/255.
        sa = (self.axes_image[0][:, :, 3]).astype(np.float64)/255.

        dd = (1-sa)
        ss = 1
        out = ((self.iframe[0][:, :, 3].astype(np.float64)*(dd) +
                self.axes_image[0][:, :, 3].astype(np.float64)*(ss)))
        for k in range(3):
            im[:, :, k] = ((self.iframe[0][:, :, k].astype(np.float64)*(da)*(dd) +
                            self.axes_image[0][:, :, k].astype(np.float64)*(sa)*(ss))).astype(np.uint8)

        im[:, :, 3] = out.astype(np.uint8)

        return im

    @property
    def hl_color(self):
        return self._hl_color

    @hl_color.setter
    def hl_color(self, value):
        self._hl_color = value

    # following code is added since when a user press right button
    # while dragging a mouse, mouse is already captured and backend_wx
    # try to capture it again, which causes trouble on linux
    def _onRightButtonDown(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()
        return super(FigureCanvasWxAggMod, self)._onRightButtonDown(evt)

    def _onLeftButtonDown(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()
        return super(FigureCanvasWxAggMod, self)._onLeftButtonDown(evt)

    def _onMiddleButtonDown(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()
        return super(FigureCanvasWxAggMod, self)._onMiddleButtonDown(evt)

    def gui_repaint(self, *args, **kwargs):
        super(FigureCanvasWxAggMod, self).gui_repaint(*args, **kwargs)
        self.Refresh()

        if hasattr(self.GetTopLevelParent(), "_playerbtn"):
            bp = self.GetTopLevelParent()._playerbtn
            if bp is not None:
                bp.Refresh()
        if hasattr(self.Parent, "_cutplane_btns"):
            bp = self.Parent._cutplane_btns
            if bp is not None:
                bp.Refresh()
