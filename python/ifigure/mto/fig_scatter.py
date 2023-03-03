#
#   fig_scatter
#
#       support scatter plot
#
#       in matplotlib
#       scatter(x, y, s=20, c=u'b', marker=u'o', cmap=None,
#               norm=None, vmin=None, vmax=None, alpha=None,
#               linewidths=None, verts=None, **kwargs)
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, CUser, ZUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import sys
import numpy as np
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
from scipy.interpolate import griddata, bisplrep, bisplev, interp2d
from ifigure.utils.cbook import ProcessKeywords
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox
from ifigure.utils.args_parser import ArgsParser
from matplotlib.colors import Colormap

#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigScatter')

default_kargs = {}


class FigScatter(FigObj, XUser, YUser, ZUser, CUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._tri = None
            for key in default_kargs:
                if not obj.hasp(key):
                    obj.setp(key, default_kargs[key])
                if not obj.hasvar(key):
                    obj.setvar(key, default_kargs[key])
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_var('x', ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_opt('z', None, ['numbers|nonstr'])
        p.add_key('s', 20)
        p.add_key('c', 'b', ['numbers', 'str'])
        p.add_key('marker', 'o')
        p.add_key('sscale', 1.0)
        p.set_ndconvert("x", "y", "z",)
        p.set_squeeze_minimum_1D("x", "y", "z", )
#        p.set_default_list(default_kargs)
        p.add_key('alpha', 1.0)
        p.add_key('cmap', 'jet')

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('x', 'y', 'z', 's', 'c', 'alpha',  'marker', 'sscale'):
            obj.setvar(name, v[name])
        if v['cmap'] is not None:
            if isinstance(v['cmap'], Colormap):
                v['cmap'] = v['cmap'].name
            kywds['cmap'] = v['cmap']
            del v['cmap']
        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args, **kywds):
        self._data_extent = None
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)
        CUser.__init__(self)

        self._pick_pos = None
        self._cb_added = False
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigScatter, self).__init__(**kywds)

    @classmethod
    def isFigScatter(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'scatter'

    @classmethod
    def property_in_file(self):
        return (["linewidth"] +
                super(FigScatter, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return ["marker_2", "linewidthz", "scatter_sscale", "alpha_2"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ([] +
                super(FigScatter, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'image.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)
        super(FigScatter, self).set_parent(parent)
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
        names = ["x", "y", "z"] + names0
        use_np = [True]*3 + [False]*len(names0)
        values = self.put_args2var(names,
                                   use_np)
        x, y, z, = values[:3]
        if x is None:
            return False
        if y is None:
            return False

        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        container = self.get_container()
        if container is None:
            return
#           if self.get_figaxes().get_3d(): return
        if self.isempty() is False:
            return
        x, y, z = self._eval_xyz()
        lp = self.getp("loaded_property")

        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return
        crange = cax.range

        if lp is None or len(lp) == 0:
            if self.get_figaxes().get_3d():
                args = (x, y, z)
                extent = (np.min(x), np.max(x),
                          np.min(y), np.max(y), )
            else:
                args = (x, y)
                extent = (self.get_xaxisparam().range +
                          self.get_yaxisparam().range)

            kywds = self._var["kywds"].copy()
            kywds['alpha'] = self.getvar('alpha')
            kywds['s'] = self.getvar('s')*self.getvar('sscale')
            kywds['c'] = self.getvar('c')
            kywds['marker'] = self.getvar('marker')
            if cax.scale == 'linear':
                kywds["vmin"] = crange[0]
                kywds["vmax"] = crange[1]
            else:
                # args.append(np.log10(zp))
                kywds["vmin"] = np.log10(max((crange[0], 0)))
                kywds["vmax"] = np.log10(max((crange[1], 0)))

            self.set_artist(container.scatter(*args,
                                              **kywds))
            cax.set_crangeparam_to_artist(self._artists[0])
        else:
            x, y, z = self.getp(('x', 'y', 'z'))
            if self.get_figaxes().get_3d():
                args = (x, y, z)
                extent = (np.min(x), np.max(x),
                          np.min(y), np.max(y), )
            else:
                args = (x, y,)
                extent = (self.get_xaxisparam().range +
                          self.get_yaxisparam().range)

            kywds = lp[0]
            kywds['s'] = self.getvar('s')*self.getvar('sscale')
            kywds['c'] = self.getvar('c')
            kywds['marker'] = self.getvar('marker')
            self.set_artist(container.scatter(*args,
                                              **kywds))
            cax.set_crangeparam_to_artist(self._artists[0])
        self.delp("loaded_property")

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = self._artists

        self.store_loaded_property()

#        self.highlight_artist(False, artistlist)
        for a in artistlist:
            a.remove()

        super(FigScatter, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        alist = self._artists
        container = self.get_container()
        if val == True:
            x, y, z = self.getp(('x', 'y', 'z'))
            if self.get_figaxes().get_3d():
                args = (x, y, z)
            else:
                args = (x, y)
            kwargs = {'marker': 's',
                      'color': 'k',
                      'linestyle': 'None',
                      'markerfacecolor': 'None',
                      'markeredgewidth': 0.5,
                      'scalex': False, 'scaley': False}

            hl = container.plot(*args, **kwargs)
            for a in alist:
                for item in hl:
                    a.figobj_hl.append(item)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    hl.remove()
                a.figobj_hl = []

    def picker_a(self, artist, evt):
        hit, extra = artist.contains(evt)
        if hit:
            return True,  {'child_artist': artist}
        else:
            return False, {}

    def set_marker(self, value, a):
        if self.getvar('marker') == value:
            return
        self.setvar('marker', value)
        if len(self._artists) > 0:
            a1 = self._artists[0]
            self.refresh_artist_data()
            a2 = self._artists[0]
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def get_marker(self, a):
        return self.getvar('marker')

    def set_sscale(self, value, a):
        if self.getvar('sscale') == value:
            return

        self.setvar('sscale', value)
        if len(self._artists) > 0:
            a1 = self._artists[0]
            self.refresh_artist_data()
            a2 = self._artists[0]
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def get_sscale(self, a):
        return self.getvar('sscale')

    def set_linewidth(self, value, a):
        v = [value for x in self._artists[0].get_linewidth()]
        self._artists[0].set_linewidth(tuple(v))

    def get_linewidth(self, value):
        v = self._artists[0].get_linewidth()
        if len(v) > 1:
            return None
        else:
            return v[0]

    def set_alpha(self, value, a):
        self.setvar('alpha', value)
        fc = self._artists[0].get_facecolor()
        fc = [(x[0], x[1], x[2], value) for x in fc]
        self._artists[0].set_facecolor(tuple(fc))

    def get_alpha(self, a):
        return self.getvar('alpha')

    def get_mappable(self):
        return [a for a in self._artists if isinstance(a, ScalarMappable)]

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y, z = self._eval_xyz()
        if x is None:
            return xrange
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()
        x, y, z = self._eval_xyz()
        if x is None:
            return yrange
        if y is None:
            return yrange
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        x, y, z = self._eval_xyz()
        c = self.getvar('c')
        if isinstance(c, str):
            return crange
        if hasattr(c, 'ndim'):
            if c.ndim > 1:
                return crange
        return self._update_range(crange, (np.nanmin(c), np.nanmax(c)))

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if self.get_figaxes().get_3d():
            x, y, z = self._eval_xyz()
            return self._update_range(zrange, (np.nanmin(z), np.nanmax(z)))
        else:
            return zrange

    def _eval_xyz(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None
        return self.getp(("x", "y", "z"))

    def _saveload_names(self):
        return ['x', 'y', 'z']

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
        data['FigScatter'] = (1, var)
        data = super(FigScatter, self).save_data2(data)

        return data

    def load_data2(self, data):
        d = data['FigScatter']
        super(FigScatter, self).load_data2(data)
        var = d[1]
        names = self._saveload_names()
        for name in names:
            if not name in var:
                var[name] = True
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])
