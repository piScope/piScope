# uncomment the following to use wx rather than wxagg
import matplotlib
import wx, weakref, array
from matplotlib.backends.backend_wx import FigureCanvasWx as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as CanvasAgg
from matplotlib.backends.backend_wx import RendererWx
from ifigure.utils.cbook import EraseBitMap 
from operator import itemgetter

import numpy as np
import time, ctypes


import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('BackendWXAggGL')

from distutils.version import LooseVersion
from ifigure.matplotlib_mod.backend_wxagg_mod import FigureCanvasWxAggMod
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

near_clipping = 8

import os
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

def check_framebuffer(message):
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) !=
        GL_FRAMEBUFFER_COMPLETE):
         print('Framebuffer imcomplete (' + message + ')')
         print(str(glCheckFramebufferStatus(GL_FRAMEBUFFER)))
         print(str(GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT))
         print(str(GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS))
         print(str(GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT))
         print(str(GL_FRAMEBUFFER_UNSUPPORTED))
         return False
    return True
class vbos_dict(dict):
    def __del__(self, *args, **kwargs):
       if 'im' in self:
           if self['im'] is not None:
                dprint2('deleteing texture', self['im'])
                glDeleteTextures(self['im'])
                self['im'] = None
       return 
    
class MyGLCanvas(glcanvas.GLCanvas):
    offscreen = True
    context = None
    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        if MyGLCanvas.context is None:
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
#        self.gc = weakref.WeakKeyDictionary()
        self._do_draw_mpl_artists = False
        self._draw_request = None
        self._no_clean = False
        self._artist_mask = None
        self._use_shadow_map = True
        self._use_clip = True
        self._use_frustum = True        
        self._attrib_loc = {}
        self._hittest_map_update = True
        self._alpha_blend = True
        self._wireframe = 0 # 1: wireframe + hidden line elimination 2: wireframe
        if MyGLCanvas.offscreen: 
            self.SetSize((2,2))
            self.SetMaxSize((2,2))
            self.SetMinSize((2,2))

    def gc_artist_data(self):
        keys = self.artists_data.keys()
        for aa in keys:
            if aa.figobj is None:
               del self.artists_data[aa]
               del self.vbo[aa]               
            else:
               keys2 = self.artists_data[aa].keys()  
               for a in keys2:
                  if hasattr(a, 'figobj') and a.figobj is None:
                      del self.artists_data[aa][a]
                      del self.vbo[aa][a]                      
    def set_uniform(self, func, name, *args, **kwargs):
        loc = self._p_uniform_loc[name]       
        func(loc, *args, **kwargs)

    def select_shader(self, shader):
        glUseProgram(shader)
        if not hasattr(shader, 'uniform_loc'):
            shader.uniform_loc= {}
        self._p_uniform_loc = shader.uniform_loc
        self._p_shader = shader

    def __del__(self):
        if len(self.frames) > 0: glDeleteFramebuffers(len(frames), self.frames)
        if len(self.bufs) > 0: glDeleteRenderbuffers(len(bufs), self.bufs)

    def start_draw_request(self, artist):
        self._draw_request = artist
        tag = self.get_container(artist)
        if not tag in self.artists_data:
            self.artists_data[tag] = weakref.WeakKeyDictionary()
        self.artists_data[tag][artist] = []

    def end_draw_request(self):
        self._draw_request = None

    def InitGL(self):
        from OpenGL.GL import shaders

        # compile shader and set uniform variables
        # set viewing projection


        fs = compile_file('depthmap.frag', GL_FRAGMENT_SHADER)
        vs = compile_file('depthmap.vert', GL_VERTEX_SHADER)
        self.dshader = shaders.compileProgram(vs, fs)
        self.select_shader(self.dshader)

        names = ['uWorldM', 'uViewM', 'uProjM', 
                 'uWorldOffset', 'uViewOffset',
                 'uArtistID', 'uClipLimit1',
                 'uClipLimit2',
                 'uisMarker', 'uMarkerTex', 'uisImage', 'uImageTex',
                 'uUseClip', 'uHasHL']
        for name in names:  define_unform(self.dshader, name)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform1i,  'uisMarker', 0)
        self.set_uniform(glUniform1i,  'uisImage', 0)
        self.set_uniform(glUniform1i,  'uUseClip', 1)
        self.set_uniform(glUniform1i,  'uHasHL', 0)                
        self.set_uniform(glUniform3fv, 'uClipLimit1', 1, (0, 0, 0))
        self.set_uniform(glUniform3fv, 'uClipLimit2', 1, (1, 1, 1))        
        
        fs = compile_file('simple.frag', GL_FRAGMENT_SHADER)
        vs = compile_file('simple.vert', GL_VERTEX_SHADER)
        self.shader = shaders.compileProgram(vs, fs)
        print(glGetProgramInfoLog(self.shader))
        self.select_shader(self.shader)

