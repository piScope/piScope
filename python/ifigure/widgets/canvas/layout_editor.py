#
#  Name   :section_editor
#
#          gui to edit section
#
#  History:
#          2012 spring v 0.1
#          2012 09 04 edge drag was added
#          2013 03    equal space and axis dge only
#          2014 02    bug fix.
#                     delete by edge drag
#               03    adding undo/redo
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu

__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

from ifigure.utils.wx3to4 import menu_AppendItem
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists
from ifigure.widgets.undo_redo_history import UndoRedoGroupUngroupFigobj
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import GlobalHistory
import wx
import weakref
import numpy as np

from ifigure.mto.fig_axes import FigAxes
#from ifigure.widgets.primitive_widgets import margin_widget, marginp_widget
from ifigure.widgets.margin_widget import MarginWidget, MarginpWidget
from ifigure.utils import geom as geom_util
import ifigure.events
#from matplotlib.figure import Figure
#from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED
from numpy.linalg import inv

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('LayoutEditor')


def _fix_event_data(w, h, event):
    event.xdata = float(event.x)/w
    event.ydata = float(event.y)/h
    if (event.xdata < 0) | (event.xdata > 1):
        event.xdata = None
    if (event.ydata < 0) | (event.ydata > 1):
        event.ydata = None
    return event


def send_area_request(canvas, axes=None, request=None, ac=None, name='area'):

    # canvas = ifigure_canvas
    fig_page = canvas._figure.figobj
    if ac is None:
        ac = []
    for mode, idx, value in request:
        if mode == 'm':  # modify
            fig_axes = fig_page.get_axes(idx)
            ac.append(UndoRedoFigobjMethod(fig_axes._artists[0],
                                           'area', value))
        elif mode == 'a':  # add
            iax = fig_page.add_axes(area=value)
            ax = fig_page.get_axes(iax)
            ax.realize()
            sel = [weakref.ref(ax._artists[0])]
            ac.append(UndoRedoAddRemoveArtists(artists=sel, mode=0))
        elif mode == 'd':  # delete
            fig_axes = fig_page.get_axes(idx)
            sel = [weakref.ref(a) for a in fig_axes._artists]
            ac.append(UndoRedoAddRemoveArtists(artists=sel, mode=1))

    window = canvas.GetTopLevelParent()
    GlobalHistory().get_history(window).make_entry(ac,
                                                   menu_name=name)


class AskRC(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title)

        box = wx.BoxSizer(wx.VERTICAL)

        from ifigure.utils.wx3to4 import FlexGridSizer
        vbox = FlexGridSizer(2, 2)

        stline1 = wx.StaticText(self, 3, 'R')
        self.sc1 = wx.SpinCtrl(self, -1, '')
        self.sc1.SetRange(1, 8)
        stline2 = wx.StaticText(self, 3, 'C')
        self.sc2 = wx.SpinCtrl(self, -1, '')
        self.sc2.SetRange(1, 8)
        vbox.Add(stline1, 1,  wx.ALIGN_CENTER | wx.TOP, 10)
        vbox.Add(self.sc1, 1, wx.ALIGN_CENTER | wx.TOP, 10)
        vbox.Add(stline2, 1, wx.ALIGN_CENTER | wx.TOP, 10)
        vbox.Add(self.sc2, 1, wx.ALIGN_CENTER | wx.TOP, 10)

        sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        box.Add(vbox,  0, wx.ALIGN_CENTER | wx.ALL, 10)
        box.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(box)
        self.Fit()
        #self.Bind(wx.EVT_BUTTON, self.OnOK, id=wx.ID_OK)
        #self.Bind(wx.EVT_BUTTON, self.OnCANCEL, id=wx.ID_CANCEL)
        self.Center()

    def OnOK(self, event):
        self.Close()

    def OnCANCEL(self, event):
        self.Close()

    def GetValue(self):
        return (self.sc1.GetValue(), self.sc2.GetValue())


class layout_editor_popup(wx.Menu):
    def __init__(self, parent):
        super(layout_editor_popup, self).__init__(
            style=wx.WS_EX_PROCESS_UI_UPDATES)
        self.parent = weakref.ref(parent)
        self.mmi = []
        m = ["Split", "Merge", "Swap", "Distribute Horizontally",
             "Distribute Vertically",
             "Sort by Column", "Sort by Row",
             "Common Bottom Axis",
             "Common Left Axis", "Reset Common Axis", ]

        h = [self.onSplit, self.onMerge, self.onSwap, self.onDistH,
             self.onDistV, self.onSortCol, self.onSortRow,
             self.onCommBtm, self.onCommLft,
             self.onResetCommon, ]

        for k in range(0, len(m)):
            key = m[k]
            if key == "---":
                self.AppendSeparator()
                continue
            mmi = wx.MenuItem(self, wx.ID_ANY, key)
            menu_AppendItem(self, mmi)
            self.Bind(wx.EVT_MENU, h[k], mmi)
            self.mmi.append(mmi)

    def onSplit(self, e):
        dialog = AskRC(self.parent(), wx.ID_ANY, "Split Subplot")
        le = self.parent().layout_editor
        if dialog.ShowModal() == wx.ID_OK:
            rc = dialog.GetValue()
            area = le.area_hit
            new_areas = le.split_area(area, rc[0], rc[1])
