import wx
import os
import time
import random
########################################################################
#from ifigure.widgets.primitive_widgets import primitive_widgets
from ifigure.widgets.section_editor import section_editor
from ifigure.widgets.artist_widgets import panel1, panel2

from ifigure.utils.wx3to4 import GridSizer, FlexGridSizer


class property_editor(wx.Panel):
    screen_width = None
#    screen_width = 290

    def __init__(self, parent=None):
        super(property_editor, self).__init__(parent)
        self._last_update = 0
        self.ifigure_canvas = None

        self.b1 = wx.ToggleButton(self, label='artist')
        self.b2 = wx.ToggleButton(self, label='axes')
        self.b3 = wx.ToggleButton(self, label='page')
        self.b1.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleArtist)
        self.b2.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleAxes)
        self.b3.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleSection)

        if (property_editor.screen_width == None
                or property_editor.screen_width == 0):
            self.CP1 = panel1(self, False)
        else:
            self.CP1 = panel1(self, True)
        self.CP2 = panel2(self)
        self.CP3 = section_editor(self)
#        self.Bind(self.CP1.events, self.hndl_event)
#        self.Bind(self.CP2.events, self.hndl_event)
#        self.Bind(self.CP3.events, self.hndl_event)

        sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = GridSizer(1, 3)
        button_sizer.Add(self.b1, 0)
        button_sizer.Add(self.b2, 0)
        button_sizer.Add(self.b3, 0)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        sizer.Add(self.CP1, 1, wx.EXPAND | wx.ALL, 3)
#        sizer.Add(self.CP2, 1, wx.EXPAND|wx.ALL, 3)
#        sizer.Add(self.CP3, 1, wx.EXPAND|wx.ALL, 3)
        self.sizer_olditem = self.CP1

        self.SetSizer(sizer)
#        self.SetSizeHints(250, -1, maxW=250)
        self.Layout()
#        self.parent = parent
        self.CP1.GetSizer().Layout()

        # initial setting
        self.b1.SetValue(True)
        self.b2.SetValue(False)
        self.b3.SetValue(False)
        self.CP2.Show()
        self.CP1.Hide()
        self.CP3.Hide()
        self.OnPaneChanged()

        # this flags record if panels are ever shown on Screen.
        # if not, GTK3 shows
        #  "lost focus even though it didn't have it"
        # Debug messages.
        self._panel_shown_flag = [True, False, False]

    @property
    def parent(self):
        return self.GetParent()

    def set_sizehint(self):
        if (property_editor.screen_width == None
                or property_editor.screen_width == 0):
            # print 'size scan start'
            #        if True:
            s = self.IsShown()

            self.Show()
            m = -1
            self.CP1.Hide()
            self.CP2.Show()
            self.CP3.Hide()
            # print 'cp2'
            self.GetSizer().Replace(self.sizer_olditem, self.CP2)
            self.sizer_olditem = self.CP2
            for p in self.CP2.panels:
                self.CP2.switch_panel(p)
                self.Layout()
                self.CP2.GetSizer().Layout()
                self.OnPaneChanged()
                # print p, self.CP2.panels[p].GetSize()
                m = max([m, self.CP2.panels[p].GetSize()[0]])
            self.CP1.Show()
            self.CP2.Hide()
            self.CP3.Hide()
            # print 'cp1'
            self.GetSizer().Replace(self.sizer_olditem, self.CP1)
            self.sizer_olditem = self.CP1
            for p in self.CP1.panels:
                self.CP1.switch_panel(p)
                self.Layout()
                self.CP1.GetSizer().Layout()
                self.OnPaneChanged()
                self.CP1.Layout()
                # print p, self.CP1.panels[p].GetSize()
                m = max([m, self.CP1.panels[p].GetSize()[0]])

            self.CP1.switch_panel('text')
            self.Layout()
            self.CP1.GetSizer().Layout()
            self.OnPaneChanged()
            property_editor.screen_width = m
            # print 'panel size ', m
            self.Show(s)
        else:
            m = property_editor.screen_width
            self.CP1.Show()
            self.CP2.Hide()
            self.CP3.Hide()
            self.CP1.switch_panel('text')
            self.CP2.switch_panel('axcommon.x.y')
            self.Layout()
            self.CP1.GetSizer().Layout()
            self.CP2.GetSizer().Layout()
            self.OnPaneChanged()
        if m > 10:
            self.SetSizeHints(m, -1, maxW=m)
            for pname in self.CP1.panels:
                self.CP1.panels[pname].SetSizeHints(m, -1, maxW=m)
                #self.CP1.panels[pname].SetSize((m, -1))
