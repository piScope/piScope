import numpy as np
import weakref
import threading

from matplotlib.image import AxesImage
from matplotlib.patches import Polygon
from ifigure.matplotlib_mod.is_supported_renderer import isSupportedRenderer
from ifigure.matplotlib_mod.backend_wxagg_gl import mixin_gl_renderer
from ifigure.utils.marker_image import marker_image
from ifigure.ifigure_config import isMPL2
import mpl_toolkits.mplot3d.proj3d as proj3d
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.art3d import PathPatch3D, juggle_axes
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3D, Patch3D
from matplotlib.collections import Collection, LineCollection, \
    PolyCollection, PatchCollection, PathCollection

# matplotlib
try:
    from matplotlib._image import fromarray, frombyte
except:
    def frombyte(im, num): return im

from matplotlib.colors import ColorConverter
from matplotlib.path import Path

cc = ColorConverter()

# mplot3d

##

# this magic number effectively scale and transpose
# an image produced by GL backend, so that it become
# consistent with the axes drawn by Axes3D.
frame_range = np.array([-0.095, -0.095, 1.1, 1.10])+0.01
#frame_range = np.array([0, 0, 1, 1])


def finish_gl_drawing(glcanvas, renderer, tag, trans):
    renderer._k_globj += 1
    if (renderer._k_globj != renderer._num_globj):
        return
    if not glcanvas._hittest_map_update:
        glcanvas._no_hl = False
        id_dict = glcanvas.draw_mpl_artists(tag)
        im = glcanvas.read_data(tag)
        gc = renderer.new_gc()
        x, y = trans.transform(frame_range[0:2])
        im = frombyte(im, 1)
        if not isMPL2:
            im.is_grayscale = False  # this is needed to print in MPL1.5
        renderer.draw_image(gc, round(x), round(y), im)
        gc.restore()
    else:
        #
        # need to draw twice due to buffering of pixel reading
        #
        glcanvas._no_hl = True
        glcanvas._hittest_map_update = True
        id_dict = glcanvas.draw_mpl_artists(tag)
        # im : image, im2, im2d: id, im3: depth
        im, im2, im2d, im3 = glcanvas.stored_im

        glcanvas._hittest_map_update = False
        id_dict = glcanvas.draw_mpl_artists(tag)
        im = glcanvas.read_data(tag)

        glcanvas._hittest_map_update = True

        gc = renderer.new_gc()
        x, y = trans.transform(frame_range[0:2])
        im = frombyte(im, 1)
        if not isMPL2:
            im.is_grayscale = False  # this is needed to print in MPL1.5

        if renderer.gl_svg_rescale:
            # svg renderer has image_dpi = 100 (not 72)
            # therefore width and height needs to be set
            x2, y2 = trans.transform(frame_range[2:])
            renderer.draw_image(gc, round(x), round(y), im,
                                dx=round(x2-x), dy=round(y2-y))
        else:
            renderer.draw_image(gc, round(x), round(y), im)
        renderer.update_id_data((x, y, id_dict, im2, im2d, im3), tag=tag)
        gc.restore()
    tag._gl_img = im


def get_glcanvas():
    from ifigure.matplotlib_mod.backend_wxagg_gl import FigureCanvasWxAggModGL
    return FigureCanvasWxAggModGL.glcanvas


def draw_wrap(func):
    def func_wrap(self, renderer):
        axes = self.axes
        bmp_update = self.axes.figobj._bmp_update
        if bmp_update and axes._gl_id_data is not None:
            renderer._k_globj += 1
            if (renderer._k_globj != renderer._num_globj):
                return
            x0, y0, id_dict, im, imd, im2 = axes._gl_id_data
            gc = renderer.new_gc()
            #print("drawing stored image", axes.figobj)
            renderer.draw_image(gc, round(x0), round(y0), axes._gl_img)
            gc.restore()
        else:
            return func(self, renderer)

    func_wrap._supports_rasterization = True  # suppress user warning
    return func_wrap


