from __future__ import print_function

#
#  Name   :ifigure_canvas
#
#          this class provide object-oriented
#          compound-widget
#
#    Relationship between ifigure_canvas and matplot
#          item on canvas is matplotlib artists and
#          containers. this canvas treats "figobj" as
#          a contents drawn on this canvas.
#
#          figobj.generate_artist() will draw item on
#          this canvas by calling matplotlib functions.
#          Additionally, artists and containers added
#          in such a way are given an extra instance
#          member called "figobj".
#
#          when ifigure_canvas.add_figobj() add objects
#          to matplotlib
#
#  History:
#         2012 06 11 selection and axes_selection
#                    becace weakref
#         2012 07-09 many changes and addition
#                    undo/redo
#                    draw with "wait for idle"
#                    its own zoom/pan
#         2013 03    Most of functions for ver.1 was
#                    added...
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

import ifigure.utils.debug as debug
import ifigure.widgets.canvas.dnd_areasplitter as sp
from ifigure.widgets.navibar2 import navibar
import wx
import time
try:
    from wx._core import PyDeadObjectError
except BaseException:
    # wx4
    PyDeadObjectError = RuntimeError
import matplotlib
import numpy as np
#from numpy import arange, sin, pi
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, PathPatch
import matplotlib.path
import weakref
import ifigure.utils.pickle_wrapper as pickle
from ifigure.ifigure_config import *
from ifigure.utils import geom as geom_util
from ifigure.utils.geom import transform_point
import ifigure.utils.cbook as cbook
import ifigure.utils.geom as geom
from matplotlib.artist import setp as mpl_setp
from ifigure.mto.fig_axes import FigAxes
from ifigure.mto.fig_page import FigPage
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_book import FigBook
from ifigure.mto.fig_image import FigImage
from ifigure.mto.fig_contour import FigContour
from ifigure.mto.fig_text import FigText
from ifigure.mto.fig_legend import FigLegend
from ifigure.mto.axis_user import CUser


import ifigure.widgets.canvas.custom_picker as cpicker
from ifigure.widgets.canvas.layout_editor import layout_editor
import ifigure.events

from ifigure.widgets.axes_range_subs import RangeRequestMaker

from ifigure.widgets.undo_redo_history import (GlobalHistory,
                                               UndoRedoArtistProperty,
                                               UndoRedoFigobjProperty,
                                               UndoRedoFigobjMethod,
                                               UndoRedoGroupUngroupFigobj,
                                               UndoRedoAddRemoveArtists)

# uncomment the following to use wx rather than wxagg
# matplotlib.use('WX')
#from ifigure.matplotlib_mod.backend_wx_mod import FigureCanvasWxMod as Canvas
# matplotlib.use('WXAGG') ## this is moved to piscope.py
from ifigure.matplotlib_mod.backend_wxagg_mod import FigureCanvasWxAggMod as Canvas
turn_on_gl = False

# comment out the following to use wx rather than wxagg
# standard Toolbar is not used anymore
# matplotlib.use('WXAgg')
#from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
#from matplotlib.backends.backend_wx import NavigationToolbar2Wx as Toolbar

dprint1, dprint2, dprint3 = debug.init_dprints('iFigureCanvas')

bitmap_names = ['xauto.png', 'yauto.png', 'samex.png', 'samey.png']
bitmaps = {}

# popup menu stype (bit)
popup_style_default = 0
popup_skip_2d = 1

# double click interval in two unit ;D
dcinterval_ms = 200
dcinterval = 0.2
# single click threshold (less than this time, drag is ignored)
scinterval_th = 0.1


class guiEventCopy(object):
    def __init__(self, guiEvent):
        object.__init__(self)
        methods = ['ShiftDown',
                   'LeftUp',
                   'GetEventObject',
                   'AltDown',
                   'ControlDown',
                   'GetX',
                   'GetY']
        for name in methods:
            if not hasattr(guiEvent, name):
                continue
            m = getattr(guiEvent, name)
            setattr(self, '_' + name, m())

    def ShiftDown(self):
        return self._ShiftDown

    def LeftUp(self):
        return self._LeftUp

    def GetEventObject(self):
        return self._GetEventObject

    def ControlDown(self):
        return self._ControlDown

    def AltDown(self):
        return self._AltDown

    def GetX(self):
        return self._GetX

    def GetY(self):
        return self._GetY


class ifigure_DropTarget(wx.TextDropTarget):
    def __init__(self, canvas):
        self._canvas = weakref.ref(canvas)
        self._modebk = 'normal'
        super(ifigure_DropTarget, self).__init__()

    def OnDropText(self, x, y, data):
        dprint1("text data is entering....")
        self._canvas().mpl_connect(mode=self._modebk)

    def OnDragOver(self, x, y, default):
        if self._canvas() is None:
            return

        class event(object):
            pass
        evt = event()
        w, h = self._canvas().canvas.get_width_height()
        self._canvas().canvas.motion_notify_event(x, h - y, evt)
        #sp.dnd_sp(x, y, self._canvas())
        return default

    def OnLeave(self, *args):
        dprint1('onLeave')
        self._canvas().mpl_connect(mode=self._modebk)

    def OnEnter(self, *args):
        dprint1('onEnter')
        self._modebk = self._canvas()._mpl_mode
        self._canvas().mpl_connect(mode='dnd')


class draghandler_base(object):
    def __init__(self, panel):
        #        super(ifigure_canvas_draghandler_zoom, self).__init__()
        self.mpl_id = None
        self.a = None
        self.rb = None
        self.dragging = False
        self.d_mode = ''
        self.panel = weakref.proxy(panel, self.clean)
        self._disable_square = False
        self.st_event = None

    def set_artist(self, a):
        self.a = a

    def get_artist(self):
        if self.a is None:
            return []
        if isinstance(self.a, list):
            return self.a
        return [self.a]

    def unbind_mpl(self):
        if self.mpl_id is not None:
            self.panel.canvas.mpl_disconnect(self.mpl_id)
        self.mpl_id = None

    def isDragging(self):
        return self.mpl_id is not None

    def clean(self, canvas):
        self.a = None
        self.unbind_mpl()
        self.st_event = None


class draghandler_base2(draghandler_base):
    def bind_mpl(self, event):
        if self.mpl_id is not None:
            self.unbind_mpl()
        self.st_event = event
        self.mpl_id = self.panel.canvas.mpl_connect(
            'motion_notify_event',
            self.panel.mousedrag_panzoom)

        self.dragging = False
        self.a = self.panel.axes_selection()


class draghandler_none(object):
    def dragstart(self, evt):
        pass

    def dodrag(self, evt):
        pass

    def dragdone(self, evt):
        pass


class draghandler_rb_d(object):
    '''
    set of methods to add rubber band drawing in device coords.
    '''

    def dragstart(self, evt):
        if self.rb is not None:
            self.rb.figure.lines.remove(self.rb)
        if evt is None:
            return

        self._figure_image = self.panel.canvas.copy_figure_image()
        self._figure_image[0] = self.panel.canvas.capture_screen_rgba()

        x, y = self._calc_xy(evt)
        self._show_box(x, y)
        self.dragging = True

        # self.panel.mpl_connect(mode='normal')

    def dodrag(self, evt):
        if evt is None:
            return
        if self.st_event is None:
            self.unbind_mpl()
            return
        x, y = self._calc_xy(evt)
        self._show_box(x, y)
#        self.panel.draw()

    def dragdone(self, evt):
        self.unbind_mpl()

        if self.rb is not None:
            self.panel._figure.lines.remove(self.rb)
            self.rb = None

    def _show_box(self, x, y):
        self.rb = Line2D(x, y, figure=self.panel._figure,
                         linestyle='-', color='red', alpha=0.5,
                         markerfacecolor='None')
        self.panel._figure.lines.extend([self.rb])

        figure_image = self.panel.canvas.swap_figure_image(self._figure_image)
        self.panel.refresh_hl_fast([self.rb])
        self.panel._figure.lines.remove(self.rb)
        self.panel.canvas.swap_figure_image(figure_image)

        self.rb = None

    def _calc_xy(self, evt):
        dx = evt.x - self.st_event.x
        dy = evt.y - self.st_event.y
        if not self._disable_square and evt.guiEvent.ShiftDown():
            if abs(dx) < abs(dy):
                dy = abs(dx) * dy / abs(dy)
            else:
                dx = abs(dy) * dx / abs(dx)
        x0 = self.st_event.x
        x1 = self.st_event.x + dx
        y0 = self.st_event.y
        y1 = self.st_event.y + dy

        x = [x0, x1, x1, x0, x0]
        y = [y0, y0, y1, y1, y0]
        self._x = x
        self._y = y
        return x, y

    '''
    def dragdone_killfocus(self):
        self.unbind_mpl()
        print(self.rb)
        if self.rb is not None:
            self.panel._figure.lines.remove(self.rb)
            self.rb = None
    '''


class draghandler_line_d(object):
    '''
    set of methods to add line drawing in device coords.
    '''

    def dragstart(self, evt):
        if self.rb is not None:
            self.rb.figure.lines.remove(self.rb)
        x = [self.st_event.x, evt.x]
        y = [self.st_event.y, evt.y]
        self._show_line(x, y)
        self.dragging = True

    def dodrag(self, evt):
        x = [self.st_event.x, evt.x]
        y = [self.st_event.y, evt.y]
        self._show_line(x, y)

    def dragdone(self, evt):
        self.unbind_mpl()
        if self.rb is not None:
            self.panel._figure.lines.remove(self.rb)
            self.rb = None

    def _show_line(self, x, y):
        self.rb = Line2D(x, y, figure=self.panel._figure,
                         linestyle='-', color='red', alpha=0.5,
                         markerfacecolor='None')
        self.panel._figure.lines.extend([self.rb])
        self.panel.refresh_hl([self.rb])
        self.panel._figure.lines.remove(self.rb)
        self.rb = None


class draghandler_ellip_d(object):
    '''
    set of methods to add line drawing in device coords.
    '''

    def dragstart(self, evt):
        self._rm_patch()
        self._add_patch(evt)
        self.dragging = True

    def dodrag(self, evt):
        self._rm_patch()
        self._add_patch(evt)
#        self.panel.draw()

    def dragdone(self, evt):
        self._rm_patch()
        self.unbind_mpl()

    def _rm_patch(self):
        if self.rb is not None:
            self.panel._figure.patches.remove(self.rb)
        self.rb = None

    def _add_patch(self, evt):
        xy = [self.st_event.x, self.st_event.y]
        w = abs(self.st_event.x - evt.x) * 2
        h = abs(self.st_event.y - evt.y) * 2
        if evt.guiEvent.ShiftDown():
            w = min((w, h))
            h = min((w, h))
        w = max((w, 2))
        h = max((h, 2))

        self.rb = Ellipse(xy, w, h, figure=self.panel._figure,
                          edgecolor='red', facecolor='none', alpha=0.5)
        self.panel._figure.patches.extend([self.rb])
        self._xy = xy
        self._w = w
        self._h = h
        self.panel.refresh_hl([self.rb])
        self._rm_patch()


class draghandler_curve_d(object):
    '''
    set of methods to add line drawing in device coords.
    '''

    def dragstart(self, evt):
        Path = matplotlib.path.Path
        self.pathdata = [(Path.MOVETO, (evt.x, evt.y))]
        self._rm_patch()
        self.dragging = True

    def dodrag(self, evt):
        Path = matplotlib.path.Path
        if ((evt.x - self.pathdata[-1][1][0])**2 +
                (evt.y - self.pathdata[-1][1][1])**2) > 255:
            #            self._rm_patch()
            self.pathdata.append((Path.LINETO, (evt.x, evt.y)))
            self._add_patch()
#        self.panel.draw()

    def dragdone(self, evt):
        self._rm_patch()
        x = [item[1][0] for item in self.pathdata]
        y = [item[1][1] for item in self.pathdata]
        self.pathdata = cbook.BezierFit(x, y)
#        self._add_patch()
        self.unbind_mpl()

    def _rm_patch(self):
        if self.rb is not None:
            self.panel._figure.patches.remove(self.rb)
        self.rb = None

    def _add_patch(self):
        codes, verts = zip(*self.pathdata)
        path = matplotlib.path.Path(verts, codes)
        self.rb = PathPatch(path, facecolor='none',
                            figure=self.panel._figure,
                            edgecolor='red', alpha=0.5)
        self.panel._figure.patches.extend([self.rb])
        self.panel.refresh_hl([self.rb])
        self.panel._figure.patches.remove(self.rb)
        self.rb = None


class ifigure_canvas_draghandler_cursor(draghandler_base):
    def __init__(self, *args, **kargs):
        super(ifigure_canvas_draghandler_cursor, self).__init__(*args,
                                                                **kargs)
        # mode : 0: standard cursor
        # 1: tracking
        self.cursor_mode = 0
        self.cursors = None
        self.cursor_owner = []

    def bind_mpl(self, event):
        if self.mpl_id is not None:
            self.unbind_mpl()
        if self.panel.toolbar.mode != 'cursor':
            return
        self.st_event = event
        self.mpl_id = self.panel.canvas.mpl_connect(
            'motion_notify_event',
            self.panel.mousedrag_cursor)

    def dragstart(self, evt):
        self.dragging = True
        self.cursor_owner = self.panel.generate_cursors(evt)

    def dodrag(self, evt):
        if evt.guiEvent.LeftIsDown():
            idx = 0
        else:
            idx = 1

        mode = self.panel._cursor_mode
        if self.panel._cursor_target is not None:
            target = self.panel._cursor_target()
            if target.figobj is None:
                target = None
        else:
            target = None
            if (mode == 1 or mode == 2):
                # need to find default target
                if self.panel.axes_selection() is not None:
                    for l in self.panel.axes_selection().lines:
                        if hasattr(l, 'figobj'):
                            target = l

        if (mode == 0 or
                (mode == 1 or mode == 2) and not isinstance(target, Line2D)):
            for figobj in self.cursor_owner:
                figobj().update_cursor(evt, idx)
        elif (mode == 1 or mode == 2):
            if target is None:
                return
            owners = [a() for a in self.cursor_owner]
            real_owner = target.figobj.get_figaxes()
            if real_owner not in owners:
                return
            ret = real_owner.update_cursor(evt, idx, mode=mode, target=target)
            if ret is None:
                return
            evt.xdata = ret[0]
            evt.ydata = ret[1]
            for figobj in owners:
                if figobj is not target.figobj.get_figaxes():
                    figobj.update_cursor(evt, idx)
        elif (mode == 3 or
              mode == 4):
            if target is None:
                return
            if target.figobj is None:
                return
            if isinstance(target.figobj, FigImage):
                mode = 3
            if isinstance(target.figobj, FigContour):
                mode = 4
            owners = [a() for a in self.cursor_owner]
            real_owner = target.figobj.get_figaxes()
            if real_owner not in owners:
                return
            if (isinstance(target.figobj, FigImage) or
                    isinstance(target.figobj, FigContour)):
                real_owner.update_cursor(evt, idx, mode=mode, target=target)
        elif mode == 5:
            if target is None:
                return
            if target.figobj is None:
                return
            owners = [a() for a in self.cursor_owner]
            real_owner = target.figobj.get_figaxes()
            if real_owner not in owners:
                return
            if (isinstance(target.figobj, FigImage) or
                    isinstance(target.figobj, FigContour)):
                real_owner.update_cursor(evt, idx, mode=mode, target=target)

        self.panel.draw_cursor()
        if mode == 3:
            if len(real_owner._cursor1) > 0:
                real_owner._cursor1[0].remove()
        elif mode == 4:
            for a in real_owner._cursor1:
                a.remove()
        else:
            pass

    def dragdone(self, evt):
        self.dragging = False
        self.st_event = None


class ifigure_canvas_draghandler(draghandler_base):
    def bind_mpl(self, event):
        if self.mpl_id is not None:
            self.unbind_mpl()
        if self.panel.toolbar.mode != '':
            return
        self.st_event = event
        self.mpl_id = self.panel.canvas.mpl_connect(
            'motion_notify_event',
            self.panel.mousedrag)

    def dragstart(self, evt):
        self.dragging = False
        if self.a is None:
            return
        redraw = False
        for a in self.a:
            if not a.figobj.isDraggable():
                continue
            if self.d_mode == '':
                val = a.figobj.dragstart(a, evt)
                redraw = redraw or val
            elif self.d_mode == 'a':
                val = a.figobj.dragstart_a(a, evt)
                redraw = redraw or val
            self.dragging = True
        if redraw:
            self.panel.draw()

    def dodrag(self, evt):
        if not self.dragging:
            return
        if self.a is None:
            return
        redraw = False
        scale = None
        alist = []
        for a in self.a:
            if not a.figobj.isDraggable():
                continue
            if self.d_mode == '':
                val = a.figobj.drag(a, evt)
                alist = alist + a.figobj.drag_get_hl(a)
                redraw = 0
            elif self.d_mode == 'a':
                val, scale = a.figobj.drag_a(a, evt, scale=scale)
                alist = alist + a.figobj.drag_a_get_hl(a)
                redraw = 0
        self.panel.refresh_hl(alist)

        for a in self.a:
            if self.d_mode == '':
                a.figobj.drag_rm_hl(a)
            if self.d_mode == 'a':
                a.figobj.drag_a_rm_hl(a)
        if redraw:
            self.panel.draw()

    def dragdone(self, evt):
        self.unbind_mpl()
        if not self.dragging:
            return
        self.dragging = False
        self.st_event = None
        redraw = False
        scale = None

        if self.a is None:
            return
        for a in self.a:
            if not a.figobj.isDraggable():
                continue
            if self.d_mode == '':
                val = a.figobj.dragdone(a, evt)
            elif self.d_mode == 'a':
                val, scale = a.figobj.dragdone_a(a, evt, scale=scale)


class ifigure_canvas_draghandler_pan(draghandler_base2):
    def __init__(self, *args, **kargs):
        draghandler_base2.__init__(self, *args, **kargs)
        self.pan_mode = 0

    def bind_mpl(self, event):
        if (self.panel.toolbar.mode != '' and
                self.panel.toolbar.mode != 'pan'):
            return
        super(ifigure_canvas_draghandler_pan, self).bind_mpl(event)

    def dragstart(self, evt):
        canvas = self.panel.canvas
        if self.a is not None:
            figaxes = self.a.figobj
            if self.panel.toolbar.pan_all == 0:
                for a in figaxes._artists:
                    a.start_pan(evt.x, evt.y, 1)
                self.pan_mode = 0
            else:
                x0, y0 = figaxes.getp('area')[:2]
                w, h = canvas.get_width_height()
                for figaxes2 in figaxes.get_parent().walk_axes():
                    for a in figaxes2._artists:
                        x1, y1 = figaxes2.getp('area')[:2]
                        a.start_pan(evt.x + (x1 - x0) * w,
                                    evt.y + (y1 - y0) * h, 1)
                self.pan_mode = 1
        self.dragging = True

    def dodrag(self, evt):
        canvas = self.panel.canvas
        if self.a is not None:
            figaxes = self.a.figobj
            if self.pan_mode == 0:
                for a in figaxes._artists:
                    a.drag_pan(1, None, evt.x, evt.y)
                figaxes.set_bmp_update(False)
            else:
                x0, y0 = figaxes.getp('area')[:2]
                w, h = canvas.get_width_height()
                for figaxes2 in figaxes.get_parent().walk_axes():
                    for a in figaxes2._artists:
                        x1, y1 = figaxes2.getp('area')[:2]
                        a.drag_pan(1, None, evt.x + (x1 - x0)
                                   * w, evt.y + (y1 - y0) * h)
                    figaxes2.set_bmp_update(False)
            self.panel.draw()

    def dragdone(self, evt):
        canvas = self.panel
        ax = canvas.axes_selection()
        if self.a is not None:
            figaxes = self.a.figobj
            if self.pan_mode == 0:
                for a in figaxes._artists:
                    a.end_pan()
                requests = canvas.make_range_request_pan(figaxes, auto=False)
            else:
                #               x0, y0 = figaxes.getp('area')[0, 1]
                #               w,h=self._canvas().canvas.get_width_height()
                requests = {}
                for figaxes2 in figaxes.get_parent().walk_axes():
                    for a in figaxes2._artists:
                        a.end_pan()
                    requests = canvas.make_range_request_pan(
                        figaxes2, auto=False, requests=requests)