#            for pname in  self.CP2.panels:
#                for elp in self.CP2.panels[pname].elp:
#                    elp.EnableScrolling(False, True)
#                    elp.SetScrollRate(0,5)
#                    elp.SetMinVirtualSize(m)

    def set_canvas(self, canvas):
        self.ifigure_canvas = canvas

    def get_canvas(self):
        return self.ifigure_canvas

    def ToggleArtist(self, e):
        obj = e.GetEventObject()
        isPressed = obj.GetValue()
        sizer = self.GetSizer()
        if isPressed:
            self.b2.SetValue(False)
            self.b3.SetValue(False)
            self.CP1.Show()
            self.CP2.Hide()
            self.CP3.Hide()
            if self.sizer_olditem is not self.CP1:
                sizer.Replace(self.sizer_olditem, self.CP1)
                self.sizer_olditem = self.CP1
        else:
            self.b1.SetValue(True)
        self.CP1.GetSizer().Layout()
        self.CP1.update_panel()
        self.OnPaneChanged()
        self._panel_shown_flag[0] = True

        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            self.GetTopLevelParent().deffered_force_layout()

    def ToggleAxes(self, e):
        obj = e.GetEventObject()
        isPressed = obj.GetValue()
        sizer = self.GetSizer()
        if isPressed:
            self.b1.SetValue(False)
            self.b3.SetValue(False)
            self.CP1.Hide()
            self.CP3.Hide()
            if self.sizer_olditem is not self.CP2:
                sizer.Replace(self.sizer_olditem, self.CP2)
                self.sizer_olditem = self.CP2
            self.CP2.Layout()
            self.CP2.Show()
        else:
            self.b2.SetValue(True)
        self.CP2.GetSizer().Layout()

        # set selected axes to panel
        canvas = self.get_canvas()
        ax = canvas.axes_selection()
        self.CP2.set_axes(ax)

        self.CP2.update_panel()
        self.OnPaneChanged()
        self.CP2.Layout()
        self._panel_shown_flag[1] = True

        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            self.GetTopLevelParent().deffered_force_layout()

    def ToggleSection(self, e):
        obj = e.GetEventObject()
        isPressed = obj.GetValue()
        sizer = self.GetSizer()
        if isPressed:
            self.b1.SetValue(False)
            self.b2.SetValue(False)
            self.CP3.Show()
            self.CP1.Hide()
            self.CP2.Hide()
            if self.sizer_olditem is not self.CP3:
                sizer.Replace(self.sizer_olditem, self.CP3)
                self.sizer_olditem = self.CP3
        else:
            self.b3.SetValue(True)
        self.CP3.SetEditorValue()
        self.CP3.GetSizer().Layout()
        self.CP3.update_panel()
        self.OnPaneChanged()
        self._panel_shown_flag[2] = True

        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            self.GetTopLevelParent().deffered_force_layout()

    def hndl_event(self, event):
        if event.GetEventObject() is self.CP1:
            pass
        if event.GetEventObject() is self.CP2:
            self.ifigure_canvas.draw()
        if event.GetEventObject() is self.CP3:
            pass

    def SetCanvasValue(self, message=None):
        self.CP1.SetCanvasValue(message)

        #  Update Axes Panel
        # self.CP2.SetCanvasValue(message)

        #  Update Section Panel
        self.CP3.SetCanvasValue(message)

    def update_panel_request2(self, time):
        if (time > self._last_update):
            self.update_panel()

    def update_panel(self):
        if self.IsShown():
            if self.CP1.IsShown():
                self.CP1.update_panel()
#                if len(self.get_canvas().selection) > 0:

            if self.CP2.IsShown():
                self.CP2.update_panel()
            if self.CP3.IsShown():
                self.CP3.update_panel()
            self._last_update = time.time()
        self.Layout()

    def OnPaneChanged(self):
        # redo the layout
        #        self.GetSizer().Layout()
        #   self.Fit()
        self.GetParent().Layout()
    #   self.parent.Fit()

    def onTD_Selection(self, evt):
        if self.IsShown():
            if self._panel_shown_flag[0]:
                self.CP1.onTD_Selection(evt)
            if self._panel_shown_flag[1]:
                self.CP2.onTD_Selection(evt)
            if self._panel_shown_flag[2]:
                self.CP3.onTD_Selection(evt)
        self.Layout()
        # this will make sure that button size is right..!?

    def onTD_ShowPage(self, evt):
        if self.IsShown():
            self.CP1.update_panel()
            self.CP2.update_panel()
            self.CP3.onTD_ShowPage(evt)

    def onTD_Replace(self, evt):
        if self.IsShown():
            self.CP1.onTD_Replace(evt)
            self.CP2.onTD_Replace(evt)
            self.CP3.onTD_Replace(evt)

    def save_screencapture(self, file='~/test.png'):
        import os
        file = os.path.expanduser(file)
        context = wx.ClientDC(self)
        memory = wx.MemoryDC()
        x, y = self.ClientSize
        bitmap = wx.EmptyBitmap(x, y, -1)
        memory.SelectObject(bitmap)
        memory.Blit(0, 0, x, y, context, 0, 0)
        memory.SelectObject(wx.NullBitmap)
        bitmap.SaveFile(file, wx.BITMAP_TYPE_PNG)
