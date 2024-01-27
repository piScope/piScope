from __future__ import print_function
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.widgets.canvas.file_structure import *
from ifigure.mto.axis_user import XUser, YUser
from ifigure.mto.fig_obj import set_mpl_all, get_mpl_first
import ifigure
import os
from ifigure.utils.cbook import nd_iter, LoadImageFile
from ifigure.utils.geom import transform_point
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod


import numpy as np
import weakref

from ifigure.utils.args_parser import ArgsParser
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigAxline')


class FigAxline(FigObj, XUser, YUser):
    def __new__(cls, *args, **kywds):
        """
        FigAxline([x1,x2,x3...], [y1,y2,...])
        x is for vertical line
        y is for horizontal line
        """
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._drag_backup = None
            obj._drag_delta = None
            obj._data_extent = None
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', [], ['numbers|nonstr', 'dynamic', 'real', 'empty'])
        p.add_opt('y', [], ['numbers|nonstr', 'dynamic', 'real', 'empty'])
        p.set_ndconvert("x", "y")
        p.add_key('draggable', False)

        v, kywds, d, flag = p.process(*args, **kywds)
        if isinstance(v["x"], float) or isinstance(v["x"], int):
            v["x"] = [v["x"]]
        if isinstance(v["y"], float) or isinstance(v["y"], int):
            v["y"] = [v["y"]]

        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)
        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args,  **kywds):
        """
        FigAxline([x]) or FigAxline(x)   
        FigAxline([], [y]) or FigAxline(y)
        """
        XUser.__init__(self)
        YUser.__init__(self)

        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigAxline, self).__init__(*args, **kywds)

    @classmethod
    def isFigAxline(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'axline'

    @classmethod
    def property_in_file(self):
        return ["color", "linestyle",
                "linewidth", "marker", "alpha"]

    @classmethod
    def property_in_palette(self):
        return (["line", "marker"],
                [["color_2", "linestyle_2", "linewidth_2",
                  "alpha_2"],
                 ["markerfacecolor_2", "markeredgecolor_2", "marker_2",
                  "markersize_2", "markeredgewidth_2"], ])

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plot1.png')
        return [idx1]

    def isDraggable(self):
        return self.getvar("draggable")

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        super(FigAxline, self).set_parent(parent)
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

        x, y = self._eval_xy()
        for x1 in x:
            self._artists.append(container.axvline(x1,
                                                   **(self._var["kywds"])))
        for y1 in y:
            self._artists.append(container.axhline(y1,
                                                   **(self._var["kywds"])))
        self.set_rasterized()
        lp = self.getp("loaded_property")
        if lp is not None:
            for i in range(0, len(lp)):
                if len(self._artists) > i:
                    self.set_artist_property(self._artists[i], lp[i])
            self.delp("loaded_property")

        dprint3("generating axline artist")
        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))

    def del_artist(self, artist=None, delall=False):
        #        if delall:
        artistlist = self._artists
