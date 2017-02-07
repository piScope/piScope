import numpy as np

## matplotlib
from matplotlib._image import fromarray, frombyte
from matplotlib.colors import ColorConverter
from matplotlib.path import Path

cc = ColorConverter()

## mplot3d
from matplotlib.collections import Collection, LineCollection, \
        PolyCollection, PatchCollection, PathCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3D, Patch3D
from mpl_toolkits.mplot3d.art3d import PathPatch3D, juggle_axes
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import mpl_toolkits.mplot3d.proj3d as proj3d

##
from ifigure.utils.marker_image import marker_image
from ifigure.matplotlib_mod.backend_wxagg_gl import mixin_gl_renderer
from ifigure.matplotlib_mod.is_supported_renderer import isSupportedRenderer

## this magic number effectively scale and transpose
## an image produced by GL backend, so that it become
## consistent with the axes drawn by Axes3D.
frame_range = np.array([-0.095, -0.095, 1.1, 1.10])+0.01
#frame_range = np.array([0, 0, 1, 1])

def finish_gl_drawing(glcanvas, renderer, tag, trans):
    if not glcanvas._hittest_map_update:
        id_dict = glcanvas.draw_mpl_artists(tag)
        im = glcanvas.read_data(tag) # im : image, im2: id, im3: depth
        gc = renderer.new_gc()
        x, y =trans.transform(frame_range[0:2])
        im = frombyte(im, 1)
        im.is_grayscale = False ## do I have to be able to switch it...?
        renderer.draw_image(gc, round(x), round(y), im)
        gc.restore()
    else:
        id_dict = glcanvas.draw_mpl_artists(tag)
        im, im2, im3 = glcanvas.read_data(tag) # im : image, im2: id, im3: depth
        gc = renderer.new_gc()
        x, y =trans.transform(frame_range[0:2])
        im = frombyte(im, 1)
        im.is_grayscale = False ## do I have to be able to switch it...?

        if renderer.gl_svg_rescale:
           ### svg renderer has image_dpi = 100 (not 72)
           ### therefore width and height needs to be set
           x2, y2 =trans.transform(frame_range[2:])        
           renderer.draw_image(gc, round(x), round(y), im,
                               dx=round(x2-x), dy = round(y2-y))
        else:
           renderer.draw_image(gc, round(x), round(y), im)
        renderer.update_id_data((x, y, id_dict, im2, im3), tag = tag)
        gc.restore()

def get_glcanvas():
    from ifigure.matplotlib_mod.backend_wxagg_gl import FigureCanvasWxAggModGL
    return FigureCanvasWxAggModGL.glcanvas


class ArtGL(object):
    is_gl = True
    def __init__(self):
        self.is_last = False        
        self._gl_3dpath = None        
        self._gl_lighting = True
        self._gl_offset = (0, 0, 0.)
        self._gl_data_extent = None
        self._gl_hl = False

    def contains(self, evt):
        if self.axes is not None:
            c = self.axes
        elif self.figure is not None:
            c = self.figure
            
        check =  c.gl_hit_test(evt.x, evt.y, id(self), radius = 3)
        if check:
            return True, {'child_artist':self} 
        else:
            return False, {}
        
    def get_gl_data_extent(self):
        if self._gl_data_extent is None:
            try:
                self._gl_data_extent = [(np.nanmin(self._gl_3dpath[k]),
                                         np.nanmax(self._gl_3dpath[k])) for k in range(3)]

            except:
                import traceback
                traceback.print_exc()
                
        if self._gl_data_extent is None: return [None]*3
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
        if c is None: return
        c.set_gl_hl_mask(id(self))
        self._gl_hl = True
        return []
        
class LineGL(ArtGL, Line3D):
    def __init__(self, xdata, ydata, zdata,  **kargs):
        self._invalidz = False
        self._zorig = None
        self.is_last = True
        self._update_path = False
        self._facecolor = None
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
            idx  = np.arange(len(x), dtype = np.int)
            l = 0; indexset = []
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
                      norms.append([0,0,1])
                  else:
                      norms.append(n1/d)
                  norms = np.hstack(norms).astype(np.float32).flatten()
            x = np.hstack(x).flatten()
            y = np.hstack(y).flatten()
            z = np.hstack(z).flatten()
            self._gl_3dpath = (x, y, z, norms, indexset)

    def draw(self, renderer):
        if isSupportedRenderer(renderer):                        
           if self._invalidy or self._invalidx or self._invalidz:
               self.recache()
               if self.get_zdata() is None:
                   self._zorig = np.array([0]*len(self.get_xdata()))
