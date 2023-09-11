from __future__ import print_function

from .gl_compound import GLCompound
from matplotlib.collections import LineCollection
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D

from matplotlib.artist import allow_rasterization
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile, isdynamic, isiterable
from ifigure.utils.args_parser import ArgsParser
from matplotlib.path import Path
from matplotlib.transforms import Bbox, TransformedPath
from matplotlib.colors import Colormap

from ifigure.matplotlib_mod.cz_linecollection import CZLineCollection
from ifigure.matplotlib_mod.art3d_gl import Line3DCollectionGL, LineGL

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigPlot')

_decimate_limit = 2500
_decimate_limit_switch = 3


class FigPlot(FigObj, XUser, YUser, ZUser, CUser):
    '''
    FigPlot: an object to handle line and errorbar plot.

    See help(plot), help(errorbar) for more detail of
    generating this object from ifigure.interactive

    '''
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._mpl_cmd = 'plot'
            obj._eb_container = (None, tuple(), tuple())
            obj._other_artists = []
            obj._objs = []  # for debug....
            obj._data_extent = None
            obj._is_decimate = False
            obj._use_decimate = False
            obj._decimate_limit = _decimate_limit
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj
        mpl_cmd = kywds.pop('mpl_command', 'plot')
        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_opt('z', None, ['numbers|nonstr', 'dynamic'])
        p.add_opt('s', '', 'str')  # optional argument
        p.add_key('cz', False, 'bool')

#        if mpl_cmd is 'errorbar':
        p.add_key('xerr', None)
        p.add_key('yerr', None)
        p.add_key('ecolor', None)
        p.add_key('elinewidth', None)
        p.add_key('array_idx', None)
        if 'cz' in kywds and kywds['cz']:
            p.add_key('cmap', 'jet')
        p.add_key('c',  None)

        p.set_ndconvert("x", "y", "z", "xerr", "yerr", "c")
        p.set_squeeze_minimum_1D("x", "y", "z", "xerr", "yerr", "c")
        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)
        obj._mpl_cmd = mpl_cmd
        if (v["x"] is None and not isdynamic(v["y"])):
            v["x"] = np.arange(v["y"].shape[-1]).astype(v["y"].dtype)
        if 'cmap' in v and v['cmap'] is not None:
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
        super(FigPlot, self).__init__(*args, **kywds)

    @classmethod
    def isFigPlot(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return True

    @classmethod
    def get_namebase(self):
        return 'plot'

    def property_in_file(self):
        #        if isinstance(self._artists[0],
        #                      CZLineCollection):
        #            return (["linewidth", "linestyle", "alpha"] +
        #                    super(FigPlot, self).property_in_file())
        #        else:
        props = (["linestyle", "linewidth", "marker", "markersize",
                  "markeredgecolor", "markerfacecolor",
                  "markeredgewidth", "alpha"] +
                 super(FigPlot, self).property_in_file())
        if not self.getp('cz'):
            props = ['color'] + props
        return props

    @classmethod
    def property_in_palette(self):
        return (["line", "marker", "errorbar"],
                [["color", "linestyle", "linewidth_2", "alpha"],
                 ["markerfacecolor", "markeredgecolor", "marker",
                  "markersize", "markeredgewidth"],
                 ["ecolor", "elinewidth"]],)

    @classmethod
    def attr_in_file(self):
        return ['cz', 'ecolor', 'elinewidth']+super(FigPlot, self).attr_in_file()

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plot1.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)

        super(FigPlot, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)
        CUser.get_caxisparam(self)

    def args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y", "z", "s", "c"]
        use_np = [True]*3 + [False] + [True, ]
        if self._mpl_cmd != 'plot':
            names = names + ["xerr", "yerr"]
            use_np = use_np + [True]*2
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)
        x = values[0]
        y = values[1]
        if x is None:
            x = np.arange((y.shape)[-1]).astype(y.dtype)
            self.setp("x", x)
        if x is None:
            return False
        if y is None:
            return False
        if (x.ndim == 1 and y.ndim == 1 and
                x.size != y.size):
            self.setp("x", None)
            self.setp("y", None)
            return False
        if self._mpl_cmd != 'plot':
            xerr, yerr = self.getp(('xerr', 'yerr'))
            if xerr is not None and xerr.size == 1:
                self.setp('xerr',
                          np.array([xerr[0]]*(self.getp("y").size)))
            if yerr is not None and yerr.size == 1:
                self.setp('yerr',
                          np.array([yerr[0]]*(self.getp("y").size)))
        if 'cmap' in self.getvar("kywds"):
            cax = self.get_caxisparam()
            cax.set_cmap(self.getvar('kywds')['cmap'])