class ArtGL(object):
    is_gl = True

    def __init__(self, **kargs):
        self._gl_3dpath = None
        self._gl_lighting = True
        self._gl_offset = (0, 0, 0.)
        self._gl_voffset = (0., 0., 0., 0.)        # view offset
        self._gl_data_extent = None
        self._gl_hl = False
        self._gl_hit_array_id = []
        self._gl_array_idx = kargs.pop('array_idx', None)
        if self._gl_array_idx is not None:
            self._gl_array_idx = np.array(self._gl_array_idx, dtype=int,
                                          copy=False)
        self._gl_pickable = True
        self._gl_hl_use_array_idx = False
        self._gl_marker_tex = weakref.WeakKeyDictionary()
        self._gl_isLast = False  # an aritst which should be drawn last
        self._gl_always_noclip = False  # used for axis
        self._gl_isArrow = False  # used for axis
        self._gl_repr_name = ''

        # MPL3.6.1 and after this is not used and not defined.
        self._offset_position = [0, 0, 0]

    def get_gl_arrayid_hit(self):
        return self._gl_hit_array_id

    def set_gl_pickable(self, value):
        self._gl_pickable = value

    def set_gl_hl_use_array_idx(self, value):
        self._gl_hl_use_array_idx = value

    def get_gl_hl_use_array_idx(self):
        return self._gl_hl_use_array_idx

    def contains(self, evt):
        if self.axes is not None:
            c = self.axes
        elif self.figure is not None:
            c = self.figure
        if not self._gl_pickable:
            return False, {}

        check, array_id = c.gl_hit_test(evt.x, evt.y,
                                        self, radius=3)

        if check:
            shift_down = evt.guiEvent.ShiftDown()

            self._gl_hit_array_id_new = self._gl_hit_array_id.copy()
            if int(array_id) in self._gl_hit_array_id:
                self._gl_hit_array_id_new.remove(int(array_id))
            else:
                if shift_down:
                    self._gl_hit_array_id_new.append(int(array_id))
                else:
                    self._gl_hit_array_id_new = [int(array_id)]
            # self.mask_array_idx()
            return True, {'child_artist': self}
        return False, {}

    def unselect_gl_artist(self):
        self._gl_hl = False
        if len(self._gl_hit_array_id) > 0:
            self._gl_hit_array_id = []
            self._gl_hit_array_id_new = []
            self.mask_array_idx()

    def mask_array_idx(self, shift_down=True):
        if self._gl_array_idx is not None:
            if (not shift_down and len(self._gl_hit_array_id) > 0):
                # any([not x in self._gl_hit_array_id  for x in self._gl_hit_array_id_new])):
                # if not shift-donw. already_selected, and all new selected is not in already_selected
                self.unselect_gl_artist()
                return

            array_idx = np.abs(self._gl_array_idx)
            mask = np.isin(array_idx, self._gl_hit_array_id_new)
            array_idx[mask] *= -1
            self._gl_array_idx = array_idx
            self._gl_hit_array_id = self._gl_hit_array_id_new
        self._update_a = True
        self.axes.figobj._bmp_update = False  # ugly...!?

    def get_gl_data_extent(self):
        if self._gl_data_extent is None:
            try:
                self._gl_data_extent = [(np.nanmin(self._gl_3dpath[k]),
                                         np.nanmax(self._gl_3dpath[k])) for k in range(3)]

            except:
                import traceback
                traceback.print_exc()

        if self._gl_data_extent is None:
            return [None]*3
        return self._gl_data_extent

    def get_glverts(self):
        '''
        x, y, z = get_glverts()
        '''
        return self._gl_3dpath[0:3]

    def add_hl_mask(self):
        if self.axes is not None:
            c = self.axes
        elif self.figure is not None:
            c = self.figure
        if c is None:
            return []
        if self._gl_hl_use_array_idx:
            c.set_gl_hl_mask(self,
                             hit_id=self._gl_hit_array_id)
        else:
            c.set_gl_hl_mask(self)

        self._gl_hl = True
        return []

    # we need a comparision operator defined for PY3
    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __le__(self, other):
        return False

    def __lt__(self, other):
        return False

    def get_alpha_float(self):
        if self.get_alpha() is None:
            return 1
        return self.get_alpha()

    def __repr__(self):
        if self._gl_repr_name == '':
            return object.__repr__(self)
        else:
            return self._gl_repr_name

    def __str__(self):
        return self.__repr__()


class LineGL(ArtGL, Line3D):
    def __init__(self, xdata, ydata, zdata,  **kargs):
        self._invalidz = False
        self._zorig = None
        self._update_path = False
        self._facecolor = None
        self._gl_array_idx = kargs.pop('array_idx', None)
        Line3D.__init__(self, xdata, ydata, zdata, **kargs)
        ArtGL.__init__(self)

    def __repr__(self):
        return 'LineGL'

    def set_zdata(self, z):
        self._zorig = z
        self._invalidz = True

    def get_zdata(self):
        return self._zorig

    def verts3d_to_3dpath(self):
        x, y, z = self._verts3d
        if np.sum(np.isfinite(x)) == len(x):
            self._gl_3dpath = (x, y, z)
        else:
            x = [x[s] for s in np.ma.clump_unmasked(np.ma.masked_invalid(x))]
            y = [y[s] for s in np.ma.clump_unmasked(np.ma.masked_invalid(y))]
            z = [z[s] for s in np.ma.clump_unmasked(np.ma.masked_invalid(z))]
            norms = None
            idx = np.arange(len(x), dtype=np.int32)
            l = 0
            indexset = []
            for chunk in x:
                indexset.append(np.arange(len(chunk))+l)
                l = l + len(chunk)