#           print self._transform_path()
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
           
           #3dpath = (self.get_xdata(), self.get_ydata(), self_zdata())           
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
           ln_color_rgba = self._get_rgba_ln_color()
           gc.set_foreground(ln_color_rgba, isRGBA=True)
           gc.set_linewidth(self._linewidth)

           if self._marker.get_marker() == ',':
                gc.set_linewidth(0)

           if self._gl_3dpath is None:
                self.verts3d_to_3dpath()
           if len(self._gl_3dpath) == 3:
              renderer.gl_draw_path(gc, self._gl_3dpath,  trans,
                                    rgbFace = self._facecolor,
                                    linestyle = self._linestyle)
           else:
              fc = None if self._facecolor is None else [self._facecolor]
              renderer.gl_draw_path_collection_e(
                   gc, None, self._gl_3dpath,
                   None, self._gl_offset, None,
                   fc, [ln_color_rgba],
                   [self._linewidth], self._linestyle,
                   self._antialiased, self._url,
                   None, lighting = self._gl_lighting, 
                   stencil_test = False)
                             
           if len(self._marker.get_path()) != 0:
              marker_path = None
              marker_trans = None
              m_facecolor = self.get_markerfacecolor()
              m_edgecolor = self.get_markeredgecolor()
              m_edgewidth = self.get_markeredgewidth()
              m_size =  renderer.points_to_pixels(self._markersize)
              marker_path = marker_image(self._marker.get_path(),
                                      m_size, self._marker.get_transform(),
                                      edgecolor = m_edgecolor,
                                      facecolor = m_facecolor,
                                      edgewidth = m_edgewidth)
              #marker_path is bitmap (texture)
              #marker_trans is marker_size and other info (liken marker_every)
              marker_trans = (m_size,)
              renderer.gl_draw_markers(gc, marker_path, marker_trans,
                                 self._gl_3dpath[:3],  trans)           
#           glcanvas.update_gc(self, gc)
           glcanvas.end_draw_request()
#           else:
#              glcanvas.update_gc(self, gc)
           gc.restore()

           if self.is_last:
               finish_gl_drawing(glcanvas, renderer, tag, trans)
           renderer.use_gl = False
        else:
           v =  Line3D.draw(self, renderer)
#        return v

def line_3d_to_gl(obj):
    obj.__class__ = LineGL
    obj._invalidz = False
    obj._zorig = None
    obj._facecolor = None
    ArtGL.__init__(obj)    
    return obj
from matplotlib.image import AxesImage
class AxesImageGL(ArtGL, AxesImage):
    def __init__(self, *args, **kargs):
        ArtGL.__init__(self)
        AxesImage.__init__(self, *args, **kargs)
        self._gl_interp = 'nearest'
        self._gl_rgbacache_id = None
    def __repr__(self):
        return 'ImageGL'
    def set_3dpath(self, im_center, im_axes):
        '''
             p2---p3
         (y) |    |
             p0---p1
               (x)
        '''
        x1, x2, y1, y2 = self.get_extent()
        p = [im_center[0]+x1*np.array(im_axes[0]) + +y1*np.array(im_axes[1]),
             im_center[0]+x2*np.array(im_axes[0]) + +y1*np.array(im_axes[1]),
             im_center[0]+x2*np.array(im_axes[0]) + +y2*np.array(im_axes[1]),
             im_center[0]+x1*np.array(im_axes[0]) + +y2*np.array(im_axes[1]),]
        
        n = np.cross(im_axes[0], im_axes[1])
        x = np.array([pp[0] for pp in p]).flatten()
        y = np.array([pp[1] for pp in p]).flatten()
        z = np.array([pp[2] for pp in p]).flatten()
        self._gl_3dpath = (x, y, z, np.hstack([n]*len(x)),
                           np.arange(len(x)).astype(np.int))
        
    def make_hl_artist(self, container):
        idx = [0, 1, 2, 3]
        x  = [self._gl_3dpath[0][k] for k in idx]
        y  = [self._gl_3dpath[1][k] for k in idx]
        z  = [self._gl_3dpath[2][k] for k in idx]        
        hl = container.plot(x, y, zs = z)[0]
        hl.set_zdata(z)
        hl.set_color([0,0,0,1])
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
               trans = self.figure.transFpigure
           glcanvas.frame_request(self, trans)
