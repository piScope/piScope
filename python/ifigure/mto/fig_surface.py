import ifigure.utils.debug as debug
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile, isdynamic
from matplotlib.tri import Triangulation
from ifigure.matplotlib_mod.triplot_mod import triplot
from ifigure.utils.args_parser import ArgsParser
from matplotlib.colors import Normalize, colorConverter, LightSource, Colormap
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ColorConverter

from ifigure.mto.axis_param import get_cmap

cc = ColorConverter()


dprint1, dprint2, dprint3 = debug.init_dprints('FigSurface')


def _reduce_size(X, Y, Z, rstride, cstride):
    rows, cols = Z.shape
    # Force X and Y to take the same shape.
    # If they can not be fitted to that shape,
    # then an exception is automatically thrown.
    X.shape = (rows, cols)
    Y.shape = (rows, cols)

    # We want two sets of lines, one running along the "rows" of
    # Z and another set of lines running along the "columns" of Z.
    # This transpose will make it easy to obtain the columns.
    rii = range(0, rows, rstride)
    cii = range(0, cols, cstride)

    # Add the last index only if needed
    if rows > 0 and rii[-1] != (rows - 1):
        rii += [rows-1]
    if cols > 0 and cii[-1] != (cols - 1):
        cii += [cols-1]
    return X[rii][:, cii],  Y[rii][:, cii], Z[rii][:, cii]

#from mpl_toolkits.axes_grid1.inset_locator import inset_axes


