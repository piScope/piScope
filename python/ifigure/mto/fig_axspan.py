from __future__ import print_function
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.widgets.canvas.file_structure import *
from ifigure.mto.axis_user import XUser, YUser
from ifigure.mto.fig_obj import set_mpl_all, get_mpl_first
import ifigure
import os
import ifigure.utils.cbook as cbook
from ifigure.utils.geom import transform_point
import ifigure.widgets.canvas.custom_picker as cpicker
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
import numpy as np
import weakref

from ifigure.utils.args_parser import ArgsParser
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigAxspan')


def _special_xy_check(v):
    # special check for x and y
    try:
        if (len(v) == 2):
            x0 = v[0]
            x1 = v[1]
            if ((isinstance(x0, float) or isinstance(x0, int)) and
                    (isinstance(x1, float) or isinstance(x1, int))):
                return [[x0, x1]], True
        for item in v:
            if len(item) != 2:
                flag = False
    except:
        flag = False
        return [], flag
    return v, True


def _make_xy_x(x):
    return np.array([[x[0], 0], [x[0], 1], [x[1], 1], [x[1], 0], [x[0], 0]])


def _make_xy_y(y):
    return np.array([[0, y[0]], [1, y[0]], [1, y[1]], [0, y[1]], [0, y[0]]])


def _sort_data(data):
    return [[min(item), max(item)] for item in data]


def _is_data_clean(data):
    for item in data:
        if not (np.isfinite(item[0]) and np.isfinite(item[1])):
            return False
    return True


def _clean_data(data):
    return [item for item in data
            if np.isfinite(item[0]) and np.isfinite(item[1])]


class FigAxspan(FigObj, XUser, YUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []
            obj._drag_backup = None
            obj._drag_delta = None
            obj._drag_mode = 0
            obj._data_extent = None
            return obj
        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', [], ['can_ndreal_array|nonstr', 'dynamic', 'empty'])
        p.add_opt('y', [], ['can_ndreal_array|nonstr', 'dynamic', 'empty'])
        p.add_key('draggable', True)
        p.set_ndconvert("x", "y")
        v, kywds, d, flag = p.process(*args, **kywds)

        # special check for x and y
        if not 'x' in v:
            raise ValueError('can not parse arguments')
        if not 'y' in v:
            raise ValueError('can not parse arguments')
        v["x"], flag2 = _special_xy_check(v["x"])
        v["y"], flag3 = _special_xy_check(v["y"])

        if not flag or not flag2 or not flag3:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)

        obj = set_hidden_vars(obj)
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args,  **kywds):
        XUser.__init__(self)
        YUser.__init__(self)

        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        FigObj.__init__(self, *args, **kywds)

    @classmethod
    def isFigAxspan(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'axspan'

    @classmethod
    def property_in_file(self):
        return ["facecolor", "edgecolor", "linestyle",
                "linewidth", "alpha"]

    @classmethod
    def property_in_palette(self):
        return ["fill_2", "facecolor_2",
                "edgecolor_2", "plinestyle_2",
                "linewidth_2", "alpha_2"]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'plot1.png')
        return [idx1]

    def isDraggable(self):
        return self._var["draggable"]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        super(FigAxspan, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)

    def args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y"]
        use_np = [False]*2
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)

        x = values[0]
        y = values[1]
        if x is None:
            return False
        if y is None:
            return False
        x, flag = _special_xy_check(x)
        if not flag:
            return False
        y, flag = _special_xy_check(y)
        if not flag:
            return False
        try:
            if not _is_data_clean(x):
                return False
            if not _is_data_clean(y):
                return False
        except:
            return False
        x = np.array(_sort_data(x))
        y = np.array(_sort_data(y))
        self.setp("x", x)
        self.setp("y", y)
        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        #           container=self._parent._artists[0]
        container = self.get_container()
        if self.isempty() is False:
            return
#              self.del_artist(delall=True)

        x, y = self._eval_xy()
        for x1 in x:
            self._artists.append(container.axvspan(x1[0], x1[1],
                                                   **(self._var["kywds"])))
        for y1 in y:
            self._artists.append(container.axhspan(y1[0], y1[1],
                                                   **(self._var["kywds"])))

        self.set_rasterized()
        lp = self.getp("loaded_property")
        if lp is not None and len(lp) > 0:
            for i, a in enumerate(self._artists):
                #              for i in range(0, len(lp)):
                #                  if len(self._artists) > i:
                lpp = lp[i] if len(lp) > i else lp[-1]
                alpha = lpp['alpha']