#            indexset = index
            if self._facecolor is None:
                norms = None
            else:
                norms = []
                for xx, yy, zz in zip(x, y, z):
                    p0, p1, p2 = [(xx[k], yy[k], zz[k]) for k in range(3)]
                    n1 = np.cross(p0-p1, p1-p2)
                    d = np.sqrt(np.sum(n1**2))
                    if d == 0:
                        norms.append([0, 0, 1])
                    else:
                        norms.append(n1/d)
                    norms = np.hstack(norms).astype(np.float32).flatten()
            x = np.hstack(x).flatten()
            y = np.hstack(y).flatten()
            z = np.hstack(z).flatten()
            self._gl_3dpath = (x, y, z, norms, indexset)

    def update_marker_texture(self, renderer):
        updte = False
        m_facecolor = self.get_markerfacecolor()
        m_edgecolor = self.get_markeredgecolor()
        m_edgewidth = self.get_markeredgewidth()
        m_marker = self.get_marker()
        m_size = renderer.points_to_pixels(self._markersize)
        marker_param = (m_size, m_edgecolor,
                        m_facecolor, m_edgewidth, m_marker)

        if self._marker in self._gl_marker_tex:
            data = self._gl_marker_tex[self._marker]
            if data['param'] == marker_param:
                return data['path']

        marker_path = marker_image(self._marker.get_path(),
                                   m_size,
                                   self._marker.get_transform(),
                                   edgecolor=m_edgecolor,
                                   facecolor=m_facecolor,
                                   edgewidth=m_edgewidth)
        data = {'path': marker_path,
                'param': marker_param}
        self._gl_marker_tex[self._marker] = data
        return marker_path

    @draw_wrap
    def draw(self, renderer):
        if isSupportedRenderer(renderer):
            if self._invalidy or self._invalidx or self._invalidz:
                self.recache()
                if self.get_zdata() is None:
                    self._zorig = np.array([0]*len(self.get_xdata()))
            renderer.use_gl = True
            glcanvas = get_glcanvas()
            if self.axes is not None:
                tag = self.axes
                trans = self.axes.transAxes
            elif self.figure is not None:
                tag = self.figure
                trans = self.figure.transFpigure

            glcanvas.frame_request(self, trans)
#           if not glcanvas.has_vbo_data(self):
            glcanvas.start_draw_request(self)

            # 3dpath = (self.get_xdata(), self.get_ydata(), self_zdata())
            #path = Path(self._xy)
            if self._invalidz:
                self.set_3d_properties(zs=self.get_zdata(), zdir='z')
                if glcanvas.has_vbo_data(self):
                    d = glcanvas.get_vbo_data(self)
                    for x in d:
                        x['v'].need_update = True
#           path.zvalues =  self.get_zdata()

            self._invalidz = False
            gc = renderer.new_gc()

            from matplotlib.colors import to_rgba
            ln_color_rgba = to_rgba(self._color, self._alpha)

            gc.set_foreground(ln_color_rgba, isRGBA=True)
            gc.set_linewidth(self._linewidth)

            if self._marker.get_marker() == ',':
                gc.set_linewidth(0)

            if self._gl_3dpath is None:
                self.verts3d_to_3dpath()
            if len(self._gl_3dpath) == 3:
                renderer.gl_draw_path(gc, self._gl_3dpath,  trans,
                                      rgbFace=self._facecolor,
                                      linestyle=self._linestyle)
            else:
                fc = None if self._facecolor is None else [self._facecolor]
                renderer.gl_draw_path_collection_e(
                    gc, None, self._gl_3dpath,
                    None, self._gl_offset, None,
                    fc, [ln_color_rgba],
                    [self._linewidth], self._linestyle,
                    self._antialiased, self._url,
                    None, lighting=self._gl_lighting,
                    stencil_test=False,
                    view_offset=self._gl_voffset,
                    array_idx=self._gl_array_idx)

            if len(self._marker.get_path()) != 0:
                marker_path = None
                marker_trans = None
                m_facecolor = self.get_markerfacecolor()
                m_edgecolor = self.get_markeredgecolor()
                m_edgewidth = self.get_markeredgewidth()
                m_size = renderer.points_to_pixels(self._markersize)
                #marker_path is bitmap (texture)
                # marker_trans is marker_size and other info (liken marker_every)
                marker_path = self.update_marker_texture(renderer)
                marker_trans = (m_size,)
                renderer.gl_draw_markers(gc, marker_path, marker_trans,
                                         self._gl_3dpath[:3],  trans,
                                         array_idx=self._gl_array_idx)
            glcanvas.end_draw_request()
            gc.restore()

            finish_gl_drawing(glcanvas, renderer, tag, trans)
            renderer.use_gl = False
        else:
            v = Line3D.draw(self, renderer)
#        return v


def line_3d_to_gl(obj):
    obj.__class__ = LineGL
    obj._invalidz = False
    obj._zorig = None
    obj._facecolor = None
    ArtGL.__init__(obj)
    return obj


