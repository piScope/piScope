from fig_surface import FigSurface
from ifigure.utils.triangulation_wrapper import tri_args
from matplotlib import cm
import numpy as np

class FigTrisurface(FigSurface):
    def __new__(self, *argc, **kywds):
        if len(argc) == 2 or len(argc) == 4:
            tri = argc[0]            
            argc = argc[1:]
        else:
            tri = None
        cz = kywds.pop('cz', None)
        obj = FigSurface.__new__(self, *argc, **kywds)

        return obj

    def __init__(self, *argc, **kywds):
        if len(argc) == 2 or len(argc) == 4:        
            tri = argc[0]            
            argc = argc[1:]
        else:
            tri = None
        cz = kywds.pop('cz', None)
        if tri is not None: self.setvar('tri', tri)
        if cz is not None: self.setvar('cz', cz)
        return FigSurface.__init__(self, *argc, **kywds)

    def _args2var(self):
        names0 = self.attr_in_file()
        names  = ["x","y", "z"]
        use_np = [True]*3
        names  = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)
        x = values[0];y = values[1];z=values[2]
        if x is None and y is None and z.ndim ==2:
            xtmp = np.arange(z.shape[1])
            ytmp = np.arange(z.shape[0])
            x, y = np.meshgrid(xtmp, ytmp)
            self.setp("x", x)
            self.setp("y", y)
        if x is None and y is None and z.ndim == 1:
            self.setp("x", None)
            self.setp("y", None)
            self.setp("z", z)
            return True
        if x is None: return False
        if y is None: return False
        if z is None:
           z = np.array([0]*len(x))
        if len(z) == 1:
           z = np.array([z[0]]*len(x))
        self.setp("z", z)
        return True

    def generate_artist(self):
        if self.isempty() is False: return

        axes = self.get_figaxes()
        if not axes.get_3d(): return

        container=self.get_container()
        x, y, z = self._eval_xy()
        ### use_var should be false if evaluation is
        ### okey.
        if self.getp('use_var'): return

        kywds = self._var["kywds"]

        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return

        kywds['alpha'] = self.getp('alpha')
        if (not 'color' in kywds and
            not 'facecolors' in kywds):
            cmap = self.get_cmap()
            kywds['cmap'] = cm.get_cmap(cmap)

        if self.hasvar('tri'):
            args = (self.getvar('tri'), z)
        else:
            args = (x, y, z)
        if self.hasvar('cz'):
            kywds['cz'] = self.getvar('cz')
        kywds['edgecolor'] = self.getvar('edgecolor')
        kywds['linewidth'] = self.getvar('linewidth')        
        self._artists = [container.plot_trisurf(*args, **kywds)]       

        for artist in self._artists:
            artist.do_stencil_test = False
            artist.figobj=self
            artist.figobj_hl=[]
            artist.set_zorder(self.getp('zorder'))
            cax.set_crangeparam_to_artist(artist)
            
    def get_xrange(self, xrange=[None,None], scale = 'linear'):
        if self.hasvar('tri'):
            tri = self.getvar('tri')
            return self._update_range(xrange, (np.nanmin(tri.x), np.nanmax(tri.x)))
        else:
            return super(FigTrisurface, self).get_xrange(xrange=xrange,
                                                         scale = 'linear')

    def get_yrange(self, yrange=[None,None], xrange=[None, None], scale = 'linear'):
        if self.hasvar('tri'):
            tri = self.getvar('tri')
            return self._update_range(yrange, (np.nanmin(tri.y), np.nanmax(tri.y)))
        else:
            return super(FigTrisurface, self).get_yrange(yrange=yrange,
                                           xrange=xrange, scale = 'linear')
    def get_zrange(self, zrange=[None,None], 
                         xrange=[None,None], 
                         yrange=[None,None],
                         scale = 'linear'):
        if self.hasvar('tri'):
            x, y, z = self._eval_xy()
            return self._update_range(zrange, (np.min(z), np.max(z)))
        else:
            return super(FigTrisurface, self).get_zrange(zrange=zrange,
                                                         xrange=xrange,
                                                         yrange=yrange,
                                                         scale = 'linear')
    def get_crange(self, crange=[None,None], 
                         xrange=[None,None], 
                         yrange=[None,None],
                         scale = 'linear'):
        if self.hasvar('cz'):
            cz = self.getvar('cz')
            return self._update_range(crange, (np.min(cz), np.max(cz)))
        if self.hasvar('tri'):
            x, y, z = self._eval_xy()
            return self._update_range(crange, (np.min(z), np.max(z)))
        else:
            return super(FigTrisurface, self).get_crange(crange=crange,
                                                         xrange=xrange,
                                                         yrange=yrange,
                                                         scale = 'linear')

        