#           self.parent.replace_area(area, new_areas)
            request = [('m', le.area.index(le.area_hit), new_areas[0])]
            for a in new_areas[1:]:
                request.append(('a', None, a))
            le.SetCanvasValue(request=request)
            le.area_hit = None
            le.SetEditorValue()
        dialog.Destroy()

    def onMerge(self, e):
        self.parent().layout_editor._wait4merge = True
        self.parent().layout_editor._merge_a = self.parent().layout_editor.area_hit

    def onSwap(self, e):
        self.parent().layout_editor._wait4swap = True
        self.parent().layout_editor._swap_a = self.parent().layout_editor.area_hit

    def onDistH(self, e):
        self.parent().layout_editor.distH(self.parent().layout_editor.area_hit)

    def onDistV(self, e):
        self.parent().layout_editor.distV(self.parent().layout_editor.area_hit)

    def onCommBtm(self, e):
        self.parent().layout_editor.apply_bottom_only(
            self.parent().layout_editor.area_hit)

    def onCommLft(self, e):
        self.parent().layout_editor.apply_left_only(
            self.parent().layout_editor.area_hit)

    def onSortRow(self, e):
        from ifigure.events import SendChangedEvent
        self.parent()._figure.figobj.sort_axes_row()
        self.parent().layout_editor.draw()
        fig = self.parent()._figure.figobj
        SendChangedEvent(fig, w=None, useProcessEvent=False)

    def onSortCol(self, e):
        from ifigure.events import SendChangedEvent
        self.parent()._figure.figobj.sort_axes_col()
        self.parent().layout_editor.draw()
        fig = self.parent()._figure.figobj
        SendChangedEvent(fig, w=None, useProcessEvent=False)

    def onResetCommon(self, evt):
        fig = self.parent()._figure
        f_page = fig.figobj
        ac = []
        request = []
        for f_axes in f_page.walk_axes():
            ac.append(UndoRedoFigobjMethod(f_axes._artists[0],
                                           'edge_only', [False]*4))
            ac.append(UndoRedoFigobjMethod(f_axes._artists[0],
                                           'extra_margin', [0, 0, 0, 0]))
            request.append(('m', f_page.get_iaxes(f_axes), f_axes.get_area()))

        # finish up
        send_area_request(self.parent(), request=request,
                          ac=ac, name='reset common axis')

    def update_ui(self):
        if self.parent().axes_selection() is None:
            return False
        if self.parent().axes_selection().figobj is None:
            return False
        if any(self.parent().axes_selection().figobj.get_edge_only()):
            self.mmi[-1].Enable(True)
        else:
            self.mmi[-1].Enable(False)
        return True
#       wx.CallAfter(self.SetEditorValue)


class layout_editor(object):
    def __init__(self, parent):
        self.parent = weakref.ref(parent)
        self.area = []
        self.rect = []
        self.fig_hl = []  # used to draw area
        self.fig_txt = []  # used to draw area
        self.fig_hl2 = []  # used to draw area during drag
        self.fig_hlp = []  # patches
        self.edge_hl = None
        self.edge_hit = []
        self._mid = None
        self.drag = 0

        self.use_def_margin = []
        self.area_hit = None
        self._wait4merge = False
        self._merge_a = None
        self._wait4swap = False
        self._swap_a = None
        self._disth = False
        self._distv = False
        self.page_margin = [0, 0, 0, 0]
        self.nomargin = False
        self._popup = layout_editor_popup(parent)
#       self. _load_canvas_value()

    @property
    def canvas(self):
        return self.parent()

    @property
    def mpl_canvas(self):
        return self.parent().canvas

    @property
    def figure(self):
        return self.parent()._figure

    def enter_layout_mode(self):
        self. _load_canvas_value()
        self.draw()

    def exit_layout_mode(self):
        if self._mid is not None:
            self.mpl_canvas.mpl_disconnect(self._mid)
        self._mid = None
        self.remove_artists()

    def remove_artists(self, drag=True, layout=True):
        if layout:
            for l in self.fig_hl:
                self.figure.lines.remove(l)
            self.fig_hl = []
            for l in self.fig_txt:
                self.figure.texts.remove(l)
            self.fig_txt = []
            for l in self.fig_hlp:
                self.figure.patches.remove(l)
            self.fig_hlp = []
        if drag:
            for l in self.fig_hl2:
                self.figure.lines.remove(l)

            self.fig_hl2 = []

    def replace_area(self, area, new_areas):
        idx = self.area.index(area)
        self.area.remove(area)
        self.area.insert(idx, new_areas[0])

        if len(new_areas) > 1:
            for k in range(1, len(new_areas)):
                self.area.append(new_areas[k])
        self.draw()

#   def onDraw(self, event):
#       dprint1('onDraw')
        # this is for  draw_event of mpl
    def draw_all(self):
        self._load_canvas_value()
        self.draw()

    def draw(self):
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle
        dprint2('draw')

        if self.nomargin:
            pm = [0, 0, 0, 0]
        else:
            pm = self.page_margin
  #      if self.parent.get_canvas() is None: return
        fig = self.figure
        f_page = fig.figobj

        self.remove_artists()

        rect1s = [(pm[0], pm[3], 1.-pm[1]-pm[0], 1.-pm[2]-pm[3])]
        rect2s = []

        for f_axes in f_page.walk_axes():
            area = f_axes.getp("area")
            rect1 = [(1.-pm[0]-pm[1])*area[0]+pm[0],
                     (1.-pm[2]-pm[3])*area[1]+pm[3],
                     area[2]*(1.-pm[0]-pm[1]),
                     area[3]*(1.-pm[2]-pm[3]), ]

            rect1s.append(rect1)
            if area == self.area_hit:
                rect2, void, void2 = f_axes.calc_rect()
                rect2s.append(rect2)
        for num, rect1 in enumerate(rect1s):
            x, y = self._area2xy(rect1)
            w, h = self.mpl_canvas.get_width_height()
            x1 = (np.array(x)*(w-2)+1)/w
            y1 = (np.array(y)*(h-2)+1)/h
            hl = Line2D(x1, y1, marker=None,
                        color='r', linestyle='-',
                        markerfacecolor='k',
                        transform=self.figure.transFigure,
                        figure=self.figure, alpha=0.3,
                        linewidth=5)
            self.fig_hl.append(hl)
            self.figure.lines.append(hl)
            if num != 0:
                t = self.figure.text((max(x1)+min(x1))/2,
                                     (max(y1)+min(y1))/2,
                                     str(num-1),
                                     transform=self.figure.transFigure,
                                     color='red', size=18)
                self.fig_txt.append(t)
        for rect2 in rect2s:
            x, y = self._area2xy(rect2)
            x1 = (np.array(x)*(w-2)+1)/w
            y1 = (np.array(y)*(h-2)+1)/h
            hl = Rectangle((min(x1), min(y1)),
                           max(x1)-min(x1), max(y1)-min(y1),
                           facecolor='r', alpha=0.3,
                           transform=self.figure.transFigure,
                           figure=self.figure)
            self.fig_hlp.append(hl)
            self.figure.patches.append(hl)

        f_page = self.canvas._figure.figobj
        nsec = f_page.num_axes()
        nsec2 = f_page.num_axes(include_floating=True)
        for i in range(nsec2-nsec):
            f_axes = f_page.get_axes(iax=i+nsec)
            bb = f_axes._artists[0].get_window_extent().bounds
            x, y = self.figure.transFigure.inverted().transform((bb[0] + bb[2]/2.,
                                                                 bb[1] + bb[3]/2.))
            t = self.figure.text(x, y,
                                 str(i+nsec),
                                 color='green',
                                 size=18)
            self.fig_txt.append(t)

        self.canvas.draw_artist(self.fig_hl+self.fig_hlp + self.fig_txt)
        self.remove_artists()

    def draw_request(self, request):
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle

        if self.nomargin:
            pm = [0, 0, 0, 0]
        else:
            pm = self.page_margin
