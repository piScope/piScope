from ifigure.mto.triangle_plots import TrianglePlots
from matplotlib.collections import LineCollection
from matplotlib.cm import ScalarMappable

from matplotlib.artist import allow_rasterization
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile, isdynamic, isiterable
from ifigure.utils.triangulation_wrapper import tri_args
from ifigure.matplotlib_mod.triplot_mod import triplot
from ifigure.utils.args_parser import ArgsParser
from matplotlib.path import Path
from matplotlib.transforms import Bbox, TransformedPath
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigPlot')


class FigTriplot(FigObj, XUser, YUser, TrianglePlots):
    '''
    triplot(x, y)
    triplot(tri, x, y)
    '''
    def __new__(cls, *args, **kywds):
        if len(args) == 3:
            tri = args[0]
            args = args[1:]
        else:
            tri = None

        def set_hidden_vars(obj):
            obj._other_artists = []
            obj._objs = []  # for debug....
            obj._data_extent = None
            return obj
        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj
        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_key('color', 'b')
        p.add_key('linestyle', '-')
        p.add_key('linewidth', 1.0)
        p.set_ndconvert("x", "y")
        p.set_squeeze_minimum_1D("x", "y")
        p.add_key('mask', None)

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)
        if (v["x"] is None and not isdynamic(v["y"])):
            v["x"] = np.arange(v["y"].shape[-1])
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        obj.setvar("tri", tri)

        return obj

    def __init__(self, *args,  **kywds):
        if len(args) == 3:
            tri = args[0]
            args = args[1:]
        else:
            tri = None
        self._tri = tri
        XUser.__init__(self)
        YUser.__init__(self)
        TrianglePlots.__init__(self)
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigTriplot, self).__init__(*args, **kywds)

    @classmethod
    def isFigTriplot(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return True

    @classmethod
    def get_namebase(self):
        return 'triplot'

    def property_in_file(self):
        return (["color", "linestyle",
                 "linewidth", "marker", "markersize",
                 "markeredgecolor", "markerfacecolor",
                 "markeredgewidth", "alpha"] +
                super(FigTriplot, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return (["line", "marker"],
                [["color_2", "plinestyle_2", "linewidth_2", "alpha_2", ],
                 ["markerfacecolor", "markeredgecolor", "marker",
                  "markersize", "markeredgewidth"], ])

    @classmethod
    def attr_in_file(self):
        return (['mask', 'color', 'linestyle', 'linewidth'] +
                super(FigTriplot, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plot1.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)

        super(FigTriplot, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)

    def args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y"]
        use_np = [True]*2 + [False]
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)
        x = values[0]
        y = values[1]
        if x is None:
            x = np.arange((y.shape)[-1])
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
        #self.setp('x', self.getp('x').flatten())
        #self.setp('y', self.getp('y').flatten())

        return True

    def generate_artist(self):
        container = self.get_container()
        if self.isempty() is False:
            return

        x, y = self._eval_xy()  # this handles "use_var"

        lp = self.getp("loaded_property")

        if True:
            x, y = self.getp(("x", "y"))
            if y is None:
                return
            if x is None:
                return

            if (x is not None and
                    y is not None):
                self._data_extent = [np.nanmin(x), np.nanmax(x),
                                     np.nanmin(y), np.nanmax(y)]

                # if len(y.shape) == 1:
                if True:
                    kywds = self._var["kywds"]
                    args, self._tri = tri_args(x, y, self._tri)
                    kywds['mask'] = self.getp('mask')
                    kywds['linestyle'] = self.getp('linestyle')
                    kywds['linewidth'] = self.getp('linewidth')
                    kywds['color'] = self.getp('color')
                    a = triplot(container, *args, **kywds)
                    self.set_artist(a[0])
                    self._other_artists = a[1:]

        if lp is not None:
            for i in range(0, len(lp)):
                self.set_artist_property(self._artists[i], lp[i])
            self.delp("loaded_property")
        self.set_rasterized()

    def refresh_artist_data(self):
        if self.isempty() and not self._suppress:
            self.generate_artist()
            return
        self._data_extent = None
        x, y = self._eval_xy()  # this handles "use_var"
        self._artists[0].set_xdata(x)
        self._artists[0].set_ydata(y)

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
                except:
                    logging.exception("fig_plot: highlight_aritst() failed")
            for a in self._other_artists:
                a.remove()

        super(FigTriplot, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        container = self.get_container()
        if val == True:
            for a in alist:
                x = a.get_xdata()
                y = a.get_ydata()
                p = 300
                if x.shape[0] > p:
                    idx = np.floor(
                        np.arange(p)*(x.shape[0]/float(p))).astype(int)
                else:
                    idx = np.arange(x.shape[0])
                hl = container.plot(x[idx].copy(), y[idx].copy(), marker='s',
                                    color='k', linestyle='None',
                                    markerfacecolor='None',
                                    markeredgewidth=0.5,
                                    scalex=False, scaley=False)

                for item in hl:
                    a.figobj_hl.append(item)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    try:
                        hl.remove()
                    except:
                        logging.exception(
                            "fig_triplot: highlight_aritst() failed")
                a.figobj_hl = []
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

    def onExport(self, event):
        from matplotlib.artist import getp

        shell = self.get_root_parent().app.shell
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        for a in self._artists:
            if a in sel:
                fig_val = {"xdata": getp(a, "xdata"),
                           "ydata": getp(a, "ydata")}
                text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\']\"'
                self._export_shell(fig_val, 'fig_val', text)
                break
#
#   setter/getter
#

    def set_color(self, value, a):
        self.setp('color', value)
        self._setter_others(value, 'color')

    def get_color(self, a):
        return self.getp('color')

    def set_linewidth(self, value, a):
        self._setter_others(value, 'linewidth')

    def get_linewidth(self, a):
        self._getter_others('linewidth')

    def set_linestyle(self, value, a):
        self._setter_others(value, 'linestyle')

    def get_linestyle(self, a):
        self._getter_others('linestyle')

    def set_alpha(self, value, a):
        self._setter_others(value, 'alpha')
        for a in self._artists:
            a.set_alpha(value)

    def get_alpha(self, a):
        return self._getter_others('alpha')

    def _setter_others(self, value, prop):
        for a in self._other_artists:
            m = getattr(a, 'set_'+prop)
            m(value)

    def _getter_others(self, prop):
        a = self._other_artists[0]
        m = getattr(a, 'get_'+prop)
        return m()

#
#   data extent
#
    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x, y = self._eval_xy()  # this handles "use_var"
        if self.isempty():
            if x is None:
                self._data_extent = [0, len(y), np.nanmin(y), np.nanmax(y)]
            else:
                self._data_extent = [np.nanmin(x), np.nanmax(
                    x), np.nanmin(y), np.nanmax(y)]
        else:
            xr = (np.inf, -np.inf)
            yr = (np.inf, -np.inf)
            for a in self._artists:
                x = a.get_xdata()
                y = a.get_ydata()
                xr = (min((xr[0], np.nanmin(x))), max((xr[1], np.nanmax(x))))
                yr = (min((yr[0], np.nanmin(y))), max((yr[1], np.nanmax(y))))
            self._data_extent = [xr[0], xr[1], yr[0], yr[1]]
        return self._data_extent

#
#   range
#
    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if x is None:
            return
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        def calc_yrange(x, y, xrange, yrange, scale):
            # x.ndim = 1, y.ndim = 1 in this func
            idx = np.where((x >= xrange[0]) & (x <= xrange[1]))
            check = False
            for ar in idx:
                if len(ar) == 0:
                    check = True
            if check:
                return yrange

            yy = y[idx]
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
            x, y = self._eval_xy()

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

    def _saveload_names(self):
        return ['x', 'y']

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
                    var[name+'data'] = np.array([0, 0])
        data['FigTriplot'] = (1, var)
        data = super(FigTriplot, self).save_data2(data)

        return data

    def prepare_compact_savemode(self):
        var_bk = self._var.copy()
        self._var['x'] = np.array([0, 0])
        self._var['y'] = np.array([0, 0])
        return var_bk

    def load_data2(self, data):
        d = data['FigTriplot']
        super(FigTriplot, self).load_data2(data)
        var = d[1]
        names = self._saveload_names()
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_xy(self):
        names = ("x", "y")
        if self._tri is None:
            self._tri = self.getvar('tri')
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)
