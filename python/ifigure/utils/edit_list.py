from __future__ import print_function
#
#   Edit list
#
#   A utility to ask user input by dialog
#   It also define all banch of gui elements
#
#   Input :  [["label", value, mode, {setting}]]
#
#   Mode  :   0 : textctrl
#             1 : radio button
#               setting = {"values":['on', off']}
#             2:  text label (static text)
#             3:  check box
#               setting = {"text":'check box label'}
from ifigure.widgets.miniframe_with_windowlist import WithWindowList_MixIn
from collections import OrderedDict
from wx import ScrolledWindow as SP
from ifigure.utils.wx3to4 import GridSizer, FlexGridSizer, wxBitmapComboBox, wxEmptyImage, TextEntryDialog, panel_SetToolTip
import ifigure.utils.debug as debug
import wx
from wx.richtext import RichTextCtrl, RE_MULTILINE
import sys
import six
import os
import ifigure
import wx.stc as stc
import numpy as np
from ifigure.numerical_function import *
import ifigure.utils.cbook as cbook
from ifigure.utils.cbook import isstringlike, isnumber
from ifigure.widgets.custom_double_slider import CustomSingleSlider, CustomDoubleSlider
from ifigure.widgets.custom_double_slider import EVT_CDS_CHANGED, EVT_CDS_CHANGING
import weakref
import base64
use_agw = False
if use_agw:
    import wx.lib.agw.aui as aui
else:
    import wx.aui as aui


dprint1, dprint2, dprint3 = debug.init_dprints('EditList')

bitmap_size = (22, 14)
b64encode = base64.urlsafe_b64encode

EditorChanged = wx.NewEventType()
EDITLIST_CHANGED = wx.PyEventBinder(EditorChanged, 1)
EditorChanging = wx.NewEventType()
EDITLIST_CHANGING = wx.PyEventBinder(EditorChanging, 1)
EditorSetFocus = wx.NewEventType()
EDITLIST_SETFOCUS = wx.PyEventBinder(EditorSetFocus, 1)


def call_send_event(obj, evt):
    if hasattr(obj.GetParent(), "send_event"):
        obj.GetParent().send_event(obj, evt)
    elif hasattr(obj.GetParent().GetParent(), "send_event"):
        obj.GetParent().GetParent().send_event(obj, evt)


def call_send_changing_event(obj, evt):
    if hasattr(obj.GetParent(), "send_changing_event"):
        obj.GetParent().send_changing_event(obj, evt)
    elif hasattr(obj.GetParent().GetParent(), "send_changing_event"):
        obj.GetParent().GetParent().send_changing_event(obj, evt)


def call_send_setfocus_event(obj, evt):
    if hasattr(obj.GetParent(), "send_setfocus_event"):
        obj.GetParent().send_setfocus_event(obj, evt)
    elif hasattr(obj.GetParent().GetParent(), "send_setfocus_event"):
        obj.GetParent().GetParent().send_setfocus_event(obj, evt)


class EditListEvent(wx.PyCommandEvent):
    """
    event for treedict to request edit a file
    """

    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)


class Panel(wx.Panel):
    """
    a panel to place edit_list widgets
    """

    def __init__(self, *args, **kargs):
        super(Panel, self).__init__(*args, **kargs)

    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        for c in self.GetChildren():
            c.Enable(value)


class Panel0(wx.Panel):
    """
    a panel to place edit_list widgets
    """

    def send_event(self, obj, evt):
        self.GetParent().send_event(obj, evt)

    def send_changing_event(self, evtobj, evt0):
        self.GetParent().send_changing_event(evtobj, evt0)

    def send_setfocus_event(self, evtobj, evt0):
        self.GetParent().send_setfocus_event(evtobj, evt0)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        for c in self.GetChildren():
            c.Enable(value)


class CollapsiblePane0(wx.CollapsiblePane):
    def __init__(self, *args, **kwargs):
        self._keepwidth = kwargs.pop("keepwidth", False)

        wx.CollapsiblePane.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.onCPChanged)

        self._size = self.Size
        self._def_size = 20

    def onCPChanged(self, evt):
        tpx, tpy = self.GetTopLevelParent().GetSize()
        px, py = self.GetParent().GetSize()
        p = self.GetPane()
        ysize = p.GetSizer().GetMinSize()[1]

        if self.IsCollapsed():
            mysize = (p.Size[0], 0)
            mypsize = (p.Size[0], self._def_size)

            p.SetSize(mysize)
            p.GetParent().SetSize(mypsize)

            self.GetParent().SetSize((px, py-ysize))
            if self._keepwidth:
                self.GetTopLevelParent().SetSize((tpx, tpy-ysize))

        else:
            mysize = (p.Size[0], ysize)
            mypsize = (p.Size[0], p.GetParent().Size[1] + ysize)

            self._def_size = p.GetParent().Size[1]

            p.SetSize(mysize)
            p.GetParent().SetSize(mypsize)

            self.GetParent().SetSize((px, py+ysize))
            if self._keepwidth:
                self.GetTopLevelParent().SetSize((tpx, tpy+ysize))

        self.GetParent().Layout()
        self.GetTopLevelParent().Layout()

    def send_event(self, obj, evt):
        self.GetParent().send_event(obj, evt)

    def GetPane(self):
        def send_event(_x, obj, evt, cp):
            self.GetParent().send_event(obj, evt)

        def send_changing_event(_x, evtobj, evt0):
            self.GetParent().send_changing_event(evtobj, evt0)

        def send_setfocus_event(_x, evtobj, evt0):
            self.GetParent().send_setfocus_event(evtobj, evt0)

        p = wx.CollapsiblePane.GetPane(self)
        p.send_event = send_event
        p.send_changing_event = send_changing_event
        p.send_setfocus_event = send_setfocus_event
        return p


class DialogButton(wx.Button):
    def __init__(self, *args, **kargs):
        setting = kargs.pop("setting", {})
        func = setting.pop('func', None)
        label = setting.pop('label', 'Default')
        wx.Button.__init__(self, *args, **kargs)
        self.Bind(wx.EVT_BUTTON, self.onSelect)
        if func is not None:
            self._handler = func(self)
        else:
            self._handler = None
        self.SetLabel(label)

    def onSelect(self, ev):
        if self._handler is not None:
            self._handler.on_button(ev)
        ev.Skip()

    def GetValue(self):
        if self._handler is None:
            print('DialogButton handler is None')
        else:
            return self._handler.get_value()

    def SetValue(self, value):
        if self._handler is None:
            print('DialogButton handler is None')
        else:
            return self._handler.set_value(value)


class FunctionButton(wx.Button):
    def __init__(self, *args, **kargs):
        setting = kargs.pop("setting", {})
        func = setting.pop('func', None)
        label = setting.pop('label', 'Default')
        style = setting.pop('style', 0)
        self.send_event = setting.pop('sendevent', False)
        kargs['style'] = style
        wx.Button.__init__(self, *args, **kargs)
        self.Bind(wx.EVT_BUTTON, self.onSelect)
        if func is not None:
            self._handler = func
        else:
            self._handler = None
        self._handler_obj = None

        self._call_method = False
        self.SetLabel(" " + label + " ")  # apparently I need white space...

    def GetValue(self):
        pass

    def SetValue(self, v):
        self._handler_obj = v

    def onSelect(self, ev):
        if self._call_method:
            if hasattr(self._handler_obj, self._handler):
                _handler = getattr(self._handler_obj, self._handler)
            else:
                _handler = None
        else:
            _handler = self._handler
        if _handler is not None:
            _handler(ev)
            if self.send_event:
                self.GetParent().send_event(self, ev)
        ev.Skip()


class FunctionButtons(Panel):
    def __init__(self, *args, **kwargs):
        setting = kwargs.pop('setting', [])
        buttons = setting.pop('buttons', [])
        super(FunctionButtons, self).__init__(*args, **kwargs)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        for s in buttons:
            bt = FunctionButton(self, wx.ID_ANY,
                                setting=s)

            self.GetSizer().Add(bt, 0, wx.EXPAND | wx.ALL, 2)

    def GetValue(self):
        pass

    def SetValue(self, v):
        pass


class LabelPanel(Panel):
    def __init__(self, *args, **kargs):
        if "setting" in kargs:
            setting = kargs["setting"]
            del kargs["setting"]
        super(LabelPanel, self).__init__(*args, **kargs)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.tc = TextCtrlCopyPaste(self, wx.ID_ANY, '',
                                    style=wx.TE_PROCESS_ENTER)
        self.tc._use_escape = False
        bt = wx.Button(self, wx.ID_ANY, 'Style...')
        self.GetSizer().Add(self.tc, 1, wx.EXPAND | wx.ALL, 1)
        self.GetSizer().Add(bt, 1, wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.onSelect, bt)

        self.val = ['', 'k', 'san-serif',
                    'normal', 'normal',  12]

    def onSelect(self, evt):
        if self.val[0] is None:
            return
        s1 = {"style": wx.CB_READONLY,
              "choices": ["serif", "sans-serif",
                          "cursive", "fantasy", "monospace", "default"]}
        s2 = {"style": wx.CB_READONLY,
              "choices": ["ultralight", "light", "normal",
                          "regular", "book", "medium",
                          "roman", "semibold", "demibold",
                          "demi", "bold", "heavy",
                          "extra bold", "black", "default"]}
        s3 = {"style": wx.CB_READONLY,
              "choices": ["normal", "italic", "oblique", "default"]}
        s4 = self._s4()
        l = [["color", self.val[1], 6,  None],
             ["font",  self.val[2], 4,  s1],
             ["weight", self.val[3], 4,  s2],
             ["style", self.val[4], 4,  s3],
             ["size",  self.val[5], 104,  s4]]

        dia = EditListDialog(self, wx.ID_ANY, '', l)
        val = dia.ShowModal()
        value = dia.GetValue()
        dia.Destroy()
        if val != wx.ID_OK:
            return
        self.val = [self.tc.GetValue()]+value
        self.GetParent().send_event(self, evt)

    def SetValue(self, value):
        self.val = value
        self.tc.SetValue(value[0])

    def GetValue(self):
        self.val[0] = self.tc.GetValue()
        return self.val

    def _s4(self):
        return {"style": wx.TE_PROCESS_ENTER,
                "choices": ["5", "7", "8", "9", "12", "15",
                            "18", "20", "24", "36", "48"]}


class LabelPanel2(LabelPanel):
    def _s4(self):
        return {"style": wx.TE_PROCESS_ENTER,
                "choices": ["default", "5", "7", "8", "9", "12", "15",
                            "18", "20", "24", "36", "48"]}


class AxisPositionPanel(Panel):
    def __init__(self, *args, **kargs):
        if "setting" in kargs:
            setting = kargs["setting"]
            del kargs["setting"]
        super(AxisPositionPanel, self).__init__(*args, **kargs)
        self.choices = setting["choices"]+["center", "zero"]
        self.cb = wx.ComboBox(self, wx.ID_ANY,
                              style=wx.TE_PROCESS_ENTER,
                              choices=self.choices)
        self.mirror = CheckBox(self, wx.ID_ANY, 'mirror tick')
        self.mirror2 = CheckBox(self, wx.ID_ANY, 'mirror box')
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self.cb, 0, wx.EXPAND)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.GetSizer().Add(sizer2, 0, wx.EXPAND)
        sizer2.Add(self.mirror, 0, wx.EXPAND)
        sizer2.Add(self.mirror2, 0, wx.EXPAND)
        self.Bind(wx.EVT_COMBOBOX, self.onHit, self.cb)
        self.value0 = None

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        self.cb.Enable(value)
        self.mirror.Enable(value)
        self.mirror2.Enable(value)

    def GetValue(self):
        if str(self.cb.GetValue()) in self.choices:
            self.value0 = str(self.cb.GetValue())
        v = self.value0
        val = (v,
               self.mirror.GetValue(),
               self.mirror2.GetValue())
        return val

    def SetValue(self, val):
        self.value0 = val[0]
        self.set_cb_items()
        if str(self.value0) in self.choices:
            self.cb.SetValue(self.value0)
        else:
            self.cb.SetValue('custom')
        self.mirror.SetValue(val[1])
        self.mirror2.SetValue(val[2])
        self._value0 = val[3]

    def set_cb_items(self):
        values = [x for x in self.choices]
#        if str(self.value0) in self.choices:
#            values.append('custom')
        values.append('customize...')
        self.cb.Clear()
        for x in values:
            self.cb.Append(x)

        comboStrings = self.cb.Strings
        if len(comboStrings) == 0:
            self.cb.SetMinSize(wx.DefaultSize)
        else:
            txt_w = max([self.GetTextExtent(s.strip())[0]
                         for s in comboStrings])
            txt_h = self.cb.Size[1]
            self.cb.SetMinSize((txt_w+txt_h+10, txt_h))

    def onHit(self, evt):
        from ifigure.widgets.dlg_axspine_setting import ask_setting
        if str(self.cb.GetValue()) == 'customize...':
            if self.value0 is None:
                is_ok, value = ask_setting(self, self.value0, self.choices[:2])
            else:
                is_ok, value = ask_setting(
                    self, self._value0, self.choices[:2])
            if not is_ok:
                return

            self.value0 = value
            self.set_cb_items()
            self.cb.SetValue('custom')
        self.GetParent().send_event(self, evt)

    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)


class LogLinScale(Panel):
    def __init__(self, *args, **kargs):
        if "setting" in kargs:
            setting = kargs["setting"]
            del kargs["setting"]
        super(LogLinScale, self).__init__(*args, **kargs)

        s2 = setting = {"style": wx.CB_READONLY,
                        "choices": ["linear", "log", "symlog"]}
        self.cb = ComboBox(self, wx.ID_ANY,
                           style=s2["style"],
                           choices=s2["choices"])
        self.tc = TextCtrlCopyPaste(self, wx.ID_ANY, '10',
                                    style=wx.TE_PROCESS_ENTER)
        self.tc2 = TextCtrlCopyPaste(self, wx.ID_ANY, '1',
                                     style=wx.TE_PROCESS_ENTER)
        self.tc3 = TextCtrlCopyPaste(self, wx.ID_ANY, '1',
                                     style=wx.TE_PROCESS_ENTER)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self.cb, 0, wx.EXPAND)
        self.GetSizer().Add(self.tc, 0, wx.EXPAND)
        hsizer = GridSizer(1, 2)
        self.GetSizer().Add(hsizer, 0, wx.EXPAND)
        hsizer.Add(self.tc2, 1, wx.EXPAND)
        hsizer.Add(self.tc3, 1, wx.EXPAND)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        self.cb.Enable(value)
        if value:
            mode = str(self.cb.GetValue())
            if mode == 'linear':
                self.tc.Enable(False)
            elif mode == 'log':
                self.tc.Enable(True)
            elif mode == 'symlog':
                self.tc2.Enable(True)
                self.tc3.Enable(True)
                self.tc.Enable(True)
            else:
                self.tc2.Enable(False)
                self.tc3.Enable(False)
                self.tc.Enable(False)
        else:
            self.tc.Enable(False)
            self.tc2.Enable(False)
            self.tc3.Enable(False)

    def GetValue(self):
        val = (self.cb.GetValue(),
               float(self.tc.GetValue()),
               float(self.tc2.GetValue()),
               float(self.tc3.GetValue()))
        if val[0] == 'linear':
            #           self.lb.Hide()
            self.tc.Enable(False)
        elif val[0] == 'log':
            #           self.lb.Show()
            self.tc.Enable(True)
        elif val[0] == 'symlog':
            self.tc2.Enable(True)
            self.tc3.Enable(True)
            self.tc.Enable(True)
        else:
            self.tc2.Enable(False)
            self.tc3.Enable(False)
            self.tc.Enable(False)
        return val

    def SetValue(self, val):
        self.cb.SetValue(val[0])
        self.tc.SetValue(str(val[1]))
        self.tc2.SetValue(str(val[2]))
        self.tc3.SetValue(str(val[3]))
        if val[0] == 'linear':
            #           self.lb.Hide()
            self.tc.Enable(False)
        elif val[0] == 'log':
            #           self.lb.Show()
            self.tc.Enable(True)
        elif val[0] == 'symlog':
            self.tc2.Enable(True)
            self.tc3.Enable(True)
            self.tc.Enable(True)
        else:
            self.tc2.Enable(False)
            self.tc3.Enable(False)
            self.tc.Enable(False)

    def send_event(self, obj, evt):
        evt.signal = 'need_adjustscale'
        self.GetParent().send_event(self, evt)


class AxisRange(wx.Panel):
    def __init__(self, *args, **kargs):
        if "setting" in kargs:
            setting = kargs["setting"]
            del kargs["setting"]
        super(AxisRange, self).__init__(*args, **kargs)

        self.panel = Panel(self)
        self.panel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.tc1 = TextCtrlCopyPaste(self.panel, wx.ID_ANY, '',
                                     style=wx.TE_PROCESS_ENTER)
        self.tc2 = TextCtrlCopyPaste(self.panel, wx.ID_ANY, '',
                                     style=wx.TE_PROCESS_ENTER)
        self.panel.GetSizer().Add(vsizer, 1,
                                  wx.EXPAND | wx.ALL, 1)
        vsizer.AddStretchSpacer()
        vsizer.Add(self.tc1, 0)  # wx.EXPAND)
        vsizer.Add(self.tc2, 0)  # , wx.EXPAND)
        vsizer.AddStretchSpacer()

        self.panel2 = Panel(self)
        self.panel2.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        s1 = GridSizer(3, 1)
        s2 = GridSizer(3, 1)
        self.panel2.GetSizer().Add(s1, 0, wx.EXPAND)
        self.panel2.GetSizer().Add(s2, 0, wx.EXPAND)
        self.cb_auto = CheckBox(self.panel2, wx.ID_ANY, 'auto')
        self.cb_int = CheckBox(self.panel2, wx.ID_ANY, 'int')
        self.cb_sym = CheckBox(self.panel2, wx.ID_ANY, 'sym')
        self.cb_mar = CheckBox(self.panel2, wx.ID_ANY, 'margin')
        s1.Add(self.cb_auto, 0, wx.EXPAND)
        s1.Add(self.cb_int, 0, wx.EXPAND)
        s1.Add(self.cb_sym, 0, wx.EXPAND)
        s2.Add(self.cb_mar, 0, wx.EXPAND)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.GetSizer().Add(self.panel, 1,
                            wx.EXPAND | wx.ALL, 1)
        self.GetSizer().Add(self.panel2, 0,
                            wx.EXPAND | wx.ALL, 1)
        self.check_range_order = setting.pop('check_range_order', False)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        self.tc1.Enable(value)
        self.tc2.Enable(value)
        self.cb_auto.Enable(value)
        self.cb_int.Enable(value)
        self.cb_sym.Enable(value)
        self.cb_mar.Enable(value)

    def GetValue(self):
        self._check_order()
        val = ((float(self.tc1.GetValue()),
                float(self.tc2.GetValue())),
               self.cb_auto.GetValue(),
               self.cb_int.GetValue(),
               self.cb_sym.GetValue(),
               self.cb_mar.GetValue())
        return val

    def SetValue(self, val):
        self.tc1.SetValue(str(val[0][0]))
        self.tc2.SetValue(str(val[0][1]))
        self.cb_auto.SetValue(val[1])
        self.cb_int.SetValue(val[2])
        self.cb_sym.SetValue(val[3])
        self.cb_mar.SetValue(val[4])

    def _check_order(self):
        if not self.check_range_order:
            return
        s1 = self.tc1.GetValue()
        s2 = self.tc2.GetValue()
        if float(s1) > float(s2):
            self.tc1.SetValue(s2)
            self.tc2.SetValue(s1)
            print('range[1] should be smaller than range[2]')

    def send_event(self, obj, evt):
        evt.signal = 'need_adjustscale'
        if (evt.GetEventObject() is self.tc1 or
                evt.GetEventObject() is self.tc2):
            self._check_order()
            self.cb_auto.SetValue(False)
        if self.cb_sym.GetValue():
            if evt.GetEventObject() is self.tc1:
                self.tc2.SetValue(str(-float(self.tc1.GetValue())))
            elif evt.GetEventObject() is self.tc2:
                self.tc1.SetValue(str(-float(self.tc2.GetValue())))
            else:
                a = float(self.tc1.GetValue())
                b = float(self.tc2.GetValue())
                if abs(a) > abs(b):
                    r = (-abs(a), abs(a))
                else:
                    r = (-abs(b), abs(b))
                self.tc1.SetValue(str(r[0]))
                self.tc2.SetValue(str(r[1]))
        if self.cb_int.GetValue():
            a = float(self.tc1.GetValue())
            b = float(self.tc2.GetValue())
            import numpy as np
            if a != 0:
                si = a/abs(a)
                ex = int(np.log10(abs(a)))
                ai = (np.floor(a/(10.**ex)))*10.**ex
#               if (a/(10.**ex) % 1)== 0. or a < 0:

#               else:
#                  ai = (np.floor(a/(10.**ex))-1)*10.**ex
            else:
                ai = 0.
            if b != 0:
                si = b/abs(b)
                ex = int(np.log10(abs(b)))
                if (b/(10.**ex) % 1) == 0.:
                    bi = (np.floor(b/(10.**ex)))*10.**ex
                else:
                    bi = (np.floor(b/(10.**ex))+1)*10.**ex
            else:
                bi = 0.
            self.tc1.SetValue(str(ai))
            self.tc2.SetValue(str(bi))
        self.GetParent().send_event(self, evt)


class AxesRangeParamPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        check_range_order = kargs.pop('check_range_order', False)

        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.mode = ''
        self.l = [["range", ('0', '1'),  13, {'check_range_order': check_range_order}],
                  ["scale", 'linear',  14]]

        self.elp = EditListPanel(self, self.l, call_sendevent=self,
                                 edge=0)
        self.elp.Show()
        self.GetSizer().Add(self.elp,  1, wx.EXPAND, 0)

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)
        self.elp.Enable(value)

    def GetValue(self):
        v = self.elp.GetValue()
        val = [v[1][1], v[0][1], v[0][0],
               v[1][0], v[1][2],  v[1][3], v[0][2], v[0][3], v[0][4]]
        return val

    def SetValue(self, value):
        # value = (base, auto, range, scale, symlogint, symloglinscale
        #          mode[0], mode[1], mode[2])
        v = [[value[2], value[1],  value[6], value[7], value[8]],
             [value[3], value[0], value[4], value[5]]]
        self.elp.SetValue(v)

    def send_event(self, obj,  evt):
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)


class BitmapButtons(wx.Panel):
    def __init__(self, *args, **kargs):
        super(BitmapButtons, self).__init__(*args, **kargs)
        self.Controls = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.gsizer = GridSizer(10, 5)
        sizer.Add(self.gsizer, 0, wx.ALL, 0)
        self._btn = None
        self._val = None

    def Enable(self, value=True):
        wx.Panel.Enable(self, value)

        for m in self.Controls:
            s = m['bitmap'].GetSize()
            m['obj'].Enable(value)
            m['obj'].SetClientSize((s[0]+8, s[1]+8))

    def check_if_need2expand(self):
        size = self.gsizer.CalcRowsCols()
        r = self.gsizer.GetRows()

        if size[0] == r:
            #          print 'expanding'
            self.gsizer.SetRows(r+1)

    def add_bitmap_buttons(self, title, ftitle, names, pname,
                           labels=None, filenames=None,
                           imagearray=None, enter_notify=None,
                           leave_notify=None):
        from ifigure.ifigure_config import icondir

        if filenames is None:
            filenames = names
        self._btn = [None]*len(names)
        self._btn_name = names
        i = 0
        if labels is None:
            labels = [None]*len(names)

        import math

        self.gsizer.SetRows(int(math.ceil(len(names)/5.)))
        for name, label, fname in zip(names, labels, filenames):

            if label is not None:
                txt = wx.StaticText(self)
                txt.SetLabel(label)
                self.gsizer.Add(txt, 0, wx.ALL, 0)
            dirname = os.path.dirname(ifigure.__file__)
            if imagearray is None:
                ffname = b64encode(fname.encode('latin-1')).decode()
                imageFile = os.path.join(icondir, 'image',
                                         ftitle+'_'+str(ffname)+'.png')

                if not os.path.exists(imageFile):
                    ffname = b64encode('other'.encode('latin-1')).decode()
                    imageFile = os.path.join(icondir, 'image',
                                             'color_' + ffname + '.png')
                    print('Cannot find bitmap for ' + ftitle + '=' + fname)
                bitmap = wx.Bitmap(imageFile)
                h, w = bitmap.GetSize()

                image = bitmap.ConvertToImage()
                array = np.frombuffer(bytes(image.GetData()), dtype=np.uint8)
                array = array.copy()
                array = array.reshape(w, h, -1)
            else:
                array = imagearray[name]
            array[:2, :, 0] = 0
            array[-2:, :, 0] = 0
            array[:, :2, 0] = 0
            array[:, -2:, 0] = 0
            array[:2, :, 1] = 0
            array[-2:, :, 1] = 0
            array[:, :2, 1] = 0
            array[:, -2:, 1] = 0
            array[:2, :, 2] = 0
            array[-2:, :, 2] = 0
            array[:, :2, 2] = 0
            array[:, -2:, 2] = 0

            image = wxEmptyImage(h, w)
            image.SetData(array.tobytes())
            bitmap2 = image.ConvertToBitmap()
            btn = wx.BitmapButton(self, bitmap=bitmap)
            self._btn[i] = btn
            self.gsizer.Add(btn, 0, wx.ALL, 0)
            self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
            if enter_notify is not None:
                def f(evt, n=name):
                    enter_notify(evt, n)
                btn.Bind(wx.EVT_ENTER_WINDOW, f)
            if leave_notify is not None:
                def f(evt, n=name):
                    leave_notify(evt, n)
                btn.Bind(wx.EVT_LEAVE_WINDOW, f)
            self.Controls.append(
                {"obj": btn, "property": pname, "value": name,
                 "bitmap": bitmap, "bitmap2": bitmap2})
            i += 1

    def onEdit(self, evt):
        for ctl in self.Controls:
            if ctl["obj"] is evt.GetEventObject():
                self.val = ctl["value"]
                self.SetValue(self.val)
                break
        self.GetParent().send_event(self, evt)

    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)

    def SetValue(self, val):
        #        print 'data coming', val
        #        import traceback
        #        traceback.print_stack()
        i = 0
        for btn in self._btn:
            btn.SetBitmapLabel(self.Controls[i]["bitmap"])
            i = i+1

        # if isnumber(val) and not isnumber(self._btn_name[0]):
        #    val = str(val)
        if isstringlike(val) and val in self._btn_name:
            j = self._btn_name.index(val)
            # print 'found', j
            self._btn[j].SetBitmapLabel(self.Controls[j]["bitmap2"])
        # else:
        #    # check error
        #    print val, self._btn_name
        self._val = val

    def GetValue(self, val):
        return self._val