class AxesImageGL(ArtGL, AxesImage):
    def __init__(self, *args, **kargs):
        ArtGL.__init__(self)
        AxesImage.__init__(self, *args, **kargs)
        self._gl_interp = 'nearest'
        self._gl_rgbacache_id = None
        self._update_im = False

    def __repr__(self):
        return 'ImageGL'

    def set_im3dpath(self, im_center, im_axes):
        '''
             p2---p3
         (y) |    |
             p0---p1
               (x)
        '''
        x1, x2, y1, y2 = self.get_extent()
        im_center = np.array(im_center)
        p = [im_center+x1*np.array(im_axes[0]) + +y1*np.array(im_axes[1]),
             im_center+x2*np.array(im_axes[0]) + +y1*np.array(im_axes[1]),
             im_center+x2*np.array(im_axes[0]) + +y2*np.array(im_axes[1]),
             im_center+x1*np.array(im_axes[0]) + +y2*np.array(im_axes[1]), ]

        n = np.cross(im_axes[0], im_axes[1])
        p = np.array(p)
        x = p[..., 0].flatten()
        y = p[..., 1].flatten()
        z = p[..., 2].flatten()
        self._gl_3dpath = (x, y, z, np.hstack([n]*len(x)),
                           np.arange(len(x)).astype(np.int32))

    def set_cmap(self, *args, **kwargs):
        super(AxesImage, self).set_cmap(*args, **kwargs)
        self._gl_rgbacache_id = None

    def make_hl_artist(self, container):
        idx = [0, 1, 2, 3]
        x = [self._gl_3dpath[0][k] for k in idx]
        y = [self._gl_3dpath[1][k] for k in idx]
        z = [self._gl_3dpath[2][k] for k in idx]
        hl = container.plot(x, y, zs=z)[0]
        hl.set_zdata(z)
        hl.set_color([0, 0, 0, 1])
        hl._facecolor = (0, 0, 0, 0.5)
        hl.set_linewidth(0)

        return [hl]

    def set_gl_interp(self, value):
        self._gl_interp = value
        glcanvas = get_glcanvas()
        if glcanvas.has_vbo_data(self):
            d = glcanvas.get_vbo_data(self)
            for x in d:
                x['im_update'] = True
#           path.zvalues =  self.get_zdata()
        self._gl_texture_update = False

    @draw_wrap
    def draw(self, renderer):
        v = None
        if isSupportedRenderer(renderer):
            renderer.use_gl = True
            glcanvas = get_glcanvas()
            if self.axes is not None:
                tag = self.axes
                trans = self.axes.transAxes
            elif self.figure is not None:
                tag = self.figure
                trans = self.figure.transFigure
            glcanvas.frame_request(self, trans)
#           if not glcanvas.has_vbo_data(self):
            glcanvas.start_draw_request(self)
            if self._gl_3dpath is not None:
                try:
                    im = self.to_rgba(self._A)
                    im = (im*255).astype(int)
                except:
                    # this is for an old version of matplotlib
                    im = self.make_image(renderer.get_image_magnification())
                idx_none = im[..., 3] == 0
                im[idx_none, 0:3] = 255
                self._im_cache = im
                gc = renderer.new_gc()
                gc.set_alpha(self.get_alpha())

                if self._gl_rgbacache_id != id(self._imcache):
                    if glcanvas.has_vbo_data(self):
                        d = glcanvas.get_vbo_data(self)
                        for x in d:
                            x['im_update'] = True
                renderer.gl_draw_image(gc, self._gl_3dpath,  trans,
                                       np.transpose(self._im_cache, (1, 0, 2)),
                                       interp=self._gl_interp,
                                       always_noclip=self._gl_always_noclip)

                self._gl_rgbacache_id = id(self._imcache)
                gc.restore()
            else:
                pass
            glcanvas.end_draw_request()
            finish_gl_drawing(glcanvas, renderer, tag, trans)
            renderer.use_gl = False
        else:
            pass


def image_to_gl(obj):
    obj.__class__ = AxesImageGL
    ArtGL.__init__(obj)
    obj._gl_interp = 'nearest'
    obj._gl_rgbacache_id = None
    return obj


class Line3DCollectionGL(ArtGL, Line3DCollection):
    def __init__(self, *args, **kargs):
        ArtGL.__init__(self)
        self.do_stencil_test = True
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_offset = kargs.pop('gl_offset', (0, 0, 0.))
        self._gl_edgecolor = kargs.pop('gl_edgecolor', None)
        self._c_data = kargs.pop('c_data', None)
        self._gl_solid_edgecolor = kargs.pop('gl_solid_edgecolor', None)
        self._gl_lighting = kargs.pop('gl_lighting', True)
        self._gl_array_idx = kargs.pop('array_idx', None)
        self._gl_voffset = kargs.pop('view_offset', (0, 0, 0, 0.))
        self._update_ec = True
        self._update_v = True
        Line3DCollection.__init__(self, *args, **kargs)

    def convert_2dpath_to_3dpath(self, z=None, zdir='z'):

        x1 = []
        y1 = []
        z1 = []
        norms = []
        idxset = []
        idxbase = 0
        if zdir == 'x':
            norm = np.array([1., 0, 0.])
        elif zdir == 'y':
            norm = np.array([0., 1, 0.])
        else:
            norm = np.array([0., 0, 1.])

        xyzlist = []
        for points in self._segments3d:
            points = np.vstack(points)
            xyzlist.append((points[:, 0], points[:, 1], points[:, 2],))