#       if self.parent.get_canvas() is None: return
        fig = self.figure
        f_page = fig.figobj
        self.remove_artists()  # layout=False)
#       for type, idx, area in request:
        areas = [area for type, idx, area in request]
        areas.append([0, 0, 1, 1])
        for area in areas:
            if area is None:
                continue
            rect1 = [(1.-pm[0]-pm[1])*area[0]+pm[0],
                     (1.-pm[2]-pm[3])*area[1]+pm[3],
                     area[2]*(1.-pm[0]-pm[1]),
                     area[3]*(1.-pm[2]-pm[3]), ]
            x, y = self._area2xy(rect1)
            w, h = self.mpl_canvas.get_width_height()
            x1 = (np.array(x)*(w-2)+1)/w
            y1 = (np.array(y)*(h-2)+1)/h
            hl = Line2D(x1, y1, marker=None,
                        color='r', linestyle='-',
                        markerfacecolor='k',
                        transform=self.figure.transFigure,
                        figure=self.figure, alpha=0.3, linewidth=5)
            self.fig_hl2.append(hl)
            self.figure.lines.append(hl)
        self.canvas.draw_artist(self.fig_hl2)
        self.remove_artists()

    def split_area(self, area, r, c):
        w = float(area[2])/c
        h = float(area[3])/r
        ret = []
        for j in range(0, c):
            for i in range(0, r):
                ret.append([area[0]+j*w, area[1]+(r-i-1)*h, w, h])
        return ret

    def merge_area(self, a1, a2):
        box1 = self._area2box(a1)
        box2 = self._area2box(a2)

        new_box = None
        if (abs(box1[0] - box2[0]) < 0.0001 and
                abs(box1[2] - box2[2]) < 0.0001):
            # vertical merge
            if abs(box1[1] - box2[3]) < 0.001:
                new_box = [box1[0], min([box1[3], box2[1]]),
                           box2[2], max([box1[3], box2[1]])]
            if abs(box2[1] - box1[3]) < 0.001:
                new_box = [box1[0], min([box1[1], box2[3]]),
                           box2[2], max([box1[1], box2[3]])]
        if (abs(box1[1] - box2[1]) < 0.001 and
                abs(box1[3] - box2[3]) < 0.001):
            # horizontal merge
            if abs(box1[0] - box2[2]) < 0.001:
                new_box = [min([box1[2], box2[0]]), box1[1],
                           max([box1[2], box2[0]]), box2[3]]
            if abs(box2[0] - box1[2]) < 0.001:
                new_box = [min([box1[0], box2[2]]), box1[1],
                           max([box1[0], box2[2]]), box2[3]]

        if new_box is None:
            return None
        return self._box2area(new_box)

    def buttonpress(self, event):
        self. _load_canvas_value()
        # edge hit check
#       h = self.figure.get_figheight()*self.figure.get_dpi()
#       w = self.figure.get_figwidth()*self.figure.get_dpi()
        w, h = self.mpl_canvas.get_width_height()
        event = _fix_event_data(w, h, event)

        self.edge_hit = []
        self.edge_hit2 = []
        self.edge_hit3 = ()
        self.drag = 0
        for i, area in enumerate(self.area):
            # edge hit overwrite event.x or event.y if it hits
            hit = self.check_edge_hit(area, event, w, h)
            if hit != -1:
                self.edge_hit.append([i, hit, False])
        for i, area in enumerate(self.area):
            hit2 = self.check_edge_hit2(area, event.x, event.y,
                                        w, h)
            if hit2 != -1:
                self.edge_hit2.append([i, hit2, False])
        if len(self.edge_hit) != 0:
            if event.key == 'shift':
                single = True
            else:
                single = False
            self.edge_hit3 = self.select_connected_edge(single=single)
            if self.edge_hit3[0] != -1:
                if self._mid is None:
                    self._last_request = None
                    self._mid = self.mpl_canvas.mpl_connect(
                        'motion_notify_event', self.motion)
                self.add_edge_hl()
                return
            else:
                self.edge_hit = []
                self.edge_hit2 = []
                self.edge_hit3 = ()

        # area hit check
        if self.nomargin:
            pm = [0, 0, 0, 0]
        else:
            pm = self.page_margin

        for area in self.area:
            rect1 = [(1.-pm[0]-pm[1])*area[0]+pm[0],
                     (1.-pm[2]-pm[3])*area[1]+pm[3],
                     area[2]*(1.-pm[0]-pm[1]),
                     area[3]*(1.-pm[2]-pm[3]), ]

            if geom_util.check_inside(rect1, event.xdata,
                                      event.ydata):
                self.area_hit = area
