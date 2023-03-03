from __future__ import print_function
#
#  Name   :fig_fill.py
#
#          FigFill is the class to support patchcollections.
#          It supports Axes.fill, fill_between, and fill_betweenx.
#          A pathce attritube is changed simultaneously.
#
#          Matplotlib generates either Polygon or PolyCollection
#          FigFill absorbes the differecne of set_xxx/get_xxx of
#          these two.
#
#          Changes:
#             2014 02 11 properties are edited using mode=2 (not mode=1)
#
#
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#  History :
#         2013 03    ver.0.1
#              04    ver.0.2 large rewrite to unifiy interface

from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, ZUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
from ifigure.utils.cbook import isiterable, ProcessKeywords, LoadImageFile
import matplotlib
from matplotlib.collections import PolyCollection
from matplotlib.patches import Polygon

from ifigure.utils.args_parser import ArgsParser

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigFill')


def _arg_names(mpl_cmd):
    if mpl_cmd == 'fill':
        return ("x", "y")
    elif mpl_cmd == 'fill_between':
        return ("x", "y", "y2", "where")
    elif mpl_cmd == 'fill_betweenx':
        return ("y", "x", "x2", "where")


class FigFill(FigObj, XUser, YUser, ZUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._mpl_cmd = 'fill'
            obj._data_extent = None
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        mpl_cmd, kywds = ProcessKeywords(kywds, 'mpl_command', 'fill')
        p = ArgsParser()

        if mpl_cmd == 'fill_betweenx':
            p.add_var('y', ['iter|nonstr', 'dynamic'])
            p.add_opt('x', None, ['iter|nonstr', 'dynamic'])
        else:
            p.add_opt('x', None, ['iter|nonstr', 'dynamic'])
            p.add_var('y', ['iter|nonstr', 'dynamic'])
        #if mpl_cmd == 'fill':
        #    p.add_opt('s', '', 'str')

        p.add_key('x2', None)
        p.add_key('y2', None)
        p.add_key('where', None)
        p.add_key('edgecolor', 'black')
        p.add_key('linewidth', 1.0)
        p.add_key('linestyle', 'solid')
        p.add_key('alpha', 1)
        p.add_key('facecolor', 'blue')
        p.add_key('zs', 0)

        p.set_ndconvert("x", "y", "x2", "y2")

        v, kywds, d, flag = p.process(*args, **kywds)

        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)
        obj._mpl_cmd = mpl_cmd
        if v["x"] is None:
            v["x"] = np.arange(v["y"].shape[-1])
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args,  **kywds):
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)

        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigFill, self).__init__(*args, **kywds)

    @classmethod
    def isFigFill(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return True

    @classmethod
    def get_namebase(self):
        return 'fill'

    @classmethod
    def property_in_file(self):
        return []

    @classmethod
    def property_in_palette(self):
        return (["path", "patch"],
                [["edgecolor_2", "linewidth_2",
                  "plinestyle_2", "alpha_2"],
                 ["facecolor_2"]])

    @classmethod
    def attr_in_file(self):
        return (["edgecolor", "facecolor", "linewidth", "linestyle",
                 "alpha"]+super(FigFill, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'fill.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)

        super(FigFill, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)

    def args2var(self):
        names0 = self.attr_in_file()

        if self._mpl_cmd == 'fill':
            names = ["x", "y", "s"]
            use_np = [True, True, False]
        elif self._mpl_cmd == 'fill_between':
            names = ["x", "y", "y2", "where"]
            use_np = [True, True, True, True]
        elif self._mpl_cmd == 'fill_betweenx':
            names = ["x", "y", "x2", "where"]
            use_np = [True, True, True, True]

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

        if self._mpl_cmd == 'fill_between':
            if self.getp('y2') is None:
                self.setp('y2', np.zeros(self.getp('y').size))
        elif self._mpl_cmd == 'fill_betweenx':
            if self.getp('x2') is None:
                self.setp('x2', np.zeros(self.getp('x').size))

        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change

        container = self.get_container()

        if self.isempty() is False:
            return
        s = ""
        if self._mpl_cmd == 'fill':
            x, y = self._eval_xy()
        elif self._mpl_cmd == 'fill_between':
            x, y, y2, where = self._eval_xy()
        elif self._mpl_cmd == 'fill_betweenx':
            y, x, x2, where = self._eval_xy()

        kywds = self._var["kywds"].copy()

        kywds["alpha"] = self.getp('alpha')
        kywds["edgecolor"] = self.getp('edgecolor')
        kywds["linewidth"] = self.getp('linewidth')
        kywds["facecolor"] = self.getp('facecolor')
        kywds["linestyle"] = self.getp('linestyle')

        try:
            if self.get_figaxes().get_3d():
                kywds['zs'] = self.getvar('zs')
        except:
            pass
        try:
            print(kywds)
            if self._mpl_cmd == 'fill':
                self._artists = container.fill(x, y, **kywds)
            elif self._mpl_cmd == 'fill_between':
                kywds["y2"] = y2
                kywds["where"] = where
                self._artists = [container.fill_between(x, y, **kywds)]
            elif self._mpl_cmd == 'fill_betweenx':
                kywds["x2"] = x2
                kywds["where"] = where
                self._artists = [container.fill_betweenx(y, x, **kywds)]
        except:
            dprint1('Failed to generate artilst')
            import traceback
            print(traceback.format_exc())
            self._artists = []
            return
            pass

#        self.set_data_extent()    # set data extent
        dprint2(self._artists)
        lp = self.getp("loaded_property")
        if lp is not None:
            # do apply saved property...
            for i in range(len(lp)):
                if i < len(self._artists):
                    self.set_artist_property(self._artists[i], lp[i])
            self.delp("loaded_property")

        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        self.store_loaded_property()

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                try:
                    a.remove()
                except:
                    logging.exception("fig_fill:: highlight_aritst() failed")

        super(FigFill, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        container = self.get_container()
        from ifigure.matplotlib_mod.art3d_gl import Polygon3DGL, \
            Poly3DCollectionGL
        if val == True:
            for a in alist:
                if isinstance(a, Polygon3DGL):
                    pass
                elif isinstance(a, Poly3DCollectionGL):
                    hl = a.make_hl_artist(container)
                    for item in hl:
                        a.figobj_hl.append(item)

                elif hasattr(a, 'get_xy'):
                    xy = a.get_xy()
                    hl = container.plot(xy[:, 0], xy[:, 1], marker='s',
                                        color='k', linestyle='None',
                                        markerfacecolor='none',
                                        markeredgewidth=0.5,
                                        scalex=False, scaley=False)
                    for item in hl:
                        a.figobj_hl.append(item)
                else:
                    x = np.concatenate([p.vertices[:, 0]
                                        for p in a.get_paths()])
                    y = np.concatenate([p.vertices[:, 1]
                                        for p in a.get_paths()])
                    hl = container.plot(x, y, marker='s',
                                        color='k', linestyle='None',
                                        markerfacecolor='none',
                                        markeredgewidth=0.5,
                                        scalex=False, scaley=False)
                    for item in hl:
                        a.figobj_hl.append(item)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    hl.remove()
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
            return True, {'child_artist': artist}
        else:
            #            print('double check for picker')
            if hasattr(artist, 'get_verts'):
                # this is for Polygon object
                figure = self.get_figpage()._artists[0]
                v = artist.get_verts()
                hl = matplotlib.lines.Line2D(v[:, 0], v[:, 1], marker='s',
                                             color='k', linestyle='None',
                                             markerfacecolor='none',
                                             figure=figure)
                figure.lines.extend([hl])
                hit, extra = hl.contains(evt)
                figure.lines.remove(hl)
                if hit:
                    return True, {'child_artist': artist}
            return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0

#
#  Setter/Getter
#
    def _fill_setter(self, prop, value):
        from ifigure.utils.cbook import isiterable
        for a in self._artists:
            if isinstance(a, PolyCollection):
                m0 = getattr(a, 'get_'+prop)
                m = getattr(a, 'set_'+prop)
                if isiterable(m0()):
                    m([value]*len(m0()))
                else:
                    m(value)
            elif isinstance(a, Polygon):
                m = getattr(a, 'set_'+prop)
                m(value)
            else:
                dprint1('FigFill::Unknown artist type')

    def set_facecolor(self, value, a):
        self.setp('facecolor', value)
        self._fill_setter('facecolor', value)

    def get_facecolor(self, value):
        return self.getp('facecolor')

    def set_edgecolor(self, value, a):
        self.setp('edgecolor', value)
        self._fill_setter('edgecolor', value)

    def get_edgecolor(self, value):
        return self.getp('edgecolor')

    def set_linewidth(self, value, a):
        self.setp('linewidth', value)
        self._fill_setter('linewidth', value)

    def get_linewidth(self, value):
        return self.getp('linewidth')

    def set_linestyle(self, value, a):
        self.setp('linestyle', value)
        self._fill_setter('linestyle', value)

    def get_linestyle(self, value):
        return self.getp('linestyle')

    def set_alpha(self, value, a):
        self.setp('alpha', value)
        self._fill_setter('alpha', value)

    def get_alpha(self, value):
        return self.getp('alpha')

#
#   data extent
#
    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        if self._mpl_cmd == 'fill':
            x, y = self._eval_xy()
            if x is None:
                self._data_extent = [None]*4
            else:
                self._data_extent = [np.min(x), np.max(x),
                                     np.min(y), np.max(y)]
        elif self._mpl_cmd == 'fill_between':
            x, y, y2, where = self._eval_xy()
            if x is None:
                self._data_extent = [None]*4
            else:
                self._data_extent = [np.min(x), np.max(x),
                                     min([np.min(y), np.min(y2)]),
                                     max([np.max(y), np.max(y2)])]
        elif self._mpl_cmd == 'fill_betweenx':
            y, x, x2, where = self._eval_xy()
            if x is None:
                self._data_extent = [None]*4
            else:
                self._data_extent = [min([np.min(x), np.min(x2)]),
                                     max([np.max(x), np.max(x2)]),
                                     np.min(y), np.max(y)]

        return self._data_extent
#
#   range
#

    def get_xrange(self, xrange=[None, None], scale='linear'):
        if self._mpl_cmd == 'fill':
            x, y = self._eval_xy()
            if x is None:
                return
            if scale == 'log':
                x = mask_negative(x)
            return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])
        elif self._mpl_cmd == 'fill_between':
            x, y, y2, where = self._eval_xy()
            if x is None:
                return
            if scale == 'log':
                x = mask_negative(x)
            return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])
        elif self._mpl_cmd == 'fill_betweenx':
            y, x, x2, where = self._eval_xy()
            if x is None:
                return
            if x2 is None:
                return
            if scale == 'log':
                x = mask_negative(x)
                x2 = mask_negative(x2)
            return self._update_range(xrange, [np.nanmin([np.nanmin(x), np.nanmin(x2)]),
                                               np.nanmax([np.nanmax(x), np.nanmax(x2)])])

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        y0 = yrange[0]
        y1 = yrange[1]
        y0n = None
        y1n = None
        if (xrange[0] is not None and
                xrange[1] is not None):
            if self._mpl_cmd == 'fill':
                x, y = self._eval_xy()
                ym = np.ma.masked_array(y)
                ym[x < xrange[0]] = np.ma.masked
                ym[x > xrange[1]] = np.ma.masked
                if scale == 'log':
                    ym[x < 0] = np.ma.masked
                return self._update_range(yrange, [np.nanmin(ym), np.nanmax(ym)])
            elif self._mpl_cmd == 'fill_between':
                x, y, y2, where = self._eval_xy()
                ym = np.ma.masked_array(y)
                y2m = np.ma.masked_array(y2)
