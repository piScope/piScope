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

import wx
import weakref
import numpy as np
from matplotlib.lines import Line2D

from ifigure.mto.fig_axes import FigAxes
#from ifigure.widgets.primitive_widgets import margin_widget, marginp_widget
from ifigure.widgets.margin_widget import MarginWidget, MarginpWidget
from ifigure.utils import geom as geom_util
import ifigure.events
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
from ifigure.utils.edit_list import ScrolledEditListPanel, EditListPanel, EDITLIST_CHANGED
from wx import ScrolledWindow as SP
from numpy.linalg import inv


from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import UndoRedoGroupUngroupFigobj
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('SectionEditor')


class section_editor(wx.Panel):

    def __init__(self, parent):
        super(section_editor, self).__init__(parent)

        self.area = []
        self.rect = []

        self.use_def_margin = []
        self.area_hit = None
        self.page_margin = [0, 0, 0, 0]
        self.nomargin = False

        notebook = wx.Notebook(self)

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)

        # nb1=wx.Panel(notebook)
        nb1 = SP(notebook)
        nb1.SetScrollRate(0, 5)
        self.nb1 = nb1
        notebook.AddPage(nb1, "Section")
        pansizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(pansizer)
        pansizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 0)

        minisizer = wx.BoxSizer(wx.VERTICAL)
        nb1.SetSizer(minisizer)
        self.st1 = wx.StaticText(nb1, label="Axis Margin")
        self.sl_margin = MarginWidget(nb1)
        minisizer.Add(self.st1, 0, wx.ALL, 2)
        minisizer.Add(self.sl_margin, 0, wx.ALL | wx.EXPAND, 1)
        self.st2 = wx.StaticText(nb1, label="Page Margin ")
        self.sl_marginp = MarginpWidget(nb1)
        minisizer.Add(self.st2, 0, wx.ALL, 2)
        minisizer.Add(self.sl_marginp, 0, wx.ALL | wx.EXPAND,  1)

        s_fontsize = {"style": wx.TE_PROCESS_ENTER,
                      "choices": ["7", "8", "9", "10", "11", "12", "14",
                                  "16", "18", "20", "22", "24", "26", "28",
                                  "36", "48", "72"]}
        s_boxwidth = {"style": wx.TE_PROCESS_ENTER,
                      "choices": ["0.5", "1.0", "1.5", "2.0", "2.5"]}
        list = [("title",  '',  115, {}),
                #                ("size", "14", 104, s_fontsize),
                ("bg color",      'red',  6, {}),
                (None, "default size", 102, {}),
                ("title", "14", 104, s_fontsize),
                ("tick label",  "12",  104,  s_fontsize),
                ("axis title",  "12",  104,  s_fontsize),
                ("axis width", "1.0",  104,  s_boxwidth),
                ("tick width", "1.0",  104,  s_boxwidth)]
        self.elp = ScrolledEditListPanel(notebook, list)
        notebook.AddPage(self.elp, "title/size")

        s1 = {"style": wx.CB_READONLY,
              "choices": ["serif", "sans-serif",
                          "cursive", "fantasy", "monospace"]}
        s2 = {"style": wx.CB_READONLY,
              "choices": ["ultralight", "light", "normal",
                          "regular", "book", "medium",
                          "roman", "semibold", "demibold",
                          "demi", "bold", "heavy",
                          "extra bold", "black"]}
        s3 = {"style": wx.CB_READONLY,
              "choices": ["normal", "italic", "oblique"]}
        l = [(None, "axis", 102, {}),
             ("font",  "serif", 4,  s1),
             ("weight", "roman", 4,  s2),
             ("style",  "normal", 4,  s3),
             (None, "title", 102, {}),
             ("font",  "serif", 4,  s1),
             ("weight", "roman", 4,  s2),
             ("style",  "normal", 4,  s3), ]

        self.elp2 = ScrolledEditListPanel(notebook,  l)
        notebook.AddPage(self.elp2, "font")

        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
#       self.elp2.Bind(EDITLIST_CHANGED, self.onEL_Changed2)

        self.events = wx.EVT_BUTTON
        self.Hide()
        self.parent = parent
        self.Fit()
        self. _load_canvas_value()

    def _load_canvas_value(self):
        ifig_canvas = self.parent.get_canvas()
        if ifig_canvas is None:
            # if property edtior is not linked...
            return

        fig = ifig_canvas.get_figure()
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

    def SetCanvasValue(self, axes=None, request=None, ac=None, name='area'):
        ifig_canvas = self.parent.get_canvas()
        if request is None:
            ifig_canvas.set_area(self.area)
        else:
            fig_page = ifig_canvas._figure.figobj
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

            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(ac,
                                                           menu_name=name)

        ifig_canvas.draw()

    def set_margin_show(self, value):
        if value:
            self.sl_margin.Enable()
            self.sl_marginp.Enable()
            self.st1.Enable()
            self.st2.Enable()
        else:
            self.sl_margin.Disable()
            self.sl_marginp.Disable()
            self.st1.Disable()
            self.st2.Disable()

    def SetEditorValue(self, axes=None):
        self._load_canvas_value()
        ifig_canvas = self.parent.get_canvas()
        if ifig_canvas is None:
            # if property edtior is not linked...
            return
        if (self.area_hit is not None):
            self.nb1.Enable(True)
            if self.area_hit in self.area:
                idx = self.area.index(self.area_hit)
                use_def = self.use_def_margin[idx]
                if use_def:
                    m = self.def_margin
                else:
                    m = self.margin[idx]
            else:
                idx = -1

            if self.nomargin:
                self.set_margin_show(False)
            else:
                self.set_margin_show(True)
                if idx > -1:
                    self.sl_margin.SetEditorValue(use_def, m)
                self.sl_marginp.SetEditorValue(self.page_margin)
        else:
            self.nb1.Enable(False)

        fig = ifig_canvas.get_figure()
        value = self.elp.GetValue()
        value[0] = fig.figobj.get_suptitle_labelinfo()