class Color(BitmapButtons):
    def _a2n(self, value):
        value = [int(v*255) for v in value]
        return value[3]*256*256*256 + value[2]*256*256 + value[1]*256 + value[0]
        # return 1*256*256*256 + value[2]*256*256 + value[1]*256 + value[0]

    def _n2a(self, value):
        x = ((value % 256),
             (value % (256*256)) // 256,
             (value % (256*256*256)) // 256**2,
             (value // 256**3), )
        return (x[0]/255., x[1]/255., x[2]/255., x[3]/255.)

    def __init__(self, *args, **kargs):
        '''
        **kargs is not used for now
        '''
        super(Color, self).__init__(*args)
        from ifigure.ifigure_config import color_list
        from matplotlib.colors import ColorConverter as CC
        self.check_if_need2expand()
        names = [self._a2n(CC().to_rgba(x)) for x in color_list()]
        names = names + ['other']
        fnames = color_list() + ['other']
        self.add_bitmap_buttons('Color', 'color', names,
                                'color', filenames=fnames)
        self.val = self.Controls[0]["value"]

    def onEdit(self, evt):
        for ctl in self.Controls:
            if ctl["obj"] is evt.GetEventObject():
                if ctl["value"] == 'other':
                    dlg = wx.ColourDialog(self.GetTopLevelParent())
                    if dlg.ShowModal() != wx.ID_OK:
                        dlg.Destroy()
                        return
                    data = dlg.GetColourData()
                    v = data.GetColour()
                    color = v.alpha*256*256*256 + \
                        v[2]*256*256 + v[1]*256 + v[0]
                    dlg.Destroy()
                    self.val = color
                else:
                    self.val = ctl["value"]
                BitmapButtons.SetValue(self, self.val)
                break
        self.GetParent().send_event(self, evt)

    def GetValue(self):
        #        if self.val == 'none':
        #             return [0,0,0,0]
        #        print self._n2a(self.val) , self.val
        return self._n2a(self.val)

    def SetValue(self, val):

        from matplotlib.colors import ColorConverter as CC
        if val is None:
            val = [0, 0, 0, 0]
        elif len(val) == 0:
            val = [0, 0, 0, 0]
        elif isinstance(val, str):
            val = CC().to_rgba(val)
        elif six.PY2 and isinstance(val, unicode):
            val = CC().to_rgba(val)
        else:
            if not isinstance(val, str) and len(val) == 3:
                val = [val[0], val[1], val[2], 1.0]

#           if (val[0] == 0 and val[1] == 0 and
#               val[2] == 0 and val[3] == 0):
#               val = 'none'

        self.val = self._a2n(val)
        BitmapButtons.SetValue(self, self.val)


class ColorFace(Color):
    def __init__(self, *args, **kargs):
        '''
        **kargs is not used for now
        '''
        super(Color, self).__init__(*args)
        from ifigure.ifigure_config import color_list_face
        from matplotlib.colors import ColorConverter as CC
        self.check_if_need2expand()
        names = [self._a2n(CC().to_rgba(x))
                 for x in color_list_face()] + ['other']
        self.add_bitmap_buttons('Color', 'color', names, 'color',
                                filenames=color_list_face() + ['other'])
        self.val = self.Controls[0]["value"]

    def SetValue(self, val):
        if isstringlike(val) and val == 'disabled':
            # if it is not list/numpy array/tuple and is 'disabled'
            self.Enable(False)
        else:
            self.Enable(True)
            super(ColorFace, self).SetValue(val)


class LineColor(BitmapButtons):
    def __init__(self, *args, **kargs):
        '''
        **kargs is not used for now
        '''
        super(LineColor, self).__init__(*args)
        from ifigure.ifigure_config import linecolorlist
        self.check_if_need2expand()
        self.add_bitmap_buttons('Color', 'color', linecolorlist, 'color')
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return self.val

    def SetValue(self, val):
        from ifigure.ifigure_config import linecolorlist, linecolor_rlist
        self.val = val
        for idx, p in enumerate(linecolor_rlist):
            if p == val:
                val = linecolorlist[idx]
                break
        BitmapButtons.SetValue(self, val)


class PathCollectionEdgeColor(BitmapButtons):
    def __init__(self, *args, **kargs):
        '''
        **kargs is not used for now
        '''
        super(PathCollectionEdgeColor, self).__init__(*args)
        from ifigure.ifigure_config import pedgecolorlist
        self.check_if_need2expand()
        self.add_bitmap_buttons('Color', 'color', pedgecolorlist, 'color')
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return self.val

    def SetValue(self, val):
        from ifigure.ifigure_config import pedgecolorlist, pedgecolor_rlist

        def _check(p, val):
            if len(p) != len(val):
                return False
#            print 'checking', p, val
            c = (p == val)
#            print c
            if isinstance(c, bool):
                return c
#            print c.all()
            return c.all()

        self.val = val
#        print val, pedgecolor_rlist
        for idx, p in enumerate(pedgecolor_rlist):

            if _check(p, val):
                #                print 'hit'
                val = pedgecolorlist[idx]
                break
#        print idx, val
        BitmapButtons.SetValue(self, val)


def colorbutton_bitmap(data):
    v = [int(data[0]*255), int(data[1]*255), int(data[2]*255)]
    w, h = bitmap_size
    array = np.array([v, ]*w*h, dtype=np.uint8).reshape((w, h, -1))
    image = wxEmptyImage(w, h)
    image.SetData(array.tobytes())
    bitmap = image.ConvertToBitmap()
    return bitmap


class ColorSelector(wx.BitmapButton):
    def __init__(self, *args, **kargs):
        from ifigure.ifigure_config import collist
        from ifigure.ifigure_config import icondir
        self.color_list = collist
        dirname = os.path.dirname(ifigure.__file__)
        self.imageFiles = {}
        for name in self.color_list:
            nname = b64encode(name.encode('latin-1')).decode()
            self.imageFiles[name] = os.path.join(icondir, 'image',
                                                 'color_' + nname + '.png')
        wx.BitmapButton.__init__(
            self, *args, bitmap=wx.Bitmap(self.imageFiles['blue']))
        self.value = 'blue'
        self.Bind(wx.EVT_BUTTON, self.onHit)

    def SetValue(self, value):
        from matplotlib.colors import ColorConverter as CC
        try:
            if sum(value) == 0.0:
                value = 'none'
        except:
            pass
        if value == 'none':
            bitmap = wx.Bitmap(self.imageFiles['none'])
        else:
            if isinstance(value, str):
                bitmap = colorbutton_bitmap(CC().to_rgba(value))
            elif six.PY2 and isinstance(value, unicode):
                bitmap = colorbutton_bitmap(CC().to_rgba(value))
            else:
                bitmap = colorbutton_bitmap(value)
        self.SetBitmapLabel(bitmap)
        self.value = value

    def GetValue(self):
        if self.value == 'none':
            return (0.0, 0.0, 0.0, 0.0)
        return self.value

    def onHit(self, evt):
        l = [[None, "Select Color", 2, None],
             ["", self.value, 6, {}]]
        pos = self.GetScreenPosition()
        dia = EditListDialog(self, wx.ID_ANY, '',
                             l, nobutton=True,
                             pos=pos)
        val = dia.ShowModal()
        value = dia.GetValue()
        dia.Destroy()
        if val != wx.ID_OK:
            return
        if value[0]:
            self.SetValue(value[1])
        evt.Skip()
        self.GetParent().send_event(self, evt)


class ColorPairSelector(Panel):
    def __init__(self, parent, id):
        Panel.__init__(self, parent, id)
        self.bt1 = ColorSelector(self, wx.ID_ANY)
        self.bt2 = ColorSelector(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        sizer.Add(self.bt1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        sizer.Add(self.bt2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.SetValue(['black', 'black'])

    def GetValue(self):
        v = (self.bt1.GetValue(), self.bt2.GetValue())
        return v

    def SetValue(self, value):
        self.bt1.SetValue(value[0])
        self.bt2.SetValue(value[1])
        self._value = value


class TickLabelSizeSelector(Panel):
    def __init__(self, parent, id, **kargs):
        setting = kargs.pop("setting", {"choices": ['default', '12', '14']})
        Panel.__init__(self, parent, id)
        self.cb1 = ComboBox_Float(self, wx.ID_ANY,
                                  style=wx.TE_PROCESS_ENTER,
                                  choices=setting["choices"])
        self.cb2 = ComboBox_Float(self, wx.ID_ANY,
                                  style=wx.TE_PROCESS_ENTER,
                                  choices=setting["choices"])
        gsizer = GridSizer(2)
        self.SetSizer(gsizer)
        gsizer.Add(self.cb1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        gsizer.Add(self.cb2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.SetValue([12, 12])

    def GetValue(self):
        v = (self.cb1.GetValue(),
             self.cb2.GetValue())
        return v

    def SetValue(self, value):
        try:
            v1 = str(int(value[0]))
        except:
            v1 = 'default'
        try:
            v2 = str(int(value[1]))
        except:
            v2 = 'default'

        self.cb1.SetValue(v1)
        self.cb2.SetValue(v2)
        self._value = value


class TickLabelColorSelector(Panel):
    def __init__(self, parent, id):
        Panel.__init__(self, parent, id)
        gsizer = FlexGridSizer(6)
        self.SetSizer(gsizer)
        self.bt1 = ColorSelector(self, wx.ID_ANY)
        self.bt2 = ColorSelector(self, wx.ID_ANY)
        self.bt3 = ColorSelector(self, wx.ID_ANY)

        w = -1
        txt1 = wx.StaticText(self, size=(w, -1))
        txt2 = wx.StaticText(self, size=(w, -1))
        txt3 = wx.StaticText(self, size=(w, -1))
        txt1.SetLabel('tick')
        txt2.SetLabel('label1')
        txt3.SetLabel('label2')
        style = wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        gsizer.Add(txt1, 0, style, 1)
        gsizer.Add(self.bt1, 0, wx.ALIGN_CENTER_VERTICAL, 1)
        gsizer.Add(txt2, 0, style, 1)
        gsizer.Add(self.bt2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        gsizer.Add(txt3, 0, style, 1)
        gsizer.Add(self.bt3, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.SetValue(['black', 'black', 'black'])

    def GetValue(self):
        v = (self.bt1.GetValue(), self.bt2.GetValue(),
             self.bt3.GetValue())
        return v

    def SetValue(self, value):
        self.bt1.SetValue(value[0])
        self.bt2.SetValue(value[1])
        self.bt3.SetValue(value[2])
        self._value = value


class ClipSetting(Panel):
    def __init__(self, parent, id):
        Panel.__init__(self, parent, id)
        self.cb = wx.CheckBox(self,  wx.ID_ANY, 'clip')
        self.bt = ColorSelector(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        sizer.Add(self.cb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        sizer.Add(self.bt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self._value = [False, 'white']
        self.Bind(wx.EVT_CHECKBOX, self.onHit)

    def GetValue(self):
        v = (self.cb.GetValue(), self.bt.GetValue())
        return v
#        return self._value

    def SetValue(self, value):
        self.cb.SetValue(value[0])
        self.bt.SetValue(value[1])
        self._value = value

    def onHit(self, evt):
        if self.cb.GetValue():
            self.bt.Enable(True)
        else:
            self.bt.Enable(False)
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)

#    def send_event(self, evt):
#        evt.SetEventObject(self)
#        self.GetParent().send_event(self, evt)


class ColorOrderPopup(wx.Menu):
    def __init__(self, parent):
        super(ColorOrderPopup, self).__init__()
        self.parent = parent
        menus = [('Add', self.parent.add, None),
                 ('Remove',  self.parent.remove, None)]
        cbook.BuildPopUpMenu(self, menus)


class ColorOrder(Panel):
    def __init__(self, parent, id, *args, **kargs):
        from ifigure.ifigure_config import collist
        color_list = collist[0:7]
        Panel.__init__(self, parent, id)
        self.make_buttons(color_list)
        self.value = self.GetValue()

    def SetValue(self, value):
        if value is None:
            return
        if len(value) != len(self.btn):
            self.remove_buttons()
            self.make_buttons(value)
        for i in range(len(value)):
            self.btn[i].SetValue(value[i])
        self.value = self.GetValue()

    def GetValue(self):
        return [btn.GetValue() for btn in self.btn]

    def onHit(self, evt):
        o = evt.GetEventObject()
        oi = self.btn.index(o)
        v = o.GetValue()
        value = self.GetValue()
        for i in range(len(value)):
            if value[i] == v and i != oi:
                value[i] = self.value[oi]
        self.SetValue(value)

    def onKeyPressed(self, evt):
        self.hitobj = evt.GetEventObject()
        self.hitpos = evt.GetPosition()
        m = ColorOrderPopup(self)
        self.PopupMenu(m,  # ifigure_popup(self),
                       evt.GetPosition())
        m.Destroy()

    def onKeyReleased(self, evt):
        # print 'key release'
        pass

    def add(self, evt):
        l = [[None, "Select Color", 2, None],
             ["", [0, 0, 0, 0], 6, {}]]
        dia = EditListDialog(self, wx.ID_ANY, '',
                             l, nobutton=True,
                             pos=self.hitobj.GetScreenPosition(),)
        val = dia.ShowModal()
        value = dia.GetValue()
        dia.Destroy()
        if val != wx.ID_OK:
            return

        if value[0]:
            pass
            # print 'adding ', value[1][1]
        else:
            return
        if value[1] in self.value:
            return
        i = self.btn.index(self.hitobj)
        color_list = self.value[:]
        color_list.insert(i, value[1])
        self.remove_buttons()
        self.make_buttons(color_list)
        self.value = self.GetValue()

    def remove(self, evt):
        i = self.btn.index(self.hitobj)
        color_list = [c for c in self.value if c != self.value[i]]
        self.remove_buttons()
        self.make_buttons(color_list)
        self.value = self.GetValue()

    def remove_buttons(self):
        self.Hide()
        self.Unbind(wx.EVT_BUTTON)
        for btn in self.btn:
            self.GetSizer().Detach(btn)
            btn.Unbind(wx.EVT_RIGHT_DOWN)
            btn.Unbind(wx.EVT_RIGHT_UP)
            btn.Hide()
            wx.CallAfter(btn.Destroy)

    def make_buttons(self, color_list):
        self.Hide()
        l = len(color_list)
        self.SetSizer(GridSizer(min((l % 7, 1))+l/7, 7))
        self.btn = [None]*l
        for i in range(l):
            name = color_list[i]
            self.btn[i] = ColorSelector(self, wx.ID_ANY)
            self.btn[i].SetValue(name)
            self.GetSizer().Add(self.btn[i], 0)
            self.Bind(wx.EVT_BUTTON, self.onHit, self.btn[i])
            self.btn[i].Bind(wx.EVT_RIGHT_DOWN, self.onKeyPressed)
            self.btn[i].Bind(wx.EVT_RIGHT_UP,   self.onKeyReleased)
        self.Show()
        self.Layout()
        self.GetTopLevelParent().Fit()
        return


class Color3DPane(Panel):
    def __init__(self, *args, **kargs):
        super(Panel, self).__init__(*args, **kargs)
        st1 = wx.StaticText(self, wx.ID_ANY, ' x: ')
        st2 = wx.StaticText(self, wx.ID_ANY, ' y: ')
        st3 = wx.StaticText(self, wx.ID_ANY, ' z: ')
        self.bt1 = ColorSelector(self)
        self.bt2 = ColorSelector(self)
        self.bt3 = ColorSelector(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(st1, 0)
        hsizer.Add(self.bt1, 0)
        hsizer.Add(st2, 0)
        hsizer.Add(self.bt2, 0)
        hsizer.Add(st3, 0)
        hsizer.Add(self.bt3, 0)
        sizer.Add(hsizer, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(sizer)

    def GetValue(self):
        return (self.bt1.GetValue(),
                self.bt2.GetValue(),
                self.bt3.GetValue())

    def SetValue(self, val):
        self.bt1.SetValue(val[0])
        self.bt2.SetValue(val[1])
        self.bt3.SetValue(val[2])


class ColorMapButton(BitmapButtons):
    def __init__(self, *args):

        from ifigure.ifigure_config import colormap_list
        super(ColorMapButton, self).__init__(*args)
        self.Controls = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        cmaps = colormap_list()
        self.gsizer = FlexGridSizer(len(cmaps)/6+1, 6)
        sizer.Add(self.gsizer, 0, wx.ALL, 0)

        self.check_if_need2expand()
        labels = ['   '+name for name in cmaps]
        self.add_bitmap_buttons('Color', 'colormap', cmaps, 'cmap',
                                enter_notify=self.button_notify)
        self.SetValue(self.Controls[0]["value"])
        self.tc = wx.StaticText(self)
        self.gsizer.Add(self.tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 0)

    def button_notify(self, evt, name):
        self.tc.SetLabel(name)
        evt.Skip()


class ColorMapButtonExtra(BitmapButtons):
    def __init__(self, *args):

        from ifigure.ifigure_config import colormap_list
        super(ColorMapButtonExtra, self).__init__(*args)
        self.Controls = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        cmaps = ['idl'+str(x) for x in range(40)]
        self.gsizer = FlexGridSizer(len(cmaps)/6+1, 6)
        sizer.Add(self.gsizer, 0, wx.ALL, 0)

        self.check_if_need2expand()
        labels = ['   '+name for name in cmaps]
        self.add_bitmap_buttons('Color', 'colormap', cmaps, 'cmap',
                                enter_notify=self.button_notify)
        self.SetValue(self.Controls[0]["value"])
        self.tc = wx.StaticText(self)
        self.gsizer.Add(self.tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 0)

    def button_notify(self, evt, name):
        self.tc.SetLabel(name)
        evt.Skip()

#    def add_bitmap_buttons(self, title, ftitle, names, pname,
#                                 enter_notify = None):
#        labels = ['   '+name for name in names]
#        super(ColorMapButton, self).add_bitmap_buttons(title, ftitle,
#                                         names, pname,
#                                         enter_notify = self.button_notify)
# , labels=labels)
#        return

#    def GetValue(self):
#        return self.val
#    def SetValue(self, val):
#        BitmapButtons.SetValue(self, val)


class ColorMapNB(wx.Notebook):
    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)


class ColorMap(wx.Panel):
    def __init__(self, *args, **kargs):
        if "setting" in kargs:
            #           setting = kargs["setting"]
            del kargs["setting"]
#        else: setting = {"reverse": False}
        super(ColorMap, self).__init__(*args, **kargs)
        self.nb = ColorMapNB(self)
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.nb, 0)


#        p1 = wx.Panel(self)
        self.bt = ColorMapButton(self.nb)
        self.nb.AddPage(self.bt, 'MPL')
#        s = wx.BoxSizer(wx.VERTICAL)
#        p1.SetSizer(s)
#        s.Add(self.bt, 1)


#        p2 = wx.Panel(self)
        self.bt2 = ColorMapButtonExtra(self.nb)
        self.nb.AddPage(self.bt2, 'Extra')

        self.cb = wx.CheckBox(self, wx.ID_ANY, 'reverse')
        s.Add(self.cb, 0, wx.ALL, 5)
        self.SetSizer(s)

    def GetValue(self):
        if self.nb.GetSelection() == 0:
            val = self.bt.val
        else:
            val = self.bt2.val
        val2 = self.cb.GetValue()
        if val2:
            v = val+'_r'
        else:
            v = val
        return v

    def SetValue(self, val):
        if val.endswith('_r'):
            name = val[:-2]
        else:
            name = val
        if name.startswith('idl'):
            self.bt2.val = name
            self.bt2.SetValue(name)
        else:
            self.bt.val = name
            self.bt.SetValue(name)
        if val.endswith('_r'):
            self.cb.SetValue(True)
        else:
            self.cb.SetValue(False)

    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)


class color_map_button(wx.Panel):
    def __init__(self, *args, **kargs):
        super(color_map_button, self).__init__(*args, **kargs)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        bt = wx.Button(self, wx.ID_ANY, 'Select...')
        sizer.Add(bt, 1, wx.ALL, 1)
        self.Bind(wx.EVT_BUTTON, self.onSelect, bt)

    def onSelect(self, evt):
        #        if self.val[0].endswith('_r'):
        #           s = {"reverse":True}
        #        else:
        #           s = {"reverse":False}
        list = [["", self.val[0], 11, None]]
        dia = EditListDialog(self, wx.ID_ANY, '', list, nobutton=True)
        val = dia.ShowModal()
        value = dia.GetValue()
        dia.Destroy()
        if val != wx.ID_OK:
            return
        self.val = value
        self.GetParent().send_event(self, evt)

    def GetValue(self):
        return self.val[0]

    def SetValue(self, val):
        self.val = [val]


class LineStyle(BitmapButtons):
    def __init__(self, *args):
        super(LineStyle, self).__init__(*args)
        from ifigure.ifigure_config import linestyle_list,  linestylenames
        self.check_if_need2expand()
        self.add_bitmap_buttons('LineStyle', 'linestyle',
                                linestyle_list(), 'linestyle',
                                filenames=linestylenames)
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return self.val

    def SetValue(self, val):
        # button widget can not set value from outside....
        # for now....
        self.val = val
        BitmapButtons.SetValue(self, val)


class LineWidth(BitmapButtons):
    def __init__(self, *args):
        super(LineWidth, self).__init__(*args)
        from ifigure.ifigure_config import linewidth_list
        self.check_if_need2expand()
        self.add_bitmap_buttons('LineWidth', 'linewidth',
                                linewidth_list(), 'linewidth')
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return float(self.val)

    def SetValue(self, val):
        # button widget can not set value from outside....
        # for now....
        if val is not None:
            self.val = str(val)
            BitmapButtons.SetValue(self, str(val))


class LineWidthWithZero(LineWidth):
    def __init__(self, *args):
        super(LineWidth, self).__init__(*args)
        from ifigure.ifigure_config import linewidth_list
        self.check_if_need2expand()

        self.add_bitmap_buttons('LineWidth', 'linewidth',
                                ['0.0'] + linewidth_list()[:-1], 'linewidth')
        self.val = self.Controls[0]["value"]

    def SetValue(self, val):
        # button widget can not set value from outside....
        # for now....
        if val is not None:
            self.val = str(val)
            BitmapButtons.SetValue(self, str(val))
            self.Enable(True)
        else:
            self.Enable(False)


class Marker(BitmapButtons):
    def __init__(self, *args, **kargs):
        super(Marker, self).__init__(*args, **kargs)
        from ifigure.ifigure_config import marker_list, markernames
        self.check_if_need2expand()
        self.add_bitmap_buttons('Marker', 'marker', marker_list(), 'marker',
                                filenames=markernames)
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return self.val

    def SetValue(self, val):
        # button widget can not set value from outside....
        # for now....
        self.val = val
        BitmapButtons.SetValue(self, val)


class PatchLineStyle(BitmapButtons):

    def __init__(self, *args):
        from ifigure.ifigure_config import plinestylelist, plinestyle_rlist
        super(PatchLineStyle, self).__init__(*args)
        self.check_if_need2expand()
        self.add_bitmap_buttons('PatchLineStyle', 'plinestyle',
                                plinestylelist, 'plinestyle')
        self.val = self.Controls[0]["value"]

    def GetValue(self):
        return self.val

    def SetValue(self, val):
        self.val = val

        from ifigure.ifigure_config import plinestylelist, plinestyle_rlist
        if val in plinestyle_rlist:
            idx = plinestyle_rlist.index(val)
            val = plinestylelist[idx]
        BitmapButtons.SetValue(self, val)


class TextDropTarget(wx.TextDropTarget):
    """ This object implements Drop Target functionality for Text """

    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj
        self.value = ''

    def OnDrop(self, x, y):
        p = self.obj
        while p.GetParent() is not None:
            p = p.GetParent()
        app = p
        # app=wx.GetApp()
        txt = app._text_clip
        f, t = self.obj.GetSelection()
        self.obj.WriteText(txt)
        return False


def textctrl_mixin_do_init(self, *args, **kargs):
    self._use_escape = True
    nlines = 1
    flag = 0

    if not 'style' in kargs:
        kargs['style'] = 0

    changing_event = kargs.pop('changing_event', False)
    setfocus_event = kargs.pop('setfocus_event', False)
    self._validator = kargs.pop('validator', None)
    self._validator_param = kargs.pop('validator_param', None)

    flag = wx.TE_MULTILINE & kargs['style']
    if 'nlines' in kargs:
        nlines = kargs['nlines']
        del kargs['nlines']

    if flag == 0:
        kargs['style'] = kargs['style'] | wx.TE_PROCESS_ENTER

    self._baseclass.__init__(self, *args, **kargs)

    self.Bind(wx.EVT_KEY_DOWN, self.onKeyPressed)
    # self.Bind(wx.EVT_LEFT_DOWN, self.onDragInit)

    if flag == 0:
        self.Bind(wx.EVT_TEXT_ENTER, self.onEnter)

    dt1 = TextDropTarget(self)
    self.SetDropTarget(dt1)
    if len(args) > 2:
        min_w = max([len(args[2]), 8])
    else:
        min_w = 8
    txt_w = self.Parent.GetTextExtent('A'*min_w)[0]
    txt_h = self.Size[1] * nlines
    self.SetMinSize((txt_w, txt_h))

    self.changing_event = changing_event
    self._send_setfocus_event = False
    self._value_at_getfocus = ''
    if setfocus_event:
        self._send_setfocus_event = True
    self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
    self.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)

    self._wxval = None


class _textctrl_mixin():
    def __init__(self, BaseClass):
        self.__baseclass = BaseClass

    @property
    def _baseclass(self):
        try:
            return self.__baseclass
        except BaseException:
            return wx.TextCtrl

    def onKeyPressed(self, event):
        tw = wx.GetApp().TopWindow
        if hasattr(tw, "appearanceconfig") and tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)

        key = event.GetKeyCode()
        if hasattr(event, 'RawControlDown'):
            controlDown = event.RawControlDown()
        else:
            controlDown = event.ControlDown()
        shiftDown = event.ShiftDown()
        altDown = event.AltDown()

        def _get_current_line():
            linelen0 = np.cumsum(
                [len(x)+1 for x in self.GetValue().split("\n")])
            linelen1 = [len(x)+1 for x in self.GetValue().split("\n")]
            ip = self.GetInsertionPoint()
            for x, y in enumerate(linelen0):
                if y > ip:
                    break
            return x

        if key == wx.WXK_LEFT:
            if shiftDown:
                a, b = self.GetSelection()
                if a > 0:
                    a = a - 1
                self.SetSelection(a, b)
            else:
                self.SetInsertionPoint(self.GetInsertionPoint()-1)
            return

        elif key == wx.WXK_RIGHT:
            if shiftDown:
                a, b = self.GetSelection()
                if b != self.GetLastPosition():
                    b = b + 1
                self.SetSelection(a, b)
            else:
                self.SetInsertionPoint(self.GetInsertionPoint()+1)
            return

        elif key > 127:
            return

        elif key == 67 and controlDown:  # ctrl + C (copy)
            self.Copy()
            return
        elif key == 87 and controlDown:  # ctrl + X (cut)
            self.Cut()

        elif key == 88 and controlDown:  # ctrl + W (cut)
            self.Cut()

        elif key == 86 and controlDown:  # ctrl + V (paste)
            self.Paste()

        elif key == 89 and controlDown:  # ctrl + Y (paste)
            self.Paste()

        elif key == 70 and controlDown:  # ctrl + F
            self.SetInsertionPoint(self.GetInsertionPoint()+1)
            return
        elif key == 66 and controlDown:  # ctrl + B
            self.SetInsertionPoint(self.GetInsertionPoint()-1)
            return

        elif key == 80 and controlDown:  # ctrl + P
            cl = _get_current_line()
            if cl == 0:
                return
            linelen = [len(x)+1 for x in self.GetValue().split("\n")]
            linest = np.cumsum(
                [0]+[len(x)+1 for x in self.GetValue().split("\n")])
            ci = self.GetInsertionPoint()
            pp = ci - linest[cl]
            if linelen[cl-1] > pp:
                pp = linest[cl-1] + pp
            else:
                pp = linest[cl-1] + linelen[cl-1]-1
            self.SetInsertionPoint(pp)
            self.SetSelection(pp, pp)
            return

        elif key == 78 and controlDown:  # ctrl + N
            cl = _get_current_line()
            linelen = [len(x)+1 for x in self.GetValue().split("\n")]
            if cl == len(linelen)-1:
                return
            linest = np.cumsum(
                [0]+[len(x)+1 for x in self.GetValue().split("\n")])
            ci = self.GetInsertionPoint()
            pp = ci - linest[cl]
            if linelen[cl+1] > pp:
                pp = linest[cl+1] + pp
            else:
                pp = linest[cl+1] + linelen[cl+1]-1
            self.SetInsertionPoint(pp)
            self.SetSelection(pp, pp)
            return

        elif key == 65 and controlDown:  # ctrl + A (beginning of line)
            cl = _get_current_line()
            linelen = np.cumsum(
                [len(x)+1 for x in self.GetValue().split("\n")])
            if cl == 0:
                pp = 0
            else:
                pp = linelen[cl-1]

            self.SetInsertionPoint(pp)
            self.SetSelection(pp, pp)
            return
        elif key == 69 and controlDown:  # ctrl + E (end of line)
            cl = _get_current_line()
            linelen = np.cumsum(
                [len(x)+1 for x in self.GetValue().split("\n")])
            pp = linelen[cl]

            self.SetInsertionPoint(pp-1)
            self.SetSelection(pp-1, pp-1)
            return

        elif key == 75 and controlDown:  # ctrl + K
            ### works only for single line ###
            self.SetSelection(self.GetInsertionPoint(),
                              self.GetLastPosition())
            self.Cut()
        else:
            event.Skip()

        '''
        ### these two are not necessary sinse event.skip will handle it ###
        elif key == wx.WXK_BACK:
            ### works only for single line ###
            a, b = self.GetSelection()
            if a != b:
                self.Remove(a, b)
                #return
            else:
                ptx = self.GetInsertionPoint()
                if ptx > 0:
                    self.Remove(ptx-1, ptx)
                #return
        elif key == wx.WXK_DELETE:
            ### works only for single line ###
            a, b = self.GetSelection()
            if a != b:
                self.Remove(a, b)
                #return
            else:
                ptx = self.GetInsertionPoint()
                if ptx < self.GetLastPosition():
                    self.Remove(ptx, ptx+1)
                #return
        '''
        if self.changing_event:
            call_send_changing_event(self, event)

        if self._validator is not None:
            wx.CallAfter(self.call_validator)

    def call_validator(self):
        if self._validator(self.GetValue(),
                           self._validator_param,
                           self):
            self.clear_value_error()
        else:
            self.set_value_error()

    def onEnter(self, evt):
        call_send_event(self, evt)

    def onSetFocus(self, evt):
        # print 'get focus', self, self.GetValue()
        self._value_at_getfocus = self.GetValue()
        if self._send_setfocus_event:
            call_send_setfocus_event(self, evt)
        evt.Skip()

    def onKillFocus(self, evt):
        '''
        kill focus -> end of editting
        '''
        # print 'kill focus', self, self.GetValue()
        if self._value_at_getfocus != self.GetValue():
            call_send_event(self, evt)

        evt.Skip()

    def onDragInit(self, e):
        sel = self.GetStringSelection()
        if sel == '':
            e.Skip()
            return
        """ Begin a Drag Operation """
        # Create a Text Data Object, which holds the text that is to be dragged
        # app=wx.GetApp()
        p = self
        while p.GetParent() is not None:
            p = p.GetParent()

        p._text_clip = sel

        tdo = wx.TextDataObject(sel)
        tds = wx.DropSource(self)
        tds.SetData(tdo)
        tds.DoDragDrop(True)
        e.Skip()

    def GetValue(self):
        if six.PY2:
            punctuation = {
                ord(u'\u2018'): unicode("'"),
                ord(u'\u2019'): unicode("'"),
            }
        else:
            punctuation = {
                ord(u'\u2018'): "'",
                ord(u'\u2019'): "'",
            }

        try:
            wxval = self._baseclass.GetValue(self)
            val = str(wxval)
        except UnicodeEncodeError:
            try:
                val = str(wxval.translate(punctuation))
            except UnicodeEncodeError:
                import traceback
                msgs = [x for x in traceback.format_exc().split('\n')
                        if len(x) > 0]
                dprint1(msgs[-1])
                self._wxval = wxval
                return wxval
        self._wxval = None

        if self._use_escape:
            if isinstance(val, str):
                val = val.encode()
            return val.decode('unicode_escape')
        else:
            return val

    def SetValue(self, value):
        try:
            value = str(value)
        except UnicodeEncodeError:
            pass
        if self._use_escape:
            self._baseclass.SetValue(self, value.encode('unicode_escape'))
        else:
            self._baseclass.SetValue(self, value)

        if self._validator is not None:
            wx.CallAfter(self.call_validator)

    def set_value_error(self):
        self.SetForegroundColour(wx.RED)

    def clear_value_error(self):
        self.SetForegroundColour(wx.BLACK)


class TextCtrlCopyPaste(wx.TextCtrl, _textctrl_mixin):
    def __init__(self, *args, **kargs):
        _textctrl_mixin.__init__(self, wx.TextCtrl)
        textctrl_mixin_do_init(self, *args, **kargs)

    def SetValue(self, value):
        return _textctrl_mixin.SetValue(self, value)

    def GetValue(self):
        return _textctrl_mixin.GetValue(self)

    def onDragInit(self, e):
        return _textctrl_mixin.onDragInit(self, e)

    def onKillFocus(self, evt):
        return _textctrl_mixin.onKillFocus(self, evt)

    def onSetFocus(self, evt):
        return _textctrl_mixin.onSetFocus(self, evt)

    def onKeyPressed(self, event):
        return _textctrl_mixin.onKeyPressed(self, event)

    def onEnter(self, evt):
        return _textctrl_mixin.onEnter(self, evt)


class RichTextCtrlCopyPaste(RichTextCtrl, _textctrl_mixin):
    def __init__(self, *args, **kargs):
        _textctrl_mixin.__init__(self, RichTextCtrl)
        textctrl_mixin_do_init(self, *args, **kargs)

    def SetValue(self, value):
        return _textctrl_mixin.SetValue(self, value)

    def GetValue(self):
        return _textctrl_mixin.GetValue(self)

    def onDragInit(self, e):
        return _textctrl_mixin.onDragInit(self, e)

    def onKillFocus(self, evt):
        return _textctrl_mixin.onKillFocus(self, evt)

    def onSetFocus(self, evt):
        return _textctrl_mixin.onSetFocus(self, evt)

    def onKeyPressed(self, event):
        return _textctrl_mixin.onKeyPressed(self, event)

    def onEnter(self, evt):
        return _textctrl_mixin.onEnter(self, evt)


class TextCtrlCopyPasteFloat(TextCtrlCopyPaste):
    def GetValue(self):
        #        print wx.TextCtrl.GetValue(self)
        return float(wx.TextCtrl.GetValue(self))

    def SetValue(self, value):
        value = float(value).__repr__()
        wx.TextCtrl.SetValue(self, value)


class TextCtrlCopyPasteInt(TextCtrlCopyPaste):
    def GetValue(self):
        return int(wx.TextCtrl.GetValue(self))

    def SetValue(self, value):
        value = int(value).__repr__()
        wx.TextCtrl.SetValue(self, value)


class TextCtrlCopyPasteEval(TextCtrlCopyPaste):
    def __init__(self, *arg, **kargs):
        # print 'copy paste eval'
        self._use_escape = True
        self.ns = None
        if 'ns' in kargs:
            self.ns = kargs['ns']
            del kargs['ns']
        if self.ns is None:
            from ifigure.mto.treedict import td_name_space
            self.ns = {key: td_name_space[key] for key in td_name_space}

        super(TextCtrlCopyPaste, self).__init__(*arg, **kargs)

    def onEnter(self, evt):
        try:
            tmp = eval(str(super(TextCtrlCopyPasteEval, self).GetValue()))
            self.SetForegroundColour(wx.BLACK)
        except Exception:
            self.SetForegroundColour(wx.RED)
        self.GetParent().send_event(self, evt)

    def SetValue(self, value):
        if isinstance(value, str):
            super(TextCtrlCopyPasteEval, self).SetValue(value)
        else:
            super(TextCtrlCopyPasteEval, self).SetValue(value[0])

    def GetValue(self):
        txt = str(super(TextCtrlCopyPasteEval, self).GetValue())

#        from ifigure.mto.treedict import td_name_space
#        lc = {key:td_name_space[key] for key in td_name_space}

        try:
            val = eval(txt, {}, self.ns)
#           val = eval(txt, self.ns, self.ns)
        except Exception:
            val = None
        return txt, val


class TextCtrHistoryPopup(wx.Menu):
    def __init__(self, parent):
        super(TextCtrHistoryPopup, self).__init__()
        self.parent = parent
        menus = []
        if self.parent.CanCut():
            menus.append(('Cut', self.parent.onCut, None))
        else:
            menus.append(('-Cut', self.parent.onCut, None))

        if self.parent.CanCopy():
            menus.append(('Copy', self.parent.onCopy, None))
        else:
            menus.append(('-Copy', self.parent.onCopy, None))

        if self.parent.CanPaste():
            menus.append(('Paste', self.parent.onPaste, None))
        else:
            menus.append(('-Paste', self.parent.onPaste, None))

        menus.append(('Delete', self.parent.onDelete, None))
        menus.append(('---', None, None))
        menus.append(('Select All ', self.parent.onSelectAll, None))

        hist = (self.parent._key_history_st1 +
                list(reversed(self.parent._key_history_st2)))

        if len(hist) > 0:
            menus.append(('---', None, None))
            menus.append(('+History', None, None))
            for i in range(len(hist)):
                def func(evt, idx=i, parent=self.parent, hist=hist):
                    a = hist[:idx+1]
                    b = list(reversed(hist[idx+1:]))
                    parent._key_history_st1 = a
                    parent._key_history_st2 = b
                    parent.SetValue(hist[idx])
                menus.append(("\\"+hist[i], func, None))

            def func(evt, hist=hist):
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject("\n".join(hist)))
                    wx.TheClipboard.Close()
            menus.append(('Export history', func, None))
            menus.append(('!', None, None))

        cbook.BuildPopUpMenu(self, menus)


class TextCtrlCopyPasteHistory(TextCtrlCopyPaste):
    '''
    TextControlWithHistory
    '''

    def __init__(self, *args, **kargs):
        TextCtrlCopyPaste.__init__(self, *args, **kargs)
        self._key_history_st1 = []
        self._key_history_st2 = []
        # self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_CONTEXT_MENU, self.onContext)

    def onCopy(self, evt):
        self.Copy()

    def onPaste(self, evt):
        self.Paste()

    def onCut(self, evt):
        self.Cut()

    def onDelete(self, evt):
        st, et = self.GetSelection()
        self.Remove(st, et)

    def onSelectAll(self, evt):
        self.SelectAll()

    def onContext(self, evt):
        m = TextCtrHistoryPopup(self)
        self.PopupMenu(m)  # ifigure_popup(self),
        m.Destroy()

    def onKeyPressed(self, event):
        key = event.GetKeyCode()
        if hasattr(event, 'RawControlDown'):
            controlDown = event.RawControlDown()
        else:
            controlDown = event.ControlDown()
        altDown = event.AltDown()

        if key == wx.WXK_UP:
            if len(self._key_history_st1) == 0:
                return
            v = self._key_history_st1.pop()
            self._key_history_st2.append(v)
            if len(self._key_history_st1) == 0:
                return
            self.SetValue(self._key_history_st1[-1])
            return
        elif key == wx.WXK_DOWN:
            if len(self._key_history_st2) == 0:
                return
            v = self._key_history_st2.pop()
            self._key_history_st1.append(v)
            if len(self._key_history_st1) == 0:
                return
            self.SetValue(self._key_history_st1[-1])
            return
        return TextCtrlCopyPaste.onKeyPressed(self, event)

    def onEnter(self, evt):
        self.add_current_to_history()
        TextCtrlCopyPaste.onEnter(self, evt)

    def add_current_to_history(self):
        v = self.GetValue()
        if len(v.strip()) == 0:
            return
        if (v not in self._key_history_st1 and
                v not in self._key_history_st2):
            self._key_history_st1.append(v)


class TextCtrlCopyPasteGeneric(TextCtrlCopyPaste):
    '''
    TextCtrlCopyPasteGeneric is TextCtrlCopyPaste
    w/o calling sendevent
    '''

    def onEnter(self, evt):
        evt.Skip()


class TextCtrlCopyPasteGenericHistory(TextCtrlCopyPasteGeneric):
    '''
    TextControlWithHistory (no sendevent)
    '''

    def __init__(self, *args, **kargs):
        TextCtrlCopyPasteGeneric.__init__(self, *args, **kargs)
        self._key_history_st1 = []
        self._key_history_st2 = []

    def onKeyPressed(self, event):
        key = event.GetKeyCode()
        if hasattr(event, 'RawControlDown'):
            controlDown = event.RawControlDown()
        else:
            controlDown = event.ControlDown()
        altDown = event.AltDown()

        if key == wx.WXK_UP:
            if len(self._key_history_st1) == 0:
                return
            v = self._key_history_st1.pop()
            self._key_history_st2.append(v)
            if len(self._key_history_st1) == 0:
                return
            self.SetValue(self._key_history_st1[-1])
            return
        elif key == wx.WXK_DOWN:
            if len(self._key_history_st2) == 0:
                return
            v = self._key_history_st2.pop()
            self._key_history_st1.append(v)
            if len(self._key_history_st1) == 0:
                return
            self.SetValue(self._key_history_st1[-1])
            return
        return TextCtrlCopyPasteGeneric.onKeyPressed(self, event)

    def onEnter(self, evt):
        v = self.GetValue()
        self._key_history_st1.append(v)
        evt.Skip()


class ArrayTextCtrl(Panel):
    def __init__(self, parent, id, **setting):
        row = setting.pop('row', 1)
        col = setting.pop('col', 1)
        textsetting = setting.pop('text_setting', [])
        super(ArrayTextCtrl, self).__init__(parent, id, **setting)
        sizer = GridSizer(row, col)
        self.SetSizer(sizer)
        self._text_ctrl = [None]*len(textsetting)
        for i, s in enumerate(textsetting):
            self._text_ctrl[i] = TextCtrlCopyPaste(self, wx.ID_ANY,
                                                   '',
                                                   style=wx.TE_PROCESS_ENTER,
                                                   **s)
            sizer.Add(self._text_ctrl[i], 1, wx.ALL | wx.EXPAND, 1)
        self.Layout()

    def GetValue(self):
        return [w.GetValue() for w in self._text_ctrl]

    def SetValue(self, val):
        for i, v in enumerate(val):
            self._text_ctrl[i].SetValue(val[i])


class Slider(wx.Panel):
    def __init__(self, parent, id, setting=None):
        super(Slider, self).__init__(parent, id)
        ##
        # internally it translates (minV, maxV)
        # to (0, datamax)
        ##
        self.minV = setting["minV"]
        self.maxV = setting["maxV"]
        self.datamax = (self.maxV-self.minV)/setting["res"]
        self.s1 = wx.Slider(self, wx.ID_ANY,
                            self._val2data(setting["val"]),
                            0, int(self.datamax),
                            wx.DefaultPosition, size=(120, -1))
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.t1 = None
        if "text_box" in setting:
            if setting["text_box"] == True:
                self.t1 = TextCtrlCopyPaste(self, wx.ID_ANY,
                                            str(setting["val"]),
                                            style=wx.TE_PROCESS_ENTER)
                sizer.Add(self.t1, 0, wx.EXPAND)
                self.Bind(wx.EVT_TEXT_ENTER, self._Update, self.t1)
        self.Bind(wx.EVT_SLIDER, self._Update, self.s1)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.thumbrelease, self.s1)
        sizer.Add(self.s1, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def SetValue(self, value):
        self.s1.SetValue(self._val2data(float(value)))
        if self.t1 is not None:
            self.t1.SetValue(value)

    def GetValue(self):
        return self._data2val(self.s1.GetValue())

    def _val2data(self, x):
        return int((x-self.minV)/(self.maxV-self.minV)*self.datamax)

    def _data2val(self, data):
        return (self.maxV-self.minV)*data/self.datamax+self.minV

    def _Update(self, evt):
        if evt.GetEventObject() == self.s1:
            val = self.GetValue()
            if self.t1 is not None:
                self.t1.SetValue(str(val))
        if evt.GetEventObject() == self.t1:
            val = float(self.t1.GetValue())
#           print val
            val = min([val, self.maxV])
            val = max([val, self.minV])
            if self.t1 is not None:
                self.t1.SetValue(str(val))
            self.s1.SetValue(self._val2data(val))

#        this allows more interactive update of screen
#        but it makes undo difficult
#        self.GetParent().send_event(self, evt)
    def send_event(self, obj, evt):
        self._Update(evt)

    def thumbrelease(self, evt):
        #        print 'release'
        self.GetParent().send_event(self, evt)


class TickLocator(Panel):
    def __init__(self, parent, id, setting=None):
        Panel.__init__(self, parent, id)
        s = wx.BoxSizer(wx.VERTICAL)
        s2 = setting = {"style": wx.TE_PROCESS_ENTER,
                        "choices": ["Auto", "[0, 0.25, 0.5, 0.75, 1]"]}
        self.cb = ComboBox(self, wx.ID_ANY,
                           style=s2["style"],
                           choices=s2["choices"])
        s.Add(self.cb, 1, wx.ALL, 1)
        self.SetSizer(s)

    def SetValue(self, value):
        if value is None:
            self.cb.SetValue('Auto')
        else:
            self.cb.SetValue(str(value))

    def GetValue(self):
        if self.cb.GetValue() == 'Auto':
            return None
        else:
            try:
                value = eval(self.cb.GetValue())
            except:
                value = None
            return value


class XYAnchor(Panel):
    l1 = ["left", "center", "right"]
    l2 = ["bottom", "center", "top"]

    def __init__(self, parent, id, setting=None):
        super(XYAnchor, self).__init__(parent, id)
        self.cb1 = ComboBoxCompact(self, wx.ID_ANY,
                                   size=(-1, -1),
                                   style=wx.CB_READONLY,
                                   choices=self.l1)
        self.cb2 = ComboBoxCompact(self, wx.ID_ANY,
                                   size=(-1, -1),
                                   style=wx.CB_READONLY,
                                   choices=self.l2)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.GetSizer().Add(self.cb1, 1, wx.EXPAND)
        self.GetSizer().Add(self.cb2, 1, wx.EXPAND)
        self.cb1.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.cb2.Bind(wx.EVT_COMBOBOX, self.onHit)

    def onHit(self, evt):
        self.send_event(self, evt)

    def SetValue(self, value):
        self.cb1.SetValue(self.l1[value[0]])
        self.cb2.SetValue(self.l2[value[1]])

    def GetValue(self):
        return (self.l1.index(str(self.cb1.GetValue())),
                self.l2.index(str(self.cb2.GetValue())))


class XYResize(Panel):
    def __init__(self, parent, id, setting=None):
        super(XYResize, self).__init__(parent, id)
        self.t1 = TextCtrlCopyPaste(self, wx.ID_ANY,
                                    '100',
                                    style=wx.TE_PROCESS_ENTER)
        self.t2 = TextCtrlCopyPaste(self, wx.ID_ANY,
                                    '100',
                                    style=wx.TE_PROCESS_ENTER)
        self.cb = wx.CheckBox(self, wx.ID_ANY,  'resize uniformly')
        self.cb2 = wx.CheckBox(self, wx.ID_ANY, 'use normal coods to resize')

        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add(self.t1, 1, wx.EXPAND)
        s2.Add(self.t2, 1, wx.EXPAND)
        s1.Add(s2, 1, wx.EXPAND)
        s1.Add(self.cb, 1, wx.EXPAND)
        s1.Add(self.cb2, 1, wx.EXPAND)
        self.SetSizer(s1)
        self.cb.Bind(wx.EVT_CHECKBOX, self.onHit)
        self.cb2.Bind(wx.EVT_CHECKBOX, self.onHit)
        self.t1.Bind(wx.EVT_TEXT_ENTER, self.onHit)
        self.t2.Bind(wx.EVT_TEXT_ENTER, self.onHit)

    def onHit(self, evt):
        if self.cb.GetValue() and not self.cb2.GetValue():
            self.t2.SetValue(self.t1.GetValue())
            self.t2.Enable(False)
        else:
            self.t2.Enable(True)
        self.send_event(self, evt)

    def SetValue(self, value):
        self.cb.SetValue(value[0])
        self.cb2.SetValue(value[1])
        if value[0] and not value[1]:
            self.t2.Enable(False)
        else:
            self.t2.Enable(True)
        self.t1.SetValue(str(value[2]))
        self.t2.SetValue(str(value[3]))

    def GetValue(self):
        return (self.cb.GetValue(), self.cb2.GetValue(),
                str(self.t1.GetValue()),
                str(self.t2.GetValue()))


class CSlider(CustomSingleSlider):
    def __init__(self, parent, id, setting=None):
        super(CSlider, self).__init__(parent, id)
        ##
        # internally it translates (minV, maxV)
        # to (0, datamax)
        ##
        self._range = [float(setting["minV"]),
                       float(setting["maxV"])]
        self._resolution = float(setting["res"])
        self._generate_motion_event = setting.get('motion_event', False)
        self.Bind(EVT_CDS_CHANGED, self.onCDS_Event)
        if self._generate_motion_event:
            self.Bind(EVT_CDS_CHANGING, self.onCDS_Event)

    def SetValue(self, value):
        import math

        v = (math.ceil((float(value) - self._range[0])/self._resolution)
             * self._resolution
             + self._range[0])
        super(CSlider, self).SetValue(v)

    def GetValue(self):
        import math
        value = super(CSlider, self).GetValue()
        v = (math.ceil((float(value) - self._range[0])/self._resolution)
             * self._resolution
             + self._range[0])
        return v

    def onCDS_Event(self, evt):
        self.GetParent().send_event(self, evt)


class CSliderWithText(wx.Panel):
    def __init__(self, parent, id, setting=None):
        wx.Panel.__init__(self, parent, id)
        ##
        # internally it translates (minV, maxV)
        # to (0, datamax)
        ##
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.minV = setting["minV"]
        self.maxV = setting["maxV"]
        self.datamax = (self.maxV-self.minV)/setting["res"]

        self.s1 = CSlider(self, wx.ID_ANY, setting=setting)
        txt = str(setting.pop("val", ''))
        self.t1 = TextCtrlCopyPaste(self, wx.ID_ANY,
                                    txt,
                                    style=wx.TE_PROCESS_ENTER)

        sizer.Add(self.t1, 0)
        sizer.Add(self.s1, 1, wx.EXPAND)
        self.Bind(wx.EVT_TEXT_ENTER, self._Update, self.t1)
        # self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.thumbrelease, self.s1)
        self.SetSizer(sizer)

    def SetValue(self, value):
        self.s1.SetValue(value)
        self.t1.SetValue(str(value))

    def GetValue(self):
        return self.s1.GetValue()

    def _Update(self, evt):
        if evt.GetEventObject() == self.s1:
            val = self.GetValue()
            self.t1.SetValue(str(val))
        elif evt.GetEventObject() == self.t1:
            try:
                val = float(self.t1.GetValue())
            except:
                val = 0.0
            val = min([val, self.maxV])
            val = max([val, self.minV])
            self.t1.SetValue(str(val))
            self.s1.SetValue(val)
        else:
            print('unknow event soruce')
        self.GetParent().send_event(self, evt)

    def send_event(self, obj, evt):
        self._Update(evt)

#    def thumbrelease(self, evt):
#        self._Update(evt)


class CDoubleSlider(CustomDoubleSlider):
    def __init__(self, parent, id, setting=None):
        super(CDoubleSlider, self).__init__(parent, id)
        ##
        # internally it translates (minV, maxV)
        # to (0, datamax)
        ##
        self._range = [float(setting["minV"]),
                       float(setting["maxV"])]
        self._resolution = float(setting["res"])
        self._generate_motion_event = setting["motion_event"]

        self.Bind(EVT_CDS_CHANGED, self.onCDS_Event)
        if self._generate_motion_event:
            self.Bind(EVT_CDS_CHANGING, self.onCDS_Event)

    def SetValue(self, value):
        import numpy as np
        value = np.array(value, dtype=np.float64)
        v = (np.ceil((value - self._range[0])/self._resolution)
             * self._resolution
             + self._range[0])
        super(CDoubleSlider, self).SetValue(v)

    def GetValue(self):
        import numpy as np
        value = np.array(
            super(CDoubleSlider, self).GetValue(), dtype=np.float64)
        v = (np.ceil((value - self._range[0])/self._resolution)
             * self._resolution
             + self._range[0])
        return v

    def onCDS_Event(self, evt):
        self.GetParent().send_event(self, evt)


class CSliderWithCB(Panel):
    def __init__(self, parent, id, setting=None, setting_sl=None):
        super(CSliderWithCB, self).__init__(parent, id)
        if setting_sl is None:
            setting_sl = {"minV": 0., "maxV": 1., "val": 0.5, "res": 0.01,
                          "text_box": False}
        if setting is None:
            setting = {"style": wx.TE_PROCESS_ENTER,
                       "choices": ["0", "0.5", "1.0"]}
        self.sl = CSlider(self, wx.ID_ANY, setting=setting_sl)
#        self.sl = SliderAlpha
        self.cb = ComboBox_Float(self,  wx.ID_ANY, **setting)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.GetSizer().Add(self.cb, 0, wx.ALIGN_CENTER)
        self.GetSizer().Add(self.sl, 1, wx.EXPAND)
        self.Bind(EVT_CDS_CHANGED, self.onCDS_Event)
        self._use_float = True

    def GetValue(self):
        if self._use_float:
            return self.sl.GetValue()
        else:
            return int(self.sl.GetValue())

    def SetValue(self, value):
        if value is None:
            self.sl.SetValue(1.0)
            if self._use_float:
                self.cb.SetValue(str(self.sl._range[1]))
            else:
                self.cb.SetValue(str(int(self.sl._range[1])))
        else:
            if not self._use_float:
                v = int(value)
            else:
                v = float(value)
            self.sl.SetValue(v)
            self.cb.SetValue(str(v))

    def onCDS_Event(self, evt):
        self.send_event(self.sl, evt)

    def send_event(self, obj, evt):
        '''
        called from combobox onHit
        '''
        if obj is self.cb:
            v = self.cb.GetValue()
            self.sl.SetValue(str(v))
        else:
            v = self.sl.GetValue()
            self.cb.SetValue(str(v))
        super(CSliderWithCB, self).send_event(self, evt)


class AlphaPanel(CSliderWithCB):
    def __init__(self, parent, id):
        setting = {"style": wx.TE_PROCESS_ENTER,
                   "choices": ["1.0", "0.9", "0.8", "0.7", "0.6",
                               "0.5",  "0.4", "0.3", "0.2", "0.1",
                               "0", "None"]}
        super(AlphaPanel, self).__init__(parent, id, setting=setting)

    def GetValue(self):
        v = self.sl.GetValue()
        cv = str(self.cb.GetValue())

        if cv == 'None':
            return None
        return float(v)

    def SetValue(self, value):
        if value is None:
            self.sl.SetValue(1.0)
            self.cb.SetValue("None")
        else:
            v = float(value)
            self.sl.SetValue(v)
            self.cb.SetValue(str(v))

    def send_event(self, obj, evt):
        '''
        called from combobox onHit
        '''
        if obj is self.cb:
            v = self.cb.GetValue()
            if str(v) == 'None':
                self.sl.SetValue(1.0)
            else:
                self.sl.SetValue(float(v))
        else:
            v = self.sl.GetValue()
            self.cb.SetValue(str(v))
        super(CSliderWithCB, self).send_event(self, evt)


class RotationPanel(CSliderWithCB):
    def __init__(self, parent, id):
        setting = {"style": wx.TE_PROCESS_ENTER,
                   "choices": ["0", "45", "90", "135", "180",
                               "225",  "270", "315"]}
        s = {"minV": 0., "maxV": 359., "val": 90, "res": 1,
             "text_box": False}
        super(RotationPanel, self).__init__(parent, id, setting=setting,
                                            setting_sl=s)
        self._use_float = False


class RadioButtons(wx.Panel):
    def __init__(self, parent, id, val, setting):
        wx.Panel.__init__(self, parent, id)
        self.widgets = []

        if 'orientation' in setting:
            o = setting['orientation']
        else:
            o = 'horizontal'
        if o == 'horizontal':
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer0 = wx.BoxSizer(wx.HORIZONTAL)
        else:
            sizer0 = wx.BoxSizer(wx.VERTICAL)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
        First = True

        for item in setting["values"]:
            if First:
                w = wx.RadioButton(self, wx.ID_ANY, item, style=wx.RB_GROUP)
                First = False
            else:
                w = wx.RadioButton(self, wx.ID_ANY, item)

            if item == val:
                w.SetValue(True)

            self.widgets.append(w)
            sizer0.Add(w, 0, wx.EXPAND)
            self.Bind(wx.EVT_RADIOBUTTON, self.onHit, w)

        sizer.Add(sizer0, 0, wx.ALIGN_LEFT)
        self.SetSizer(sizer)

    def GetValue(self):
        for w in self.widgets:
            if w.GetValue():
                return w.GetLabelText()

    def SetValue(self, value):
        chk = False
        for w in self.widgets:
            if value == w.GetLabelText():
                w.SetValue(True)
                chk = True
            else:
                w.SetValue(False)

        return chk

    def onHit(self, evt):
        self.GetParent().send_event(self, evt)


class ELP(Panel):
    def __init__(self, parent, id, setting=None):
        Panel.__init__(self, parent, id)
        self.elp = (EditListPanel(self, setting["elp"], setting["tip"], call_sendevent=self, edge=0)
                    if "tip" in setting else
                    EditListPanel(self, setting["elp"], call_sendevent=self, edge=0))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.elp, 1, wx.EXPAND, 0)

    def SetValue(self, value):
        self.elp.SetValue(value)

    def GetValue(self):
        return self.elp.GetValue()


class ComboBoxModifiedELP(Panel):
    '''
    this panel is ELP, which represetns an element
    of array. Attached combobox allows user to select
    the index of array which user wants to edit the
    elements.
    '''

    def __init__(self, parent, id, setting=None):
        Panel.__init__(self, parent, id)

        self.cb = ComboBoxCompact(self, wx.ID_ANY, style=wx.CB_READONLY)
        self.elp = (EditListPanel(self, setting["elp"], setting["tip"], call_sendevent=self)
                    if "tip" in setting else
                    EditListPanel(self, setting["elp"], call_sendevent=self))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.cb,  0)
        sizer.Add(self.elp, 1, wx.EXPAND, 0)
        self.cb.Bind(wx.EVT_COMBOBOX, self.onHit)

        tip = setting.pop('cb_tip', None)
        if tip is not None:
            panel_SetToolTip(self.cb, tip)

    def onHit(self, evt):
        sel = str(self.cb.GetValue())
        index = self.cb_values.index(sel)
        self.elp.SetValue(self.elp_values[index])

    def SetValue(self, value):
        self.cb.Clear()
        for x in value[1]:
            self.cb.Append(x)
        self.cb.adjust_size()
        idx = value[0]
        if idx >= 0:
            self.cb.SetValue(value[1][idx])
            self.elp.SetValue(value[2][idx])
        else:
            if len(value[1]) > 0:
                self.cb.SetValue(value[1][0])
                self.elp.SetValue(value[2][0])
        self.cb_values = value[1]
        self.elp_values = value[2]

    def GetValue(self):
        idx = -1
        sel = self.cb.GetValue()
        if sel in self.cb_values:
            idx = self.cb_values.index(sel)
        self.elp_values[idx] = self.elp.GetValue()
        return idx, self.cb_values, self.elp_values


class SelectableELP(Panel):
    def __init__(self, parent, id, val=(True, None),
                 setting=None):
        Panel.__init__(self, parent, id)
        if setting is None:
            setting = ({}, {})
        self._call_fit = setting[0].pop('call_fit', True)

        st = wx.StaticText(self, wx.ID_ANY, setting[0]['text'])

        self.cb = ComboBoxCompact(self, wx.ID_ANY, style=wx.CB_READONLY)
        self.cb.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.cb.Clear()

        tip = setting[0].pop('cb_tip', None)
        if tip is not None:
            panel_SetToolTip(self.cb, tip)
            if len(setting[0]['text']) > 0:
                panel_SetToolTip(st, tip)

        for x in setting[0]['choices']:
            self.cb.Append(x)
        self.cb.adjust_size()
        self.elps = [(EditListPanel(self, ss['elp'], tip=ss['tip']) if 'tip' in ss else
                      EditListPanel(self, ss['elp']))
                     for ss in setting[1:]]
        for elp in self.elps:
            elp.Layout()
        msizer = wx.BoxSizer(wx.HORIZONTAL)
        mmsizer = wx.BoxSizer(wx.HORIZONTAL)
        csizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(msizer)
        mmsizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        mmsizer.Add(self.cb, 1, wx.ALL, 1)
        if "space" in setting[0]:
            msizer.AddSpacer(setting[0]["space"])
        msizer.Add(csizer, 1, wx.EXPAND)
        csizer.Add(mmsizer, 0, wx.ALL, 1)
#        csizer.Add(self.elp, 1, wx.EXPAND|wx.ALL, 5)
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        self.csizer = csizer
        self.msizer = msizer
#        self.show_elp(self.elp)
        for elp in self.elps:
            self.csizer.Add(elp, 1, wx.EXPAND | wx.ALL, 5)

        self.cb.SetValue(setting[0]['choices'][0])
        self.SetFFShowHide()

    def SetFFShowHide(self):
        idx = self.cb.GetSelection()
        for k, elp in enumerate(self.elps):
            if k == idx:
                self.csizer.Show(elp)
            else:
                self.csizer.Hide(elp)
        p = self
        while p is not None:
            p.Layout()
            p = p.GetParent()
        if (isinstance(self.GetTopLevelParent(), wx.Dialog)
                and self._call_fit):
            self.GetTopLevelParent().Fit()

    def onHit(self, evt):
        self.SetFFShowHide()
        self.send_event(evt.GetEventObject(), evt)

    def GetValue(self):
        v = [self.cb.GetValue()]
        for elp in self.elps:
            v.append(elp.GetValue())
        return v

    def SetValue(self, value):
        self.cb.SetValue(value[0])
        for v, elp in zip(value[1:], self.elps):
            elp.SetValue(v)
        self.SetFFShowHide()

    def onEL_Changed(self, evt):
        self.send_event(evt.GetEventObject(), evt)

    def send_event(self, obj, evt):
        if obj == self.cb:
            self.SetFFShowHide()
#        print self.GetValue()
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)

    def Enable(self, value):
        super(SelectableELP, self).Enable(value)
        if not value:
            self.cb.Enable(False)
            for elp in self.elps:
                elp.Enable(False)
        else:
            self.cb.Enable(True)
            for elp in self.elps:
                elp.Enable(True)


class CheckBoxModifiedELP(Panel):
    def __init__(self, parent, id, val=(True, None),
                 setting=None):
        Panel.__init__(self, parent, id)
        if setting is None:
            setting = ({}, {})

        self.btn = CheckBox(self, id, setting[0]["text"])
        self._ff = False
        self._forward_logic = True
        self.elp = (EditListPanel(self, setting[1]["elp"], tip=setting[1]["tip"])
                    if "tip" in setting[1] else EditListPanel(self, setting[1]["elp"]))
#        self.elp.Hide()
        self.elp.Layout()
        if len(setting) == 3:
            self.elp2 = (EditListPanel(self, setting[2]["elp"], tip=setting[2]["tip"])
                         if "tip" in setting[1] else EditListPanel(self, setting[2]["elp"]))

#           self.elp2.Hide()
            self.elp2.Layout()
            self._ff = True
        msizer = wx.BoxSizer(wx.HORIZONTAL)
        csizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(msizer)
        if "space" in setting[0]:
            msizer.AddSpacer(setting[0]["space"])
        msizer.Add(csizer, 1, wx.EXPAND)
        csizer.Add(self.btn, 0, wx.ALL, 1)
#        csizer.Add(self.elp, 1, wx.EXPAND|wx.ALL, 5)
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        self.csizer = csizer
        self.msizer = msizer
#        self.show_elp(self.elp)
        self.csizer.Add(self.elp, 1, wx.EXPAND | wx.ALL, 5)
        if self._ff:
            self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
            self.csizer.Add(self.elp2, 1, wx.EXPAND | wx.ALL, 5)
#             self.show_elp(self.elp2)
            self.SetFFShowHide()
        else:
            self.Layout()

    def _set_size(self):
        print((self.elp.GetSize(), self.elp2.GetSize()))

#   self.elp[i]=EditListPanel(nb, [x[0:4] for x in list])
#   value = DialogEditListTab(tab, l, tip=tip, parent=parent,
#                 style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    def hide_elp(self, elp):
        self.csizer.Hide(elp)

    def show_elp(self, elp):
        self.csizer.Show(elp)

    def SetFFShowHide(self):
        if self.btn.GetValue():
            self.show_elp(self.elp)
            self.hide_elp(self.elp2)
        else:
            self.show_elp(self.elp2)
            self.hide_elp(self.elp)
        p = self
        while p is not None:
            p.Layout()
#            p.SendSizeEvent()
            p = p.GetParent()

#        self.SendSizeEvent()
#        self.csizer.Layout()
#        self.GetTopLevelParent().Layout()
#        self.GetTopLevelParent().SendSizeEvent()
#        wx.CallAfter(self.csizer.Layout)

    def GetValue(self):
        if not self._ff:
            v = (self.btn.GetValue(),
                 self.elp.GetValue())
        else:
            v = (self.btn.GetValue(),
                 self.elp.GetValue(),
                 self.elp2.GetValue())
#        print v
        return v

    def SetValue(self, value):
        self.btn.SetValue(value[0])
        flag = self.btn.GetValue()
        flag = flag if self._forward_logic else (not flag)
        self.elp.Enable(True)  # must be enabled before setting the value...
        self.elp.SetValue(value[1])
        self.elp.Enable(flag)
        if self._ff:
            self.elp.Enable(True)
            self.elp2.Enable(True)
            self.elp2.SetValue(value[2])
            self.SetFFShowHide()

    def onEL_Changed(self, evt):
        self.send_event(evt.GetEventObject(), evt)

    def send_event(self, obj, evt):
        if obj == self.btn:
            flag = self.btn.GetValue()
            flag = flag if self._forward_logic else (not flag)
            self.elp.Enable(flag)
            if self._ff:
                self.elp.Enable(True)
                self.elp2.Enable(True)
                self.SetFFShowHide()
#        print self.GetValue()
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)

    def Enable(self, value):
        super(CheckBoxModifiedELP, self).Enable(value)
        if not value:
            self.elp.Enable(False)
            if self._ff:
                self.elp2.Enable(False)
        else:
            flag = self.btn.GetValue()
            flag = flag if self._forward_logic else (not flag)
            self.elp.Enable(flag)
            if self._ff:
                self.elp.Enable(True)
                self.elp2.Enable(True)


class CheckBoxModified(Panel):
    def __init__(self, parent, id, cls, val=(True, None),
                 setting=None):
        Panel.__init__(self, parent, id)
        if setting is None:
            setting = ({}, {})
        self.btn = CheckBox(self, id, setting[0]["text"])
        self.p = cls(self, id, setting=setting[1])
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self.btn, 0, wx.ALL, 1)
        self.GetSizer().Add(self.p, 1, wx.EXPAND | wx.ALL, 1)
        self.Layout()

    def GetValue(self):
        return (self.btn.GetValue(),
                self.p.GetValue())

    def SetValue(self, value):
        self.btn.SetValue(value[0])
        if value[0]:
            self.p.Enable(True)
        else:
            self.p.Enable(False)
        self.p.SetValue(value[1])

    def send_event(self, obj, evt):
        if obj == self.btn:
            self.p.Enable(self.btn.GetValue())
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)


class CheckBox(wx.CheckBox):
    def __init__(self, *args, **kargs):
        super(CheckBox, self).__init__(*args, **kargs)
        self.Bind(wx.EVT_CHECKBOX, self.onHit)

    def onHit(self, evt):
        self.GetParent().send_event(self, evt)


class ComboBoxCompact(wx.ComboBox):
    def __init__(self, *args, **kargs):
        super(ComboBoxCompact, self).__init__(*args, **kargs)
        if 'style' in kargs:
            if kargs['style'] != wx.CB_READONLY:
                self.Bind(wx.EVT_TEXT_ENTER, self.onHit)
        self.adjust_size()

    def adjust_size(self):
        comboStrings = self.Strings
        if len(comboStrings) == 0:
            self.SetMinSize(wx.DefaultSize)
        else:
            txt_w = max([self.Parent.GetTextExtent(s.strip())[0]
                         for s in comboStrings])
            extra_w = self.Parent.GetTextExtent("AA")[0]
            txt_h = self.Size[1]
            self.SetMinSize((txt_w+txt_h+extra_w, txt_h))

#        args[0].SetSize((txt_w-txt_h,-1))
#        self.SetMinSize((10,-1))
#        self.SetMaxSize((txt_w-10,-1))
#            print txt_w, self.Strings


class ComboBox(ComboBoxCompact):
    def __init__(self, *args, **kargs):
        self.choices_cb = kargs.pop("choices_cb", None)
        super(ComboBox, self).__init__(*args, **kargs)
        self.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.Bind(wx.EVT_TEXT_ENTER, self.onHit)

        if self.choices_cb is not None:
            self.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.onDropDown)

    def onHit(self, evt):
        self.GetParent().send_event(self, evt)

    def onDropDown(self, evt):
        sel = self.GetValue()
        ch = self.choices_cb()
        if sel in ch:
            idx = ch.index(sel)
        else:
            idx = 0
        self.SetChoices(ch, index=idx)

    def SetChoices(self, ch, index=-1):
        sel = self.GetValue()
        self.Clear()
        for c in ch:
            # if len(c) == 0: continue
            self.Append(c)

        if index != -1:
            self.SetSelection(index)
        else:
            if sel in ch:
                index = ch.index(sel)
                self.SetSelection(index)