#        self.setp("x", self.getp('x').astype(np.float64))
#        self.setp("y", self.getp('y').astype(np.float64))
        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        #import inspect
        # print [(x[1],x[3]) for x in inspect.stack()]
        # print 'generating plot', self, self._suppress
        #import traceback
        # traceback.print_stack()
        container = self.get_container()
        if container is None:
            return
        if self.isempty() is False:
            return

        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()  # this handles "use_var"
        else:
            x, y, z, s, c, xerr, yerr = self._eval_xy()  # this handles "use_var"

        lp = self.getp("loaded_property")
        cz = self.getp('cz')
        axes = self.get_figaxes()


#           if lp is None:
        if True:
            #              x, y, z, s, c = self.getp(("x", "y", "z", "s", "c"))
            if y is None:
                return
            if x is None:
                return

            if (x is not None and
                    y is not None):
                if len(y.shape) == 1:
                    kywds = self._var["kywds"].copy()
                    if self._mpl_cmd == 'plot':
                        if not cz:
                            if 'cmap' in kywds:
                                del kywds['cmap']
                            if (x.size > self._decimate_limit and
                                self._use_decimate and
                                    self.check_data_uniform(x)):
                                self.set_artist(container.plot([0], [0],
                                                               s, **kywds))
                                self._is_decimate = True
                                self.handle_axes_change()
                            else:
                                if np.iscomplexobj(x):
                                    x = np.array(x, copy=False).real
                                if np.iscomplexobj(y):
                                    y = np.array(y, copy=False).real
                                args = [x, y]
                                self._is_decimate = False
                                axes = self.get_figaxes()
                                if axes.get_3d():
                                    if z is None:
                                        z = np.array([0]*len(x))
                                    else:
                                        if np.iscomplexobj(z):
                                            z = np.array(z, copy=False).real
                                    args.append(z)
                                    kywds['array_idx'] = self.getvar(
                                        'array_idx')
                                args.append(s)
                                self.set_artist(container.plot(*args,
                                                               **kywds))
                                if axes.get_3d():
                                    self = convert_to_FigPlotGL(self)
#                             self._artists[0].set_lod(True)
                        else:
                            cax = self.get_caxisparam()
                            cmap = cax.get_cmap()
                            if cmap is None:
                                cmap = 'jet'
                                cax.set_cmap(cmap)
                            args = [x, y, z]
                            if c is not None and axes.get_3d():
                                args.append(c)

                            a = container.cz_plot(*args,  **kywds)
                            self.set_artist(a)

                    elif self._mpl_cmd == 'errorbar':
                        if axes.get_3d():
                            return
                        #xerr, yerr = self.getp(("xerr", "yerr"))
                        kywds['fmt'] = s
                        a = container.errorbar(x,
                                               y,
                                               xerr=xerr,
                                               yerr=yerr,
                                               **kywds)
                        self.set_artist(a[0])
                        self._eb_container = a
                        if self.getp('ecolor') is None:
                            self.setp('ecolor', self.get_ecolor(a[0]))
                        else:
                            self.set_ecolor(self.getp('ecolor'), a[0])

                        if self.getp('elinewidth') is None:
                            self.setp('elinewidth',
                                      self.get_elinewidth(a[0]))
                        else:
                            self.set_elinewidth(self.getp('elinewidth'),
                                                a[0])
        if lp is not None:
            for i in range(0, len(lp)):
                self.set_artist_property(self._artists[i], lp[i])
            self.delp("loaded_property")

        self.set_rasterized()

        mappable = self.get_mappable()
        ac = self.get_caxisparam()
        for a in mappable:
            ac.set_crangeparam_to_artist(a)

