from __future__ import print_function

'''
   Wave Viewer is a video viewer modifiied to view
   a wave field expreesed by complex number.

   figobj which has "set_phasor" can dynamically
   compute a new data set using phasor.

   (Presently, only fig_tripcolor has this feature.)

   Usage:
         from ifigure.widgets.wave_viewer import WaveViewer

         v = figure(viewer = WaveViewer, nframe = 15, absolute = True)

             nframe: number of frame
             absolute: if true, the last frame is absolute 
'''
import wx
from ifigure.widgets.video_viewer import VideoBookPlayer, VideoViewerMode
from ifigure.widgets.book_viewer import BookViewer, BookViewerFrame
from ifigure.widgets.book_viewer_interactive import allow_interactive_call
import ifigure.events
import numpy as np
import weakref

from ifigure.mto.fig_tripcolor import FigTripcolor
from ifigure.mto.fig_quiver import FigQuiver
from ifigure.mto.fig_plot import FigPlot
from ifigure.mto.fig_solid import FigSolid
from ifigure.mto.fig_surface import FigSurface
from ifigure.mto.fig_image import FigImage
from matplotlib.collections import TriMesh


class FigTripcolorPhasor(FigTripcolor):
    def set_phasor(self, angle=None):
        tri = self.get_masked_tri()
        if angle is not None:
            z = self.getp('z') * np.exp(1j*angle)
            if isinstance(self._artists[0], TriMesh):
                C = z.flatten().real
            else:
                C = (z.flatten().real)[tri].mean(axis=1)
        else:
            z = np.absolute(self.getp('z')).flatten()
            if isinstance(self._artists[0], TriMesh):
                C = z.flatten()
            else:
                C = z[tri].mean(axis=1)
        self._artists[0].set_array(C)

class FigPlotPhasor(FigPlot):
    def set_phasor(self, angle=None):
        y = self._artists[0].get_ydata()
        y_complex = self.getvar('complex_y')
        if angle is not None:
            new_y = (y_complex * np.exp(1j*angle))[:len(y)]
            new_y = new_y.real
        else:
            new_y = np.absolute(y_complex[:len(y)])
        self._artists[0].set_ydata(new_y)
        self.setp('y', new_y)

class FigQuiverPhasor(FigQuiver):
    def set_phasor(self, angle=None):
        u = self.getvar('complex_u')
        v = self.getvar('complex_v')
        y_complex = self.getvar('y')
        if angle is not None:
            self.setvar('u', (u * np.exp(1j*angle)).real)
            self.setvar('v', (v * np.exp(1j*angle)).real)
        else:
            self.setvar('u', np.absolute(u))
            self.setvar('v', np.absolute(v))
        self.reset_artist()


class FigSolidPhasor(FigSolid):
    def set_phasor(self, angle=None):
        if angle is not None:
            z = self.getvar('cdata') * np.exp(1j*angle)
#           if len(z.shape) == 2:
#              z =  np.mean(z, -1).real
#           else:
            z = z.real
        else:
            z = np.absolute(self.getvar('cdata'))
#           if len(z.shape) == 2:
#              z =  np.mean(z, -1)
        self._artists[0]._gl_facecolordata = z
        self._artists[0]._update_fc = True


class FigImagePhasor(FigImage):
    def set_phasor(self, angle=None):
        z = self.getvar('complex_z')
        if angle is not None:
            self.setvar('z', (z * np.exp(1j*angle)).real)
        else:
            self.setvar('z', np.absolute(z))
        self.reset_artist()

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        z = self.getvar('complex_z')        
        return [-np.max(np.abs(z)), np.max(np.abs(z))]
    
    def get_export_val(self, a):
        x, y, z = self._eval_xyz()
        z = self.getvar('complex_z')
        return {"cdata": z,
                "xdata": x,
                "ydata": y}

class FigSurfacePhasor(FigSurface):
    def set_phasor(self, angle=None):
        if angle is not None:
            z = self.getvar('cdata') * np.exp(1j*angle)
#           if len(z.shape) == 2:
#              z =  np.mean(z, -1).real
#           else:
            z = z.real
        else:
            z = np.absolute(self.getvar('cdata'))
#           if len(z.shape) == 2:
#              z =  np.mean(z, -1)
        r, c, idxset = self._artists[0]._idxset
        if r is not None:
            # surface plot
            fc = z[r, :][:, c].flatten()[idxset]
        else:
            # trisurf plot
            fc = z.flatten()
        if idxset is not None:
            fc = fc[idxset]
        self._artists[0]._gl_facecolordata = fc
        self._artists[0]._update_fc = True


def convert_figobj(obj):
    if obj.__class__ == FigTripcolor:
        obj.__class__ = FigTripcolorPhasor
    elif obj.__class__ == FigPlot:
        obj.__class__ = FigPlotPhasor
    elif obj.__class__ == FigQuiver:
        obj.__class__ = FigQuiverPhasor
    elif obj.__class__ == FigSolid:
        if obj.getvar('cdata') is None:
            return
        obj.__class__ = FigSolidPhasor
    elif obj.__class__ == FigSurface:
        if obj.getvar('cdata') is None:
            return
        obj.__class__ = FigSurfacePhasor
    elif obj.__class__ == FigImage:
        obj.__class__ = FigImagePhasor
    else:
        pass


