from __future__ import print_function
import ifigure.utils.debug as debug
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists, GlobalHistory
import ifigure.widgets.canvas.custom_picker as cpicke
from ifigure.utils.args_parser import ArgsParser
import ifigure.utils.cbook as cbook
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.mto.fig_obj import FigObj, mask_negative
import ifigure.events
import ifigure
import weakref
import wx
import os
import sys
import logging
import numpy as np

from matplotlib.cm import ScalarMappable
from matplotlib.colors import ColorConverter
cc = ColorConverter()


dprint1, dprint2, dprint3 = debug.init_dprints('FigQuiver')

default_kargs = {'alpha':  1.0,
                 'pivot':  'tail',
                 'cmap':  'jet'}


class FigQuiver(FigObj, XUser, YUser, CUser):
    def __new__(cls, *args, **kywds):
        """
        quiver : quiver plot 
        quiver(U, V, **kargs)
        quiver(U, V, C, **kargs)
        quiver(X, Y, U, V, **kargs)
        quiver(X, Y, U, V, C, **kargs)
        """
        def set_hidden_vars(obj):
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj
        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_opt('y', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('u', ['numbers|nonstr', 'dynamic'])
        p.add_var('v', ['numbers|nonstr', 'dynamic'])
        p.add_opt('c', None, ['numbers|nonstr', 'dynamic'])

        p.set_default_list(default_kargs)
        p.add_key2(("alpha", "cmap"))
        p.add_key2(("pivot", "pivot"))
        p.set_pair("x", "y")  # x and y should be given
        # together
        p.set_ndconvert("x", "y", "u", "v", "c")
#        p.set_squeeze_minimum_1D("x","y","z")

        v, kywds, d, flag = p.process(*args, **kywds)
        dprint2(d)

        if not flag:
            raise ValueError('Failed when processing argument')
            return None

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('u', 'v', 'c', 'x', 'y'):
            obj.setvar(name, v[name])
        for name in ('alpha', 'cmap', 'pivot'):
            obj.setvar(name, v[name])

        if v['cmap'] is not None:
            kywds['cmap'] = v['cmap']

        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args, **kywds):
        self._data_extent = None
        XUser.__init__(self)
        YUser.__init__(self)
        CUser.__init__(self)

        self._pick_pos = None
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigQuiver, self).__init__(**kywds)

    @classmethod
    def isFigQuiver(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'quiver'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'plot1.png')
        return [idx1]

    @classmethod
    def attr_in_file(self):
        return (["alpha", "pivot"] +
                super(FigQuiver, self).attr_in_file())

    def property_in_file(self):
        return (['facecolor', 'edgecolor',  'elinewidth', 'alpha'] +
                super(FigQuiver, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return (['quiver', 'path', 'patch'], [
            ["qheadlength", "qheadwidth", "qpivot",
             "alpha_2"],
            ["pedgecolor_2", "elinewidth"],
            ["facecolor_2"]])

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        CUser.unset_ac(self)
        super(FigQuiver, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
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
        names = ["x", "y", "u", "v", "c"] + names0
        use_np = [True]*5 + [False]*(len(names0))
        # n and v can be dynamic too.
        values = list(self.put_args2var(names,
                                        use_np))
        if values[0] is None:
            u = values[2]
            if len(u.shape) != 2:
                return False
            x = np.arange(u.shape[1])
            y = np.arange(u.shape[0])
            values[0], values[1] = np.meshgrid(x, y)

        self.setp('x', values[0])
        self.setp('y', values[1])
        self.setp('u', values[2])
        self.setp('v', values[3])
        self.setp('c', values[4])
        return True

    def _eval_xyz(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None, None, None
        return self.getp(("x", "y", "u", "v", "c"))

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

        flag = 0
        if self.isempty() is False:
            return
        x, y, u, v, c = self._eval_xyz()  # this handles "use_var"
        if u is None:
            return
        if v is None:
            return

        lp = self.getp("loaded_property")

#           v, n, FillMode = self.getp(('v', 'n', 'FillMode'))

        kywds = self.getvar('kywds')
        kywds['alpha'] = self.getp('alpha')

        args = []
        if (x is not None and y is not None):
            args.append(x)
            args.append(y)
        args.append(u)
        args.append(v)
        if c is not None:
            args.append(c)
        cax = self.get_caxisparam()

        dprint2(args)
        if len(args) == 0:
            return

        self._data_extent = [np.min(x), np.max(x), np.min(y), np.max(y)]

        try:
            a = container.quiver(*args, **kywds)
            self._artists = [a]
            a.figobj = self
            a.figobj_hl = []
            a.set_zorder(self.getp('zorder'))

            if c is not None:
                self._mappable = self._artsits
            for a in self.get_mappable():
                cax.set_crangeparam_to_artist(a)
        except Exception:
            logging.exception(
                "FigQuiver:generate_artist : artist generation failed")

        if lp is not None:
            #              print lp
            for i, var in enumerate(lp):
                if len(self._artists) > i:
                    self.set_artist_property(self._artists[i], var)
            self.delp("loaded_property")

    def del_artist(self, artist=None, delall=False):
        #
        #  delete highlight and artist
        #  for fig_contour, all artists are treated
        #  as one set. it does not support to delete
        #  a part of path collections
        delall = True
        if delall:
            artistlist = self._artists
        else:
            artistlist = self._artists

        self.store_loaded_property()
#        if not self.hasp("loaded_property"):
#             self.load_data2(self.save_data2({}))
#        self.highlight_artist(False)
        for a in artistlist:
            a.remove()
        self._mappable = None
        super(FigQuiver, self).del_artist(artistlist)

    def get_mappable(self):
        if self.getp('c') is not None:
            return self._artists
        else:
            return []

    def reset_artist(self):
        #        print('resetting contour artist')
        self.del_artist(delall=True)
# (why not)  self.delp('loaded_property')
        self.setp('use_var', True)
        self.generate_artist()

    def highlight_artist(self, val, artist=None):
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

            try:
                x = self.getp('x').flatten()
                y = self.getp('y').flatten()
            except:
                return
            hl = container.plot(x, y, marker='s',
                                color='k', linestyle='None',
                                markerfacecolor='None',
                                markeredgewidth=0.5,
                                scalex=False, scaley=False)
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
#   HitTest
#
    def picker_a(self, artist, evt):
        if artist.contains(evt)[0]:
            return True, {'child_artist': artist}
        return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0
    #
    #  getter/setter
    #

    def set_alpha(self, value, a):
        for a in self._artists:
            a.set_alpha(value)

    def get_alpha(self, a):
        v = self._artists[0].get_alpha()
        return v

    def set_edgecolor(self, value, a):
        for a in self._artists:
            a.set_edgecolor(value)

    def get_edgecolor(self, a):
        v = a.get_edgecolor()
        return v[0]

    def set_facecolor(self, value, a):
        for a in self._artists:
            a.set_facecolor(value)

    def get_facecolor(self, a):
        v = a.get_facecolor()
        return v[0]

    def set_elinewidth(self, value, a):
        for a in self._artists:
            a.set_linewidth(value)

    def get_elinewidth(self, a):
        v = a.get_linewidth()
        if len(v) > 0:
            return v[0]
        return ['1.0']

    def set_angles(self, v, a):
        a.angles = str(v)
        a._new_UV = True

    def set_headlength(self, v, a):
        a.headlength = float(v)
        a._new_UV = True

    def set_headaxislength(self, v, a):
        a.headaxislength = float(v)
        a._new_UV = True

    def set_headwidth(self, v, a):
        a.headwidth = float(v)
        a._new_UV = True

    def set_pivot(self, v, a):
        return self.setp('pivot', v)

    def get_angles(self, a):
        return a.angles

    def get_headlength(self, a):
        return a.headlength

    def get_headaxislength(self, a):
        return a.headaxislength

    def get_headwidth(self,  a):
        return a.headwidth

    def get_pivot(self, a):
        return self.getp('pivot')

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y, u, v, c = self._eval_xyz()  # this handles "use_var"
        if x is None:
            return
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()
        x, y, u, v, c = self._eval_xyz()  # this handles "use_var"
        if x is None:
            return
        if y is None:
            return
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):

        x, y, u, v, c = self._eval_xyz()  # this handles "use_var"
        if c is None:
            return crange
        return crange

        ###
        if (x is None or
                y is None):
            x = np.arange(z.shape[1])
            y = np.arange(z.shape[0])

        if (xrange[0] is not None and
            xrange[1] is not None and
            yrange[0] is not None and
                yrange[1] is not None):
            zt = np.ma.masked_array(z)
            zt[(y < yrange[0]) | (y > yrange[1]), :] = np.ma.masked
            zt[:, (x < xrange[0]) | (x > xrange[1])] = np.ma.masked
            if scale == 'log':
                zt[z <= 0] = np.ma.masked
            crange = self._update_range(crange, (np.amin(zt), np.amax(zt)))
        return crange

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
               'u': check(self, 'u'),
               'v': check(self, 'v'),
               'c': check(self, 'c')}

        if not var["x"]:
            if self._save_mode == 0:
                var["xdata"] = self.getp("x")
            else:
                var["xdata"] = np.array([[0, 1], [0, 1]])
        if not var["y"]:
            if self._save_mode == 0:
                var["ydata"] = self.getp("y")
            else:
                var["ydata"] = np.array([[0, 0], [1, 1]])
        if not var["u"]:
            if self._save_mode == 0:
                var["udata"] = self.getp("u")
            else:
                var["udata"] = np.array([[1, 1], [1, 1]])
        if not var["v"]:
            if self._save_mode == 0:
                var["vdata"] = self.getp("v")
            else:
                var["vdata"] = np.array([[1, 1], [1, 1]])
        if not var["c"]:
            if self._save_mode == 0:
                var["cdata"] = self.getp("c")
            else:
                var["cdata"] = np.array([[1, 1], [1, 1]])

        data['FigQuiver'] = (1, var)
        data = super(FigQuiver, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigQuiver']
        super(FigQuiver, self).load_data2(data)
        dprint2('load_data2', d[1])
        var = d[1]
        names = ["x", "y", "u", "v", "c"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])


class FigQuiver3D(FigQuiver, ZUser):
    def __new__(cls, *args, **kywds):
        """
        quiver(X, Y, Z, U, V, W, **kwargs)
        """
        def set_hidden_vars(obj):
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        if 'cz' in kywds and kywds['cz']:
            def_alpha = None
            def_ec = None
            def_fc = None
            def_lw = 0.0
        else:
            def_alpha = 1.0
            def_ec = (0, 0, 0, 1)
            def_fc = (0, 0, 1, 1)
            def_lw = 1.0

        p = ArgsParser()
        p.add_var('x', ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])
        p.add_var('z', ['numbers|nonstr', 'dynamic'])
        p.add_var('u', ['numbers|nonstr', 'dynamic'])
        p.add_var('v', ['numbers|nonstr', 'dynamic'])
        p.add_var('w', ['numbers|nonstr', 'dynamic'])
        p.add_key('cz', False, 'bool')
        p.add_key('cdata', None)
        p.set_default_list(default_kargs)
        p.add_key2(("cmap"))
        p.add_key2(("pivot", "pivot"))
        p.add_key("length", 1.0)
        p.add_key("arrow_length_ratio", 0.3)
        p.add_key('alpha', def_alpha)
        p.add_key('facecolor', def_fc)
        p.add_key('edgecolor', def_ec)

        p.set_ndconvert("x", "y", "z", "u", "v", "w", "c")

        v, kywds, d, flag = p.process(*args, **kywds)
        dprint2(d)

        if not flag:
            raise ValueError('Failed when processing argument')
            return None

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('u', 'v', 'w', 'x', 'y', 'z'):
            obj.setvar(name, v[name])
        for name in ('alpha', 'cmap', 'pivot', 'length', 'arrow_length_ratio',
                     'cz', 'cdata', 'facecolor', 'edgecolor'):
            obj.setvar(name, v[name])

        if v['cmap'] is not None:
            kywds['cmap'] = v['cmap']

        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args, **kywds):
        ZUser.__init__(self)
        super(FigQuiver3D, self).__init__(**kywds)

    @classmethod
    def get_namebase(self):
        return 'quiver3d'

    @classmethod
    def attr_in_file(self):
        return (["length", "arrow_length_ratio", "facecolor", "edgecolor",
                 "linewidth", ] +
                super(FigQuiver3D, self).attr_in_file())

    @classmethod
    def property_in_palette(self):
        return (['quiver', 'path/patch'], [
            ["qpivot", "q3dlength", "q3dratio", "alpha_2"],
            ["facecolor_2", "edgecolor_2", "elinewidth"], ])

    def set_parent(self, parent):
        ZUser.unset_az(self)
        super(FigQuiver3D, self).set_parent(parent)
        ZUser.get_zaxisparam(self)

    def _args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y", "z", "u", "v", "w"] + names0
        use_np = [True]*6 + [False]*(len(names0))
        # n and v can be dynamic too.
        values = list(self.put_args2var(names,
                                        use_np))
        if values[0] is None:
            u = values[2]
            if len(u.shape) != 2:
                return False
            x = np.arange(u.shape[1])
            y = np.arange(u.shape[0])
            values[0], values[1] = np.meshgrid(x, y)

        self.setp('x', values[0])
        self.setp('y', values[1])
        self.setp('z', values[2])
        self.setp('u', values[3])
        self.setp('v', values[4])
        self.setp('w', values[5])
        return True

    def _eval_xyzw(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None, None, None
        return self.getp(("x", "y", "z", "u", "v", "w"))

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
        if not self.get_figaxes().get_3d():
            return
        flag = 0
        if self.isempty() is False:
            return
        x, y, z, u, v, w = self._eval_xyzw()  # this handles "use_var"
        if u is None:
            return
        if v is None:
            return
        if w is None:
            return

        lp = self.getp("loaded_property")

#           v, n, FillMode = self.getp(('v', 'n', 'FillMode'))

        kywds = self.getvar('kywds')
        kywds['alpha'] = self.getp('alpha')
        kywds['length'] = self.getp('length')
        kywds['pivot'] = self.getp('pivot')
        kywds['arrow_length_ratio'] = self.getp('arrow_length_ratio')

        kywds['alpha'] = self.getp('alpha') if self.getp(
            'alpha') is not None else 1

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
        if self.getvar('cz'):
            kywds['cz'] = self.getvar('cz')
            if self.getvar('cdata') is not None:
                cdata = self.getvar('cdata')
            else:
                cdata = z
            if np.iscomplexobj(cdata):
                kywds['facecolordata'] = cdata.real
            else:
                kywds['facecolordata'] = cdata
        else:
            kywds['facecolor'] = (fc,)
        kywds['edgecolor'] = (ec,)
        kywds['linewidths'] = 0.0 if self.getp(
            'linewidth') is None else self.getp('linewidth')

        args = (x, y, z, u, v, w)
        cax = self.get_caxisparam()

        dprint2(args)
        if len(args) == 0:
            return

        self._data_extent = [np.min(x), np.max(x), np.min(y), np.max(y)]

        try:
            a = container.quiver(*args, **kywds)
            self._artists = [a]
            a.figobj = self
            a.figobj_hl = []
            a.set_zorder(self.getp('zorder'))

            for a in self.get_mappable():
                cax.set_crangeparam_to_artist(a)
        except Exception:
            logging.exception(
                "FigQuiver3D:generate_artist : artist generation failed")

        if lp is not None:
            # print lp
            for i, var in enumerate(lp):
                if len(self._artists) > i:
                    self.set_artist_property(self._artists[i], var)
            self.delp("loaded_property")

    def highlight_artist(self, val, artist=None):
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

            try:
                x = self.getp('x').flatten()
                y = self.getp('y').flatten()
                z = self.getp('z').flatten()
            except:
                return
            hl = container.plot(x, y, z, marker='s',
                                color='k', linestyle='None',
                                markerfacecolor='None',
                                markeredgewidth=0.5,
                                scalex=False, scaley=False)
            for item in hl:
                alist[0].figobj_hl.append(item)
        else:
            for a in alist:
                if len(a.figobj_hl) == 0:
                    continue
                for hl in a.figobj_hl:
                    hl.remove()
                a.figobj_hl = []

    def get_mappable(self):
        if self.getvar('cz'):
            return [a for a in self._artists if isinstance(a, ScalarMappable)]
        else:
            return []

    def set_edgecolor(self, value, a):
        for a in self._artists:
            a.set_edgecolor(value)
            a._update_ec = True
            print('update_ec')

    def _update_artist(self):
        self.highlight_artist(False)
        self.del_artist(delall=True)
        # self.delp('loaded_property')
        self.generate_artist()
        sel = [weakref.ref(self._artists[0])]
        import wx
        app = wx.GetApp().TopWindow
        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)

    def set_pivot(self, v, a):
        self.setp('pivot', v)
        self._update_artist()

    def set_edgecolor(self, value, a):
        self.setp('edgecolor', value)
        a.set_edgecolor([value])

    def get_edgecolor(self, a=None):
        return self.getp('edgecolor')

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

    def set_q3dlength(self, v, a):
        self.setp('length', float(v))
        self._update_artist()

    def get_q3dlength(self, a):
        return self.getp('length')

    def set_q3dratio(self, v, a):
        self.setp('arrow_length_ratio', float(v))
        self._update_artist()

    def get_q3dratio(self, a):
        return self.getp('arrow_length_ratio')

    #
    #  xyzc-range
    #

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y, z, u, v, w = self._eval_xyzw()  # this handles "use_var"
        if x is None:
            return
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()
        x, y, z, u, v, w = self._eval_xyzw()  # this handles "use_var"
        if y is None:
            return
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        x, y, z, u, v, w = self._eval_xyzw()  # this handles "use_var"
        if z is None:
            return
        if scale == 'log':
            z = mask_negative(z)
        return self._update_range(zrange, (np.nanmin(z), np.nanmax(z)))

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        cdata = self.getvar('cdata')
        cz = self.getvar('cz')
        if not cz:
            return crange
        if cdata is None:
            x, y, z, u, v, w = self._eval_xyzw()  # this handles "use_var"
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

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        var = {'z': check(self, 'z'),
               'w': check(self, 'w')}
        if not var["z"]:
            if self._save_mode == 0:
                var["zdata"] = self.getp("z")
            else:
                var["zdata"] = np.array([[0, 1], [0, 1]])
        if not var["w"]:
            if self._save_mode == 0:
                var["wdata"] = self.getp("w")
            else:
                var["ydata"] = np.array([[0, 0], [1, 1]])

        data['FigQuiver3D'] = (1, var)
        data = super(FigQuiver3D, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigQuiver3D']
        super(FigQuiver3D, self).load_data2(data)
        dprint2('load_data2', d[1])
        var = d[1]
        names = ["w", "z"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])
