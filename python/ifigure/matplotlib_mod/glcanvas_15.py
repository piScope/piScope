from __future__ import print_function
from ifigure.matplotlib_mod.canvas_common import *
# uncomment the following to use wx rather than wxagg

import numpy as np
import time
import wx
import weakref
import array
import gc
import traceback
import platform

from packaging import version

from ctypes import sizeof, c_float, c_void_p, c_uint, string_at

import matplotlib

from functools import wraps
from matplotlib.backends.backend_wx import FigureCanvasWx as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as CanvasAgg
from matplotlib.backends.backend_wx import RendererWx
from ifigure.utils.cbook import EraseBitMap
from operator import itemgetter

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('GLCanvas15')


vert_suffix = '_15.vert'
frag_suffix = '_15.frag'
geom_suffix = '_15.geom'

#depth_stencil_format = GL_DEPTH24_STENCIL8
depth_stencil_format = GL_DEPTH32F_STENCIL8


class dummy(object):
    pass


class MyGLCanvas(glcanvas.GLCanvas):
    offscreen = True
    context = None

    def __init__(self, parent):
        self.init = False
        
        if version.parse(wx.__version__) >= version.parse('4.1'):
            dispAttrs = wx.glcanvas.GLAttributes()

            if platform.system() == 'Darwin':
                dispAttrs.PlatformDefaults().RGBA().EndList()
            elif platform.system() == 'Linux':
                dispAttrs.PlatformDefaults().RGBA().EndList()
            else:
                ## this is not tested..
                dispAttrs.PlatformDefaults().EndList()

            # this is from sample but does not work..
            #dispAttrs.PlatformDefaults().MinRGBA(8, 8, 8, 8).DoubleBuffer().Depth(32).EndList()
            glcanvas.GLCanvas.__init__(self, parent, dispAttrs, -1)
        else:
            attribs = [glcanvas.WX_GL_CORE_PROFILE,
                       glcanvas.WX_GL_MAJOR_VERSION, 3,
                       glcanvas.WX_GL_MINOR_VERSION, 2, -1]
            glcanvas.GLCanvas.__init__(self, parent, -1, attribs)
            
        if MyGLCanvas.context is None:
            if version.parse(wx.__version__) >= version.parse('4.1'):
                ctxAttrs = wx.glcanvas.GLContextAttrs()
                if platform.system() == 'Darwin':
                    ctxAttrs.CoreProfile().OGLVersion(4, 1).Robust().ResetIsolation().EndList()
                elif platform.system() == 'Linux':
                    ctxAttrs.PlatformDefaults().EndList()
                else:
                    ## this is not tested..
                    ctxAttrs.PlatformDefaults().EndList()

                MyGLCanvas.context = glcanvas.GLContext(self, other=None, ctxAttrs=ctxAttrs)
                assert MyGLCanvas.context.IsOK(), "OpenGL Context is not OK"
            else:
                MyGLCanvas.context = glcanvas.GLContext(self)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.size = None
        self.frames = []
        self.bufs = []
#        self.artists = []
        self.artists_data = weakref.WeakKeyDictionary()
        self.frame_list = weakref.WeakKeyDictionary()
        self.vbo = weakref.WeakKeyDictionary()
        self.vbo_check = {}
        self._do_draw_mpl_artists = False
        self._draw_request = None
        self._do_depth_test = True
        self._depth_mask = True
        self._artist_mask = None
        self._use_shadow_map = True
        self._use_clip = 1   # 0 no clip, 1 clip box, 2, CP, 3 CP + clip box
        self._use_frustum = True
        self._attrib_loc = {}
        self._hittest_map_update = True

        self._alpha_blend = True
        self._current_uniform = {}
        #self._no_smooth = False
        self._hl_color = (0., 0., 0., 0.65)
        self.PIXBUFS = (None, None, None)
        self._read_data_pixbuf_target1 = (weakref.ref(dummy()), 0)
        self._read_data_pixbuf_target2 = (weakref.ref(dummy()), 0)
        self._wireframe = 0  # 1: wireframe + hidden line elimination 2: wireframe
        self._gl_scale = 1.0

        if MyGLCanvas.offscreen:
            self.SetSize((2, 2))
            self.SetMaxSize((2, 2))
            self.SetMinSize((2, 2))

        self._merge_check = 1

    def gc_artist_data(self):
        keys = list(self.artists_data.keys())
        for aa in keys:
            if aa.figobj is None:
                del self.artists_data[aa]
                del self.vbo[aa]
            else:
                keys2 = list(self.artists_data[aa].keys())
                for a in keys2:
                    if hasattr(a, 'figobj') and a.figobj is None:
                        del self.artists_data[aa][a]
                        del self.vbo[aa][a]

    def gc_vbo_dict(self):
        names = []
        for aa in self.vbo:
            tmp = [str(id(a)) + '_' + str(id(aa)) for a in self.vbo[aa]]
            names.extend(tmp)
        del_names = [n for n in self.vbo_check if n not in names]
        for n in del_names:
            #print("deleteing n", n)
            del self.vbo_check[n]
        gc.collect()

    def set_depth_test(self):
        if self._do_depth_test:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)

    def set_depth_mask(self, value=None):
        if value is not None:
            self._depth_mask = value
        if self._depth_mask:
            glDepthMask(GL_TRUE)
        else:
            glDepthMask(GL_FALSE)

    # @wait_gl_finish
    def set_uniform(self, func, name, *args, **kwargs):
        if name not in self._p_uniform_loc:
            return
        loc = glGetUniformLocation(self._p_shader, name)
        self._current_uniform[name] = (func, args, kwargs)


        '''            
        if name == 'uUseClip':
            print("Setting Clip", args, kwargs)
        if name == 'uClipLimit1':
            print("Clip1", args, kwargs)
        if name == 'uAmbient':            
            print("uAmbient", args, kwargs)              
        '''
        func(loc, *args, **kwargs)

    def select_shader(self, shader):
        glUseProgram(shader)
        if not hasattr(shader, 'uniform_loc'):
            shader.uniform_loc = {}
        if not hasattr(shader, 'attrib_loc'):
            shader.attrib_loc = {}
        self._p_uniform_loc = shader.uniform_loc
        self._p_attrib_loc = shader.attrib_loc
        self._p_shader = shader
        for name in self._current_uniform:
            func, args, kwargs = self._current_uniform[name]
            self.set_uniform(func, name, *args, **kwargs)

    def __del__(self):
        if len(self.frames) > 0:
            glDeleteFramebuffers(len(frames), self.frames)
        if len(self.bufs) > 0:
            glDeleteRenderbuffers(len(bufs), self.bufs)
        self.vbo_check = None

    def start_draw_request(self, artist):
        self._draw_request = artist
        tag = self.get_container(artist)
        if tag not in self.artists_data:
            self.artists_data[tag] = weakref.WeakKeyDictionary()
        self.artists_data[tag][artist] = []

    def end_draw_request(self):
        self._draw_request = None

    def InitGL(self):
        from OpenGL.GL import shaders

        # compile shader and set uniform variables
        # set viewing projection
        fs = compile_file('depthmap' + frag_suffix, GL_FRAGMENT_SHADER)
        vs = compile_file('depthmap' + vert_suffix, GL_VERTEX_SHADER)
        # default vertex array object was deprecated, so I need this
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        self.dshader = shaders.compileProgram(vs, fs)
        glBindFragDataLocation(self.dshader, 0, 'FragData0')
        glBindFragDataLocation(self.dshader, 1, 'FragData1')
        glLinkProgram(self.dshader)
        glDeleteVertexArrays(1, [vao])
        self.select_shader(self.dshader)

        anames = ['inVertex', 'inColor']
        anames0 = anames
        for name in anames:
            define_attrib(self.dshader, name)

        names0 = ['uWorldM', 'uViewM', 'uProjM',
                  'uWorldOffset', 'uViewOffset',
                  'uArtistID', 'uClipLimit1',
                  'uClipLimit2',
                  'uisMarker', 'uMarkerTex', 'uisImage', 'uImageTex',
                  'uUseClip',
                  'uHasHL', 'uUseArrayID', 'nearZ', 'farZ',
                  'isFrust', 'uHLColor', 'uAlphaTest', 'uAlphaLimit',
                  'uUseSolidColor', 'uColor']
        names = names0
        for name in names:
            define_unform(self.dshader, name)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform1i, 'uisMarker', 0)
        self.set_uniform(glUniform1i, 'uisImage', 0)
        self.set_uniform(glUniform1i, 'uUseClip', 1)
        self.set_uniform(glUniform1i, 'uHasHL', 0)
        self.set_uniform(glUniform3fv, 'uClipLimit1', 1, (1, 0, 0))
        self.set_uniform(glUniform3fv, 'uClipLimit2', 1, (0.0, 1, 1))
        self.set_uniform(glUniform1i, 'uUseArrayID', 0)
        self.set_uniform(glUniform1i, 'uAlphaTest', 0)
        self.set_uniform(glUniform1f, 'uAlphaLimit', 0.0)
        self.set_uniform(glUniform4fv, 'uHLColor', 1, (0, 0, 0., 0.65))
        self.set_uniform(glUniform1i, 'uUseSolidColor', 0)
        self.set_uniform(glUniform4fv, 'uColor', 1, (0, 0, 0., 1.0))

        #
        # line & triangles
        #
        fs = compile_file('lines' + frag_suffix, GL_FRAGMENT_SHADER)
        gs = compile_file('lines' + geom_suffix, GL_GEOMETRY_SHADER)
        vs = compile_file('lines' + vert_suffix, GL_VERTEX_SHADER)
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        self.lshader = shaders.compileProgram(vs, gs, fs)
        glBindFragDataLocation(self.lshader, 0, 'FragData0')
        glBindFragDataLocation(self.lshader, 1, 'FragData1')
        glLinkProgram(self.lshader)
        glDeleteVertexArrays(1, [vao])
        self.select_shader(self.lshader)

        anames = anames0 + ['inNormal', 'inNormalMatrix',
                            'Vertex2', 'vertex_id', 'inTexCoord']
        for name in anames:
            define_attrib(self.lshader, name)
        names = names0 + ['uLightDir', 'uLightColor',
                          'uLightPow', 'uLightPowSpec',
                          'uMaxAlpha', 'uShadowM',
                          'uShadowMaxZ', 'uShadowMinZ',
                          'uShadowTex', 'uUseShadowMap',
                          'uShadowTexSize', 'uShadowTex2',
                          'uStyleTex', 'uisAtlas', 'uAtlasParam',
                          'uLineStyle', 'uAmbient',
                          'uRT0', 'uRT1', 'uisFinal', 'uisClear',
                          'uSCSize', 'uisSolid',
                          'uNormalM', 'uLineWidth']

        for name in names:
            define_unform(self.lshader, name)

        fs = compile_file('lines' + frag_suffix, GL_FRAGMENT_SHADER)
        gs = compile_file('triangles' + geom_suffix, GL_GEOMETRY_SHADER)
        vs = compile_file('lines' + vert_suffix, GL_VERTEX_SHADER)
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        self.tshader = shaders.compileProgram(vs, gs, fs)
        glBindFragDataLocation(self.tshader, 0, 'FragData0')
        glBindFragDataLocation(self.tshader, 1, 'FragData1')
        glLinkProgram(self.tshader)
        glDeleteVertexArrays(1, [vao])
        self.select_shader(self.tshader)

        for name in anames:
            define_attrib(self.tshader, name)
        for name in names:
            define_unform(self.tshader, name)

        #
        #  default shader
        #
        fs = compile_file('simple_oit' + frag_suffix, GL_FRAGMENT_SHADER)
        vs = compile_file('simple' + vert_suffix, GL_VERTEX_SHADER)
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        self.shader = shaders.compileProgram(vs, fs)
        glBindFragDataLocation(self.shader, 0, 'FragData0')
        glBindFragDataLocation(self.shader, 1, 'FragData1')
        glLinkProgram(self.shader)
        glDeleteVertexArrays(1, [vao])
        # print(glGetProgramInfoLog(self.shader))
        self.select_shader(self.shader)

        anames = anames0 + ['inNormal', 'inNormalMatrix',
                            'Vertex2', 'vertex_id', 'inTexCoord']
        for name in anames:
            define_attrib(self.shader, name)
        names = names0 + ['uLightDir', 'uLightColor',
                          'uLightPow', 'uLightPowSpec',
                          'uMaxAlpha', 'uShadowM',
                          'uShadowMaxZ', 'uShadowMinZ',
                          'uShadowTex', 'uUseShadowMap',
                          'uShadowTexSize', 'uShadowTex2',
                          'uStyleTex', 'uisAtlas', 'uAtlasParam',
                          'uLineStyle', 'uAmbient',
                          'uRT0', 'uRT1', 'uisFinal', 'uisClear',
                          'uSCSize', 'uisSolid',
                          'uNormalM']

        for name in names:
            define_unform(self.shader, name)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform1i, 'uisMarker', 0)
        self.set_uniform(glUniform1i, 'uisImage', 0)
        self.set_uniform(glUniform1i, 'uisAtlas', 0)
        self.set_uniform(glUniform1i, 'uUseClip', 1)
        self.set_uniform(glUniform1i, 'uHasHL', 0)
        self.set_uniform(glUniform4fv, 'uHLColor', 1, (0, 0, 0., 0.65))
        self.set_uniform(glUniform1i, 'uLineStyle', -1)
        self.set_uniform(glUniform1i, 'uisFinal', 0)
        self.set_uniform(glUniform1i, 'uisSolid', 0)
        self.set_uniform(glUniform1i, 'uisClear', 0)
        self.set_uniform(glUniform2iv, 'uSCSize', 1, (0, 0))
        self.set_uniform(glUniform1i, 'uUseArrayID', 0)
        self.set_uniform(glUniform1i, 'uAlphaTest', 0)
        self.set_uniform(glUniform1f, 'uAlphaLimit', 0.0)
        self.set_uniform(glUniform1i, 'uUseSolidColor', 0)
        self.set_uniform(glUniform4fv, 'uColor', 1, (0, 0, 0., 1.0))

        self.set_lighting()
        # glEnable(GL_MULTISAMPLE)
        # glEnable(GL_SAMPLE_ALPHA_TO_COVERAGE)
        #glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        #glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_CULL_FACE)
        #c= (GLfloat * 2)()
        #glGetFloatv(GL_ALIASED_LINE_WIDTH_RANGE, c)
        #self._line_width_range = list(np.transpose(c))

        glEnable(GL_MULTISAMPLE)
        #glHint(GL_MULTISAMPLE_FILTER_HINT_NV, GL_NICEST)

        from OpenGL.error import GLError
        try:
            glDisable(GL_POINT_SPRITE)
            self.has_pointsprite = True
        except GLError:
            self.has_pointsprite = False

    def check_msaa(self):
        iMultiSample = (GLint * 1)()
        iNumSamples = (GLint * 1)()
        glGetIntegerv(GL_SAMPLE_BUFFERS, iMultiSample)
        glGetIntegerv(GL_SAMPLES, iNumSamples)
        print(("MSAA on, GL_SAMPLE_BUFFERS ", np.array(iMultiSample),
               " ", np.array(iNumSamples)))

    def setLineWidth(self, l):
        self.set_uniform(glUniform1f, 'uLineWidth', l)
        #print('uLineWidth', l)
        #l = min(l, self._line_width_range[1])
        #l = max(l, self._line_width_range[0])
        # glLineWidth(l)

    def setSolidColor(self, c):
        if c == -1:
            self.set_uniform(glUniform1i, 'uUseSolidColor', 0)
        else:
            self.set_uniform(glUniform1i, 'uUseSolidColor', 1)
            self.set_uniform(glUniform4fv, 'uColor', 1, tuple(c))

    def EnableVertexAttrib(self, name):
        if name in self._p_attrib_loc:
            if self._p_attrib_loc[name] != -1:
                glEnableVertexAttribArray(self._p_attrib_loc[name])

    def DisableVertexAttrib(self, name):
        if name in self._p_attrib_loc:
            if self._p_attrib_loc[name] != -1:
                glDisableVertexAttribArray(self._p_attrib_loc[name])

    def VertexAttribPointer(self, name, *args):
        if name in self._p_attrib_loc:
            if self._p_attrib_loc[name] != -1:
                glVertexAttribPointer(self._p_attrib_loc[name], *args)

    def set_lighting(self, ambient=0.5, light_direction=(1, 0, 1., 0),
                     light=1.0,
                     specular=1.5, light_color=(1.0, 1.0, 1.0),
                     wireframe=0,
                     clip_limit1=[0, 0, 0],
                     clip_limit2=[1, 1, 1], shadowmap=True):
        if not self.init:
            return
        if self._p_shader != self.shader:
            return
        
        #print('set_lighting', light, clip_limit1)
        glUniform4fv(self.shader.uniform_loc['uAmbient'], 1,
                     (ambient, ambient, ambient, 1.0))
        
        self.set_uniform(glUniform3fv, 'uClipLimit1', 1, clip_limit1)
        self.set_uniform(glUniform3fv, 'uClipLimit2', 1, clip_limit2)
        glUniform4fv(self.shader.uniform_loc['uLightDir'], 1, light_direction)
        glUniform3fv(self.shader.uniform_loc['uLightColor'], 1, light_color)
        glUniform1fv(self.shader.uniform_loc['uLightPow'], 1, light)
        glUniform1fv(self.shader.uniform_loc['uLightPowSpec'], 1, specular)

        self._wireframe = wireframe
        self._light_direction = light_direction
        self._use_shadow_map = shadowmap
        # print 'light power', self.shader, light

    def set_lighting_off(self):
        #print('set_lighting_off')
        if self._p_shader != self.shader:
            return

        a = (GLfloat * 4)()
        b = (GLfloat * 1)()
        c = (GLfloat * 1)()
        d = self._use_shadow_map
        glGetUniformfv(self.shader, self.shader.uniform_loc['uAmbient'], a)
        glGetUniformfv(self.shader, self.shader.uniform_loc['uLightPow'], b)
        glGetUniformfv(
            self.shader, self.shader.uniform_loc['uLightPowSpec'], c)

        clip1 = (GLfloat * 3)()
        clip2 = (GLfloat * 3)()
        glGetUniformfv(
            self.shader, self.shader.uniform_loc['uClipLimit1'], clip1)
        glGetUniformfv(
            self.shader, self.shader.uniform_loc['uClipLimit2'], clip2)

        glUniform4fv(self.shader.uniform_loc['uAmbient'], 1,
                     (1.0, 1.0, 1.0, 1.0))
        glUniform1fv(self.shader.uniform_loc['uLightPow'], 1, 0.0)
        glUniform1fv(self.shader.uniform_loc['uLightPowSpec'], 1, 0.0)
        self._use_shadow_map = False

        return list(a)[0], list(b)[0], list(c)[0], d, clip1, clip2

    def OnPaint(self, event):
        # print  self._do_draw_mpl_artists
        #dc = wx.PaintDC(self)

        self.SetCurrent(MyGLCanvas.context)

