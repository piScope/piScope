from __future__ import print_function
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.widgets.canvas.file_structure import *
from ifigure.mto.axis_user import XUser, YUser
from ifigure.ifigure_config import pick_r
import ifigure
import os
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty, UndoRedoFigobjProperty, UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.utils.args_parser import ArgsParser

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigSpline')


def bs_basis(t):
    at = abs(t)
    if t > -1. and t < 1.:
        return (3*at*at*at-6*at*at+4)/6
    if t > -2. and t < 2.:
        return -(at-2)*(at-2)*(at-2)/6
    return 0.


def calc_xy(xp, yp, mesh=10, mode=1):
    if mode == 0:
        return [p for p in xp], [p for p in yp]
    xp1 = np.concatenate(([xp[0], xp[0]], xp, [xp[-1], xp[-1]]))
    yp1 = np.concatenate(([yp[0], yp[0]], yp, [yp[-1], yp[-1]]))

    ks = range(len(xp)+2)
    ts = np.arange((len(xp)+1)*mesh+1)/float(mesh)-1
    xval = np.zeros(len(ts))
    yval = np.zeros(len(ts))
    i = 0
    for t in ts:
        j = 0
        for j in range(len(xp1)):

            t0 = j-2.
#           print t0, t
            xval[i] = xval[i]+xp1[j]*bs_basis(t-t0)
            yval[i] = yval[i]+yp1[j]*bs_basis(t-t0)
            j = j+1
        i = i+1
    return xval, yval