#             self.draw()
                self.SetEditorValue()
                return
        self.area_hit = self.area[0]
        self.SetEditorValue()

    def buttonrelease(self, event):
        w, h = self.mpl_canvas.get_width_height()
        event = _fix_event_data(w, h, event)
        # cleaning...
        if self._mid is not None:
            self.mpl_canvas.mpl_disconnect(self._mid)
        self._mid = None
        self.remove_artists(layout=False)

        if event.button == 3:
            if len(self.edge_hit) == 0:
                # context menu
                #              scr_size=self.mpl_canvas.GetClientSize()
                if not self._popup.update_ui():
                    return
                self.mpl_canvas.PopupMenu(self._popup,
                                          [event.x, h-event.y])
            else:
                self.rm_edge_hl()
        if event.button == 1:
            #         print self._wait4merge
            if self._wait4merge:
                if self._merge_a is None:
                    return
                if self.area_hit is None:
                    return
                new_area = self.merge_area(self._merge_a, self.area_hit)
                if new_area is not None:
                    request = [('m', self.area.index(self._merge_a), new_area),
                               ('d', self.area.index(self.area_hit), None)]
                    self.SetCanvasValue(request=request)
                wx.CallAfter(self.SetEditorValue)
#               self.SetEditorValue()
#               self.canvas.draw()
                self._merge_a = None
                self._wait4merge = False
            if self._wait4swap:
                if self._swap_a is None:
                    return
                if self.area_hit is None:
                    return
                request = [('m', self.area.index(self.area_hit), self._swap_a),
                           ('m', self.area.index(self._swap_a), self.area_hit)]
                self.SetCanvasValue(request=request)
                wx.CallAfter(self.SetEditorValue)
#            self.canvas.draw()

                self._swap_a = None
                self._wait4swap = False

            if (self.drag == 1 and
                    len(self.edge_hit) != 0):
                self.rm_edge_hl()
                request = self.process_edge_drag(event)
                if request is not None:
                    self.SetCanvasValue(request=request)
#             wx.CallAfter(self.SetEditorValue)

            fig = self.figure
            f_page = fig.figobj

            ax = None
            for f_axes in f_page.walk_axes():
                if not isinstance(f_axes, FigAxes):
                    continue
                area = f_axes.getp("area")
                if area == self.area_hit:
                    ax = f_axes
                    break
            if ax is not None:
                ifigure.events.SendSelectionEvent(
                    f_axes, self.canvas.GetTopLevelParent(), [])

        # print self.area_hit

    def onpick(self, event):
        pass

    def motion(self, event):
        w, h = self.mpl_canvas.get_width_height()
        event = _fix_event_data(w, h, event)

        if event.xdata is None or event.ydata is None:
            return
        self.drag = 1
        if (self.edge_hl is not None and
                len(self.edge_hit3) != 0):
            area_bk = [a[:] for a in self.area]
            request = self.process_edge_drag(event)
            self.area = area_bk
        if request is not None:
            self.draw_request(request)

    def add_edge_hl(self):
        self.edge_hl = True

    def rm_edge_hl(self):
        #       if self.edge_hl in self.axes.lines:
        #           self.edge_hl.remove()
        self.edge_hl = None

    def process_release_outside(self, event):
        cx, cy = self.canvas.GetClientSize()
        # rarea -> removed
        # earea -> expanded
        request = []
        irarea = []
        earea = None
        if event.x < 0:
            irarea = [k[0] for k in self.edge_hit2 if k[1] == 2]
            earea = [(k[0], self.area[k[0]])
                     for k in self.edge_hit2 if k[1] == 0]
            for idx, x in earea:
                x[2] = x[2]+x[0]
                x[0] = 0
                request.append(('m', idx, x))
        elif event.x > cx:
            irarea = [k[0] for k in self.edge_hit2 if k[1] == 0]
            earea = [(k[0], self.area[k[0]])
                     for k in self.edge_hit2 if k[1] == 2]
            for idx, x in earea:
                x[2] = 1.-x[0]
                request.append(('m', idx, x))

        elif event.y < 0:
            irarea = [k[0] for k in self.edge_hit2 if k[1] == 3]
            earea = [(k[0], self.area[k[0]])
                     for k in self.edge_hit2 if k[1] == 1]
            for idx, x in earea:
                x[3] = x[3]+x[1]
                x[1] = 0
                request.append(('m', idx, x))

        elif event.y > cy:
            irarea = [k[0] for k in self.edge_hit2 if k[1] == 1]
            earea = [(k[0], self.area[k[0]])
                     for k in self.edge_hit2 if k[1] == 3]
            for idx, x in earea:
                x[3] = 1 - x[1]
                request.append(('m', idx, x))

        if earea is not None and len(earea) == 0:
            # filling void
            if len(irarea) == 1:
                k = irarea[0]
                left, right, up, down = self._search_nearby(self.area[k])
                if len(left) > 0 and len(right) == 0:
                    for idx, x in left:
                        x[2] = 1 - x[0]
                        request.append(('m', idx, x))
                elif len(left) > 0 and len(right) > 0:
                    mid = self.area[k][0] + self.area[k][2]/2.0
                    for idx, x in right:
                        x[2] = x[0] + x[2] - mid
                        x[0] = mid
                        request.append(('m', idx, x))
                    for idx, x in left:
                        x[2] = mid - x[0]
                        x[0] = x[0]
                        request.append(('m', idx, x))
                elif len(left) == 0 and len(right) > 0:
                    for idx, x in right:
                        x[2] = x[0] + x[2]
                        x[0] = 0
                        request.append(('m', idx, x))
                elif len(up) > 0 and len(down) == 0:
                    for idx, x in up:
                        x[3] = x[1] + x[1]
                        x[1] = 0
                        request.append(('m', idx, x))
                elif len(up) > 0 and len(down) > 0:
                    mid = self.area[k][1] + self.area[k][3]/2.0
                    for idx, x in down:
                        x[3] = mid - x[1]
                        x[1] = x[1]
                        request.append(('m', idx, x))
                    for idx, x in up:
                        x[3] = x[1] + x[3] - mid
                        x[1] = mid
                        request.append(('m', idx, x))
                elif len(up) == 0 and len(down) > 0:
                    for idx, x in down:
                        x[3] = 1 - x[1]
                        request.append(('m', idx, x))

        for k in irarea:
            request.append(('d', k, None))

        if len(request) > 0:
            return request

    def process_edge_drag(self, event):
        def calc_push(areas, nextones, d, mode, min_d):
            if (mode == 0) | (mode == 2):
                dd = sum([areas[k][2]-min_d for k in nextones])
                ddd = [d*(areas[k][2]-min_d)/dd for k in nextones]
            else:
                dd = sum([areas[k][3]-min_d for k in nextones])
                ddd = [d*(areas[k][3]-min_d)/dd for k in nextones]

            return ([sum(ddd[k:]) for k in range(len(nextones))],
                    [sum(ddd[k+1:]) for k in range(len(nextones))])
