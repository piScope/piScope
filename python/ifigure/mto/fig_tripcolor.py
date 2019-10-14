from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.fig_image import FigImage
from ifigure.mto.triangle_plots import TrianglePlots
from ifigure.utils.cbook import ProcessKeywords
from matplotlib.tri import Triangulation
import numpy as np
import ifigure.events


class FigTripcolor(FigImage, TrianglePlots):
    '''
    tripcolor(x, y, z)
    tripcolor(tri, x, y, z)
    '''
    default_rasterized = True

    def __new__(self, *args, **kywds):
        if len(args) == 4:
            tri = args[0]
            args = args[1:]
        else:
            tri = None
        kywds['use_tri'] = True
        shading = kywds.pop('shading', "flat")
        mask = kywds.pop('mask', None)
        obj = FigImage.__new__(self, *args, **kywds)
        obj.setp('shading', shading)
        obj.setp('mask', mask)
        obj.setvar('shading', shading)
        obj.setvar('mask', mask)
        obj.setvar("tri", tri)
        return obj

    def __init__(self, *args,  **kywds):
        if len(args) == 4:
            tri = args[0]
            args = args[1:]
        else:
            tri = None
        FigImage.__init__(self, *args, **kywds)
        TrianglePlots.__init__(self)
        self._tri = tri

    @classmethod
    def isTripColor(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'tripcolor'

    @classmethod
    def attr_in_file(self):
        return (["alpha", "shading", "mask"] +
                super(FigImage, self).attr_in_file())

    @classmethod
    def property_in_palette(self):
        return ["cmap", "tripcolor_shading", "alpha_2"]
#    def set_shading(self, value, a):
#        self.setp('shading', value)
#        a.set_shading(value)
#    def get_shading(self, a):
#        return self.getp('interp')

    def onResize(self, evt):
        self.set_bmp_update(False)

        # self.del_artist(delall=True)
        # self.delp('loaded_property')
        #self.setp('use_var', False)
        # if hasattr(self, "_data_extent"):
        #   self._data_extent = None
        # self.generate_artist()

    def handle_axes_change(self, evt=None):
        return super(FigImage, self).handle_axes_change(evt)

    def set_alpha(self, value, a):
        a.set_alpha(value)
        cax = self.get_caxisparam()
        cax.set_crangeparam_to_artist(a)
        self.setp('alpha', value)
        self.set_bmp_update(False)

    def get_alpha(self, a):
        return a.get_alpha()

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if len(self._artists) == 0:
            return FigImage.get_crange(self, crange=crange,
                                       xrange=xrange, yrange=yrange,
                                       scale=scale)
        else:
            zt = self._artists[0].get_array()
            if scale == 'log':
                zt = mask_negative(zt)
            crange = self._update_range(crange,
                                        (min(zt), max(zt)))
        return crange

    def _eval_xyz(self):
        if self._tri is None:
            self._tri = self.getvar('tri')
        return FigImage._eval_xyz(self)

    def picker_a(self, artist, evt):
        '''
        this picker is faster since it judges based on
        x, y nodes. It does not look if the mouse is 
        inside the path. A user has to click the corner
        of triangles...
        '''
        x, y = self.getp(('x', 'y'))
        ptx = np.vstack((x.flatten(), y.flatten()))
        t = self._artists[0].axes.transData
        ptx = t.transform(ptx.transpose())
        dist = np.sqrt((ptx[:, 0] - evt.x) ** 2 + (ptx[:, 1] - evt.y)**2)
        if np.min(dist) < 5:
            self._pick_pos = [evt.xdata, evt.ydata]
            return True,  {'child_artist': artist}
        else:
            return False, {}