#        xyzlist = [(points[:,0], points[:, 1], points[:,2])
#                   for points in self._segments3d]

        for v0, v1, v2 in xyzlist:
            x1.append(v0)
            y1.append(v1)
            idxset.append(np.arange(len(v0))+idxbase)
            z1.append(v2)
            norms.append(np.hstack([norm]*len(v0)))
            idxbase = len(v0)+idxbase

        x1 = np.hstack(x1)
        y1 = np.hstack(y1)
        z1 = np.hstack(z1)
        norms = np.hstack(norms).reshape(-1, 3)
        X3D, Y3D, Z3D = juggle_axes(x1, y1, z1, zdir)
        # does norm may mean anything, but let's leave it...
        self._gl_3dpath = [X3D, Y3D, Z3D, norms, idxset]

    def set_cmap(self, *args, **kwargs):
        super(Line3DCollectionGL, self).set_cmap(*args, **kwargs)
        self._update_ec = True

    def set_color(self, colors):
        super(Line3DCollectionGL, self).set_color(colors)
        if colors is None:
            colors = tuple()
        if len(colors) == 1:
            self._gl_solid_edgecolor = colors[0]
        else:
            self._gl_solid_edgecolor = None
        self._update_ec = True

#    set_edgecolor = set_color
#    set_edgecolors = set_edgecolor

    def set_alpha(self, a):
        self._alpha = a
        if self._gl_solid_edgecolor is not None:
            c = cc.to_rgba(self._gl_solid_edgecolor, alpha=a)
            self._gl_solid_edgecolor = c
        self._update_ec = True

    def get_alpha(self):
        return self._alpha

    def seg_c_data(self, cdata):
        if np.iscomplexobj(cdata):
            cdata = cdata.real
        self._c_data = cdata
        self._gl_solid_edgecolor = None

    def update_scalarmappable(self):
        if self._c_data is None:
            self._gl_solid_edgecolor = self.get_color()[0]
        if self._gl_solid_edgecolor is not None:
            f = cc.to_rgba(self._gl_solid_edgecolor)
            self._gl_edgecolor = np.tile(f, (len(self._gl_3dpath[2]), 1))
        else:
            self._gl_edgecolor = self.to_rgba(self._c_data)
            idx = (np.sum(self._gl_edgecolor[:, :3], 1) != 0.0)
            self._gl_edgecolor[idx, -1] = self._alpha

        Line3DCollection.update_scalarmappable(self)

    def make_hl_artist(self, container):
        hl = Line3DCollectionGL([], gl_3dpath=self._gl_3dpath,
                                gl_lighting=False, linewidth=5.0)
        container.add_collection(hl)
        hl.set_edgecolor(([0, 0, 0, 0.6],))
#        hl.set_edgecolor(([1, 1, 1, 0.5],))
        return [hl]

    @draw_wrap
    def draw(self, renderer):
        v = None
        if isSupportedRenderer(renderer):
            self._sort_zpos = None
            renderer.use_gl = True
            glcanvas = get_glcanvas()
            if self.axes is not None:
                tag = self.axes
                trans = self.axes.transAxes
            elif self.figure is not None:
                tag = self.figure
                trans = self.figure.transFigure

            do_proj = False
            if glcanvas.has_vbo_data(self):
                d = glcanvas.get_vbo_data(self)
                if self._update_v:
                    d[0]['v'].need_update = True
                    self._gl_facecolor = self.to_rgba(self._gl_3dpath[2])
                if self._update_ec:
                    d[0]['ec'].need_update = True
                    self._gl_edgecolor = self.to_rgba(self._gl_3dpath[2])
            if self._update_ec:
                self.update_scalarmappable()

            gc = renderer.new_gc()
            glcanvas.frame_request(self, trans)
#           if not glcanvas.has_vbo_data(self):
#           renderer.do_stencil_test = self.do_stencil_test
            glcanvas.start_draw_request(self)
            if self._gl_3dpath is not None:
                renderer.gl_draw_path_collection_e(
                    gc, None, self._gl_3dpath,
                    self.get_transforms(), self._gl_offset, None,
                    None, self._gl_edgecolor,
                    self._linewidths, self._linestyles,
                    self._antialiaseds, self._urls,
                    self._offset_position, lighting=self._gl_lighting,
                    stencil_test=self.do_stencil_test,
                    view_offset=self._gl_voffset)

#           renderer.do_stencil_test = False
            glcanvas.end_draw_request()
            gc.restore()

            self._update_ec = False
            self._update_v = False

            finish_gl_drawing(glcanvas, renderer, tag, trans)

            renderer.use_gl = False
        else:
            v = Line3DCollectionGL.draw(self, renderer)