class FigSurface(FigObj, XUser, YUser, ZUser, CUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._data_extent = None
            obj._coarse_artist = None
            obj._fine_artist = None
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', None, ['iter|nonstr', 'dynamic'])
        p.add_opt('y', None, ['iter|nonstr', 'dynamic'])
        p.add_var('z', ['iter|nonstr', 'dynamic'])

        p.add_key('cmap', None)
        p.add_key('shade', 'flat')
        p.add_key('linewidth', 1.0)
        p.add_key('alpha', None)
        p.add_key('rstride', 1)
        p.add_key('cstride', 1)
        p.add_key('edgecolor', 'k')
        p.add_key('facecolor', 'b')
        p.add_key('cz', not 'color' in kywds)
        p.add_key('cdata', None)

        p.set_pair("x", "y")
        p.set_ndconvert("x", "y", "z")
        p.set_squeeze_minimum_1D("x", "y", "z")

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)

        obj = set_hidden_vars(obj)
        if v['cmap'] is not None:
            if isinstance(v['cmap'], Colormap):
                v['cmap'] = v['cmap'].name
            kywds['cmap'] = v['cmap']
            del v['cmap']

        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args,  **kywds):
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)
        CUser.__init__(self)

        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigSurface, self).__init__(*args, **kywds)
        self._method = 'plot_surface'

    @classmethod
    def get_namebase(self):
        return 'surface'

    @classmethod
    def property_in_palette(self):
        return ["facecolor_2", "edgecolor_2", "linewidthz", "solid_shade",
                "alpha_2", "noclip3d"]

    @classmethod
    def attr_in_file(self):
        return (["cmap", "cstride", "rstride", "shade", "alpha",
                 "edgecolor", "linewidth", "facecolor"] +
                super(FigSurface, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'surf.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)

        super(FigSurface, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)
        CUser.get_caxisparam(self)

    def args2var(self):
        ret = self._args2var()
        if ret:
            if 'cmap' in self.getvar("kywds"):
                cax = self.get_caxisparam()
                cax.set_cmap(self.getvar('kywds')['cmap'])
        return ret

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
        if x is None and y is None:
            xtmp = np.arange(z.shape[1])
            ytmp = np.arange(z.shape[0])
            x, y = np.meshgrid(xtmp, ytmp)
            self.setp("x", x)
            self.setp("y", y)
        if (x.ndim == 1 and
                y.ndim == 1):
            x, y = np.meshgrid(x, y)
            self.setp("x", x)
            self.setp("y", y)
        if (x.ndim != 2 or
            y.ndim != 2 or
                z.ndim != 2):
            return False

        if x is None:
            return False
        if y is None:
            return False
        if z is None:
            return False

        return True

    def generate_artist(self, coarse=False):
        if (self.isempty() is False
                and not coarse):
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

        kywds = self._var["kywds"].copy()

        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return

        kywds['alpha'] = self.getp('alpha')
        ### stride is handled in fig_surface
        kywds['cstride'] = self.getvar('cstride')
        kywds['rstride'] = self.getvar('rstride')
        if coarse:
            f = ifigure._visual_config["3d_rot_accel_factor"]
        else:
            f = 1
        x, y, z = _reduce_size(x, y, z,
                               self.getp('cstride')*f,
                               self.getp('rstride')*f)

        if (not 'color' in kywds and
                not 'facecolors' in kywds):
            cmap = self.get_cmap()
            kywds['cmap'] = get_cmap(cmap)

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

        m = getattr(container, self._method)
        self._artists = [m(x, y, z, **kywds)]
        self._fine_artist = self._artists[0]

        for artist in self._artists:
            artist.do_stencil_test = False
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))
            self._objs.append(weakref.ref(artist))
            cax.set_crangeparam_to_artist(artist)

    def switch_scale(self, level='fine'):
        return
        col = self.get_figaxes()._artists[0].collections
        if self._coarse_artist is None:
            self._coarse_artist = self.generate_artist(coarse=True)
            self._coarse_artist.figobj = self

        dprint1('collection ', col)
        if level == 'fine':
            if self._coarse_artist in col:
                col.remove(self._coarse_artist)
            if not self._fine_artist in col:
                col.append(self._fine_artist)
            self._artists[0] = self._fine_artist
        elif level == 'coarse':
            if self._fine_artist in col:
                col.remove(self._fine_artist)
            if not self._coarse_artist in col:
                col.append(self._coarse_artist)
            self._artists[0] = self._coarse_artist

    def del_artist(self, artist=None, delall=False):
        if (len(self._artists) == 1 and
                self._artists[0] != self._fine_artist):
            self.switch_scale(level='fine')

        artistlist = self._artists
        self.store_loaded_property()

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                # GL canvas check this if artist is still alive.
                a.axes = None
                try:
                    a.set_figure(None)
                except:
                    a.figure = None
                try:
                    a.remove()
                except:
                    dprint1("remove failed")

        if self._coarse_artist is not None:
            col = self.get_figaxes()._artists[0].collections
            if self._coarse_artist in col:
                self._coarse_artist.remove()
            self._coarse_artist.figobj = None
            self._coarse_artist = None
        self._fine_artist = None
        super(FigSurface, self).del_artist(artistlist)

    def get_mappable(self):
        return [a for a in self._artists if isinstance(a, ScalarMappable)]

    def highlight_artist(self, val, artist=None):
        from ifigure.matplotlib_mod.art3d_gl import Poly3DCollectionGL
        figure = self.get_figpage()._artists[0]
        ax = self.get_figaxes()
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        if val == True:
            if self._parent is None:
                return
            container = self.get_container()
            if container is None:
                return

            de = self.get_data_extent()
            x = (de[0], de[1], de[1], de[0], de[0])
            y = (de[2], de[2], de[3], de[3], de[2])

            facecolor = 'k'
            if isinstance(alist[0], Poly3DCollectionGL):
                hl = alist[0].add_hl_mask()
#               hl = alist[0].make_hl_artist(container) # slower
                facecolor = 'none'
            else:
                hl = []

            for item in hl:
                alist[0].figobj_hl.append(item)

        else:
            for a in alist:
                if len(a.figobj_hl) == 0:
                    continue
                for hl in a.figobj_hl:
                    hl.remove()
                a.figobj_hl = []