#           if not glcanvas.has_vbo_data(self):
           glcanvas.start_draw_request(self)
#           print self._gl_rgbacache_id, id(self._rgbacache)
           if self._gl_3dpath is not None:
              im = self.make_image(renderer.get_image_magnification())
              gc = renderer.new_gc()              
              gc.set_alpha(self.get_alpha())
              if self._gl_rgbacache_id != id(self._rgbacache):
                 if glcanvas.has_vbo_data(self):                                   
                     d = glcanvas.get_vbo_data(self)
                     for x in d:
                         x['im_update'] = True              
              renderer.gl_draw_image(gc, self._gl_3dpath,  trans,
                                     np.transpose(self._rgbacache, (1,0,2)),
                                     interp = self._gl_interp)
              self._gl_rgbacache_id = id(self._rgbacache)
              gc.restore()
           else:
              pass
           glcanvas.end_draw_request()
           if self.is_last:
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
        
        self.is_last = False
        self.do_stencil_test = True
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_offset = kargs.pop('gl_offset', (0, 0, 0.))
        self._gl_edgecolor = kargs.pop('gl_edgecolor', None)
        self._c_data = kargs.pop('c_data', None)
        self._gl_solid_edgecolor = kargs.pop('gl_solid_edgecolor', None)
        self._gl_lighting = kargs.pop('gl_lighting', True)        
        self._update_ec = True
        self._update_v = True
        Line3DCollection.__init__(self, *args, **kargs)
        
    def convert_2dpath_to_3dpath(self, z=None, zdir = 'z'):

        x1 = []; y1 = []; z1 =[]; norms = []; idxset = []
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
            xyzlist.append((points[:,0], points[:, 1], points[:,2],))
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
        
        ##does norm may mean anything, but let's leave it...        
        self._gl_3dpath = [X3D, Y3D, Z3D, norms, idxset]
        
    def set_cmap(self, *args, **kwargs):
        super(Line3DCollectionGL, self).set_cmap(*args, **kwargs)
        self._update_ec = True
    
    def set_color(self, colors):
        super(Line3DCollectionGL, self).set_color(colors)
        if colors is None: colors = tuple()
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
            c = cc.to_rgba(self._gl_solid_edgecolor, alpha = a)
            self._gl_solid_edgecolor = c
        self._update_ec = True
        
    def get_alpha(self):
        return self._alpha

    def seg_c_data(self, cdata):
        self._c_data  = cdata
        self._gl_solid_edgecolor = None
        
    def update_scalarmappable(self):
        if self._c_data is None:
            self._gl_solid_edgecolor = self.get_color()[0]
        if self._gl_solid_edgecolor is not None:
            f = cc.to_rgba(self._gl_solid_edgecolor)
            self._gl_edgecolor = np.tile(f, (len(self._gl_3dpath[2]),1))        
        else:
            self._gl_edgecolor = self.to_rgba(self._c_data)
            idx = (np.sum(self._gl_edgecolor[:,:3],1) != 0.0)
            self._gl_edgecolor[idx,-1]=self._alpha

        Line3DCollection.update_scalarmappable(self)
        
    def make_hl_artist(self, container):
        hl = Line3DCollectionGL([], gl_3dpath = self._gl_3dpath,
                                gl_lighting = False, linewidth = 5.0)
        container.add_collection(hl)
        hl.set_edgecolor(([0,0,0, 0.6],))
#        hl.set_edgecolor(([1, 1, 1, 0.5],))
        return [hl]

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
                   self._offset_position, lighting = self._gl_lighting, 
                   stencil_test = self.do_stencil_test)
#           renderer.do_stencil_test = False
           glcanvas.end_draw_request()
           gc.restore()
           
           self._update_ec = False
           self._update_v = False

           if self.is_last:
               finish_gl_drawing(glcanvas, renderer, tag, trans)

           renderer.use_gl = False        
        else:
           v =  Line3DCollectionGL.draw(self, renderer)

def line_collection_3d_to_gl(obj):
    obj.__class__ = Line3DCollectionGL
    obj._gl_offset = (0, 0, 0.)
    obj._gl_3dpath = None
    obj._gl_solid_edgecolor = None
    obj._c_data = None
    obj._update_ec = True
    obj._update_v = True
    obj._gl_lighting = False
    return obj