def line_collection_3d_to_gl(obj):
    obj.__class__ = Line3DCollectionGL
    obj._gl_3dpath = None
    obj._gl_solid_edgecolor = None
    obj._c_data = None
    obj._update_ec = True
    obj._update_v = True
    obj._gl_lighting = False
    ArtGL.__init__(obj)
    return obj


class Poly3DCollectionGL(ArtGL, Poly3DCollection):
    def __init__(self, *args, **kargs):
        ArtGL.__init__(self, **kargs)

        self.do_stencil_test = True
        self._gl_offset = kargs.pop('gl_offset', (0, 0, 0.))
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_facecolor = kargs.pop('gl_facecolor', None)
        self._gl_edgecolor = kargs.pop('gl_edgecolor', None)
        self._gl_solid_facecolor = kargs.pop('gl_solid_facecolor', None)
        self._gl_solid_edgecolor = kargs.pop('gl_solid_edgecolor', None)
        self._gl_edge_idx = kargs.pop('gl_edge_idx', None)
        self._gl_shade = kargs.pop('gl_shade', 'smooth')
        self._gl_lighting = kargs.pop('gl_lighting', True)
        self._gl_facecolordata = kargs.pop('facecolordata', None)
        self._gl_voffset = kargs.pop('view_offset', (0, 0, 0, 0.))
        self._gl_array_idx = kargs.pop('array_idx', None)
        self._gl_use_pointfill = kargs.pop('use_pointfill', False)

        self._cz = None
        self._gl_cz = None
        self._update_ec = True
        self._update_fc = True
        self._update_v = True
        self._update_i = True
        self._update_a = True

        Poly3DCollection.__init__(self, *args, **kargs)

    def convert_2dpath_to_3dpath(self, z, zdir='z'):
        '''
        convert a path on flat surface
        to 3d path
        '''
        #print("calling convert 2dpath to 3dpath")
        x1 = []
        y1 = []
        z1 = []
        norms = []
        idxset = []
        idxbase = 0
        if zdir == 'x':
            norm = np.array([1., 0, 0.])
        elif zdir == 'y':
            norm = np.array([0., 1, 0.])
        else:
            norm = np.array([0., 0, 1.])

        txs, tys, tzs, ones = self._vec

        if hasattr(self, '_segis'):
            xyzlist = [(txs[si:ei], tys[si:ei], tzs[si:ei])
                       for si, ei in self._segis]
        else:
            xyzlist = [(txs[sl], tys[sl], tzs[sl]) for sl in
                       self._segslices]

        for v0, v1, v2 in xyzlist:
            x1.append(v0)
            y1.append(v1)
            idxset.append(np.arange(len(v0))+idxbase)
            z1.append(v2)
 #           norms.append(np.hstack([norm]*len(v0)))
            idxbase = len(v0)+idxbase

        x1 = np.hstack(x1)
        y1 = np.hstack(y1)
        z1 = np.hstack(z1)

#        norms = np.hstack(norms).reshape(-1, 3)
        X3D, Y3D, Z3D = juggle_axes(x1, y1, z1, zdir)
        norms = np.array([norm]).reshape(-1, 3)
        self._gl_3dpath = [X3D, Y3D, Z3D, norms, idxset]

    def make_hl_artist(self, container):
        hl = Poly3DCollectionGL([], gl_3dpath=self._gl_3dpath,
                                gl_lighting=False, linewidth=0)
        container.add_collection(hl)
        hl.set_facecolor(([0., 0., 0, 0.6],))
        hl.set_edgecolor(([1, 1, 1, 0.],))
        return [hl]

    def do_3d_projection(self):
        return 1

    '''
    def do_3d_projection(self, renderer):
        #        if not hasattr(renderer, 'use_gl'):
        if hasattr(renderer, '_gl_renderer'):
            return 1
        return Poly3DCollection.do_3d_projection(self, renderer)
    '''

    def set_cmap(self, *args, **kwargs):
        super(Poly3DCollectionGL, self).set_cmap(*args, **kwargs)
        self._update_fc = True
        self._update_ec = True

    def set_shade(self, value):
        self._gl_shade = value
        self._update_fc = True

    def get_shade(self):
        return self._gl_shade

    def set_edgecolor(self, colors):
        super(Poly3DCollectionGL, self).set_edgecolor(colors)
        if colors is None:
            colors = tuple()
        if len(colors) == 1:
            self._gl_solid_edgecolor = colors[0]
        else:
            self._gl_solid_edgecolor = None
        self._update_ec = True

    set_edgecolors = set_edgecolor

    def set_facecolor(self, colors):
        super(Poly3DCollectionGL, self).set_facecolor(colors)
        if colors is None:
            colors = tuple()
        if len(colors) == 1:
            self._gl_solid_facecolor = colors[0]
        else:
            self._gl_solid_facecolor = None
        self._update_fc = True
    set_facecolors = set_facecolor

    def get_facecolors(self):
        return self._facecolor3d
    get_facecolor = get_facecolors

    def get_edgecolors(self):
        return self._edgecolor3d
    get_edgecolor = get_edgecolors

    def set_facecolordata(self, data):
        self._gl_facecolordata = data

    def get_facecolordata(self):
        return self._gl_facecolordata
        pass

    def set_alpha(self, a):
        self._alpha = a
        if self._gl_solid_facecolor is not None:
            c = cc.to_rgba(self._gl_solid_facecolor, alpha=a)
            self._gl_solid_facecolor = c
