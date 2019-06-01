from __future__ import print_function
# uncomment the following to use wx rather than wxagg
from matplotlib.backends.backend_agg import RendererAgg
import os
from ifigure.matplotlib_mod.backend_wxagg_mod import FigureCanvasWxAggMod
from distutils.version import LooseVersion
import numpy as np
import time
import wx
import weakref
import array
from scipy.misc import imresize
from ctypes import sizeof, c_float, c_void_p, c_uint, string_at

import matplotlib

from functools import wraps
from matplotlib.backends.backend_wx import FigureCanvasWx as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as CanvasAgg
from matplotlib.backends.backend_wx import RendererWx
from ifigure.utils.cbook import EraseBitMap
from operator import itemgetter

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('BackendWXAggGL')

isMPL_before_1_2 = LooseVersion(matplotlib.__version__) < LooseVersion("1.2")

#
#  OpenGL extention
#
try:
    from wx import glcanvas
except ImportError:
    pass
try:
    # The Python OpenGL package can be found at
    # http://PyOpenGL.sourceforge.net/
    from OpenGL.GL import *
    from OpenGL.GLUT import *
    from OpenGL.GLU import *
    from OpenGL.GL import shaders
    from OpenGL.arrays import vbo

    class myvbo(vbo.VBO):
        pass
    haveOpenGL = True
except ImportError:
    haveOpenGL = False

near_clipping = 8.

multisample = 1
multisample_init_done = False

basedir = os.path.dirname(__file__)


def compile_file(file, mode):
    fid = open(os.path.join(basedir, file), 'r')
    prog = ''.join(fid.readlines())
    pl = shaders.compileShader(prog, mode)
    return pl


def get_vbo(data, *args, **kwargs):
    vbo = myvbo(data, *args, **kwargs)
    vbo.need_update = False
    return vbo


def read_glmatrix(mode):
    #    a = (GLfloat * 16)()
    return np.transpose(glGetFloatv(mode))
#    return np.transpuse(np.array(list(a)).reshape(4,4))


def define_unform(shader, name):
    shader.uniform_loc[name] = glGetUniformLocation(shader, name)


def check_framebuffer(message, mode=GL_FRAMEBUFFER):
    if (glCheckFramebufferStatus(mode) !=
            GL_FRAMEBUFFER_COMPLETE):
        print('Framebuffer imcomplete (' + message + ')')
        print(str(glCheckFramebufferStatus(GL_FRAMEBUFFER)))
        print(str(GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT))
        print(str(GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS))
        print(str(GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT))
        print(str(GL_FRAMEBUFFER_UNSUPPORTED))
        return False
    return True


def frustum(left, right, bottom, top, zNear, zFar):
    dx = right - left
    dy = top - bottom
    A = (right + left) / (right - left)
    B = (top + bottom) / (top - bottom)
    C = -(zFar + zNear) / (zFar - zNear)
    D = - (2*zFar * zNear) / (zFar - zNear)
    return np.array([[2*zNear/dx, 0,           A, 0],
                     [0,          2*zNear/dy,  B, 0],
                     [0,          0,           C, D],
                     [0,          0,          -1, 0]])


def ortho(left, right, bottom, top, zNear, zFar):
    dx = right - left
    dy = top - bottom
    dz = zFar - zNear
    tx = - (right + left) / (right - left)
    ty = - (top + bottom) / (top - bottom)
    tz = - (zFar + zNear) / (zFar - zNear)
    return np.array([[2/dx, 0,     0,     tx],
                     [0,    2/dy,  0,     ty],
                     [0,    0,     -2/dz, tz],
                     [0,    0,     0,     1.]])


def wait_gl_finish(method):
    @wraps(method)
    def method2(self, *args, **kargs):
        method(self, *args, **kargs)
        glFinish()
    return method


def check_gl_error():
    error = glGetError()
    if error != 0:
        print(("GL error ", error))


class vbos_dict(dict):
    def __del__(self, *args, **kwargs):
        if 'im' in self:
            if self['im'] is not None:
                dprint2('deleteing texture', self['im'])
                glDeleteTextures(self['im'])
                self['im'] = None
        return


#from renderer_gl import RendererGL


class RendererGLMixin(object):
    def __init__(self, *args, **kwargs):
        self.do_stencil_test = False
        self._no_update_id = False
        self._num_globj = 0

    def __del__(self):
        self._glcanvas = None