#           for artist in self._artists:
#               artist.figobj=self
#               artist.figobj_hl=[]
#               artist.set_zorder(self.getp('zorder'))
#               self._objs.append(weakref.ref(artist))

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        self.store_loaded_property()

        if len(artistlist) is len(self._artists):
            for name, child in self.get_children():
                child.del_artist(delall=True)

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                #             a.set_picker(None)
                try:
                    if a in container.collections:
                        a.remove()
                    elif a in container.lines:
                        a.remove()
                    if self._mpl_cmd == 'errorbar':
                        for a in self._eb_container[1]:
                            a.remove()
                        for a in self._eb_container[2]:
                            a.remove()
                        self._eb_container = (None, tuple(), tuple())
                except:
                    logging.exception("fig_plot: highlight_aritst() failed")
            for a in self._other_artists:
                a.remove()

        super(FigPlot, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        container = self.get_container()
        if val == True:
            for a in alist:
                if isinstance(a, LineGL):
                    hl = alist[0].add_hl_mask()
                elif isinstance(a, Line2D) or isinstance(a, CZLineCollection):
                    if hasattr(a, 'set_3d_properties'):
                        args = a._verts3d
                    else:
                        x = a.get_xdata()
                        y = a.get_ydata()
                        p = 300
                        if x.shape[0] > p:
                            idx = np.floor(
                                np.arange(p)*(x.shape[0]/float(p))).astype(int)
                        else:
                            idx = np.arange(x.shape[0])
                        args = [x[idx].copy(), y[idx].copy()]
                    kwargs = {'marker': 's',
                              'color': 'k',
                              'linestyle': 'None',
                              'markerfacecolor': 'None',
                              'markeredgewidth': 0.5,
                              'scalex': False, 'scaley': False}

                    hl = container.plot(*args, **kwargs)

#                  if hasattr(a, 'set_3d_properties'):
#                      z=a._verts3d[2]
#                      hl[0].set_3d_properties(zs = z)
                elif isinstance(a, Line3DCollectionGL):
                    hl = alist[0].add_hl_mask()
#                  hl = a.make_hl_artist(container) #slower
                for item in hl:
                    a.figobj_hl.append(item)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    hl.remove()
                a.figobj_hl = []

    def get_mappable(self):
        return [a for a in self._artists if isinstance(a, ScalarMappable)]

#
#   def hit_test
#
    def picker_a(self, artist, evt):
        axes = artist.axes
        if axes is None:
            return False, {}
        hit, extra = artist.contains(evt)
        if hit:
            return True, {"child_artist": artist}
        else:
            return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0
#
#  Popup in Canvas
#

    def canvas_menu(self):
        ac = self.get_caxisparam()
        if len(ac._member) > 1:
            pass
        cz = self.getp('cz')
        if ac is None:
            return super(FigPlot, self).tree_viewer_menu()
        if cz and ac.cbar_shown():
            m = [('Hide ColorBar', self.onHideCB1, None), ]
        elif cz and not ac.cbar_shown():
            m = [('Show ColorBar', self.onShowCB1, None), ]
        else:
            m = []
        menus = m + \
            super(FigPlot, self).canvas_menu()
        return menus

    def get_export_val(self, a):
        from matplotlib.artist import getp
        data = {"xdata": self.getvar("x"),
                "ydata": self.getvar("y")}
        zdata = self.getvar("z")
        cdata = self.getvar("c")
        if cdata is not None:
            data["cdata"] = cdata
            if zdata is not None:
                data["zdata"] = zdata
        else:
            if zdata is not None:
                if self.getvar("cz"):
                    data["cdata"] = zdata
                else:
                    data["zdata"] = zdata
        return data

    def get_data_extent(self):
        #        print 'entering data extent',  self._data_extent
        if self._data_extent is not None:
            return self._data_extent
        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()  # this handles "use_var"
        else:
            x, y, z, s, c, xerr, yerr = self._eval_xy()  # this handles "use_var"

#        if self.isempty():
        if x is None:
            self._data_extent = [0, len(y), np.nanmin(y), np.nanmax(y)]
        else:
            self._data_extent = [np.nanmin(x), np.nanmax(x),
                                 np.nanmin(y), np.nanmax(y)]
#        else:
#            xr = (np.inf, -np.inf)
#            yr = (np.inf, -np.inf)
#            for a in self._artists:
#                x = a.get_xdata()
#                y = a.get_ydata()
#                xr = (min((xr[0], np.nanmin(x))), max((xr[1], np.nanmax(x))))
#                yr = (min((yr[0], np.nanmin(y))), max((yr[1], np.nanmax(y))))
#            self._data_extent=[xr[0], xr[1], yr[0], yr[1]]
#        print 'exiting data extent',  self._data_extent
        return self._data_extent
#
#   error bar properties
#

    def set_ecolor(self, value, a=None):
        if self._mpl_cmd == 'errorbar':
            self.setp('ecolor', value)
            for a in self._eb_container[1]:
                a.set_color(value)
            for a in self._eb_container[2]:
                a.set_color(value)

    def get_ecolor(self, a):
        v = None
        if self._mpl_cmd == 'errorbar':
            for a in self._eb_container[1]:
                v = a.get_color()
            for a in self._eb_container[2]:
                v = a.get_color()
            if isinstance(v, np.ndarray):
                v = np.squeeze(v)
            return v
        else:
            return v

    def set_elinewidth(self, value, a=None):
        if self._mpl_cmd == 'errorbar':
            self.setp('elinewidth', value)
            for a in self._eb_container[1]:
                a.set_linewidth(value)
            for a in self._eb_container[2]:
                a.set_linewidth(value)

    def get_elinewidth(self, a):
        v = None
        if self._mpl_cmd == 'errorbar':
            for a in self._eb_container[1]:
                v = a.get_linewidth()
            for a in self._eb_container[2]:
                v = a.get_linewidth()
            if isiterable(v):
                v = v[0]
            return v
        else:
            return v

    def set_linewidth(self, value, a=None):
        a.set_linewidth(value)

    def get_linewidth(self, a):
        try:
            return a.get_linewidth()[0]
        except:
            return a.get_linewidth()

    def set_decimate(self, value, a):
        if (self._mpl_cmd == 'plot' and
                not self.getp('cz')):
            self._use_decimate = value
            if self._use_decimate:
                self.handle_axes_change()
            else:
                x = self.getp('x')
                y = self.getp('y')
                self._artists[0].set_xdata(x)
                self._artists[0].set_ydata(y)
                if hasattr(self._artists[0], 'set_czdata'):
                    z = self.getp('z')
                    self._artists[0].set_czdata(z)
        else:
            self._use_decimate = False

    def get_decimate(self, a):
        return self._use_decimate

    def check_data_uniform(self, x):
        if any(np.isnan(x)):
            self._use_decimate = False
            return False
        skip = x.size//10
        ix = range(10)
        t = [x[ix*skip] - x[(ix+1)*skip] for ix in range(9)]
        # print t
        # print abs((max(t) - min(t))/np.mean(t))
        if abs((max(t) - min(t))/np.mean(t)) > 0.01:
            self._use_decimate = False
        return abs((max(t) - min(t))/np.mean(t)) < 0.01
#
#   range
#

    def get_xrange(self, xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()[0:2]
        #        if de is not None:
        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()  # this handles "use_var"
        else:
            x, y, z, s, c, xerr, yerr = self._eval_xy()  # this handles "use_var"
        if x is None:
            return xrange
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        def calc_yrange(x, y, xrange, yrange, scale):
            # x.ndim = 1, y.ndim = 1 in this func
            xidx = np.isfinite(x)
            idx = (np.where((x[xidx] >= xrange[0]) &
                            (x[xidx] <= xrange[1])))
            check = False
            for ar in idx:
                if len(ar) == 0:
                    check = True
            if check:
                return yrange

            yy = y[xidx][idx]
            if scale == 'log':
                yy = mask_negative(yy)
            y0n = np.nanmin(yy)
            y1n = np.nanmax(yy)
            yrange = self._update_range(yrange, (y0n, y1n))
            return yrange

        de = self.get_data_extent()
        y0 = yrange[0]
        y1 = yrange[1]

        if (xrange[0] is not None and
                xrange[1] is not None):
            if self._mpl_cmd == 'plot':
                x, y, z, s, c = self._eval_xy()
            else:
                x, y, z, s, c, xerr, yerr = self._eval_xy()

            if x.ndim > 2 or y.ndim > 2:
                return yrange
            if x.ndim == 1:
                xl = 1
            else:
                xl = x.shape[0]
            if y.ndim == 1:
                yl = 1
            else:
                yl = y.shape[0]
            for k in range(xl):
                if x.ndim == 1:
                    xt = x
                else:
                    xt = x[k]
                for m in range(yl):
                    if y.ndim == 1:
                        yt = y
                    else:
                        yt = y[m]
                    yrange = calc_yrange(xt, yt, xrange, yrange, scale)

        if (not (xrange[0] is not None and
                 xrange[1] is not None) or
                (yrange[0] is None) or (yrange[1] is None)):
            if de is not None:
                yrange = self._update_range(yrange, de[2:])
        return yrange

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()
        else:
            x, y, z, s, c, xerr, yerr = self._eval_xy()
        if c is not None:
            if scale == 'log':
                c = mask_negative(c)
            crange = self._update_range(crange,
                                        (np.nanmin(c), np.nanmax(c)))
        else:
            if z is not None and self.getp('cz'):
                if scale == 'log':
                    z = mask_negative(z)
                crange = self._update_range(crange,
                                            (np.nanmin(z), np.nanmax(z)))
        return crange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()
        else:
            x, y, z, s, c, xerr, yerr = self._eval_xy()
        if z is not None:
            if scale == 'log':
                z = mask_negative(z)
            zrange = self._update_range(zrange, (np.nanmin(z), np.nanmax(z)))
        return zrange

    def _saveload_names(self):
        return ['x', 'y', 'z', 'xerr', 'yerr', 's', 'c']

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
                if self._save_mode == 0 or name == 's':
                    var[name+'data'] = self.getp(name)
                else:
                    if self.getp(name) is not None:
                        var[name+'data'] = np.array([0, 0])
                    else:
                        var[name+'data'] = None
        var["mpl_cmd"] = self._mpl_cmd
        var["use_decimate"] = self._use_decimate
        data['FigPlot'] = (1, var)
        data = super(FigPlot, self).save_data2(data)

        return data

    def prepare_compact_savemode(self):
        var_bk = self._var.copy()
        self._var['x'] = np.array([0, 0])
        self._var['y'] = np.array([0, 0])
        self._var['c'] = None
        self._var['z'] = None
        self._var['xerr'] = None
        self._var['yerr'] = None

        return var_bk

    def load_data2(self, data):
        d = data['FigPlot']
        super(FigPlot, self).load_data2(data)
        var = d[1]
        self._mpl_cmd = var["mpl_cmd"]
        if "use_decimate" in var:
            self._use_decimate = var["use_decimate"]
        names = self._saveload_names()
        for name in names:
            if not name in var:
                var[name] = True
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def refresh_artist_data(self):
        if self._mpl_cmd != 'plot':
            FigObj.refresh_artist_data(self)
            return
        if self.isempty() and not self._suppress:
            self.generate_artist()
            return
        self._data_extent = None
        if self._mpl_cmd == 'plot':
            x, y, z, s, c = self._eval_xy()

        if x.ndim == 0:
            x = np.array([x])
        if y.ndim == 0:
            y = np.array([y])
        self._artists[0].set_xdata(x)
        self._artists[0].set_ydata(y)
        self.handle_axes_change()

    def handle_axes_change(self, evt=None):
        '''
        decimation when the range changed
        '''
#        print ' handle_axes_change(self,evt)'
        if False:  # skip this part...
            if (self._mpl_cmd == 'plot' and
                    len(self._artists) != 0):
                x = self.getp('x')
                y = self.getp('y')
                yrange = self.get_yaxisparam().range
                xrange = self.get_xaxisparam().range
                idx = self._get_idx_from_range(x, xrange)

                self._artists[0].set_xdata(x[idx])
                self._artists[0].set_ydata(y[idx])
                if hasattr(self._artists[0], 'set_czdata'):
                    z = self.getp('z')
                    self._artists[0].set_czdata(z[idx])
            else:
                pass
        x = self.getp('x')
        y = self.getp('y')
        if (self._use_decimate and
                x.size > self._decimate_limit*_decimate_limit_switch):
            yrange = self.get_yaxisparam().range
            xrange = self.get_xaxisparam().range
            idx = self._get_idx_from_range(x, xrange)

            x2, y2 = self._decimate_array_method2(x, y, idx)
            x2 = np.concatenate(
                ([x[max((0, idx[0]-1))]], x2, [x[min((len(x)-1, idx[-1]+1))]]))
            y2 = np.concatenate(
                ([y[max((0, idx[0]-1))]], y2, [y[min((len(y)-1, idx[-1]+1))]]))
            self._artists[0].set_xdata(x2)
            self._artists[0].set_ydata(y2)
            self._is_decimate = True
        else:
            self._is_decimate = False
        mappable = self.get_mappable()
        ac = self.get_caxisparam()
        for a in mappable:
            ac.set_crangeparam_to_artist(a)

    def _eval_xy(self):
        if self._mpl_cmd == 'plot':
            names = ("x", "y", "z", "s", "c")
        else:
            names = ("x", "y", "z", "s", "c", "xerr", "yerr")

        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)

    def _get_idx_from_range(self, x, range):
        idx = np.where((x[np.isfinite(x)] > range[0]) &
                       (x[np.isfinite(x)] < range[1]))[0]
        if idx.size > 0:
            if idx[0] != 0:
                idx = np.hstack((idx[0]-1, idx))
            if idx[-1] != x.size-1:
                idx = np.hstack((idx, idx[-1]+1))
            return idx
        else:
            return np.array([np.argmin(np.abs(x-range[0]))])

    def _decimate_array_method2(self, x, y, idx):
        x2 = x[idx]
        y2 = y[idx]

        chunksize = self._decimate_limit//2
        numchunks = y2.size // chunksize
        if numchunks == 0:
            # when size of y2 is too small..
            return x2, y2

        if y2.size//numchunks > chunksize:
            chunksize = y2.size//numchunks

        ychunks_f = y2[:chunksize*numchunks].reshape((-1, numchunks))
        xchunks_f = x2[:chunksize*numchunks].reshape((-1, numchunks))

        y3 = np.vstack((np.nanmin(ychunks_f, axis=1),
                        np.nanmax(ychunks_f, axis=1))).transpose().reshape(chunksize*2)
        x3 = np.vstack((np.nanmin(xchunks_f, axis=1),
                        np.nanmax(xchunks_f, axis=1))).transpose().reshape(chunksize*2)
        # append left over..
        if chunksize*numchunks < y2.size:
            x2 = np.hstack(
                (x3, np.nanmin(x2[chunksize*numchunks:]), np.nanmax(x2[chunksize*numchunks:])))
            y2 = np.hstack(
                (y3, np.nanmin(y2[chunksize*numchunks:]), np.nanmax(y2[chunksize*numchunks:])))
            return x2, y2
        else:
            return x3, y3

    def set_alpha(self, v, a):
        a.set_alpha(v)


class StepPlot(FigPlot):
    '''
    stepplot is a special case of figplot.
    if has only x and y data. 
    it supports decimation
    it supports data compression using file.

    Because of historiy, routines for decimation is 
    written in FigPLot
    '''
    def __new__(cls, *args, **kywds):
        if 'src' in kywds:
            obj = FigPlot.__new__(cls, *args, **kywds)
#            obj = set_hidden_vars(obj)
            obj._use_decimate = False
            return obj
        mpl_cmd, kywds = ProcessKeywords(kywds, 'mpl_command', 'plot')
        mpl_cmd = 'plot'
        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_opt('s', '', 'str')  # optional argument

#        if mpl_cmd is 'errorbar':

        p.set_ndconvert("x", "y")
        p.set_squeeze_minimum_1D("x", "y")

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigPlot.__new__(cls, *args, **kywds)
#        obj = set_hidden_vars(obj)
        obj._use_decimate = False
        obj._mpl_cmd = mpl_cmd
        if (v["x"] is None and not isdynamic(v["y"])):
            v["x"] = np.arange(v["y"].shape[-1])
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    @classmethod
    def get_namebase(self):
        return 'stepplot'

    def get_export_val(self, a):
        self.expand_catalog()
        data = {"xdata": self.getvar('x'),
                "ydata": self.getvar('y')}
        return data

    def _eval_xy(self):
        names = ("x", "y", "z", "s", "c")
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)

            self._expand_stepplot_data()
        return self.getp(names)

    def _expand_stepplot_data(self):
        x = self.getp('x')
        y = self.getp('y')

        dx = np.hstack(((x[1:]-x[:-1])/1e6, 0))
        x = np.transpose(np.vstack((x, x+dx))).flatten()[:-1]
        y = np.transpose(np.vstack((y, y))).flatten()[:-1]
        self.setp('x', np.array(x))
        self.setp('y', np.array(y))

        #new_x = [x[0]]
        #new_y = [y[0]]
        # for k in range(x.size-1):
        #  new_x.append(x[k+1] -  (x[k+1] - x[k])/1e6)
        #  new_x.append(x[k+1])
        #  new_y.append(y[k])
        #  new_y.append(y[k+1])
        # print new_x
        # print new_y