class WaveViewer(VideoBookPlayer):
    def __init__(self, *args, **kwargs):
        self.nframe = kwargs.pop('nframe', 30)
        self.sign = kwargs.pop('sign',  -1)
        super(WaveViewer, self).__init__(*args, **kwargs)

        if self.book is not None:
            self.add_all_video_obj()

    def add_bookmenus(self, editmenu, viewmenu):
        VideoViewerMode.add_bookmenus(self, editmenu, viewmenu)
        self.add_menu(viewmenu, wx.ID_ANY,
                      "Show Absolute",  "show absolute value of wave field",
                      self.onShowAbs)

    def tripcolor(self, *args, **kwargs):
        o = BookViewer.tripcolor(self, *args, **kwargs)
        if o is None:
            return
        if o.getvar('z').dtype.name.startswith('complex'):
            convert_figobj(o)
            self.add_video_obj(o)
        return o

    def plot(self, *args, **kwargs):
        o = BookViewer.plot(self, *args, **kwargs)
        if o is None:
            return
        y = args[1]
        if y.dtype.name.startswith('complex'):
            o.setvar('complex_y', y)
            convert_figobj(o)
            self.add_video_obj(o)
        return o

    @allow_interactive_call
    def quiver(self, *args, **kwargs):
        try:
            o = FigQuiver(*args, **kwargs)
        except ValueError as x:
            print(x.message)
            return
        if o.getvar('u').dtype.name.startswith('complex'):
            convert_figobj(o)
            self.add_video_obj(o)
            o.setvar('complex_u', o.getvar('u'))
            o.setvar('complex_v', o.
                     getvar('v'))
            o.setvar('u', o.getvar('u').real)
            o.setvar('v', o.getvar('v').real)
        return o

    # @allow_interactive_call
    def solid(self, *args, **kwargs):
        try:
            o = BookViewer.solid(self, *args, **kwargs)
        except ValueError as x:
            return
        convert_figobj(o)
        self.add_video_obj(o)
        return o

    def surf(self, *args, **kwargs):
        try:
            o = BookViewer.surf(self, *args, **kwargs)
        except ValueError as x:
            return
        convert_figobj(o)
        self.add_video_obj(o)
        return o

    def image(self, *args, **kwargs):
        if len(args) == 1:
            complex_z = args[0]
            if np.iscomplexobj(complex_z):
               args = (complex_z.real,)
        elif len(args) == 3:
            complex_z = args[2]
            if np.iscomplexobj(complex_z):
               args = (args[0], args[1], complex_z.real,)
        else:
            print("incorrect number of arguments: image(z) or image(x, y, z)")
            return
        
        try:
            o = BookViewer.image(self, *args, **kwargs)
        except ValueError as x:
            return
        o.setvar('complex_z', complex_z)                
        convert_figobj(o)
        self.add_video_obj(o)
        return o
        
    def _get_phase(self, ipage):
        return self.sign*np.pi*2*ipage/self.nframe

    def num_page(self):
        return self.nframe

    def add_all_video_obj(self):
        self.reset_video_obj_set()
        for obj in self.book.walk_tree():
            if isinstance(obj, FigTripcolorPhasor):
                self.add_video_obj(obj)
            elif isinstance(obj, FigPlotPhasor):
                self.add_video_obj(obj)
            elif isinstance(obj, FigQuiverPhasor):
                self.add_video_obj(obj)
            elif isinstance(obj, FigSolidPhasor):
                self.add_video_obj(obj)
            elif isinstance(obj, FigSurfacePhasor):
                self.add_video_obj(obj)
            elif isinstance(obj, FigImagePhasor):
                self.add_video_obj(obj)
            else:
                pass

    def UpdateImage(self, i):
        phase = self._get_phase(i)
        for obj in self._video_obj:
            obj.set_phasor(phase)
            obj.set_bmp_update(False)
        self._video_page = i
        self.draw()

    def onShowAbs(self, evs):
        for obj in self._video_obj:
            obj.set_phasor(None)
            obj.set_bmp_update(False)
        self.draw()

    def onNextVideoPage(self, evt):
        if self._video_page == self.nframe - 1:
            return
#        self._video_page = self._video_page + 1
        ifigure.events.SendShowPageEvent(self.book, self, '1')

    def onPrevVideoPage(self, evt):
        if self._video_page == 0:
            return
#        self._video_page = self._video_page - 1
        ifigure.events.SendShowPageEvent(self.book, self, '-1')

    def videoviewer_config(self):
        from ifigure.utils.edit_list import DialogEditList
        l = [
            ["Interval(sec.)", str(float(self._playinterval)/1000.),
             0, {'noexpand': True}],
            ["Frame #", str(self.nframe),
             0, {'noexpand': True}],
            [None, self._playloop, 3, {
                "text": "Loop Movie", "noindent": None}],
            [None, self.sign == -1, 3,
                {"text": "Use exp(-iwt)", "noindent": None}],
        ]
        value = DialogEditList(l, parent=self,
                               title='Player Config.',
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        if not value[0]:
            return
        self._playinterval = int(float(value[1][0])*1000.)
        self._playloop = bool(value[1][2])
        self.sign = -1 if bool(value[1][3]) else 1
        self.nframe = int(value[1][1])