#       event = self._fix_event_data(event)
        cx, cy = self.canvas.GetClientSize()
        if event.xdata is None or event.ydata is None:
            return self.process_release_outside(event)

        if self.nomargin:
            pm = [0., 0., 0., 0.]
        else:
            pm = self.page_margin

        # this maps events to normal coordinate so that
        # area can use it.
        event.xdata = (event.xdata - pm[0])/(1.-pm[0]-pm[1])
        event.ydata = (event.ydata - pm[3])/(1.-pm[2]-pm[3])
        event.x = (event.x - cx*pm[0])/(1.-pm[0]-pm[1])
        event.y = (event.y - cy*pm[3])/(1.-pm[2]-pm[3])

        if event.xdata > 1 or event.xdata < 0:
            event.xdata = None
        if event.ydata > 1 or event.ydata < 0:
            event.ydata = None

        if event.xdata is None or event.ydata is None:
            return self.process_release_outside(event)

        area_bk = [a[:] for a in self.area]
        # backup

        request = []
        min_dx = 10./cx
        min_dy = 10./cy
        ohit2 = [tmp for tmp in self.edge_hit2]  # original data
        for hit in self.edge_hit2:
            if not hit[2]:
                continue
            nextones = self.find_nexeones(hit[0], hit[1])

            if hit[1] == 0:
                x = self.area[hit[0]][0]+self.area[hit[0]][2]
                d = x - event.xdata
                if d < min_dx:
                    if len(nextones) == 0:
                        return self._last_request
#                       self.area = area_bk
#                       return
                    x = min_dx - d
                    x1, x2 = calc_push(self.area, nextones, x, 0, min_dx)
                    for i, k2 in enumerate(nextones):
                        self.push_area(k2, 0, x1[i], x2[i])
                    d = min_dx
                self.area[hit[0]][0] = event.xdata
                self.area[hit[0]][2] = d
            elif hit[1] == 1:
                y = self.area[hit[0]][1]+self.area[hit[0]][3]
                d = y - event.ydata
                if d < min_dy:
                    if len(nextones) == 0:
                        return self._last_request
                #           self.area = area_bk
#                       return
                    x = min_dy - d
                    x1, x2 = calc_push(self.area, nextones, x, 1, min_dy)
                    for i, k2 in enumerate(nextones):
                        self.push_area(k2, 1, x1[i], x2[i])
                    d = min_dy
                self.area[hit[0]][1] = event.ydata
                self.area[hit[0]][3] = d

            elif hit[1] == 2:
                d = event.xdata - self.area[hit[0]][0]
                if d < min_dx:
                    if len(nextones) == 0:
                        return self._last_request
#                       self.area = area_bk
#                       return
                    x = min_dx - d
                    x1, x2 = calc_push(self.area, nextones, x, 2, min_dx)
                    for i, k2 in enumerate(nextones):
                        self.push_area(k2, 2, -x1[i], -x2[i])
                    d = min_dx
  #                 self.area[hit[0]][0] = self.area[hit[0]][0] - min_d
                    self.area[hit[0]][0] = event.xdata - d
                self.area[hit[0]][2] = d

            elif hit[1] == 3:
                d = event.ydata - self.area[hit[0]][1]
                if d < min_dy:
                    if len(nextones) == 0:
                        return self._last_request
#                       self.area = area_bk
#                       return
                    x = min_dy - d
                    x1, x2 = calc_push(self.area, nextones, x, 3, min_dy)
                    for i, k2 in enumerate(nextones):
                        self.push_area(k2, 3, -x1[i], -x2[i])
                    d = min_dy
#                  self.area[hit[0]][1] = self.area[hit[0]][1] - min_d
                    self.area[hit[0]][1] = event.ydata - d
                self.area[hit[0]][3] = d

        for k, a in enumerate(self.area):
            request.append(('m', k, self.area[k]))

#       for mode, idx, area in request:
#           if area[3] < 0:
#                print self._search_connecting_area(self.area[idx], False)
        d = self.edge_hit3[2] - self.edge_hit3[1]
        if self.edge_hit3[4] == 1:  # boundary drag mode..
            for hit in ohit2:
                if not hit:
                    continue
                if hit[1] == 0:
                    newa = [0, self.edge_hit3[1], event.xdata, d]
                    break
                if hit[1] == 1:
                    newa = [self.edge_hit3[1], 0, d, event.ydata]
                    break
                if hit[1] == 2:
                    newa = [event.xdata, self.edge_hit3[1],
                            abs(1-event.xdata), d]
                    break
                if hit[1] == 3:
                    newa = [self.edge_hit3[1],
                            event.ydata, d, abs(1-event.ydata)]
                    break
            request.append(('a', None, newa))
#          self.area.append(newa)
        for mode, idx, a in request:
            if (a[2]*cx < 10) | (a[3]*cy < 10):
                return self._last_request
#                self.area = area_bk
                return
        if abs(sum([abs(a[2]*a[3]) for mode, idx, a in request]) - 1) > 0.01:
            return self._last_request
