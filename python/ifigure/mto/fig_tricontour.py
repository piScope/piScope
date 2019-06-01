from ifigure.mto.fig_contour import FigContour
from ifigure.mto.triangle_plots import TrianglePlots
from ifigure.utils.cbook import ProcessKeywords
from matplotlib.tri import Triangulation
import numpy as np
import ifigure.events


class FigTricontour(FigContour, TrianglePlots):
    '''
        tricontour : contour plot using triangulation
        tricontour(x, y, z, n)  
        tricontour(x, y, z, v)  
        tricontour(tri, x, y, z, v)  
        tricontour(tri, x, y, z, n)  

        n: number of levels
        v: a list of contour levels
    '''
    default_rasterized = True

    def __new__(self, *args, **kywds):
        if len(args) == 5:
            tri = args[0]
            args = args[1:]
        else:
            tri = None
        kywds['use_tri'] = True
        mask = kywds.pop('mask', None)
        obj = FigContour.__new__(self, *args, **kywds)
        obj.setp('mask', mask)
        obj.setvar('mask', mask)
        return obj

    def __init__(self, *args,  **kywds):
        if len(args) == 4:
            tri = args[0]
            args = args[1:]
        else:
            tri = None
        kywds['use_tri'] = True
        FigContour.__init__(self, *args, **kywds)
        TrianglePlots.__init__(self)
        self._tri = tri

    @classmethod
    def isTripContour(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'tricontour'

#    @classmethod
#    def attr_in_file(self):
#        return  (["alpha", "shading", "mask"] +
#                super(FigImage, self).attr_in_file())
#    @classmethod
#    def property_in_palette(self):
#        return ["cmap","tripcolor_shading", "alpha_2"]

    def onResize(self, evt):
        self.set_bmp_update(False)

        # self.del_artist(delall=True)
        # self.delp('loaded_property')
        #self.setp('use_var', False)
        # if hasattr(self, "_data_extent"):
        #   self._data_extent = None
        # self.generate_artist()

    def handle_axes_change(self, evt=None):
        return super(FigContour, self).handle_axes_change(evt)

    def set_alpha(self, value, a):
        a.set_alpha(value)
        cax = self.get_caxisparam()
        cax.set_crangeparam_to_artist(a)
        self.setp('alpha', value)
        self.set_bmp_update(False)

    def get_alpha(self, a):
        return a.get_alpha()
