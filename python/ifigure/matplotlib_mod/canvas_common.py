from __future__ import print_function
import os
import numpy as np
import time
import wx
import weakref

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('canvas_common')

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
    #from OpenGL.GLUT import *
    from OpenGL.GLU import *
    from OpenGL.GL import shaders
    from OpenGL.arrays import vbo

    class myvbo(vbo.VBO):
        pass
    haveOpenGL = True
except ImportError:
    haveOpenGL = False

    
near_clipping = 45.    # must be float (default 8) = A
camera_distance = 50.  # must be float (default 10) = B
# I haven't check relations between these. Apparently, (B-A)/B = 1/10.?

view_scale = 1.

multisample = 1
multisample_init_done = False

basedir = os.path.dirname(__file__)


def compile_file(file, mode):
    fid = open(os.path.join(basedir, file), 'r')
    prog = ''.join(fid.readlines())
    fid.close()
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


def define_attrib(shader, name):
    shader.attrib_loc[name] = glGetAttribLocation(shader, name)


def check_framebuffer(message, mode=GL_FRAMEBUFFER):
    # list up possible errors
    attrs = [GL_FRAMEBUFFER_COMPLETE, GL_FRAMEBUFFER_UNSUPPORTED, GL_INVALID_ENUM]
    for x in dir(OpenGL.GL):
        if x.startswith('GL_FRAMEBUFFER_INCOMPLETE'):
            attrs.append(getattr(OpenGL.GL,x))
    #for a in attrs:
    #    print(a, int(a))

    check = glCheckFramebufferStatus(mode)
    if int(check) != int(attrs[0]):
        print('Framebuffer imcomplete (' + message + ')')
        for x in attrs:
            if int(check) == int(x):
                print(x)
        return False

    # print "test sample", glGetIntegerv(GL_SAMPLE_BUFFERS)
    return True

def frustum(left, right, bottom, top, zNear, zFar, view_scale=1):
    dx = right - left
    dy = top - bottom
    A = (right + left) / (right - left)
    B = (top + bottom) / (top - bottom)
    C = -(zFar + zNear) / (zFar - zNear)
    D = - (2*zFar * zNear) / (zFar - zNear)
    M = np.array([[2*zNear/dx*view_scale, 0,           A, 0],
                  [0,          2*zNear/dy*view_scale,  B, 0],
                  [0,          0,           C, D],
                  [0,          0,          -1, 0]])
    return M


def ortho(left, right, bottom, top, zNear, zFar, view_scale=1):
    dx = right - left
    dy = top - bottom
    dz = zFar - zNear
    tx = - (right + left) / (right - left)
    ty = - (top + bottom) / (top - bottom)
    tz = - (zFar + zNear) / (zFar - zNear)
    return np.array([[2/dx*view_scale, 0,     0,     tx],
                     [0,    2/dy*view_scale,  0,     ty],
                     [0,    0,     -2/dz,    tz],
                     [0,    0,     0,        1.]])


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