#           self.area = area_bk
        else:
            self._last_request = request
            return request

    def push_area(self, k, mode, d, d2):
        # d move of the first side
        # d2 move of the other side
        if mode == 0:
            self.area[k][0] = self.area[k][0] + d
            self.area[k][2] = self.area[k][2] - d + d2
        elif mode == 1:
            self.area[k][1] = self.area[k][1] + d
            self.area[k][3] = self.area[k][3] - d + d2
        elif mode == 2:
            self.area[k][0] = self.area[k][0] + d2
            self.area[k][2] = self.area[k][2] + d - d2
        elif mode == 3:
            self.area[k][1] = self.area[k][1] + d2
            self.area[k][3] = self.area[k][3] + d - d2

    def find_nexeones(self, k, mode, ans=None):
        # find next one:
        def check_dir(a1, a2, mode):
            #  mode = 0 : true if a1 is left of a2
            if mode == 0:
                return a1[0] < a2[0]
            elif mode == 1:
                return a1[1] < a2[1]
            elif mode == 2:
                return a1[0] > a2[0]
            elif mode == 3:
                return a1[1] > a2[1]

        def op_mode(mode):
            if mode == 0:
                return 2
            elif mode == 1:
                return 3
            elif mode == 2:
                return 0
            elif mode == 3:
                return 1

        h = True if (mode == 0) | (mode == 2) else False
        omode = op_mode(mode)
        if ans is None:
            ans = []
        for k2, a in enumerate(self.area):
            if (self._check_attached(self.area[k2], self.area[k], h=h) &
                    check_dir(self.area[k2], self.area[k], omode)):
                ans.append(k2)
                ans = self.find_nexeones(k2, mode, ans)
        return ans

    def check_corner_hit(self, area, x, y, w, h):
        delta = 5

        box = self._area2box(area)
        boxd = [box[0]*w, box[1]*h, box[2]*w, box[3]*h]
        xd = x*w
        yd = y*h

        if abs(boxd[0]-xd) < delta:
            if abs(boxd[1]-yd) < delta:
                return 0
            if abs(boxd[3]-yd) < delta:
                return 1
        if abs(boxd[2]-xd) < delta:
            if abs(boxd[1]-yd) < delta:
                return 2
            if abs(boxd[3]-yd) < delta:
                return 3
        return -1

    def check_edge_hit(self, area, event, w, h):
        '''
        check if event hit on edge
        '''
        xd = event.x
        yd = event.y
        area2 = self.apply_pm_2_area(area)
        box = self._area2box(area2)
        boxd = [box[0]*w, box[1]*h, box[2]*w, box[3]*h]
        if (xd < 15) | (w-xd < 15) | (yd < 15) | (h-yd < 15):
            delta = 20
        else:
            delta = 5

        if abs(boxd[0]-xd) < delta:
            if (boxd[1]-yd)*(boxd[3]-yd) < 0:
                event.x = boxd[0]
                return 0
        if abs(boxd[1]-yd) < delta:
            if (boxd[0]-xd)*(boxd[2]-xd) < 0:
                event.y = boxd[1]
                return 1
        if abs(boxd[2]-xd) < delta:
            if (boxd[1]-yd)*(boxd[3]-yd) < 0:
                event.x = boxd[2]
                return 2
        if abs(boxd[3]-yd) < delta:
            if (boxd[0]-xd)*(boxd[2]-xd) < 0:
                event.y = boxd[3]
                return 3
        return -1

    def check_edge_hit2(self, area, xd, yd, w, h):
        '''
        check if event hit on edge or extended
        '''

        area2 = self.apply_pm_2_area(area)
        box = self._area2box(area2)
        boxd = [box[0]*w, box[1]*h, box[2]*w, box[3]*h]
        if (xd < 15) | (w-xd < 15) | (yd < 15) | (h-yd < 15):
            delta = 20
        else:
            delta = 3
        if abs(boxd[0]-xd) < delta:
            return 0
        if abs(boxd[1]-yd) < delta:
            return 1
        if abs(boxd[2]-xd) < delta:
            return 2
        if abs(boxd[3]-yd) < delta:
            return 3
        return -1

    def apply_pm_2_area(self, area):
        if self.nomargin:
            pm = [0., 0., 0., 0.]
        else:
            pm = self.page_margin
        area2 = [(1.-pm[0]-pm[1])*area[0]+pm[0],
                 (1.-pm[2]-pm[3])*area[1]+pm[3],
                 area[2]*(1.-pm[0]-pm[1]),
                 area[3]*(1.-pm[2]-pm[3]), ]
        return area2

    def unapply_pm_2_area(self, area):
        if self.nomargin:
            pm = [0., 0., 0., 0.]
        else:
            pm = self.page_margin
        return [(area[0]-pm[0])/(1.-pm[0]-pm[1]),
                (area[1]-pm[3])/(1.-pm[2]-pm[3]),
                area[2]/(1.-pm[0]-pm[1]),
                area[3]/(1.-pm[2]-pm[3]), ]

    def select_connected_edge(self, single=False):
        '''
        chose all edge among hit2 which are 
        connected to hit
        '''
        area = self.area[self.edge_hit[0][0]]
        #area = self.apply_pm_2_area(area)
        if self.edge_hit[0][1] == 0:
            x = area[0]
        if self.edge_hit[0][1] == 1:
            y = area[1]
        if self.edge_hit[0][1] == 2:
            x = area[0]+area[2]
        if self.edge_hit[0][1] == 3:
            y = area[1]+area[3]

        if single:
            self.edge_hit2 = [tmp[:] for tmp in self.edge_hit]

        # extend edge_hit flag (left edge of the area)
        cx, cy = self.canvas.GetClientSize()
        if self.edge_hit[0][1] == 0 or self.edge_hit[0][1] == 2:
            maxy0, miny0 = self.mark_hit2_edge(0, 1, 3)
            maxy1, miny1 = self.mark_hit2_edge(2, 1, 3)