class ComboBoxWithNew(ComboBoxCompact):
    def __init__(self, *args, **kargs):
        self.choices_cb = kargs.pop("choices_cb", None)
        self.new_choice_message = kargs.pop(
            "new_choice_msg", "Enger new choice")
        super(ComboBoxWithNew, self).__init__(*args, **kargs)
        self.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.Bind(wx.EVT_TEXT_ENTER, self.onHit)

        if self.choices_cb is not None:
            self.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.onDropDown)

    def onHit(self, evt):
        sel = self.GetValue()
        if sel == 'New...':
            from ifigure.widgets.dialog import textentry
            flag, txt = textentry(self,
                                  self.new_choice_message,
                                  def_string=self._current_value,
                                  center=True)
            choices = [self.GetString(n) for n in range(self.GetCount())]
            if flag:
                choices = choices[:-1]
                choices.append(txt)
                index = choices.index(txt)
                self.SetChoices(choices, index)
                wx.CallAfter(self.GetParent().send_event, self, evt)
            else:
                index = choices.index(self._current_value)
                self.SetChoices(choices, index)
                wx.CallAfter(self.GetParent().send_event, self, evt)
        else:
            self._current_value = sel
            self.GetParent().send_event(self, evt)
        evt.Skip()

    def onDropDown(self, evt):
        sel = self.GetValue()
        self._current_value = sel

        ch = self.choices_cb()
        if sel in ch:
            idx = ch.index(sel)
        else:
            idx = 0
        self.SetChoices(ch, index=idx)

    def SetChoices(self, ch, index=0):
        self.Clear()
        ch = [x for x in ch if x != 'New...']
        ch = ch + ['New...']
        for c in ch:
            if len(c) == 0:
                continue
            self.Append(c)
        index = min(index, len(ch)-1)
        # print("setting index", index)
        self.SetSelection(index)