#           actions = self.a.figobj.get_axranges_update_action(auto=False)

            requests = canvas.expand_requests(requests)
            canvas.send_range_action(requests, 'pan')

        self.dragging = False
        self.unbind_mpl()
        self.st_event = None


class ifigure_canvas_draghandler_3d(draghandler_base2):
    '''
    handler for 3D axes
    axes 3D needs to be button_pressed before hand
    calls on_move and button_release of axes3D
    '''

    def __init__(self, *args, **kargs):
        draghandler_base2.__init__(self, *args, **kargs)

    def dragstart(self, evt):
        canvas = self.panel
        ax = canvas.axes_selection()
        ax._button_press(evt)
        self.dragging = True
        self._org = ax.figobj.get_axes3d_viewparam(ax)
        self._st_evt = evt
        canvas.mpl_connect(mode='3dpanrotzoom')

    def dodrag(self, evt):
        canvas = self.panel
        ax = canvas.axes_selection()
        if (abs(self._st_evt.x - evt.x) + abs(self._st_evt.y - evt.y)) < 5:
            return
        self._st_evt = evt
        ax._on_move(evt)

    def dragdone(self, evt):
        self.dragging = False
        self.unbind_mpl()
        self.panel.mpl_connect(mode='normal')
        self.st_event = None
        canvas = self.panel
        ax = canvas.axes_selection()
        ax._button_release(evt)
        ax._on_move_done()
        figaxes = ax.figobj
        if (canvas.toolbar.mode == 'pan' or
            canvas.toolbar.mode == 'zoom' or
                canvas.toolbar.mode == '3dzoom'):
            req = None
            func = canvas.make_range_request_zoom
            minx, maxx, miny, maxy, minz, maxz = ax.get_w_lims()

            req = func(figaxes, 'x', [minx, maxx], False, ax, requests=req)
            req = func(figaxes, 'y', [miny, maxy], False, ax, requests=req)
            req = func(figaxes, 'z', [minz, maxz], False, ax, requests=req)

            if canvas.toolbar.mode == '3dzoom':
                new_value = ax.elev, ax.azim, ax._upvec
                extra_actions = [UndoRedoFigobjMethod(ax, 'axes3d_viewparam', new_value,
                                                      old_value=self._org)]
            else:
                extra_actions = None
            canvas.send_range_action(req,
                                     '3D ' + canvas.toolbar.mode,
                                     extra_actions=extra_actions)
        else:
            new_value = ax.elev, ax.azim, ax._upvec
            actions = [UndoRedoFigobjMethod(ax, 'axes3d_viewparam', new_value,
                                            old_value=self._org)]
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(actions,
                                                           menu_name='3D view')


class ifigure_canvas_draghandler_3d_sel(draghandler_base2,
                                        draghandler_rb_d):
    def dragdone(self, evt):
        draghandler_rb_d.dragdone(self, evt)
        x1 = min(self._x)
        x2 = max(self._x)
        y1 = min(self._y)
        y2 = max(self._y)
        rect = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]

        self._rect = rect
        self._shiftdown = evt.guiEvent.ShiftDown()
        self._controldown = evt.guiEvent.ControlDown()
        self._altdown = evt.guiEvent.AltDown()

    def _calc_xy(self, evt):
        dx = evt.x - self.st_event.x
        dy = evt.y - self.st_event.y
        x0 = self.st_event.x
        x1 = self.st_event.x + dx
        y0 = self.st_event.y
        y1 = self.st_event.y + dy

        x = [x0, x1, x1, x0, x0]
        y = [y0, y0, y1, y1, y0]
        self._x = x
        self._y = y
        return x, y


class ifigure_canvas_draghandler_none(draghandler_base2,
                                      draghandler_none):
    pass


class ifigure_canvas_draghandler_line(draghandler_base2,
                                      draghandler_line_d):
    pass


class ifigure_canvas_draghandler_ellip(draghandler_base2,
                                       draghandler_ellip_d):
    pass


class ifigure_canvas_draghandler_rb(draghandler_base2,
                                    draghandler_rb_d):
    pass


class ifigure_canvas_draghandler_curve(draghandler_base2,
                                       draghandler_curve_d):
    def __init__(self, *args, **kargs):
        super(ifigure_canvas_draghandler_curve,
              self).__init__(*args, **kargs)
        self.pathdata = []
    pass
# class ifigure_canvas_draghandler_line(draghandler_base2, draghandler_line_d):
#    pass


class ifigure_canvas_draghandler_selecta(draghandler_base2, draghandler_rb_d):
    def bind_mpl(self, evt):
        if (self.panel.toolbar.mode != '' and
                self.panel.toolbar.mode != 'pan'):
            return
        super(ifigure_canvas_draghandler_selecta, self).bind_mpl(evt)

    def dragstart(self, evt):
        super(ifigure_canvas_draghandler_selecta, self).dragstart(evt)

    def dodrag(self, evt):
        super(ifigure_canvas_draghandler_selecta, self).dodrag(evt)
        if self.st_event is None:
            return
        x = [self.st_event.x, evt.x]
        y = [self.st_event.y, evt.y]
        box1 = [min(x), max(x), min(y), max(y)]
        self.panel.unselect_all()
        fig_page = self.panel._figure.figobj
        for name, child in fig_page.get_children():
            if not isinstance(child, FigAxes):
                for a in child._artists:
                    box2 = child.get_artist_extent2(a)
                    if geom.check_boxoverwrap(box1, box2):
                        self.panel.add_selection(a)

    def dragdone(self, evt):
        super(ifigure_canvas_draghandler_selecta, self).dragdone(evt)
        self.panel.draw()
        self.st_event = None


class ifigure_canvas_draghandler_zoom(draghandler_base2,
                                      draghandler_rb_d):
    def __init__(self, *args, **kargs):
        super(ifigure_canvas_draghandler_zoom, self).__init__(*args, **kargs)
        self._disable_square = True

    def bind_mpl(self, evt):
        if (self.panel.toolbar.mode != '' and
                self.panel.toolbar.mode != 'zoom'):
            return
        super(ifigure_canvas_draghandler_zoom, self).bind_mpl(evt)

    def dragstart(self, evt):
        if evt.xdata is None:
            return
        super(ifigure_canvas_draghandler_zoom, self).dragstart(evt)

    def dodrag(self, evt):
        super(ifigure_canvas_draghandler_zoom, self).dodrag(evt)

    def dragdone(self, evt):
        st_event = self.st_event
        super(ifigure_canvas_draghandler_zoom, self).dragdone(evt)

        if not hasattr(self, 'expand_dir'):
            self.expand_dir = 'both'
        if self.a is None:
            return

        ax = self.panel.axes_selection()
        figaxes = ax.figobj

        d1 = abs(evt.x - st_event.x)
        d2 = abs(evt.y - st_event.y)

        if not ((d1 > 5) and (d2 > 5)):
            return

        canvas = self.panel
        range_data = {}
        extra_actions = None

        for a in figaxes._artists:
            range_data[a] = {}
            xdata, ydata = transform_point(
                a.transData.inverted(),
                evt.x, evt.y)
            sxdata, sydata = transform_point(
                a.transData.inverted(),
                st_event.x, st_event.y)

            if figaxes.get_3d():
                updown = canvas.toolbar.zoom_up_down
                val = a.calc_range_change_zoom3d(
                    xdata, ydata, sxdata, sydata, updown)
                range_data[a]['x'] = val[0]
                range_data[a]['y'] = val[1]
                range_data[a]['z'] = val[2]
                # set scale accumulator for pan_sensitivity
                extra_actions = [
                    UndoRedoArtistProperty(
                        a,
                        'gl_scale_accum',
                        a._gl_scale_accum *
                        val[3]),
                ]

            else:
                # work to expand/shrink range
                if evt.x > st_event.x:
                    xrange = [sxdata, xdata]
                else:
                    xrange = [xdata, sxdata]

                if evt.y > st_event.y:
                    yrange = [sydata, ydata]
                else:
                    yrange = [ydata, sydata]
                if canvas.toolbar.zoom_menu:
                    m = zoom_popup(self)
                    self.panel.canvas.PopupMenu(
                        m, [evt.guiEvent.GetX(), evt.guiEvent.GetY()])
                    m.Destroy()

                if canvas.toolbar.zoom_up_down == 'down':
                    #  if self.st_event.key == 'd':
                    atrans = a.transAxes.transform
                    iatrans = a.transAxes.inverted().transform
                    dtrans = a.transData.transform
                    idtrans = a.transData.inverted().transform
                    dtrans = a.transData.transform
                    p0, p1 = dtrans(np.array([[xrange[0], yrange[0]],
                                              [xrange[1], yrange[1]]]))
                    # print p0, p1
                    a0, a1 = iatrans(np.array([p0, p1]))
                    # print a0, a1
                    ia0 = [-a0[0], -a0[1]]
                    ia1 = [1 + (1 - a1[0]), 1 + (1. - a1[1])]
                    # print ia0, ia1
                    ip0, ip1 = atrans(np.array([ia0, ia1]))
                    # print ip0, ip1
                    d0, d1 = idtrans(np.array([ip0, ip1]))
                    xrange = [d0[0], d1[0]]
                    yrange = [d0[1], d1[1]]

                if self.expand_dir in ['x', 'both']:
                    # this is to change values in artists
                    # as it happens in pan mode
                    range_data[a]['x'] = xrange
                if self.expand_dir in ['y', 'both']:
                    range_data[a]['y'] = yrange
                    # this is to change values in artists
                    # as it happens in pan mode
    #               a.set_ylim(yrange)
    #               requests =  canvas.make_range_request_zoom(figaxes, 'y', yrange, False, a, requests=requests)

        requests = None
        for a in range_data:
            for key in range_data[a]:
                range = range_data[a][key]
                if key == 'x':
                    a.set_xlim(range)
                elif key == 'y':
                    a.set_ylim(range)
                requests = canvas.make_range_request_zoom(
                    figaxes, key, range, False, a, requests=requests)
        requests = canvas.expand_requests(requests)
        canvas.send_range_action(requests, 'zoom', extra_actions=extra_actions)

        self.expand_dir = 'both'
#        self.panel.draw()
#           self.a.xrange
#           print yrange
        self.dragging = False
        self.unbind_mpl()
        self.st_event = None


class zoom_popup(wx.Menu):
    def __init__(self, parent):
        super(zoom_popup, self).__init__()
        self.parent = parent

        menus = [('X', self.set_expand_x, None),
                 ('Y', self.set_expand_y, None),
                 ('Both', self.set_expand_xy, None)]
        cbook.BuildPopUpMenu(self, menus)

    def set_expand_x(self, e):
        self.parent.expand_dir = 'x'

    def set_expand_y(self, e):
        self.parent.expand_dir = 'y'

    def set_expand_xy(self, e):
        self.parent.expand_dir = 'both'


class ifigure_popup(wx.Menu):
    def __init__(self, parent, xy=None, xydata=None):
        super(ifigure_popup, self).__init__()