#                print y, y2
                ym[x < xrange[0]] = np.ma.masked
                ym[x > xrange[1]] = np.ma.masked
                y2m[x < xrange[0]] = np.ma.masked
                y2m[x > xrange[1]] = np.ma.masked
                if scale == 'log':
                    ym[x < 0] = np.ma.masked
                    y2m[x < 0] = np.ma.masked
                return self._update_range(yrange, [np.nanmin([np.nanmin(ym),  np.nanmin(y2m)]),
                                                   np.nanmax([np.nanmax(ym), np.nanmax(y2m)])])
            elif self._mpl_cmd == 'fill_betweenx':
                y, x, x2, where = self._eval_xy()
                ym = np.ma.masked_array(y)
                ym[x < xrange[0]] = np.ma.masked
                ym[x > xrange[1]] = np.ma.masked
                if scale == 'log':
                    ym[x < 0] = np.ma.masked
                return self._update_range(yrange, [np.nanmin(ym), np.nanmax(ym)])
        return yrange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        return self._update_range(zrange, [self.getvar('zs'), self.getvar('zs')])
#
#   export
#

    def get_export_val(self, a):
        v = {"xdata": self.getvar('x'),
             "ydata": self.getvar('y')}
        if self.getvar('x2') is not None:
            v["x2data"] = self.getvar('x2')
        if self.getvar('y2') is not None:
            v["y2data"] = self.getvar('y2')
        return v

#
#   save/load
#
    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        var = {'x': check(self, 'x'),
               'y': check(self, 'y'),
               'x2': check(self, 'x2'),
               'y2': check(self, 'y2'),
               'where': check(self, 'where'),
               's': check(self, 's'), }

        if var["x"] is not True:
            var["xdata"] = self.getp("x")
        if var["y"] is not True:
            var["ydata"] = self.getp("y")
        if var["x2"] is not True:
            var["x2data"] = self.getp("x2")
        if var["y2"] is not True:
            var["y2data"] = self.getp("y2")
        if var["where"] is not True:
            var["wheredata"] = self.getp("where")
        if var["s"] is not True:
            var["sdata"] = self.getp("s")
        var["mpl_cmd"] = self._mpl_cmd

        data['FigFill'] = (1, var)
        return super(FigFill, self).save_data2(data)

    def load_data2(self, data):
        d = data['FigFill']
        super(FigFill, self).load_data2(data)
        var = d[1]

        self._mpl_cmd = var["mpl_cmd"]
        names = ["x", "y", "x2", "y2", "s", "where"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_xy(self):
        names = _arg_names(self._mpl_cmd)
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)