#    def set_glcanvas(self, glcanvas):
#        self._glcanvas = glcanvas

    def get_glcanvas(self):
        from ifigure.matplotlib_mod.backend_wxagg_gl import FigureCanvasWxAggModGL
        return FigureCanvasWxAggModGL.glcanvas

    def gl_draw_image(self, gc, path, trans, im, **kwargs):
        self.get_glcanvas().store_draw_request('image', gc,
                                               path, trans,
                                               im, **kwargs)

    def gl_draw_markers(self, gc, marker_path, marker_trans,
                        path, transform, rgbFace=None, **kwargs):
        self.get_glcanvas().store_draw_request('markers', gc, marker_path, marker_trans,
                                               path, rgbFace, **kwargs)

    def gl_draw_path(self, gc, path, transform, rgbFace=None, **kwargs):
        self.get_glcanvas().store_draw_request('path', gc, path, rgbFace, **kwargs)

    def gl_draw_path_collection(self, gc, frozen, paths,
                                transform, offset, transOffset,
                                facecolor, edgecolor,
                                linewidth, linestyle,
                                antialias, urls, offset_position, **kwargs):

        self.get_glcanvas().store_draw_request('path_collection', gc, paths,
                                               facecolor, edgecolor,
                                               linewidth, linestyle, offset,
                                               **kwargs)

    def gl_draw_path_collection_e(self, gc, frozen, paths,
                                  transform, offset, transOffset,
                                  facecolor, edgecolor,
                                  linewidth, linestyle,
                                  antialias, urls, offset_position, **kwargs):
        self.get_glcanvas().store_draw_request('path_collection_e', gc, paths,
                                               facecolor, edgecolor,
                                               linewidth, linestyle, offset,
                                               **kwargs)

#    def set_canvas_proj(self, worldM, viewM, perspM, lookat):
#        self.get_glcanvas().set_proj(worldM, viewM, perspM, lookat)

    def update_id_data(self, data, tag=None):
        if not self._no_update_id:
            tag._gl_id_data = data
        self._no_update_id = False

    def no_update_id(self):
        self._no_update_id = True


def mixin_gl_renderer(renderer):
    if hasattr(renderer, '_gl_renderer'):
        return
    renderer._gl_renderer = RendererGLMixin()
    renderer.gl_svg_rescale = False
    names = ('gl_draw_markers', 'gl_draw_path_collection',
             'gl_draw_path_collection_e',
             'gl_draw_path', 'gl_draw_image',
             'get_glcanvas',
             'update_id_data', 'no_update_id')
    for name in names:
        setattr(renderer, name, getattr(renderer._gl_renderer, name))


class FigureCanvasWxAggModGL(FigureCanvasWxAggMod):
    glcanvas = None

    def __init__(self, *args, **kwargs):
        FigureCanvasWxAggMod.__init__(self, *args, **kwargs)
        if FigureCanvasWxAggModGL.glcanvas is None:
            win = wx.GetApp().TopWindow
            glcanvas = MyGLCanvas(win)
            FigureCanvasWxAggModGL.glcanvas = glcanvas
            glcanvas.SetMinSize((2, 2))
            glcanvas.SetMaxSize((2, 2))
            # self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
            win.GetSizer().Add(glcanvas)
            win.Layout()
            glcanvas.Refresh()

    def get_renderer(self, cleared=False):
        l, b, w, h = self.figure.bbox.bounds
        key = w, h, self.figure.dpi
        try:
            self._lastKey, self.renderer
        except AttributeError:
            need_new_renderer = True
        else:
            need_new_renderer = (self._lastKey != key)

        if need_new_renderer:
            self.renderer = RendererAgg(w, h, self.figure.dpi)
            mixin_gl_renderer(self.renderer)
            self._lastKey = key
        elif cleared:
            self.renderer.clear()
        return self.renderer

    def draw(self, *args, **kargs):
        self._update_hl_color()
        return FigureCanvasWxAggMod.draw(self,  *args, **kargs)

    def draw_artist(self, drawDC=None, alist=None):
        if alist is None:
            alist = []
        gl_obj = [a for a in alist if hasattr(a, 'is_gl')]

        for o in gl_obj:
            o.is_last = False
        if len(gl_obj) > 0:
            gl_obj[-1].is_last = True
            self.renderer._k_globj = 0
            self.renderer._num_globj = len(gl_obj)
            self.renderer.no_update_id()
#            self.renderer.no_lighting = no_lighting
            self._update_hl_color()
            FigureCanvasWxAggModGL.glcanvas._artist_mask = alist

        v = FigureCanvasWxAggMod.draw_artist(self, drawDC=drawDC, alist=alist)
#        self.renderer.no_lighting = False
        return v

    def _update_hl_color(self):
        value = self.hl_color
        vv = list([float(x) for x in value]) + [1.0]
        vv[3] = 0.65
        FigureCanvasWxAggModGL.glcanvas._hl_color = tuple(vv[:4])

    def _onPaint(self, evt):
        #        self.glcanvas.OnPaint(evt)
        #        evt.Skip()
        FigureCanvasWxAggMod._onPaint(self, evt)

    def _onSize(self, evt=None, nocheck=False):
        FigureCanvasWxAggMod._onSize(self, evt=evt, nocheck=nocheck)
        # self.glcanvas.SetSize(self.bitmap.GetSize())

    def disable_alpha_blend(self):
        FigureCanvasWxAggModGL.glcanvas._alpha_blend = False

    def enable_alpha_blend(self):
        FigureCanvasWxAggModGL.glcanvas._alpha_blend = True