class TimeTrace(FigPlot):
    '''
    time trace is a special case of figplot.
    if has only x and y data. 
    it supports decimation
    it supports data compression using file.

    Because of historiy, routines for decimation is 
    written in FigPLot

    '''
    def __new__(cls, *args, **kywds):
        if 'src' in kywds:
            obj = FigPlot.__new__(cls, *args, **kywds)
#            obj = set_hidden_vars(obj)
            obj._use_decimate = True
            return obj
        mpl_cmd, kywds = ProcessKeywords(kywds, 'mpl_command', 'plot')
        mpl_cmd = 'plot'
        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_opt('s', '', 'str')  # optional argument

#        if mpl_cmd is 'errorbar':

        p.set_ndconvert("x", "y")
        p.set_squeeze_minimum_1D("x", "y")

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigPlot.__new__(cls, *args, **kywds)
#        obj = set_hidden_vars(obj)
        obj._use_decimate = True
        obj._mpl_cmd = mpl_cmd
        if (v["x"] is None and not isdynamic(v["y"])):
            v["x"] = np.arange(v["y"].shape[-1])
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    @classmethod
    def property_in_palette(self):
        tab, names = super(TimeTrace, self).property_in_palette()
        names[0].append('decimate')
        return tab[:2], names[:2]

    @classmethod
    def get_namebase(self):
        return 'timetrace'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'timetrace.png')
        return [idx1]

    def refresh_artist_data(self):
        if self.isempty() and not self._suppress:
            self.generate_artist()
            return
        self._data_extent = None

        x, y, z, s, c = self._eval_xy()  # this handles "use_var"

        if x.ndim == 0:
            x = np.array([x])
        if y.ndim == 0:
            y = np.array([y])
        self.check_data_uniform(x)  # this could make _use_decimate False

        self.handle_axes_change()