#
#   Setter/Getter
#
    def set_cmap(self, value, a):
        a.set_cmap(et_cmap(value))
        self.setp('cmap', value)
        ca = self.get_caxisparam()
        ca.set_cmap(value)
        if self.has_cbar():
            ca.update_cb()

    def get_cmap(self, a=None):
        ca = self.get_caxisparam()
        return ca.cmap

    def set_alpha(self, value, a):
        a.set_alpha(value)
        self.setp('alpha', value)
        #self.setp('cmap', value)
        self.set_cmap(self.get_cmap(a), a)

    def get_alpha(self, a=None):
        return self.getp('alpha')

    def set_edgecolor(self, value, a):
        self.setp('edgecolor', value)
        a.set_edgecolor([value])

    def get_edgecolor(self, a=None):
        return self.getp('edgecolor')

    def set_linewidth(self, value, a):
        self.setp('linewidth', value)
        a.set_linewidth(value)

    def get_linewidth(self, a=None):
        return self.getp('linewidth')

    def set_shade(self, value, a):
        self.setvar('shade', value)
        self.del_artist(delall=True)
        self.delp('loaded_property')

        self.generate_artist()
        ax = self.get_figaxes()
        ax.set_bmp_update(False)

        sel = [weakref.ref(self._artists[0])]
        import wx
        app = wx.GetApp().TopWindow
        # ifigure.events.SendPVDrawRequest(self, w=None,
        #                        wait_idle=True, refresh_hl=True)
        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)
        # self.reset_artist()

    def get_shade(self, a=None):
        return self.getvar('shade')

    def set_facecolor(self, value, a):
        if self.getvar('cz'):
            return
        if value == 'disabled':
            return
        if isinstance(value, str):
            value = cc.to_rgba(value)
        alpha = self.getp('alpha')
        if alpha is None:
            alpha = 1.0
        value = (value[0], value[1], value[2], alpha)
        self.setp('facecolor', value)
        a.set_facecolor([value])

    def get_facecolor(self, a=None):
        if self.getvar('cz'):
            return 'disabled'
        return self.getp('facecolor')

#
#   def hit_test
#
    def picker_a(self, artist, evt):
        axes = artist.axes
        if axes is None:
            return False, {}
        hit, extra = artist.contains(evt)

        if hit:
            return True, {}
        else:
            return False, {}

    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x, y, z = self._eval_xy()
        self._data_extent = [np.min(x), np.max(x),
                             np.min(y), np.max(y),
                             np.min(z), np.max(z)]
        return self._data_extent

    def _update_range_gl(self, range, idx):
        for a in self._artists:
            if hasattr(a, 'get_gl_data_extent'):
                tmprange = a.get_gl_data_extent()[idx]
            range = self._update_range(range,
                                       tmprange)
        return range

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y, z = self._eval_xy()
        if x is None:
            return xrange
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, (np.nanmin(x), np.nanmax(x)))

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        x, y, z = self._eval_xy()
        if x is None:
            return yrange
        if y is None:
            return yrange
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):

        x, y, z = self._eval_xy()
        if (xrange[0] is not None and
            xrange[1] is not None and
            yrange[0] is not None and
                yrange[1] is not None):
            if x.size*y.size == z.size:
                idx1 = np.where((y >= yrange[0]) & (y <= yrange[1]))[0]
                idx2 = np.where((x >= xrange[0]) & (x <= xrange[1]))[0]
                if (len(idx1) == 0 or len(idx2) == 0):
                    if (zrange[0] is None and
                            zrange[1] is None):
                        # this is for safety maybe not necessary
                        if scale == 'log':
                            z = mask_negative(z)
                        self._update_range(
                            zrange, [np.nanmin(z), np.nanmax(z)])
                        zrange = update_zrange(z)
                else:
                    zt = z[idx1, :]
                    zt = zt[:, idx2]
                    if scale == 'log':
                        zt = mask_negative(zt)
                    self._update_range(zrange, [np.nanmin(zt), np.nanmax(zt)])
            else:
                self._update_range(zrange, [np.nanmin(z), np.nanmax(z)])

        return zrange

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        cdata = self.getvar('cdata')
        cz = self.getvar('cz')
        if not cz:
            return crange
        if cdata is None:
            x, y, z = self._eval_xy()
            crange = self._update_range(crange,
                                        (np.nanmin(z), np.nanmax(z)))

        else:
            if np.iscomplexobj(cdata):
                tmp = np.max(np.abs(cdata))
                crange = self._update_range(crange,
                                            (-tmp, tmp))

            else:
                crange = self._update_range(crange,
                                            (np.nanmin(cdata), np.nanmax(cdata)))

        return crange

    def get_mappable(self):
        if self.getvar('cz'):
            return [a for a in self._artists if isinstance(a, ScalarMappable)]
        else:
            return []

    def handle_axes_change(self, data):
        name = data['name']
        if name.startswith('c') and self.getvar('cz'):
            self.del_artist(delall=True)
            self.delp('loaded_property')
            self.generate_artist()

    @classmethod
    def _saveload_names(self):
        return {'x', 'y', 'z'}

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        names = self._saveload_names()
        var = {name: check(self, name) for name in names}
        for name in names:
            if not var[name]:
                var[name+'data'] = self.getp(name)

        data['FigSurface'] = (1, var)
        data = super(FigSurface, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigSurface']
        super(FigSurface, self).load_data2(data)
        var = d[1]

        names = self._saveload_names()
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_xy(self):
        names = ("x", "y", "z")
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)

    def get_export_val(self, a):
        x, y, z = self.getvar("x", "y", "z")
        val = {"x": x, "y": y, "z": z}
        if self.getvar('cz'):
            val['cdata'] = self.getvar("cdata")
        return val

