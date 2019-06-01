#
#    Margin widget
#
import wx
from ifigure.widgets.custom_double_slider import CustomDoubleSlider, EVT_CDS_CHANGED

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import UndoRedoGroupUngroupFigobj
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty

from ifigure.utils.wx3to4 import GridSizer, FlexGridSizer


class MarginWidget(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY, *args, **kargs):
        super(MarginWidget, self).__init__(parent, id, *args, **kargs)
        self.use_def = wx.CheckBox(self, -1, 'Use Global Setting',
                                   (10, 10))

        self.st1 = wx.StaticText(self, label="   X  ")
        self.h_slider = CustomDoubleSlider(self, wx.ID_ANY)
        self.st2 = wx.StaticText(self, label="   Y  ")
        self.v_slider = CustomDoubleSlider(self, wx.ID_ANY)

        big_sizer = wx.BoxSizer(wx.VERTICAL)
        big_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer = FlexGridSizer(2, 2)
        sizer.AddGrowableCol(1)
        sizer.Add(self.st1, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.h_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        sizer.Add(self.st2, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.v_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        big_sizer.Add(self.use_def, 0)
        big_sizer.Add(sizer, 1, wx.EXPAND)
        big_sizer2.Add(big_sizer, 1, wx.EXPAND)
        self.SetSizer(big_sizer2, wx.EXPAND)

        self.Bind(EVT_CDS_CHANGED, self.onEvent)
#        self.Bind(wx.EVT_SCROLL_CHANGED, self.onEvent)
        self.Bind(wx.EVT_CHECKBOX, self.onEvent)
        self.Fit()

    def Disable(self):
        self.use_def.Disable()
        self.st1.Disable()
        self.st2.Disable()
        self.h_slider.Disable()
        self.v_slider.Disable()

    def Enable(self):
        self.use_def.Enable()
        self.st1.Enable()
        self.st2.Enable()
        self.h_slider.Enable()
        self.v_slider.Enable()

    def onEvent(self, event):
        if event.GetEventObject() is self.use_def:
            self.SetCanvasValue2()
            return
        self.SetCanvasValue()
        return

    def SetEditorValue(self, use_def, m):
        self.use_def.SetValue(use_def)
        self.h_slider.SetValue([m[0], 1.-m[1]])
        self.v_slider.SetValue([m[2], 1.-m[3]])

    def SetCanvasValue2(self, artist=None):
        a = self.h_slider.GetValue()
        b = self.v_slider.GetValue()
        c = self.use_def.IsChecked()

        se = self.GetParent().GetParent().GetParent()
        pe = se.GetParent()
        canvas = pe.get_canvas()

        f_page = (canvas.get_figure()).figobj
        if se.area_hit in se.area:
            idx = se.area.index(se.area_hit)
        else:
            se.area_hit = se.area[0]
            idx = 0

        f_axes = f_page.get_child(idx)
        if f_axes is None:
            return
        ac = [UndoRedoFigobjProperty(f_axes._artists[0],
                                     'use_def_margin', c), ]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(ac,
                                                       menu_name='use default margin')
        wx.CallAfter(self.GetParent().GetParent().GetParent().SetEditorValue)
        return
        f_axes.setp("use_def_margin", c)
        f_page.realize()
        canvas.draw()
        self.GetParent().GetParent().GetParent().SetEditorValue()

    def SetCanvasValue(self, artist=None):
        a = self.h_slider.GetValue()
        b = self.v_slider.GetValue()
        c = self.use_def.IsChecked()

        se = self.GetParent().GetParent().GetParent()
        pe = se.GetParent()
        canvas = pe.get_canvas()

        f_page = (canvas.get_figure()).figobj
        idx = se.area.index(se.area_hit)
        f_axes = f_page.get_child(idx)

        ac = []
        if c:
            ac.append(UndoRedoFigobjMethod(canvas.get_figure(),
                                           'def_margin',
                                           [a[0], 1.-a[1], b[0], 1.-b[1]]))
        else:
            ac.append(UndoRedoFigobjMethod(f_axes._artists[0],
                                           'margin',
                                           [a[0], 1.-a[1], b[0], 1.-b[1]]))
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(ac,
                                                       menu_name='margin')
        wx.CallAfter(self.GetParent().GetParent().GetParent().SetEditorValue)


class MarginpWidget(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, *args, **kargs):
        super(MarginpWidget, self).__init__(parent, id, *args, **kargs)

#        self.use_def= wx.CheckBox(self, -1, 'Use Global Setting',
#                                  (10, 10))

        self.st1 = wx.StaticText(self, label="   X  ")
        self.h_slider = CustomDoubleSlider(self, wx.ID_ANY)
        self.st2 = wx.StaticText(self, label="   Y  ")
        self.v_slider = CustomDoubleSlider(self, wx.ID_ANY)

        big_sizer = wx.BoxSizer(wx.VERTICAL)
        big_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer = FlexGridSizer(2, 2)
        sizer.AddGrowableCol(1)
        sizer.Add(self.st1, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.h_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        sizer.Add(self.st2, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.v_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        big_sizer.Add(sizer, 1, wx.EXPAND)
        big_sizer2.Add(big_sizer, 1, wx.EXPAND)
        self.SetSizer(big_sizer2, wx.EXPAND)

        self.Bind(EVT_CDS_CHANGED, self.onEvent)
        self.Fit()
#        self.Bind(wx.EVT_SCROLL_CHANGED, self.onEvent)

    def Disable(self):
        self.st1.Disable()
        self.st2.Disable()
        self.h_slider.Disable()
        self.v_slider.Disable()

    def Enable(self):
        self.st1.Enable()
        self.st2.Enable()
        self.h_slider.Enable()
        self.v_slider.Enable()

    def onEvent(self, event):
        self.SetCanvasValue()

    def SetEditorValue(self, m):
        self.h_slider.SetValue([m[0], 1.-m[1]])
        self.v_slider.SetValue([m[2], 1.-m[3]])

    def SetCanvasValue(self, artist=None):
        a = self.h_slider.GetValue()
        b = self.v_slider.GetValue()

        se = self.GetParent().GetParent().GetParent()
        pe = se.GetParent()
        canvas = pe.get_canvas()

        f_page = (canvas.get_figure()).figobj
        ac = []
        ac.append(UndoRedoFigobjMethod(canvas.get_figure(),
                                       'page_margin',
                                       [a[0], 1.-a[1], b[0], 1.-b[1]]))
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(ac,
                                                       menu_name='page margin')
        wx.CallAfter(self.GetParent().GetParent().GetParent().SetEditorValue)