#        names = names + ['uAmbient', 'uLightDir', 'uLightColor',
        names = names + ['uLightDir', 'uLightColor',                         
                         'uLightPow', 'uLightPowSpec',
                         'uMaxAlpha',  'uShadowM',
                         'uShadowMaxZ', 'uShadowMinZ',
                         'uShadowTex', 'uUseShadowMap',
                         'uShadowTexSize', 'uShadowTex2',
                         'uStyleTex', 'uisAtlas', 'uAtlasParam',
                         'uLineStyle', 'uAmbient']
        for name in names:  define_unform(self.shader, name)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, (0, 0, 0., 0))
        self.set_uniform(glUniform1i,  'uisMarker', 0)
        self.set_uniform(glUniform1i,  'uisImage', 0)
        self.set_uniform(glUniform1i,  'uisAtlas', 0)
        self.set_uniform(glUniform1i,  'uUseClip', 1)
        self.set_uniform(glUniform1i,  'uHasHL', 0)                        
        self.set_uniform(glUniform1i,  'uLineStyle', -1)        
        self._attrib_loc['Vertex2'] = glGetAttribLocation(self.shader,
                                                          "Vertex2")
        self._attrib_loc['vertex_id'] = glGetAttribLocation(self.shader,
                                                            "vertex_id")
        self.set_lighting()

    def EnableVertexAttrib(self, name):
        glEnableVertexAttribArray(self._attrib_loc[name])
    def DisableVertexAttrib(self, name):
        glDisableVertexAttribArray(self._attrib_loc[name])
    def VertexAttribPointer(self, name, *args):
        glVertexAttribPointer(self._attrib_loc[name], *args)

    def set_lighting(self, ambient = 0.5, light_direction = (1, 0, 1., 0),
                           light = 1.0, 
                           specular = 1.5, light_color = (1.0, 1.0, 1.0),
                           wireframe = 0,
                           clip_limit1 = [0, 0, 0],
                           clip_limit2 = [1, 1, 1], shadowmap = True):
        if not self.init: return
        #print('set_lighting', light)
        glUniform4fv(self.shader.uniform_loc['uAmbient'], 1,
                          (ambient, ambient, ambient, 1.0))

        glUniform4fv(self.shader.uniform_loc['uLightDir'], 1, light_direction)
        glUniform3fv(self.shader.uniform_loc['uLightColor'], 1, light_color)
        glUniform1f(self.shader.uniform_loc['uLightPow'], light)
        glUniform1f(self.shader.uniform_loc['uLightPowSpec'], specular)
        glUniform3fv(self.shader.uniform_loc['uClipLimit1'], 1, clip_limit1)
        glUniform3fv(self.shader.uniform_loc['uClipLimit2'], 1, clip_limit2)

        self._wireframe = wireframe
        self._light_direction = light_direction
        self._use_shadow_map = shadowmap
        #print 'light power', self.shader, light
        
    def set_lighting_off(self):
        #print('set_lighting_off')
        a = (GLfloat * 4)()
        b = (GLfloat * 1)()
        c= (GLfloat * 1)()
        d = self._use_shadow_map
        glGetUniformfv(self.shader, self.shader.uniform_loc['uAmbient'], a)
        glGetUniformfv(self.shader, self.shader.uniform_loc['uLightPow'], b)
        glGetUniformfv(self.shader, self.shader.uniform_loc['uLightPowSpec'], c)
        
        clip1= (GLfloat * 3)()
        clip2= (GLfloat * 3)()        
        glGetUniformfv(self.shader, self.shader.uniform_loc['uClipLimit1'], clip1)
        glGetUniformfv(self.shader, self.shader.uniform_loc['uClipLimit2'], clip2)
        
        glUniform4fv(self.shader.uniform_loc['uAmbient'], 1,
                          (1.0, 1.0, 1.0, 1.0))
        glUniform1f(self.shader.uniform_loc['uLightPow'], 0.0)
        glUniform1f(self.shader.uniform_loc['uLightPowSpec'], 0.0)
        self._use_shadow_map = False

        return list(a)[0], list(b)[0], list(c)[0], d, clip1, clip2

    def OnPaint(self, event):
        #print  self._do_draw_mpl_artists
        dc = wx.PaintDC(self)
        self.SetCurrent(MyGLCanvas.context)
#        fbo = glGenRenderbuffers(1)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnSize(self, event):
        if MyGLCanvas.offscreen and self.GetSize()[0] > 2:
            self.SetSize((2,2))
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        if MyGLCanvas.offscreen: return
        size = self.size = self.GetClientSize()
        self.SetCurrent(self.context)
        glViewport(0, 0, size.width, size.height)

    def del_frame(self):
        glDeleteFramebuffers(len(self.frames), self.frames)
        glDeleteRenderbuffers(len(self.bufs), self.bufs)
        self.frames = []
        self.bufs = []

    def get_newframe(self, w, h):
#        if (self._frame_w == self._frame_w_req and
#            self._frame_h == self._frame_h_req): return
#        print('getting new frame')
#        if len(self.frames) != 0:
#             self.del_frame()
        frame = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, frame)

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 
                     w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        tex2 = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex2)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
#        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 
#                     w, h, 0, GL_RED, GL_UNSIGNED_BYTE, None)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                     w, h, 0, GL_RGBA, GL_FLOAT, None)
        dtex =  glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, dtex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                        GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                        GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8,
                     w, h, 0,GL_RGBA, GL_UNSIGNED_BYTE, None)


        glBindTexture(GL_TEXTURE_2D, 0)

#        dtex = None
#        glDrawBuffer(GL_NONE); // No color buffer is drawn to.
         
        buf = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, buf)
        glRenderbufferStorage(GL_RENDERBUFFER,
                              GL_DEPTH24_STENCIL8,
                              w, h)
        #glFramebufferRenderbuffer(GL_FRAMEBUFFER, 
        #                          GL_DEPTH_ATTACHMENT, 
        #                          GL_RENDERBUFFER, buf)
        dbuf = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, dbuf)
        glRenderbufferStorage(GL_RENDERBUFFER,
                              GL_DEPTH24_STENCIL8,
                              w, h)
        glBindRenderbuffer(GL_RENDERBUFFER, 0)        

        '''
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, 
                                  GL_STENCIL_ATTACHMENT, 
                                  GL_RENDERBUFFER, buf)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT0, 
                               GL_TEXTURE_2D, tex, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT1, 
                               GL_TEXTURE_2D, tex2, 0)
        '''
#        if not check_framebuffer('creating new frame buffer'): return [None]*4

#        glBindTexture(GL_TEXTURE_2D, 0)
#        glBindRenderbuffer(GL_RENDERBUFFER, 0);
#        glBindFramebuffer(GL_FRAMEBUFFER, 0);

        self.frames.append(frame)
        self.bufs.append(buf)
        #self.stcs.append(buf)
        stc = None
        return frame, [buf, dbuf], stc, [tex, tex2, dtex,]
 
    def get_frame_4_artist(self, a):
        c = self.get_container(a)
        try:
            w, h, frame, buf, stc, dtex = self.frame_list[c]
            return  w, h, frame, buf, stc, dtex
        except:
            return [None]*4

    def force_fill_screen(self):
        # draw a big rectangle covering the entire 3D scene
        # some graphics card (Intel HD) does not do glClear 
        # as it supposed to do.
        # It clears a screen area where 3D object exists. Otherwise
        # the buffer is not untouched...
        # This routine forces to erase entire scene.
        I_M = np.diag([1.0]*4)
        I_MS = np.array([[1.,0., 0., -0.5],
                         [0.,1., 0., -0.5],
                         [0.,0., 1., -0.5],
                         [0.,0., 0., 1.0]])
        self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE, I_M)
        self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE, I_MS)
        self.set_uniform(glUniformMatrix4fv, 'uProjM', 1, GL_TRUE, I_M)
        self.set_uniform(glUniform1i,  'uUseClip', 0)           
        glDisable(GL_BLEND)             
        glColor4f(1., 1, 1,  0)
        glRecti(-1, -1, 2, 2)

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
#        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
#                               GL_TEXTURE_2D, 0, 0);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, texs[0], 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT1, 
                               GL_TEXTURE_2D, texs[1], 0)
        
#        glReadBuffer(GL_NONE)
#        glDepthMask(GL_TRUE)
        if not check_framebuffer('going to depthmap mode'): return

        self.select_shader(self.dshader)        
        #self.force_fill_screen()

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        dist = self.M[-1]

        # viwe range shoud be wide enough to avoid near clipping
        #minZ = dist-1
        #maxZ = dist+1
        minZ = dist-near_clipping
        maxZ = dist+near_clipping
        if self._use_frustum:
#           glFrustum(-1, 1, -1, 1, minZ, maxZ) #this is original (dist = 10, so 9 is adjustment)
           glFrustum(-minZ/9., minZ/9., -minZ/9., minZ/9., minZ, maxZ)           
        else:
            a = (dist+1.)/dist
            glOrtho(-a, a, -a, a, minZ, maxZ)                      

        projM = read_glmatrix(mode = GL_PROJECTION_MATRIX)

        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_NORMALIZE)
        glLoadIdentity()

        glViewport(0, 0, w, h)        

        R = np.array([0.5, 0.5, 0.5])
        d = np.array(self._light_direction)[:3]*3
        E = d/np.sqrt(np.sum(d**2))*self.M[-1] + R
        
        V = np.array((0, 0, 1))
        #zfront, zback = -10, 10
        
        import mpl_toolkits.mplot3d.proj3d as proj3d        
        viewM = proj3d.view_transformation(E, R, V)

        self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE, self.M[0])
        self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE, viewM)
        self.set_uniform(glUniformMatrix4fv, 'uProjM', 1, GL_TRUE, projM)

        M = np.dot(viewM, self.M[0]) #viewM * worldM
        M = np.dot(projM, M) #projM * viewM * worldM        
        #glLoadMatrixf(np.transpose(M).flatten())

        if self._use_clip:
            self.set_uniform(glUniform1i,  'uUseClip', 1)
        else:
            self.set_uniform(glUniform1i,  'uUseClip', 0)           
        
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                          GL_COLOR_ATTACHMENT1])

        if self._alpha_blend:
            glEnable(GL_BLEND);
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        else:
            glDisable(GL_BLEND);                
        self._shadow = True
        
        return (M, minZ, maxZ)
        
    def use_draw_mode(self, frame, buf, texs, w, h, shadow_params = None):
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

        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT0, 
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT1, 
                               GL_TEXTURE_2D, 0, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT0, 
                               GL_TEXTURE_2D, texs[0], 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, 
                               GL_COLOR_ATTACHMENT1, 
                               GL_TEXTURE_2D, texs[1], 0)

        if not check_framebuffer('going to normal mode'): return

        self.select_shader(self.shader)
        #self.InitGL()
        self.set_uniform(glUniform1i, 'uUseShadowMap', 0) 
        self.force_fill_screen()
        if self._use_shadow_map:
            self.set_uniform(glUniform1i, 'uUseShadowMap', 1) 
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        dist = self.M[-1]

        # viwe range shoud be wide enough to avoid near clipping 
        #minZ = dist-1
        #maxZ = dist+1
        minZ = dist-near_clipping
        maxZ = dist+near_clipping
        if self._use_frustum:
#           glFrustum(-1, 1, -1, 1, minZ, maxZ) this is original (dist = 10, so 9 is adjustment)
           glFrustum(-minZ/9., minZ/9., -minZ/9., minZ/9., minZ, maxZ)           
        else:
           a = (dist+1.)/dist
           glOrtho(-a, a, -a, a, minZ, maxZ)           
        projM = read_glmatrix(mode = GL_PROJECTION_MATRIX)

        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_NORMALIZE)
        glLoadIdentity()

        glViewport(0, 0, w, h)
        # loading this so that I don't need to compute matrix for normal vec
        M = np.dot(self.M[1], self.M[0]) #viewM * worldM
        glLoadMatrixf(np.transpose(M).flatten())

        self.set_uniform(glUniformMatrix4fv, 'uWorldM', 1, GL_TRUE,
                         self.M[0])
        self.set_uniform(glUniformMatrix4fv, 'uViewM', 1, GL_TRUE,
                         self.M[1])
        self.set_uniform(glUniformMatrix4fv, 'uProjM', 1, GL_TRUE, projM)

        if shadow_params is not None:
           self.set_uniform(glUniformMatrix4fv, 'uShadowM', 1, GL_TRUE,
                         shadow_params[0])
           self.set_uniform(glUniform1f, 'uShadowMinZ', shadow_params[1])
           self.set_uniform(glUniform1f, 'uShadowMaxZ', shadow_params[2])
           self.test_M = shadow_params[0]

        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                          GL_COLOR_ATTACHMENT1])
        if self._use_clip:
            self.set_uniform(glUniform1i,  'uUseClip', 1)
        else:
            self.set_uniform(glUniform1i,  'uUseClip', 0)           
        
        M = np.dot(self.M[1], self.M[0]) #viewM * worldM
        M = np.dot(projM, M) #projM * viewM * worldM
        self.draw_M = M
        if self._alpha_blend:        
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        else:
            glDisable(GL_BLEND)
        self._shadow = False

    def do_draw_artists(self, tag,  update_id = True):
        id_dict = {}
        current_id = 1.0
        if not self._no_clean:
          #glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
          #glDepthMask(GL_TRUE)
          #glDisable(GL_BLEND)
          glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | 
                  GL_STENCIL_BUFFER_BIT|GL_ACCUM_BUFFER_BIT)

          for aa in self.artists_data:
             if not aa is tag: continue
             if not aa in self.vbo:
                 self.vbo[aa] = weakref.WeakKeyDictionary()
             #aa:axes, a: aritsit
             artists = [(a.get_alpha(), a)for a in self.artists_data[aa]] 
#             for a in self.artists_data[aa]: # a: artist, aa:axes
             for alpha, a in reversed(sorted(artists)):
                if a.axes is not aa: continue
                if self._artist_mask is not None and not  a in self._artist_mask: continue
                if update_id:
                    cid = ((int(current_id) % 256)/255.,
                           (int(current_id)/256 % 256)/255.,
                           (int(current_id)/256**2 % 256)/255., 1.0)
                    self.set_uniform(glUniform4fv, 'uArtistID', 1,  cid)
                if a._gl_hl and not self._hittest_map_update:
                    # second condition indicate it is during pan/rotate
                    self.set_uniform(glUniform1i, 'uHasHL', 1)
                else:
                    self.set_uniform(glUniform1i, 'uHasHL', 0)
                if not a in self.vbo[aa]:
                    xxx = [None]*len(self.artists_data[aa][a])
                else:
                    xxx = self.vbo[aa][a]
                    
                for k, data in enumerate(self.artists_data[aa][a]):
                    m = getattr(self, 'makevbo_'+ data[0])
                    if len(xxx) == k: xxx.append(None)
                    xxx[k] = m(xxx[k], *data[1], **data[2])
                    m = getattr(self, 'draw_'+ data[0])
                    m(xxx[k], *data[1], **data[2])
                self.vbo[aa][a] = xxx
                id_dict[long(current_id)] = id(a)
                current_id = current_id + 1
        return id_dict