#        fbo = glGenRenderbuffers(1)
        if not self.init:
            self.InitGL()
            self.init = True
        event.Skip()
        # self.OnDraw()

    def OnSize(self, event):
        if MyGLCanvas.offscreen and self.GetSize()[0] > 2:
            self.SetSize((2, 2))
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        if MyGLCanvas.offscreen:
            return
        size = self.size = self.GetClientSize()

        self.SetCurrent(MyGLCanvas.context)

        glViewport(0, 0, size.width, size.height)

    def del_frame(self):
        glDeleteFramebuffers(len(self.frames), self.frames)
        glDeleteRenderbuffers(len(self.bufs), self.bufs)
        self.frames = []
        self.bufs = []

    def get_newframe(self, w, h):
        self.SetCurrent(MyGLCanvas.context)

        def gen_tex(w, h, internal_format, format, data_type):
            tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexImage2D(GL_TEXTURE_2D, 0, internal_format,
                         w, h, 0, format, data_type, None)
            # glTexImage2DMultisample(GL_TEXTURE_2D_MULTISAMPLE, 8, internal_format,
            #                        w, h, GL_FALSE)

            glBindTexture(GL_TEXTURE_2D, 0)
            return tex

        def gen_renderbuffer(w, h, format):
            buf = glGenRenderbuffers(1)
            glBindRenderbuffer(GL_RENDERBUFFER, buf)
            glRenderbufferStorage(GL_RENDERBUFFER, format,
                                  w, h)
            glBindRenderbuffer(GL_RENDERBUFFER, 0)
            return buf

        frame = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, frame)

        tex = gen_tex(w, h, GL_RGBA, GL_RGBA, GL_UNSIGNED_BYTE)
        tex2 = gen_tex(w, h, GL_RGBA, GL_RGBA, GL_FLOAT)
        dtex = gen_tex(w, h, GL_RGBA, GL_RGBA, GL_UNSIGNED_BYTE)
        otex = gen_tex(w, h, GL_RGBA12, GL_RGBA, GL_FLOAT)
        otex2 = gen_tex(w, h, GL_RGBA12, GL_RGBA, GL_FLOAT)

        buf = gen_renderbuffer(w, h, depth_stencil_format)
        dbuf = gen_renderbuffer(w, h, depth_stencil_format)

#        if not check_framebuffer('creating new frame buffer'): return [None]*4

