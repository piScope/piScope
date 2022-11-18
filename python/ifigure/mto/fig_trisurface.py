import numpy as np
from matplotlib import cm
from ifigure.mto.fig_surface import FigSurface
from ifigure.utils.triangulation_wrapper import tri_args
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ColorConverter
cc = ColorConverter()


class FigTrisurface(FigSurface):
    def __new__(self, *argc, **kywds):
        if len(argc) == 2 or len(argc) == 4:
            tri = argc[0]
            argc = argc[1:]
        else:
            tri = None
        obj = FigSurface.__new__(self, *argc, **kywds)

        if not hasattr(obj, '_tri'):
            obj._tri = None

        return obj

    def __init__(self, *argc, **kywds):
        if len(argc) == 2 or len(argc) == 4:
            tri = argc[0]
            argc = argc[1:]
        else:
            tri = None
        if tri is not None:
            self.setvar('tri', tri)
        return FigSurface.__init__(self, *argc, **kywds)

    @classmethod
    def get_namebase(self):
        return 'trisurface'

    @classmethod
    def property_in_palette(self):
        return ["facecolor_2",
                "edgecolor_2", "linewidthz", "solid_shade",
                "alpha_2"]

    def _args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y", "z"]
        use_np = [True]*3
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)
        x = values[0]
        y = values[1]
        z = values[2]
        if x is None and y is None and z.ndim == 2:
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
        if x is None:
            return False
        if y is None:
            return False
        if z is None:
            z = np.array([0]*len(x))
        if len(z) == 1:
            z = np.array([z[0]]*len(x))
        self.setp("z", z)
        return True

    def generate_artist(self):
        if self.isempty() is False:
            return

        axes = self.get_figaxes()
        if not axes.get_3d():
            return

        container = self.get_container()
        x, y, z = self._eval_xy()
        # use_var should be false if evaluation is
        # okey.
        if self.getp('use_var'):
            return

        kywds = self._var["kywds"]

        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return
        # if self.getp('alpha') is not None else 1
        kywds['alpha'] = self.getp('alpha')

        fc = self.getp('facecolor')
        if isinstance(fc, str):
            fc = cc.to_rgba(fc)
        if fc is None:
            fc = [0, 0, 0, 0]
        else:
            fc = list(fc)
            if self.getp('alpha') is not None:
                fc[3] = self.getp('alpha')
        ec = self.getp('edgecolor')
        if isinstance(ec, str):
            ec = cc.to_rgba(ec)
        if ec is None:
            ec = [0, 0, 0, 0]
        else:
            ec = list(ec)
            if self.getp('alpha') is not None:
                ec[3] = self.getp('alpha')
        cz = self.getvar('cz')
        if cz is None:
            kywds['cz'] = False
        else:
            kywds['cz'] = cz
        if kywds['cz']:
            kywds['cdata'] = self.getvar('cdata')
        kywds['facecolor'] = (fc,)
        kywds['edgecolor'] = (ec,)
        kywds['linewidths'] = 0.0 if self.getp(
            'linewidth') is None else self.getp('linewidth')
        kywds['shade'] = self.getvar('shade')

        args, self._tri = tri_args(x, y, self._tri)
        args.append(z.flatten().astype(float))
        # if self.hasvar('tri'):
        #    args = (self.getvar('tri'), z)
        # else:
        #    args = (x, y, z)
        self._artists = [container.plot_trisurf(*args, **kywds)]

        for artist in self._artists:
            artist.do_stencil_test = False
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))
            if self.getvar('cz'):
                cax = self.get_caxisparam()
                if cax is None:
                    dprint1('Error: cax is None')
                cax.set_crangeparam_to_artist(artist)

    def get_xrange(self, xrange=[None, None], scale='linear'):
        if self.hasvar('tri'):
            tri = self.getvar('tri')
            return self._update_range(xrange, (np.nanmin(tri.x), np.nanmax(tri.x)))
        else:
            return super(FigTrisurface, self).get_xrange(xrange=xrange,
                                                         scale='linear')

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        if self.hasvar('tri'):
            tri = self.getvar('tri')
            return self._update_range(yrange, (np.nanmin(tri.y), np.nanmax(tri.y)))
        else:
            return super(FigTrisurface, self).get_yrange(yrange=yrange,
                                                         xrange=xrange, scale='linear')

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if self.hasvar('tri'):
            x, y, z = self._eval_xy()
            return self._update_range(zrange, (np.min(z), np.max(z)))
        else:
            return super(FigTrisurface, self).get_zrange(zrange=zrange,
                                                         xrange=xrange,
                                                         yrange=yrange,
                                                         scale='linear')
    '''    
    def get_crange(self, crange=[None,None], 
                         xrange=[None,None], 
                         yrange=[None,None],
                         scale = 'linear'):
        cdata = self.getvar('cdata')
        cz = self.getvar('cz')
        if not cz: return crange
        if cdata is None:
            x, y, z = self._eval_xy()
            crange = self._update_range(crange,
                             (np.nanmin(z), np.nanmax(z)))

        else:
            if np.iscomplexobj(cdata):
                tmp  = np.max(np.abs(cdata))
                crange = self._update_range(crange,
                                    (-tmp, tmp))

            else:
                crange = self._update_range(crange,
                                    (np.nanmin(cdata), np.nanmax(cdata)))

        return crange

    '''