#            self._update_fc = True
        if self._gl_solid_edgecolor is not None:
            c = cc.to_rgba(self._gl_solid_edgecolor, alpha=a)
            self._gl_solid_edgecolor = c
#            self._update_ec = True
        self._update_fc = True
        self._update_ec = True

    def get_alpha(self):
        return self._alpha

    def set_cz(self, cz):
        if cz is not None:
            self._gl_cz = cz
        else:
            self._gl_cz = False

    def update_scalarmappable(self):
        #print('update_scalarmappable', self._gl_solid_facecolor, self._gl_solid_edgecolor, self._gl_cz, self._gl_facecolordata)

        if self._gl_solid_facecolor is not None:
            f = cc.to_rgba(self._gl_solid_facecolor)
            self._gl_facecolor = np.tile(f, (len(self._gl_3dpath[2]), 1))
        else:
            if self._gl_cz:
                if self._gl_facecolordata is not None:
                    self._gl_facecolor = self.to_rgba(self._gl_facecolordata)
            elif self._gl_shade == 'flat':
                if self._gl_cz:
                    z = [np.mean(self._gl_3dpath[2][idx])
                         for idx in self._gl_3dpath[4]]
                else:
                    z = [np.mean(self._gl_cz[idx])
                         for idx in self._gl_3dpath[4]]
                z = np.array(z)
                self._gl_facecolor = self.to_rgba(z)
            else:
                if self._gl_cz is None:
                    self._gl_facecolor = self.to_rgba(self._gl_3dpath[2])
                else:
                    self._gl_facecolor = self.to_rgba(self._gl_cz)
            if self._alpha is not None:
                if self._gl_facecolor.ndim == 3:
                    self._gl_facecolor[:, :, -1] = self._alpha
                else:
                    self._gl_facecolor[:, -1] = self._alpha

        if self._gl_solid_edgecolor is not None:
            f = cc.to_rgba(self._gl_solid_edgecolor)
            self._gl_edgecolor = np.tile(f, (len(self._gl_3dpath[2]), 1))
        else:
            if self._gl_shade == False:
                z = [np.mean(self._gl_3dpath[2][idx])
                     for idx in self._gl_3dpath[4]]
                z = np.array(z)
                self._gl_edgecolor = self.to_rgba(z)
            else:
                if self._gl_cz is None:
                    self._gl_edgecolor = self.to_rgba(self._gl_3dpath[2])
                else:
                    self._gl_edgecolor = self.to_rgba(self._gl_cz)
            if self._alpha is not None:
                if self._gl_edgecolor.ndim == 3:
                    self._gl_edgecolor[:, :, -1] = self._alpha
                else:
                    self._gl_edgecolor[:, -1] = self._alpha

        #print('update_scalarmappable', self._gl_solid_facecolor, self._gl_solid_edgecolor, self._gl_cz, self._gl_facecolordata)
        #print('update_scalarmappable', self._gl_facecolor, self._gl_edgecolor)
        Poly3DCollection.update_scalarmappable(self)

    def update_idxset(self, idxset):
        self._gl_3dpath[4] = idxset
        self._update_i = True

    def update_edge_idxset(self, idxset):
        self._gl_edge_idx = idxset
        self._update_i = True

    @draw_wrap
    def draw(self, renderer):
        v = None
        if isSupportedRenderer(renderer):
            self._sort_zpos = None
            renderer.use_gl = True
            glcanvas = get_glcanvas()
            if self.axes is not None:
                tag = self.axes
                trans = self.axes.transAxes
            elif self.figure is not None:
                tag = self.figure
                trans = self.figure.transFigure

            if glcanvas.has_vbo_data(self):
                d = glcanvas.get_vbo_data(self)
                if self._gl_cz:
                    cz = self._gl_facecolordata
                elif self._gl_cz is not None:
                    cz = self._gl_cz
                else:
                    cz = self._gl_3dpath[2]

                if len(d) > 0 and d[0] is not None:
                    if self._update_v:
                        d[0]['v'].need_update = True
                        self._gl_facecolor = self.to_rgba(cz)
                    if self._update_fc:
                        d[0]['fc'].need_update = True
                        self._gl_facecolor = self.to_rgba(cz)
                    if self._update_ec:
                        d[0]['ec'].need_update = True
                        self._gl_edgecolor = self.to_rgba(cz)
                    if self._update_i:
                        d[0]['i'].need_update = True
                    if self._update_a:
                        if 'vertex_id' in d[0] and d[0]['vertex_id'] is not None:
                            d[0]['vertex_id'].need_update = True
                else:
                    self._update_a = False
                    self._update_v = False
                    self._update_fc = False
                    self._update_ec = False
                    self._update_i = False
                # this happens when all surfaces are hidden.
                # if (len(d)) == 0: print('vbo zero length', self.figobj)
            if self._update_ec or self._update_fc:
                self.update_scalarmappable()

            gc = renderer.new_gc()
            glcanvas.frame_request(self, trans)