class ComboBox_Float(ComboBoxCompact):
    def __init__(self, *args, **kargs):
        super(ComboBox_Float, self).__init__(*args, **kargs)
#        self.SetSize((80,-1))
        self.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.Bind(wx.EVT_TEXT_ENTER, self.onHit)
        self._choices = kargs["choices"]
        self._value = None

    def onHit(self, evt):
        new_value = self.GetValue()
        if str(new_value) != str(self._value):
            self.GetParent().send_event(self, evt)

    def SetValue(self, value):
        self._value = value
        for c in self._choices:
            try:
                if float(c) == float(value):
                    return super(ComboBox_Float, self).SetValue(c)
            except:
                pass
        return super(ComboBox_Float, self).SetValue(str(value))

    def GetValue(self):
        try:
            return float(super(ComboBox_Float, self).GetValue())
        except:
            return super(ComboBox_Float, self).GetValue()


class CAxisSelector(ComboBoxCompact):
    def __init__(self, *args, **kargs):
        super(CAxisSelector, self).__init__(*args, **kargs)
        self.Bind(wx.EVT_COMBOBOX, self.onHit)
        self._choices = kargs['choices']

    def onHit(self, evt):
        self.GetParent().send_event(self, evt)

    def SetValue(self, value):
        if self.GetTopLevelParent().canvas is None:
            return
        value = str(value)
        self._check_update_selection()
        return super(CAxisSelector, self).SetValue(value)

    def GetValue(self):
        self._check_update_selection()
        return super(CAxisSelector, self).GetValue()

    def Enable(self, value):
        if value:
            self._check_update_selection()
        v = super(CAxisSelector, self).GetValue()
        super(CAxisSelector, self).SetValue(v)
        return super(CAxisSelector, self).Enable(value)

    def _check_update_selection(self):
        from ifigure.mto.axis_user import CUser
        if self.GetTopLevelParent().canvas is None:
            return
        if len(self.GetTopLevelParent().canvas.selection) == 0:
            return
        if self.GetTopLevelParent().canvas.selection[0]() is None:
            return
        if not isinstance(self.GetTopLevelParent().canvas.selection[0]().figobj, CUser):
            return

        choices = self.GetTopLevelParent(
        ).canvas.selection[0]().figobj.get_caxis_choices()

        if set(self._choices) != set(choices):
            self._update_choices(choices)

    def _update_choices(self, c):
        v = str(super(CAxisSelector, self).GetValue())
        self.Clear()
        for item in c:
            self.Append(str(item))
        self._choices = c
        if v in self._choices:
            super(CAxisSelector, self).SetValue(v)


class GenericCoordsTransform(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        self.widgets = []
        p2 = wx.Panel(self, wx.ID_ANY)
        sizer0 = wx.BoxSizer(wx.HORIZONTAL)
        sizer = FlexGridSizer(rows=2, cols=2)
        st1 = wx.StaticText(p2, wx.ID_ANY, 'x: ')
        self.cb1 = ComboBoxCompact(p2, wx.ID_ANY,
                                   size=(-1, -1),
                                   style=wx.CB_READONLY,
                                   choices=["figure", "axes", "data"])
        st2 = wx.StaticText(p2, wx.ID_ANY, 'y: ')
        self.cb2 = ComboBoxCompact(p2, wx.ID_ANY,
                                   size=(-1, -1),
                                   style=wx.CB_READONLY,
                                   choices=["figure", "axes", "data"])
        self.bt = wx.Button(self, wx.ID_ANY, 'Axes...')
        sizer.Add(st1, 0, wx.ALL, 1)
        sizer.Add(self.cb1, 0, wx.ALL, 1)
        sizer.Add(st2, 0, wx.ALL, 1)
        sizer.Add(self.cb2, 0, wx.ALL, 1)
        sizer0.Add(p2, 0, wx.ALL, 1)
        sizer0.Add(self.bt, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        p2.SetSizer(sizer)
        self.SetSizer(sizer0)
        self.axes = None
        self.bt.Enable(False)
        self.Bind(wx.EVT_COMBOBOX, self.onHit)
        self.Bind(wx.EVT_BUTTON, self.onButton)
        self.axes_sel_mode = False

    def onHit(self, evt):
        self.set_button_eneable()
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)

    def onButton(self, evt):
        self.axes_sel_mode = True
        self.onHit(evt)

    def SetValue(self, value):
        self.cb1.SetValue(value[0][0])
        self.cb2.SetValue(value[0][1])
        self.axes = value[1]
        self.set_button_eneable()

    def GetValue(self):
        value = ([str(self.cb1.GetValue()),
                  str(self.cb2.GetValue())],
                 self.axes, self.axes_sel_mode)
        self.axes_sel_mode = False
        self.set_button_eneable()
        print(('getvalue in generic...', value))

        return value

    def set_button_eneable(self):
        if (str(self.cb1.GetValue()) != 'figure' or
                str(self.cb2.GetValue()) != 'figure'):
            self.bt.Enable(True)
        else:
            self.bt.Enable(False)


class LegendLocPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        param = {}
        s = {"text": 'on'}
        param["draggable"] = ["draggable", True,  3, s]
        s = {"style": wx.CB_READONLY,
             "choices": ['best', 'upper right',  'upper left', 'lower left',
                         'lower right',  'right',  'center left', 'center right',
                         'lower center',  'upper center',  'center']}
        param["legenddrag"] = ["loc", 'best',  4, s]
        l = [param[key] for key in param]
        self.elp = EditListPanel(self, l, call_sendevent=self,
                                 edge=0)
        self.elp.Show()
        self.GetSizer().Add(self.elp,  1, wx.EXPAND)

    def GetValue(self):
        v = self.elp.GetValue()
        return v

    def SetValue(self, value):
        self.elp.SetValue(value[0:2])

    def send_event(self, obj,  evt):
        evt.SetEventObject(self)
#        val =  self.cb.GetValue()
        self.GetParent().send_event(self, evt)


class ArrowStylePanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.cb = ArrowStyleCombobox(self, wx.ID_ANY)
        self.cb.Bind(wx.EVT_COMBOBOX, self.onCBHit)
        self.mode = ''
        self.elp = None
        self.param = {}
        self.param["default"] = []
        s = {"minV": 1, "maxV": 30., "val": 1, "res": 0.1, "text_box": False}
        self.param["head_length"] = ["head L",   '5', 5, s]
        self.param["head_width"] = ["head W",  '5', 5, s]
        self.param["tail_width"] = ["tail W",  '1', 5, s]
        self.param["widthA"] = ["widthA",  '5', 5, s]
        self.param["widthB"] = ["widthB",  '5', 5, s]
        s2 = {"minV": 0, "maxV": 180., "val": 0, "res": 1, "text_box": False}
        self.param["angleA"] = ["angleA",  '5', 5, s2]
        self.param["angleB"] = ["angleB",  '5', 5, s2]
        self.param["lengthA"] = ["lengthA",  '5', 5, s]
        self.param["lengthB"] = ["lengthB",  '5', 5, s]
        s = {"minV": 0.1, "maxV": 10., "val": 1, "res": 0.1, "text_box": False}
        self.param["shrink_factor"] = ["shrink",  '1', 5, s]

        self.panels = {}
        self.panels["-"] = ()
        self.panels["->"] = ("head_length", "head_width")
        self.panels["-["] = ("widthB", "lengthB", "angleB",)
        self.panels["-|>"] = ("head_length", "head_width")
        self.panels["<-"] = ("head_length", "head_width")
        self.panels["<->"] = ("head_length", "head_width")
        self.panels["<|-"] = ("head_length", "head_width")
        self.panels["<|-|>"] = ("head_length", "head_width")
        self.panels["|-|"] = ("widthA", "angleA",
                              "widthB", "angleB",)
        self.panels["]-"] = ("widthA", "lengthA", "angleA",)
        self.panels["]-["] = ("widthA", "lengthA", "angleA",
                              "widthB", "lengthB", "angleB",)
        self.panels["fancy"] = ("head_length", "head_width", "tail_width")
        self.panels["simple"] = ("head_length", "head_width", "tail_width")
        self.panels["wedge"] = ("tail_width", "shrink_factor")
        self.GetSizer().Add(self.cb)
        self.mode = '-'
        self._elp_values = {}
        self.cb.SetValue(self.mode)
        self.elp = None  # wx.Panel(self)

#       self.GetSizer().Add(self.elp,  1, wx.EXPAND)
    def switch_panel(self, mode):
        # print 'switch panel', mode, self.mode
        if self.elp is not None:
            self._elp_values[self.mode] = self.elp.GetValue()
        if mode not in self.panels:
            return False
        if self.mode == mode:
            self.GetParent().Layout()
            # print 'fitting'
            # self.GetParent().Fit()
            # self.GetTopLevelParent()._force_layout()
            return True
        if self.mode != '':
            if self.elp is not None:
                self.GetSizer().Detach(self.elp)
                self.elp.Destroy()
                self.GetParent().Layout()
        self.mode = mode

        keys = self.panels[self.mode]
        l = []
        for k in keys:
            l.append(self.param[k])
        if len(l) != 0:
            self.elp = EditListPanel(self, l, call_sendevent=self,
                                     edge=0)
            self.elp.Show()
            self.GetSizer().Add(self.elp,  1, wx.EXPAND)
            if mode in self._elp_values:
                self.elp.SetValue(self._elp_values[mode])
        else:
            self.elp = None
        self.Layout()
        self.GetParent().Layout()
        self.GetTopLevelParent().Layout()
        return True

    def GetValue(self):
        val = [self.mode]
        for i in range(len(self.panels[self.mode])):
            val.append(self.panels[self.mode][i] +
                       '='+str(self.elp.GetValue()[i]))
        s = ','.join(val)
        # print 'Getting Arrow Panel Value', s
        return s

    def SetValue(self, value):
        # print 'Setting Arrow Panel Value', value
        arr = value.split(',')
        self.cb.SetValue(arr[0])
        self.switch_panel(arr[0])
        if self.elp is not None:
            value = [item.split('=')[1] for item in arr[1:]]
            if len(value) != 0:
                self.elp.SetValue(value)
        return self.cb.SetValue(value)

    def send_event(self, obj,  evt):
        evt.SetEventObject(self)
        val = self.cb.GetValue()
        self.GetParent().send_event(self, evt)

    def onCBHit(self, evt):
        val = self.cb.GetValue()
        self.switch_panel(val)
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)


