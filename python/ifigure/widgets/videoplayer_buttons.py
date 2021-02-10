from __future__ import print_function
from .miniframe_with_windowlist import MiniFrameWithWindowList
import os
import wx
import ifigure
import numpy as np
import wx.lib.platebtn as platebtn
import wx.lib.buttons as buttons
import wx.lib.agw.buttonpanel as bp
import ifigure.utils.cbook as cbook
from ifigure.mto.fig_axes import FigInsetAxes
import ifigure.widgets.dialog as dialog
from .navibar2 import make_bitmap_with_bluebox, TaskBtnList, ButtonInfo
from ifigure.utils.wx3to4 import wxCursorFromImage

from ifigure.utils.wx3to4 import evt_GetPosition

btasks0 = [('goto_first', 'arrow_firstpage.png', 0, 'first page'),
           ('play_rev',   'arrow_revplay.png', 1, 'reverse play'),
           ('step_rev',   'arrow_revstep.png', 1, 'step reverse'),
           ('stop_play',  'stop_play.png', 1, 'stop'),
           ('step_fwd',   'arrow_fwdstep.png', 1, 'step forward'),
           ('play_fwd',   'arrow_fwdplay.png', 1, 'forward play'),
           ('goto_last',  'arrow_lastpage.png', 0, 'last page'),
           ('config',    'cog.png', 1, 'config'), ]


class VideoplayerBar(bp.ButtonPanel):
    def __init__(self, parent, id=-1, text='', *args, **kargs):
        self.container = kargs.pop('container')

        super(VideoplayerBar, self).__init__(parent, id,  text, *args, **kargs)
        # mode of action (''=select, 'pan', 'zoom', 'text'....)
        self.mode = ''
        self.ptype = ''   # palette type ('pmode', 'amode')
        self.rotmode = False

        self.three_d_bar = False
        self.p0 = self.make_button_group(self, btasks0)
        self.btasks0 = btasks0[:]
        self.refresh_button()
        self.Fit()
        self.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)
        self.Bind(wx.EVT_KEY_UP, self._onKeyUp)

    def _onKeyDown(self, evt):
        wx.PostEvent(self.GetParent(), evt)

    def _onKeyUp(self, evt):
        wx.PostEvent(self.GetParent(), evt)

    def make_button_group(self, parent, btasks):

        bts = TaskBtnList()
        for items in btasks:
            btask, icon, tg, hint = items[:4]
            if btask == '---':
                bts.append('---')
#              bts.AddSpacer(icon)
                continue
            from ifigure.ifigure_config import icondir
            path = os.path.join(icondir, '16x16', icon)
            if icon[-3:] == 'png':
                im = wx.Image(path, wx.BITMAP_TYPE_PNG)
                image = im.ConvertToBitmap()
#              im = im.ConvertToGreyscale()
#              im = im.ConvertToMono(0,0,0)
                if im.HasAlpha():
                    im.ConvertAlphaToMask()
                crs = wxCursorFromImage(im)
            if icon[-3:] == 'bmp':
                im = wx.Image(path, wx.BITMAP_TYPE_BMP)
                image = im.ConvertToBitmap()
                if im.HasAlpha():
                    im.ConvertAlphaToMask()
                crs = wxCursorFromImage(im)
            # image.SetSize((8,8))
            btnl = ButtonInfo(self, wx.ID_ANY, image)
            btnl.custom_cursor = crs
            btnl.btask = btask
            btnl.bitmap1 = image
            btnl.bitmap2 = make_bitmap_with_bluebox(image)
            if hint != '':
                btnl.SetShortHelp(hint)
            if tg == 1:
                btnl.SetKind('toggle')
            if len(items) > 4:
                btnl.use_in_2d_menu = items[4]
            if len(items) > 5:
                btnl.use_in_3d_menu = items[5]

            bts.append(btnl)
            #           def func(evt, btask=btask): return self.OnButton(evt, btask)
            #           parent.Bind(wx.EVT_BUTTON, func, btnl)
        return bts

    def OnLeftUp(self, evt):
        ret = self.HitTest(evt_GetPosition(evt))
        if ret[0] == wx.NOT_FOUND:
            return bp.ButtonPanel.OnLeftUp(self, evt)

        bp.ButtonPanel.OnLeftUp(self, evt)
        btask = self.allbinfo[ret[0]].btask
        self.OnButton(evt, btask)

    def AddButtonOrS(self, b):
        if isinstance(b, bp.ButtonInfo):
            if not self.three_d_bar:
                if not b.use_in_2d_menu:
                    return
            if self.three_d_bar:
                if not b.use_in_3d_menu:
                    return
            self.AddButton(b)
            self.allbinfo.append(b)
        else:
            self.AddSeparator()

    def Clear(self):
        self.allbinfo = []
        self.Freeze()
        bp.ButtonPanel.Clear(self)

    def set_toggle(self, btask):
        for p in self.p0:
            if p.btask != btask:
                p.SetStatus('Normal')
                p.SetToggled(False)
            else:
                p.SetStatus('Toggled')
                p.SetToggled(True)

    def set_bitmap2(self, btask):
        for p in self.p0:
            if p.btask == btask:
                p.SetBitmap(p.bitmap2)
            else:
                p.SetBitmap(p.bitmap1)

    def refresh_button(self):

        self.Clear()
        for b in self.p0:
            self.AddButtonOrS(b)
        self.DoLayout()