#           print maxy0, miny0, maxy1, miny1
            if maxy0 == -1 and miny0 == -1:
                return 0, miny1, maxy1, x, 1
            if maxy1 == -1 and miny1 == -1:
                return 0, miny0, maxy0, x, 1
            if (int(maxy0*cy) == int(maxy1*cy) and
                    int(miny0*cy) == int(miny1*cy)):
                return 0, miny0, maxy0, x, 0
        elif self.edge_hit[0][1] == 1 or self.edge_hit[0][1] == 3:
            maxx0, minx0 = self.mark_hit2_edge(1, 0, 2)
            maxx1, minx1 = self.mark_hit2_edge(3, 0, 2)
            if maxx0 == -1 and minx0 == -1:
                return 1, minx1, maxx1, y, 1
            if maxx1 == -1 and minx1 == -1:
                return 1, minx0, maxx0, y, 1
            if (int(maxx0*cx) == int(maxx1*cx) and
                    int(minx0*cx) == int(minx1*cx)):
                return 1, minx0, maxx0, y, 0

        return -1, 0, 0, 0

    def mark_hit2_edge(self, k, m1, m2):
        delta = 5
        cx, cy = self.canvas.GetClientSize()
        if (k == 1) | (k == 3):
            cx = cy
        hit = self.edge_hit
        hit2 = self.edge_hit2
        maxx = -1
        minx = -1
        for i in range(len(hit)):
            if hit[i][1] == k:
                a = self.area[hit[i][0]]
#            a = self.apply_pm_2_area(a)
                maxx = max([a[m1], a[m1]+a[m2]])
                minx = min([a[m1], a[m1]+a[m2]])
        check = True
        while check:
            check = False
            for i in range(len(hit2)):
                if hit2[i][1] == k:
                    if hit2[i][2]:
                        continue
                    a = self.area[hit2[i][0]]
                    if (abs(a[m1] - maxx)*cx < delta or
                        abs(a[m1]+a[m2] - maxx)*cx < delta or
                        abs(a[m1] - minx)*cx < delta or
                            abs(a[m1]+a[m2] - minx)*cx < delta):
                        hit2[i][2] = True
                        check = True
                        maxx = max([maxx, a[m1], a[m1]+a[m2]])
                        minx = min([minx, a[m1], a[m1]+a[m2]])
        return maxx, minx

    def distH(self, area_hit):
        # searching area
        areas = self._search_connecting_area(area_hit, True)
        # adjusting area
        w = sum([a1[2] for a1 in areas])
        w = w/len(areas)
        tmp = sorted([(a1[0], a1) for a1 in areas],  key=lambda x:x[0])
        x0 = tmp[0][0]
        i = 0
        for void, a1 in tmp:
            idx = self.area.index(a1)
            self.area[idx][2] = w
            self.area[idx][0] = x0 + w*i
            i = i+1
        # finish up
        request = [('m', k, a) for k, a in enumerate(self.area)]
        self._finish_up_area_edit(request=request)

    def distV(self, area_hit):
        # searching area
        areas = self._search_connecting_area(area_hit, False)
        # adjusting area
        h = sum([a1[3] for a1 in areas])
        h = h/len(areas)
        tmp = sorted([(a1[1], a1) for a1 in areas],  key=lambda x:x[0])
        y0 = tmp[0][0]
        i = 0
        for void, a1 in tmp:
            k = self.area.index(a1)
            self.area[k][3] = h
            self.area[k][1] = y0 + h*i
            i = i+1
        # finish up
        request = [('m', k, a) for k, a in enumerate(self.area)]
        self._finish_up_area_edit(request=request)

    def apply_left_only(self, area_hit):
        fig = self.figure
        f_page = fig.figobj
        if self.area.count(area_hit) == 0:
            return
        areas = self._search_connecting_area(area_hit, True)

        areas = [b[1] for b in
                 sorted([(a[0], a) for a in areas],  key=lambda x:x[0])]

        f_axes_arr, ac = self._checkup_edge_only_leftbottom(areas, 0)
        new_len = self._calc_axis_edge_only_newlen_bottomleft(
            f_axes_arr, 0, 1, 2)

        # apply new length
        request = []
        p0 = f_axes_arr[0].getp("area")[0]
        fig_page = f_axes_arr[0].get_figpage()
        for j in range(len(f_axes_arr)):
            f_axes = f_axes_arr[j]
            a = f_axes.get_area()
            a[0] = p0
            a[2] = new_len[j, 0]
            request.append(('m', fig_page.get_iaxes(f_axes), a))
            p0 = p0 + new_len[j, 0]

        # finish up
        self._finish_up_area_edit(request=request, ac=ac, name='left only')

    def apply_bottom_only(self, area_hit):

        if self.area.count(area_hit) == 0:
            return
        areas = self._search_connecting_area(area_hit, False)

        # sort area
        areas = [b[1] for b in
                 sorted([(a[1], a) for a in areas],  key=lambda x:x[0])]

        # set _edge_only
        f_axes_arr, ac = self._checkup_edge_only_leftbottom(areas, 1)

        new_len = self._calc_axis_edge_only_newlen_bottomleft(
            f_axes_arr, 3, 2, 3)
        # apply new length
        request = []
        p0 = f_axes_arr[0].getp("area")[1]
        fig_page = f_axes_arr[0].get_figpage()
        for j in range(len(f_axes_arr)):
            f_axes = f_axes_arr[j]
            a = f_axes.get_area()
            a[1] = p0
            a[3] = new_len[j, 0]
            request.append(('m', fig_page.get_iaxes(f_axes), a))
            p0 = p0 + new_len[j, 0]

        # finish up
        self._finish_up_area_edit(request=request, ac=ac, name='bottom only')

    def _calc_axis_edge_only_newlen_bottomleft(self, f_axes_arr, p1, p2, p3):
        '''
        p1 = 3, p2 = 2, p3=3 : bottom
        p1 = 0, p2 = 1, p3=2 : left
        '''
        # find the length of each section
        l = len(f_axes_arr)  # size of problem
        # (1) reset extra margin
        for j in range(l):
            f_axes_arr[j]._extra_margin[p1] = 0.0
        # (2) set extra margin for edge
        text_space = 0.05
        f_axes_arr[0]._extra_margin[p1] = text_space
        # (3) fill matrix
        import numpy as np
        M = np.zeros((l, l))
        for j in range(l-1):
            rect, defm, margin1 = f_axes_arr[j].calc_rect()
            rect, defm, margin2 = f_axes_arr[j+1].calc_rect()
            emargin1 = f_axes_arr[j]._extra_margin
            emargin2 = f_axes_arr[j+1]._extra_margin
            M[j, j] = (1 - margin1[p1] - margin1[p2]
                       - emargin1[p1] - emargin1[p2])
            M[j, j+1] = -(1 - margin2[p1] - margin2[p2]
                          - emargin2[p1] - emargin2[p2])
        d = 0
        for j in range(l):
            M[-1, j] = 1
            d = d + f_axes_arr[j].getp("area")[p3]
        a = np.zeros((l, 1))
        a[-1, 0] = d
        # (4) solve
        new_len = inv(M).dot(a)
        return new_len

    def _checkup_edge_only_leftbottom(self, areas, idx):
        '''
        idx  = 1 : bottom
        idx  = 0 : left
        '''
        fig = self.figure
        f_page = fig.figobj
        f_axes_arr = []
        ac = []
        for f_axes in f_page.walk_axes():
            if f_axes.getp("area") in areas:
                edge_only = f_axes.get_edge_only()
                if f_axes.getp("area") != areas[0]:
                    edge_only[idx] = True
                    ac.append(UndoRedoFigobjMethod(f_axes._artists[0],
                                                   'edge_only', edge_only))
                else:
                    edge_only[idx] = False
                    ac.append(UndoRedoFigobjMethod(f_axes._artists[0],
                                                   'edge_only', edge_only))
                f_axes_arr.append(f_axes)
        f_axes_arr = [b[1] for b in
                      sorted([(a.getp("area")[idx], a) for a in f_axes_arr], key=lambda x:x[0])]
        return f_axes_arr, ac

    def _finish_up_area_edit(self, request=None, ac=None, name='area'):
        self.SetCanvasValue(request=request, ac=ac, name=name)
        wx.CallAfter(self.SetEditorValue)