class ArrowStyleCombobox(wxBitmapComboBox):
    def __init__(self, *args, **kargs):
        from ifigure.ifigure_config import arrowstyle_list
        from ifigure.ifigure_config import icondir
        self.choice_list = arrowstyle_list()
        choices = []
        kargs["choices"] = choices
        kargs["style"] = wx.CB_READONLY
        parent = args[0]
        id = args[1]
        super(ArrowStyleCombobox, self).__init__(parent, id,
                                                 '', (-1, -1), (150, -1),  **kargs)
        for name, style in self.choice_list:
            dirname = os.path.dirname(ifigure.__file__)
            nname = b64encode(name.encode('latin-1')).decode()
            imageFile = os.path.join(icondir, 'image',
                                     'arrow_' + nname + '.png')
            bitmap = wx.Bitmap(imageFile)
            super(ArrowStyleCombobox, self).Append(name, bitmap, name)
        self.SetSelection(3)
#        self.SetValue('-')

    def SetValue(self, value):
        for name, style in self.choice_list:
            if value == style:
                super(ArrowStyleCombobox, self).SetValue(name)
            if value == name:
                super(ArrowStyleCombobox, self).SetValue(name)

    def GetValue(self):
        val = super(ArrowStyleCombobox, self).GetValue()
        for name, style in self.choice_list:
            if val == name:
                return style
            if val == style:
                return style
        return 'simple'


class MDSRange(Panel):
    def __init__(self, parent, id, *args, **kargs):
        Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))

        mm = [['xmin', '-1',  0, {}, ],
              ['xmax', '-1',  0, {}, ], ]
        l = [(None,  (False, ['-1', '-1']), 127,
              ({"text": 'evaluate xrange in TDI'}, {"elp": mm}),), ]
        self.elp1 = EditListPanel(self, l, edge=0, call_sendevent=self)
        mm = [['ymin', '-1',  0, {}, ],
              ['ymax', '-1',  0, {}, ], ]
        l = [(None,  (False, ['-1', '-1']), 127,
              ({"text": 'evaluate yrange in TDI'}, {"elp": mm}),)]
        self.elp2 = EditListPanel(self, l, edge=0, call_sendevent=self)

        self.GetSizer().Add(self.elp1,  1, wx.EXPAND)
        self.GetSizer().Add(self.elp2,  1, wx.EXPAND)

    def GetValue(self):
        v = self.elp1.GetValue()[0]
        a = (v[0], (str(v[1][0]), str(v[1][1])))
        v = self.elp2.GetValue()[0]
        b = (v[0], (str(v[1][0]), str(v[1][1])))
        return a, b

    def SetValue(self, value):
        v = value[0]
        self.elp1.SetValue(((v[0], (str(v[1][0]), str(v[1][1]))),))
        v = value[1]
        self.elp2.SetValue(((v[0], (str(v[1][0]), str(v[1][1]))),))

    def send_event(self, obj, evt):
        self.GetParent().send_event(self, evt)


class MDSFigureType(Panel):
    def __init__(self, parent, id, *args, **kargs):
        Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        s = {"style": wx.CB_READONLY,
             "choices": ["timetrace", "stepplot",
                         "plot", "contour", "image", "axline",
                         "axspan", "text", "surface"]}
        l = [["MDS figure type",  'plot',  4, s], ]

        self.elp = EditListPanel(self, l, edge=0, call_sendevent=self)
        self.st = wx.StaticText(self, wx.ID_ANY, 'explanation')

        self.GetSizer().Add(self.elp,  1, wx.EXPAND)
        self.GetSizer().Add(self.st,   1, wx.EXPAND, 5)
        self.SetValue('plot')

    def GetValue(self):
        value = str(self.elp.GetValue()[0]),
        return str(self.elp.GetValue()[0])

    def SetValue(self, value):
        from ifigure.mdsplus.fig_mds import panel_text
        self.st.SetLabel(panel_text[value])
        self.elp.SetValue([value, ])

    def send_event(self, obj, evt):
        from ifigure.mdsplus.fig_mds import panel_text
        value = str(self.elp.GetValue()[0])
        self.st.SetLabel(panel_text[value])
#        self.set_param_panel(value)
        self.GetParent().send_event(self, evt)


class MDSServerDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="New MDS server"):
        wx.Dialog.__init__(self, parent, id, title)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)

        sizer = FlexGridSizer(3, 2)
        sizer.AddGrowableCol(1, 1)
        st1 = wx.StaticText(self, label="Server")
        self.field = wx.TextCtrl(
            self, value="alcdata.psfc.mit.edu", size=(300, -1))
        st2 = wx.StaticText(self, label="Port")
        self.field2 = wx.TextCtrl(self, value=" ", size=(-1, -1))
        st3 = wx.StaticText(self, label="Defaut Tree")
        self.field3 = wx.TextCtrl(self, value="CMOD", size=(-1, -1))
        sizer.Add(st1, 0, wx.ALL, 2)
        sizer.Add(self.field, 1, wx.ALL | wx.EXPAND, 2)
        sizer.Add(st2, 0, wx.ALL, 2)
        sizer.Add(self.field2, 1, wx.ALL | wx.EXPAND, 2)
        sizer.Add(st3, 0, wx.ALL, 2)
        sizer.Add(self.field3, 1, wx.ALL | wx.EXPAND, 2)

        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.okbutton = wx.Button(self, label="OK", id=wx.ID_OK)
        self.cancelbutton = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)

        self.mainSizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)
        self.buttonSizer.Add(self.okbutton, 0, wx.ALL, 8)
        self.buttonSizer.Add(self.cancelbutton, 0, wx.ALL, 8)
        self.mainSizer.Add(self.buttonSizer, 0, wx.ALL, 0)
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_TEXT_ENTER, self.onOK)
        self.SetSizer(self.mainSizer)
        self.Fit()
        self.result = None

    def onOK(self, event):
        tt = str(self.field2.GetValue().strip())
        port = 'default' if tt == '' else tt
        self.result = {'server': str(self.field.GetValue().strip()),
                       'port': str(self.field2.GetValue().strip()),
                       'tree': str(self.field3.GetValue().strip())}
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def onCancel(self, event):
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()


class ComboBoxPrefList(ComboBox):
    def __init__(self, parent, id, *args, **kargs):
        self.rule = kargs['setting']['rule']  # ('connection', {'server':''...}
        self.pref = kargs['setting']['pref']  # 'mdsplus.mdssever_config'
        self.varname = kargs['setting']['varname']  # 'connection
        self.keyname = kargs['setting']['keyname']
        self.dialog = kargs['setting']['dialog']
        self.defv = kargs['setting']['def_value']
        del kargs['setting']['rule']
        del kargs['setting']['pref']
        del kargs['setting']['varname']
        del kargs['setting']['keyname']
        del kargs['setting']['dialog']
        del kargs['setting']['def_value']
        if len(kargs['setting']) == 0:
            del kargs['setting']
        kargs['style'] = wx.CB_DROPDOWN
        kargs['choices'] = ['']

        self.vars = self._read_list()
        super(ComboBoxPrefList, self).__init__(parent, id, *args, **kargs)
        choices = self._set_menu_item()
        self.SetValue(choices[0])

    def SetValue(self, value):
        if value is None:
            return
        super(ComboBoxPrefList, self).SetValue(value)
        self._valuebk = value

    def _write_list(self):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP().set_rule(*(self.rule))
        var = p.read_setting(self.pref)
        var['connection'] = self.vars
        p.write_setting(self.pref, var)

    def _read_list(self, fromDefault=False):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP().set_rule(*(self.rule))
        var = p.read_setting(self.pref, fromDefault=fromDefault)
        return var[self.varname]

    def _make_choices(self, l):
        choices = [self.defv]
        for x in l:
            choices.append(x[self.keyname])
        choices.append("New...")
        choices.append("Reset Menu")
        l = max([len(t) for t in choices])
        self.SetSizeHints(l*10, -1)
        return choices

    def _set_menu_item(self):
        choices = self._make_choices(self.vars)
        self.Clear()
        for i in choices:
            self.Append(i)
        self.Layout()
        return choices

    def onHit(self, evt):
        if self.GetValue() == 'New...':
            a = self.dialog(self)
            if a is not None:
                self.vars.append(a)
                choices = self._set_menu_item()
                self.SetValue(choices[-3])
                self._write_list()
            else:
                self.SetValue(self._valuebk)
        elif self.GetValue() == 'Reset Menu':
            self.vars = self._read_list(fromDefault=True)
            choices = self._set_menu_item()
            self.SetValue(choices[0])
            self._write_list()
        else:
            self._valuebk = self.GetValue()
            super(ComboBoxPrefList, self).onHit(evt)

    def value_suggestion(self):
        return str(self._valuebk)


class ComboBoxPrefListDirectory(Panel):
    def __init__(self, parent, id, *args, **kargs):
        Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        s = kargs['setting']
        self.cb = ComboBoxPrefList(self, wx.ID_ANY, setting=s)
        self.bt = wx.Button(self, label='Browse...')
        self.bt.Bind(wx.EVT_BUTTON, self.onBrowse)
        self.GetSizer().Add(self.cb, 1, wx.EXPAND | wx.ALL, 2)
        self.GetSizer().Add(self.bt, 0, wx.EXPAND | wx.ALL, 2)

    def SetValue(self, value):
        self.cb.SetValue(value)

    def GetValue(self):
        return self.cb.GetValue()

    def onBrowse(self, evt):
        diag = wx.DirDialog(self)
        ret = diag.ShowModal()
        if ret == wx.ID_OK:
            path = diag.GetPath()
            self.SetValue(path)
        diag.Destroy()


class MDSserver(ComboBox):
    def __init__(self, parent, id, *args, **kargs):
        kargs['style'] = wx.CB_DROPDOWN
        kargs['choices'] = ['']
        self.connections = self._read_connections()
        super(MDSserver, self).__init__(parent, id, *args, **kargs)
        choices = self._set_menu_item()
        self.SetValue(choices[0])

    def _make_choices(self, l):
        choices = []
        for x in l:
            port = '' if x['port'].upper() == 'DEFAULT' else x['port']
            choices.append(x['server']+':'+port+':'+x['tree'])
        choices.append("New Server")
        choices.append("Reset Menu")
        return choices

    def _set_menu_item(self):
        choices = self._make_choices(self.connections)
        self.Clear()
        for i in choices:
            self.Append(i)
        return choices

    def _write_connections(self):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP().set_rule('connection',
                          {'server': '', 'port': '', 'tree': ''})
        var = p.read_setting('mdsplus.mdsserver_config')
        var['connection'] = self.connections
        p.write_setting('mdsplus.mdsserver_config', var)

    def _read_connections(self, fromDefault=False):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP().set_rule('connection',
                          {'server': '', 'port': '', 'tree': ''})
        var = p.read_setting('mdsplus.mdsserver_config',
                             fromDefault=fromDefault)
        return var['connection']

    def onHit(self, evt):
        if self.GetValue() == 'New Server':
            dlg = MDSServerDialog(self)
            a = dlg.ShowModal()
            if a == wx.ID_OK:
                self.connections.append(dlg.result)
                choices = self._set_menu_item()
                self.SetValue(choices[-3])
                self._write_connections()
        elif self.GetValue() == 'Reset Menu':
            self.connections = self._read_connections(fromDefault=True)
            choices = self._set_menu_item()
            self.SetValue(choices[0])
            self._write_connections()
        else:
            super(MDSserver, self).onHit(evt)


class FilePath(Panel):
    def __init__(self, parent, id, *args, **kargs):
        self.wildcard = kargs.pop("wildcard", "*")
        self.defaultpath = kargs.pop("defaultpath", "")
        self.message = kargs.pop("message", "Select file to read")
        Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.t1 = TextCtrlCopyPaste(self, wx.ID_ANY,
                                    '',
                                    style=wx.TE_PROCESS_ENTER)
        self.bt = wx.Button(self, label='Browse...')
        self.bt.Bind(wx.EVT_BUTTON, self.onBrowse)
        self.GetSizer().Add(self.t1, 1, wx.EXPAND | wx.ALL, 2)
        self.GetSizer().Add(self.bt, 0, wx.EXPAND | wx.ALL, 2)

    def SetValue(self, value):
        self.t1.SetValue(value)

    def GetValue(self):
        return str(self.t1.GetValue())

    def onBrowse(self, evt):
        from ifigure.widgets.dialog import read
        file = self.GetValue()
        defaultdir = os.path.dirname(file)
        defaultfile = file if self.defaultpath == '' else self.defaultpath
        path = read(parent=self,
                    message=self.message,
                    wildcard=self.wildcard,
                    defaultfile=defaultfile,
                    defaultdir=defaultdir)
        if path != '':
            self.SetValue(path)
            self.send_event(self, evt)


class MDSSource0(wx.Panel):
    bitmaps = None
    tag_order = ['x', 'y', 'z', 'xerr', 'yerr']

    def __init__(self, parent, id, *args, **kargs):
        if MDSSource0.bitmaps is None:
            from ifigure.utils.cbook import make_bitmap_list
            from ifigure.ifigure_config import icondir as path
            path1 = os.path.join(path, '16x16', 'variable.png')
            path2 = os.path.join(path, '16x16', 'script.png')
            MDSSource0.bitmaps = make_bitmap_list([path1, path2])

        wx.Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetSizer().Add(sizer, 1, wx.EXPAND)
        self.mode = ''
        self.l = [["experiment", "cmod", 200],
                  ["default_node", "", 200],
                  ["title", "", 200], ]
        self.elp = EditListPanel(self, self.l, call_sendevent=self,
                                 edge=0)
        self.bt_var = wx.BitmapButton(self, wx.ID_ANY,
                                      MDSSource0.bitmaps[0])  # 'Add Variable...')
#       self.elp.Show()
        from ifigure.widgets.script_editor import Notebook
        self.nb = aui.AuiNotebook(self, wx.ID_ANY)  # , style=aui.AUI_NB_TOP)
        sigs = ["x", "y", "z", "xerr", "yerr"]
        self._always = []
        for i, tt in enumerate(sigs):
            #           panel = wx.Panel(self.nb)
            #           sizer2 = wx.BoxSizer(wx.VERTICAL)
            #           panel.SetSizer(sizer2)
            p = self._new_stc(self.nb, ' ')
#           sizer2.Add(p, 1, wx.EXPAND|wx.ALL)
            title = '{:>3s}'.format(tt)
            self.nb.AddPage(p, title, select=True)
        self.rb_mask = wx.CheckBox(self, wx.ID_ANY, 'Always Evaluate')
        mini_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mini_sizer.Add(self.elp, 1, wx.EXPAND | wx.ALL)
        mini_sizer.Add(self.bt_var, 0, wx.ALIGN_CENTER | wx.ALL, 2)
        sizer.Add(mini_sizer,  0, wx.EXPAND | wx.ALL)
        sizer.Add(self.nb,  1, wx.EXPAND | wx.ALL)
        sizer.Add(self.rb_mask, 0, wx.ALL, 1)
#       self.Layout()
        self.nb.SetSelection(1)
#       self.nb.SetSize((450,400))
#       self.nb.Show()
#       wx.CallAfter(self.nb.Fit)
#       print self.GetSize()
        self.Bind(wx.EVT_SIZE, self.OnSize, self)
        self.bt_var.Bind(wx.EVT_BUTTON, self.onAddVar)
        self.rb_mask.Bind(wx.EVT_CHECKBOX, self.onHitAlways)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED,
                  self.onPageChanging, self.nb)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onPageClose, self.nb)

    def onPageChanging(self, evt):
        ipage = self.nb.GetSelection()
        txt = self.nb.GetPageText(ipage)
        txt = ''.join(txt.split('*'))
        self.rb_mask.SetValue(txt in self._always)
        evt.Skip()

    def OnSize(self, evt):
        #        print 'onSize', self.GetSize(), self.GetParent().GetSize()
        self.SetSize((self.GetSize()[0], self.GetParent().GetSize()[1]-10))
        evt.Skip()
        # return wx.Panel.OnSize(self, evt)

    def GetValue(self):
        v = self.elp.GetValue()
        val = {'experiment': v[0],
               'default_node': v[1],
               'title': v[2], }

        sigs = list(self.pages2data())
        for i, name in enumerate(sigs):
            p = self.nb.GetPage(i)
            name = ''.join(name.split('*'))
            name = name.strip()
            val[name] = str(p.GetText())
        val['_flag'] = self._always
        return val

    def onPageClose(self, evt):
        ipage = self.nb.GetSelection()
        label = self.nb.GetPageText(ipage).strip()
        # print(label, 'closing')
        if str(label) in ['x', 'y', 'z', 'xerr', 'yerr']:
            ret = dialog.message(self,
                                 '"'+label+'"' + " is reserved and cannot be deleted",
                                 'Error',
                                 0)
            evt.Veto()
            return
        if label in self._always:
            self._always.remove(label)

    def SetValue(self, value):
        self.elp.SetValue([value['experiment'],
                           value['default_node'],
                           value['title']])
        sigs = list(value)
        for key in ['experiment', 'default_node', 'title', 'event', '_flag']:
            if key in sigs:
                sigs.remove(key)
        for key in sigs:
            if value[key] is None:
                sigs.remove(key)

        sigs2 = []
        for name in sigs:
            if not name in MDSSource0.tag_order:
                sigs2.append(name)
        sigs2.extend(MDSSource0.tag_order)

        npage = len(sigs2)
        while self.nb.GetPageCount() != npage:
            if self.nb.GetPageCount() > npage:
                self.nb.DeletePage(self.nb.GetPageCount()-1)
            elif self.nb.GetPageCount() < npage:
                title = 'tmp_key' + str(self.nb.GetPageCount())
                p = self._new_stc(self.nb, '')
                title = '{:>3s}'.format(title)
                self.nb.AddPage(p, title, select=True)
                self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)
        for ipage, key in enumerate(sigs2):
            self.nb.SetPageText(ipage, key)
            p = self.nb.GetPage(ipage)
            self._set_stc_txt(p, value[key])

        if '_flag' in value:
            self._always = value['_flag']
        else:
            self._always = []

    def send_event(self, obj,  evt):
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)

    def _new_stc(self, parent, txt):
        from ifigure.widgets.script_editor import PythonSTC
        p = PythonSTC(parent, -1)
        self._set_stc_txt(p, txt)
        p.EmptyUndoBuffer()
        p.Colourise(0, -1)
        # line numbers in the margin
        p.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        p.SetMarginWidth(1, 25)
        return p

    def _set_stc_txt(self, p, txt):
        #        mod = p.GetModify()
        try:
            p.SetText(txt)
#            if not mod: p.SetSavePoint()
        except UnicodeDecodeError:
            if six.PY2:
                p.SetText(unicode(txt, errors='ignore'))
            else:
                assert False, "_set_stc_txt got unicode error"
#            if not mod: p.SetSavePoint()

    def onHitAlways(self, evt):
        ipage = self.nb.GetSelection()
        txt = self.nb.GetPageText(ipage)
        txt = ''.join(txt.split('*'))
        if self.rb_mask.GetValue():
            if not str(txt) in self._always:
                self._always.append(str(txt))
        else:
            self._always = [x for x in self._always if x != str(txt)]
        evt.Skip()

    def onAddVar(self, evt):
        dlg = TextEntryDialog(self.GetTopLevelParent(),
                              "Enter the name of variable", "Add variable", "")
        if dlg.ShowModal() == wx.ID_OK:
            #            self.Freeze()
            new_name = str(dlg.GetValue())
            data = self.pages2data()
            if new_name in data:
                dlg.Destroy()
                return
#            len(data.keys())
            p = self._new_stc(self.nb, '')
            self.nb.InsertPage(0, p, new_name, True)
            self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)
#            data[new_name] = ''
#            self.data2pages(data)
        dlg.Destroy()

    def pages2data(self):
        data = OrderedDict()
        for ipage in range(self.nb.GetPageCount()):
            name = str(self.nb.GetPageText(ipage))
            if name.startswith('*'):
                name = name[1:]
            p = self.nb.GetPage(ipage)
            data[name] = str(p.GetText()).strip()
            p.SetSavePoint()
        return data

    def onModified(self, e=None):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
#        self.nb.SetPageTextModifiedMark(ipage, p.GetModify())


class MDSSource(wx.Panel):
    # this panel is not used any more...
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
#       self.mode=''
        self._current_labels = ['']
        self.elp = None
        # self.elp = EditListPanel(self, self.l, call_sendevent=self,
        #                         edge = 0)
        self.st = wx.StaticText(self, wx.ID_ANY, 'MDS+ session object')
#       self.bt = wx.Button(self, wx.ID_ANY, 'Editor...')
#       self.elp.Show()

#       self.GetSizer().Add(self.elp,  1, wx.EXPAND)
        self.GetSizer().Add(self.st,   0, wx.ALL | wx.ALIGN_CENTER, 1)
#       self.GetSizer().Add(self.bt,  0, wx.ALIGN_RIGHT|wx.ALL, 2)
#       self.Bind(wx.EVT_BUTTON, self.onButton)
        self._figmds = None

    def GetValue(self):
        #        v = self.elp.GetValue()
        #        val = [(self.l[k][0], v[k]) for k in range(len(v))]
        return None

    def SetValue(self, value):
        #        self.elp.SetValue(value["data"])
        self._figmds = weakref.ref(value["figmds"])
        ax = self._figmds().get_figaxes()
        from ifigure.mdsplus.fig_mds import FigMds

        sessions = [child for name, child in ax.get_children()
                    if isinstance(child, FigMds)]
        labels = []
        for s in sessions:
            v = s.getvar('mdsvars')
            lines = [str(k) + ':' + v[k].__repr__() for k in v]
            lines = [(l + ' '*25)[:25] for l in lines]
            labels.append('\n'.join(lines))
        if self._current_labels == labels:
            return

        if self.elp is not None:
            self.GetSizer().Detach(self.elp)
            self.elp.Destroy()
            self.elp = None
        l4 = []
        for k, l in enumerate(labels):
            def handler(evt, ichild=k, figmds=self._figmds):
                ax = figmds().get_figaxes()
                sessions = [child for name, child in ax.get_children()
                            if isinstance(child, FigMds)]
                sessions[ichild].onDataSetting(evt)

            if isinstance(l, str):
                l = l.encode()
            ll = l.decode('unicode_escape')

            l4.append([ll, None, 141, {"label": "Edit...",
                                       'func': handler,
                                       'noexpand': True,
                                       'alignright': True}])

        self.elp = EditListPanel(self, l4, call_sendevent=self,
                                 edge=0)
        self.GetSizer().Add(self.elp,   0, wx.ALL | wx.EXPAND, 1)
        self.GetTopLevelParent().Layout()