#    def OnKeyUp(self, evt):
#       if evt.GetKeyCode() == wx.WXK_SHIFT:
#           if self.mode == 'zoom': self.SetZoomUpDown('Up')

    def OnButton(self, evt, btask):
        v = self.container
        if btask == 'goto_first':
            v.goto_first()
        elif btask == 'goto_last':
            v.goto_last()
        elif btask == 'config':
            v.videoviewer_config()
        elif btask == 'play_fwd':
            v.play_fwd()
            self.set_toggle(btask)
            self.set_bitmap2(btask)
            self.refresh_button()
        elif btask == 'play_rev':
            v.play_rev()
            self.set_toggle(btask)
            self.set_bitmap2(btask)
            self.refresh_button()

        elif btask == 'stop_play':
            v.stop_play()
            self.reset_btn_toggle_bitmap()
        elif btask == 'step_fwd':
            v.stop_play()
            v.step_fwd()
        elif btask == 'step_rev':
            v.stop_play()
            v.step_rev()
        else:
            print(btask)

    def reset_btn_toggle_bitmap(self):
        self.set_toggle('')
        self.set_bitmap2('')
        self.refresh_button()

    def place_right_bottom(self):
        # self.Fit()
        psize = self.GetSize()
        csize = self.GetParent().GetSize()
        self.SetPosition((csize[0]-psize[0]-4,
                          csize[1]-psize[1]-4))


class VideoplayerButtons(MiniFrameWithWindowList):
    def __init__(self, parent, id, title='',
                 style=wx.CAPTION |
                 wx.CLOSE_BOX |
                 wx.MINIMIZE_BOX |
                 wx.RESIZE_BORDER |
                 wx.FRAME_FLOAT_ON_PARENT,
                 pos=None):
        MiniFrameWithWindowList.__init__(self, parent, id, title, style=style)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.btn = VideoplayerBar(self, container=self.GetParent())
        self.SetSizer(vbox)
        vbox.Add(self.btn, 1, wx.EXPAND | wx.ALIGN_CENTER, 3)

        self.Layout()
        self.Fit()
        self.Show()
        self.Bind(wx.EVT_CLOSE, self.onClose)
        wx.GetApp().add_palette(self)
        wx.CallAfter(self.CentreOnParent)

    def onClose(self, evt):
        wx.GetApp().rm_palette(self)
        self.GetParent().onPlayerButtonClose()
        evt.Skip()

    def reset_btn_toggle_bitmap(self):
        self.btn.reset_btn_toggle_bitmap()


def add_player_btn(parent):
    canvas = parent.canvas.canvas
    playerbtn = VideoplayerBar(canvas, wx.ID_ANY, container=parent)
    playerbtn.Show()
    playerbtn.place_right_bottom()

    return playerbtn