#    def make_shadow_texture(self, w, h, data, data2 = None):
    def make_shadow_texture(self, w, h, data2 = None):
#        glBindFramebuffer(GL_FRAMEBUFFER, frame)
        shadow_tex = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, shadow_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)
        #glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
        #             w, h, 0, GL_DEPTH_COMPONENT, GL_FLOAT,
        #             data)
        glReadBuffer(GL_COLOR_ATTACHMENT0)
        glCopyTexImage2D(GL_TEXTURE_2D, 0,  GL_DEPTH_COMPONENT,
                                     0, 0, w, h, 0)
        
        glActiveTexture(GL_TEXTURE0 + 1)        
        #  self.set_uniform(glUniform1i, 'uShadowTex', 1)
        #  self.set_uniform(glUniform2fv, 'uShadowTexSize', 1, (w, h))        
        #  self.shadow =  data.reshape(h, w)
        if data2 is not None:
           shadow_tex2 = glGenTextures(1)

           glBindTexture(GL_TEXTURE_2D, shadow_tex)
           glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
           glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
           glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_NONE)
           #glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
           #          w, h, 0, GL_DEPTH_COMPONENT, GL_FLOAT,
           #         data2)
           glReadBuffer(GL_COLOR_ATTACHMENT1)
           glCopyTexImage2D(GL_TEXTURE_2D, 0,  GL_DEPTH_COMPONENT,
                                     0, 0, w, h, 0)
           glActiveTexture(GL_TEXTURE0 + 2)           
#           self.set_uniform(glUniform1i, 'uShadowTex2', 2)
           return shadow_tex, shadow_tex2
        else:
           return shadow_tex
              
    def draw_mpl_artists(self, tag):
        self._use_frustum = tag._use_frustum
        self._use_clip = tag._use_clip        
        self.gc_artist_data()
#        w, h = self.size = self._frame_w, self._frame_h
        if MyGLCanvas.offscreen:
            w, h, frame, buf, stc, texs = self.get_frame_4_artist(tag)
            glBindFramebuffer(GL_FRAMEBUFFER, frame)
#            print w, h, frame, buf
#            glBindFramebuffer(GL_FRAMEBUFFER, self.frames[0])
        else:
            w, h = self.GetClientSize()
            glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glEnable(GL_DEPTH_TEST)
        
        self.M = tag._matrix_cache
        glPushMatrix()

        if self._use_shadow_map:
           shadow_params = self.use_depthmap_mode(frame, buf, texs, w, h)
           id_dict = self.do_draw_artists(tag, update_id = True)
           glFinish()
           shadow_tex = self. make_shadow_texture(w, h, None)             
           self.use_draw_mode(frame, buf, texs, w, h, shadow_params)
           self.set_uniform(glUniform1i, 'uShadowTex', 1)
           self.set_uniform(glUniform1i, 'uShadowTex2', 2)             
           self.set_uniform(glUniform2fv, 'uShadowTexSize', 1, (w, h))
           self.set_uniform(glUniform1i, 'uUseShadowMap', 1) 
        else:
           self.use_draw_mode(frame, buf, texs, w, h)
           self.set_uniform(glUniform1i, 'uUseShadowMap', 0)            
           
        id_dict = self.do_draw_artists(tag, update_id = True)        
        glFinish()
        glPopMatrix()

        if self._use_shadow_map:        
            glDeleteTextures(shadow_tex)
            #glDeleteTextures(shadow_tex2)            

        self._do_draw_mpl_artists = False
        self._artist_mask = None
        return id_dict
        
    def read_data(self, a):
        w, h, frame, buf, stc, texs = self.get_frame_4_artist(a)
        glBindFramebuffer(GL_FRAMEBUFFER, frame);
        glReadBuffer(GL_COLOR_ATTACHMENT0)
        data = glReadPixels(0,0, w, h, GL_RGBA,GL_UNSIGNED_BYTE)
        if self._hittest_map_update:
           glReadBuffer(GL_COLOR_ATTACHMENT1) # (to check id buffer)
           #data2 = glReadPixels(0,0, w, h, GL_RED, GL_UNSIGNED_BYTE)
           data2 = glReadPixels(0,0, w, h, GL_RGBA, GL_FLOAT)
           # this is to read depth buffer
           data3 = glReadPixels(0,0, w, h, GL_DEPTH_COMPONENT,GL_FLOAT)
           #self.depth =  np.fromstring(data3, np.float32).reshape(h, w)
           #glBindFramebuffer(GL_FRAMEBUFFER, 0)
           glReadBuffer(GL_NONE)
           idmap = (np.fromstring(data2, np.float32).reshape(h, w, -1))*255.
           #print np.sort(np.unique(idmap[:,:, 0].flatten()))
           #print np.sort(np.unique(idmap[:,:, 1].flatten()))           
           #idmap = idmap.astype(int)

           idmap = idmap[:,:,0] + idmap[:,:,1]*256 + idmap[:,:,2]*256**2
           #print np.sort(np.unique(idmap.flatten()))
           return (np.fromstring(data, np.uint8).reshape(h, w, -1),
                   #np.fromstring(data2, np.uint8).reshape(h, w),
                   np.rint(idmap),
                   np.fromstring(data3, np.float32).reshape(h, w))
        else:
           glReadBuffer(GL_NONE)
           return np.fromstring(data, np.uint8).reshape(h, w, -1)
    #
    #  drawing routines
    # 
    def _draw_polygon(self, f, c, facecolor = None, edgecolor = None):
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)
        glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE);
        glClear(GL_STENCIL_BUFFER_BIT)
        glStencilFunc(GL_ALWAYS, 1, 1)
        glStencilOp(GL_INCR, GL_INCR, GL_INCR)
        glDrawArrays(GL_TRIANGLE_FAN, f, c)

        glEnable(GL_DEPTH_TEST)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glStencilFunc(GL_EQUAL, 1, 1)
        glStencilOp(GL_KEEP, GL_KEEP, GL_ZERO)
        if facecolor is not None: glColor(facecolor)

        if self._wireframe != 2:
            if self._wireframe == 1:
               glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
            glDrawArrays(GL_TRIANGLE_FAN, f, c)
            if self._wireframe == 1:
               glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
            
        glDisable(GL_STENCIL_TEST)
        glDepthFunc(GL_LEQUAL)
        if edgecolor is not None: glColor(edgecolor)