class FigRevolve(FigSurface):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._data_extent = None
            obj._coarse_artist = None
            obj._fine_artist = None
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_var('r', ['iter|nonstr', 'dynamic'])
        p.add_var('z', ['iter|nonstr', 'dynamic'])

        p.add_key('cmap', None)
        p.add_key('shade', 'flat')
        p.add_key('linewidth', 1.0)
        p.add_key('alpha', 1)
        p.add_key('rstride', 1)
        p.add_key('cstride', 1)
        p.add_key('edgecolor', 'k')
        p.add_key('facecolor', 'b')
        p.add_key('cz',  False)
        p.add_key('cdata', None)

        p.set_ndconvert("x", "y")

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)

        obj = set_hidden_vars(obj)
        if v['cmap'] is not None:
            if isinstance(v['cmap'], Colormap):
                v['cmap'] = v['cmap'].name
            kywds['cmap'] = v['cmap']
            del v['cmap']

        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args,  **kywds):
        FigSurface.__init__(self, *args,  **kywds)
        self._method = 'plot_revolve'

    @classmethod
    def get_namebase(self):
        return 'revolve'

    def _args2var(self):
        names0 = self.attr_in_file()
        names = ["r", "z"]
        use_np = [True]
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)
        r = values[0]
        z = values[1]
        if r is None or z is None:
            return False
        self.setp("r", r)
        self.setp("z", z)
        return True

    def generate_artist(self, coarse=False):
        if (self.isempty() is False
                and not coarse):
            return

        axes = self.get_figaxes()
        if not axes.get_3d():
            return

        container = self.get_container()
        r, z = self._eval_rz()
        # use_var should be false if evaluation is
        # okey.
        if self.getp('use_var'):
            return

        kywds = self._var["kywds"]

        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return

        ### stride is handled in fig_surface
        kywds['cstride'] = 1
        kywds['rstride'] = 1
        if coarse:
            f = ifigure._visual_config["3d_rot_accel_factor"]
        else:
            f = 1

        if (not 'color' in kywds and
                not 'facecolors' in kywds):
            cmap = self.get_cmap()
            kywds['cmap'] = get_cmap(cmap)

        kywds['shade'] = self.getvar('shade')
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

        m = getattr(container, self._method)
        self._artists = [m(r, z, **kywds)]
        self._fine_artist = self._artists[0]

        for artist in self._artists:
            artist.do_stencil_test = False
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))
            self._objs.append(weakref.ref(artist))
            cax.set_crangeparam_to_artist(artist)

    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        r, z = self._eval_rz()
        self._data_extent = [-np.max(r), np.max(r),
                             -np.max(r), np.max(r),
                             np.min(z), np.max(z)]
        return self._data_extent

    def get_xrange(self, xrange=[None, None], scale='linear'):
        r, z = self._eval_rz()
        if r is None:
            return xrange
        xrange = self._update_range_gl(xrange, 0)
        if scale == 'log':
            return self._update_range(xrange, [1e-15, np.nanmax(xrange)])
        return xrange

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        r, z = self._eval_rz()
        if r is None:
            return yrange
        yrange = self._update_range_gl(yrange, 1)
        if scale == 'log':
            return self._update_range(yrange, [1e-15, np.nanmax(yrange)])
        return yrange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        r, z = self._eval_rz()
        zrange = self._update_range_gl(zrange, 2)
        if scale == 'log':
            return self._update_range(zrange, [1e-15, np.nanmax(zrange)])
        return zrange

    @classmethod
    def _saveload_names(self):
        return {'r', 'z'}

    def _eval_rz(self):
        names = ("r", "z")
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)

    def get_shade(self, a=None):
        return self.getvar('shade')

    def get_export_val(self, a):
        r, z = self.getvar("r", "z",)
        val = {"r": r, "z": z}
        return val