class Poly3DCollectionGL(ArtGL, Poly3DCollection):
    def __init__(self, *args, **kargs):
        ArtGL.__init__(self)

        self.is_last = False
        self.do_stencil_test = True
        self._gl_offset = kargs.pop('gl_offset', (0, 0, 0.))
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_facecolor = kargs.pop('gl_facecolor',  None)
        self._gl_edgecolor = kargs.pop('gl_edgecolor', None)
        self._gl_solid_facecolor = kargs.pop('gl_solid_facecolor', None)
        self._gl_solid_edgecolor = kargs.pop('gl_solid_edgecolor', None)
        self._gl_shade = kargs.pop('gl_shade', 'smooth')
        self._gl_lighting = kargs.pop('gl_lighting', True)
        self._gl_facecolordata = kargs.pop('facecolordata', None)
        self._cz = None
        self._gl_cz = None
        self._update_ec = True
        self._update_fc = True
        self._update_v = True

        Poly3DCollection.__init__(self, *args, **kargs)
        

    def convert_2dpath_to_3dpath(self, z, zdir = 'z'):
        '''
        convert a path on flat surface
        to 3d path
        '''
        x1 = []; y1 = []; z1 =[]; norms = []; idxset = []
        idxbase = 0
        if zdir == 'x':
            norm = np.array([1., 0, 0.])
        elif zdir == 'y':
            norm = np.array([0., 1, 0.])
        else:
            norm = np.array([0., 0, 1.])

        txs, tys, tzs, ones = self._vec
        xyzlist = [(txs[si:ei], tys[si:ei], tzs[si:ei]) \
                for si, ei in self._segis]
            
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
        hl = Poly3DCollectionGL([], gl_3dpath = self._gl_3dpath,
                                gl_lighting = False, linewidth=0)                                
        container.add_collection(hl)
        hl.set_facecolor(([0.,0., 0, 0.6],))
        hl.set_edgecolor(([1, 1, 1, 0.],))        
        return [hl]
    
    def do_3d_projection(self, renderer):
#        if not hasattr(renderer, 'use_gl'):
        if hasattr(renderer, '_gl_renderer'): return             
        Poly3DCollection.do_3d_projection(self,renderer)
      
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
        if colors is None: colors = tuple()
        if len(colors) == 1:
            self._gl_solid_edgecolor = colors[0]
        else:
            self._gl_solid_edgecolor = None
        self._update_ec = True
        
    set_edgecolors = set_edgecolor
    def set_facecolor(self, colors):
        super(Poly3DCollectionGL, self).set_facecolor(colors)
        if colors is None: colors = tuple()
        if len(colors) == 1:
            self._gl_solid_facecolor = colors[0]
        else:
            self._gl_solid_facecolor = None
        self._update_fc = True
    set_facecolors = set_facecolor
    
    def get_facecolors(self):
        return self._facecolors3d
    get_facecolor = get_facecolors

    def get_edgecolors(self):
        return self._edgecolors3d
    get_edgecolor = get_edgecolors    

    def set_facecolordata(self, data):
        self._gl_facecolordata = data

    def get_facecolordata(self):
        return self._gl_facecolordata
        pass

    def set_alpha(self, a):
        self._alpha = a
        if self._gl_solid_facecolor is not None:
            c = cc.to_rgba(self._gl_solid_facecolor, alpha = a)
            self._gl_solid_facecolor = c
#            self._update_fc = True
        if self._gl_solid_edgecolor is not None:
            c = cc.to_rgba(self._gl_solid_edgecolor, alpha = a)
            self._gl_solid_edgecolor = c