#        if not self._shadow :
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                             (0, 0, 0.005, 0.))
#            self.set_uniform(glUniform4fv, 'uViewOffset', 1,
#                             (0, 0, 0.00, 0.))        
            
        if self._wireframe == 2: glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)        
        glDrawArrays(GL_LINE_STRIP, f, c)
        glDepthMask(GL_TRUE)                
        if self._wireframe == 2: glEnable(GL_DEPTH_TEST)
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0.00, 0.))                
        
        glDepthFunc(GL_LESS)

    def _styled_line(self, vbos, linestyle = '--'):
        w = vbos['count']


        atlas_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, atlas_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 
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
        vertex_id.unbind()
        self.EnableVertexAttrib('vertex_id')
        self.EnableVertexAttrib('Vertex2')                        
        void1, void2, w0, h0 = glGetIntegerv(GL_VIEWPORT)
        glViewport(0, 0, w, 1)
        self.set_uniform(glUniform1i,  'uisAtlas', 1)
        self.set_uniform(glUniform3fv, 'uAtlasParam', 1, [w, w0, h0])
        glDrawArrays(GL_LINE_STRIP, 0, w)
        glReadBuffer(GL_COLOR_ATTACHMENT2)
        data = glReadPixels(0, 0, w, 1, GL_RED, GL_FLOAT)
        atlas =  np.hstack((0, np.cumsum(np.fromstring(data, np.float32))))[:-1]

        vertex_id.set_array(atlas.astype(np.float32))
        vertex_id.bind()
        self.VertexAttribPointer('vertex_id', 1, GL_FLOAT, GL_FALSE, 0, None)
        vertex_id.unbind()
#        glFramebufferTexture2D(GL_FRAMEBUFFER, 
#                               GL_COLOR_ATTACHMENT2, 
#                               GL_TEXTURE_2D, 0, 0)
#        glDeleteTextures(atlas_tex)
        self.set_uniform(glUniform1i,  'uisAtlas', 0)
        if linestyle == '--':
           self.set_uniform(glUniform1i,  'uLineStyle', 0)
        elif linestyle == '-.':
           self.set_uniform(glUniform1i,  'uLineStyle', 1)
        elif linestyle == ":":
           self.set_uniform(glUniform1i,  'uLineStyle', 2)  
        else:
           self.set_uniform(glUniform1i,  'uLineStyle', -1)             
        glEnable(GL_DEPTH_TEST)                
        glViewport(0, 0, w0, h0)
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0,
                          GL_COLOR_ATTACHMENT1])
        glDrawArrays(GL_LINE_STRIP, 0, w)

        self.set_uniform(glUniform1i,  'uLineStyle', -1)                
        self.DisableVertexAttrib('vertex_id')
        self.DisableVertexAttrib('Vertex2')                        
        

    def draw_path(self, vbos, gc, path, rgbFace = None,
                  stencil_test = True, linestyle = 'None'):

        glEnableClientState(GL_VERTEX_ARRAY)
        vbos['v'].bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        vbos['v'].unbind()
        if vbos['n'] is not None:
           glEnableClientState(GL_NORMAL_ARRAY)
           vbos['n'].bind()
           glNormalPointer(GL_FLOAT, 0, None)
           vbos['n'].unbind()
        
        lw = gc.get_linewidth()
        if lw > 0: glLineWidth(lw)
        if rgbFace is None:
            glColor(gc._rgb)
            if self._wireframe == 2: glDisable(GL_DEPTH_TEST)            
            if lw != 0:
                if (linestyle == '-' or self._p_shader != self.shader):
                    glDrawArrays(GL_LINE_STRIP, 0, vbos['count'])
                elif linestyle == 'None':
                    pass
                else:
                    self._styled_line(vbos, linestyle = linestyle)
            if self._wireframe == 2: glEnable(GL_DEPTH_TEST)
#            self.set_uniform(glUniform4fv, 'uViewOffset', 1,
#                             (0, 0, 0.00, 0.))
        else:
            glColor(rgbFace)
            self._draw_polygon(0, vbos['count'], facecolor = rgbFace,
                               edgecolor = gc._rgb)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)        
        
    def makevbo_path(self, vbos, gc, path, *args, **kwargs):
        if vbos is None:
            vbos  = {'v': None, 'count':None, 'n':None}
        if vbos['v'] is None or vbos['v'].need_update:
            xyz = np.hstack((path[0], path[1], path[2])).reshape(3, -1)
            xyz = np.transpose(xyz).flatten()
            ### 0, 0, 0 is to make length longer by 1 vetex
            ### for styled_drawing
            xyz = np.hstack((xyz, 0,0,0)) 
            count  = len(path[0])
            xyz =  np.array(xyz, dtype=np.float32)


            if len(path) > 3:
                if paths[3] is None:
                    norms = None
                elif len(paths[3]) == 1:
                    norms = [paths[3]]*len(path[0])
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
        return  vbos

    def draw_image(self, vbos, gc, path, trans, im, interp = 'nearest'):
        glEnableClientState(GL_VERTEX_ARRAY)
        vbos['v'].bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        vbos['v'].unbind()
        glEnableClientState(GL_NORMAL_ARRAY)
        vbos['n'].bind()
        glNormalPointer(GL_FLOAT, 0, None)
        vbos['n'].unbind()
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        vbos['uv'].bind()
        glTexCoordPointer(2, GL_FLOAT, 0, None)
        vbos['uv'].unbind()
        
        glBindTexture(GL_TEXTURE_2D, vbos['im'])
        glActiveTexture(GL_TEXTURE0 + 0)
        self.set_uniform(glUniform1i, 'uImageTex', 0)        
        
        self.set_uniform(glUniform1i, 'uisImage', 1)       
        if self._wireframe == 2: glDisable(GL_DEPTH_TEST)            
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        if self._wireframe == 2: glEnable(GL_DEPTH_TEST)


        self.set_uniform(glUniform1i, 'uisImage', 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
#        glDeleteTextures(image_tex)        

    def makevbo_image(self, vbos, gc, path, trans, im, interp = 'nearest'):
        if vbos is None:
            vbos  = vbos_dict({'v': None, 'count':None, 'n':None, 'im':None,
                               'uv': None, 'im_update':False})
        if vbos['v'] is None or vbos['v'].need_update:
            xyz = np.hstack((path[0], path[1], path[2])).reshape(3, -1)
            xyz = np.transpose(xyz).flatten()
            xyz =  np.array(xyz, dtype=np.float32)
            norms = path[3].astype(np.float32).flatten()
            uv = ((0,0), (0, 1), (1,1), (1,0))
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
            
            h, w,  void = im.shape
            image_tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, image_tex)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, mode)
            glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, mode)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 
                     w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     im)
            glBindTexture(GL_TEXTURE_2D, 0)           
            vbos['im'] = image_tex
            vbos['im_update'] = False

        return  vbos
     
    def draw_markers(self, vbos, gc, marker_path, marker_trans, path,
                     trans, rgbFace=None):


        marker_size = marker_trans[0]
        h, w,  void = marker_path.shape
        
        marker_tex = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0 + 0)
        glBindTexture(GL_TEXTURE_2D, marker_tex)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 
                     w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     marker_path)
        glTexEnvi(GL_POINT_SPRITE, GL_COORD_REPLACE, GL_TRUE)        
        dprint2('marker texture unit : '+ str(marker_tex))
        self.set_uniform(glUniform1i, 'uMarkerTex', 0)


        glEnableClientState(GL_VERTEX_ARRAY)
        vbos['v'].bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        vbos['v'].unbind()
        if rgbFace is None:
           glColor(gc._rgb)
        else:
           glColor(rgbFace)


        if self._wireframe == 2: glDisable(GL_DEPTH_TEST)
        self.set_uniform(glUniform1i, 'uisMarker', 1)
        glPointSize(marker_size*2+1)
        glEnable(GL_POINT_SPRITE)
        self.set_view_offset()        