#        self.elp = EditListPanel(self, self.l, call_sendevent=self,
#                                edge = 0)

#        if value["posvars"] is not None:
#            self.st.SetLabel( value["posvars"])
#            self.st.Refresh()
#        else:
#            self.st.SetLabel('Posiiton vars undefined')
#            self.st.Refresh()

#    def onButton(self, evt):
#        if self._figmds is None: return
#        if self._figmds() is None: return
#        evt.SetEventObject(self)
#        self.elp.Enable(False)
#        self._figmds().onDataSetting(evt)


    def data_setting_closed(self):
        pass
#        self.elp.Enable(True)

    def send_event(self, obj,  evt):
        evt.SetEventObject(self)
        self.GetParent().send_event(self, evt)


class MDSGlobalSelection(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id)
        sizer = GridSizer(4, 4)
        self.SetSizer(sizer)

        self.cb = [None]*16
        for i in range(16):
            minisizer = wx.BoxSizer(wx.VERTICAL)
            st = wx.StaticText(self, wx.ID_ANY, 'Shot '+str(i+1))
            self.cb[i] = ComboBoxCompact(self, wx.ID_ANY,
                                         style=wx.CB_READONLY,
                                         choices=["1", "2", "3", "4"])
            minisizer.Add(st, 1, wx.ALIGN_CENTER | wx.TOP, 3)
            minisizer.Add(self.cb[i], 1, wx.EXPAND)
            sizer.Add(minisizer, 1, wx.EXPAND)

    def GetValue(self):
        val = [int(cb.GetValue()) for cb in self.cb]
        return val

    def SetValue(self, value):
        for i in range(16):
            self.cb[i].SetValue(str(value[i]))


class GL_Lighting(Panel):
    setting = {"minV": 0.,
               "maxV": 2.,
               "val": 0.5,
               "res": 0.01,
               "motion_event": True}
    setting2 = {"minV": -180.,
                "maxV": 180.,
                "val": 0.,
                "res": 0.1,
                "motion_event": True}
    setting3 = {"minV": 0.,
                "maxV": 180.,
                "val": 0.,
                "res": 0.1,
                "motion_event": True}

    l = [["Light type", "", 2],
         [" Ambient", 0.5, 124, setting],
         [" Diffuse", 0.5, 124, setting],
         [" Spcecular", 0.5, 124, setting],
         ["Light location", "", 2],
         [" Phi", 0., 124, setting2],
         [" Theta", 0., 124, setting3],
         [None, True, 3, {"text": "Shadow Map"}],
         [None,    True, 3, {"text": "Frustum"}],
         ]

    def __init__(self, parent, id):
        Panel.__init__(self, parent, id)
        self.elp = EditListPanel(self, GL_Lighting.l, call_sendevent=self,
                                 edge=0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.elp, 1, wx.EXPAND)

    def SetValue(self, value):
        self.elp.SetValue(value)

    def GetValue(self):
        v = self.elp.GetValue()
        return v


class GL_View(Panel):
    setting2 = {"minV": -180.,
                "maxV": 180.,
                "val": 0.,
                "res": 0.1,
                "motion_event": True}
    setting3 = {"minV": -180.,
                "maxV": 180.,
                "val": 0.,
                "res": 0.1,
                "motion_event": True}

    l = [["View location", "", 2],
         [" Azim", 0., 124, setting2],
         [" Elev", 0., 124, setting3], ]

    def __init__(self, parent, id):
        Panel.__init__(self, parent, id)
        self.elp = EditListPanel(self, GL_View.l,
                                 call_sendevent=self,
                                 edge=0)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.elp, 1, wx.EXPAND)

    def SetValue(self, value):
        self.elp.SetValue([None, value[0], value[1]])

    def GetValue(self):
        v = self.elp.GetValue()
        return v[1], v[2]


class StaticText(wx.StaticText):
    def __init__(self, *args, **kwargs):
        wx.StaticText.__init__(self, *args, **kwargs)
        self._nlines = -1
        self.need_refresh = False

    def SetValue(self, text):
        if text is not None:
            self.SetLabel(text)
            nlines = len(text.split('\n'))
            if self._nlines > 0 and self._nlines != nlines:
                self.need_refresh = True
            else:
                self.need_refresh = False
            self._nlines = nlines

    def GetValue(self):
        return self.GetLabel()


class EditListCore(object):
    def __init__(self, parent, list=None,
                 call_sendevent=None, edge=5, tip=None):
        #        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.call_sendevent = call_sendevent

      #  sizer =  wx.FlexGridSizer(0, 2)
        sizer0 = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer0)
        parent = []
        bsizers = []

        def add_newpanel():
            p = Panel0(self, wx.ID_ANY)
            sizer0.Add(p, 0, wx.EXPAND | wx.GROW | wx.ALL)
            parent.append(p)

            sizer = wx.GridBagSizer()
            bsizers.append(sizer)

            parent[-1].SetSizer(sizer)
            return 0, sizer

        def add_newcollapsiblepane(label, setting):
            kwargs = {}
            if setting.pop("no_tlw_resize", True):
                kwargs["style"] = wx.CP_NO_TLW_RESIZE
            keepwidth = setting.pop("tlb_resize_samewidth", False)
            colour = setting.pop("colour", wx.Colour(235, 235, 235, 255))
            cp = CollapsiblePane0(self, wx.ID_ANY, label=label,
                                  keepwidth=keepwidth,
                                  **kwargs)

            sizer0.Add(cp, 0, wx.RIGHT | wx.LEFT | wx.EXPAND)
            p = cp.GetPane()
            cp.SetBackgroundColour(colour)
            p.SetBackgroundColour(colour)
            sizer = wx.GridBagSizer()
            bsizers.append(sizer)

            parent.append(p)
            parent[-1].SetSizer(sizer)
            sizer.SetSizeHints(p)
            return 0, sizer

        row, sizer = add_newpanel()

        self.widgets = []
        self.widgets_enable = []
        # by default, widgets are added in (row, col)
        # row increass in this loop
        k = 0

        for val in list:
            setting = {}
            col = 1
            span = wx.DefaultSpan
            noexpand = False
            expand_space = 5
            alignright = False
            enabled = True
            UpdateUI = None
            if len(val) >= 4:
                if val[3] is not None:
                    # val[3] can be either tuple or dict
                    if 'expand_space' in val[3]:
                        expand_space = val[3]['expand_space']
                        del val[3]['expand_space']
                    if 'UpdateUI' in val[3]:
                        UpdateUI = val[3]["UpdateUI"]
                        del val[3]["UpdateUI"]

            if val[0] is not None:
                if val[0].startswith("->"):
                    if len(val) < 3:
                        setting = {"no_tlw_resize": True}
                    else:
                        setting = val[3]
                    row, sizer = add_newcollapsiblepane(val[0][2:], setting)
                    k = k + 1
                    continue

                elif val[0].startswith("<-"):
                    row, sizer = add_newpanel()
                    k = k + 1
                    continue

                txt = wx.StaticText(parent[-1], wx.ID_ANY, val[0])
                sizer.Add(txt, (row, 0), span,
                          wx.ALL | wx.ALIGN_CENTER_VERTICAL, edge)
            else:
                txt = None
                col = 0
                span = (1, 2)

            if val[2] < -1:
                val = __builtins__['list'](val)
                val[2] = val[2] + 10000
                enabled = False
            if val[2] == -1:
                w = wx.StaticText(parent[-1], wx.ID_ANY, '')
