#
#  Name   :primitive_widgets
#
#          this module provide a collection of widgets
#
#          there are two groups of widget defined in
#          this file
#
#          1) primitive widgets
#             this is a collection of generic widgets
#             those widgets should hava
#                set_value/get_value procedure
#                self.events : list of events to be returned
#             also, event must be skipped.
#
#          2) widgets for ifigure
#             these are made by combining the above primitives.
#
#             SetCanvasValue/SetEditorValue needs to be implemented.
#

#
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

from ifigure.widgets.custom_double_slider import CustomDoubleSlider, EVT_CDS_CHANGED
import wx
import random
import os
import ifigure
import ifigure.utils.cbook as cbook
#from ifigure.widgets.base_widget import base_widget
from matplotlib.artist import getp as mpl_getp
from matplotlib.artist import setp as mpl_setp
from ifigure.utils.edit_list import EditListEvent, EditorChanged

dirname = os.path.dirname(ifigure.__file__)


class primitive_widgets(wx.Panel):
    def __init__(self, parent):
        super(primitive_widgets, self).__init__(parent)

        from ifigure.utils.wx3to4 import FlexGridSizer
        sizer = FlexGridSizer(1, 2)

        self.SetSizer(sizer)
        self.Controls = []
        self.events = None
### list events needs to be handled ###
        self.event_obj = None

    def get_control_command(self):
        #        obj=self.event_obj.GetEventObject()
        for ctl in self.Controls:
            if ctl["obj"] is self.event_obj:
                return ctl

    def check_if_need2expand(self):
        sizer = self.GetSizer()
        size = sizer.CalcRowsCols()
        r = sizer.GetRows()

        if size[0] == r:
            #          print 'expanding'
            sizer.SetRows(r+1)

    def add_bitmap_buttons(self, title, ftitle, names, pname):

        topsizer = self.GetSizer()

        gridsizer = wx.GridSizer(10, 4)

        st1 = wx.StaticText(self, label=title)
        topsizer.Add(st1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)

        from ifigure.ifigure_config import icondir
        for name in names:
            imageFile = os.path.join(icondir, 'image',
                                     ftitle+'_'+name+'.png')
            btn = wx.BitmapButton(self, bitmap=wx.Bitmap(imageFile))
            gridsizer.Add(btn, 0, wx.ALL, 0)
            self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
            self.Controls.append(
                {"obj": btn, "property": pname, "value": name})
        topsizer.Add(gridsizer, 0, wx.ALL, 1)

    def add_sample(self):
        colors = ["red", "blue", "gray", "yellow", "green"]
        self.SetBackgroundColour(random.choice(colors))

        btn = wx.Button(self, label="Press Me")
        sizer = self.GetSizer()
        sizer.Add(btn, 0, wx.ALL, 5)

    def add_text_label(self, parent=None, label="", style=wx.TE_PROCESS_ENTER):
        topsizer = parent.GetSizer()
        st1 = wx.StaticText(parent, label=label)
        ct1 = wx.TextCtrl(parent, value="", style=style)
        topsizer.Add(st1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        topsizer.Add(ct1, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 1)
        return ct1

    def onEdit(self, event):

        event.SetEventObject(self)
        event.Skip()
        return
        self.event_obj = event.GetEventObject()
        evt = EditListEvent(EditorChanged, wx.ID_ANY)
        evt.SetEventObject(self)
        evt.elp = self
        evt.widget_idx = 0
        handler = self.GetParent()
        handler.ProcessEvent(evt)

    def set_value(self, value):
        pass

    def get_value(self):
        return None


class two_sliders_widget(wx.Panel):
    def __init__(self, parent, minV=0., maxV=1., val1=0.5, val2=0.5, res=0.01, position=(10, 10), size=(100, 20)):
        super(two_sliders_widget, self).__init__(parent)

        self.minV = minV
        self.maxV = maxV
        self.res = res
        self.datamax = (self.maxV-self.minV)/self.res
        self.s1 = wx.Slider(self, wx.ID_ANY, self._val2data(val1), 0,
                            self.datamax, position, (120, -1))
        self.s2 = wx.Slider(self, wx.ID_ANY, self._val2data(val2), 0,
                            self.datamax, position, (120, -1))

        sizer = wx.BoxSizer(wx.VERTICAL)
#        sizer2=wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.s1, 1, wx.EXPAND | wx.ALL, 2)
        sizer.Add(self.s2, 1, wx.EXPAND | wx.ALL, 2)
#        sizer.Add(sizer2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_SLIDER, self._sliderUpdate, self.s1)
        self.Bind(wx.EVT_SLIDER, self._sliderUpdate, self.s2)
        self.events = wx.EVT_SLIDER
        self._val = [val1, val2]

    def set_value(self, value):
        self.s1.SetValue(self._val2data(value[0]))
        self.s2.SetValue(self._val2data(value[1]))

    def get_value(self):
        return [self._data2val(self.s1.GetValue()),
                self._data2val(self.s2.GetValue())]

    def _val2data(self, x):
        return (x-self.minV)/(self.maxV-self.minV)*self.datamax

    def _data2val(self, data):
        return (self.maxV-self.minV)*data/self.datamax+self.minV

    def _sliderUpdate(self, event):
        sl = event.GetEventObject()
        val = self.get_value()
        if val[0] > val[1]:
            if sl is self.s1:
                self.s2.SetValue(self._val2data(val[0])+1)
            else:
                self.s1.SetValue(self._val2data(val[1])-1)

        do_skip = False
        if sl is self.s1:
            if self._val[0] == val[0]:
                do_skip = True
        else:
            if self._val[1] == val[1]:
                do_skip = True
        self._val = val

        if do_skip:
            event.SetEventObject(self)
            event.Skip()

#
#   compound widget specifically designed for ifigure
#   these widgets has its own SetEditorValue/SetCanvas
#   Value/onEdit implementation
#


#
#    Margin widget
#


class margin_widget(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY, *args, **kargs):
        super(margin_widget, self).__init__(parent, id, *args, **kargs)
        self.use_def = wx.CheckBox(self, -1, 'Use Global Setting',
                                   (10, 10))

        st1 = wx.StaticText(self, label="   X  ")
        self.h_slider = CustomDoubleSlider(self, wx.ID_ANY)
        st2 = wx.StaticText(self, label="   Y  ")
        self.v_slider = CustomDoubleSlider(self, wx.ID_ANY)

        big_sizer = wx.BoxSizer(wx.VERTICAL)
        big_sizer2 = wx.BoxSizer(wx.HORIZONTAL)

        from ifigure.utils.wx3to4 import FlexGridSizer
        sizer = FlexGridSizer(2, 2)

        sizer.AddGrowableCol(1)
        sizer.Add(st1, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.h_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        sizer.Add(st2, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.v_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        big_sizer.Add(self.use_def, 0)
        big_sizer.Add(sizer, 1, wx.EXPAND)
        big_sizer2.Add(big_sizer, 1, wx.EXPAND)
        self.SetSizer(big_sizer2, wx.EXPAND)

        self.Bind(EVT_CDS_CHANGED, self.onEvent)
#        self.Bind(wx.EVT_SCROLL_CHANGED, self.onEvent)
        self.Bind(wx.EVT_CHECKBOX, self.onEvent)

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
        idx = se.area.index(se.area_hit)
        f_axes = f_page.get_child(idx)
        if c:
            f_axes.setp("use_def_margin", True)
        else:
            f_axes.setp("use_def_margin", False)

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
        if c:
            f_page.setp("def_margin", [a[0], 1.-a[1], b[0], 1.-b[1]])
            f_page.reset_axesbmp_update()
        else:
            f_axes.setp("margin", [a[0], 1.-a[1], b[0], 1.-b[1]])
            f_axes.set_bmp_update(False)

        f_page.realize()
        canvas.draw()
        self.GetParent().GetParent().GetParent().SetEditorValue()


class marginp_widget(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY, *args, **kargs):
        super(marginp_widget, self).__init__(parent, id, *args, **kargs)

#        self.use_def= wx.CheckBox(self, -1, 'Use Global Setting',
#                                  (10, 10))

        st1 = wx.StaticText(self, label="   X  ")
        self.h_slider = CustomDoubleSlider(self, wx.ID_ANY)
        st2 = wx.StaticText(self, label="   Y  ")
        self.v_slider = CustomDoubleSlider(self, wx.ID_ANY)

        big_sizer = wx.BoxSizer(wx.VERTICAL)
        big_sizer2 = wx.BoxSizer(wx.HORIZONTAL)

        from ifigure.utils.wx3to4 import FlexGridSizer
        sizer = FlexGridSizer(2, 2)
        sizer.AddGrowableCol(1)
        sizer.Add(st1, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.h_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        sizer.Add(st2, 0, wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(self.v_slider, 1, wx.EXPAND |
                  wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        big_sizer.Add(sizer, 1, wx.EXPAND)
        big_sizer2.Add(big_sizer, 1, wx.EXPAND)
        self.SetSizer(big_sizer2, wx.EXPAND)

        self.Bind(EVT_CDS_CHANGED, self.onEvent)
#        self.Bind(wx.EVT_SCROLL_CHANGED, self.onEvent)

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
        f_page._page_margin = [a[0], 1.-a[1], b[0], 1.-b[1]]
        for f_axes in f_page.walk_axes():
            f_axes.set_bmp_update(False)
        f_page.realize()
        canvas.draw()
        self.GetParent().GetParent().GetParent().SetEditorValue()