#                   del lp[i]['alpha']
                self.set_artist_property(a,
                                         {"alpha": alpha})
                self.set_artist_property(a, lpp)

            self.delp("loaded_property")

        dprint3("generating axspan artist")
        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))
#             self._objs.append(weakref.ref(artist))

    def del_artist(self, artist=None, delall=False):
        #        if delall:
        #           artistlist=self._artists
        #        else:
        #           artistlist=artist
        artistlist = self._artists
        self.store_loaded_property()

#        val = []
#        for a in self._artists:
#           val.append(self.get_artist_property(a))
#        if len(val) != 0:
#           self.setp("loaded_property", val)

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                a.set_picker(None)
                a.remove()
#             container.lines.remove(a)

        super(FigAxspan, self).del_artist(artist=artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
#        container=self._parent._artists[0]
        container = self.get_container()
        if val == True:
            hl = []
            x, y = self._eval_xy()
            for x1 in x:
                hl.append(container.axvline(x1[0],  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
                hl.append(container.axvline(x1[1],  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
            for y1 in y:
                hl.append(container.axhline(y1[0],  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
                hl.append(container.axhline(y1[1],  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
            for a in alist:
                a.figobj_hl += hl

        else:
            for a in self._artists:
                for hl in a.figobj_hl:
                    try:
                        hl.remove()
                    except:
                        pass
                a.figobj_hl = []

#
#   HitTest
#
    def picker_a(self, a, evt):
        ###
        # it does not use contain to catch edges
        ###
        if not a in self._artists:
            return False, {}

        idx = self._artists.index(a)
        x = self.getp("x")
        if idx >= len(x):
            mode = 'h'
        else:
            mode = 'v'
        xy = a.get_xy()
        axes = a.axes
        x0d, y0d = transform_point(axes.transData,
                                   min(xy[:, 0]), min(xy[:, 1]))
        x1d, y1d = transform_point(axes.transData,
                                   max(xy[:, 0]), max(xy[:, 1]))
        x0da, y0da = transform_point(axes.transAxes,
                                     min(xy[:, 0]), min(xy[:, 1]))
        x1da, y1da = transform_point(axes.transAxes,
                                     max(xy[:, 0]), max(xy[:, 1]))

        hit = False
        if mode == 'v':
            if (evt.x > x0d-5 and
                evt.x < x1d+5 and
                evt.y > y0da and
                    evt.y < y1da):
                hit = True
        else:
            if (evt.x > x0da and
                evt.x < x1da and
                evt.y > y0d-5 and
                    evt.y < y1d+5):
                hit = True
        if hit:
            return True, {'child_artist': a}
        return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0

    def dragstart_a(self, a, evt):
        return self.dragstart(a, evt)

    def dragstart(self, a, evt):
        if evt.inaxes is None:
            return 0
        axes = a.axes
        if axes is None:
            return 0

        if not a in self._artists:
            return False, {}
        idx = self._artists.index(a)
        x = self.getp("x")
        if idx >= len(x):
            mode = 'h'
        else:
            mode = 'v'

        self._drag_backup = (evt.xdata, evt.ydata, evt.x, evt.y)
        self._drag_delta = (0, 0)
        self._drag_mode = 1
        # 1 transpose
        # 2 x expand(smaller edge)
        # 3 x expand(larger edge)
        # 4 y expand(smaller edge)
        # 5 y expand(smaller edge)
        xy = a.get_xy()
        x0d, y0d = transform_point(axes.transData,
                                   min(xy[:, 0]), min(xy[:, 1]))
        x1d, y1d = transform_point(axes.transData,
                                   max(xy[:, 0]), max(xy[:, 1]))
#        print evt.x, x0d

        delta = 3
        if mode == 'v':
            if abs(evt.x - x0d) < delta:
                self._drag_mode = 2
            if abs(evt.x - x1d) < delta:
                self._drag_mode = 3
        else:
            if abs(evt.y - y0d) < delta:
                self._drag_mode = 4
            if abs(evt.y - y1d) < delta:
                self._drag_mode = 5

        return 0

    def drag_a(self, a, evt, shift=None, scale=None):
        return self.drag(a, evt), scale

    def drag(self, a, evt, idx='all'):
        if evt.xdata is None:
            return
        if evt.inaxes is None:
            return
        axes = a.axes
        x, y = self._eval_xy()
        dx = evt.xdata - self._drag_backup[0]
        dy = evt.ydata - self._drag_backup[1]
        dxd = (evt.x - self._drag_backup[2])
        dyd = (evt.y - self._drag_backup[3])
        if (evt.guiEvent.ShiftDown()):
            if abs(dxd) > 2*abs(dyd):
                dyd = 0
            elif abs(dyd) > 2*abs(dxd):
                dxd = 0

        i = 0
        for x0 in x:
            if idx != 'all' and idx != i:
                i = i+1
                continue
            xd, void = transform_point(axes.transData,
                                       x0[0], evt.ydata)
            x1, void = transform_point(axes.transData.inverted(),
                                       xd+dxd, void)
            xd, void = transform_point(axes.transData,
                                       x0[1], evt.ydata)
            x2, void = transform_point(axes.transData.inverted(),
                                       xd+dxd, void)
            if self._drag_mode == 1:
                xx = [x1, x2]
            elif self._drag_mode == 2:
                xx = [x1, x0[1]]
            elif self._drag_mode == 3:
                xx = [x0[0], x2]
            elif self._drag_mode == 4:
                xx = x0
            elif self._drag_mode == 5:
                xx = x0
            xy = _make_xy_x(xx)
            self._artists[i].set_xy(xy)
            i = i+1
        for y0 in y:
            if idx != 'all' and idx != i:
                i = i+1
                continue
            void, yd = transform_point(axes.transData,
                                       evt.xdata, y0[0])
            void, y1 = transform_point(axes.transData.inverted(),
                                       void, yd+dyd)
            void, yd = transform_point(axes.transData,
                                       evt.xdata, y0[1])
            void, y2 = transform_point(axes.transData.inverted(),
                                       void, yd+dyd)
            if self._drag_mode == 1:
                yy = [y1, y2]
            elif self._drag_mode == 2:
                yy = y0
            elif self._drag_mode == 3:
                yy = y0
            elif self._drag_mode == 4:
                yy = [y1, y0[1]]
            elif self._drag_mode == 5:
                yy = [y0[0], y2]
            xy = _make_xy_y(yy)
            self._artists[i].set_xy(xy)
            i = i+1
        self._drag_delta = (dxd, dyd)

    def drag_a_get_hl(self, a):
        return self.drag_get_hl(a)

    def drag_get_hl(self, a):
        self._alpha_backup = self.get_alpha(None)
        self.set_alpha(0.5, None)
        return self._artists

    def drag_a_rm_hl(self, a):
        return self.drag_rm_hl(a)

    def drag_rm_hl(self, a):
        self.set_alpha(self._alpha_backup, None)

    def dragdone_a(self, a, evt, shift=None, scale=None):
        return self.dragdone(a, evt), scale

    def dragdone(self, a, evt, idx='all'):
        axes = a.axes
        x, y = self._eval_xy()
        x = x.copy()
        y = y.copy()
        dxd, dyd = self._drag_delta

        if (evt.xdata is not None and
                evt.ydata is not None):
            i = 0
            xdata = []
            ydata = []
            for x0 in x:
                x1 = x0[:]
                if idx == 'all' or idx == i:
                    if (self._drag_mode == 1 or
                            self._drag_mode == 2):
                        xd, void = transform_point(axes.transData,
                                                   x0[0], evt.ydata)
                        x1[0], void = transform_point(axes.transData.inverted(),
                                                      xd+dxd, void)
                    if (self._drag_mode == 1 or
                            self._drag_mode == 3):
                        xd, void = transform_point(axes.transData,
                                                   x0[1], evt.ydata)
                        x1[1], void = transform_point(axes.transData.inverted(),
                                                      xd+dxd, void)
                xdata.append(x1)
                i = i + 1
            for y0 in y:
                y1 = y0[:]
                if idx == 'all' or idx == i:
                    if (self._drag_mode == 1 or
                            self._drag_mode == 4):
                        void, yd = transform_point(axes.transData,
                                                   evt.xdata, y0[0])
                        void, y1[0] = transform_point(axes.transData.inverted(),
                                                      void, yd+dyd)
                    if (self._drag_mode == 1 or
                            self._drag_mode == 5):
                        void, yd = transform_point(axes.transData,
                                                   evt.xdata, y0[1])
                        void, y1[1] = transform_point(axes.transData.inverted(),
                                                      void, yd+dyd)
                ydata.append(y1)
                i = i + 1
        else:
            xdata = x
            ydata = y

        xdata = np.array(xdata)
        ydata = np.array(ydata)
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data', (xdata, ydata))

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1
#
#  Popup in Canvas
#

    def onExport(self, event):
        from matplotlib.artist import getp
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        shell = self.get_root_parent().app.shell
        for a in self._artists:
            if a in sel:
                print("Exporting Data to Shell")
                xy = a.get_xy()
                fig_val = {"xdata": (min(xy[:, 0]), max(xy[:, 0])),
                           "ydata": (min(xy[:, 1]), max(xy[:, 1])), }
                self.write2shell(fig_val, "fig_val")
                break
        shell.redirectStdout(True)
        text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\']\"'
        shell.writeOut(text)
        shell.redirectStdout(False)
        # print "exporting data to file"

#
#   setter/getter
#
    def set_data(self, value, a):
        if (len(self._artists) != len(value[0]) + len(value[1]) or
            not _is_data_clean(value[0]) or
                not _is_data_clean(value[1])):
            x = _clean_data(value[0])
            y = _clean_data(value[1])
            x = _sort_data(x)
            y = _sort_data(y)
            self.setp("x", np.array(x))
            self.setp("y", np.array(y))
            self.del_artist()
            self.generate_artist()
        else:
            x = _sort_data(value[0])
            y = _sort_data(value[1])
            self.setp("x", np.array(x))
            self.setp("y", np.array(y))
            i = 0
            for x0 in x:
                xy = _make_xy_x(x0)
                self._artists[i].set_xy(xy)
                i = i+1
            for y0 in y:
                xy = _make_xy_y(y0)
                self._artists[i].set_xy(xy)
                i = i+1
        self._data_extent = None

    def get_data(self, a):
        return (self.getp('x')[:], self.getp('y')[:])

    def set_alpha(self, value, a):
        set_mpl_all(self._artists, 'alpha', value)

    def get_alpha(self, a):
        return get_mpl_first(self._artists, 'alpha')

    def set_fill(self, value, a):
        set_mpl_all(self._artists, 'fill', value)

    def get_fill(self, a):
        return get_mpl_first(self._artists, 'fill')

    def set_facecolor(self, value, a):
        set_mpl_all(self._artists, 'facecolor', value)

    def get_facecolor(self, a):
        return get_mpl_first(self._artists, 'facecolor')

    def set_edgecolor(self, value, a):
        set_mpl_all(self._artists, 'edgecolor', value)

    def get_edgecolor(self, a):
        return get_mpl_first(self._artists, 'edgecolor')

    def set_linestyle(self, value, a):
        set_mpl_all(self._artists, 'linestyle', value)

    def get_linestyle(self, a):
        return get_mpl_first(self._artists, 'linestyle')

    def set_linewidth(self, value, a):
        set_mpl_all(self._artists, 'linewidth', value)

    def get_linewidth(self, a):
        return get_mpl_first(self._artists, 'linewidth')

#
#   data extent
#
    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x, y = self._eval_xy()
        d = [None]*4
        if len(x) != 0:
            x1 = [min(item) for item in x if len(item) == 2]
            x2 = [max(item) for item in x if len(item) == 2]
            d[0] = min(x1)
            d[1] = max(x2)
        if len(y) != 0:
            y1 = [min(item) for item in y if len(item) == 2]
            y2 = [max(item) for item in y if len(item) == 2]
            d[2] = min(y1)
            d[3] = max(y2)
        self._data_extent = d
        return self._data_extent

#
#   range setting
#
    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if scale == 'log':
            x = mask_negative(x)
        if x.size > 0:
            return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])
        else:
            return super(FigAxspan, self).get_xrange(xrange=xrange, scale=scale)

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if scale == 'log':
            y = mask_negative(y)
        if y.size != 0:
            return self._update_range(yrange, [np.nanmin(y), np.nanmax(y)])
        else:
            return super(FigAxspan, self).get_yrange(yrange=yrange,
                                                     xrange=xrange, scale=scale)

    def save_data2(self, data=None):
        def check(obj, name):
            return obj.getp(name) is obj.getvar(name)
        if data is None:
            data = {}
        var = {'x': check(self, 'x'),
               'y': check(self, 'y')}

        if var["x"] is not True:
            var["xdata"] = self.getp("x")
        if var["y"] is not True:
            var["ydata"] = self.getp("y")

        data['FigAxspan'] = (1, var)
        data = super(FigAxspan, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigAxspan']
        super(FigAxspan, self).load_data2(data)
        var = d[1]
        names = ["x", "y"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_xy(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None
        return self.getp(("x", "y"))