#        self.parent=parent

        menus = []
        arrange_menu = True if len(parent.selection) != 0 else False
        self._cur_paths = []
        if parent.toolbar.mode == 'cursor':
            func = [None] * 6
            for i in range(len(func)):
                def f(evt, choice=i, obj=self):
                    obj.onCursorMenu(evt, choice)
                func[i] = f
            check = ['*'] * len(func)
            check[parent._cursor_mode] = '^'
            if len(menus) != 0:
                menus = menus + [('---', None, None)]
            menus = menus + \
                [(check[0] + 'Standard Cursor', func[0], None),
                 (check[1] + 'Tracking X Cursor', func[1], None),
                    (check[2] + 'Taccking Y Cursor', func[2], None),
                    ('+2D Cursor', None, None),
                    (check[3] + 'Contour/Image cursor', func[3], None),
                    #                        (check[4]+'Contour cursor',         func[4], None),
                    (check[5] + 'Slice viewer', func[5], None),
                    ('!', None, None), ]
            try:
                if parent.axes_selection().figobj.get_3d():
                    menus.append(
                        ('3D slice', self.on3Dslice, None))
                else:  # in 2D mode check if contour path plot should be added
                    if check[3] == '^':
                        target = parent._cursor_target()
                        if (target is not None and
                            target.figobj is not None and
                            isinstance(target.figobj, FigContour) and
                            parent.axes_selection() is not None and
                                len(parent.axes_selection().figobj._cursor1) > 0):
                            for cur in parent.axes_selection().figobj._cursor1:
                                self._cur_paths.extend(cur.get_paths())
                            menus.append(
                                ('Add CursorPath Plot', self.onGeneratePath, None))
            except BaseException:
                pass
            menus.append(
                ('Cursor setting...', self.onCursorSetting, None))
            arrange_menu = False
        if parent.toolbar.ptype != 'amode':
            if len(menus) != 0:
                menus = menus + [('---', None, None)]
            if parent._popup_style & popup_skip_2d == 0:
                if parent.axes_selection() is None:
                    menus = menus + \
                        [('Autoscale all', self.onXYauto_all, None),
                         ('Autoscale all X', self.onXauto_all, None),
                            ('Autoscale all Y', self.onYauto_all, None), ]
                else:
                    menus = menus + \
                        [('Autoscale', self.onXYauto, None),
                         ('Autoscale X', self.onXauto,
                          None, bitmaps['xauto'],),
                            ('Autoscale Y', self.onYAuto,
                             None, bitmaps['yauto'],),
                            ('Autoscale all', self.onXYauto_all, None),
                            ('Autoscale all X', self.onXauto_all, None),
                            ('Autoscale all Y', self.onYauto_all, None), ]
                    a = parent.axes_selection()
                    fig_axes = a.figobj
                    if len(fig_axes._caxis) > 0:
                        menus = menus + \
                            [('Autoscale C', self.onCAuto, None), ]

                    if a.figobj.get_3d():
                        sameall = self.onSameXYZ
                    else:
                        sameall = self.onSameXY

                    menus = menus + \
                        [('All same scale', sameall, None),
                         ('All same X scale', self.onSameX,
                          None, bitmaps['samex']),
                            ('All same X (Y auto)', self.onSameX_autoY, None),
                            ('All same Y scale', self.onSameY, None, bitmaps['samey']), ]
                    if len(fig_axes._caxis) > 0:
                        menus = menus + \
                            [('All same C scale', self.onSameC, None), ]
                    if a.figobj.get_3d():
                        menus = menus + \
                            [('All same 3D view', self.onSameView, None), ]

                menus.extend(
                    parent.GetTopLevelParent().extra_canvas_range_menu())
            try:
                if parent.axes_selection().figobj.get_3d():
                    menus.extend([
                        ('+3D view', None, None),
                        ('XY plane', self.on3DXY, None),
                        ('XZ plane', self.on3DXZ, None),
                        ('YZ plane', self.on3DYZ, None),
                        ('Rotate 90', self.on3D_Rot90r, None),
                        ('Rotate -90', self.on3D_Rot90, None),
                        ('Flip', self.on3DUpDown, None),
                        ('Default view', self.on3DDefaultView, None),
                        ('---', None, None), ])
                    if parent.axes_selection()._use_frustum:
                        menus.append(('Use ortho', self.on3DOrtho, None))
                    else:
                        menus.append(('Use frustum', self.on3DFrustum, None))

                    if parent.axes_selection()._use_clip & 1:
                        menus.append(('Clip off', self.on3DClipOff, None))
                    else:
                        menus.append(('Clip on', self.on3DClipOn, None))

                    if parent.axes_selection()._use_clip & 2:
                        menus.append(
                            ('CutPlane off', self.on3DCutPlaneOff, None))
                    else:
                        menus.append(
                            ('CutPlane on', self.on3DCutPlaneOn, None))

                    if parent.axes_selection()._show_3d_axes:
                        menus.append(
                            ('Hide axes icon', self.on3DAxesIconOff, None))
                    else:
                        menus.append(
                            ('Show axes icon', self.on3DAxesIconOn, None))

                    if (parent.axes_selection().figobj.getp('aspect') ==
                            'equal'):
                        menus.append(('Auto aspect', self.on3DAutoAspect,
                                      None))
                    else:
                        menus.append(('Equal aspect', self.on3DEqualAspect,
                                      None))
                    if len(parent.selection) == 1:
                        method = parent.selection[0]().figobj.onSetRotCenter
                        menus.append(('Set rotation center', method, None))
                    else:
                        menus.append(('Reset rotation center',
                                      self.onResetRotCenter, None))
                    menus.extend([
                        ('!', None, None), ])
            except BaseException:
                pass

        fig_axes = None

        menus2 = []
        if parent.axes_selection() is not None:
            a = parent.axes_selection()
            fig_axes = a.figobj
            menus2 = fig_axes.canvas_menu()
            if len(parent.selection) == 0:
                menus2.extend(fig_axes.canvas_axes_menu())
        if len(menus2) == 0:
            if len(parent.selection) == 1:
                a = (parent.selection[0])()
                if a is not None:
                    if a.figobj is not None:
                        menus2 = a.figobj.canvas_menu()
                        if fig_axes is not None:
                            menus2.extend(
                                a.figobj.canvas_axes_selection_menu(fig_axes))
        if len(menus2) != 0 and len(menus) != 0:
            menus = menus + [('---', None, None)]
            menus = menus + menus2
        if len(parent.selection) > 1:
            if parent._check_can_group():
                if len(menus) != 0:
                    menus = menus + [('---', None, None)]
                if all([x().figobj.get_figaxes()
                        is None for x in parent.selection]):
                    menus = menus + [('+Arrange X...', None, None),
                                     ('left', self.onArrange, (1, 0)),
                                     ('center', self.onArrange, (1, 1)),
                                     ('right', self.onArrange, (1, 2)),
                                     ('!', None, None),
                                     ('+Arrange Y...', None, None),
                                     ('top', self.onArrange, (2, 2)),
                                     ('center', self.onArrange, (2, 1)),
                                     ('bottom', self.onArrange, (2, 0)),
                                     ('!', None, None),
                                     ('+Distribute X...', None, None),
                                     ('left', self.onArrange, (4, 0)),
                                     ('center', self.onArrange, (4, 1)),
                                     ('right', self.onArrange, (4, 2)),
                                     ('!', None, None),
                                     ('+Distribute Y...', None, None),
                                     ('top', self.onArrange, (8, 2)),
                                     ('center', self.onArrange, (8, 1)),
                                     ('bottom', self.onArrange, (8, 0)),
                                     ('!', None, None), ]
                menus = menus + [
                    ('---', None, None),
                    ('Group', self.onGroup, None), ]

        if arrange_menu:
            if len(menus) != 0:
                menus = menus + [('---', None, None)]
            menus = menus + \
                [('Forward', self.onForward, None),
                 ('Backward', self.onBackward, None),
                    ('Front', self.onFront, None),
                    ('Bottom', self.onBottom, None)]
        if (len(parent.selection) == 1 and
            parent.selection[0]() is not None and
                parent.selection[0]().figobj.get_figaxes() is None):
            if parent.selection[0]().figobj.get_frameart():
                menus = menus + \
                    [('Unset FrameArt', self.onUnsetFrameArt, None)]
            else:
                menus = menus + [('Set FrameArt', self.onSetFrameArt, None)]
        frame = cbook.FindFrame(parent)

        menus = frame.viewer_canvasmenu() + menus
        self._menus = len(menus)
        if len(menus) != 0:
            cbook.BuildPopUpMenu(self, menus, eventobj=parent,
                                 xy=xy, xydata=xydata)
            self.xy = xy

    def onGroup(self, e):
        canvas = e.GetEventObject()
        canvas.group()

    def on3DXY(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('xy')

    def on3DXZ(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('xz')
        pass

    def on3DYZ(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('yz')

    def on3DDefaultView(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('default')

    def on3DUpDown(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('updown')

    def on3D_Rot90(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('90')

    def on3D_Rot90r(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('-90')

    def on3DOrtho(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('ortho')

    def on3DFrustum(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('frustum')

    def on3DEqualAspect(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('equal')

    def on3DAutoAspect(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('auto')

    def on3DClipOn(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('clip')

    def on3DClipOff(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('noclip')

    def on3DCutPlaneOn(self, e):
        from ifigure.widgets.cutplane_buttons import add_cutplane_btns

        canvas = e.GetEventObject()
        win = canvas.GetTopLevelParent()
        win.view('cp')

        if canvas._cutplane_btns is None:
            canvas._cutplane_btns = add_cutplane_btns(win)

    def on3DCutPlaneOff(self, e):
        canvas = e.GetEventObject()
        win = canvas.GetTopLevelParent()
        win.view('nocp')

        if canvas._cutplane_btns is not None:
            canvas._cutplane_btns.Destroy()
        canvas._cutplane_btns = None

    def on3DAxesIconOff(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('noaxesicon')

    def on3DAxesIconOn(self, e):
        canvas = e.GetEventObject()
        canvas.GetTopLevelParent().view('axesicon')

    def onResetRotCenter(self, e):
        canvas = e.GetEventObject()
        canvas.axes_selection()._gl_use_rot_center = False

    def onSameXY(self, e):
        canvas = e.GetEventObject()
        canvas.set_samexy()

    def onSameXYZ(self, e):
        canvas = e.GetEventObject()
        canvas.set_samexyz()

    def onSameX(self, e):
        canvas = e.GetEventObject()
        canvas.set_samex()

    def onSameX_autoY(self, e):
        canvas = e.GetEventObject()
        canvas.set_samex_autoy()

    def onSameY(self, e):
        canvas = e.GetEventObject()
        canvas.set_samey()

    def onSameC(self, e):
        canvas = e.GetEventObject()
        canvas.set_samec()

    def onXYauto_all(self, e):
        canvas = e.GetEventObject()
        canvas.set_xyauto_all()

    def onXauto_all(self, e):
        canvas = e.GetEventObject()
        canvas.set_xauto_all()

    def onYauto_all(self, e):
        canvas = e.GetEventObject()
        canvas.set_yauto_all()

    def onXYauto(self, e):
        canvas = e.GetEventObject()
        canvas.set_xyauto()

    def onXauto(self, e):
        canvas = e.GetEventObject()
        canvas.set_xauto()

    def onYAuto(self, e):
        canvas = e.GetEventObject()
        canvas.set_yauto()

    def onCAuto(self, e):
        canvas = e.GetEventObject()
        canvas.set_cauto()

    def onSameView(self, e):
        canvas = e.GetEventObject()
        canvas.set_sameview()

    def onForward(self, e):
        canvas = e.GetEventObject()
#        canvas.nodraw_on()
        a = []
        for item in canvas.selection:
            if item() is not None:
                a.extend(item().figobj.move_zorder_forward(get_action=True))
#        canvas.draw()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='move forward')

    def onBackward(self, e):
        canvas = e.GetEventObject()
#        canvas.nodraw_on()
        a = []
        for item in canvas.selection:
            if item() is not None:
                a.extend(item().figobj.move_zorder_backward(get_action=True))
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='move backword')

#        canvas.draw()
    def onFront(self, e):
        canvas = e.GetEventObject()
#        canvas.nodraw_on()
        a = []
        for item in canvas.selection:
            if item() is not None:
                a.extend(item().figobj.set_zorder_front(get_action=True))
#        canvas.draw()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='move to front')

    def onBottom(self, e):
        canvas = e.GetEventObject()
#        canvas.nodraw_on()
        a = []
        for item in canvas.selection:
            if item() is not None:
                a.extend(item().figobj.set_zorder_bottom(get_action=True))
#        canvas.draw()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='move to bottom')

    def onSetFrameArt(self, e):
        #        print 'set frame art'
        canvas = e.GetEventObject()
        for item in canvas.selection:
            print(item())
            if item() is not None:
                item().figobj.set_frameart(True)
        canvas.draw_all()
        canvas.unselect_all()

    def onUnsetFrameArt(self, e):
        canvas = e.GetEventObject()
        for item in canvas.selection:
            if item() is not None:
                item().figobj.set_frameart(False)
        canvas.draw_all()
        canvas.unselect_all()

    def on3Dslice(self, e):
        canvas = e.GetEventObject()
        canvas.show_3d_slice_palette(self.xy)

    def onArrange(self, e):
        canvas = e.GetEventObject()
        print(('arrange', e.ExtraInfo))

        dx = [0] * len(canvas.selection)
        dy = [0] * len(canvas.selection)

        offset = 0
        if (e.ExtraInfo[0] == 2 or
                e.ExtraInfo[0] == 8):
            offset = 2

        if e.ExtraInfo[1] == 0:
            b = [a().figobj.get_artist_extent2(a())[0 + offset]
                 for a in canvas.selection]
        elif e.ExtraInfo[1] == 2:
            b = [a().figobj.get_artist_extent2(a())[1 + offset]
                 for a in canvas.selection]
        elif e.ExtraInfo[1] == 1:
            b = [(a().figobj.get_artist_extent2(a())[0 + offset] +
                  a().figobj.get_artist_extent2(a())[1 + offset]) / 2
                 for a in canvas.selection]
#        print 'ref', b
        if (e.ExtraInfo[0] == 1 or
                e.ExtraInfo[0] == 2):
            d = [x - b[0] for x in b]
        else:
            import numpy as np
            b2 = np.linspace(min(b), max(b), len(b))
            idx = [x[0] for x in sorted(enumerate(b), key=lambda x:x[1])]
            b3 = [b2[i] for i in idx]
            d = [b[i] - b3[i] for i in range(len(b))]
        h = []

        for i in range(len(canvas.selection)):
            a = canvas.selection[i]()
            figobj = a.figobj
            if (e.ExtraInfo[0] == 1 or
                    e.ExtraInfo[0] == 4):
                scale = [1, 0, 0, 1, -d[i], 0]
            else:
                scale = [1, 0, 0, 1, 0, -d[i]]
            h = h + figobj.scale_artist(scale, action=True)

#        hist = canvas._figure.figobj.get_root_parent().app.history
        if len(h) != 0:
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(h, menu_name='arrange')

#        window = canvas.GetTopLevelParent()
#        hist = GlobalHistory().get_history(window)
#        hist.start_record()
#        for item in h: hist.add_history(item)
#        hist.stop_record()
#        canvas.draw()

    def onCursorMenu(self, evt, choice):
        canvas = evt.GetEventObject()
        canvas._cursor_mode = choice
        for f_axes in canvas._figure.figobj.walk_axes():
            f_axes._cursor_data = [tuple(), tuple(), tuple()]

    def onCursorSetting(self, evt):
        import ifigure
        from ifigure.utils.edit_list import DialogEditList
        config = ifigure._cursor_config

        name = ["1dcolor1", "1dcolor2", "1dthick",
                "1dalpha", "2dcolor", "2dalpha",
                "format"]
        list = [["Line color (1)", config[name[0]], 6, None],
                ["Line color (2)", config[name[1]], 6, None],
                ["Line thickness", str(config[name[2]]), 7, None],
                ["Line alpha", config[name[3]], 105, None],
                ["2D cursor color", config[name[4]], 6, None],
                ["2D cursor alpha", config[name[5]], 105, None],
                ["StatusBar Format", config[name[6]], 0, None], ]
        ans, value = DialogEditList(list, modal=True, tip=None,
                                    parent=evt.GetEventObject())
        if ans:
            for i in range(len(name)):
                config[name[i]] = value[i]

    def onGeneratePath(self, evt):
        canvas = evt.GetEventObject()
        ax = canvas.axes_selection().figobj
        for path in self._cur_paths:
            x = path.vertices[:, 0]
            y = path.vertices[:, 1]
            if len(x) == 0:
                continue
            name = ax.get_next_name('cursor_path')
            child = ax.get_child(idx=ax.add_plot(name, x, y, 'k'))
            child.realize()
        book = ax.get_figbook()
        ifigure.events.SendChangedEvent(book, w=canvas, useProcessEvent=True)
        ifigure.events.SendPVDrawRequest(
            book, wait_idle=True, refresh_hl=False)


class spacer_panel(wx.Panel):
    def __init__(self, *args, **kargs):
        super(spacer_panel, self).__init__(*args, **kargs)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def set_color(self, value):
        self._color = value
        return self

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        self.Unbind(wx.EVT_PAINT)
        if dc is None:
            dc = wx.ClientDC(self)
#       print 'drawing spacer'
        dc.BeginDrawing()
        w, h = self.GetSize()
#       print w, h
        dc.SetPen(wx.Pen(self._color))
        dc.SetBrush(wx.Brush(self._color))
        dc.DrawRoundedRectangle(0, 0, w, h, 0)
        dc.EndDrawing()
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnSize(self, evt):
        self.Refresh(eraseBackground=False)


class ifigure_canvas(wx.Panel, RangeRequestMaker):
    def __init__(self, parent=None, figure=None):
        super(ifigure_canvas, self).__init__(parent, wx.ID_ANY, (0, 0), (1, 1))
        self.SetWindowStyle(self.GetWindowStyle() &
                            ~wx.TAB_TRAVERSAL)
        self._std_bg_color = self.TopLevelParent.GetBackgroundColour()
        self._isec = -1  # isec is axes index referred in interactive command
        # it is updated when click happenes
        self._figure = figure
        self._last_update = 0
        self._hold_once = False
        self._drawing = False
#      self._nodraw = False
        self._draw_refresh_hl_request = False
        self._picked = False
        self._control = False
        self._insert_mode = False
        self._insert_st_event = None
        self._iaxesselection_mode = False
        self._line_insert_mode = False
        self._bindidle = False
        self._previous_lclick = 0.
        self._previous_lclickxy = (0., 0.)
        self._last_draw_time = -1.
#      self._press_key = None
        self._mpl_mode = 'normal'
        self._mplc = None
        self._onkey_id = None
        self._show_cursor = False
        self._cursor_mode = 1
        self._cursor_owner = []
        self._cursor_target = None
        self._txt_box = None
        self._popup_style = popup_style_default
        self._mailpic_format = 'pdf'
        self._mpl_artist_click = None  # mpl artist not directly managed by ifigure
        from numpy import inf
        self._a_mode_scale_anchor = [inf, -inf, inf, -inf]
        self._a_mode_scale_mode = False
        self._3d_rot_mode = 0
        self._frameart_mode = False
        self._alt_shift_hit = False
        self._full_screen_mode = False
        self._skip_blur_hl = False  # on during drag
        self.dblclick_occured = False  # double click

        self._cutplane_btns = None

        self.selection = []
        self.axes_selection = cbook.WeakNone()

        self.toolbar = navibar(self)
        self.spacer1 = spacer_panel(self).set_color([0, 0, 0])
        if turn_on_gl:
            try:
                from ifigure.matplotlib_mod.backend_wxagg_gl import FigureCanvasWxAggModGL as CanvasGL
                self.canvas = CanvasGL(self, -1, self._figure)
            except BaseException:
                import traceback
                traceback.print_exc()
                print('failed to creat GL canvas, using standard canvas')
                self.canvas = Canvas(self, -1, self._figure)
                globals()['turn_on_gl'] = False
        else:
            self.canvas = Canvas(self, -1, self._figure)
#      self.canvas.SetWindowStyle(self.canvas.GetWindowStyle() &
#                          ~wx.TAB_TRAVERSAL)

        # self.canvas.Unbind(wx.EVT_IDLE) ### testing this to see if it reduces
        # idle time cpu load
        self.spacer2 = spacer_panel(self).set_color([0, 0, 0])
        #      self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.onLeftDClick)
        self.canvas.SetSizeHints(minW=100, minH=100)
        self.mpl_connect()
        self._layout_mode = False
        self.layout_editor = layout_editor(self)

        self.draghandlers = [ifigure_canvas_draghandler(self),
                             ifigure_canvas_draghandler_pan(self),
                             ifigure_canvas_draghandler_zoom(self),
                             ifigure_canvas_draghandler_selecta(self),
                             ifigure_canvas_draghandler_none(self),
                             ifigure_canvas_draghandler_line(self),
                             ifigure_canvas_draghandler_rb(self),
                             ifigure_canvas_draghandler_ellip(self),
                             ifigure_canvas_draghandler_curve(self),
                             ifigure_canvas_draghandler_cursor(self),
                             ifigure_canvas_draghandler_3d(self),
                             ifigure_canvas_draghandler_3d_sel(self),
                             ]
        self.draghandler = self.draghandlers[0]
        self.canvas.set_wheel_cb(self.on_mouse_wheel)
#      self.toolbar = Toolbar(self.canvas)
#      self.toolbar.Realize()
#      self.fig_objs=[]

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.toolbar, 0, wx.EXPAND)
        self.sizer2 = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.sizer2, 1, wx.EXPAND)

        self.sizer2.Add(self.spacer1, 0)
        self.sizer2.Add(self.canvas, 1, wx.EXPAND, 0)
        self.sizer2.Add(self.spacer2, 0)
        self.spacer1.Hide()
        self.spacer2.Hide()

        self.toolbar.DoLayout()
        sizer.Layout()

        self.SetSizer(sizer)

        # dt=ifigure_DropTarget(self)
        # self.canvas.SetDropTarget(dt)
        #self.Bind(wx.EVT_SIZE, self.HandleResize)

        from ifigure.ifigure_config import icondir
        if len(bitmaps) == 0:
            for icon in bitmap_names:
                path = os.path.join(icondir, '16x16', icon)
                if icon[-3:] == 'png':
                    im = wx.Image(path, wx.BITMAP_TYPE_PNG)
                    bitmaps[icon[:-4]] = im.ConvertToBitmap()

        from ifigure.events import CANVAS_EVT_DRAWREQUEST
        from ifigure.events import SendCanvasDrawRequest
        self.Bind(CANVAS_EVT_DRAWREQUEST, self.onDrawRequest)
        self.canvas.Bind(wx.EVT_SET_FOCUS, self.onCanvasFocus)
        self.canvas.Bind(wx.EVT_KILL_FOCUS, self.onCanvasKillFocus)
        #self.canvas.Bind(wx.EVT_ENTER_WINDOW, self.onCanvasFocus)
        #self.canvas.Bind(wx.EVT_LEAVE_WINDOW, self.onCanvasKillFocus)

        #self.canvas.Bind(wx.EVT_CHAR, self.test)
        self._cursor_icon = None

    def test(self, evt):
        def func(self):
            if self.FindFocus() != self.canvas:
                self.canvas.SetFocus()
        wx.CallAfter(func, self)
        evt.Skip()

    def close(self):
        dprint2("process close window")
        for dh in self.draghandlers:
            dh.clean(None)
        self.draghandlers = None
        self.draghandler = None
        self.canvas.set_wheel_cb(None)
        self.mpl_disconnect()
        self.canvas = None

    def hold_once(self, value=None):
        if value is None:
            return self._hold_once
        else:
            self._hold_once = value

    def onCanvasFocus(self, e):
        #print('get focus')
        if self.canvas is not None:
            self.mpl_connect(mode=self._mpl_mode)
        e.Skip()

    def onCanvasKillFocus(self, e):
        #print('kill focus')
        #       self.mpl_connect(mode = self._mpl_mode)
        if self.canvas is not None:
            self.mpl_disconnect()

        # if hasattr(self.draghandler, "dragdone_killfocus"):
        #    self.draghandler.dragdone_killfocus()
        if self.draghandler is not None:
            self.draghandler.unbind_mpl()
        e.Skip()

    def enter_layout_mode(self):
        self._layout_mode = True

        if self.axes_selection() is None:
            for a in self._figure.figobj.walk_axes():
                if not a._floating:
                    if len(a._artists) > 0:
                        self.set_axes_selection(a._artists[0])
                        break

        self.layout_editor.enter_layout_mode()
        self.toolbar.SetPMode()
        self.mpl_connect(mode='layout')

    def exit_layout_mode(self):
        if self._layout_mode:
            self._layout_mode = False
            self.layout_editor.exit_layout_mode()
            self.mpl_connect(mode='normal')
            self.draw()

    def show_spacer(self, w=None, h=None, direction=wx.HORIZONTAL):
        sizer = self.GetSizer()
        sizer.Detach(self.sizer2)
        self.sizer2.Detach(self.canvas)
        self.sizer2.Detach(self.spacer1)
        self.sizer2.Detach(self.spacer2)
#       xd, yd = wx.GetDisplaySize()
        if direction is not None:
            self.sizer2 = wx.BoxSizer(direction)
        self.spacer1.SetMinSize((w, h))
        self.spacer2.SetMinSize((w, h))
        sizer.Add(self.sizer2, 1, wx.EXPAND)
        self.sizer2.Add(self.spacer1, 0)
        self.sizer2.Add(self.canvas, 1, wx.EXPAND, 0)
        self.sizer2.Add(self.spacer2, 0)

        rgba = [int(x * 255) for x in self._figure.get_facecolor()]
        self.std_bg_color = self.TopLevelParent.GetBackgroundColour()
        self.TopLevelParent.SetBackgroundColour(rgba[0:3])
        self.spacer1.set_color(rgba[0:3])
        self.spacer2.set_color(rgba[0:3])
#       self.spacer1.SetBackgroundColour(rgba[0:3])
#       self.spacer2.SetBackgroundColour(rgba[0:3])
#       self.spacer1.SetForegroundColour(rgba[0:3])
#       self.spacer2.SetForegroundColour(rgba[0:3])

        self.spacer1.Refresh()
        self.spacer2.Refresh()
        self.spacer1.Show()
        self.spacer2.Show()

    def hide_spacer(self):
        self.spacer1.SetSize((-1, -1))
        self.spacer2.SetSize((-1, -1))
        self.spacer1.Hide()
        self.spacer2.Hide()
        self.TopLevelParent.SetBackgroundColour(self._std_bg_color)

    def HandleResize(self, evt):
        print('canvas handle_resize')
        print(self.TopLevelParent.GetSize())
#       if self._figure is not None:
#           self.canvas._onSize()
        evt.Skip()

    def chain_layout(self):
        '''
        does it do magic?
        '''
        p = self
        while p is not None:
            p.Layout()
            p = p.GetParent()

    def mpl_connect(self, mode='normal'):
        if self._figure is None:
            return
        if self.canvas.figure is None:
            return
        self.mpl_disconnect()
        self._mpl_mode = mode
        #print("setting mode", mode)
        if mode == 'normal':
            self._mplc = [self.canvas.mpl_connect('button_press_event',
                                                  self.buttonpress),
                          self.canvas.mpl_connect('button_release_event',
                                                  self.buttonrelease),
                          self.canvas.mpl_connect('scroll_event',
                                                  self.mousescroll),
                          self.canvas.mpl_connect('key_press_event',
                                                  self.onKey),
                          self.canvas.mpl_connect('key_release_event',
                                                  self.onKey2),
                          # self.canvas.mpl_connect('resize_event',
                          #                         self.onResize),
                          self.canvas.mpl_connect('draw_event', self.onDraw),
                          ]
            if self.canvas.HasFocus():
                self._mplc.append(
                    self.canvas.mpl_connect(
                        'motion_notify_event',
                        self.motion_event))
        elif mode == '3dpanrotzoom':
            self._mplc = [self.canvas.mpl_connect('button_press_event',
                                                  self.buttonpress),
                          self.canvas.mpl_connect('button_release_event',
                                                  self.buttonrelease),
                          ]

        elif mode == 'axesselection':
            self._mplc = [  # self.canvas.mpl_connect('button_press_event',
                #                       self.buttonpress),
                self.canvas.mpl_connect('button_release_event',
                                        self.iaxesselection_release),
                #                 self.canvas.mpl_connect('key_press_event',
                #                                         self.onKey),
                #                 self.canvas.mpl_connect('key_release_event',
                #                                         self.onKey2),
                #                 self.canvas.mpl_connect('resize_event', self.onResize),
                self.canvas.mpl_connect('motion_notify_event',
                                        self.iaxesselection_motion)]
        elif mode == 'line_insert':
            self._mplc = [self.canvas.mpl_connect('button_press_event',
                                                  self.line_insert_press),
                          self.canvas.mpl_connect('button_release_event',
                                                  self.line_insert_release),
                          self.canvas.mpl_connect('motion_notify_event',
                                                  self.line_insert_motion)]
        elif mode == 'dnd':
            self._mplc = [self.canvas.mpl_connect('motion_notify_event',
                                                  self.dnd_motion)]
        elif mode == 'layout':
            self._mplc = [self.canvas.mpl_connect('button_press_event',
                                                  self.layout_editor.buttonpress),
                          self.canvas.mpl_connect('button_release_event',
                                                  self.layout_editor.buttonrelease),
                          self.canvas.mpl_connect('pick_event',
                                                  self.layout_editor.onpick),
                          self.canvas.mpl_connect('draw_event', self.onDraw), ]

    def mpl_disconnect(self):
        # print("mpi_disconnect")
        if self._mplc is None:
            return
        if self.canvas.figure is None:
            return
        for id in self._mplc:
            self.canvas.mpl_disconnect(id)
        self._mplc = None

    def set_3dzoom_mode(self, value, rotate_btn=1, pan_btn=2, zoom_btn=3):
        if self._figure is None:
            return
        f_page = self._figure.figobj
        if f_page is None:
            return
        if value:
            for f_axes in f_page.walk_axes():
                if not f_axes.get_3d():
                    continue
                ax = f_axes._artists[0]

                ax.disable_mouse_rotation()
                ax.set_mouse_button(rotate_btn=rotate_btn, zoom_btn=zoom_btn,
                                    pan_btn=pan_btn)
#           self.mpl_disconnect()
#           self.mpl_connect('normal')
        else:
            for f_axes in f_page.walk_axes():
                if not f_axes.get_3d():
                    continue
                ax = f_axes._artists[0]
                ax.disable_mouse_rotation()
#           self.mpl_disconnect()
#           self.mpl_connect('normal')

    # this is read-only!
    def set_figure(self, figure):
        self.set_3dzoom_mode(False)
        self.unselect_all()
        self.axes_selection = cbook.WeakNone()

        self.mpl_disconnect()
        self.canvas.figure = figure
        self.mpl_connect()
        self._figure = figure

        # this enforce the size of figure fits with window size
        if figure is not None:
            dpival = figure.dpi
            winch = self.canvas._width / dpival
            hinch = self.canvas._height / dpival
            figure.set_size_inches(winch, hinch, forward=False)

        try:
            self.set_axes_selection(figure.figobj.get_axes(0)._artists[0])
        except BaseException:
            pass

    def get_figure(self):
        return self._figure

    def set_property_editor(self, pe):
        self.property_editor = pe

    def set_axes_selection(self, axes):
        self.axes_selection = weakref.ref(axes)
        if axes.figobj.get_3d():
            self.toolbar.Show3DMenu()
        else:
            self.toolbar.Hide3DMenu()

    def get_canvas_screen_size(self):
        s = self.canvas.GetClientSize()
        return s

    def set_canvas_screen_size(self, s):
        self.canvas.SetClientSize(s)

    def get_axes_selection(self):
        return self.axes_selection()

    def onResize(self, evt):
        return
#        print('onResize in ifigure_canvas')
#       self.draw()
        if self._figure.figobj is not None:
            self._figure.figobj.reset_axesbmp_update()
            self._figure.figobj.onResize(evt)
#           self.draw_later()
        return

    def turn_on_key_press(self):
        self._full_screen_mode = True

    def turn_off_key_press(self):
        self._full_screen_mode = False

    def full_screen(self, value):
        if value:
            self.toolbar.Hide()
        else:
            self.toolbar.Show()

    def onKey(self, evt):
        if evt.guiEvent.GetKeyCode() == wx.WXK_SHIFT:
            self._alt_shift_hit = True
        if evt.guiEvent.GetKeyCode() == wx.WXK_ALT:
            self._alt_shift_hit = True
        if evt.guiEvent.GetKeyCode() == wx.WXK_ESCAPE:
            if self._full_screen_mode:
                self.GetTopLevelParent().onFullScreen(evt=evt, value=False)

    def onKey2(self, evt):
        #       print 'onKey2 in ifigure canvas'

        if self.axes_selection() is not None:
            ax = self.axes_selection()
            if ax.figobj is None:
                ax = None
                is3Dax = False
            else:
                is3Dax = ax.figobj.get_3d()
        else:
            ax = None
            is3Dax = False

        if self._txt_box is not None and self._txt_box.IsShown():
            self.onKey3(evt)
            return
        if evt.key == 'backspace':
            if len(self.selection) != 0:
                self.del_selection()
#             ifigure.events.SendChangedEvent(self._figure.figobj, self)
                self.draw()
            return

        if evt.guiEvent.GetKeyCode() == wx.WXK_SHIFT:
            if is3Dax and self._alt_shift_hit:
                # select -> zoom up -> zoom down -> pan -> 3d zoom
                if self.toolbar.mode == 'pan':
                    self.toolbar.ClickP1Button('3dzoom')
                elif self.toolbar.mode == '3dzoom':
                    self.toolbar.ClickP1Button('select')
                elif self.toolbar.mode == 'select':
                    self.toolbar.ClickP1Button('zoom')
                elif self.toolbar.mode == 'zoom':
                    if self.toolbar.ToggleZoomForward():
                        pass
                    else:
                        self.toolbar.ClickP1Button('pan')
                else:
                    self.toolbar.ClickP1Button('zoom')

            elif self.toolbar.mode == 'zoom':
                self.toolbar.ToggleZoomUpDown()
            elif self.toolbar.mode == 'pan':
                self.toolbar.TogglePanAll()
            elif self.toolbar.mode == '3dzoom':
                if self._3d_rot_mode == 0:
                    self.toolbar.SetZoomCursor()
                    self._3d_rot_mode = 1
                else:
                    self.toolbar.Set3DZoomCursor()
                    self._3d_rot_mode = 0
        elif evt.guiEvent.GetKeyCode() == wx.WXK_ALT:
            if is3Dax and self._alt_shift_hit:
                # select -> 3dzoom -> pan -> zoom down -> zoom up
                if self.toolbar.mode == 'zoom':
                    if self.toolbar.ToggleZoomBackward():
                        pass
                    else:
                        self.toolbar.ClickP1Button('select')
                elif self.toolbar.mode == 'select':
                    self.toolbar.ClickP1Button('3dzoom')
                elif self.toolbar.mode == '3dzoom':
                    self.toolbar.ClickP1Button('pan')
                elif self.toolbar.mode == 'pan':
                    self.toolbar.ClickP1Button('zoom')
                    self.toolbar.ToggleZoomForward()
                else:
                    self.toolbar.ClickP1Button('3dzoom')

            elif self.toolbar.mode == 'zoom':
                self.toolbar.ToggleZoomMenu()
            elif self.toolbar.mode == '3dzoom':
                if self._3d_rot_mode == 0:
                    self.toolbar.SetPanCursor()
                    self._3d_rot_mode = 2
                else:
                    self.toolbar.Set3DZoomCursor()
                    self._3d_rot_mode = 0

        if True:
            if evt.guiEvent.ShiftDown():
                step = 5
            else:
                step = 1
            flag = False

            if evt.guiEvent.GetKeyCode() == wx.WXK_UP:
                scale = [1, 0, 0, 1, 0, step]
                flag = True
            elif evt.guiEvent.GetKeyCode() == wx.WXK_DOWN:
                scale = [1, 0, 0, 1, 0, -step]
                flag = True
            elif evt.guiEvent.GetKeyCode() == wx.WXK_RIGHT:
                scale = [1, 0, 0, 1, step, 0]
                flag = True
            elif evt.guiEvent.GetKeyCode() == wx.WXK_LEFT:
                scale = [1, 0, 0, 1, -step, 0]
                flag = True
            if flag:
                #              window = self.GetTopLevelParent()
                #              hist = GlobalHistory().get_history(window)
                #              hist = self._figure.figobj.get_root_parent().app.history
                h = []
                for a in self.selection:
                    ac = a().figobj.scale_artist(scale, True)
                    if ac is not None:
                        h = h + ac
#              if len(h) != 0:
#                 hist.start_record()
#                 for item in h: hist.add_history(item)
#                 hist.stop_record()
                if len(h) != 0:
                    window = self.GetTopLevelParent()
                    GlobalHistory().get_history(window).make_entry(h, menu_name='move')
                return

        if hasattr(evt.guiEvent, 'RawControlDown'):
            if not evt.guiEvent.RawControlDown():
                return
        else:
            if not evt.guiEvent.ControlDown():
                return

        if evt.key.upper() == 'G':
            if not evt.guiEvent.ShiftDown():  # group
                if self._check_can_group():
                    self.group()
            else:  # ungroup
                if self._check_can_ungroup():
                    self.ungroup()

        elif evt.key.upper() == 'A':
            # control + A in amode = select all
            if self.toolbar.ptype == 'amode':
                #              print self.toolbar.mode
                if self.toolbar.mode == '':
                    self.unselect_all()
                    fig_page = self._figure.figobj
                    for name, child in fig_page.get_children():
                        if not isinstance(child, FigAxes):
                            for a in child._artists:
                                self.add_selection(a)
                    if len(self.selection) != 0:
                        ifigure.events.SendSelectionEvent(
                            fig_page, self, self.selection)
                    self.draw_later()
                    dprint1('select  all...')
        evt.guiEvent.Skip()

    def Cut(self):
        self.GetTopLevelParent().set_status_text('cut')
        self.cut_selection()
        self.draw_later()

    def Copy(self):
        self.GetTopLevelParent().set_status_text('copy')
        self.copy_selection()

    def Paste(self):
        self.GetTopLevelParent().set_status_text('paste')
        ret = self.paste_selection()
        self.draw_later()
        return ret

    def _mpl_artist_gone(self, obj):
        self._mpl_artist_click = None

    def onpick(self, event, extra):
        self._mpl_artist_click = None
        if "mpl_artist" in extra:
            self._mpl_artist_click = (weakref.ref(extra["mpl_artist"],
                                                  self._mpl_artist_gone),
                                      weakref.ref(extra["linked_artist"],
                                                  self._mpl_artist_gone))
            return
        a = extra["child_artist"]
        if a is None:
            # if child_artist is none, pick does not happen
            # but it exits a picker loop, which prevent
            # looking for item in lower layer axes.
            return
        if a.axes is not None:
            self.set_axes_selection(a.axes)
#          self.axes_selection=weakref.ref(a.axes)
        if event.button != 1:
            return

        self._picked = True
        event.artist = a
        self._pevent = event
        return

    def mousescroll(self, event):
        if self.toolbar.mode != '':
            return
        if not bool(self):
            return
        frame = self.GetTopLevelParent()
        if frame is None:
            return
        #frame = cbook.FindFrame(self)
        if event.step < 0:
            frame.onNextPage(event.guiEvent)
        if event.step > 0:
            frame.onPrevPage(event.guiEvent)

    def mousedrag(self, event):
        # print('mousedrag')
        # drag event cancel picking
        #      if len(self.selection) != 0:
        # print 'mouse drag', self.selecetion[0]().figobj.get_full_path()
        from ifigure.mto.fig_grp import FigGrp
        ptype = self.toolbar.ptype
        if self._picked:
            flag = False
            for b in self.selection:
                if b() is None:
                    continue
                if b().figobj is None:
                    continue
                figobj = b().figobj
                if isinstance(figobj, FigGrp):
                    box = figobj.get_artist_extent_all()
                    figobj._artist_extent = box
                    flag, extra = figobj.picker_a(figobj._artists[0],
                                                  event)
                    figobj.canvas_unselected()
                else:
                    #                if ptype == 'pmode':
                    #                    flag, extra = figobj.picker(b(), event)
                    #                if ptype == 'amode':
                    flag, extra = figobj.picker_a(b(), event)
                if flag:
                    break
            if not flag:
                self._picked = False
                self._pevent = None
                self.draghandler.dragstart(event)
            else:
                if self.draghandler is self.draghandlers[0]:
                    a = []
                    for b in self.selection:
                        if not b() in a:
                            a.append(b())
                    self.draghandler.set_artist(a)
                self._picked = False
                self._pevent = None
                self.draghandler.dragstart(event)
        self.draghandler.dodrag(event)

    def mousedrag_cursor(self, event):
        # print('mousedrag_cursor')
        if not self.draghandler.dragging:
            if (len(self.selection) == 1 and
                    self.selection[0]() is not None):
                self._cursor_target = weakref.ref(self.selection[0]())
            self._picked = False
            self.draghandler.dragstart(event)
            if not self.draghandler.dragging:
                self.draghandler.unbind_mpl()
                return
        self.draghandler.dodrag(event)

    def mousedrag_panzoom(self, event):
        #print('mousedrag_panzoom', time.time()-self._previous_lclick)
        if time.time() - self._previous_lclick < scinterval_th:
            # too short interval is ignored
            return
        self._skip_blur_hl = True
        if not self.draghandler.dragging:
            self._picked = False
            self.draghandler.dragstart(event)
            if not self.draghandler.dragging:
                self.draghandler.unbind_mpl()
                return
        self.draghandler.dodrag(event)

    def run_picker(self, event):
        #       optype =  self.toolbar.ptype
        #       self.toolbar.ptype = 'amode'
        hit, extra = cpicker.fig_picker(self._figure, event)
        if hit:
            self.onpick(event, extra)
            return
        #
        # do floating obj (not axes) first
        #
        for obj in self._figure.figobj.walk_tree():
            if obj._floating:
                for a in obj.get_artists_for_pick():
                    if isinstance(obj, FigAxes):
                        continue
                    hit, extra = obj.picker_a(a, event)
                    if hit:
                        extra['child_artist'] = a
                        self.onpick(event, extra)
                        return
        #
        #
        # reordering floating axes if necessary
        #
        floating_axes = [
            x for x in sorted(
                [
                    (axes.figobj.getp('zorder'),
                     axes) for axes in self._figure.axes if axes.figobj._floating],
                key=lambda x:x[0])]

        if len(floating_axes) != 0:
            fixed_axes_zordermax = max([axes.figobj.getp(
                'zorder') for axes in self._figure.axes if not axes.figobj._floating])

            if floating_axes[0][0] < fixed_axes_zordermax:
                for zorder, axes in sorted(floating_axes, key=lambda x: x[0]):
                    axes.figobj.set_zorder_front()

        figax_list = set([a.figobj for a in reversed(self._figure.axes)])

        alist = [a for a in
                 reversed(sorted([(o.getp('zorder'), o)
                                  for o in figax_list], key=lambda x:x[0]))]

        if len(alist) == 0:
            return
        zorder, figax_list = zip(*alist)
        for figax in figax_list:
            for ax in figax._artists:
                hit, extra = cpicker.axes_picker(ax, event)
                if hit:
                    self.onpick(event, extra)
                    break
            hit, extra = figax.picker_a(figax._artists[-1],
                                        event)
            if hit:
                break
        return
    '''
    Double click descrimator.

    Basically, I want to handle double clike as a one event, not a sequence
    of events

       mouse_down -> mouse_up (1) -> mouse_down (can be dobule click) -> mouse_up (2)

       using timer, we skip mouse_up(1) if it is double click.
       mouse_down (2) is also skipped if it is double click

       note: guiEvent loses background wxWidget objects when called with
             wxCallLater. We copyed the guiEvent to our own object to use
             it in the buttonrelease0.
    '''

    def buttonpress(self, event):
        self._previous_lclick = time.time()
        dist = ((event.x - self._previous_lclickxy[0])**2 +
                (event.y - self._previous_lclickxy[1])**2)**0.5
        self._previous_lclickxy = (event.x, event.y)

        if dist > 5:
            self.dblclick_occured = False
        else:
            self.dblclick_occured = event.dblclick

        if self.dblclick_occured:
            pass
        else:
            self.buttonpress0(event)

    def buttonrelease(self, event):
        #print("button release", event.guiEvent)
        evt = guiEventCopy(event.guiEvent)
        event.guiEvent_memory = evt

        if self.draghandler is not None:
            self.draghandler.unbind_mpl()

        self._click_interval = time.time() - self._previous_lclick
        wx.CallLater(dcinterval_ms, self.run_buttonrelease0, event)

    def run_buttonrelease0(self, event):
        if self._figure is None:
            return

        if self.dblclick_occured:
            self.dblclick_occured = False
            self._previous_lclick = time.time()
        else:
            self.buttonrelease0(event)

    def buttonpress0(self, event):
        if self._figure is None:
            return

        self._alt_shift_hit = False

        if self.draghandler is not None:
            self.draghandler.clean(None)

        if self.toolbar.mode == '':
            hit = 0
            if (abs(self._a_mode_scale_anchor[0] - event.x) < 10 and
                    abs(self._a_mode_scale_anchor[2] - event.y) < 10):
                x = self._a_mode_scale_anchor[1]
                y = self._a_mode_scale_anchor[3]
                hit = 1
            if (abs(self._a_mode_scale_anchor[0] - event.x) < 10 and
                    abs(self._a_mode_scale_anchor[3] - event.y) < 10):
                x = self._a_mode_scale_anchor[1]
                y = self._a_mode_scale_anchor[2]
                hit = 2
            if (abs(self._a_mode_scale_anchor[1] - event.x) < 10 and
                    abs(self._a_mode_scale_anchor[2] - event.y) < 10):
                x = self._a_mode_scale_anchor[0]
                y = self._a_mode_scale_anchor[3]
                hit = 3
            if (abs(self._a_mode_scale_anchor[1] - event.x) < 10 and
                    abs(self._a_mode_scale_anchor[3] - event.y) < 10):
                x = self._a_mode_scale_anchor[0]
                y = self._a_mode_scale_anchor[2]
                hit = 4
            if hit != 0:
                self.draghandler = self.draghandlers[6]
                self.draghandler.bind_mpl(event)
                self.draghandler.st_event.x = x
                self.draghandler.st_event.y = y
                self._a_mode_scale_mode = True
                return

                # print hit, event.x, event.y, self._a_mode_scale_anchor
        self.axes_selection = cbook.WeakNone()
        hit = False

#      hit, extra = cpicker.figure_picker(self._figure, event)

        if (not (self.toolbar.mode in ('zoom', 'pan', '3dzoom'))
                and event.button == 1):
            self.run_picker(event)

        elif event.button == 2:
            self.toolbar.ExitInsertMode()
            self.toolbar.SetPMode()
            if event.guiEvent.ShiftDown():
                self.toolbar.GoPan()
            else:
                self.toolbar.GoZoom()

        for axes in reversed(self._figure.axes):
            if axes is not axes.figobj._artists[0]:
                continue
            bbox = axes.get_position()
            pt = bbox.get_points()
            sec = [pt[0][0], pt[0][1],
                   pt[1][0] - pt[0][0], pt[1][1] - pt[0][1]]

            nx, ny = self.px2norm(event.x, event.y)

            if geom_util.check_inside(sec, nx, ny):
                self.set_axes_selection(axes)
#            self.axes_selection=weakref.ref(axes)
                #  print sec, nx, ny
                break

#      print event.button, event.key, self.toolbar.ptype
#      print self.toolbar.mode, self._picked
#      self._show_cursor = False
        if (self.toolbar.mode == 'cursor'):
            if self._cursor_target is not None:
                if self._cursor_target() is not None:
                    if self._cursor_target().figobj is None:
                        self._cursor_target = None
                    elif self.axes_selection() is None:
                        pass
                    else:
                        #                  print self._cursor_target().figobj.get_figaxes()
                        #                  print self.axes_selection().figobj
                        if (self._cursor_target().figobj.get_figaxes() is not
                                self.axes_selection().figobj):
                            #                      print('reset cursor target')
                            self._cursor_target = None
                else:
                    self._cursor_target = None
            self.draghandler = self.draghandlers[9]
            self.draghandler.bind_mpl(event)
#          self._show_cursor = True
            return
        if (event.button == 1 and
            #          self.toolbar.ptype == 'amode' and
            self.toolbar.mode in ['rect', 'text', 'line', 'curve', 'curve2',
                                  'circle', 'legend', 'colorbar',
                                  'eps', 'arrow']):
            #dprint1('toolbar mode ' + self.toolbar.mode)
            self._insert_mode = True
            self._insert_st_event = event
            if self.toolbar.mode == 'arrow':
                self.draghandler = self.draghandlers[5]
            elif self.toolbar.mode == 'rect':
                self.draghandler = self.draghandlers[6]
            elif self.toolbar.mode == 'circle':
                self.draghandler = self.draghandlers[7]
            elif self.toolbar.mode == 'curve':
                self.draghandler = self.draghandlers[8]
            elif self.toolbar.mode == 'curve2':
                return
            elif self.toolbar.mode == 'line':
                return
            else:
                self.draghandler = self.draghandlers[4]
            self.draghandler.bind_mpl(event)
            return

        if self.axes_selection() is not None:
            ax = self.axes_selection()
        else:
            ax = None

        # On MacOS (always 1, True with shift key, True with Opt key
        # On Linux (depends on button, True with shift key, True with Opt key
        # print event.button,  event.guiEvent.ShiftDown(),
        # event.guiEvent.AltDown()

        self._cursor_icon = None
        do_3d_rot = False
        if (self.toolbar.mode == '3dzoom' and
                event.button == 1):
            do_3d_rot = True
        if do_3d_rot:
            if (ax is not None and ax.figobj.get_3d()):
                if self._3d_rot_mode == 0:
                    self.set_3dzoom_mode(True)
                    ax._drag_mode = 'rot'
                elif self._3d_rot_mode == 1:
                    self.set_3dzoom_mode(True, zoom_btn=1, rotate_btn=10)
                    ax._drag_mode = 'zoom'
                else:
                    self.set_3dzoom_mode(True, pan_btn=1,
                                         zoom_btn=11, rotate_btn=10)
                    ax._drag_mode = 'pan'
                ax._button_press(event)
                self.draghandler = self.draghandlers[10]
                self.draghandler.bind_mpl(event)
            return

        if (event.button == 1 and
            self.toolbar.ptype == 'amode' and
                len(self.selection) == 0):
            self.draghandler = self.draghandlers[3]
            self.draghandler.bind_mpl(event)
            self.draghandler.d_mode = 'a'
            return

        if (event.button == 1 and
                self.toolbar.ptype == 'amode'):
            self.draghandler = self.draghandlers[0]
            self.draghandler.bind_mpl(event)
            self.draghandler.d_mode = 'a'
            return

        if ((event.button == 1 and event.key == 's') or
            (event.button == 1 and event.key == 'd') or
                self.toolbar.mode == 'zoom'):
            if (ax is not None and
                    ax.figobj.get_3d()):
                # 10 => no button to rotate ;D
                # if event.guiEvent.ShiftDown():
                self.draghandler = self.draghandlers[2]
                self.draghandler.bind_mpl(event)
                ax._drag_mode = 'zoom'
                # else:
                #    self.set_3dzoom_mode(True, zoom_btn = 1, rotate_btn = 10)
                #    ax._button_press(event)
                #    self.draghandler = self.draghandlers[10]
                #    self.draghandler.bind_mpl(event)
            else:
                self.set_3dzoom_mode(False)
                self.draghandler = self.draghandlers[2]
                self.draghandler.bind_mpl(event)
            return

        if ((event.button == 1 and event.key == 'a') or
                self.toolbar.mode == 'pan'):
            if (ax is not None and
                    ax.figobj.get_3d()):
                # 10 => no button to rotate ;D
                self.set_3dzoom_mode(True, pan_btn=1,
                                     zoom_btn=11, rotate_btn=10)
                ax._button_press(event)
                self.draghandler = self.draghandlers[10]
                self.draghandler.bind_mpl(event)
                ax._drag_mode = 'pan'
            else:
                self.set_3dzoom_mode(False)
                self.draghandler = self.draghandlers[1]
                self.draghandler.bind_mpl(event)
            return

        annote_selected = (len(self.selection) > 0 and
                           self.selection[0]() is not None and
                           self.selection[0]().figobj is not None and
                           self.selection[0]().figobj.get_figaxes() is None)

        if (event.button == 1 and self.toolbar.mode == '' and
            not annote_selected and
                ax is not None and ax.figobj.get_3d()):
            self.draghandler = self.draghandlers[11]
            self.draghandler.bind_mpl(event)
            ax._drag_mode = 'select'
            return

        if event.button == 3:
            self.mpl_connect('normal')
#      if event.button == 1 and event.key == 'd':
#         self.draghandler = self.draghandlers[2]
#         self.draghandler.bind_mpl(event)
#         return
        # if (event.button == 1 and
        #    self.toolbar.mode == ''):
        # print 'k=0 drag_handler'
        k = 0
        if len(self.selection) == 0:
            k = 3
        self.draghandler = self.draghandlers[k]
        self.draghandler.bind_mpl(event)
        self.draghandler.d_mode = 'a'

    def buttonrelease0(self, event):
        #print("button release0")
        self._alt_shift_hit = False
        self._skip_blur_hl = False
        double_click = False

        # check double click
        if event.guiEvent_memory.LeftUp():
            # print(time.time()-self._previous_lclick)
            if ((time.time() - self._previous_lclick) < dcinterval and
                    not self.draghandler.dragging):
                double_click = True

        drag_happend = False
        set_pmode = False
        if self.draghandler is not None:
            if self.draghandler.dragging:
                drag_happend = True
                self.draghandler.dragdone(event)
                if (self.toolbar.mode == 'cursor' or
                    self.toolbar.mode == 'zoom' or
                        self.toolbar.mode == 'pan'):
                    if event.button == 2:
                        set_pmode = True
                    event.button = 1
            self.draghandler.unbind_mpl()

        if self._insert_mode:
            dprint2('toolbar mode ' + self.toolbar.mode)
            self.insert_figobj(event)
            return

        if self._a_mode_scale_mode:
            self._a_mode_scale_mode = False
            self.do_amode_scale()
            return
        if event.button == 3:
            # context menu
            scr_size = self.canvas.get_width_height()
            m = ifigure_popup(self, xy=(event.x, event.y),
                              xydata=(event.xdata, event.ydata))
            if m._menus != 0:
                self.canvas.PopupMenu(m,  # ifigure_popup(self),
                                      [event.x, scr_size[1] - event.y])
            m.Destroy()
        if event.button == 1:
            # left click (deselect all if _picked is false)
            if self._picked:
                already_selected = False
                shift_down = event.guiEvent_memory.ShiftDown()
                for item in self.selection:
                    if item() is not None:
                        figobj = item().figobj
#                  if figobj is not None: figobj.highlight_artist(False)
                        if (self._pevent.artist == item() and
                                figobj._picker_a_mode == 0 and not figobj.isCompound()):
                            already_selected = True

                if already_selected and not double_click:
                    if shift_down:
                        #                 if event.key == 'shift':
                        self.unselect(self._pevent.artist)
                    else:
                        self.unselect_all()
                # elif double_click:
                #    pass
                else:
                    figobj = self._pevent.artist.figobj
                    if figobj.isCompound() and not double_click:
                        figobj._artists[0].mask_array_idx(shift_down)

                    if not event.guiEvent_memory.ShiftDown() and not double_click:
                        self.unselect_all()

                    if figobj is not None:
                        if figobj.isSelected():
                            self.add_selection(self._pevent.artist)
                        else:
                            self.unselect(self._pevent.artist)

                td = self._pevent.artist.figobj
                if td is not None:
                    ifigure.events.SendSelectionEvent(td, self, self.selection)
                if len(self.selection) == 0:
                    self.toolbar.ptype = 'pmode'
                else:
                    # axes is picked. so that isec may need to be changed
                    if self.axes_selection() is not None:
                        if self.axes_selection().figobj._generic_axes:
                            self._isec = self._figure.figobj.get_iaxes(
                                self.axes_selection().figobj)
                            self.hold_once(True)

                if drag_happend:
                    self.draw_later()  # no draw until next idle
                else:
                    self.refresh_hl()
            else:
                if double_click:
                    pass
                elif not drag_happend:
                    if len(self.selection):
                        if (any([s().figobj.isCompound() for s in self.selection
                                 if s() is not None and
                                 s().figobj is not None])
                                and event.guiEvent_memory.ShiftDown()):
                            #
                            pass
                        else:
                            self.unselect_all()
                            self.refresh_hl()
#                  self.draw_later()
                    axes = self.axes_selection()
                    if axes is not None:
                        ifigure.events.SendSelectionEvent(
                            axes.figobj, self, self.selection)
                        self._isec = self._figure.figobj.get_iaxes(axes.figobj)
                        self.hold_once(True)
                    else:
                        # this is when nothing is selected
                        if (self.axes_selection() is None and
                                len(self.selection) == 0):
                            ifigure.events.SendSelectionEvent(
                                self._figure.figobj, self, self.selection)
                    if len(self.selection) == 0:
                        self.toolbar.ptype = 'pmode'
                else:
                    if self.draghandler in self.draghandlers[1:11]:
                        axes = self.axes_selection()
                        if axes is not None:
                            ifigure.events.SendSelectionEvent(
                                axes.figobj, self, self.selection)
                        if len(self.selection) == 0:
                            self.draw_later()  # no draw until next idle
                    elif self.draghandler is self.draghandlers[11]:
                        self.handle_dragselection()
                        # no draw until next idl e
                        self.draw_later(refresh_hl=False)
                    else:
                        alist = self.draghandler.get_artist()
                        self.unselect_all()
                        assert len(alist) > 0, "nothing was draggded?"
                        for a in alist:
                            self.add_selection(a)
                            td = a.figobj
                        ifigure.events.SendSelectionEvent(
                            td, self, self.selection)
                        self.draw_later()  # no draw until next idle
                    if len(self.selection) == 0:
                        self.toolbar.ptype = 'pmode'

        self._picked = False
        self._pevent = None
        if double_click:
            #          print 'double click', self.selection
            self._clean_selection()

            if self._mpl_artist_click is not None:
                if isinstance(
                        self._mpl_artist_click[0](), matplotlib.text.Text):
                    # print 'calling handle_double_click_mpltext'
                    self.handle_double_click_mpltext(event)
            elif (len(self.selection) == 1 and
                  isinstance(self.selection[0]().figobj, FigText)):
                # 'text double click'
                self.handle_double_click_text(event)
            elif(len(self.selection) == 1 and
                 isinstance(self.selection[0]().figobj, FigLegend)):
                self.selection[0]().figobj.double_click_on_canvas(event, self)
            else:
                self.handle_double_click_ax(event)
#      cpicker.activate()
        self.draghandler.set_artist(None)
        ifigure.events.SendCanvasSelected(self._figure.figobj, w=self)

        if set_pmode:
            wx.CallLater(2, self.set_pmode)

    def on_mouse_wheel(self, event):
        if (self.toolbar.mode != 'zoom' and
            self.toolbar.mode != 'pan' and
                self.toolbar.mode != '3dzoom'):
            return
        axes = self.axes_selection()
        if axes is None:
            return
        if axes.figobj is None:
            return
        if not axes.figobj.get_3d():
            return

        if event['start']:
            self._wheel_start_range = axes.get_w_lims()
            axes._on_move_start()

        elif event['end']:
            # apparently this event is not returned on linux...
            self._wheel_end_range = axes.get_w_lims()
            requests = self.make_range_request_pan(axes.figobj, auto=False)
            #requests = self.expand_requests(requests)
            axes._on_move_done()
            self.send_range_action(requests, '3D zoom')

        else:
            range_data = {}
            range_data[axes] = {}

            # convert event point and axes center
            xdata, ydata = axes.transData.inverted(
            ).transform((event['x'], event['y']))
            x0, y0 = axes.transAxes.transform((0.5, 0.5))
            sxdata, sydata = axes.transData.inverted().transform((x0, y0))

            updown = 'up' if event['direction'] else 'down'
            val = axes.calc_range_change_wheel(
                xdata, ydata, sxdata, sydata, updown)

            axes.set_xlim3d(val[0])
            axes.set_ylim3d(val[1])
            axes.set_zlim3d(val[2])
            axes.figobj.set_bmp_update(False)

            # set scale accumulator for pan_sensitivity
            requests = self.make_range_request_pan(axes.figobj, auto=False)
            action = UndoRedoArtistProperty(axes, 'gl_scale_accum',
                                            axes._gl_scale_accum * val[3])

            self.send_range_action(
                requests, '3D wheel', extra_actions=[action])

    def set_pmode(self):
        self.toolbar.ExitInsertMode()
        self.toolbar.SetPMode()
        self.toolbar.SetPMode()
        # somehow I need to call it twice to set button highlight correctly
        # ...!?!?

    def handle_dragselection(self):
        ax = self.axes_selection()
        if ax is None:
            return

        selected = [
            item().figobj for item in self.selection if item() is not None]
        selected = [f for f in selected if f.isCompound()]
        selected = [
            f for f in selected if len(
                f._artists) > 0 and f._artists[0]._gl_pickable]
        rect = self.draghandler._rect
        shiftdown = self.draghandler._shiftdown
        altdown = self.draghandler._altdown
        controldown = self.draghandler._controldown
        alist = []
        selevent = False

        figobj = [f for f in ax.figobj.walk_tree() if f.isCompound()]
        figobj = [
            f for f in figobj if len(
                f._artists) > 0 and f._artists[0]._gl_pickable]

        selection_idx = []
        #print("figobj", figobj, selected)
        if len(selected) == 0 and len(figobj) == 0:
            return
        # elif len(selected) == 0 and len(figobj) > 1:
        #    for f in figobj:
        #       selevent = True
        #       hit, a, all_covered, selected_idx = f.rect_contains(rect)
        #       if hit and all_covered:
        #            alist.append(a)
        #       td = f
        else:
            if len(selected) == 0:
                selected = figobj
                selevent = True
            # for f in selected:
            for f in figobj:
                hit, a, all_covered, selected_idx = f.rect_contains(
                    rect, check_selected_all_covered=altdown)
                #print(hit, a, all_covered, selected_idx)
                if hit:
                    alist.append(a)
                    if shiftdown:
                        f.addSelectedIndex(selected_idx)
                    else:
                        f.setSelectedIndex(selected_idx)
                    selection_idx.append((f, f.getSelectedIndex()))
                    td = f
                else:
                    f.setSelectedIndex([])
                    selected_idx = []
                    selevent = True
                    td = f
        event_sent = False
        if selevent:
            self.unselect_all()
            # unselect_all erase the component selection. so put it back
            for f, idx in selection_idx:
                f.setSelectedIndex(idx)
            for a in alist:
                self.add_selection(a)
                td = a.figobj
            if len(alist) > 0:
                ifigure.events.SendSelectionEvent(td, self, self.selection)
                event_sent = True
        if not event_sent:
            ifigure.events.SendDragSelectionEvent(td, self,
                                                  self.selection,
                                                  selected_index=selected_idx)

    def handle_double_click_mpltext(self, event):
        target_artist = self._mpl_artist_click[0]
        current_txt = target_artist().get_text()
        y = abs(event.y - self.canvas.GetClientSize()[1])

        def finish_text_edit(
                x,
                y,
                txt,
                target_artist=target_artist,
                obj=self,
                figobj=self._mpl_artist_click[1]().figobj):
            self = obj
            from ifigure.widgets.undo_redo_history import UndoRedoAxesArtistProperty
            a1 = UndoRedoAxesArtistProperty(target_artist(),
                                            'text', txt, figobj=figobj)
            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry([a1])

        box = target_artist().get_window_extent().get_points()
        self.ask_text_input(box[0][0] + 5, y,
                            value=current_txt, callback=finish_text_edit)
        self._mpl_artist_click = None

    def handle_double_click_text(self, event):
        target_artist = self.selection[0]
        current_txt = target_artist().get_text()
        y = abs(event.y - self.canvas.GetClientSize()[1])

        def finish_text_edit(x, y, txt, target_artist=target_artist, obj=self):
            self = obj
            a1 = UndoRedoArtistProperty(target_artist(),
                                        'text', txt)
            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry([a1])
        box = target_artist().get_window_extent().get_points()
        self.ask_text_input(box[0][0] + 5, y,
                            value=current_txt, callback=finish_text_edit)

    def handle_double_click_ax(self, event):
        ax = self.axes_selection()
        if ax is not None:
            if hasattr(ax.figobj, 'hndl_dclick'):
                ax.figobj.hndl_dclick(self)
            else:
                if self.toolbar.ptype != 'pmode':
                    return

                requests = self.make_xyauto_request(ax.figobj, 'x')
                requests = self.make_xyauto_request(
                    ax.figobj, 'y', requests=requests)

                if ax.figobj.get_3d():
                    requests = self.make_xyauto_request(
                        ax.figobj, 'z', requests=requests)
                    ax._gl_scale = 1.0
                    ax._gl_scale_accum = 1.0

                requests[ax.figobj] = ax.figobj.compute_new_range(
                    request=requests[ax.figobj])

                if ax.figobj.get_3d():
                    if ax.figobj.getp("aspect") == 'equal':
                        xlim = requests[ax.figobj][0][1][2]
                        ylim = requests[ax.figobj][1][1][2]
                        zlim = requests[ax.figobj][2][1][2]
                        dx = abs(xlim[1] - xlim[0])
                        dy = abs(ylim[1] - ylim[0])
                        dz = abs(zlim[1] - zlim[0])
                        dd = max((dx, dy, dz))
                        xlim = (
                            (xlim[1] + xlim[0] - dd) / 2,
                            (xlim[1] + xlim[0] + dd) / 2)
                        ylim = (
                            (ylim[1] + ylim[0] - dd) / 2,
                            (ylim[1] + ylim[0] + dd) / 2)
                        zlim = (
                            (zlim[1] + zlim[0] - dd) / 2,
                            (zlim[1] + zlim[0] + dd) / 2)
                        requests[ax.figobj][0][1][2] = xlim
                        requests[ax.figobj][1][1][2] = ylim
                        requests[ax.figobj][2][1][2] = zlim
                        requests[ax.figobj][0][1][1] = False
                        requests[ax.figobj][1][1][1] = False
                        requests[ax.figobj][2][1][1] = False
                requests = self.expand_requests(requests)
                self.send_range_action(requests, 'range')

    def refresh_hl_fast(self, alist=None):
        self.draw_artist(alist=alist)

    def refresh_hl(self, alist=None):
        #       import traceback
        #       traceback.print_stack()
        if self.canvas is None:
            return
        if alist is None:
            alist = []
        if turn_on_gl:
            checklist = []
            axes_gl = []
            for item in self.selection:
                if item() is None:
                    continue
                if item().axes is not None:
                    if hasattr(item().axes, '_gl_mask_artist'):
                        if not item().axes in checklist:
                            hls = item().axes.make_gl_hl_artist()
                            alist.extend(hls)
                            checklist.append(item().axes)
                            axes_gl.append(item().axes)
            del checklist

        for item in self.selection:
            if item() is None:
                continue
            figobj = item().figobj
            if figobj is not None:
                figobj.highlight_artist(False, artist=[item()])
                figobj.highlight_artist(True, artist=[item()])

        if turn_on_gl and not self._skip_blur_hl:
            for a in axes_gl:
                a.blur_gl_hl_mask()

        from numpy import inf
        hl_range = [inf, -inf, inf, -inf]
        for item in self.selection:
            if item() is None:
                continue
            alist = alist + item().figobj_hl
#           if (self.toolbar.ptype == 'amode' and
#               len(self.selection)> 1):
            if len(self.selection) > 1:
                for a in item().figobj_hl:
                    #box = a.get_window_extent(a.figure._cachedRenderer)
                    box = a.get_window_extent(a.figure.canvas.get_renderer())
                    hl_range = [min([box.xmin, hl_range[0]]),
                                max([box.xmax, hl_range[1]]),
                                min([box.ymin, hl_range[2]]),
                                max([box.ymax, hl_range[3]])]
        hl = None
        if hl_range[0] != inf:
            x = [
                hl_range[0],
                hl_range[0],
                hl_range[1],
                hl_range[1],
                hl_range[0]]
            y = [
                hl_range[3],
                hl_range[2],
                hl_range[2],
                hl_range[3],
                hl_range[3]]
            hl = Line2D(x, y, marker='o',
                        color='k', linestyle='None',
                        markerfacecolor='b',
                        figure=self._figure)
            self._figure.lines.extend([hl])
            alist.append(hl)
        self._a_mode_scale_anchor = hl_range

#           item().figobj.write2shell(alist, 'alist')
        if turn_on_gl:
            self.canvas.disable_alpha_blend()
        self.draw_artist(alist=alist)
        if turn_on_gl:
            self.canvas.enable_alpha_blend()
        for item in self.selection:
            if item() is None:
                continue
            figobj = item().figobj
            if figobj is not None:
                figobj.highlight_artist(False, artist=[item()])
        if turn_on_gl:
            for item in self.selection:
                if item() is None:
                    continue
                if item().axes is not None:
                    if hasattr(item().axes, '_gl_mask_artist'):
                        item().axes.del_gl_hl_artist()
        if hl is not None:
            self._figure.lines.remove(hl)
        # refresh  txt box
        if self._txt_box is not None:
            self._txt_box.Refresh()

    def onDrawRequest(self, evt):
        if (self._last_update < evt.time - evt.delay):
            #       if (self._last_update < evt.time):
            #           self._nodraw = False
            dprint2('drawing canvas')
            if evt.all:
                self.draw_all()
            else:
                self.draw(refresh_hl=evt.refresh_hl)
#           else:
#               print 'resending request'
#               wx.CallLater(300, self.draw_later)
        else:
            #           pass
            dprint2('skipping draw since screen is already updated')

    def onDraw(self, evt):
        dprint2('draw_event')
        if self._show_cursor:
            self.draw_cursor()
        elif self._layout_mode:
            self.layout_editor.draw_all()
        else:
            self.refresh_hl()

    def draw_later(self, all=False, delay=0.0, refresh_hl=False):
        from ifigure.events import SendCanvasDrawRequest
        SendCanvasDrawRequest(self, all=all, delay=delay,
                              refresh_hl=refresh_hl)
#       self._nodraw = True
#       self._draw_request = True

    def draw_artist(self, alist=None):
        self.canvas.draw_artist(alist=alist)

    def draw(self, refresh_hl=False):
        #       if not self._nodraw:
        if self._figure is None:
            return

        t = time.time()
        self._last_draw_time = t

        self._figure.figobj.update_artist()
        self._drawing = True
#          self.canvas.draw(nogui_reprint = True)
        #import traceback
        # traceback.print_stack()

        try:
            self.canvas.draw(nogui_reprint=False)
        except BaseException:
            import traceback
            traceback.print_exc()
            dprint1('canvas draw failed')

        self._last_update = time.time()
        self._drawing = False

        dprint2('drawing time ' + str(time.time() - t))
        if refresh_hl:
            self.refresh_hl()
        if self._layout_mode:
            self.layout_editor.draw_all()
#       else:
#          self._draw_request = True

    def draw_all(self):
        dprint2('draw all')
        self.canvas.draw_all()

    def draw_cursor(self):
        lines = []
        collections = []
        images = []
        ax = None
        for figobj in self._cursor_owner:
            if figobj() is None:
                continue

            cursors = figobj().valid_cursor()
            for a in cursors:
                if isinstance(a, Line2D):
                    lines.append(a)
                elif isinstance(a, matplotlib.collections.LineCollection):
                    ax = figobj()._artists[0]
                    collections.append(a)
                elif isinstance(a, matplotlib.image.AxesImage):
                    ax = figobj()._artists[0]
                    images.append(a)
                else:
                    print(type(a))
        self._figure.lines += lines
        if ax is not None:
            ax.collections += collections
            ax.images += images
        self.refresh_hl(lines + collections + images)
        for l in lines:
            self._figure.lines.remove(l)
        if ax is not None:
            for l in collections:
                ax.collections.remove(l)
            for l in images:
                ax.images.remove(l)

    def generate_cursors(self, evt):
        if evt.guiEvent.LeftIsDown():
            idx = 0
        else:
            idx = 1

        if self._cursor_target is not None:
            target = self._cursor_target()
        else:
            target = None

        self._cursor_owner = []
        f_page = self._figure.figobj

        if (self._cursor_mode == 0 or
            self._cursor_mode == 1 or
                self._cursor_mode == 2):
            for f_axes in f_page.walk_axes():
                f_axes.generate_cursor(evt, idx, target=target)
                self._cursor_owner.append((weakref.ref(f_axes)))
        elif (self._cursor_mode == 3 or
              self._cursor_mode == 4):
            for f_axes in f_page.walk_axes():
                f_axes.erase_cursor()
                rect, dummy, dummy = f_axes.calc_rect()
                nx, ny = self.px2norm(evt.x, evt.y)
                if geom_util.check_inside(rect, nx, ny):
                    self._cursor_owner.append((weakref.ref(f_axes)))
                    f_axes.reset_cursor_range(evt, idx)
        elif (self._cursor_mode == 5):
            for f_axes in f_page.walk_axes():
                rect, dummy, dummy = f_axes.calc_rect()
                nx, ny = self.px2norm(evt.x, evt.y)
                if geom_util.check_inside(rect, nx, ny):
                    f_axes.generate_cursor(evt, idx)
                    self._cursor_owner.append((weakref.ref(f_axes)))
                    f_axes.reset_cursor_range(evt, idx)
                else:
                    f_axes.erase_cursor()
        else:
            print('Unknown cursor mode')

        return self._cursor_owner

    def copy_selection(self, obj=None):
        '''
        copy selected object to scratch file
        obj is either FigAxes or FigPage
        '''
        self._clean_selection()
        if (obj is None and
                len(self.selection) == 0):
            return

        mode = 'figobj'
        cmap_hint = None
        if obj is not None:
            figobj = obj
            if isinstance(figobj[0], FigPage):
                mode = 'page'
            if isinstance(figobj[0], FigAxes):
                mode = 'axes'
        else:
            # check if all pageobj
            mode = 'pageobj'
            for s in self.selection:
                if not s().figobj.isPageObj():
                    mode = 'figobj'
            if mode == 'figobj':
                mode = 'axesobj'
                for s in self.selection:
                    if s().figobj.isPageObj():
                        mode = 'figobj'
            ####### fall back ########
            if mode == 'figobj':
                figobj = [self.selection[0]().figobj]
            else:
                figobj = [s().figobj for s in self.selection]

        if len(figobj) == 1:
            if isinstance(figobj[0], CUser):
                ca = figobj[0].get_caxisparam()
                cmap_hint = ca.get_cmap()

        # figobj : list of figobj
        data = {"mode": mode, "num": len(figobj), "dirs": []}
        if cmap_hint is not None:
            data["cmap_hint"] = cmap_hint

        from ifigure.ifigure_config import canvas_scratch as cs
        from ifigure.ifigure_config import canvas_scratch_page as csp
        from ifigure.ifigure_config import canvas_scratch_axes as csa
        import shutil
        if mode == 'page':
            dest = csp
        elif mode == 'axes':
            dest = csa
        else:
            dest = cs
        for item in os.listdir(dest):
            path = os.path.join(dest, item)
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)

        for k, item in enumerate(figobj):
            filename = os.path.join(dest, 'figobj_' + str(k))
            flag, dirname = item.save_subtree(filename, compress=False,
                                              maketar=False)
            data["dirs"].append(dirname)

        fid = open(os.path.join(dest, 'header'), 'wb')
        pickle.dump(data, fid)
        fid.close()

    def paste_selection(self, cs=None, return_history=False,
                        return_header=False):
        import ifigure.widgets.dialog as dialog
        f_page = self._figure.figobj
        f_book = f_page.get_parent()
        i_page = f_book.i_page(f_page)

        if self.axes_selection() is None:
            if f_page.num_axes() == 0:
                f_axes = None
            else:
                f_axes = f_page.get_axes(0)
                i_axes = f_page.i_axes(f_axes)
        else:
            axes = self.axes_selection()
            f_axes = axes.figobj
            i_axes = f_page.i_axes(f_axes)
            # can be none if f_axes is inset

        if cs is None:
            from ifigure.ifigure_config import canvas_scratch as cs

        fid = open(os.path.join(cs, 'header'), 'rb')
        header = pickle.load(fid)
        fid.close()
        # dprint1(str(header))
        if return_header:
            return header

        p = None
        if (header["mode"] == 'obj' or
                header["mode"] == 'axesobj'):
            p = f_axes
        elif header["mode"] == 'axes':
            p = f_page
        elif header["mode"] == 'page':
            p = f_book
        elif header["mode"] == 'pageobj':
            p = f_page

        if p is None:
            print("error in pasting obj")
            fid.close()
            if return_history:
                return None, []
            else:
                return

        objs = []
        actions = []
        import shutil
        for tmpdir in header['dirs']:
            shutil.copytree(tmpdir, tmpdir + '_bk')
            obj = p.load_subtree(tmpdir, compress=False,
                                 usetar=False)
            shutil.move(tmpdir + '_bk', tmpdir)
#           obj, ol, nl=p.paste_tree(fid)
            dprint2('mode: ', header["mode"])

            if header["mode"] == 'page':
                idx = p.i_child(obj)
                p.move_child(idx, i_page + 1)
                objs.append(obj)
            elif header["mode"] == 'axes':
                if f_axes is not None:
                    if obj.num_child() == 0:
                        ret = dialog.message(
                            parent=self,
                            message='Axes does not have any plot',
                            title="Can not paste",
                            style=0)
                        obj.destroy()
                        if return_history:
                            return None, []
                        else:
                            return
                    ret = dialog.message(
                        parent=self,
                        message='Do you want to replace section ?',
                        title="Paste Section",
                        style=4)
                    if ret == 'yes':
                        self.unselect_all()
                        for name, child in f_axes.get_children():
                            child.destroy()
                        # copying axes setting, here
                        # however, zorder is kept.
                        zorder = f_axes.getp('zorder')
                        data = obj.save_data2({})
                        del data['FigAxes'][1]['area']
                        # f_axes.load_data2(data)
                        if f_axes.hasp('zorder'):
                            del_z = zorder - f_axes.getp('zorder')
                        else:
                            del_z = 0.0
                        data['FigAxes'][1]['zoder'] = zorder
                        # I can not reset artist simply, since I need to use
                        # loaded_property
                        f_axes.reset_artist(load_data=data)

                        # moving child (at this _?axis are set and therfore
                        # move should take care of handling axis_param._member
                        # here speical care is needed to keep zorder
                        for name, child in obj.get_children():
                            if isinstance(child, FigAxes):
                                continue
                            child.move(f_axes, keep_zorder=True)
                            child.set_zorder(child.getp('zorder') + del_z)
                            objs.append(child)
                        obj.destroy()
                    else:
                        for name, child in obj.get_children():
                            if isinstance(child, FigAxes):
                                continue
                            child.move(f_axes)
                            objs.append(child)
                        obj.destroy()
                else:
                    objs.append(obj)
            elif header["mode"] == 'axesobj':
                # cleaning...;D
                self.clean_selection()
                for s in self.selection:
                    if s().figobj.isPageObj():
                        self.unselect(s())
                    if not p.isdescendant(s().figobj):
                        self.unselect(s())
                    if s().figobj is p:
                        self.unselect(s())
                self.unselect_all()
#               if len(self.selection) > 0:
#                   actions.append(UndoRedoAddRemoveArtists(artists = self.selection,
#                                         mode = 1))
#               self.del_selection()
                objs.append(obj)

            elif header["mode"] == 'pageobj':
                self.clean_selection()
                self.unselect_all()

                for s in self.selection:
                    if not s().figobj.isPageObj():
                        self.unselect(s())
                if len(self.selection) != 0:
                    for s in self.selection:
                        if s() is None:
                            continue
                        if isinstance(s().figobj, FigAxes):
                            break
                    else:
                        #                     actions.append(UndoRedoAddRemoveArtists(artists = self.selection,
                        #                                         mode = 1))
                        self.del_selection()
                objs.append(obj)
            else:
                objs.append(obj)

        for obj in objs:
            if (header["mode"] == 'axesobj'):
                if not len(obj.get_figaxes()._artists) > obj._container_idx:
                    obj.set_container_idx(0)

            obj.realize()
            if (header["mode"] == 'axesobj' or
                    header["mode"] == 'pageobj'):
                for a in obj._artists:
                    self.add_selection(a)
                obj.set_zorder_front()
        ifigure.events.SendSelectionEvent(p, self, self.selection)

        # registor paste action to history
        check = len(objs)
        objs = [x for x in objs if len(x._artists) > 0]
        if len(objs) != check:
            print("Some objects did not generate aritsts.")
        artists = [weakref.ref(obj._artists[0]) for obj in objs]
        ret = [obj.get_full_path() for obj in objs]
        if header["mode"] == 'page':
            return ret
        if len(artists) == 0:
            if return_history:
                return None, None, None
            else:
                return ret
        actions.append(UndoRedoAddRemoveArtists(artists=artists,
                                                mode=0))
        f = []
        if p is not None and header["mode"] == 'axesobj':
            actions = actions + p.adjust_axes_range(get_action=True)
            f.append((weakref.ref(p), 'call_handle_axes_change', ('x',)))
            # mappable may have cmap_hint
            # chane cmap if new obj is the only member of caxis
            if 'cmap_hint' in header:
                cax = objs[0].get_caxisparam()
                if cax.num_member() == 1:
                    action = UndoRedoFigobjMethod(objs[0]._artists[0].axes,
                                                  'cmap3',
                                                  header['cmap_hint'])
                    action.set_extrainfo(cax.name)
                    actions = actions + [action]
        if return_history:
            return ret, actions, f
        else:
            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(actions,
                                                           finish_action=f,
                                                           menu_name='paste')
        return ret

#       f_axes.realize()

    def del_selection(self, menu_name='delete'):
        if len(self.selection) == 0:
            return
        h = UndoRedoAddRemoveArtists(artists=self.selection,
                                     mode=1)
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(
            [h], menu_name=menu_name)
        self.selection = []
        return

    def clean_selection(self):
        self.selection = [s for s in self.selection if s() is not None]
        self.selection = [s for s in self.selection if s().figobj is not None]

    def cut_selection(self):
        if len(self.selection) == 0:
            return
        self.copy_selection()
        self.del_selection(menu_name='cut')

    def add_selection(self, ain):
        for a in self.selection:
            if a() is ain:
                return
        ain.figobj.canvas_selected()
        self.selection = [weakref.ref(ain)] + self.selection
#       ain.figobj.highlight_artist(True, artist=[ain])

    def unselect(self, ain):
        self._clean_selection()
        for a in self.selection:
            if a() == ain:
                if a().figobj is not None:
                    a().figobj.highlight_artist(False, artist=[ain])
                    a().figobj.canvas_unselected()
                if hasattr(a(), 'is_gl'):
                    a().unselect_gl_artist()

        self.selection = [x for x in self.selection if x() != ain]

    def unselect_all(self):
        self._clean_selection()
        for a in self.selection:
            if a() is None:
                continue
            figobj = a().figobj
            if figobj is not None:
                figobj.canvas_unselected()
                figobj.highlight_artist(False)
            if hasattr(a(), 'is_gl'):
                a().unselect_gl_artist()
        self.selection = []

#   def set_axesselection(self, fig_axes):
#       self.axes_selection=weakref.ref(fig_axes._artists[0])
#       self.unselect_all()
#       self.draw()

    def del_area(self, iarea):
        figure = self._figure
        f_page = self._figure.figobj

        fa = f_page.get_axes()
        f_page.del_axes(fa[iarea][1])

    def set_area(self, areas):
        figure = self._figure
        f_page = self._figure.figobj
        f_page.set_area(areas)

#       f_page.realize()
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.update_widget()

    def mpl_setp(self, message, axes=False):
        kwarg = {message["property"]: message["value"]}
        if axes is True:
            axes = self.axes_selection()
            mpl_setp(axes, **kwarg)
        else:
            for item in self.selection:
                mpl_setp(item(), **kwarg)

        self.draw()

    def onTD_RangeChanged(self, evt):
        pass
#      figobj=evt.GetTreeDict()
#      figobj.handle_axes_change(evt)
#      print 'range change in', figobj.get_full_path()

#      for name, child in figobj.get_children():
#          child.handle_axes_change(evt)

    def onTD_Replace(self, evt):
        i = 0
        done = False
        for x in self.selection:
            if x() == evt.a1:
                self.selection[i] = weakref.ref(evt.a2)
                done = True
#              self.refresh_hl_idle()
                break
            i = i + 1

        # if replace does not match
        # do replacement based on evt.GetTreeDict()
        if not done:
            valid_selection = [x for x in self.selection if (
                               x() is not None and
                               x().figobj is not None)]
            tmp = [x for x in self.selection if (
                x() is not None and
                x().figobj is not evt.GetTreeDict() and
                x().figobj is not None)]
            for x in valid_selection:
                if x().figobj is evt.GetTreeDict():
                    tmp.append(weakref.ref(evt.a2))
            self.selection = []
            #for x in self.selection: self.selection.remove(x)
            for x in tmp:
                self.selection.append(x)

        if self.axes_selection() == evt.a1:
            self.axes_selection = weakref.ref(evt.a2)

    def onTD_Selection(self, evt):
        # when td was selected in other widget...
        figobj = evt.GetTreeDict()

        if not self._figure.figobj.is_descendant(figobj):
            if len(self.selection) == 0:
                return

        if len(evt.selections) != 0:
            if evt.multi_figobj is not None:
                alist = sum([x._artists for x in evt.multi_figobj], [])
            else:
                alist = figobj._artists

            evt.selections = [
                weakref.ref(
                    x().figobj._artists[0]) for x in evt.selections if x() in alist]

        alist = [x() for x in evt.selections]

        mode = 0
        if (isinstance(figobj, FigObj) and
            not isinstance(figobj, FigPage) and
            not isinstance(figobj, FigBook) and
                not isinstance(figobj, FigAxes)):
            mode = 1
        if isinstance(figobj, FigAxes):
            if isinstance(figobj.get_parent(), FigPage):
                mode = 2
            else:
                mode = 3

        if mode == 0:
            self.unselect_all()
        if mode == 1 or mode == 3:
            flag = True
            for item in self.selection:
                if len(evt.selections) == 0:
                    continue
                if not item() in alist:
                    self.unselect(item())
                else:
                    flag = False
            if flag:
                self.selection = evt.selections

        if mode == 2:
            self.unselect_all()
            self.axes_selection = weakref.ref(figobj._artists[0])
        if mode == 3:
            self.axes_selection = weakref.ref(figobj._artists[0])

        self.draw_later(refresh_hl=True)

    def px2norm(self, x, y):
        # conversion from screen pixel to normal
        scr_size = self.canvas.get_width_height()
        return [float(x) / float(scr_size[0]), float(y) / float(scr_size[1])]

    def motion_event(self, evt):
        if evt.inaxes is None:
            return
        if evt.inaxes.figobj.get_3d():
            return
        self.update_status_str(evt)

    def update_status_str(self, evt):
        p = self.GetTopLevelParent()
        if self.toolbar.mode == 'cursor':
            if len(self._cursor_owner) > 0:
                if self._cursor_owner[0]() is not None:
                    p.sb.show_cursor_string(self._cursor_owner[0]())
                    return
        if (evt.xdata is not None and
                evt.ydata is not None):
            p.sb.set_xy_string(evt.xdata, evt.ydata)

    def _set_xyauto(self, name, noevent=False):
        if self.axes_selection is None:
            return
        if self.axes_selection() is None:
            return

        axes = self.axes_selection()
        ax = axes.figobj

        requests = {}
        for x in name:
            requests = self.make_xyauto_request(ax, x, requests=requests)
        requests[ax] = ax.compute_new_range(request=requests[ax])
        requests = self.expand_requests(requests)
        self.send_range_action(requests, 'range')

        ifigure.events.SendSelectionEvent(ax, self, self.selection)

    def set_xyauto(self):
        self._set_xyauto('xy')

    def set_yauto(self):
        self._set_xyauto('y')

    def set_xauto(self):
        self._set_xyauto('x')

    def set_zauto(self):
        self._set_xyauto('z')

    def set_cauto(self):
        self._set_xyauto('c')

    def _set_samexy(self, name, auto=False, mode=1):
        window = self.GetTopLevelParent()
        if (self._figure.figobj.num_axes() == 1 and
                not window._use_samerange):
            return
        if self.axes_selection is None:
            return
        if self.axes_selection() is None:
            return

        axes = self.axes_selection()
        ax = axes.figobj

        requests = {}
        for x in name:
            requests = self.make_samexy_request(ax, x, auto,
                                                mode=mode,
                                                requests=requests)
#          for key in requests2:
#             if key in requests:
#                requests[key].extend(requests2[key])
#             else:
#                requests[key] = requests2[key]
        requests = self.expand_requests(requests)
        self.send_range_action(requests, 'range')
        ifigure.events.SendSelectionEvent(ax, self, self.selection)

    def set_sameview(self):
        window = self.GetTopLevelParent()
        if self._figure.figobj.num_axes() == 1:
            return
        if self.axes_selection is None:
            return
        if self.axes_selection() is None:
            return

        axes = self.axes_selection()
        f_ax_org = axes.figobj
        new_value = f_ax_org.get_axes3d_viewparam(axes)
        f_page = f_ax_org.get_parent()

        actions = []
        for f_ax in f_page.walk_axes():
            if f_ax is f_ax_org:
                continue
            if not f_ax.get_3d():
                continue
            aa = f_ax._artists[0]
            old_value = f_ax.get_axes3d_viewparam(aa)
            actions.append(UndoRedoFigobjMethod(aa,
                                                'axes3d_viewparam',
                                                new_value,
                                                old_value=old_value, figobj=f_ax))

        if len(actions) == 0:
            return
        window = self.GetTopLevelParent()

        GlobalHistory().get_history(window).make_entry(actions,
                                                       menu_name='3D view(all)')
        ifigure.events.SendSelectionEvent(f_ax_org, self, self.selection)

    def set_samex(self):
        self._set_samexy('x', mode=1)

    def set_samey(self):
        self._set_samexy('y', mode=1)

    def set_samexy(self):
        self._set_samexy('xy', mode=1)

    def set_samexyz(self):
        self._set_samexy('xyz', mode=1)

    def set_xauto_all(self):
        self._set_samexy('x', auto=True, mode=2)

    def set_yauto_all(self, auto=False):
        self._set_samexy('y', auto=True, mode=2)

    def set_samec(self):
        self._set_samexy('c', mode=1)

    def set_samex_autoy(self, *args, **kargs):
        window = self.GetTopLevelParent()
        if (self._figure.figobj.num_axes() == 1 and
                not window._use_samerange):
            return
        if self.axes_selection is None:
            return
        if self.axes_selection() is None:
            return

        axes = self.axes_selection()
        ax = axes.figobj

        requests = self.make_samex_autoy_request(ax)
        requests = self.expand_requests(requests)
        self.send_range_action(requests, 'range')

    def set_xyauto_all(self):
        window = self.GetTopLevelParent()
        if (self._figure.figobj.num_axes() == 1 and
                not window._use_samerange):
            return
        if self.axes_selection is None:
            return
        if self.axes_selection() is None:
            return

        axes = self.axes_selection()
        ax = axes.figobj
        requests = self.make_autox_autoy_request(ax)
        requests = self.expand_requests(requests)
        self.send_range_action(requests, 'range')

    def mail_pic(self):
        from ifigure.ifigure_config import rcdir
        import datetime
        namebase = 'figure' + str(os.getpid())
        txt = datetime.datetime.now().strftime("%m_%d_%H_%M_%S")
        namebase = namebase + '_' + txt

        data = {'eps': (0, namebase + '.eps'),
                'pdf': (1, namebase + '.pdf'),
                'svg': (2, namebase + '.svg'),
                'png': (3, namebase + '.png'),
                'jpeg': (4, namebase + '.jpeg'),
                'gifanim': (5, namebase + '.gif'),
                'pnganim': (6, namebase + '.png'),
                'pdfall': (7, namebase + '.pdf'), }

        fname = os.path.join(rcdir, data[self._mailpic_format][1])
        self.save_pic(ret=fname, wc=data[self._mailpic_format][0])

        po = wx.GetApp().TopWindow.po
        try:
            po.send_file(fname, parent=self.GetTopLevelParent())
        except BaseException:
            import traceback
            traceback.print_exc()
            dprint1("send_file failed")
        os.remove(fname)

    def save_pic(self, ret='', wc=None):
        def call_convert_to_tex_style_text(value):
            for obj in self._figure.figobj.walk_tree():
                if hasattr(obj, 'convert_to_tex_style_text'):
                    obj.convert_to_tex_style_text(value)

        import ifigure.widgets.dialog as dialog
        if wc is None:
            wildcard1 = "Encapsulated Post Script(eps)|*.eps|Portable Document Format(pdf)|*.pdf|Scalable Vector Graphics (svg)|*.svg|Portable Network Graphics(png)|*.png|Joint Photographic Experts Group (jpeg)|*.jpeg"
            wildcard2 = "Animated - Graphic Interchange Format (gif)|*.gif"
            wildcard3 = "Animated - PNG (png)|*.png"
            wildcard4 = "Multipage PDF|*.pdf"
            if self.GetTopLevelParent().num_page() > 1:
                wildcard = wildcard1 + '|' + wildcard2 + '|' + wildcard3 + '|' + wildcard4
            else:
                wildcard = wildcard1
            ret, wc = dialog.write(parent=None, defaultfile='image',
                                   message='Enter figure file name',
                                   wildcard=wildcard, return_filterindex=True)

        if ret == '':
            return

        org_rc = (matplotlib.rcParams['text.usetex'],
                  matplotlib.rcParams['ps.usedistiller'],
                  matplotlib.rcParams['font.family'])
        if wx.GetApp().TopWindow.aconfig.setting['keep_text_as_text']:
            matplotlib.rcParams['text.usetex'] = True
            matplotlib.rcParams['ps.usedistiller'] = 'xpdf'
            matplotlib.rcParams['font.family'] = [u'serif']
            call_convert_to_tex_style_text(True)
#             matplotlib.rcParams['ps.fonttype'] = 42

        if wc == 0:
            if ret[-4:] != '.eps':
                ret = ret + '.eps'
        elif wc == 1:
            if ret[-4:] != '.pdf':
                ret = ret + '.pdf'
        elif wc == 2:
            if ret[-4:] != '.svg':
                ret = ret + '.svg'
        elif wc == 3:
            if ret[-4:] != '.png':
                ret = ret + '.png'
        elif wc == 4:
            if ret[-5:] != '.jpeg':
                ret = ret + '.jpeg'
        elif wc == 5:
            if ret[-4:] != '.gif':
                ret = ret + '.gif'
            fname = '.'.join(ret.split('.')[:-1])
            try:
                self.GetTopLevelParent().save_animgif(filename=fname + '.gif')
            except BaseException:
                import traceback
                print(traceback.format_exc())
            if (matplotlib.rcParams['text.usetex'] and
                    not org_rc[0]):
                call_convert_to_tex_style_text(False)
            matplotlib.rcParams['text.usetex'] = org_rc[0]
            matplotlib.rcParams['ps.usedistiller'] = org_rc[1]
            matplotlib.rcParams['font.family'] = org_rc[2]
            return
        elif wc == 6:
            if ret[-4:] != '.png':
                ret = ret + '.png'
            fname = '.'.join(ret.split('.')[:-1])
            try:
                import apng
            except ImportError:
                dialog.message(
                    parent=self,
                    message='APNG is not found (consider pip install apng)',
                    title='missing module',
                    style=0)
                return
            try:
                self.GetTopLevelParent().save_animpng(filename=fname + '.png')
            except BaseException:
                import traceback
                print(traceback.format_exc())
            if (matplotlib.rcParams['text.usetex'] and
                    not org_rc[0]):
                call_convert_to_tex_style_text(False)
            matplotlib.rcParams['text.usetex'] = org_rc[0]
            matplotlib.rcParams['ps.usedistiller'] = org_rc[1]
            matplotlib.rcParams['font.family'] = org_rc[2]
            return
        elif wc == 7:
            if ret[-4:] != '.pdf':
                ret = ret + '.pdf'
            fname = '.'.join(ret.split('.')[:-1])
            try:
                self.GetTopLevelParent().save_multipdf(filename=fname + '.pdf')
            except BaseException:
                import traceback
                print(traceback.format_exc())
            if (matplotlib.rcParams['text.usetex'] and
                    not org_rc[0]):
                call_convert_to_tex_style_text(False)
            matplotlib.rcParams['text.usetex'] = org_rc[0]
            matplotlib.rcParams['ps.usedistiller'] = org_rc[1]
            matplotlib.rcParams['font.family'] = org_rc[2]
            return

        image_dpi = wx.GetApp().TopWindow.aconfig.setting['image_dpi']

        from ifigure.matplotlib_mod.mpl_utils import call_savefig_method
        try:
            if ret[-4:] == '.png':
                call_savefig_method(self, 'print_png', ret)
            elif ret[-5:] == '.jpeg':
                call_savefig_method(self, 'print_jpeg', ret)
            elif ret[-4:] == '.eps':
                call_savefig_method(self, 'print_eps', ret, dpi=image_dpi)
            elif ret[-4:] == '.pdf':
                call_savefig_method(self, 'print_pdf', ret, dpi=image_dpi)
            elif ret[-4:] == '.svg':
                call_savefig_method(self, 'print_svg', ret)
            else:
                call_savefig_method(self, 'print_pdf',
                                    ret + '.pdf', dpi=image_dpi)
        except BaseException:
            import traceback
            print(traceback.format_exc())

        if (matplotlib.rcParams['text.usetex'] and
                not org_rc[0]):
            call_convert_to_tex_style_text(False)
        matplotlib.rcParams['text.usetex'] = org_rc[0]
        matplotlib.rcParams['ps.usedistiller'] = org_rc[1]
        matplotlib.rcParams['font.family'] = org_rc[2]

    def export_hdf(self):

        from ifigure.widgets.hdf_export_window import HdfExportWindow

        try:
            exist_flag = True
            if wx.GetApp().TopWindow.hdf_export_window is not None:
                wx.GetApp().TopWindow.hdf_export_window.GetSize()
            else:
                exist_flag = False
        except PyDeadObjectError:
            exist_flag = False
        if exist_flag:
            return

        window = self.GetTopLevelParent()
        page = self._figure.figobj
        w = HdfExportWindow(parent=window,
                            page=page)
        self.w = w

    def _clean_selection(self):
        for item in self.selection:
            if item() is None:
                self.selection.remove(item)
                continue
            if item().figobj is None:
                self.selection.remove(item)

    def change_figobj_axes(self, figobj, value, direction):
        if len(self.selection) == 0:
            return
        h = []
        if direction != 'c':
            for a in self.selection:
                h.append(UndoRedoFigobjMethod(a(), 'container_idx', value))
        else:
            for a in self.selection:
                h.append(UndoRedoFigobjMethod(a(), 'caxis_idx', value))
        ax = a().axes
        h.append(UndoRedoFigobjMethod(ax, 'adjustrange', None))

        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h, use_reverse=False)

    def insert_figobj(self, evt):
        if hasattr(self, 'insert_' + self.toolbar.mode):
            m = getattr(self, 'insert_' + self.toolbar.mode)
            m(evt)
        else:
            dprint1('insert "' + self.toolbar.mode + '" not implemented')
        self._picked = False
        self._pevent = None
#       cpicker.activate()
        self.toolbar.ExitInsertMode()
        self._insert_mode = False
        self._insert_st_event = None
        self.draw_later()

    def insert_colorbar(self, evt):
        asel = self.axes_selection
        psel = self.selection

        if asel is None:
            return
        a = asel()
        if a is None:
            return

        artists = [p() for p in psel]
        ax = a.figobj

#       if len(artists) == 0:
        artists = []
        if False in [p.has_cbar() for p in ax._caxis]:
            for k, p in enumerate(ax._caxis):
                if not p.has_cbar():
                    p.show_cbar(ax, offset=-0.1 * k)
                    artists.append(p._cb()._artists[0])
        # registor paste action to history
        if len(artists) == 0:
            return
        artists = [weakref.ref(a) for a in artists]
        actions = [UndoRedoAddRemoveArtists(artists=artists,
                                            mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions,
                                                       menu_name='add cbar')

        self.draw()
        ifigure.events.SendChangedEvent(ax, w=self)

    def insert_legend(self, evt):
        import ifigure.widgets.dialog as dialog
        from ifigure.utils.edit_list import DialogEditList
        from ifigure.interactive import legend

        if self.axes_selection() is None:
            return
        axes = self.axes_selection()
        self._isec = self._figure.figobj.get_iaxes(axes.figobj)
        app = self.GetTopLevelParent()

        list6 = [['', "      Enter Legend Labels       ", 2, None],
                 [None, "('plot1', 'plot2')", 200, None], ]

        if len(axes.figobj._artists) > 1:
            list6.append([None, False, 3, {"text": "Use Second Axes"}])

#       print self.GetTopLevelParent()
        value = DialogEditList(
            list6,
            modal=True,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            tip=None,
            parent=self.GetTopLevelParent())

        if value[0]:
            new_name = str(value[1][1])
            if len(axes.figobj._artists) > 1:
                kargs = {"axes2": value[1][2]}
            else:
                kargs = {}
        else:
            return

        args = eval(new_name)
        try:
            obj = legend(args, **kargs)
        except BaseException:
            print('Failed to create legend')
            import traceback
            print(traceback.format_exc())
            return

        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        actions = [UndoRedoAddRemoveArtists(artists=artists,
                                            mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions,
                                                       menu_name='add legend')

    def insert_eps(self, evt):
        '''
        insert art file (image from *.eps)
        '''
        from ifigure.mto.fig_eps import FigEPS
        parent = self._figure.figobj

        nx, ny = self.px2norm(evt.x, evt.y)
        open_dlg = wx.FileDialog(
            None,
            message="Select art file (.eps) to place",
            wildcard='EPS(*.eps)|*.eps',
            style=wx.FD_OPEN)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            return
        file = open_dlg.GetPath()
        open_dlg.Destroy()

        obj = FigEPS(file, xy=[nx, ny])
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)
        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_line(self, evt, use_fit=False):
        '''
        insert line
        '''
        from ifigure.mto.fig_curve import FigCurve
        parent = self._figure.figobj
        if self.axes_selection() is not None:
            figaxes = self.axes_selection().figobj
        else:
            figaxes = None
        while len(self._line_insert_path) > 2:
            if (abs(self._line_insert_path[-2][1][0] -
                    self._line_insert_path[-1][1][0]) < 3 and
                abs(self._line_insert_path[-2][1][1] -
                    self._line_insert_path[-1][1][1]) < 3):
                self._line_insert_path = self._line_insert_path[:-1]
            else:
                break
        path = self._line_insert_path
        if use_fit:
            x = [x1[1][0] for x1 in self._line_insert_path]
            y = [x1[1][1] for x1 in self._line_insert_path]
            path = cbook.BezierFit(x, y)

        obj = FigCurve(path=path,
                       figaxes1=figaxes)
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)

        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_curve2(self, evt):
        return self.insert_line(evt, use_fit=True)

    def insert_curve(self, evt):
        '''
        insert  curve
        '''
        from ifigure.mto.fig_curve import FigCurve
        path = self.draghandler.pathdata
        self.draghandler.pathdata = []
        if len(path) < 3:
            ifigure.events.SendChangedEvent(self._figure.figobj, self)
            return
        parent = self._figure.figobj

        if self.axes_selection() is not None:
            figaxes = self.axes_selection().figobj
        else:
            figaxes = None
        obj = FigCurve(path=path,
                       figaxes1=figaxes)
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)
        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_arrow(self, evt):
        '''
        insert  arrow
        '''
        from ifigure.mto.fig_arrow import FigArrow
        parent = self._figure.figobj
        if parent is None:
            return
        if (abs(self._insert_st_event.x - evt.x) < 5 and
                abs(self._insert_st_event.y - evt.y) < 5):
            return
        t = parent._artists[0].transFigure
        n1 = np.array([evt.x, evt.y]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        xytext = (n1[0][0], n1[0][1])

        n1 = np.array([self._insert_st_event.x,
                       self._insert_st_event.y]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        xy = (n1[0][0], n1[0][1])

        if self.axes_selection() is not None:
            figaxes = self.axes_selection().figobj
        else:
            figaxes = None
        obj = FigArrow(xy[0], xy[1],
                       xytext[0], xytext[1],
                       #                      figaxes1=figaxes, figaxes2=figaxes,
                       facecolor='k', edgecolor='k')
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)
        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_rect(self, evt):
        '''
        insert  fig_box
        '''
        from ifigure.mto.fig_box import FigBox

        parent = self._figure.figobj
        if parent is None:
            return
        if (abs(self._insert_st_event.x - evt.x) < 5 and
                abs(self._insert_st_event.y - evt.y) < 5):
            return

        dh = self.draghandler
        t = parent._artists[0].transFigure
        n1 = np.array([min(dh._x), min(dh._y)]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        x1, y1 = (n1[0][0], n1[0][1])

        n1 = np.array([max(dh._x),
                       max(dh._y)]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        x2, y2 = (n1[0][0], n1[0][1])

        if self.axes_selection() is not None:
            figaxes = self.axes_selection().figobj
        else:
            figaxes = None

        xy = (min([x1, x2]), min([y1, y2]))
        w = abs(x1 - x2)
        h = abs(y1 - y2)

        obj = FigBox(xy=xy, width=w, height=h,
                     figaxes1=figaxes)
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)
        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_circle(self, evt):
        '''
        insert  fig_circle
        '''
        from ifigure.mto.fig_circle import FigCircle

        parent = self._figure.figobj

        if parent is None:
            return
        if (abs(self._insert_st_event.x - evt.x) < 5 and
                abs(self._insert_st_event.y - evt.y) < 5):
            return

        dh = self.draghandler
        t = parent._artists[0].transFigure
        n1 = np.array([dh._xy[0] - dh._w / 2,
                       dh._xy[1] - dh._h / 2]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        x1, y1 = (n1[0][0], n1[0][1])

        n1 = np.array([dh._xy[0] + dh._w / 2,
                       dh._xy[1] + dh._h / 2]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        x2, y2 = (n1[0][0], n1[0][1])

        if self.axes_selection() is not None:
            figaxes = self.axes_selection().figobj
        else:
            figaxes = None

        xy = ((x2 + x1) / 2, (y1 + y2) / 2)
        w = abs(x1 - x2)
        h = abs(y1 - y2)

#       print 'insert circle', xy, w, h
        obj = FigCircle(xy=xy, width=w, height=h,
                        figaxes1=figaxes)
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)
        # registor paste action to history
        artists = [weakref.ref(obj._artists[0])]
        h = [UndoRedoAddRemoveArtists(artists=artists,
                                      mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def insert_annotate(self, evt):
        '''
        insert annotation arrow
        '''
        from ifigure.mto.fig_annotate import FigAnnotate
        parent = self.find_ax_4_insert(evt)
        if parent is None:
            return

        t = parent._artists[0].transAxes
        n1 = np.array([evt.x, evt.y]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        xytext = (n1[0][0], n1[0][1])

        n1 = np.array([self._insert_st_event.x,
                       self._insert_st_event.y]).reshape(1, 2)
        n1 = t.inverted().transform(n1)
        xy = (n1[0][0], n1[0][1])

        obj = FigAnnotate('', xy, xytext=xytext)
        name = parent.get_next_name(obj.get_namebase())
        parent.add_child(name, obj)
        obj.realize()
        ifigure.events.SendChangedEvent(self._figure.figobj, self)

    def insert_text(self, evt):
        '''
        insert fig_text to the place where the mouse
        release happened.
        it try to find an axes to associate fig_text.
        first it looks axes_selection(). if mouse down
        happend inside the axes. it is not none, and
        will be used.
        second it checks if mouse down happend inside
        the area of any fig_axes, which are a direct
        child of fig_page.
        if both check fails, it uses fig_page as parent
        of fig_text.
        2013 05 : disabled find_ax_4_insert so that
                  it insert text always to page
                  in future, maybe it will be changed to
                  selectable action by shift-down or something.
        '''

        def finish_text_insert(x, y, txt, evt=evt, obj=self):
            self = obj
            nx, ny = self.px2norm(evt.x, evt.y)
            parent = self.find_ax_4_insert(evt)
            parent = None
            if parent is not None:
                t = parent._artists[0].transAxes
                n1 = np.array([evt.x, evt.y]).reshape(1, 2)
                n1 = t.inverted().transform(n1)
                nx = n1[0][0]
                ny = n1[0][1]
            else:
                parent = self._figure.figobj
            # print nx, ny, txt
            obj = FigText(nx, ny, txt)
            name = parent.get_next_name(obj.get_namebase())
            parent.add_child(name, obj)
            obj.realize()
            self.draw()
            ifigure.events.SendChangedEvent(self._figure.figobj, self)
            # registor paste action to history
            artists = [weakref.ref(obj._artists[0])]
            h = [UndoRedoAddRemoveArtists(artists=artists,
                                          mode=0)]
            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(h)

        y = abs(evt.y - self.canvas.GetClientSize()[1])
        self.ask_text_input(evt.x, y,
                            value='', callback=finish_text_insert)

    def find_ax_4_insert(self, evt):
        '''
        it try to find an axes to associate fig_obj
        first it looks axes_selection(). if mouse down
        happend inside the axes. it is not none, and
        will be used.
        second it checks if mouse down happend inside
        the area of any fig_axes
        '''

        nx, ny = self.px2norm(evt.x, evt.y)
        parent = None
        if self.axes_selection() is not None:
            parent = self.axes_selection().figobj
        else:
            f_page = self._figure.figobj
            for name, f_axes in f_page.get_axes():
                area = f_axes.getp('area')
                if geom_util.check_inside(area, nx, ny):
                    parent = f_axes
                    break
        return parent

    #
    #
    #   iaxesselection
    #
    #
    def i_axesselection(self, callback, figaxes):
        self._iaxesselection_mode = True
        self._iaxesselection_cb = callback
        self._iaxesselection_figaxes = figaxes
        self._iaxesselection_hl = matplotlib.patches.Rectangle(
            (0, 0), 0.01, 0.01, alpha=0.5, color='red', transform=self._figure.transFigure)
        self._figure.patches.append(self._iaxesselection_hl)
        self._iaxesselection_figaxes = figaxes
        self.iaxesselection_update_redbox()
        self.mpl_connect('axesselection')

    def iaxesselection_update_redbox(self):
        if self._iaxesselection_figaxes is None:
            return
        if self._iaxesselection_hl is None:
            return

        axes = self._iaxesselection_figaxes._artists[0]
        bbox = axes.get_position()
        pt = bbox.get_points()
        sec = [pt[0][0], pt[0][1],
               pt[1][0] - pt[0][0], pt[1][1] - pt[0][1]]
        self._iaxesselection_hl.set_x(sec[0])
        self._iaxesselection_hl.set_y(sec[1])
        self._iaxesselection_hl.set_width(sec[2])
        self._iaxesselection_hl.set_height(sec[3])
#       print 'update'
        self.draw_artist([self._iaxesselection_hl])

    def iaxesselection_motion(self, evt):
        for axes in reversed(self._figure.axes):
            bbox = axes.get_position()
            pt = bbox.get_points()
            sec = [pt[0][0], pt[0][1],
                   pt[1][0] - pt[0][0], pt[1][1] - pt[0][1]]
            nx, ny = self.px2norm(evt.x, evt.y)

            if geom_util.check_inside(sec, nx, ny):
                #  print sec, nx, ny
                self._iaxesselection_figaxes = axes.figobj
                self.iaxesselection_update_redbox()
                break

    def iaxesselection_release(self, evt):
        self._figure.patches.remove(self._iaxesselection_hl)
        self._iaxesselection_hl = None
        self._iaxesselection_cb(self._iaxesselection_figaxes)
        self._iaxesselection_mode = False
        self._iaxesselection_cb = None
        self._iaxesselection_figaxes = None
        self.draw_artist([])
        self.mpl_connect('normal')
    #
    #
    #  line_insert
    #
    #

    def line_insert(self, callback=None, mode=0):
        self.mpl_connect('line_insert')
        self._line_insert_a = None
        self._line_insert_type = mode
        self._line_insert_path = None
        self._line_insert_release = (-100, -100)

    def line_insert_show_hl(self, path):
        if self._line_insert_a is not None:
            self._figure.patches.remove(self._line_insert_a)
            self._line_insert_a = None

        p = [(item[0], item[1]) for item in path]
        codes, verts = zip(*p)
        path = matplotlib.path.Path(verts, codes)
        self._line_insert_a = PathPatch(path, facecolor='none',
                                        figure=self._figure,
                                        edgecolor='red', alpha=0.5)
        self._figure.patches.extend([self._line_insert_a])
        self.refresh_hl([self._line_insert_a])
        self._figure.patches.remove(self._line_insert_a)
        self._line_insert_a = None

    def line_insert_motion(self, evt):
        if self._line_insert_path is None:
            return
        Path = matplotlib.path.Path
        self._line_insert_path[-1] = (Path.LINETO, (evt.x, evt.y), 0)
        if evt.guiEvent.ShiftDown():
            dx = self._line_insert_path[-2][1][0] - \
                self._line_insert_path[-1][1][0]
            dy = self._line_insert_path[-2][1][1] - \
                self._line_insert_path[-1][1][1]
            if abs(dx) < abs(dy):
                self._line_insert_path[-1] = (Path.LINETO,
                                              (self._line_insert_path[-2]
                                               [1][0], evt.y),
                                              0)
            else:
                self._line_insert_path[-1] = (Path.LINETO,
                                              (evt.x,
                                               self._line_insert_path[-2][1][1]),
                                              0)
        if self._line_insert_type == 1:
            x = [x1[1][0] for x1 in self._line_insert_path]
            y = [x1[1][1] for x1 in self._line_insert_path]
            path = cbook.BezierFit(x, y)
        else:
            path = self._line_insert_path
        self.line_insert_show_hl(path)
#       self.line_insert_show_hl(self._line_insert_path)

    def line_insert_press(self, evt):
        Path = matplotlib.path.Path
        if self._line_insert_path is None:
            self._line_insert_path = [(Path.MOVETO, (evt.x, evt.y), 0),
                                      (Path.LINETO, (evt.x, evt.y), 0)]
        else:
            self._line_insert_path.append((Path.LINETO, (evt.x, evt.y), 0))

        if self._line_insert_type == 1:
            x = [x1[1][0] for x1 in self._line_insert_path]
            y = [x1[1][1] for x1 in self._line_insert_path]
            path = cbook.BezierFit(x, y)
        else:
            path = self._line_insert_path

#       self.line_insert_show_hl(self._line_insert_path)
        self.line_insert_show_hl(path)

    def line_insert_release(self, evt):
        #       print 'line insert release', evt.x, evt.y
        if (abs(self._line_insert_release[0] - evt.x) < 5 and
                abs(self._line_insert_release[1] - evt.y) < 5):
            self.mpl_connect('normal')
            self.insert_figobj(evt)
            if self._line_insert_a is not None:
                self._figure.patches.remove(self._line_insert_a)
            self._line_insert_a = None
        else:
            self._line_insert_release = (evt.x, evt.y)

    def ask_text_input(self, x, y, value='', callback=None):

        from ifigure.widgets.growable_text_ctrl import GrowableTextCtrl, EVT_GTC_ENTER

        self.Freeze()
        if self._txt_box is not None:
            self._txt_box.Show()
        else:
            self._txt_box = GrowableTextCtrl(self, wx.ID_ANY, ' ',
                                             size=(0, 0))

        self._txt_box.SetPosition((x, y))
        self._txt_box.setText(value)
        self._txt_box.SetFocus()
        self._txt_box.Refresh()

        self.Thaw()

        def finish_text_input(evt, obj=self, x=x, y=y, callback=callback):
            obj.Unbind(EVT_GTC_ENTER)
            self._txt_box.Unbind(wx.EVT_KILL_FOCUS)
            txt = ''
            if obj._txt_box is not None:
                try:
                    txt0 = obj._txt_box.GetValue()
                    txt = str(txt0)
                except UnicodeEncodeError:
                    txt = txt0
                obj._txt_box.Hide()
            callback(x, y, txt)

        def exit_text_input(evt, obj=self):
            obj.Unbind(EVT_GTC_ENTER)
            if obj._txt_box is not None:
                obj._txt_box.Hide()

        def keep_focus(evt, obj=self):
            print('Focus lost')
            # print wx.GetMousePosition()
            obj._txt_box.Refresh()
        self.Bind(EVT_GTC_ENTER, finish_text_input)
        self._txt_box.Bind(wx.EVT_KILL_FOCUS, finish_text_input)
        #self._txt_box.Bind(wx.EVT_KILL_FOCUS, exit_text_input)
        #self._txt_box.Bind(wx.EVT_KILL_FOCUS, keep_focus)

    def onKey3(self, evt):
        print('key_event')

    def dnd_motion(self, evt):
        print(('dnd motion', evt.xdata, evt.ydata))
        pass

    def _check_can_group(self):
        if len(self.selection) < 2:
            return False
        if self.selection[0]() is None:
            return False
        f = self.selection[0]().figobj.get_parent()
        flag = True
        for s in self.selection:
            if s() is None:
                flag = False
                continue
            if not s().figobj.get_parent() is f:
                flag = False
        for s in self.selection:
            if s() is None:
                flag = False
                continue
            if isinstance(s().figobj, FigAxes):
                flag = False
        return flag

    def _check_can_ungroup(self):
        if len(self.selection) != 1:
            return False
        if self.selection[0]() is None:
            return False
        if not hasattr(self.selection[0]().figobj, 'onUngroup'):
            return False
        return True

    def group(self):
        obj = [ref().figobj for ref in self.selection]
        if len(obj) == 0:
            return
        self.unselect_all()
        h = [UndoRedoGroupUngroupFigobj(figobjs=obj, mode=0)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h, menu_name='group')


#        hist = GlobalHistory().get_history(window)
#        hist.start_record()
#        hist.add_history(UndoRedoGroupUngroupFigobj(figobjs=obj, mode=0))
#        hist.stop_record()


    def ungroup(self):
        obj = [ref().figobj for ref in self.selection]
        self.unselect_all()
        h = [UndoRedoGroupUngroupFigobj(figobjs=obj, mode=1)]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h, menu_name='ungroup')

#        hist = GlobalHistory().get_history(window)
#        hist.start_record()
#        hist.add_history(UndoRedoGroupUngroupFigobj(figobjs=obj, mode=1))
#        hist.stop_record()

    def do_amode_scale(self):
        box1 = self._a_mode_scale_anchor
        box2 = [min(self.draghandlers[6]._x), max(self.draghandlers[6]._x),
                min(self.draghandlers[6]._y), max(self.draghandlers[6]._y)]
        from ifigure.utils.geom import calc_scale, scale_rect
        scale = calc_scale(box2, box1)
        # print scale_rect(box1, scale)

        h = []
        for a in self.selection:
            h.extend(a().figobj.scale_artist(scale, action=True))
        window = self.GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.make_entry(h)
        #       self.draw()

    # 3D slice panel
    def show_3d_slice_palette(self, pos=None):
        if self.axes_selection() is None:
            return
        target = self.axes_selection().figobj

        def callback(value, target=target, canvas=self):
            v1 = [value[0][0], value[1][0], value[2][0]]
            v2 = [value[0][1], value[1][1], value[2][1]]
            if value[3]:
                book = canvas._figure.figobj
                for ax in book.walk_axes():
                    if ax.get_3d():
                        ax._artists[0]._lighting['clip_limit1'] = v1
                        ax._artists[0]._lighting['clip_limit2'] = v2
                        ax.set_bmp_update(False)
            else:
                target._artists[0]._lighting['clip_limit1'] = v1
                target._artists[0]._lighting['clip_limit2'] = v2
                target.set_bmp_update(False)
            canvas.draw()

        def close_callback(value, target=target, canvas=self):
            book = canvas._figure.figobj
            for ax in book.walk_axes():
                if ax.get_3d():
                    if (np.sum(ax._artists[0]._lighting['clip_limit1']) == 0 and
                            np.sum(ax._artists[0]._lighting['clip_limit2']) == 3):
                        continue

                    ax._artists[0]._lighting['clip_limit1'] = [0, 0, 0]
                    ax._artists[0]._lighting['clip_limit2'] = [1, 1, 1]
                    ax.set_bmp_update(False)

            canvas.draw()

        from ifigure.utils.edit_list import EditListMiniFrame

        setting = {"minV": -4,
                   "maxV": 5.,
                   "val": [-4.1, 4.9],
                   "res": 0.001,
                   "motion_event": True,
                   "text_box": True}
        ll = (["X", (0, 1.0), 39, setting],
              ["Y", (0, 1.0), 39, setting],
              ["Z", (0, 1.0), 39, setting],
              [None, False, 3, {"text": "slice all 3d panels"}])

        f = EditListMiniFrame(
            self,
            wx.ID_ANY,
            title='3D slice setting',
            list=ll,
            callback=callback,
            pos=pos,
            close_callback=close_callback)
        f.Show()

    def install_toolbar_palette(self, name, tasks, mode='2D', refresh=None):
        self.toolbar.install_palette(name, tasks, mode, refresh)

    def use_toolbar_palette(self, name, mode='2D'):
        self.toolbar.use_palette(name, mode)

    def use_toolbar_std_palette(self):
        self.toolbar.use_std_palette()

    @property
    def hl_color(self):
        return self.canvas.hl_color

    @hl_color.setter
    def hl_color(self, value):
        self.canvas.hl_color = value