#               sizer.Add(w, (row,0), span,
#                         wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
                col = 0
                p = w
            elif val[2] == 0:
                if len(val) == 4 and val[3] is not None:
                    setting = val[3]
                else:
                    setting = {}
                noexpand = setting.pop('noexpand', False)
                w = TextCtrlCopyPaste(parent[-1], wx.ID_ANY, '',
                                      style=wx.TE_PROCESS_ENTER,
                                      **setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                p = w
            elif val[2] == 100:
                ns = None
                if len(val) == 4 and val[3] is not None:
                    setting = val[3]
                    if 'ns' in setting:
                        ns = setting['ns']
                w = TextCtrlCopyPasteEval(parent[-1], wx.ID_ANY, val[1],
                                          style=wx.TE_PROCESS_ENTER | wx.TE_RICH,
                                          ns=ns)
                self.Bind(wx.EVT_TEXT_ENTER, w.onEnter, w)
                p = w
            elif val[2] == 200:
                w = TextCtrlCopyPaste(parent[-1], wx.ID_ANY, '',
                                      style=wx.TE_PROCESS_ENTER)
                self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                w._use_escape = False
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 300:
                w = TextCtrlCopyPasteFloat(parent[-1], wx.ID_ANY, '',
                                           style=wx.TE_PROCESS_ENTER)
                self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 400:
                w = TextCtrlCopyPasteInt(parent[-1], wx.ID_ANY, '',
                                         style=wx.TE_PROCESS_ENTER)
                self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 500:
                if len(val) == 4 and val[3] is not None:
                    setting = val[3]
                else:
                    setting = {}
                noexpand = setting.pop('noexpand', False)
                w = TextCtrlCopyPasteHistory(parent[-1], wx.ID_ANY, '',
                                             style=wx.TE_PROCESS_ENTER,
                                             **setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                p = w
            elif val[2] == 35:
                try:
                    nlines = val[3]['nlines']
                except:
                    nlines = 1
                w = TextCtrlCopyPaste(parent[-1], wx.ID_ANY, '',
                                      style=wx.TE_MULTILINE,
                                      nlines=nlines)
                if val[1] is not None:
                    w.SetValue(val[1])
                # self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                p = w
            elif val[2] == 235:
                try:
                    nlines = val[3]['nlines']
                except:
                    nlines = 5
                w = TextCtrlCopyPaste(parent[-1], wx.ID_ANY, '',
                                      style=wx.TE_MULTILINE,
                                      nlines=nlines)
                # self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                w._use_escape = False
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 2235:
                try:
                    nlines = val[3]['nlines']
                except:
                    nlines = 5
                w = RichTextCtrlCopyPaste(parent[-1], wx.ID_ANY, '',
                                          style=wx.richtext.RE_MULTILINE,
                                          nlines=nlines)
                # self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                w._use_escape = False
                if val[1] is not None:
                    w.SetValue(val[1])
                w.SetSizeHints((1, 32*nlines))
                p = w
            elif val[2] == 1:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"values": ["on", "off"]}
                w = RadioButtons(parent[-1], wx.ID_ANY, val[1], setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 2:
                w = StaticText(parent[-1], wx.ID_ANY, val[1])
                p = w
            elif val[2] == 102:
                w = StaticText(parent[-1], wx.ID_ANY, val[1])
                p = w
                col = 0
                span = (1, 2)
                noexpand = True
            elif val[2] == 3:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"text": "check box"}
                if not "expand" in setting:
                    setting["expand"] = False
                w = CheckBox(parent[-1], wx.ID_ANY, setting["text"])
                w.SetValue(val[1])
                if "noindent" in setting:
                    col = 0
                    span = (1, 2)
                p = w
                noexpand = not setting["expand"]
            elif val[2] == 4:
                if len(val) == 4:
                    setting = val[3]
                    if "style" not in setting:
                        #                    setting["style"]=wx.CB_DROPDOWN
                        setting["style"] = wx.TE_PROCESS_ENTER
                else:
                    setting = {"style": wx.CB_READONLY,
                               "choices": ["ok", "cancel"], }
                choices_cb = setting.pop("choices_cb", None)
                w = ComboBox(parent[-1], wx.ID_ANY, style=setting["style"],
                             choices=setting["choices"],
                             choices_cb=choices_cb)
                w.SetValue(val[1])
                p = w
#              noexpand = True
            elif val[2] == 104:
                if len(val) == 4:
                    setting = val[3]
                    if "readonly" in setting:
                        setting["style"] = wx.CB_READONLY if setting["readonly"] else wx.DROPDOWN
                    if ("style" in setting) is False:
                        setting["style"] = wx.TE_PROCESS_ENTER
                else:
                    setting = {"style": wx.CB_READONLY,
                               "choices": ["ok", "cancel"]}
                w = ComboBox_Float(parent[-1], wx.ID_ANY, style=setting["style"],
                                   choices=setting["choices"])
                w.SetValue(val[1])
                p = w
            elif val[2] == 204:
                w = MDSserver(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 304:
                w = ComboBoxPrefList(parent[-1], wx.ID_ANY, setting=val[3])
                w.SetValue(val[1])
                p = w
            elif val[2] == 404:
                w = ComboBoxPrefListDirectory(
                    parent[-1], wx.ID_ANY, setting=val[3])
                w.SetValue(val[1])
                p = w
            elif val[2] == 504:
                if len(val) == 4:
                    setting = val[3]
                    if "style" not in setting:
                        setting["style"] = wx.CB_READONLY
                else:
                    setting = {"style": wx.CB_READONLY,
                               "choices": ["ok", "cancel"], }
                s = setting["choices"]
                s = [x for x in s if x != 'New...']
                s = s + ['New...']
                choices_cb = setting.pop("choices_cb", None)
                w = ComboBoxWithNew(parent[-1], wx.ID_ANY, style=setting["style"],
                                    choices=s,
                                    choices_cb=choices_cb,)
                w.SetValue(val[1])
                p = w

            elif val[2] == 5:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"minV": 0.,
                               "maxV": 1.,
                               "val": 0.5,
                               "res": 0.01,
                               "text_box": True}
                w = Slider(parent[-1], wx.ID_ANY, setting=setting)
                w.SetValue(val[1])
                p = w

            elif val[2] == 105:
                w = AlphaPanel(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 6:
                w = Color(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 3006:
                w = CheckBoxModified(parent[-1], wx.ID_ANY, Color,
                                     setting=val[3])
                w.SetValue(val[1])
                p = w
            elif val[2] == 27:
                w = CheckBoxModifiedELP(parent[-1], wx.ID_ANY,
                                        setting=val[3])
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 127:
                w = CheckBoxModifiedELP(parent[-1], wx.ID_ANY,
                                        setting=val[3])
                w._forward_logic = False
                w.SetValue(val[1])
                p = w
            elif val[2] == 227:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"elp": [("name", '', 0, None), ]}
                w = ComboBoxModifiedELP(parent[-1], wx.ID_ANY,
                                        setting=val[3])
                w.SetValue(val[1])
                p = w
            elif val[2] == 106:
                w = ColorFace(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 206:
                w = ColorSelector(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
                noexpand = True
            elif val[2] == 306:
                w = PathCollectionEdgeColor(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 406:
                w = LineColor(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 506:
                w = ColorPairSelector(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 606:
                w = TickLabelColorSelector(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 7:
                w = LineWidth(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 107:
                w = LineWidthWithZero(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 8:
                w = LineStyle(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 9:
                w = Marker(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 10:
                w = PatchLineStyle(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 11:
                #              if len(val)==4:
                #                 setting=val[3]
                #              else:
                #                 setting={"reverse": False}
                w = ColorMap(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 12:
                w = color_map_button(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 13:
                if len(val) >= 4:
                    setting = val[3]
                else:
                    setting = {'check_range_order': False}
                w = AxisRange(parent[-1], wx.ID_ANY, setting=setting)
                p = w
            elif val[2] == 14:
                w = LogLinScale(parent[-1], wx.ID_ANY)
                p = w
            elif val[2] == 15:
                w = LabelPanel(parent[-1], wx.ID_ANY)
                p = w
            elif val[2] == 115:
                w = LabelPanel2(parent[-1], wx.ID_ANY)
                p = w
            elif val[2] == 16:
                w = ArrowStylePanel(parent[-1], wx.ID_ANY)
                p = w
                noexpand = True
            elif val[2] == 17:
                w = GenericCoordsTransform(parent[-1], wx.ID_ANY)
                p = w
            elif val[2] == 18:
                w = MDSSource(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
                col = 0
                span = (1, 2)
            elif val[2] == 118:
                w = MDSSource0(parent[-1],  wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
                col = 0
                span = (1, 2)
            elif val[2] == 19:
                w = LegendLocPanel(parent[-1],  wx.ID_ANY)
                p = w
                col = 0
                span = (1, 2)
            elif val[2] == 20:
                if len(val) >= 4:
                    setting = val[3]
                else:
                    setting = {'check_range_order': False}
                w = AxesRangeParamPanel(parent[-1],  wx.ID_ANY, **setting)
                p = w
                col = 0
                span = (1, 2)
                noexpand = True
            elif val[2] == 21:
                w = MDSGlobalSelection(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 22:
                w = ColorOrder(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
                noexpand = True
            elif val[2] == 23:
                w = Color3DPane(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
                noexpand = True
            elif val[2] == 24:
                if len(val) >= 4:
                    setting = val[3]
                else:
                    setting = {"minV": 0.,
                               "maxV": 1.,
                               "val": 0.5,
                               "res": 0.01,
                               "motion_event": False}
                w = CSlider(parent[-1], wx.ID_ANY, setting=setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 124:
                if len(val) >= 4:
                    setting = val[3]
                else:
                    setting = {"minV": 0.,
                               "maxV": 1.,
                               "val": 0.5,
                               "res": 0.01,
                               "motion_event": False}
                w = CSliderWithText(parent[-1], wx.ID_ANY, setting=setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 25:
                w = RotationPanel(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 26:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"style": wx.CB_READONLY,
                               "choices": ["left", "right"]}
                w = AxisPositionPanel(parent[-1], wx.ID_ANY, setting=setting)
                w.SetValue(val[1])
                p = w
            elif val[2] == 28:
                style = wx.CB_READONLY
                choices = ['c']
                if len(val) == 4 and val[3] is not None:
                    if 'choices' in val[3]:
                        choices = val[3]['choices']
                    if 'style' in val[3]:
                        style = val[3]['style']

                w = CAxisSelector(parent[-1],
                                  wx.ID_ANY, style=style, choices=choices)
                if val[1] is not None:
                    w.SetValue(val[1])
#              w.SetValue(val[1])
                p = w
            elif val[2] == 29:
                w = XYResize(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 30:
                w = XYAnchor(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 31:
                w = MDSFigureType(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
#              w.SetValue(val[1])
                p = w
            elif val[2] == 32:
                w = MDSRange(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 33:
                w = ELP(parent[-1], wx.ID_ANY, setting=val[3])
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 34:
                w = SelectableELP(parent[-1], wx.ID_ANY, setting=val[3])
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 36:
                from ifigure.utils.checkbox_panel import CheckBoxes
                # setting = {'col': 4,
                #     'labels': ['lable1','label2', ...]}
                w = CheckBoxes(parent[-1], wx.ID_ANY, setting=val[3])
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 37:
                w = TickLocator(parent[-1], wx.ID_ANY, setting=val[3])
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 38:
                w = ClipSetting(parent[-1], wx.ID_ANY)
                w.SetValue(val[1])
                p = w
            elif val[2] == 39:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {"minV": -4.,
                               "maxV": 5.,
                               "val": 0.5,
                               "res": 0.01,
                               "motion_event": False,
                               "text_box": True}
                w = CDoubleSlider(parent[-1], wx.ID_ANY, setting=setting)
                w.SetValue(val[1])
                p = w
            elif val[2] == 40:
                w = GL_Lighting(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                col = 0
                span = (1, 2)
                p = w
            elif val[2] == 41:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {}
                w = DialogButton(parent[-1], wx.ID_ANY, setting=setting)
                p = w
                alignright = setting.pop('alignright', alignright)
                noexpand = setting.pop('noexpand', False)
            elif val[2] == 141:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {}
                w = FunctionButton(parent[-1], wx.ID_ANY, setting=setting)
                p = w
                alignright = setting.pop('alignright', alignright)
                noexpand = setting.pop('noexpand', False)
            elif val[2] == 241:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {}
                w = FunctionButtons(parent[-1], wx.ID_ANY, setting=setting)
                p = w
                alignright = setting.pop('alignright', alignright)
                noexpand = setting.pop('noexpand', False)
            elif val[2] == 341:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {}
                w = FunctionButton(parent[-1], wx.ID_ANY, setting=setting)
                w._call_method = True
                p = w
                noexpand = setting.pop('noexpand', False)
            elif val[2] == 42:
                if len(val) == 4:
                    setting = val[3]
                else:
                    setting = {}
                w = TickLabelSizeSelector(
                    parent[-1], wx.ID_ANY, setting=setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 43:      # array text box
                if len(val) == 4 and val[3] is not None:
                    setting = val[3]
                else:
                    raise ValueError("array text box setting is misssing")
                w = ArrayTextCtrl(parent[-1], wx.ID_ANY, **setting)
                if val[1] is not None:
                    w.SetValue(val[1])
#              self.Bind(wx.EVT_TEXT_ENTER, self._textctrl_enter, w)
                noexpand = setting.pop('noexpand', False)
                p = w
            elif val[2] == 44:
                w = GL_View(parent[-1], wx.ID_ANY)
                if val[1] is not None:
                    w.SetValue(val[1])
                col = 0
                span = (1, 2)
                p = w
            elif val[2] == 45:
                if len(val) == 4 and val[3] is not None:
                    setting = val[3]
                else:
                    setting = {}
                w = FilePath(parent[-1], wx.ID_ANY, wx.Panel, **setting)
                if val[1] is not None:
                    w.SetValue(val[1])
                p = w
            elif val[2] == 99:  # custom UI component
                setting = val[3]
                UI = setting.pop('UI', None)
                noexpand = setting.pop('noexpand', False)
                col = setting.pop('col', col)
                span = setting.pop('span', span)
                alignright = setting.pop('alignright', alignright)
                if UI is not None:
                    w = UI(parent[-1], wx.ID_ANY, setting=setting)
                    if val[1] is not None:
                        w.SetValue(val[1])
                    p = w
                else:
                    w = wx.StaticText(
                        parent[-1], wx.ID_ANY, 'Custom UI is not defined!')

            if tip is not None and len(tip) > k:
                if tip[k] is not None:
                    if txt is not None:
                        panel_SetToolTip(txt, tip[k])
                    else:
                        panel_SetToolTip(w, tip[k])

            w.Fit()
            if UpdateUI is not None:
                # print("setting update event")
                w.Bind(wx.EVT_UPDATE_UI, UpdateUI)

            self.widgets.append((w, txt, val[2]))
            self.widgets_enable.append(enabled)
            alignright = setting.pop('alignright', alignright)

            alignment = wx.ALL | wx.ALIGN_CENTER_VERTICAL
            if not noexpand:
                alignment = wx.EXPAND | alignment
            if alignright:
                alignment = wx.ALIGN_RIGHT | alignment
            if not enabled:
                w.Enable(False)
            sizer.Add(p, (row, col), span, alignment, expand_space)
            row = row+1
            k = k + 1

        for sizer in bsizers:
            if len(sizer.GetChildren()) > 0:
                sizer.AddGrowableCol(1)

        self.list = list

    def GetValue(self):
        v = []
        for w, txt, wc in self.widgets:
            v.append(w.GetValue())
        return v

    def AddCurrentToHistory(self):
        for w, txt, wc in self.widgets:
            if hasattr(w, "add_current_to_history"):
                w.add_current_to_history()

    def SetValue(self, value):
        if value is None:
            return

        i = 0
        for w, txt, wc in self.widgets:
            if w.IsEnabled():
                try:
                    err = w.SetValue(value[i])
                except:
                    import traceback
                    traceback.print_exc()
                    print("failed to call SetValue" + str(w))
                    continue
                if err is False:
                    w.Hide()
                    if txt is not None:
                        txt.Hide()
                elif err is True:
                    w.Show()
                    if txt is not None:
                        txt.Show()
                elif err is None:
                    pass
                    # print 'no check in setvalue'
                if wc == 2:
                    if w.need_refresh:
                        wx.CallAfter(self.Layout)
                        w.need_refresh = False
            en = self.widgets_enable[i]
            if not en:
                w.Enable(False)
                if txt is not None:
                    txt.Enable(False)
            i = i+1

    def update_label(self, ll):
        i = 0

        # these has to be skipped (relating to collapsable pane
        ll = [x for x in ll if x[0] is None or not x[0].startswith("->")]
        ll = [x for x in ll if x[0] is None or not x[0].startswith("<-")]

        for w, txt, wc in self.widgets:
            if txt is not None:
                label = ll[i][0] if ll[i][0] is not None else ""
                txt.SetLabel(label)
            i = i+1

    def send_event(self, evtobj, evt0):
        if self.call_sendevent is not None:
            self.call_sendevent.send_event(self, evt0)
            return
        self.send_some_event(evtobj, evt0, EditorChanged)

    def send_changing_event(self, evtobj, evt0):
        self.send_some_event(evtobj, evt0, EditorChanging)

    def send_setfocus_event(self, evtobj, evt0):
        self.send_some_event(evtobj, evt0, EditorSetFocus)

    def send_some_event(self, evtobj, evt0, eventtype):
        i = 0
#        print evtobj, self.widgets
        for w, txt, wc in self.widgets:
            if w == evtobj:
                break
            i = i+1
        evt = EditListEvent(eventtype, wx.ID_ANY)
        evt.SetEventObject(evtobj)
        evt.elp = self
        evt.widget_idx = i
        if hasattr(evt0, 'signal'):
            evt.signal = evt0.signal
        handler = self.GetParent()
        handler.ProcessEvent(evt)

    def Enable(self, value=True):
        if isinstance(value, bool):
            value = [value]*len(self.widgets)
        elif isinstance(value, int):
            value = [value]*len(self.widgets)
        for k, pair in enumerate(self.widgets):
            w, txt, wc = pair
            en = self.widgets_enable[k]
            if len(value) == k:
                break
            if en:
                v = value[k]
            else:
                v = False
            if txt is not None:
                txt.Enable(v)
            if w is not None:
                w.Enable(v)

    def _textctrl_enter(self, evt):
        pass

# from wx.lib.scrolledpanel import ScrolledPanel as SP


class ScrolledEditListPanel(EditListCore, SP):
    def __init__(self, parent, list=None,
                 call_sendevent=None, edge=5, tip=None,):
        SP.__init__(self, parent, wx.ID_ANY)
        EditListCore.__init__(self, parent, list=list,
                              call_sendevent=call_sendevent, edge=edge, tip=tip,)
        self.SetScrollRate(0, 5)

    def Enable(self, value=True):
        if isinstance(value, bool):
            SP.Enable(self, value)
        EditListCore.Enable(self, value=value)


class EditListPanel(EditListCore, wx.Panel):
    def __init__(self, parent, list=None,
                 call_sendevent=None, edge=5, tip=None,):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        EditListCore.__init__(self, parent, list=list,
                              call_sendevent=call_sendevent, edge=edge, tip=tip,)

    def Enable(self, value=True):
        if isinstance(value, bool):
            wx.Panel.Enable(self, value)
        EditListCore.Enable(self, value=value)


'''
   use_frame=True
   def_style = (wx.CAPTION|
             wx.CLOSE_BOX|
             wx.MINIMIZE_BOX|
             wx.RESIZE_BORDER|
             wx.FRAME_FLOAT_ON_PARENT|
             wx.FRAME_TOOL_WINDOW)
   base_widget = wx.Frame
'''


class EditListDialog(wx.Dialog):
    def __init__(self, parent, id, title='', list=None,
                 style=wx.DEFAULT_DIALOG_STYLE,
                 tip=None, pos=(-1, -1), size=(-1, -1), nobutton=False,
                 add_palette=False,
                 endmodal_value=None):
        wx.Dialog.__init__(self, parent, id=id, title=title, pos=pos,
                           size=size, style=style)
        self.endmodal_value = endmodal_value
        self.nobutton = nobutton
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        self.elp = EditListPanel(self, list, tip=tip)
        self.elp.Layout()
        vbox.Add(self.elp, 1, wx.EXPAND | wx.RIGHT | wx.LEFT, 10)
        if not self.nobutton:
            sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
            if sizer is not None:
                vbox.Add(sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
#        self.Fit()
        self.Layout()
        if pos is None:
            self.Centre()
        else:
            self.SetPosition(pos)
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        wx.CallAfter(self._myRefresh, size)

        if add_palette:
            wx.GetApp().add_palette(self)

    def GetValue(self):
        return self.elp.GetValue()

    def SetValue(self, value):
        self.elp.SetValue(value)

    def onEL_Changed(self, evt):
        value = self.elp.GetValue()
        if self.nobutton:
            self.EndModal(wx.ID_OK)
        if (self.endmodal_value is not None and
                self.endmodal_value == value[-1]):
            self.EndModal(wx.ID_OK)

    def _myRefresh(self, size=(-1, -1)):
        win = self.GetTopLevelParent()
#        win.SetSizeHints(win)
        if size[0] == -1 and size[1] == -1:
            win.Fit()
        win.Layout()


class EditListDialogTab(wx.Dialog):
    def __init__(self, parent, id, title='', tab=None, list=None,
                 style=wx.DEFAULT_DIALOG_STYLE,
                 tip=None, pos=None, size=(-1, -1), nobutton=False,
                 add_palette=False):
        wx.Dialog.__init__(self, parent, id=id, title=title,  style=style)
        self.nobutton = nobutton
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.list = list
        self.tab = tab
        self.elp = [None]*len(self.list)
        self.nb = wx.Notebook(self)
        i = 0
        for t in tab:
            self.elp[i] = EditListPanel(self.nb, list[i], tip=tip[i])
            self.nb.AddPage(self.elp[i], t)
            i = i+1

        vbox.Add(self.nb, 1, wx.EXPAND | wx.ALL, 10)
        if not self.nobutton:
            sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
            if sizer is not None:
                vbox.Add(sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(vbox)
        self.Fit()
        if pos is None:
            self.Centre()
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        wx.CallAfter(self._myRefresh)

        if add_palette:
            wx.GetApp().add_palette(self)

    def GetValue(self):
        return [elp.GetValue() for elp in self.elp]

    def SetValue(self, value):
        i = 0
        for elp in self.elp:
            elp.SetValue(value[i])
            i = i+1

    def onEL_Changed(self, evt):
        value = self.GetValue()
        if self.nobutton:
            self.EndModal(wx.ID_OK)

    def _myRefresh(self):
        win = self.GetTopLevelParent()
#        win.SetSizeHints(win)
        win.Fit()
        win.Layout()


def _DialogEditListCore(list, modal=True, style=wx.DEFAULT_DIALOG_STYLE,
                        tip=None, parent=None, pos=(-1, -1), size=(-1, -1),
                        title='',
                        ok_cb=None, close_cb=None,
                        ok_noclose=False, _class=EditListDialog, **kwargs):
    """
    Dialog to ask user a list of input using various
    wx control widgets

    list has a following form
         [["label1", value1, mode1, {setting1}],
          ["label2", value2, mode2  {setting2}],
          ...]

    label is a text shown on the left of control.
    value is an intial value for widget
    made/setting
      mode defiens which wx.controls will be used.
      setting gives additional information to build
      wx.controls.

      -1 : None (skip this area of sizer)
       0 : textctrl with cut&paste
     100 : textctrl with cut&paste with eval
     200 : textctrl with cut&paste (no backslash escape)
     300 : textctrl with cut&paste float
     400 : textctrl with cut&paste int
     500 : textctrl with cut&paste and history
       1 : radio button
           setting = {"values":['on', 'off']}
       2:  text label (static text)
     102:  text label (use two columns)
       3:  check box
           setting = {"text":'check box label'
       4:  combo box
           setting={"style":wx.CB_READONLY,
                    "choices": ["ok", "cancel"]}
     104:  combo box float
     204:  MDSserver
     304:  ComboBoxPrefList(generalized version of MDSserver type control)

           (example)
           setting = {'rule':  rule to read pref ex. ('connection', {'server':''...})
                      'pref':  pref file  ex. 'mdsplus.mdssever_config'
                      'varname': varname ex. 'connection'
                      'keyname': keyname ex. 'server'
                      'def_value': value which appears at top
                      'dialog':  callable to ask new entry (see below)}
           app = wx.GetApp().TopWindow
           def callable(parent, app0 = app):
              ret, m = dialog.textentry(app0,
                         "Enter message for commit", "Mercurial Commit", "change #1")
              if not ret: return ''
              return m
           !!! setting dict will be destroyed. not reused it.
     404:  ComboBoxPrefList + DirectoryBrowseButton
       5:  slider
           setting={"minV": 0.,
                    "maxV": 1.,
                    "val" : 0.5,
                    "res" : 0.01,
                    "text_box" : True}
     105: slideralpha
            used to alpha setting
            range = (0, 1)
            translate 1 => None
       6: color
    3006: color?
     106: color_face (no none color button)
     206: colorcombobox
     306: pathcollection edgecolor
     406: line color
     506: color pair (double 206)
       7: linewidth
       8: linestyle
       9: marker
      10: patch linestyle
      11: color map
      12: color_map_button
      13: range
      14: log/linear
      15: text label
     115: text label (with defaults)
      16: fancy arrow style
      17: generic point
      18: mdsplus
      19: legendloc
      20: axes_ranage_param
      21: mdsscope global selection
      22: color order
      23: color 3D pane
      24: custom single slider with slider (5) like
          setting. text box is not yet implemented
           setting={"minV": 0.,
                    "maxV": 1.,
                    "val" : 0.5,
                    "res" : 0.01,
                    "text_box" : False}
     124: custom single slider with text box
      25: Rotation Panel
      26: AxisPosition Panel
      27: CheckBoxModifiedELP
           example:
           [None,  [True, ['0.95']], 27, [{'text':'use q0'},
                                          {'elp':[['Experiment', 'cmod', 0, None],]
                                           }], ]
     127: CheckBoxModifiedELP (revserse the bool of checkbox)
     227: ComoboBoxModifiedELP
      28: CaxisSelector
      29: XYResize
      30: XYAnchor
      31: MDSfiguretype
      32: MDSRnage
      33: ELP (EditListPanel) Sometimes you want to set/get two (or more)
                              fields at once
      34: SelectableELP
      35 : textctrl with cut&paste multiline
     235 : textctrl with cut&paste (no backslash escape)
      36 : checkbox_panel
      37 : ticklocator
      38: clip setting
      39: custom double slider
           setting={"minV": 0.,
                    "maxV": 1.,
                    "val" : 0.5,
                    "res" : 0.01,
                    "motion_event: : False,
                    "text_box" : False}
      40: GL Lighting
      41: Dialog button (opens a custom dialog)
     141: Function button  (call a function)
     241: Function buttons (multiple function buttons)
     341: Method buttons   (object method call. note that SetValue shoudl set object)
      42: TickLabelSizeSelector
      43: ArrayTextBox
      44: GL azim/elev panel
      45: File path
      99: Custom UI (To use UI component which is not defined here)

    """
    # if not modal:
    #   style = wx.STAY_ON_TOP|style
    dia = _class(parent, wx.ID_ANY, title=title, list=list,
                 style=style, tip=tip, pos=pos, size=size, **kwargs)

    if modal:
        val = dia.ShowModal()
        value = dia.GetValue()
        if val == wx.ID_OK:
            dia.Destroy()
            return True, value
        dia.Destroy()
        return False, value
    else:
        def ok_func(evt):
            diag = evt.GetEventObject().GetParent()
            value = diag.GetValue()
            if not ok_noclose:
                diag.Destroy()
            ok_cb(value)
        if ok_cb is not None:
            dia.Bind(wx.EVT_BUTTON, ok_func, id=wx.ID_OK)
        if close_cb is not None:
            dia.Bind(wx.EVT_CLOSE, close_cb)
        dia.Show()
        return dia


class EditListDialogWithWindowList(EditListDialog, WithWindowList_MixIn):
    def __init__(self, *args, **kargs):
        style = kargs.pop('style', wx.DEFAULT_DIALOG_STYLE)
        kargs['style'] = style
        super(EditListDialogWithWindowList, self).__init__(*args, **kargs)
        WithWindowList_MixIn.__init__(self)


class EditListDialogTabWithWindowList(EditListDialogTab, WithWindowList_MixIn):
    def __init__(self, *args, **kargs):
        style = kargs.pop('style', wx.DEFAULT_DIALOG_STYLE)
#        kargs['style'] = style|wx.STAY_ON_TOP
        kargs['style'] = style
        super(EditListDialogTabWithWindowList, self).__init__(*args, **kargs)
        WithWindowList_MixIn.__init__(self)


def DialogEditList(list, **kwargs):
    '''
    DialogEditList(list, modal = True, style = wx.DEFAULT_DIALOG_STYLE,
                   tip = None, parent = None, pos = None, size=(-1,-1),
                   title='',
                   ok_cb = None, close_cb = None,
                   ok_noclose = False ):
    '''
    kwargs['_class'] = EditListDialog
    return _DialogEditListCore(list, **kwargs)


def DialogEditListWithWindowList(list, **kwargs):
    kwargs['_class'] = EditListDialogWithWindowList
    return _DialogEditListCore(list, **kwargs)


def DialogEditListTab(tab, list, **kwargs):
    '''
    DialogEditListTab(tab, list, modal=True, style=wx.DEFAULT_DIALOG_STYLE,
                      tip=None, parent=None, pos=None, title='',
                      ok_cb = None):
    '''
    tip = kwargs.pop('tip', None)
    if tip is None:
        tip = [['']*len(x) for x in list]
    kwargs['tip'] = tip
    kwargs['tab'] = tab
    kwargs['_class'] = EditListDialogTab
    return _DialogEditListCore(list, **kwargs)


def DialogEditListTabWithWindowList(tab, list, **kwargs):
    tip = kwargs.pop('tip', None)
    if tip is None:
        tip = [['']*len(x) for x in list]
    kwargs['tip'] = tip
    kwargs['tab'] = tab
    kwargs['_class'] = EditListDialogTabWithWindowList
    return _DialogEditListCore(list, **kwargs)

    '''
    dia = EditListDialogTab(parent, wx.ID_ANY, title, tab,
                            list, style=style, tip=tip, pos=pos)
    wx.CallAfter(dia.Layout)
    if modal:
        val = dia.ShowModal()
        value=dia.GetValue()
        if val == wx.ID_OK:
           dia.Destroy()
           return True, value
        dia.Destroy()
        return False, value
    else:
       def ok_func(evt):
           diag = evt.GetEventObject().GetParent()
           value = diag.GetValue()
           diag.Destroy()
           ok_cb(value)
       if ok_cb is not None:
           dia.Bind(wx.EVT_BUTTON, ok_func, id=wx.ID_OK)
       dia.Show()
    '''


class EditListMiniFrame(wx.MiniFrame):
    def __init__(self, parent, id, title='', list=None,
                 style=wx.CAPTION |
                 wx.CLOSE_BOX |
                 wx.MINIMIZE_BOX |
                 wx.RESIZE_BORDER |
                 wx.FRAME_FLOAT_ON_PARENT,
                 tip=None, pos=None, nobutton=True,
                 callback=None, close_callback=None,
                 ok_callback=None):

        wx.MiniFrame.__init__(self, parent, id, title, style=style)
        self.nobutton = nobutton
        self.callback = callback
        self.close_callback = close_callback
        self.ok_callback = ok_callback
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        self.elp = EditListPanel(self, list, tip=tip)
        self.elp.Layout()
        vbox.Add(self.elp, 1, wx.EXPAND | wx.RIGHT | wx.LEFT, 10)
        if not self.nobutton:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            okbutton = wx.Button(self, wx.ID_OK, "OK")
            cancelbutton = wx.Button(self, wx.ID_CANCEL, "Cancel")
            sizer.AddStretchSpacer()
            sizer.Add(okbutton, 0, wx.ALIGN_CENTER | wx.ALL, 1)
            sizer.Add(cancelbutton, 0, wx.ALIGN_CENTER | wx.ALL, 1)
            sizer.AddStretchSpacer()
            okbutton.Bind(wx.EVT_BUTTON, self.onOK)
            cancelbutton.Bind(wx.EVT_BUTTON, self.onCancel)
            vbox.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)
#        self.Fit()
        self.Layout()
        if pos is None:
            self.Centre()
        else:
            self.SetPosition(pos)

        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        if close_callback is not None:
            self.Bind(wx.EVT_CLOSE, self.onClose)
        wx.CallAfter(self._myRefresh)

    def GetValue(self):
        return self.elp.GetValue()

    def SetValue(self, value):
        self.elp.SetValue(value)

    def onEL_Changed(self, evt):
        value = self.GetValue()
        if self.callback is not None:
            self.callback(value)

    def onClose(self, evt):
        if self.close_callback is not None:
            value = self.GetValue()
            self.close_callback(value)
        evt.Skip()

    def onOK(self, evt):
        if self.ok_callback is not None:
            value = self.GetValue()
            self.ok_callback(value)
        self.Close()

    def onCancel(self, evt):
        self.Close()

    def _myRefresh(self):
        win = self.GetTopLevelParent()
#        win.SetSizeHints(win)
        win.Fit()
        win.Layout()


class Example(wx.Frame):
    def __init__(self, parent, title, list=None, style=None, tip=None):
        super(Example, self).__init__(parent, title=title)
        dia = EditListDialog(self, wx.ID_ANY, '', list, tip=tip)
#        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
#        self.GetSizer().Add(dia, 1, wx.EXPAND, 0)
        val = dia.ShowModal()
        if val == wx.ID_OK:
            print("YES")
            print(dia.GetValue())
        dia.Destroy()
        self.Close()


# example
if __name__ == "__main__":
    app = wx.App(False)
    list = [["", " " * 50, 2],
            ["Server", "cmodws60.psfc.mit.edu", 0],
            ["Use Proxy", "on", 1, {"values": ["on", "off"]}],
            ["Check Box", True, 3, {"text": ""}],
            ["ComboBox", "ok", 4],
            ["Slider", 0.0, 5], ]

    server = "localhost"
    port = "10002"
    tree = "ANALYSIS"
    shot = "-1"

    list = [["", " " * 50, 2],
            ["Server", server, 0],
            ["Port", port, 0],
            ["Tree", tree, 4, {"choices": ["ANALYSIS", "ELECTRONS",
                                           "SPECTROSCOPY", "XTOMO", "DNB",
                                           ]}],
            ["Shot", shot, 0]]

    list = [["color order", ['blue', 'red', 'green'], 22, {}],
            ["->"],
            ["color map", 3, 12, {}],
            ["color map", 3, 12, {}],
            ["color map", 3, 12, {}],
            ["color map", 3, 12, {}],
            ["Env  options",  None, 235, {'nlines': 2}],
            ["<-"],
            ["color map", 3, 12, {}],
            ["color map", 3, 12, {}],
            ["color map", 3, 12, {}]]
    list = [["Max", (True, 'r'), 3006, ({"text": "Clip"}, {})]]
    list = [["Server", "cmodws60.psfc.mit.edu", 235],
            ["Server", "cmodws60.psfc.mit.edu", 2235], ]
#   e=Example(None, 'example', list=list, style='no button')
    e = Example(None, 'example', list=list, tip=[
                "tip for " + str(x) for x in range(len(list))])
    app.MainLoop()