#        dprint1('refresh_artist_data :'+
#                str(self._artists[0].get_xdata().size) + ' ' +
#                str(self._artists[0].get_ydata().size))
#        self._artists[0].set_ydata(y)
#        self._artists[0].set_xdata(x)

    def expand_catalog(self):
        if not self.hasvar('x_catalog'):
            return
        try:
            x = self.getvar('x_catalog').restore(0)
        except IOError:
            print("IOError during catalog expansion")
            self.delvar('x_catalog')
            self.delvar('y_catalog')
            return
        try:
            y = self.getvar('y_catalog').restore(0)
        except IOError:
            print("IOError during catalog expansion")
            self.delvar('x_catalog')
            self.delvar('y_catalog')
            return

        self.delvar('x_catalog')
        self.delvar('y_catalog')
        if x.size != y.size:
            dprint1('catalog data x and y has different length')
            l = min([x.size, y.size])
            x = x[:l]
            y = y[:l]
        self.setvar('x', x)
        self.setvar('y', y)
        self.setp('x', x)
        self.setp('y', y)
        return x, y

    def get_export_val(self, a):
        self.expand_catalog()
        return {"xdata": self.getvar('x'),
                "ydata": self.getvar('y')}

    def handle_axes_change(self, evt=None):
        '''
        decimation when the range changed
        '''