#        glBindTexture(GL_TEXTURE_2D, 0)
#        glBindRenderbuffer(GL_RENDERBUFFER, 0);
#        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        texs = [tex, tex2, dtex, otex, otex2]
        frames = [frame]
        bufs = [buf, dbuf]

        if multisample > 1:
            wim = w // multisample
            him = h // multisample

            frame2 = glGenFramebuffers(1)
            glBindFramebuffer(GL_FRAMEBUFFER, frame2)
            smallTexId = glGenTextures(1)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, smallTexId)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                         wim, him, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)

            smallTexId2 = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, smallTexId2)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                         wim, him, 0, GL_RGBA, GL_FLOAT, None)

            smallbuf = glGenRenderbuffers(1)
            glBindRenderbuffer(GL_RENDERBUFFER, smallbuf)
            glRenderbufferStorage(GL_RENDERBUFFER,
                                  depth_stencil_format,
                                  wim, him)

            texs.append(smallTexId)
            texs.append(smallTexId2)
            bufs.append(smallbuf)
            frames.append(frame2)

        self.bufs.append(buf)
        self.frames.extend(frames)
        # self.stcs.append(buf)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        stc = None

        return frames, bufs, stc, texs

    def get_frame_4_artist(self, a):
        c = self.get_container(a)
        try:
            w, h, m, frame, buf, stc, dtex = self.frame_list[c]
            return w, h, m, frame, buf, stc, dtex
        except BaseException:
            return [None] * 6

    def force_fill_screen(self):
        # draw a big rectangle covering the entire 3D scene
        # some graphics card (Intel HD) does not do glClear
        # as it supposed to do.
        # It clears a screen area where 3D object exists. Otherwise
        # the buffer is not untouched...
        # This routine forces to erase entire scene.
        I_M = np.diag([1.0] * 4)
        I_MS = np.array([[1., 0., 0., -0.5],
                         [0., 1., 0., -0.5],
                         [0., 0., 1., -0.5],
                         [0., 0., 0., 1.0]])
        self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE, I_M)
        self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE, I_MS)
        self.set_uniform(glUniformMatrix4fv, 'uProjM', 1, GL_TRUE, I_M)
        self.set_uniform(glUniform1i, 'uUseClip', 0)
        glDisable(GL_BLEND)
        glDepthMask(GL_FALSE)
        glColor4f(1., 1, 1, 0)
        glRecti(-1, -1, 2, 2)
        self.set_depth_mask()
        # glFinish()
        # glDepthMask(GL_TRUE)

    def prepare_proj_matrix(self):
        # glMatrixMode(GL_PROJECTION)
        # glLoadIdentity()
        dist = self.M[-1]

        # viwe range shoud be wide enough to avoid near clipping
        minZ = dist - near_clipping
        maxZ = dist + near_clipping
        self.set_uniform(glUniform1f, 'nearZ', -minZ)
        self.set_uniform(glUniform1f, 'farZ', -maxZ)

        if self._use_frustum:
            projM = frustum(-minZ / near_clipping,
                            minZ / near_clipping,
                            -minZ / near_clipping,
                            minZ / near_clipping,
                            minZ, maxZ, view_scale=self._gl_scale)
            self.set_uniform(glUniform1i, 'isFrust', 1)
        else:
            a = dist / near_clipping
            projM = ortho(-a, a, -a, a, minZ, maxZ, view_scale=self._gl_scale)
            self.set_uniform(glUniform1i, 'isFrust', 0)
        projM = np.dot(self.M_extra, projM)
        return projM, minZ, maxZ

    def use_depthmap_mode(self, frame, buf, texs, w, h):
        glBindFramebuffer(GL_FRAMEBUFFER, frame)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_STENCIL_ATTACHMENT,
                                  GL_RENDERBUFFER, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_STENCIL_ATTACHMENT,
                                  GL_RENDERBUFFER, buf[1])
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, buf[1])
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT1,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, texs[0], 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT1,
                               GL_TEXTURE_2D, texs[1], 0)

        if not check_framebuffer('going to depthmap mode'):
            return

        self.select_shader(self.dshader)

        projM, minZ, maxZ = self.prepare_proj_matrix()

        glViewport(0, 0, w, h)
        R = np.array([0.5, 0.5, 0.5])
        d = np.array(self._light_direction)[:3] * 10
        E = d / np.sqrt(np.sum(d**2)) * self.M[-1] + R

        V = np.array((0, 0, 1))
        #zfront, zback = -10, 10

        from ifigure.matplotlib_mod.axes3d_mod import view_transformation
        viewM = view_transformation(E, R, V)

        self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE, self.M[0])
        self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE, viewM)
        self.set_uniform(glUniformMatrix4fv, 'uProjM', 1, GL_TRUE, projM)
        self.set_uniform(glUniform4fv, 'uHLColor', 1, self._hl_color)

        M = np.dot(viewM, self.M[0])  # viewM * worldM
        M = np.dot(projM, M)  # projM * viewM * worldM
        # glLoadMatrixf(np.transpose(M).flatten())

        '''
        if self._use_clip:
            self.set_uniform(glUniform1i, 'uUseClip', 1)
        else:
            self.set_uniform(glUniform1i, 'uUseClip', 0)
        ''' 
        self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                          GL_COLOR_ATTACHMENT1])

        self._shadow = True

        return (M, minZ, maxZ)

    def use_draw_mode(self, frame, buf, texs, w, h, shadow_params=None):

        glBindFramebuffer(GL_FRAMEBUFFER, frame)

        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_STENCIL_ATTACHMENT,
                                  GL_RENDERBUFFER, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_STENCIL_ATTACHMENT,
                                  GL_RENDERBUFFER, buf[0])
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                  GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, buf[0])

        self.set_draw_mode_tex(texs)

        if not check_framebuffer('going to normal mode'):
            return

        def setup_shader():
            self.set_uniform(glUniform1i, 'uisFinal', 0)
            self.set_uniform(glUniform2iv, 'uSCSize', 1, (w, h))
            self.set_uniform(glUniform1i, 'uUseShadowMap', 0)

            if self._use_shadow_map:
                self.set_uniform(glUniform1i, 'uUseShadowMap', 1)

            self.projM, minZ, maxZ = self.prepare_proj_matrix()

            glViewport(0, 0, w, h)

            # loading this so that I don't need to compute matrix for normal
            # vec
            M = np.dot(self.M[1], self.M[0])  # viewM * worldM
            # (core) glLoadMatrixf(np.transpose(M).flatten())

            self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE,
                             self.M[0])
            self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE,
                             self.M[1])
            self.set_uniform(glUniformMatrix4fv, 'uProjM',
                             1, GL_TRUE, self.projM)

            tmp = np.dot(self.M[1], self.M[0])[:3, :3]
            normM = np.linalg.inv(tmp).transpose()
            self.set_uniform(glUniformMatrix3fv, 'uNormalM', 1, GL_TRUE, normM)

            if shadow_params is not None:
                self.set_uniform(glUniformMatrix4fv, 'uShadowM', 1, GL_TRUE,
                                 shadow_params[0])
                self.set_uniform(glUniform1f, 'uShadowMinZ', shadow_params[1])
                self.set_uniform(glUniform1f, 'uShadowMaxZ', shadow_params[2])
                self.test_M = shadow_params[0]

            glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                              GL_COLOR_ATTACHMENT1])

            self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)

            M = np.dot(self.M[1], self.M[0])  # viewM * worldM
            M = np.dot(self.projM, M)  # projM * viewM * worldM
            self.draw_M = M
            if self._alpha_blend:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            else:
                glDisable(GL_BLEND)

            self.set_uniform(glUniform4fv, 'uHLColor', 1, self._hl_color)
            self._shadow = False

        self.select_shader(self.lshader)
        setup_shader()
        self.select_shader(self.tshader)
        setup_shader()
        self.select_shader(self.shader)
        setup_shader()

    def set_oit_mode_tex(self, texs, firstpath=True):
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, texs[0], 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT1,
                               GL_TEXTURE_2D, 0, 0)
        if firstpath:
            glFramebufferTexture2D(GL_FRAMEBUFFER,
                                   GL_COLOR_ATTACHMENT1,
                                   GL_TEXTURE_2D, texs[1], 0)
        glBlendFunc(1, GL_ONE, GL_ZERO)

    def set_draw_mode_tex(self, texs):

        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT1,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, texs[3], 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT1,
                               GL_TEXTURE_2D, texs[4], 0)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def choose_artists(self, aa, draw_arrow):
        artists = [(a.get_alpha_float(), a) for a in self.artists_data[aa]]
        artists = list(reversed(sorted(artists, key=lambda x: x[0])))
        artists = ([(alpha, a) for alpha, a in artists if not a._gl_isLast] +
                   [(alpha, a) for alpha, a in artists if a._gl_isLast])
        if draw_arrow:
            artists = [(alpha, a) for alpha, a in artists if a._gl_isArrow]
        else:
            artists = [(alpha, a)
                       for alpha, a in artists if not a._gl_isArrow]
        return artists

    def do_draw_artists(self, tag, update_id=False, do_clear=None,
                        draw_solid=True,
                        draw_non_solid=True,
                        do_clear_depth=False,
                        id_dict=None, ignore_alpha=False,
                        draw_arrow=False):

        if id_dict is None:
            id_dict = {}
        need_oit = False
        current_id = 1.0
        if do_clear is not None:
            glClearColor(*do_clear)
            # glClear(GL_COLOR_BUFFER_BIT|GL_STENCIL_BUFFER_BIT|GL_ACCUM_BUFFER_BIT)
            glClear(GL_COLOR_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
        if do_clear_depth:
            glClear(GL_DEPTH_BUFFER_BIT)

        for aa in self.artists_data:
            if aa is not tag:
                continue
            if aa not in self.vbo:
                self.vbo[aa] = weakref.WeakKeyDictionary()
            # aa:axes, a: aritsit

            artists = self.choose_artists(aa, draw_arrow)

            for alpha, a in artists:
                if alpha == 1 or alpha is None:
                    if not draw_solid:
                        current_id = current_id + 1
                        continue
                else:
                    need_oit = True
                    if not draw_non_solid:
                        current_id = current_id + 1
                        continue
                if ignore_alpha:
                    alpha = 1.0
                if a.axes is not aa:
                    continue
                if self._artist_mask is not None and a not in self._artist_mask:
                    continue
                if update_id:
                    cid = ((int(current_id) % 256) / 255.,
                           (int(current_id) // 256 % 256) / 255.,
                           0.0, 1.0)
                    #       (int(current_id)/256**2 % 256)/255., 1.0)
                    self.set_uniform(glUniform4fv, 'uArtistID', 1, cid)
                if ((a._gl_hl and not self._hittest_map_update)
                        and not self._no_hl):
                    # second condition indicate it is during pan/rotate
                    self.set_uniform(glUniform1i, 'uHasHL', 1)
                else:
                    self.set_uniform(glUniform1i, 'uHasHL', 0)

                if a not in self.vbo[aa]:
                    xxx = [None] * len(self.artists_data[aa][a])
                else:
                    xxx = self.vbo[aa][a]

                for k, data in enumerate(self.artists_data[aa][a]):
                    m = getattr(self, 'makevbo_' + data[0])
                    if len(xxx) == k:
                        xxx.append(None)
                    xxx[k] = m(xxx[k], *data[1], **data[2])
                    m = getattr(self, 'draw_' + data[0])
                    m(xxx[k], *data[1], **data[2])

                self.vbo[aa][a] = xxx
                self.vbo_check[str(id(a)) + '_' + str(id(aa))] = xxx

                id_dict[int(current_id)] = weakref.ref(a)
                current_id = current_id + 1
        # glFinish()
        return id_dict, need_oit

    def make_shadow_texture(self, w, h, data2=None):
        #        glBindFramebuffer(GL_FRAMEBUFFER, frame)
        shadow_tex = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0 + 1)
        glBindTexture(GL_TEXTURE_2D, shadow_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)

        #print('reading shadow data')
        glReadBuffer(GL_COLOR_ATTACHMENT0)
        #data = glReadPixels(0,0, w, h, GL_RGBA, GL_UNSIGNED_BYTE)
        #data = (np.fromstring(data, np.uint8).reshape(h, w, -1))
        #self.shadowc =  data.copy()
        glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                         0, 0, w, h, 0)
        glActiveTexture(GL_TEXTURE0)

        #  self.set_uniform(glUniform1i, 'uShadowTex', 1)
        #  self.set_uniform(glUniform2fv, 'uShadowTexSize', 1, (w, h))
        if data2 is not None:
            shadow_tex2 = glGenTextures(1)

            glBindTexture(GL_TEXTURE_2D, shadow_tex)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)
            # glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
            #          w, h, 0, GL_DEPTH_COMPONENT, GL_FLOAT,
            #         data2)
            glReadBuffer(GL_COLOR_ATTACHMENT1)
            glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                             0, 0, w, h, 0)
            glActiveTexture(GL_TEXTURE0 + 2)