class FigSpline(FigObj, XUser, YUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._hit_idx = -1
            obj._hit_seg = -1
            obj._hit_artist = -1
            obj._mesh = 10
            obj._data_extent = None
            obj._data_extent_checked = False
            obj._sp_interp = 1
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('y', ['numbers|nonstr', 'dynamic'])

        p.set_ndconvert("x", "y")
        p.set_squeeze_minimum_1D("x", "y")

        p.add_key('draggable', True)

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        if v["x"] is None:
            v["x"] = np.arange(v["y"].shape[-1])
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
        super(FigSpline, self).__init__(*args, **kywds)

    @classmethod
    def isFigSpline(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'spline'

    @classmethod
    def property_in_file(self):
        return ["color", "linestyle",
                "linewidth", "marker"]

    @classmethod
    def property_in_palette(self):
        return (["spline", "line", "marker"],
                [["spinterp"],
                 ["color", "linestyle", "linewidth"],
                 ["markerfacecolor", "markeredgecolor", "marker"]])

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ["x", "y"]

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

        super(FigSpline, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)

    def args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y"]
        use_np = [True, True]
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
#              self.del_artist(delall=True)

        dprint2("generating spline artist")
        x, y = self._eval_xy()  # this handles "use_var"
        if (x is not None and
                y is not None):

            xval, yval = calc_xy(x, y,
                                 mesh=self._mesh,
                                 mode=self._sp_interp)
            try:
                self._artists = container.plot(xval, yval,
                                               **(self._var["kywds"]))
            except:
                self._artists = []
                raise ValueError("failed to generate spline artist")

        lp = self.getp("loaded_property")
        if lp is not None:
            for i in range(0, len(lp)):
                if i < len(self._artists):
                    self.set_artist_property(self._artists[i], lp[i])
            self.delp("loaded_property")

        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))
            self._objs.append(weakref.ref(artist))

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                a.remove()
                # container.lines.remove(a)

        super(FigSpline, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        container = self.get_container()
        if val == True:
            for a in alist:
                x = self.getp("x")
                y = self.getp("y")
#              x=a.get_xdata()
#              y=a.get_ydata()
                hl = container.plot(x, y, marker='s',
                                    color='k', linestyle='None',
                                    markerfacecolor='None',
                                    markeredgewidth=0.5,
                                    scalex=False, scaley=False)
                for item in hl:
                    self._objs.append(weakref.ref(item))
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
        self._hit_seg = -1
        self._hit_idx = -1
        self._hit_artist = -1
        axes = artist.axes
        if axes is None:
            return False, {}
        x = self.getp("x")
        y = self.getp("y")
        trans = axes.transData.transform
        itrans = axes.transData.inverted().transform

        # this checks if picker can use xdata/ydata
        # for hit test
        p = np.array([evt.xdata, evt.ydata]).reshape(1, 2)
        pd = trans(p)
        if abs(pd.flat[0] - evt.x) > 3 or abs(pd.flat[1] - evt.y) > 3:
            return False, {}

        for i in range(len(x)):
            x0d, y0d = trans((x[i], y[i]))
            if abs(x0d-evt.x)+abs(y0d-evt.y) < pick_r:
                self._hit_idx = i
                self._hit_artist = (self._artists.index(artist), evt)
                # print "hit control", self._hit_idx
                return True, {'child_artist': artist}

        xdata = artist.get_xdata()
        ydata = artist.get_ydata()
        ans, idx = cpicker.CheckLineHit(xdata, ydata,
                                        evt.xdata, evt.ydata, trans, itrans)

        if ans:
            check = True
            extra = {}

            self._hit_artist = (self._artists.index(artist), evt)
            self._hit_seg = idx
        else:
            check = False
            extra = {}
        if check:
            return True, {'child_artist': artist}
        return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0
#
#   drag
#

    def dragstart_a(self, a, evt):
        return self.dragstart(a, evt)

    def dragstart(self, a, evt):
        #        print "drag spline", self._hit_idx
        self._drag_start = evt

    def get_dragged_node(self, evt):
        d = (evt.xdata - self._drag_start.xdata,
             evt.ydata - self._drag_start.ydata)

        if self._hit_idx != -1:  # change control
            x = [item for item in self.getp("x")]
            y = [item for item in self.getp("y")]
            x[self._hit_idx] = x[self._hit_idx] + d[0]
            y[self._hit_idx] = y[self._hit_idx] + d[1]
        else:  # transpose
            x = [item + d[0] for item in self.getp("x")]
            y = [item + d[1] for item in self.getp("y")]
        return x, y

    def drag_a(self, a, evt, shift=None, scale=None):
        return self.drag(a, evt), scale

    def drag(self, a, evt):
        if evt.inaxes is None:
            return 0
        x, y = self.get_dragged_node(evt)
        if len(a.figobj_hl) == 1:
            if a.figobj_hl[0] is not None:
                a.figobj_hl[0].set_xdata(x)
                a.figobj_hl[0].set_ydata(y)
        xval, yval = calc_xy(x, y, mesh=self._mesh,
                             mode=self._sp_interp)
        a.set_xdata(xval)
        a.set_ydata(yval)
        return 1

    def drag_a_get_hl(self, a):
        return self.drag_get_hl(a)

    def drag_get_hl(self, a):
        self._alpha_backup = a.get_alpha()
        a.set_alpha(0.5)
        return [a]

    def drag_a_rm_hl(self, a):
        self.drag_rm_hl(a)

    def drag_rm_hl(self, a):
        a.set_alpha(self._alpha_backup)

    def dragdone_a(self, a, evt, shift=None, scale=None):
        return self.dragdone(a, evt), scale

    def dragdone(self, a, evt):
        if evt.inaxes is None:
            return 0

        x, y = self.get_dragged_node(evt)
#        app = evt.guiEvent.GetEventObject().GetTopLevelParent()
#        hist = app.history
        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.start_record()
        action1 = UndoRedoFigobjMethod(a, 'splinenode', (x, y))
        hist.add_history(action1)
        hist.stop_record()
        return 1
#
#  Popup in Canvas
#

    def canvas_menu(self):
        menus = [("Add Node",  self.onAddNode, None),
                 ("Remove Node", self.onRmNode, None),
                 ("Export Node", self.onExportNode, None)] + super(FigSpline, self).canvas_menu()
        return menus

    def onAddNode(self, evt):
        if self._hit_artist == -1:
            return
        if self._hit_seg == -1:
            return

        # _hit_artist = (artist index, mpl event)
        idx = int(self._hit_seg/self._mesh)
        x = [p for p in self.getp("x")]
        y = [p for p in self.getp("y")]
        x.insert(idx, self._hit_artist[1].xdata)
        y.insert(idx, self._hit_artist[1].ydata)

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.start_record()
        a = self._artists[self._hit_artist[0]]
        action1 = UndoRedoFigobjMethod(a,
                                       'splinenode', (x, y))
        hist.add_history(action1)
        hist.stop_record()

    def onRmNode(self, evt):
        if self._hit_artist == -1:
            return
        if self._hit_idx == -1:
            return

        x = self.getp("x")
        y = self.getp("y")
        xn = [x[i] for i in range(len(x)) if i != self._hit_idx]
        yn = [y[i] for i in range(len(y)) if i != self._hit_idx]

#        app = evt.GetEventObject().GetTopLevelParent()
        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.start_record()
        a = self._artists[self._hit_artist[0]]
        action1 = UndoRedoFigobjMethod(a,
                                       'splinenode', (xn, yn))
        hist.add_history(action1)
        hist.stop_record()

    def onExportNode(self, event):
        fig_val = {"xdata": self.getp("x"),
                   "ydata": self.getp("y")}
        text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\']\"'
        self._export_shell(fig_val, 'fig_val', text)

    def onExport(self, event):
        from matplotlib.artist import getp
        fig_val = None
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        for a in self._artists:
            if a in sel:
                print("Exporting Data to Shell")
                fig_val = {"xdata": getp(a, "xdata"),
                           "ydata": getp(a, "ydata")}
                break
        if fig_val is not None:
            text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\']\"'
            self._export_shell(fig_val, 'fig_val', text)

    def set_splinenode(self, value, a):
        self.setp("x", value[0])
        self.setp("y", value[1])
        xval, yval = calc_xy(value[0], value[1],
                             mesh=self._mesh,
                             mode=self._sp_interp)
        a.set_xdata(xval)
        a.set_ydata(yval)
        self._data_extent = None
        self._data_extent_checked = False

    def get_splinenode(self, a):
        x = self.getp("x")
        y = self.getp("y")
        return x, y
#
#   data extent
#

    def get_data_extent(self):
        if (self._data_extent is not None and
                self._data_extent_checked):
            return self._data_extent
        if (self._data_extent is not None and
                self.isempty()):
            return self._data_extent
        x, y = self._eval_xy()
        if self.isempty():
            if x is None:
                self._data_extent = [0, len(y), np.min(y), np.max(y)]
            else:
                self._data_extent = [
                    np.min(x), np.max(x), np.min(y), np.max(y)]
        else:
            xr = (np.inf, -np.inf)
            yr = (np.inf, -np.inf)
            for a in self._artists:
                xdata = a.get_xdata()
                ydata = a.get_ydata()
                xr = (min((xr[0], np.amin(xdata))),
                      max((xr[1], np.amax(xdata))))
                yr = (min((yr[0], np.amin(ydata))),
                      max((yr[1], np.amax(ydata))))

            self._data_extent = [min((min(xr), np.amin(x))),
                                 max((max(xr), np.amax(x))),
                                 min((min(yr), np.amin(y))),
                                 max((max(yr), np.amax(y)))]
            self._data_extent_checked = True
        return self._data_extent
#
#   range
#

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if len(self._artists) != 0:
            xc = self._artists[0].get_xdata()
        else:
            xc, yc = calc_xy(x, y,
                             mesh=self._mesh,
                             mode=self._sp_interp)
        if scale == 'log':
            x = mask_negative(x)
            xc = mask_negative(xc)
        return self._update_range(xrange, [np.nanmin([np.nanmin(x), np.nanmin(xc)]),
                                           np.nanmax([np.nanmax(x), np.nanmax(xc)])])

    def get_yrange(self, yrange=[None, None], xrange=[None, None], scale='linear'):
        x, y = self._eval_xy()
        if len(self._artists) != 0:
            xc = self._artists[0].get_xdata()
            yc = self._artists[0].get_ydata()
        else:
            xc, yc = calc_xy(x, y,
                             mesh=self._mesh,
                             mode=self._sp_interp)
        ym = np.ma.masked_array(y)
        ycm = np.ma.masked_array(yc)
        ym[x < xrange[0]] = np.ma.masked
        ym[x > xrange[1]] = np.ma.masked
        ycm[xc < xrange[0]] = np.ma.masked
        ycm[xc > xrange[1]] = np.ma.masked
        if scale == 'log':
            ym[x < 0] = np.ma.masked
            ycm[xc < 0] = np.ma.masked
        return self._update_range(yrange, [np.nanmin([np.nanmin(ym), np.nanmin(ycm)]),
                                           np.nanmax([np.nanmax(ym), np.nanmax(ycm)])])

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
               'y': check(self, 'y')}

        if var["x"] is not True:
            var["xdata"] = self.getp("x")
        if var["y"] is not True:
            var["ydata"] = self.getp("y")
        var["_sp_interp"] = self._sp_interp

        data['FigSpline'] = (1, var)
        data = super(FigSpline, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigSpline']
        super(FigSpline, self).load_data2(data)
        var = d[1]
        names = ["x", "y"]
        if '_sp_interp' in var:
            self._sp_interp = var['_sp_interp']
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_xy(self):
        names = ("x", "y")
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return [None]*len(names)
        return self.getp(names)

    def set_sp_interp(self, value, a):
        print(value)
        if str(value) == 'linear':
            self._sp_interp = 0
        else:
            self._sp_interp = 1

        xval, yval = calc_xy(self.getp('x'),
                             self.getp('y'),
                             mesh=self._mesh,
                             mode=self._sp_interp)
        a.set_xdata(xval)
        a.set_ydata(yval)
        self._data_extent = None
        self._data_extent_checked = False

    def refresh_artist_data(self):
        super(FigSpline, self).refresh_artist_data()
        self._data_extent_checked = False

    def get_sp_interp(self, a):
        if self._sp_interp == 0:
            return 'linear'
        else:
            return 'spline'

    def setp(self, *args):  # arg = name, var or var
        super(FigSpline, self).setp(*args)
        if len(args) == 2:
            if (args[0] == 'x' or args[0] == 'y'):
                self.setvar(args[0], args[1])

# Public
    def GetSplineData(self, x=None):
        from matplotlib.artist import getp
        return [(getp(a, "xdata"),
                 getp(a, "ydata")) for a in self._artists]