#        else:
#           artistlist=artist
        self.store_loaded_property()

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
#            container=self._parent._artists[0]
            for a in artistlist:
                a.remove()

        super(FigAxline, self).del_artist(artist=artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        container = self.get_container()
#        container=self._parent._artists[0]
        if val == True:
            hl = []
            x, y = self._eval_xy()

            for x1 in nd_iter(x):
                hl.append(container.axvline(x1,  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
            for y1 in nd_iter(y):
                hl.append(container.axhline(y1,  marker='s',
                                            color='k', linestyle='None',
                                            markeredgewidth=0.5,
                                            markerfacecolor='None'))
            for a in alist:
                a.figobj_hl += hl
        else:
            for a in self._artists:
                for hl in a.figobj_hl:
                    #if hl in container.lines:
                    #    container.lines.remove(hl)
                    hl.remove()
                a.figobj_hl = []
#
#   HitTest
#

    def picker_a(self, a, evt):
        hit = False
        axes = a.axes
        if axes is None:
            return False, {}
        x = a.get_xdata()[0]
        xd, yd = transform_point(axes.transData,
                                 x, 0)
        if abs(evt.x - xd) < 5:
            hit = True
        y = a.get_ydata()[0]
        xd, yd = transform_point(axes.transData,
                                 0, y)

        if abs(evt.y - yd) < 5:
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

    def dragstart(self, a, evt):
        self._drag_backup = (evt.xdata, evt.ydata, evt.x, evt.y)
        self._drag_delta = (0, 0)
        return 0

    def dragstart_a(self, a, evt):
        return self.dragstart(a, evt)

    def drag_a(self, a, evt, shift=None, scale=None):
        return self.drag(a, evt), scale

    def drag(self, a, evt):
        if evt.inaxes is None:
            return 0
        if evt.xdata is None:
            return

        axes = a.axes
        x, y = self._eval_xy()
        dxd = evt.x - self._drag_backup[2]
        dyd = evt.y - self._drag_backup[3]

        if (evt.guiEvent.ShiftDown()):
            if abs(dxd) > 2*abs(dyd):
                dyd = 0
            elif abs(dyd) > 2*abs(dxd):
                dxd = 0
        i = 0
        for x0 in nd_iter(x):
            xd, void = transform_point(axes.transData,
                                       x0, evt.ydata)
            x1, void = transform_point(axes.transData.inverted(),
                                       xd+dxd, void)
            self._artists[i].set_xdata([x1, x1])
            i = i+1
        for y0 in nd_iter(y):
            void, yd = transform_point(axes.transData,
                                       evt.xdata, y0)
            void, y1 = transform_point(axes.transData.inverted(),
                                       void, yd+dyd)

            self._artists[i].set_ydata([y1, y1])
            i = i+1
        self._drag_delta = (dxd, dyd)
        return 1

    def drag_a_get_hl(self, a):
        return self.drag_get_hl(a)

    def drag_get_hl(self, a):
        self._alpha_backup = a.get_alpha()
        for a in self._artists:
            a.set_alpha(0.5)
        return self._artists

    def drag_a_rm_hl(self, a):
        self.drag_rm_hl(a)

    def drag_rm_hl(self, a):
        a.set_alpha(self._alpha_backup)
        for a in self._artists:
            a.set_alpha(self._alpha_backup)

    def dragdone_a(self, a, evt, shift=None, scale=None):
        return self.dragdone(a, evt), scale

    def dragdone(self, a, evt):
        axes = a.axes
        x, y = self._eval_xy()
        dxd, dyd = self._drag_delta

        if (evt.xdata is not None and
                evt.ydata is not None):
            i = 0
            xdata = []
            ydata = []
            for x0 in nd_iter(x):
                xd, void = transform_point(axes.transData,
                                           x0, evt.ydata)
                x1, void = transform_point(axes.transData.inverted(),
                                           xd+dxd, void)
                xdata.append(x1)
                i = i+1
            for y0 in nd_iter(y):
                void, yd = transform_point(axes.transData,
                                           evt.xdata, y0)
                void, y1 = transform_point(axes.transData.inverted(),
                                           void, yd+dyd)
                ydata.append(y1)

                i = i+1
        else:
            xdata = x
            ydata = y

        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (np.array(xdata), np.array(ydata)))
        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1

    def set_data(self, value, a):
        self.setp('x', value[0])
        self.setp('y', value[1])
        self._data_extent = None
        i = 0
        for x0 in value[0]:
            self._artists[i].set_xdata([x0, x0])
            i = i+1
        for y0 in value[1]:
            self._artists[i].set_ydata([y0, y0])
            i = i+1

    def get_data(self, a=None):
        return (self.getp('x').copy(), self.getp('y').copy())

    def onExport(self, event):
        from matplotlib.artist import getp

        shell = self.get_root_parent().app.shell
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        for a in self._artists:
            if a in sel:
                print("Exporting Data to Shell")
                fig_val = {"xdata": getp(a, "xdata"),
                           "ydata": getp(a, "ydata")}
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

    def set_alpha(self, value, a):
        set_mpl_all(self._artists, 'alpha', value)

    def get_alpha(self, a):
        return get_mpl_first(self._artists, 'alpha')

    def set_color(self, value, a):
        set_mpl_all(self._artists, 'color', value)

    def get_color(self, a):
        return get_mpl_first(self._artists, 'color')

    def set_linestyle(self, value, a):
        set_mpl_all(self._artists, 'linestyle', value)

    def get_linestyle(self, a):
        return get_mpl_first(self._artists, 'linestyle')

    def set_linewidth(self, value, a):
        set_mpl_all(self._artists, 'linewidth', value)

    def get_linewidth(self, a):
        return get_mpl_first(self._artists, 'linewidth')

    def set_marker(self, value, a):
        set_mpl_all(self._artists, 'marker', value)

    def get_marker(self, a):
        return get_mpl_first(self._artists, 'marker')

    def set_markerfacecolor(self, value, a):
        set_mpl_all(self._artists, 'markerfacecolor', value)

    def get_markerfacecolor(self, a):
        return get_mpl_first(self._artists, 'markerfacecolor')

    def set_markeredgecolor(self, value, a):
        set_mpl_all(self._artists, 'markeredgecolor', value)

    def get_markeredgecolor(self,  a):
        return get_mpl_first(self._artists, 'markeredgecolor')

    def set_markersize(self, value, a):
        set_mpl_all(self._artists, 'markersize', value)

    def get_markersize(self, a):
        return get_mpl_first(self._artists, 'markersize')

    def set_markeredgewidth(self, value, a):
        set_mpl_all(self._artists, 'markeredgewidth', value)

    def get_markeredgewidth(self,  a):
        return get_mpl_first(self._artists, 'markeredgewidth')

#
#   data extent
#
    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x, y = self._eval_xy()
        d = [None]*4
        if len(x) != 0:
            d[0] = min(x)
            d[1] = max(x)
        if len(y) != 0:
            d[2] = min(y)
            d[3] = max(y)
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
            return super(FigAxline, self).get_xrange(xrange, scale=scale)

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if scale == 'log':
            y = mask_negative(y)
        if y.size != 0:
            return self._update_range(yrange, [np.nanmin(y), np.nanmax(y)])
        else:
            return super(FigAxline, self).get_yrange(yrange=yrange,
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

        #dprint1('save_data2', var)
        data['FigAxline'] = (1, var)
        data = super(FigAxline, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigAxline']
        super(FigAxline, self).load_data2(data)
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