#           self.set_uniform(glUniform1i, 'uShadowTex2', 2)
            return shadow_tex, shadow_tex2
        else:
            return shadow_tex

    def make_oit_texture(self, texs):
        #        glBindFramebuffer(GL_FRAMEBUFFER, frame)
        glActiveTexture(GL_TEXTURE0 + 1)
        glBindTexture(GL_TEXTURE_2D, texs[3])
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)

        glActiveTexture(GL_TEXTURE0 + 2)
        glBindTexture(GL_TEXTURE_2D, texs[4])
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)

        glActiveTexture(GL_TEXTURE0)

    def draw_mpl_artists(self, tag):
        self._use_frustum = tag._use_frustum
        self._use_clip = tag._use_clip

        self.gc_artist_data()
        self.gc_vbo_dict()

        if MyGLCanvas.offscreen:
            w, h, m, frames, buf, stc, texs = self.get_frame_4_artist(tag)
            frame = frames[0]
            glBindFramebuffer(GL_FRAMEBUFFER, frame)
        else:
            w, h = self.GetClientSize()
            glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glEnable(GL_DEPTH_TEST)
        self.set_depth_mask(True)

        self.M = tag._matrix_cache
        self.M_extra = tag._matrix_cache_extra
        # glPushMatrix()
        self.set_uniform(glUniform1i, 'uisSolid', 1)
        if self._use_shadow_map:
            shadow_params = self.use_depthmap_mode(frame, buf, texs, w, h)
            self.do_draw_artists(tag,
                                 do_clear=(0, 0, 0, 0),
                                 do_clear_depth=True,
                                 draw_non_solid=False)
            # glFinish()
            shadow_tex = self.make_shadow_texture(w, h, None)
            self.use_draw_mode(frame, buf, texs, w, h, shadow_params)
            self.set_uniform(glUniform1i, 'uShadowTex', 1)
            self.set_uniform(glUniform1i, 'uShadowTex2', 2)
            self.set_uniform(glUniform2fv, 'uShadowTexSize', 1, (w, h))
            self.set_uniform(glUniform1i, 'uUseShadowMap', 1)
        else:
            self.use_draw_mode(frame, buf, texs, w, h)
            self.set_uniform(glUniform1i, 'uUseShadowMap', 0)

        ##
        # draw solid first ...
        ##
        # self.make_oit_texture(texs)
        self.set_oit_mode_tex(texs)

        #self.set_uniform(glUniform1i, 'uisClear', 1)
        #
        # self.do_draw_artists(tag)
        #self.set_uniform(glUniform1i, 'uisClear', 0)
        glClearColor(0, 0, 0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        #
        #  We draw id_dict first. Since RG BA are both used
        #  I need to disable blending...
        #
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)  # glBlendFunc(GL_ONE, GL_ZERO)
        #self._no_smooth = True
        # glEnable(GL_BLEND)  # glBlendFunc(GL_ONE, GL_ZERO)
        #glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        id_dict, need_oit = self.do_draw_artists(tag, update_id=True,
                                                 do_clear=(0, 0, 0, 0),
                                                 do_clear_depth=True,
                                                 ignore_alpha=True)
        if self._hittest_map_update:
            self.read_hit_map_data(tag)

        # if multisample == 1: #use OpenGL hardware smoothing in this case
        #    self._no_smooth = False

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])
        self.do_draw_artists(tag, do_clear=(0, 0, 0, 0),
                             draw_non_solid=False,
                             do_clear_depth=True)
        if need_oit:
            self.set_uniform(glUniform1i, 'uisSolid', 0)
            self.set_uniform(glUniform1i, 'uUseShadowMap', 0)

            ##
            # draw transparent....
            ##
            #self.use_draw_mode(frame, buf, texs, w, h)
            self.set_draw_mode_tex(texs)
            glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                              GL_COLOR_ATTACHMENT1])
            # From here
            glClearColor(0, 0, 0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)

            # to here
            glDepthMask(GL_FALSE)
            glEnable(GL_BLEND)
            glBlendEquationSeparate(GL_FUNC_ADD, GL_FUNC_ADD)
            glBlendFuncSeparate(GL_ONE, GL_ONE, GL_ZERO,
                                GL_ONE_MINUS_SRC_ALPHA)
            #glBlendFuncSeparate(GL_ONE, GL_ONE, GL_ONE, GL_ZERO)

            # glDisable(GL_DEPTH_TEST)
            glEnable(GL_DEPTH_TEST)
            self.do_draw_artists(tag, draw_solid=False)

            ##
            # final path...
            ##
            self.make_oit_texture(texs)
            self.set_oit_mode_tex(texs, firstpath=False)
            #glBlendFunc(GL_ONE, GL_ZERO)

            #self.set_uniform(glUniform1i, 'uisClear', 2)
            # self.force_fill_screen()
            #self.set_uniform(glUniform1i, 'uisClear', 0)
            # glFinish()
            glFlush()

            self.set_uniform(glUniform1i, 'uRT0', 1)
            self.set_uniform(glUniform1i, 'uRT1', 2)

            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            #glBlendFunc(GL_SRC_ALPHA, GL_ZERO)
            #glBlendFunc(GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            self.set_uniform(glUniform1i, 'uisFinal', 1)
            self._do_depth_test = False
            glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])
            self.do_draw_artists(tag, draw_solid=False)
            self.set_uniform(glUniform1i, 'uisFinal', 0)
            self._do_depth_test = True

        if self._hittest_map_update:
            self._im_stored = self.read_data(tag)
        self.do_draw_artists(tag,
                             draw_non_solid=False,
                             do_clear_depth=True,
                             draw_arrow=True)
        # glFinish()
        # glPopMatrix()

        if self._use_shadow_map:
            glDeleteTextures(shadow_tex)
            # glDeleteTextures(shadow_tex2)
        self._do_draw_mpl_artists = False
        self._artist_mask = None
        return id_dict

    @property
    def stored_im(self):
        return self._im_stored

    def read_hit_map_data(self, a):
        w, h, m, frames, buf, stc, texs = self.get_frame_4_artist(a)
        frame = frames[0]

        if multisample > 1:
            frame2 = frames[1]
            wim = w // multisample
            him = h // multisample

            glBindFramebuffer(GL_READ_FRAMEBUFFER, frame)
            glReadBuffer(GL_COLOR_ATTACHMENT1)

            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, frame2)
            glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                   GL_TEXTURE_2D, texs[-2], 0)
            glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT1,
                                   GL_TEXTURE_2D, texs[-1], 0)
            glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                      GL_STENCIL_ATTACHMENT,
                                      GL_RENDERBUFFER, buf[2])
            glFramebufferRenderbuffer(GL_FRAMEBUFFER,
                                      GL_DEPTH_ATTACHMENT,
                                      GL_RENDERBUFFER, buf[2])
            glDrawBuffer(GL_COLOR_ATTACHMENT1)
            glBlitFramebuffer(0, 0, w, h,
                              0, 0, wim, him,
                              GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT,
                              GL_NEAREST)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            glBindFramebuffer(GL_FRAMEBUFFER, frame2)
        else:
            wim = w
            him = h
            glBindFramebuffer(GL_FRAMEBUFFER, frame)
        ###

        glReadBuffer(GL_COLOR_ATTACHMENT1)  # (to check id buffer)
        stream_read = True

        if stream_read:
            pixel_buffers = glGenBuffers(2)
            size = wim * him

            glBindBuffer(GL_PIXEL_PACK_BUFFER, pixel_buffers[0])
            glBufferData(GL_PIXEL_PACK_BUFFER, size * 4, None, GL_STREAM_READ)

            glReadPixels(0, 0, wim, him, GL_RGBA,
                         GL_UNSIGNED_BYTE, c_void_p(0))
            data2 = string_at(glMapBuffer(
                GL_PIXEL_PACK_BUFFER, GL_READ_ONLY), size * 4)
            # *255.
            #idmap = (np.fromstring(data2, np.uint8).reshape(him, wim, -1))
            idmap = (
                np.frombuffer(
                    bytes(data2), dtype=np.uint8)).reshape(
                him, wim, -1)
            idmap2 = idmap[:, :, 2] + idmap[:, :, 3] * 256
            idmap0 = idmap[:, :, 0] + idmap[:, :, 1] * 256
            glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
            glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)

            glBindBuffer(GL_PIXEL_PACK_BUFFER, pixel_buffers[1])
            glBufferData(GL_PIXEL_PACK_BUFFER, size * 4, None, GL_STREAM_READ)
            glReadPixels(0, 0, wim, him, GL_DEPTH_COMPONENT,
                         GL_FLOAT, c_void_p(0))

            data3 = string_at(glMapBuffer(
                GL_PIXEL_PACK_BUFFER, GL_READ_ONLY), size * 4)
            #depth = np.fromstring(data3, np.float32).reshape(him, wim)
            depth = (
                np.frombuffer(
                    bytes(data3),
                    dtype=np.float32)).reshape(
                him,
                wim)

            glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
            glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
            glDeleteBuffers(2, pixel_buffers)

        else:
            data2 = glReadPixels(0, 0, wim, him, GL_RGBA, GL_FLOAT)
            data3 = glReadPixels(0, 0, wim, him, GL_DEPTH_COMPONENT, GL_FLOAT)
            #idmap = (np.fromstring( data2, np.float32).reshape(him, wim, -1)) * 255.
            idmap = (
                np.frombuffer(
                    bytes(data2), dtype=np.float32).reshape(
                    him, wim, -1)) * 255.
            idmap2 = idmap[:, :, 2] + idmap[:, :, 3] * 256
            idmap0 = idmap[:, :, 0] + idmap[:, :, 1] * 256
            #depth = np.fromstring(data3, np.float32).reshape(him, wim)
            depth = np.frombuffer(
                bytes(data3),
                dtype=np.float32).reshape(
                him,
                wim)

        glReadBuffer(GL_NONE)
        # if multisample > 1:
        #   ms =multisample
        #   self._hit_map_data = (np.rint(idmap0)[::ms, ::ms],
        #                         np.rint(idmap2)[::ms, ::ms],
        #                         depth[::ms, ::ms])
        # else:
        self._hit_map_data = (np.rint(idmap0).astype(int),
                              np.rint(idmap2).astype(int),
                              depth)

    def read_data(self, a):
        w, h, m, frames, buf, stc, texs = self.get_frame_4_artist(a)
        frame = frames[0]
        ###
        if multisample > 1:
            frame2 = frames[1]
            wim = w // multisample
            him = h // multisample

            glBindFramebuffer(GL_READ_FRAMEBUFFER, frame)
            glReadBuffer(GL_COLOR_ATTACHMENT0)
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, frame2)
            glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                   GL_TEXTURE_2D, texs[-2], 0)
            glDrawBuffer(GL_COLOR_ATTACHMENT0)
            glBlitFramebuffer(0, 0, w, h,
                              0, 0, wim, him,
                              GL_COLOR_BUFFER_BIT, GL_LINEAR)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            glBindFramebuffer(GL_FRAMEBUFFER, frame2)
        else:
            wim = w
            him = h
            glBindFramebuffer(GL_FRAMEBUFFER, frame)
            self.set_oit_mode_tex(texs)
        ###
        glReadBuffer(GL_COLOR_ATTACHMENT0)
        size = wim * him

        def read_pixbuf(pixel_buffer):
            glBufferData(GL_PIXEL_PACK_BUFFER, size * 4, None, GL_STREAM_READ)
            glReadPixels(0, 0, wim, him, GL_RGBA,
                         GL_UNSIGNED_BYTE, c_void_p(0))

        def map_pixbuf(pixel_buffer):
            data = string_at(glMapBuffer(GL_PIXEL_PACK_BUFFER,
                                         GL_READ_ONLY), size * 4)
            glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
            return data
        stream_read = True
        # number of buffering (> 3 does not work well, show noise on screen)
        nump = 2

        new_target = True  # flag to force rest pixel buffering.
        if self._read_data_pixbuf_target1[0]() is not None:
            # can use pixel buff data if size is the same and previous data
            # targets the same axes artist.
            if (self._read_data_pixbuf_target1[0]() == a and
                    self._read_data_pixbuf_target1[1] == size):
                new_target = False

        if stream_read:
            if self._hittest_map_update or new_target:
                pixel_buffer = glGenBuffers(1)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, pixel_buffer)
                read_pixbuf(pixel_buffer)
                data = map_pixbuf(pixel_buffer)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
                glDeleteBuffers(1, [pixel_buffer])
                if self.PIXBUFS[0] is not None:
                    glDeleteBuffers(nump, self.PIXBUFS[:-1])
                    self.PIXBUFS = (None, None, None)
                glFlush()
            elif self.PIXBUFS[0] is None:
                bufs = glGenBuffers(nump)
                self.PIXBUFS = list(bufs) + [1]
                pixel_buffer = self.PIXBUFS[0]
                glBindBuffer(GL_PIXEL_PACK_BUFFER, pixel_buffer)
                read_pixbuf(pixel_buffer)
                data = map_pixbuf(pixel_buffer)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
                glFlush()
                # self.PIXBUFS = (None, None, None) # disable buffering
                self._data_bk = data
            else:
                read_buffer = self.PIXBUFS[(self.PIXBUFS[-1]) % nump]
                map_buffer = self.PIXBUFS[(self.PIXBUFS[-1] + 1) % nump]
                glBindBuffer(GL_PIXEL_PACK_BUFFER, read_buffer)
                read_pixbuf(read_buffer)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, map_buffer)
                data = map_pixbuf(map_buffer)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
                self.PIXBUFS[-1] += 1
                glFlush()
            self._read_data_pixbuf_target1 = (weakref.ref(a), size)
        else:
            data = glReadPixels(0, 0, wim, him, GL_RGBA, GL_UNSIGNED_BYTE)
        #image = np.fromstring(data, np.uint8).reshape(him, wim, -1)
        image = np.frombuffer(
            bytes(data), dtype=np.uint8).reshape(
            him, wim, -1)

        # if multisample > 1:
        #glDeleteFramebuffers(1, [frame2])
        #w,h,d = image.shape
        #image = imresize(image, (w/multisample , h/multisample, d))

        glReadBuffer(GL_NONE)
        if self._hittest_map_update:
            return (image,
                    self._hit_map_data[0],
                    self._hit_map_data[1],
                    self._hit_map_data[2])
        else:
            return image
    #
    #  drawing routines
    #

    def EnableVertex(self, vbos):
        vbos['v'].bind()
        self.EnableVertexAttrib('inVertex')
        self.VertexAttribPointer('inVertex', 3, GL_FLOAT, GL_FALSE,
                                 0, None)

    def DisableVertex(self, vbos):
        vbos['v'].bind()
        self.DisableVertexAttrib('inVertex')

    def EnableNormal(self, vbos):
        if vbos['n'] is None:
            return
        vbos['n'].bind()
        self.EnableVertexAttrib('inNormal')
        self.VertexAttribPointer('inNormal', 3, GL_FLOAT, GL_FALSE,
                                 0, None)

    def DisableNormal(self, vbos):
        if vbos['n'] is None:
            return
        vbos['n'].bind()
        self.DisableVertexAttrib('inNormal')

    def EnableFaceColor(self, vbos):
        vbos['fc'].bind()
        self.EnableVertexAttrib('inColor')
        self.VertexAttribPointer('inColor', 4, GL_FLOAT, GL_FALSE,
                                 0, None)

    def DisableFaceColor(self, vbos):
        vbos['fc'].unbind()
        self.DisableVertexAttrib('inColor')

    def EnableEdgeColor(self, vbos):
        vbos['ec'].bind()
        self.EnableVertexAttrib('inColor')
        self.VertexAttribPointer('inColor', 4, GL_FLOAT, GL_FALSE,
                                 0, None)

    def DisableEdgeColor(self, vbos):
        vbos['ec'].unbind()
        self.DisableVertexAttrib('inColor')

    def EnableVertexID(self, vbos):
        if vbos['vertex_id'] is not None:
            vertex_id = vbos['vertex_id']
            vertex_id.bind()
            self.EnableVertexAttrib('vertex_id')
            self.VertexAttribPointer('vertex_id', 1, GL_FLOAT, GL_FALSE,
                                     0, None)
            self.set_uniform(glUniform1i, 'uUseArrayID', 1)
        else:
            self.set_uniform(glUniform1i, 'uUseArrayID', 0)

    def draw_polygon(self, vbos, gc, f, c, facecolor=None, edgecolor=None):
        glBindVertexArray(vbos['vao'])
        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        self.EnableFaceColor(vbos)
        lw = gc.get_linewidth()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
        glClear(GL_STENCIL_BUFFER_BIT)
        glStencilFunc(GL_ALWAYS, 1, 1)
        glStencilOp(GL_INCR, GL_INCR, GL_INCR)
        glDrawArrays(GL_TRIANGLE_FAN, f, c)

        self.set_depth_test()
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glStencilFunc(GL_EQUAL, 1, 1)
        glStencilOp(GL_KEEP, GL_KEEP, GL_ZERO)
        if facecolor is not None:
            glColor(facecolor)

        if self._wireframe != 2:
            if self._wireframe == 1:
                glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
            glDrawArrays(GL_TRIANGLE_FAN, f, c)
            if self._wireframe == 1:
                glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

        glDisable(GL_STENCIL_TEST)
        glDepthFunc(GL_LEQUAL)
        if edgecolor is not None:
            glColor(edgecolor)