#           renderer.do_stencil_test = self.do_stencil_test
            glcanvas.start_draw_request(self)
            if self._gl_3dpath is not None:
                if isinstance(self._gl_3dpath[4], list):
                    renderer.gl_draw_path_collection(
                        gc, None, self._gl_3dpath,
                        self.get_transforms(), self._gl_offset, None,
                        self._gl_facecolor, self._gl_edgecolor,
                        self._linewidths, self._linestyles,
                        self._antialiaseds, self._urls,
                        self._offset_position,
                        stencil_test=self.do_stencil_test,
                        view_offset=self._gl_voffset,
                        array_idx=self._gl_array_idx,
                        always_noclip=self._gl_always_noclip)

                else:
                    renderer.gl_draw_path_collection_e(
                        gc, None, self._gl_3dpath,
                        self.get_transforms(), self._gl_offset, None,
                        self._gl_facecolor, self._gl_edgecolor,
                        self._linewidths, self._linestyles,
                        self._antialiaseds, self._urls,
                        self._offset_position,
                        stencil_test=self.do_stencil_test,
                        view_offset=self._gl_voffset,
                        array_idx=self._gl_array_idx,
                        use_pointfill=self._gl_use_pointfill,
                        always_noclip=self._gl_always_noclip,
                        edge_idx=self._gl_edge_idx)

#           renderer.do_stencil_test = False
            glcanvas.end_draw_request()
            gc.restore()

            self._update_fc = False
            self._update_ec = False
            self._update_v = False
            self._update_i = False
            finish_gl_drawing(glcanvas, renderer, tag, trans)

            renderer.use_gl = False
        else:
            v = Collection.draw(self, renderer)
        return v


def poly_collection_3d_to_gl(obj):
    obj.__class__ = Poly3DCollectionGL
    obj.do_stencil_test = True
    obj._update_v = True
    obj._update_fc = True
    obj._update_ec = True
    obj._update_a = False
    obj._gl_solid_facecolor = None
    obj._gl_solid_edgecolor = None
    obj._gl_facecolor = None
    obj._gl_edgecolor = None
    obj._gl_shade = 'smooth'
    obj._gl_cz = None

    ArtGL.__init__(obj)
    return obj


class Polygon3DGL(ArtGL, Polygon):
    def __init__(self, xyz, **kargs):
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_lighting = kargs.pop('gl_lighting', True)
        xy = xyz[:, 0:2]
        Polygon.__init__(self, xy, **kargs)
        self.do_stencil_test = True
        self.set_3d_properties(zs=xyz[:, 2])

    def set_3d_properties(self, zs=0, zdir='z'):
        xs = self.get_xy()[:, 0]
        ys = self.get_xy()[:, 1]
        try:
            # If *zs* is a list or array, then this will fail and
            # just proceed to juggle_axes().
            zs = float(zs)
            zs = [zs for x in xs]
        except TypeError:
            pass
        self._verts3d = juggle_axes(xs, ys, zs, zdir)
        self._invalidz = True

    def do_3d_projection(self):
        #    def do_3d_projection(self, renderer):
        # I am not sure what I should return...
        return 1

    @draw_wrap
    def draw(self, renderer):
        if isSupportedRenderer(renderer):
            renderer.use_gl = True
            glcanvas = get_glcanvas()
            if self.axes is not None:
                tag = self.axes
                trans = self.axes.transAxes
            elif self.figure is not None:
                tag = self.figure
                trans = self.figure.transFigure

            gc = renderer.new_gc()
            rgbFace = self._facecolor
            gc.set_foreground(self._edgecolor, isRGBA=True)

            glcanvas.frame_request(self, trans)
#           if not glcanvas.has_vbo_data(self):
            glcanvas.start_draw_request(self)

            if self._invalidz:
                if glcanvas.has_vbo_data(self):
                    d = glcanvas.get_vbo_data(self)
                    d[0]['v'].need_update = True
            self._invalidz = False
            renderer.gl_draw_path(gc, self._verts3d,  trans,
                                  rgbFace=rgbFace,
                                  stencil_test=self.do_stencil_test)
#           glcanvas.update_gc(self, gc)
            glcanvas.end_draw_request()
#           else:
#              glcanvas.update_gc(self, gc)
            gc.restore()
            renderer.use_gl = False
            finish_gl_drawing(glcanvas, renderer, tag, trans)

        else:
            Polygon.draw(self, renderer)


def polygon_2d_to_gl(obj, zs, zdir):
    obj.__class__ = Polygon3DGL
    obj._invalidz = True
    obj.do_stencil_test = True
    obj._gl_lighting = True
    obj.set_3d_properties(zs=zs, zdir=zdir)
    return obj