#        print ' handle_axes_change(self,evt)'
        if len(self._artists) != 0:
            x = self.getp('x')
            y = self.getp('y')
            yrange = self.get_yaxisparam().range
            xrange = self.get_xaxisparam().range
#                print xrange, yrange
            idx = self._get_idx_from_range(x, xrange)
            if ((idx.size < self._decimate_limit) and
                    self.hasvar('x_catalog') and
                    self.hasvar('y_catalog')):
                dprint1('expanding high resolution data ' +
                        self.get_full_path())
                x, y = self.expand_catalog()
                idx = self._get_idx_from_range(x, xrange)
            if (self._use_decimate and
                    idx.size > self._decimate_limit*_decimate_limit_switch):
                x2, y2 = self._decimate_array_method2(x, y, idx)
                x2 = np.concatenate(
                    ([x[max((0, idx[0]-1))]], x2, [x[min((len(x)-1, idx[-1]+1))]]))
                y2 = np.concatenate(
                    ([y[max((0, idx[0]-1))]], y2, [y[min((len(y)-1, idx[-1]+1))]]))
                self._artists[0].set_xdata(x2)
                self._artists[0].set_ydata(y2)
                self._is_decimate = True
            else:
                self._artists[0].set_xdata(x[idx])
                self._artists[0].set_ydata(y[idx])
                self._is_decimate = False
    #                dprint1(str(time.time()-t))
        else:
            pass
        mappable = self.get_mappable()
        ac = self.get_caxisparam()
        for a in mappable:
            ac.set_crangeparam_to_artist(a)

    def save_data2(self, data=None):
        return FigPlot.save_data2(self, data)

    def load_data2(self, data):
        return FigPlot.load_data2(self, data)


class FigPlotGL(GLCompound, FigPlot):
    def onSetRotCenter(self, evt):
        x, y, z = self.getvar('x', 'y', 'z')

        sel = self.getSelectedIndex()
        if len(sel) == 0:
            sel = self.shown_component

        array_idx = self.getvar('array_idx')

        if array_idx is not None and len(sel) > 0:
            idx = np.in1d(array_idx, sel)
            vv = np.vstack((x[idx], y[idx], z[idx])).transpose()
            cc = np.mean(vv, 0)
        else:
            cc = np.array([np.mean(x),
                           np.mean(y),
                           np.mean(z)])

        axes = self._artists[0].axes
        axes._gl_rot_center = cc
        axes._gl_use_rot_center = True
        evt.Skip()

    def canvas_menu(self):
        m = FigObj.canvas_menu(self)
        m2 = GLCompound.canvas_menu(self)
        return m[:1]+m2+m[1:]

def convert_to_FigPlotGL(obj):
    obj.__class__ = FigPlotGL
    obj.set_pickmask(obj._pickmask)
    return obj