#        if not self._shadow :
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0.005, 0.))
#            self.set_uniform(glUniform4fv, 'uViewOffset', 1,
#                             (0, 0, 0.00, 0.))

        if self._wireframe == 2:
            glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glDrawArrays(GL_LINE_STRIP, f, c)
        self.set_depth_mask()
        if self._wireframe == 2:
            self.set_depth_test()
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0.00, 0.))

        glDepthFunc(GL_LESS)

        self.setSolidColor(-1)
        self.DisableVertex(vbos)
        self.DisableNormal(vbos)
        self.DisableFaceColor(vbos)

        glBindVertexArray(0)
        self.select_shader(self.shader)

    def draw_path_atlas(self, vbos, gc, path, *args):

        glBindVertexArray(vbos['vao'])
        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        lw = gc.get_linewidth()

        w = vbos['count']
        void1, void2, w0, h0 = glGetIntegerv(GL_VIEWPORT)

        atlas_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, atlas_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R16,
                     w, 1, 0, GL_RED, GL_FLOAT, None)

        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT2,
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT2,
                               GL_TEXTURE_2D, atlas_tex, 0)

        glDrawBuffer(GL_COLOR_ATTACHMENT2)

        glDisable(GL_DEPTH_TEST)
        tmp = get_vbo(vbos['v'].data[3:],
                      usage='GL_STATIC_DRAW')

        tmp.bind()
        self.VertexAttribPointer('Vertex2', 3, GL_FLOAT,
                                 GL_FALSE, 0, None)
        tmp.unbind()

        vertex_id = get_vbo(np.arange(w, dtype=np.float32),
                            usage='GL_STATIC_DRAW')
        vertex_id.bind()
        self.VertexAttribPointer('vertex_id', 1, GL_FLOAT, GL_FALSE, 0, None)
        self.EnableVertexAttrib('vertex_id')
        self.EnableVertexAttrib('Vertex2')
        glViewport(0, 0, w, 1)
        self.set_uniform(glUniform1i, 'uisAtlas', 1)
        self.set_uniform(glUniform3fv, 'uAtlasParam', 1, [w, w0, h0])
        glDrawArrays(GL_LINE_STRIP, 0, w)
        glReadBuffer(GL_COLOR_ATTACHMENT2)
        data = glReadPixels(0, 0, w, 1, GL_RED, GL_FLOAT)
        glReadBuffer(GL_NONE)

        glFramebufferTexture2D(GL_FRAMEBUFFER,
                               GL_COLOR_ATTACHMENT2,
                               GL_TEXTURE_2D, 0, 0)

        #atlas = np.hstack((0, np.cumsum(np.fromstring(data, np.float32))))[:-1]
        atlas = np.hstack(
            (0,
             np.cumsum(
                 np.frombuffer(
                     bytes(data),
                     dtype=np.float32))))[
            :-1]
        atlas *= 1000.
        if globals()['multisample'] == 2:
            atlas /= 2.
        self.set_depth_test()
        glViewport(0, 0, w0, h0)
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                          GL_COLOR_ATTACHMENT1])
        vertex_id.unbind()
        self.setSolidColor(-1)
        self.DisableVertexAttrib('inNormal')
        self.DisableVertexAttrib('inVertex')
        self.DisableVertexAttrib('Vertex2')
        self.DisableVertexAttrib('vertex_id')
        glBindVertexArray(0)
        self.select_shader(self.shader)
        return atlas

    def draw_path_drawarray(self, vbos, gc, path, rgbFace=None,
                            stencil_test=True, linestyle='None',
                            atlas=None):

        self.select_shader(self.lshader)
        glBindVertexArray(vbos['vao'])
        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        lw = gc.get_linewidth()

        self.setLineWidth(lw * multisample)
        self.setSolidColor(gc._rgb)
        if self._wireframe == 2:
            glDisable(GL_DEPTH_TEST)

        if atlas is not None:
            vertex_id = get_vbo(atlas.astype(np.float32),
                                usage='GL_STATIC_DRAW')
            vertex_id.bind()
            self.VertexAttribPointer(
                'vertex_id', 1, GL_FLOAT, GL_FALSE, 0, None)
            self.EnableVertexAttrib('vertex_id')

        self.set_uniform(glUniform1i, 'uisAtlas', 0)
        if linestyle == '--':
            self.set_uniform(glUniform1i, 'uLineStyle', 0)
        elif linestyle == '-.':
            self.set_uniform(glUniform1i, 'uLineStyle', 1)
        elif linestyle == ":":
            self.set_uniform(glUniform1i, 'uLineStyle', 2)
        else:
            self.set_uniform(glUniform1i, 'uLineStyle', -1)

        glDrawArrays(GL_LINE_STRIP, 0, vbos['count'])

        self.set_uniform(glUniform1i, 'uLineStyle', -1)
        self.setSolidColor(-1)
        self.DisableVertexAttrib('inNormal')
        self.DisableVertexAttrib('inVertex')
        if atlas is not None:
            self.DisableVertexAttrib('vertex_id')
        glBindVertexArray(0)
        self.select_shader(self.shader)

    def draw_path(self, vbos, gc, *args, **kwargs):
        rgbFace = kwargs.get('rgbFace', None)
        linestyle = kwargs.get('linestyle', None)
        lw = gc.get_linewidth()
        if rgbFace is None:
            if lw > 0:
                if (linestyle == '-' or self._p_shader != self.shader):
                    self.draw_path_drawarray(vbos, gc, *args, **kwargs)
                elif linestyle == 'None':
                    return
                else:
                    atlas = self.draw_path_atlas(vbos, gc, *args)
                    kwargs['atlas'] = atlas
                    self.draw_path_drawarray(vbos, gc, *args, **kwargs)
        else:
            self.draw_polygon(vbos, gc, 0, vbos['count'], facecolor=rgbFace,
                              edgecolor=gc._rgb)

            mode = 3  # polygon
        return

    def makevbo_path(self, vbos, gc, path, *args, **kwargs):
        if vbos is None:
            vbos = {'v': None, 'count': None, 'n': None}
            vbos['vao'] = glGenVertexArrays(1)

        glBindVertexArray(vbos['vao'])
        if vbos['v'] is None or vbos['v'].need_update:
            xyz = np.hstack((path[0], path[1], path[2])).reshape(3, -1)
            xyz = np.transpose(xyz).flatten()
            # 0, 0, 0 is to make length longer by 1 vetex
            # for styled_drawing
            xyz = np.hstack((xyz, 0, 0, 0))
            count = len(path[0])
            xyz = np.array(xyz, dtype=np.float32)

            if len(path) > 3:
                if paths[3] is None:
                    norms = None
                elif len(paths[3]) == 1:
                    norms = [paths[3]] * len(path[0])
                    norms = np.hstack(norms).astype(np.float32).flatten()
                else:
                    norms = paths[3].astype(np.float32).flatten()
            else:
                norms = None
            if vbos['v'] is None:
                vbos['v'] = get_vbo(xyz, usage='GL_STATIC_DRAW')
            else:
                vbos['v'].set_array(xyz)
            if norms is not None:
                if vbos['n'] is None:
                    vbos['n'] = get_vbo(norms, usage='GL_STATIC_DRAW')
                else:
                    vbos['n'].set_array(norms)
            else:
                vbos['n'] = None
            vbos['count'] = count
            vbos['v'].need_update = False
        glBindVertexArray(0)
        return vbos

    def draw_image(self, vbos, gc, path, trans, im,
                   interp='nearest',
                   always_noclip=False):

        if always_noclip:
            self.set_uniform(glUniform1i, 'uUseClip', 0)
        
        self.select_shader(self.lshader)
        self.select_shader(self.shader)
        glBindVertexArray(vbos['vao'])

        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        vbos['uv'].bind()
        self.EnableVertexAttrib('inTexCoord')
        self.VertexAttribPointer('inTexCoord', 2, GL_FLOAT, GL_FALSE,
                                 0, None)
        glBindTexture(GL_TEXTURE_2D, vbos['im'])
        glActiveTexture(GL_TEXTURE0 + 0)
        self.set_uniform(glUniform1i, 'uImageTex', 0)
        self.set_uniform(glUniform1i, 'uUseArrayID', 0)

        self.set_uniform(glUniform1i, 'uisImage', 1)
        if self._wireframe == 2:
            glDisable(GL_DEPTH_TEST)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        if self._wireframe == 2:
            self.set_depth_test()

        self.set_uniform(glUniform1i, 'uisImage', 0)
        # self.DisableVertexAttrib('inVertex')
        self.DisableVertex(vbos)
        self.DisableNormal(vbos)
        vbos['uv'].unbind()
        self.DisableVertexAttrib('inTexCoord')

        if self._use_clip and always_noclip:
            self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)
        
        glBindVertexArray(0)

    def makevbo_image(self, vbos, gc, path, trans, im,
                      interp='nearest',
                      always_noclip=False):
        if vbos is None:
            vbos = vbos_dict({'v': None, 'count': None, 'n': None, 'im': None,
                              'uv': None, 'im_update': False})
            vbos['vao'] = glGenVertexArrays(1)

        glBindVertexArray(vbos['vao'])
        if vbos['v'] is None or vbos['v'].need_update:
            xyz = np.hstack((path[0], path[1], path[2])).reshape(3, -1)
            xyz = np.transpose(xyz).flatten()
            xyz = np.array(xyz, dtype=np.float32)
            norms = path[3].astype(np.float32).flatten()
            uv = ((0, 0), (0, 1), (1, 1), (1, 0))
            uv = np.hstack(uv).astype(np.float32).flatten()
            if vbos['v'] is None:
                vbos['v'] = get_vbo(xyz, usage='GL_STATIC_DRAW')
            else:
                vbos['v'].set_array(xyz)
            if vbos['n'] is None:
                vbos['n'] = get_vbo(norms, usage='GL_STATIC_DRAW')
            else:
                vbos['n'].set_array(norms)
            if vbos['uv'] is None:
                vbos['uv'] = get_vbo(uv, usage='GL_STATIC_DRAW')
            vbos['count'] = 4
            vbos['v'].need_update = False
        if vbos['im'] is None or vbos['im_update']:
            if interp == 'linear':
                mode = GL_LINEAR
            else:
                mode = GL_NEAREST

            h, w, void = im.shape
            image_tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, image_tex)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, mode)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, mode)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                         w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                         im)
            glBindTexture(GL_TEXTURE_2D, 0)
            vbos['im'] = image_tex
            vbos['im_update'] = False
        glBindVertexArray(0)
        return vbos

    def draw_markers(self, vbos, gc, marker_path, marker_trans, path,
                     trans, rgbFace=None, array_idx=None):

        marker_size = marker_trans[0]
        h, w, void = marker_path.shape
        # this should not be necessary, but some linux box need this.
        self.select_shader(self.lshader)
        self.select_shader(self.shader)
        glBindVertexArray(vbos['vao'])

        marker_tex = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0 + 0)
        glBindTexture(GL_TEXTURE_2D, marker_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     marker_path)
        dprint2('marker texture unit : ' + str(marker_tex))
        self.set_uniform(glUniform1i, 'uMarkerTex', 0)

        self.EnableVertex(vbos)

        # if rgbFace is None:
        #   self.setSolidColor(gc._rgb)
        # else:
        #   self.setSolidColor(rgbFace)

        if self._wireframe == 2:
            glDisable(GL_DEPTH_TEST)
        self.set_uniform(glUniform1i, 'uisMarker', 1)
        self.setLineWidth(1)
        
        if self.has_pointsprite:
            glEnable(GL_PROGRAM_POINT_SIZE)
            glEnable(GL_POINT_SPRITE)
        #
        #glPointParameterf(GL_POINT_SIZE_MAX, 50.)
        #glPointParameterf(GL_POINT_SIZE_MIN, 5.)
        #glPointParameterf(GL_POINT_FADE_THRESHOLD_SIZE, 50.)
        glPointSize(marker_size * 2 * multisample + 1)

        self.set_uniform(glUniform1i, 'uAlphaTest', 1)
        self.set_uniform(glUniform1f, 'uAlphaLimit', 0.5)
        self.set_view_offset()

        vertex_id = vbos['vertex_id']
        vertex_id.bind()
        self.VertexAttribPointer('vertex_id', 1, GL_FLOAT, GL_FALSE,
                                 0, None)
        vertex_id.unbind()
        self.set_uniform(glUniform1i, 'uUseArrayID', 1)
        self.EnableVertexAttrib('vertex_id')

        glDepthFunc(GL_LEQUAL)

        glDrawArrays(GL_POINTS, 0, vbos['count'])
        #glDrawArrays(GL_LINES,  0, vbos['count'])
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0., 0.))
        self.set_uniform(glUniform1i, 'uAlphaTest', 0)

        if self.has_pointsprite:
            glDisable(GL_PROGRAM_POINT_SIZE)            
            glDisable(GL_POINT_SPRITE)        

        self.set_uniform(glUniform1i, 'uisMarker', 0)
        self.set_uniform(glUniform1i, 'uUseArrayID', 0)
        if self._wireframe == 2:
            self.set_depth_test()

        glDeleteTextures(marker_tex)
        self.DisableVertexAttrib('inVertex')
        self.DisableVertexAttrib('vertex_id')
        self.setSolidColor(-1)
        glBindVertexArray(0)

    def makevbo_markers(self, vbos, gc, marker_path, maker_trans,
                        path, *args, **kwargs):

        vbos = self.makevbo_path(vbos, gc,
                                 (np.array(path[0]).flatten(),
                                  np.array(path[1]).flatten(),
                                  np.array(path[2]).flatten()),
                                 *args, **kwargs)
        array_idx = kwargs.pop("array_idx", None)
        l = np.array(path[0]).flatten().shape[0]
        if array_idx is not None:
            array_idx = np.array(array_idx, copy=False).flatten()
            if array_idx.shape[0] != l:
                assert False, "array_idx length should be the same as the number of elements"
        else:
            array_idx = np.arange(l)
        vertex_id = np.array(array_idx, dtype=np.float32,
                             copy=False).transpose().flatten()
        vbos['vertex_id'] = get_vbo(vertex_id,
                                    usage='GL_STATIC_DRAW')
        return vbos

    def draw_path_collection(self, vbos, gc, paths,
                             facecolor, edgecolor,
                             linewidth, linestyle, offset,
                             stencil_test=False,
                             lighting=True,
                             view_offset=(0, 0, 0, 0),
                             array_idx=None,
                             always_noclip=False):

        if vbos is None:
            return
        first = vbos['first']
        counts = vbos['counts']
        if vbos['fc'] is not None:
            if stencil_test:
                for f, c in zip(first, counts):
                    self.draw_polygon(vbos, gc, f, c)
            else:
                self.select_shader(self.shader)
                glBindVertexArray(vbos['vao'])

                self.EnableVertex(vbos)
                self.EnableNormal(vbos)
                self.EnableFaceColor(vbos)

                self.set_uniform(glUniform1i, 'uUseArrayID', 0)
                self.set_uniform(glUniform4fv, 'uWorldOffset', 1, offset)
                self.set_uniform(glUniform4fv, 'uViewOffset', 1, view_offset)

                # I don't remember why I needed this...
                # if not lighting and self._p_shader is self.shader:
                #    ambient, light, specular, shadowmap, clip1, clip2 = self.set_lighting_off()
                if not self._shadow:
                    self.set_view_offset(offset_base=view_offset)
                if self._wireframe == 2:
                    glDisable(GL_DEPTH_TEST)
                #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                # if use_multdrawarrays:
                glMultiDrawArrays(GL_TRIANGLE_FAN, first, counts,
                                  len(counts))
                # else:
                #glDrawArrays(GL_LINE_STRIP, 0, vbos['counts'])
                #glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                if self._wireframe == 2:
                    self.set_depth_test()

                self.DisableVertex(vbos)
                self.DisableNormal(vbos)
                self.DisableFaceColor(vbos)
                self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                                 (0, 0, 0., 0.))
                self.set_uniform(glUniform4fv, 'uWorldOffset',
                                 1, (0, 0, 0, 0.))
                glBindVertexArray(0)

        if linewidth[0] == 0.0:
            return

        self.select_shader(self.lshader)
        glBindVertexArray(vbos['vao'])

        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        self.EnableEdgeColor(vbos)

        self.set_uniform(glUniform1i, 'uUseArrayID', 0)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, offset)
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, view_offset)

        # I don't remember why I needed this...
        # if not lighting and self._p_shader is self.shader:
        #    ambient, light, specular, shadowmap, clip1, clip2 = self.set_lighting_off()
        if linewidth[0] > 0.0 and not self._shadow:
            self.setLineWidth(linewidth[0] * multisample)

            glDepthFunc(GL_LEQUAL)

            if not self._shadow:
                self.set_view_offset(offset_base=view_offset)
            if self._wireframe == 2:
                glDisable(GL_DEPTH_TEST)
            #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            # if use_multdrawarrays:
            glMultiDrawArrays(GL_LINE_STRIP, first, counts,
                              len(counts))
            # else:
            #glDrawArrays(GL_LINE_STRIP, 0, vbos['counts'])
            #glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            if self._wireframe == 2:
                self.set_depth_test()
            glDepthFunc(GL_LESS)

        self.DisableVertex(vbos)
        self.DisableNormal(vbos)
        self.DisableEdgeColor(vbos)
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0., 0.))
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0, 0.))

        glBindVertexArray(0)
        self.select_shader(self.shader)

    def makevbo_path_collection(self, vbos, gc, paths, facecolor,
                                edgecolor, *args, **kwargs):
        if vbos is None:
            vbos = {'v': None, 'n': None, 'fc': None,
                    'ec': None, 'first': None, 'counts': None}
            vbos['vao'] = glGenVertexArrays(1)
        glBindVertexArray(vbos['vao'])

        from matplotlib.path import Path
        # print 'draw_path_collection', len(facecolor)

        if vbos['v'] is None or vbos['v'].need_update:
            xyzs = np.transpose(np.vstack((paths[0],
                                           paths[1],
                                           paths[2])))

            xyzs = xyzs.flatten().astype(np.float32)
            norms = paths[3].astype(np.float32).flatten()
            counts = np.array([len(x) for x in paths[4]])
            first = np.array(counts).cumsum()
            first = list(np.hstack((np.array([0]), first[:-1])))

            if vbos['v'] is None:
                vbos['v'] = get_vbo(xyzs, usage='GL_STATIC_DRAW')
                vbos['n'] = get_vbo(norms, usage='GL_STATIC_DRAW')
            else:
                vbos['v'].set_array(xyzs)
                vbos['n'].set_array(norms)
            vbos['first'] = first
            vbos['counts'] = counts
            vbos['n'].need_update = False
            vbos['v'].need_update = False
        if ((vbos['fc'] is None or vbos['fc'].need_update) and
                facecolor is not None):
            counts = vbos['counts']
            if len(facecolor) == 0:
                facecolor = np.array([[1, 1, 1, 0]])
            if len(facecolor) == len(counts):
                col = [list(f) * c for f, c in zip(facecolor, counts)]
            else:
                col = [facecolor] * np.sum(counts)
            col = np.hstack(col).astype(np.float32)
            if vbos['fc'] is None:
                vbos['fc'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['fc'].set_array(col)
            vbos['fc'].need_update = False
        if vbos['ec'] is None or vbos['ec'].need_update:
            counts = vbos['counts']
            if len(edgecolor) == 0:
                edgecolor = np.array([[1, 1, 1, 0]])
            if len(edgecolor) == np.sum(counts):
                col = edgecolor
            else:
                #print(edgecolor.shape, counts)
                assert False, "edge color length is wrong"
            col = np.hstack(col).astype(np.float32)
            if vbos['ec'] is None:
                vbos['ec'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['ec'].set_array(col)
            vbos['ec'].need_update = False
        glBindVertexArray(0)
        return vbos

    def draw_path_collection_e(self, vbos, gc, paths,
                               facecolor, edgecolor,
                               linewidth, linestyle, offset,
                               stencil_test=False,
                               lighting=True,
                               view_offset=(0, 0, 0, 0),
                               array_idx=None,
                               use_pointfill=True,
                               always_noclip=False,
                               edge_idx=None):
        if vbos is None:
            return

        if len(paths[4][0]) > 4:
            self.draw_path_collection(vbos, gc, paths,
                                      facecolor, edgecolor,
                                      linewidth, linestyle, offset,
                                      stencil_test=stencil_test,
                                      lighting=lighting,
                                      view_offset=view_offset,
                                      array_idx=array_idx)
            if self._use_clip and always_noclip:
                self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)

            return
        nindex, nindexe, counts = vbos['nindex'], vbos['nindexe'], vbos['counts']

        if always_noclip:
            self.set_uniform(glUniform1i, 'uUseClip', 0)

        if facecolor is not None and vbos['primitive'] is not None:
            glBindVertexArray(vbos['vao'])
            vbos['i'].bind()
            self.EnableVertex(vbos)
            self.EnableNormal(vbos)
            self.EnableVertexID(vbos)

            offset = list(offset) + [0]
            self.set_uniform(glUniform4fv, 'uWorldOffset', 1, offset)
            self.set_uniform(glUniform4fv, 'uViewOffset', 1, view_offset)

            # if not lighting and self._p_shader is self.shader:
            #    ambient, light, specular, shadowmap, clip1, clip2 = self.set_lighting_off()

            self.EnableFaceColor(vbos)
            if self._wireframe != 2:
                if self._wireframe == 1:
                    glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
                check_gl_error()
                if use_pointfill:
                    # pointfill will fill voids when area is filled with a
                    # lot of very small triangles...
                    # maybe usefull for a high resolution 2D simulaiton plot
                    self.set_uniform(
                        glUniform4fv, 'uViewOffset', 1, (0, 0, +0.005, 0))
                    glEnable(GL_PROGRAM_POINT_SIZE)
                    #glDrawElements(GL_POINTS, nindex, GL_UNSIGNED_INT, None)
                    glDisable(GL_PROGRAM_POINT_SIZE)
                    self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                                     (0, 0, 0., 0.))
                glDrawElements(vbos['primitive'], nindex,
                               GL_UNSIGNED_INT, None)
                if self._wireframe == 1:
                    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
            vbos['fc'].unbind()
            self.DisableVertexAttrib('inColor')
            self.DisableVertexAttrib('inVertex')
            vbos['v'].unbind()
            if vbos['n'] is not None:
                self.DisableVertexAttrib('inNormal')
                vbos['n'].unbind()
            if vbos['vertex_id'] is not None:
                self.DisableVertexAttrib('vertex_id')
                vbos['vertex_id'].unbind()
            glBindVertexArray(0)
            self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0, 0.))
            vbos['i'].unbind()

        # if not(linewidth[0] > 0.0 and not self._shadow): return
        if self._shadow:
            if self._use_clip and always_noclip:
                self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)
            return

        if vbos['primitive'] is not None:
            if linewidth[0] == 0.0:
                if self._use_clip and always_noclip:
                    self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)
                return
        
        if vbos['eprimitive'] == GL_TRIANGLES:
            self.select_shader(self.tshader)
        else:
            self.select_shader(self.lshader)

        glBindVertexArray(vbos['vao'])
        if vbos['ie'] is not None:
            vbos['ie'].bind()
        else:
            vbos['i'].bind()

        self.EnableVertex(vbos)
        self.EnableNormal(vbos)
        self.EnableVertexID(vbos)

        offset = list(offset) + [0]
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, offset)
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, view_offset)

        self.setLineWidth(linewidth[0] * multisample)

        # Line draw is done using facecolor.
        if vbos['primitive'] is not None:
            self.EnableEdgeColor(vbos)
        else:
            if linewidth[0] == 0.0:
                self.EnableEdgeColor(vbos)
                self.setLineWidth(1.0 * multisample)
            else:
                self.EnableFaceColor(vbos)
        glDepthFunc(GL_LEQUAL)

        if not self._shadow:
            self.set_view_offset(offset_base=view_offset)
        if self._wireframe == 2:
            glDisable(GL_DEPTH_TEST)
        # glDepthMask(GL_FALSE)
        #glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        # self.set_uniform(glUniform4fv, 'uViewOffset', 1,
        #                 (0, 0, -0.01, 0.))

        glDrawElements(vbos['eprimitive'], nindexe,
                       GL_UNSIGNED_INT, None)
        # self.set_depth_mask()
        if self._wireframe == 2:
            self.set_depth_test()
        #glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        if self._wireframe == 2:
            self.set_depth_test()
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0., 0.))

        if vbos['primitive'] is not None:
            vbos['ec'].unbind()
        else:
            if linewidth[0] == 0.0:
                vbos['ec'].unbind()
            else:
                vbos['fc'].unbind()

        self.DisableVertexAttrib('inColor')

        glDepthFunc(GL_LESS)
        if vbos['ie'] is not None:
            vbos['ie'].unbind()
        else:
            vbos['i'].unbind()

        self.DisableVertexAttrib('inVertex')
        vbos['v'].unbind()
        if vbos['n'] is not None:
            self.DisableVertexAttrib('inNormal')
            vbos['n'].unbind()
        if vbos['vertex_id'] is not None:
            self.DisableVertexAttrib('vertex_id')
            vbos['vertex_id'].unbind()
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0, 0.))

        glBindVertexArray(0)
        self.select_shader(self.shader)

        if self._use_clip and always_noclip:
            self.set_uniform(glUniform1i, 'uUseClip', self._use_clip)

    def makevbo_path_collection_e(self, vbos, gc, paths, facecolor,
                                  edgecolor, *args, **kwargs):
        ### paths is [X, Y, Z, norms, idxset]
        if len(paths[4]) == 0:
            return None
        if len(paths[4][0]) > 4:
            vbos = self.makevbo_path_collection(vbos, gc, paths, facecolor,
                                                edgecolor, *args, **kwargs)
            return vbos

        if vbos is None:
            vbos = {
                'vao': None,
                'v': None,
                'n': None,
                'i': None,
                'fc': None,
                'ec': None,
                'counts': None,
                'nindexe': None,
                'nindex': None,
                'vertex_id': None,
                'ie': None,
                'primitve': None,
                'eprimitive': None}
            vbos['vao'] = glGenVertexArrays(1)
        glBindVertexArray(vbos['vao'])

        array_idx = kwargs.pop('array_idx', None)
        edge_idx = kwargs.pop('edge_idx', None)

        # make indexset when it is needed
        # index set is changed to uint32 instead of uint16 (2016 06 28)
        if ((vbos['v'] is None or vbos['v'].need_update) or
            (vbos['i'] is None or vbos['i'].need_update) or
            ((vbos['fc'] is None or vbos['fc'].need_update) and
             facecolor is not None) or
                (vbos['ec'] is None or vbos['ec'].need_update)):

            idxset0 = np.array(
                paths[4],
                copy=False).astype(
                np.uint32,
                copy=False).flatten()
            if edge_idx is not None:
                edge_idx = np.array(
                    edge_idx, copy=False).astype(
                    np.uint32, copy=False).flatten()

            if len(paths[4][0]) == 4:
                idxset0 = idxset0.reshape(-1, 4)
                idxset = idxset0[:, [0, 1, 2, 2, 3, 0]].flatten()
                if edge_idx is not None:
                    idxsete = edge_idx
                else:
                    idxsete = idxset
            elif len(paths[4][0]) == 3:
                idxset = idxset0
                if edge_idx is not None:
                    idxsete = edge_idx
                else:
                    idxset0 = idxset0.reshape(-1, 3)
                    idxsete = idxset0[:, [0, 1, 2, 1, 2, 0]].flatten()
            elif len(paths[4][0]) == 2:
                idxset = idxset0
                idxsete = None
            else:
                assert False, "Unsupported element shape"

        if len(paths[4][0]) == 4:
            counts = 3
            nindex = len(paths[4]) * 6
            nindexe = len(paths[4]) * \
                6 if edge_idx is None else len(edge_idx) * 2
            primitive = GL_TRIANGLES
            eprimitive = GL_TRIANGLES if edge_idx is None else GL_LINES
        elif len(paths[4][0]) == 3:
            counts = 3
            nindex = len(paths[4]) * 3
            nindexe = len(paths[4]) * \
                6 if edge_idx is None else len(edge_idx) * 2
            primitive = GL_TRIANGLES
            eprimitive = GL_TRIANGLES if edge_idx is None else GL_LINES
        elif len(paths[4][0]) == 2:
            counts = 2
            nindex = len(paths[4]) * 2
            nindexe = len(paths[4]) * 2
            primitive = None
            eprimitive = GL_LINES
        else:
            assert False, "Unsupported element shape"

        nverts = len(paths[0])
        vbos['nindex'] = nindex
        vbos['nindexe'] = nindexe
        vbos['counts'] = counts
        vbos['primitive'] = primitive
        vbos['eprimitive'] = eprimitive

        if vbos['v'] is None or vbos['v'].need_update:
            xyzs = np.transpose(np.vstack((paths[0],
                                           paths[1],
                                           paths[2])))
            xyzs = xyzs.flatten().astype(np.float32)
            if paths[3] is None:
                norms = None
            elif len(paths[3]) == len(paths[0]):
                # norm is already specified for each vetex
                norms = paths[3].astype(np.float32, copy=False).flatten()
            elif len(paths[3]) == 1:
                # norm is common (flat surface)
                norms = [paths[3]] * nverts
                norms = np.hstack(norms).astype(
                    np.float32, copy=False).flatten()
            else:
                norms = paths[3].astype(np.float32, copy=False).flatten()

            if vbos['v'] is None:
                vbos['v'] = get_vbo(xyzs, usage='GL_DYNAMIC_DRAW')
                if norms is not None:
                    vbos['n'] = get_vbo(norms, usage='GL_DYNAMIC_DRAW')
                vbos['i'] = get_vbo(idxset, usage='GL_DYNAMIC_DRAW',
                                    target='GL_ELEMENT_ARRAY_BUFFER')
                if idxsete is not None:
                    vbos['ie'] = get_vbo(idxsete, usage='GL_DYNAMIC_DRAW',
                                         target='GL_ELEMENT_ARRAY_BUFFER')
                else:
                    vbos['ie'] = None
            else:
                vbos['v'].set_array(xyzs)
                if norms is not None:
                    vbos['n'].set_array(norms)
                else:
                    vbos['n'] = None
                if idxsete is not None:
                    vbos['ie'].set_array(idxsete)
                else:
                    vbos['ie'] = None

            vbos['v'].need_update = False
            if vbos['n'] is not None:
                vbos['n'].need_update = False
            if vbos['vertex_id'] is not None:
                vbos['vertex_id'].need_update = True
            vbos['i'].need_update = False

        if vbos['i'].need_update:
            if len(vbos['i']) > len(idxset):
                # we need  not to change the size of i ...!?
                data = np.zeros(len(vbos['i']), np.uint32)
                data = data.reshape(-1, len(paths[4][0]))
                idxset0 = idxset.reshape(-1, len(paths[4][0]))
                data[:len(idxset0), :] = idxset0
                data = data.flatten()
                vbos['i'].set_array(data)
            else:
                vbos['i'].set_array(idxset)

            vbos['counts'] = len(paths[4][0])
            vbos['i'].need_update = False

            if idxsete is not None:
                vbos['ie'].set_array(idxsete)
            else:
                vbos['ie'] = None

        if ((vbos['fc'] is None or vbos['fc'].need_update) and
                facecolor is not None):
            counts = vbos['counts']
            #print('facecolor', facecolor.shape, paths[0].shape, len(paths[4]))
            if len(facecolor) == 0:
                facecolor = np.array([[1, 1, 1, 0]])
            if facecolor.ndim == 3:
                # non index array/linear
                col = [facecolor]
                col = np.hstack(col).astype(np.float32)
            elif facecolor.ndim == 2 and len(paths[0]) == len(facecolor):
                # index array/linear
                col = [facecolor]
                col = np.hstack(col).astype(np.float32)
            elif len(facecolor)*paths[4].shape[1]  == len(paths[0]):
                # non index array/flat
                c = paths[4].shape[1]
                col = np.array(facecolor, copy=False).astype(
                    np.float32, copy=False)
                col = np.hstack([col] * c)
            else:
                col = np.repeat(np.array(facecolor).astype(np.float32),
                                nindex * counts)
            if vbos['fc'] is None:
                vbos['fc'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['fc'].set_array(col)

            vbos['fc'].need_update = False

        if vbos['ec'] is None or vbos['ec'].need_update:
            counts = vbos['counts']
            if len(edgecolor) == 0:
                edgecolor = np.array([[1, 1, 1, 0]]).astype(np.float32)
            if len(edgecolor) == len(paths[0]):
                col = np.array(edgecolor, copy=False).astype(
                    np.float32, copy=False)
            else:
                col = np.repeat(np.array(edgecolor).astype(np.float32),
                                nindex * counts)
            #col = np.hstack(col).astype(np.float32, copy = False)
            if vbos['ec'] is None:
                vbos['ec'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['ec'].set_array(col)
            vbos['ec'].need_update = False
        if vbos['vertex_id'] is None or vbos['vertex_id'].need_update:
            counts = vbos['counts']
            l = nindex // counts   # number of faces
            nverts = len(paths[0])

            if array_idx is not None:
                array_idx = np.array(array_idx, copy=False).flatten()

                if array_idx.shape[0] == nverts:
                    pass
                elif array_idx.shape[0] == l:
                    array_idx = [array_idx] * counts
                else:
                    assert False, "array_idx length should be the same as the number of vertex:" + str(array_idx.shape) + " : "  + str(nverts) + " : " + str(l)
                vertex_id = np.array(array_idx,
                                     dtype=np.float32,
                                     copy=False).transpose().flatten()
                
                if vbos['vertex_id'] is None:
                    vbos['vertex_id'] = get_vbo(vertex_id,
                                                usage='GL_STATIC_DRAW')
                else:
                    vbos['vertex_id'].set_array(vertex_id)
                vbos['vertex_id'].need_update = False

        glBindVertexArray(0)
        return vbos

    def set_view_offset(self, offset_base=(0, 0, 0., 0)):
        # depth 32bit, clipping, camera = (45, 50)
        offset = tuple(np.array(offset_base) + np.array((0, 0, -0.0001, 0.)))
        # offset = tuple(np.array(offset_base) + np.array((0, 0, -0.0005, 0.)))
        # # depth 24bit, clipping, camera = (9, 10)

        if self._use_frustum:
            self.set_uniform(glUniform4fv, 'uViewOffset', 1, offset)
        else:
            self.set_uniform(glUniform4fv, 'uViewOffset', 1, offset)

    def has_vbo_data(self, artist):
        tag = self.get_container(artist)
        if tag not in self.vbo:
            return False
        return artist in self.vbo[tag]

    def get_vbo_data(self, artist):
        tag = self.get_container(artist)
        if tag not in self.vbo:
            return None
        if artist in self.vbo[tag]:
            return self.vbo[tag][artist]
        return None

    def store_artists(self, artists):
        for a in artists:
            if a not in self.artists:
                self.artists.append(a)
                self._do_draw_mpl_artists = True

    def store_draw_request(self, name, *data, **kwargs):
        tag = self.get_container(self._draw_request)
        dd = (name, data, kwargs)
        self.artists_data[tag][self._draw_request].append(dd)
        self._do_draw_mpl_artists = True

#    def set_proj(self, *args):
#        self.M = args

    def get_container(self, obj):
        if obj.axes is not None:
            return obj.axes
        elif obj.figure is not None:
            return obj.figure
        return None

    def frame_request(self, a, trans):
        globals()['multisample_init_done'] = True
        s = wx.GetApp().TopWindow.appearanceconfig.setting
        if s['gl_multisample']:
            globals()['multisample'] = 2
        else:
            globals()['multisample'] = 1
        from .art3d_gl import frame_range
        target = self.get_container(a)
        box = trans.transform([frame_range[0:2], frame_range[2:4]])
        d = box[1] - box[0]
        w, h = int(d[0]) * multisample, int(d[1]) * multisample
        make_new = False

        if target in self.frame_list:
            w2, h2, m2, frames, bufs, stc, texs = self.frame_list[target]
            if w2 != w or h2 != h or m2 != multisample:
                glDeleteTextures(texs)
                glBindFramebuffer(GL_FRAMEBUFFER, 0)
                glBindRenderbuffer(GL_RENDERBUFFER, 0)

                glDeleteFramebuffers(len(frames), frames)
                glDeleteRenderbuffers(len(bufs), bufs)
                del self.frame_list[target]
                for f in frames:
                    self.frames.remove(f)
                make_new = True
        else:
            make_new = True
        if make_new:
            # print 'makeing new frame', w, h
            frame, buf, stc, dtex = self.get_newframe(w, h)
            if frame is not None:
                self.frame_list[target] = (w, h, multisample, frame,
                                           buf, stc, dtex)

    def OnDraw(self):
        if self._do_draw_mpl_artists:
            pass
#            self.get_newframe()
#            self.draw_mpl_artists()

#         glBindFramebuffer(GL_FRAMEBUFFER, 0)
 #        self.SwapBuffers()

        #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