#       self.canvas.draw()

    def _search_connecting_area(self, area_hit, Flag):
        '''
        Flag = True  : horizontal connection
        Flag = Flase : vertical connection
        '''
        areas = [area_hit]
        hit = True
        while hit:
            hit = False
            for a1 in areas:
                for a2 in self.area:
                    if (not a2 in areas and
                            self._check_attached(a1, a2, Flag)):
                        areas.append(a2)
                        hit = True
        return areas

    def _check_attached(self, a1, a2, h=True):
        def check(a, b):
            return abs(a-b) < 3
        x1, y1, x2, y2 = self._area2boxv(a1)
        x10, y10, x20, y20 = self._area2boxv(a2)
        if (h and (check(y1, y10) and check(y2, y20)) and
                (check(x1, x20) or check(x2, x10))):
               return True
        if (not h and (check(x1, x10) and check(x2, x20)) and
                (check(y1, y20) or check(y2, y10))):
               return True

        return False

    def _search_nearby(self, a):
        x10, y10, x20, y20 = self._area2boxv(a)

        def check(a, b):
            return abs(a-b) < 3

        left = []  # area at the left of a
        right = []
        up = []
        down = []
        for k, a1 in enumerate(self.area):
            x1, y1, x2, y2 = self._area2boxv(a1)
            if check(x10, x2):
                left.append((k, a1[:]))
            elif check(x20, x1):
                right.append((k, a1[:]))
            elif check(y10, y2):
                down.append((k, a1[:]))
            elif check(y20, y1):
                up.append((k, a1[:]))
        return left, right, up, down

    def _area2xy(self, sec):
        # convert x0, y0, w, h to x, y
        x = [sec[0], sec[0]+sec[2], sec[0]+sec[2], sec[0],  sec[0]]
        y = [sec[1], sec[1], sec[1]+sec[3], sec[1]+sec[3], sec[1]]
        return x, y

    def _area2box(self, sec):
        # convert x0, y0, w, h to x0, y0, x1, y1
        return [sec[0], sec[1], sec[0]+sec[2], sec[1]+sec[3]]

    def _area2boxv(self, sec):
        h = self.figure.get_figheight()*self.figure.get_dpi()
        w = self.figure.get_figwidth()*self.figure.get_dpi()
        # convert x0, y0, w, h to x0, y0, x1, y1
        return [sec[0]*w, sec[1]*h,
                (sec[0]+sec[2])*w, (sec[1]+sec[3])*h]

    def _box2area(self, box):
        return [min([box[0], box[2]]), min([box[1], box[3]]),
                abs(box[0]-box[2]), abs(box[1]-box[3])]

    def _load_canvas_value(self):
        ifig_canvas = self.canvas
        if ifig_canvas is None:
            # if property edtior is not linked...
            return

        fig = self.figure
        f_page = fig.figobj

        self.area = []
        self.rect = []
        self.use_def_margin = []
        self.margin = []
        self.def_margin = f_page.getp("def_margin")
        self.page_margin = f_page._page_margin[:]
        self.nomargin = f_page.get_nomargin()
#       print  f_page.get_children()
        for name, f_axes in f_page.get_children():
            if not isinstance(f_axes, FigAxes):
                continue
            area = f_axes.get_area()
            self.area.append(area)
            r1, c1, m1 = f_axes.calc_rect(ignore_pagemargin=True)
            self.rect.append(r1)
            self.margin.append(m1)
            self.use_def_margin.append(c1)
        if self.area_hit == None:
            if len(self.area) != 0:
                self.area_hit = self.area[0]
#       self.draw()

    def SetCanvasValue(self, axes=None, request=None, ac=None, name='area'):
        ifig_canvas = self.canvas
        if request is None:
            ifig_canvas.set_area(self.area)
            ifig_canvas.draw()
        else:
            send_area_request(ifig_canvas, axes=axes,
                              request=request, ac=ac, name=name)
#       ifig_canvas.draw()

    def SetEditorValue(self, axes=None):
        self._load_canvas_value()