#        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
#                         (0, 0, -0.005, 0.))
        glDrawArrays(GL_POINTS, 0, vbos['count'])
        self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                         (0, 0, 0., 0.))
        glDisable(GL_POINT_SPRITE)
        
        self.set_uniform(glUniform1i, 'uisMarker', 0)
        if self._wireframe == 2: glEnable(GL_DEPTH_TEST)
                    
        glDeleteTextures(marker_tex)
        glDisableClientState(GL_VERTEX_ARRAY)

    def makevbo_markers(self, vbos, gc, marker_path, maker_trans,
                        path, *args, **kwargs):
       
        vbos = self.makevbo_path(vbos, gc,
                                 (np.array(path[0]).flatten(),
                                  np.array(path[1]).flatten(),
                                  np.array(path[2]).flatten()),
                                 *args, **kwargs)
        return vbos

    def draw_path_collection(self, vbos, gc,  paths, 
                                          facecolor, edgecolor,
                                          linewidth, linestyle, offset,
                                          stencil_test = False,
                                          lighting = True,
                                          view_offset = (0, 0, 0, 0)):


        glEnableClientState(GL_VERTEX_ARRAY)
        vbos['v'].bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        vbos['v'].unbind()
        
        if vbos['n'] is not None:
           glEnableClientState(GL_NORMAL_ARRAY)
           vbos['n'].bind()
           glNormalPointer(GL_FLOAT, 0, None)
           vbos['n'].unbind()

        glEnableClientState(GL_COLOR_ARRAY)
        first, counts = vbos['first'], vbos['counts']
        offset = list(offset)+[0]

        if counts[0] == 3:
           use_multdrawarrays = False           
           primitive_mode = GL_TRIANGLES
        elif counts[0] == 4:
           use_multdrawarrays = False                      
           primitive_mode = GL_QUADS
        elif counts[0] == 2:
           use_multdrawarrays = False                      
           primitive_mode = GL_LINES
        else:           
           use_multdrawarrays = True

        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, offset)
        self.set_uniform(glUniform4fv, 'uViewOffset', 1, view_offset)
        
        if not lighting and self._p_shader is self.shader:
            ambient, light,  specular, shadowmap, clip1, clip2 = self.set_lighting_off()
        if facecolor is not None:
           glEnable(GL_POLYGON_SMOOTH)
           vbos['fc'].bind()
           glColorPointer(4, GL_FLOAT, 0, None)
           vbos['fc'].unbind()

           if len(facecolor) != 0:
               if facecolor.ndim == 3:
                   if facecolor[0,0,3] != 1.0:glDepthMask(GL_FALSE)
               else:
                   if facecolor[0,3] != 1.0:glDepthMask(GL_FALSE)

           if stencil_test:
              for f, c in zip(first, counts): 
                  self._draw_polygon(f, c)
           else:
              if self._wireframe != 2:
                  if self._wireframe == 1:
                      glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
                  if use_multdrawarrays:
                      glMultiDrawArrays(GL_TRIANGLE_FAN, first, counts, 
                                  len(counts))
                  else:
                      glDrawArrays(primitive_mode, 0, len(counts)*counts[0])
                  if self._wireframe == 1:
                      glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)           

        if linewidth[0] > 0.0:
            glLineWidth(linewidth[0])
            vbos['ec'].bind()
            glColorPointer(4, GL_FLOAT, 0, None)
            glDepthFunc(GL_LEQUAL)

            if not self._shadow:
                self.set_view_offset(offset_base = view_offset)
            if self._wireframe == 2: glDisable(GL_DEPTH_TEST)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            if use_multdrawarrays:
                glMultiDrawArrays(GL_LINE_STRIP, first, counts, 
                                 len(counts))
            else:
                glDrawArrays(primitive_mode, 0, len(counts)*counts[0])
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)            
#            glMultiDrawArrays(GL_LINE_STRIP, first, counts,
#                              len(counts))
            if self._wireframe == 2: glEnable(GL_DEPTH_TEST)            
            self.set_uniform(glUniform4fv, 'uViewOffset', 1,
                             (0, 0, 0., 0.))
            vbos['ec'].unbind()
        if not lighting and self._p_shader is self.shader:            
            self.set_lighting(ambient = ambient,
                              light = light, 
                              specular = specular,
                              shadowmap = shadowmap,
                              clip_limit1=clip1, clip_limit2=clip2)
        glDepthFunc(GL_LESS)
        #for f, c in zip(first, counts): 
        #   glDrawArrays(GL_LINE_STRIP, f, c)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        self.set_uniform(glUniform4fv, 'uWorldOffset', 1, (0, 0, 0, 0.))
        glDepthMask(GL_TRUE)

    def set_view_offset(self, offset_base = (0, 0, 0., 0)):
        offset = tuple(np.array(offset_base) + np.array((0, 0, -0.0005, 0.)))
        if self._use_frustum:
           self.set_uniform(glUniform4fv, 'uViewOffset', 1, offset)
        else:
           self.set_uniform(glUniform4fv, 'uViewOffset', 1, offset)
          
    def makevbo_path_collection(self, vbos, gc, paths, facecolor, 
                                      edgecolor, *args, **kwargs):
        if vbos is None:
            vbos  = {'v': None, 'n': None, 'fc':None,
                     'ec': None, 'first':None, 'counts':None}

        from matplotlib.path import Path
        #print 'draw_path_collection', len(facecolor)

        if vbos['v'] is None or vbos['v'].need_update:
            norms = [None]*len(paths)
            xyzs = [None]*len(paths)
            counts = [None]*len(paths)
            for idx, a in enumerate(paths):
                p = [np.array((a.vertices[k][0], a.vertices[k][1], a.zvalues[k]))
                     for k in range(3)]
                n = np.cross(p[2]-p[0], p[1]-p[0])
                
                if np.sum(n*n) != 0:
                    n = -n/np.sqrt(np.sum(n*n))
                xyzs[idx] = np.hstack((a.vertices[:len(a.zvalues)], 
                                       np.vstack(a.zvalues))).flatten()
                counts[idx]  = len(a.zvalues)
                norms[idx] = np.array([n[0], n[1], n[2]]*len(a.zvalues))
            xyzs = np.hstack(xyzs).astype(np.float32)
            norms = np.hstack(norms).astype(np.float32)
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
                facecolor = np.array([[1,1,1, 0]])
            if len(facecolor) == len(counts):
                col = [list(f)*c  for f, c in  zip(facecolor, counts)]
            else:
                col = [facecolor]*np.sum(counts)
            col = np.hstack(col).astype(np.float32)
            if vbos['fc'] is None:
                vbos['fc'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['fc'].set_array(col)
            vbos['fc'].need_update = False

        if vbos['ec'] is None or vbos['ec'].need_update:
            counts = vbos['counts']
            if len(edgecolor) == 0:
                edgecolor = np.array([[1,1,1, 0]])
            if len(edgecolor) == len(counts):
                col = [list(f)*c  for f, c in  zip(edgecolor, counts)]
            else:
                col = [edgecolor]*np.sum(counts)
            col = np.hstack(col).astype(np.float32) 
            if vbos['ec'] is None:
                vbos['ec'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['ec'].set_array(col)
            vbos['ec'].need_update = False

        return vbos
    '''
    (2015 05) I couldn't figure out how to use glMultiDrawElements with VBO
              through PyOpenGL... 
    def draw_path_collection_e(self, vbos, gc,  paths, 
                                          facecolor, edgecolor,
                                          linewidth, offset, stencil_test):
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_INDEX_ARRAY)        
        offset = list(offset)+[0]
        if len(facecolor) != 0:
            if facecolor[0][3] != 1.0:
                glDepthMask(GL_FALSE)

        glUniform4fv(self.uniform_loc['uWorldOffset'], 1, offset)
        vbos['v'].bind()
        glVertexPointer(3, GL_FLOAT, 0, None)
        vbos['v'].unbind()
        vbos['n'].bind()
        glNormalPointer(GL_FLOAT, 0, None)
        vbos['n'].unbind()

        vbos['fc'].bind()
        glColorPointer(4, GL_FLOAT, 0, None)
        vbos['fc'].unbind()
        
        vbos['i'].bind()
        glIndexPointer(GL_SHORT, 0, None)

        first, counts = vbos['first'], vbos['counts']
        if stencil_test:
           for f, c in zip(first, counts): 
               self._draw_polygon_e(f, c, vbos['i'])
        else:
           if self._wireframe != 2:
               if self._wireframe == 1:
                   glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)

               glMultiDrawElements(GL_TRIANGLE_FAN, counts, GL_UNSIGNED_SHORT,
                                   vbos['i'], 1)
               if self._wireframe == 1:
                   glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)           

#        linewidth = np.atleast_1d(gc.get_linewidth())
#        if linewidth[0] != 0.0:
        if False:
            glLineWidth(linewidth[0])
            vbos['ec'].bind()
            glColorPointer(4, GL_FLOAT, 0, None)
            vbos['ec'].unbind()
            glDepthFunc(GL_LEQUAL)
            
            glUniform4fv(self.uniform_loc['uViewOffset'], 1, (0, 0, 0.01, 0.))
            if self._wireframe == 2: glDisable(GL_DEPTH_TEST)                        
            glMultiDrawElements(GL_LINE_STRIP, counts, GL_UNSIGNED_SHORT,
                                vbos['i'], len(counts))                                
            if self._wireframe == 2: glEnable(GL_DEPTH_TEST)           
            glUniform4fv(self.uniform_loc['uViewOffset'], 1, (0, 0, 0.00, 0.))
            
        glDepthFunc(GL_LESS)
        #for f, c in zip(first, counts): 
        #   glDrawArrays(GL_LINE_STRIP, f, c)
        vbos['i'].unbind()                
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_INDEX_ARRAY)        
        glUniform4fv(self.uniform_loc['uWorldOffset'], 1, (0, 0, 0, 0.))
        glDepthMask(GL_TRUE)
    '''

    '''
       _e is made to use index buffer,,, but for now
       the index buffer is not used...which means perhapse
       2-3 times GPU memory consumption...
    '''
    draw_path_collection_e = draw_path_collection
    
    def makevbo_path_collection_e(self, vbos, gc, paths, facecolor, 
                                      edgecolor, *args, **kwargs):
        ### paths is [X, Y, Z, norms, idxset]       
        if vbos is None:
            vbos  = {'v': None, 'n': None, 'i':None, 'fc':None,
                     'ec': None, 'first':None, 'counts':None}

        from matplotlib.path import Path
        #print 'draw_path_collection', len(facecolor)

        # make indexset when it is needed
        # index set is changed to uint32 instead of uint16 (2016 06 28)
        if ((vbos['v'] is None or vbos['v'].need_update) or
            ((vbos['fc'] is None or vbos['fc'].need_update) and
             facecolor is not None) or 
            (vbos['ec'] is None or vbos['ec'].need_update)):           
           idxset = np.hstack(paths[4]).astype(np.uint32).flatten()
           
        
        if vbos['v'] is None or vbos['v'].need_update:
#        if True:
            xyzs = np.transpose(np.vstack((paths[0][idxset],
                                           paths[1][idxset],
                                           paths[2][idxset])))
            
#            if hasattr(self, 'test_M'):
#               for k in range(20):
#                   print np.dot(self.test_M, np.hstack((xyzs[k], 1)))
            xyzs = xyzs.flatten().astype(np.float32)
            counts = [len(idx) for idx in paths[4]]
            first = np.array(counts).cumsum()
            first = list(np.hstack((np.array([0]), first[:-1])))
            if paths[3] is None:
                norms = None
            elif len(paths[3]) == len(paths[0]):
                ## norm is already specified for each vetex
                norms = paths[3].astype(np.float32)[idxset,:].flatten()
            elif len(paths[3]) == 1:
                ## norm is common (flat surface)
                norms = [paths[3]]*np.sum(counts)
                norms = np.hstack(norms).astype(np.float32).flatten()
            else:
                norms = paths[3].astype(np.float32).flatten()
            if vbos['v'] is None:
                vbos['v'] = get_vbo(xyzs, usage='GL_STATIC_DRAW')
                if norms is not None: vbos['n'] = get_vbo(norms, usage='GL_STATIC_DRAW')
                vbos['i'] = get_vbo(idxset, usage='GL_STATIC_DRAW',
                                    target = 'GL_ELEMENT_ARRAY_BUFFER')
            else:
                vbos['v'].set_array(xyzs)
                if norms is not None:
                   vbos['n'].set_array(norms)
                else:
                   vbos['n'] = None
                vbos['i'].set_array(idxset)

            vbos['counts'] = np.array(counts)   ## 2016 06 27
            vbos['first'] = np.array(first)     ## 2016 06 27
            vbos['v'].need_update = False
            if vbos['n'] is not None: vbos['n'].need_update = False

        if ((vbos['fc'] is None or vbos['fc'].need_update) and
            facecolor is not None):
            counts = vbos['counts']
            
            if len(facecolor) == 0:
                facecolor = np.array([[1,1,1, 0]])
            if  facecolor.ndim == 3:
                col = [facecolor]
            elif len(facecolor) == len(paths[0]):
#                col = [list(f)*c  for f, c in  zip(facecolor, counts)]
                col = facecolor[idxset,:]
            elif len(facecolor) == len(counts):
                col = [list(f)*c  for f, c in  zip(facecolor, counts)]
            else:
                col = [facecolor]*np.sum(counts)
            
            col = np.hstack(col).astype(np.float32)
            if vbos['fc'] is None:
                vbos['fc'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['fc'].set_array(col)
            
            vbos['fc'].need_update = False
        if vbos['ec'] is None or vbos['ec'].need_update:
            counts = vbos['counts']
            if len(edgecolor) == 0:
                edgecolor = np.array([[1,1,1, 0]])
            if len(edgecolor) == len(paths[0]):
#                col = [list(f)*c  for f, c in  zip(edgecolor, counts)]
                col = edgecolor[idxset, :]               
            else:
                col = [edgecolor]*np.sum(counts)
            col = np.hstack(col).astype(np.float32) 
            if vbos['ec'] is None:
                vbos['ec'] = get_vbo(col, usage='GL_STATIC_DRAW')
            else:
                vbos['ec'].set_array(col)
            
            vbos['ec'].need_update = False        
        return vbos
          
    def has_vbo_data(self, artist):
        tag = self.get_container(artist)
        if not tag in self.vbo: return False
        return artist in self.vbo[tag]

    def get_vbo_data(self, artist):
        tag = self.get_container(artist)
        if not tag in self.vbo: return None
        if artist in self.vbo[tag]:
            return self.vbo[tag][artist]
        return None

    def store_artists(self, artists):
        for a in artists:
            if not a in self.artists:
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
        from art3d_gl import frame_range
        target = self.get_container(a)
        box = trans.transform([frame_range[0:2], frame_range[2:4]])
        d = box[1] - box[0]
        w, h = long(d[0]), long(d[1])
        make_new = False


        if target in self.frame_list:
             w2, h2, frame, bufs, stc, texs = self.frame_list[target]
             if w2 != w or h2 != h:
                 glDeleteTextures(texs)
                 glBindFramebuffer(GL_FRAMEBUFFER, 0)
                 glBindRenderbuffer(GL_RENDERBUFFER, 0)
                 glDeleteFramebuffers(1, [frame])
                 glDeleteRenderbuffers(len(bufs), bufs)
                 del self.frame_list[target]
                 self.frames.remove(frame)
                 make_new = True
        else:
            make_new = True
        if make_new:
#            print 'makeing new frame', w, h
            frame, buf, stc, dtex = self.get_newframe(w, h)
            if frame is not None:
                self.frame_list[target] = (w, h, frame, buf, stc, dtex)

    def OnDraw(self):
         if self._do_draw_mpl_artists:
              pass
#            self.get_newframe()
#            self.draw_mpl_artists()

#         glBindFramebuffer(GL_FRAMEBUFFER, 0)
 #        self.SwapBuffers()

        #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

#from renderer_gl import RendererGL
from matplotlib.backends.backend_agg import RendererAgg
class RendererGLMixin(object):
    def __init__(self, *args, **kwargs):
        self.do_stencil_test = False
        self._no_update_id = False
        
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

    def update_id_data(self, data, tag = None):
        if not self._no_update_id:
           tag._gl_id_data = data
        self._no_update_id = False
    def no_update_id(self):
        self._no_update_id = True
        

def mixin_gl_renderer(renderer):
    if hasattr(renderer, '_gl_renderer'): return 
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
            glcanvas.SetMinSize((2,2))
            glcanvas.SetMaxSize((2,2))
            #self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
            win.GetSizer().Add(glcanvas)
            win.Layout()
            glcanvas.Refresh()
        
    def get_renderer(self, cleared=False):
        l, b, w, h = self.figure.bbox.bounds
        key = w, h, self.figure.dpi
        try: self._lastKey, self.renderer
        except AttributeError: need_new_renderer = True
        else:  need_new_renderer = (self._lastKey != key)

        if need_new_renderer:
            self.renderer = RendererAgg(w, h, self.figure.dpi)
            mixin_gl_renderer(self.renderer)
            self._lastKey = key
        elif cleared:
            self.renderer.clear()
        return self.renderer

    def draw(self, drawDC = None, nogui_reprint = False):
        if self.figure is None: return
        if self.figure.figobj is None: return

        for fig_axes in self._auto_update_ax:
            fig_axes.set_bmp_update(False)

        #st =time.time()       
        if not self.resize_happend:
            s = self.draw_by_bitmap()
            # this makes draw_event
            self.figure.draw_from_bitmap(self.renderer)
            self._isDrawn = True
            if not nogui_reprint:
                #print 'draw calling gui_repaint'
                self.gui_repaint(drawDC=drawDC)

    def draw_artist(self, drawDC=None, alist=None):
        if alist is None: alist = []
        gl_obj = [a for a in alist if hasattr(a, 'is_gl')]
        for o in gl_obj: o.is_last =  False
        if len(gl_obj) > 0:
            gl_obj[-1].is_last =  True
            self.renderer.no_update_id()
#            self.renderer.no_lighting = no_lighting
            FigureCanvasWxAggModGL.glcanvas._artist_mask = alist
        v =  FigureCanvasWxAggMod.draw_artist(self, drawDC=drawDC, alist=alist)
#        self.renderer.no_lighting = False
        return v


    def _onPaint(self, evt):
#        self.glcanvas.OnPaint(evt)
#        evt.Skip()
        FigureCanvasWxAggMod._onPaint(self, evt)

    def _onSize(self, evt=None, nocheck=False):
        FigureCanvasWxAggMod._onSize(self, evt = evt, nocheck = nocheck)
        #self.glcanvas.SetSize(self.bitmap.GetSize())
        
    def disable_alpha_blend(self):
        FigureCanvasWxAggModGL.glcanvas._alpha_blend = False

    def enable_alpha_blend(self):
        FigureCanvasWxAggModGL.glcanvas._alpha_blend = True