#            self._update_ec = True
        self._update_fc = True            
        self._update_ec = True            

    def get_alpha(self):
        return self._alpha

    def set_cz(self, cz):
        if cz is not None:
            if hasattr(self, '_segis'):
                self._gl_cz = np.hstack([cz[si:ei] for si, ei in self._segis])
            else:
                self._gl_cz = cz
        else:
            self._gl_cz = None

    def update_scalarmappable(self):
        if self._gl_solid_facecolor is not None:
            f = cc.to_rgba(self._gl_solid_facecolor)
            self._gl_facecolor = np.tile(f, (len(self._gl_3dpath[2]),1))        
        else:
            if self._gl_cz:
                if self._gl_facecolordata is not None:
                   self._gl_facecolor = self.to_rgba(self._gl_facecolordata)
            elif self._gl_shade == False:
                if self._gl_cz is None:
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
                self._gl_facecolor[:,-1]=self._alpha
            
        if self._gl_solid_edgecolor is not None:
            f = cc.to_rgba(self._gl_solid_edgecolor)
            self._gl_edgecolor = np.tile(f, (len(self._gl_3dpath[2]),1))        
        else:
            if self._gl_shade == False:
                z = [np.mean(self._gl_3dpath[2][idx])
                      for idx in self._gl_3dpath[4]]
                z = np.array(z)
                self._gl_edgecolor = self.to_rgba(z)
            else:                
                self._gl_edgecolor = self.to_rgba(self._gl_3dpath[2])
            if self._alpha is not None:                
                self._gl_edgecolor[:,-1]=self._alpha

        Poly3DCollection.update_scalarmappable(self)

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
               elif self._gl_cz is not None: cz = self._gl_cz
               else: cz = self._gl_3dpath[2]
               if self._update_v:
                   d[0]['v'].need_update = True
                   self._gl_facecolor = self.to_rgba(cz)
               if self._update_fc:
                   d[0]['fc'].need_update = True
                   self._gl_facecolor = self.to_rgba(cz)
               if self._update_ec:
                   d[0]['ec'].need_update = True
                   self._gl_edgecolor = self.to_rgba(cz)
           if self._update_ec or self._update_fc:
               self.update_scalarmappable()

           gc = renderer.new_gc()               
           glcanvas.frame_request(self, trans)
#           renderer.do_stencil_test = self.do_stencil_test
           glcanvas.start_draw_request(self)
           if self._gl_3dpath is not None:
                renderer.gl_draw_path_collection_e(
                   gc, None, self._gl_3dpath,
                   self.get_transforms(), self._gl_offset, None,
                   self._gl_facecolor, self._gl_edgecolor,
                   self._linewidths, self._linestyles,
                   self._antialiaseds, self._urls,
                    self._offset_position, stencil_test = self.do_stencil_test)

#           renderer.do_stencil_test = False
           glcanvas.end_draw_request()
           gc.restore()
           
           self._update_fc = False
           self._update_ec = False
           self._update_v = False

           if self.is_last:
               finish_gl_drawing(glcanvas, renderer, tag, trans)

           renderer.use_gl = False
        else:
           v =  Collection.draw(self, renderer)
        return v


def poly_collection_3d_to_gl(obj):
    obj.__class__ = Poly3DCollectionGL
    obj.do_stencil_test = True
    obj._update_v = True
    obj._update_fc = True
    obj._update_ec = True
    obj._gl_solid_facecolor = None
    obj._gl_solid_edgecolor = None
    obj._gl_facecolor = None
    obj._gl_edgecolor = None
    obj._gl_shade = 'smooth'
    obj._gl_cz = None

    ArtGL.__init__(obj)
    return obj

from matplotlib.patches import Polygon

class Polygon3DGL(ArtGL, Polygon):
    def __init__(self, xyz, **kargs):
        self._gl_3dpath = kargs.pop('gl_3dpath', None)
        self._gl_lighting = kargs.pop('gl_lighting', True)
        xy = xyz[:,0:2]
        Polygon.__init__(self, xy, **kargs)
        self.is_last = False
        self.do_stencil_test = True
        self.set_3d_properties(zs = xyz[:,2])
        
    def set_3d_properties(self, zs=0, zdir='z'):
        xs = self.get_xy()[:,0]
        ys = self.get_xy()[:,1]
        try:
            # If *zs* is a list or array, then this will fail and
            # just proceed to juggle_axes().
            zs = float(zs)
            zs = [zs for x in xs]
        except TypeError:
            pass
        self._verts3d = juggle_axes(xs, ys, zs, zdir)
        self._invalidz = True
        
    def do_3d_projection(self, renderer):
        pass

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
                              rgbFace = rgbFace,
                              stencil_test = self.do_stencil_test)
#           glcanvas.update_gc(self, gc)
           glcanvas.end_draw_request()
#           else:
#              glcanvas.update_gc(self, gc)
           gc.restore()
           renderer.use_gl = False
           if self.is_last:
               finish_gl_drawing(glcanvas, renderer, tag, trans)

        else:
            Polygon.draw(self, renderer)

def polygon_2d_to_gl(obj, zs, zdir):
    obj.__class__ = Polygon3DGL
    obj.is_last = False
    obj._invalidz = True
    obj.do_stencil_test = True
    obj._gl_lighting = True    
    obj.set_3d_properties(zs = zs, zdir=zdir)
    return obj