#       value[1] = fig.figobj.get_suptitle_size()
        value[1] = fig.get_facecolor()
        value[3] = fig.figobj.getp("title_size")
        value[4] = fig.figobj.getp("ticklabel_size")
        value[5] = fig.figobj.getp("axeslabel_size")
        value[6] = fig.figobj.getp("axesbox_width")
        value[7] = fig.figobj.getp("axestick_width")
        self.elp.SetValue(value)
        value = self.elp2.GetValue()
        value[1] = fig.figobj.getp("tick_font")
        value[2] = fig.figobj.getp("tick_weight")
        value[3] = fig.figobj.getp("tick_style")
        value[5] = fig.figobj.getp("title_font")
        value[6] = fig.figobj.getp("title_weight")
        value[7] = fig.figobj.getp("title_style")

        self.elp2.SetValue(value)

    def update_panel(self):
        #       dprint1('update panel')
        self.SetEditorValue()
        return
        self._load_canvas_value()
        if self.nomargin:
            self.set_margin_show(False)
        else:
            self.set_margin_show(True)

        self.draw()

    def onTD_Selection(self, evt):
        if self.IsShown():
            td = evt.GetTreeDict()
            if isinstance(td, FigAxes):
                ax = td
            elif isinstance(td.get_parent(), FigAxes):
                ax = td.get_parent()
            else:
                return
            area = ax.getp("area")
            self.area_hit = area
            self.SetEditorValue()
#          print "do something on section editor (selection)", td, evt.selections

    def onTD_ShowPage(self, evt):
        if self.IsShown():
            td = evt.GetTreeDict()
            self.area_hit = None
            self.SetEditorValue()
#           "do something on section editor (showpage)", td, evt

    def onEL_Changed(self, evt):
        ifig_canvas = self.parent.get_canvas()
        fig = ifig_canvas.get_figure()

        menu_name = 'page property'
        if evt.elp == self.elp:
            value = self.elp.GetValue()
            v = value[evt.widget_idx]
            if evt.widget_idx == 1:
                action = UndoRedoArtistProperty(fig,
                                                "facecolor",
                                                v)
                menu_name = 'background color'
            elif evt.widget_idx == 0:
                action = UndoRedoFigobjMethod(fig,
                                              "suptitle_labelinfo",
                                              v)
                menu_name = 'suptitle'

#               fig.figobj.set_suptitle(str(v))
            elif evt.widget_idx == 1:
                action = UndoRedoFigobjMethod(fig,
                                              "suptitle_size",
                                              float(v))
                menu_name = 'suptitle size'

#               fig.figobj.set_suptitle_size(float(v))
            elif evt.widget_idx == 3:
                action = UndoRedoFigobjProperty(fig,
                                                "title_size",
                                                float(v), nodelete=True)
                menu_name = 'title size'
            elif evt.widget_idx == 4:
                action = UndoRedoFigobjProperty(fig,
                                                "ticklabel_size",
                                                float(v), nodelete=True)
                menu_name = 'tick label size'
            elif evt.widget_idx == 5:
                action = UndoRedoFigobjProperty(fig,
                                                "axeslabel_size",
                                                float(v), nodelete=True)
                menu_name = 'axes label size'
            elif evt.widget_idx == 6:
                action = UndoRedoFigobjProperty(fig,
                                                "axesbox_width",
                                                float(v), nodelete=True)
                menu_name = 'axes box width'
            elif evt.widget_idx == 7:
                action = UndoRedoFigobjProperty(fig,
                                                "axestick_width",
                                                float(v), nodelete=True)
                menu_name = 'axes tick width'

#               fig.figobj.setp("axestick_width", float(v))
        elif evt.elp == self.elp2:
            value = self.elp2.GetValue()
            v = value[evt.widget_idx]
            if evt.widget_idx == 1:
                action = UndoRedoFigobjProperty(fig, "tick_font", str(v),
                                                nodelete=True)
                menu_name = 'tick font'
            elif evt.widget_idx == 2:
                action = UndoRedoFigobjProperty(fig, "tick_weight", str(v),
                                                nodelete=True)
                menu_name = 'tick weight'
            elif evt.widget_idx == 3:
                action = UndoRedoFigobjProperty(fig, "tick_style", str(v),
                                                nodelete=True)
                menu_name = 'tick style'
            elif evt.widget_idx == 5:
                action = UndoRedoFigobjProperty(fig, "title_font", str(v),
                                                nodelete=True)
                menu_name = 'title font'
            elif evt.widget_idx == 6:
                action = UndoRedoFigobjProperty(fig, "title_weight", str(v),
                                                nodelete=True)
                menu_name = 'title weight'
            elif evt.widget_idx == 7:
                action = UndoRedoFigobjProperty(fig, "title_style", str(v),
                                                nodelete=True)
                menu_name = 'title style'

        window = ifig_canvas.GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.make_entry([action], menu_name=menu_name,
                        draw_request='draw_all')

#       ifig_canvas.draw_all()

    def onTD_Replace(self, evt):
        pass

    def onNBChanged(self, evt):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            self.GetTopLevelParent().deffered_force_layout()

        evt.Skip()
