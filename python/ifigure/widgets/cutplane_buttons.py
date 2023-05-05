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

btasks0 = [('plus_theta', 'shift_theta.png', 0, '+ polar angle (shift-key: reserse direction)'),
#           ('minus_theta',   'minus_theta.png', 0, '- polar angle'),
           ('plus_phi',   'shift_phi.png', 0, '+ azimuthal angle (shift-key: reserse direction)'),
#           ('minus_phi',  'minus_phi.png', 0, '- azimuthal angle'),
           ('plus_offset',   'shift_cp.png', 0, '+/- offset (shift-key: reserse direction)'),
           ('yz_plane',  'yz_plane.png', 0, 'YZ plane'),
           ('xz_plane',  'xz_plane.png', 0, 'XZ plane'),           
           ('xy_plane',  'xy_plane.png', 0, 'XY plane'),                      
           ('flip_sign',    'flip_cp_side.png', 0, 'flip side'), 
           ('reset_cp',    'reset.png', 0, 'reset cp setting'), ]

# step size
delta_z = 0.02
delta_a = 5.
# interval(must be integer)
dtime = 150

class CutPlaneBar(bp.ButtonPanel):
    def __init__(self, parent, id=-1, text='', *args, **kargs):
        self.container = kargs.pop('container')

        super(CutPlaneBar, self).__init__(parent, id,  text, *args, **kargs)
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
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)        
        self.Bind(wx.EVT_SET_FOCUS, self._onFocus)
        
        self.place_bottoms()
        self._mouse_inside = False
        self._shift_down = False

    def _onKeyDown(self, evt):
        if evt.GetKeyCode() == wx.WXK_SHIFT:
            self._shift_down = True
            if self._mouse_inside:
                return
            
        wx.PostEvent(self.GetParent(), evt)

    def _onKeyUp(self, evt):
        if evt.GetKeyCode() == wx.WXK_SHIFT:
            self._shift_down = False
            if self._mouse_inside:
                return
            
        wx.PostEvent(self.GetParent(), evt)

    def _onFocus(self, evt):
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
            #btnl.bitmap2 = make_bitmap_with_bluebox(image)
            if hint != '':
                btnl.SetShortHelp(hint)
            #if tg == 1:
            #    btnl.SetKind('toggle')
            #if len(items) > 4:
            #    btnl.use_in_2d_menu = items[4]
            #if len(items) > 5:
            #    btnl.use_in_3d_menu = items[5]

            bts.append(btnl)
            #           def func(evt, btask=btask): return self.OnButton(evt, btask)
            #           parent.Bind(wx.EVT_BUTTON, func, btnl)
        return bts

    def OnLeftDown(self, evt):
        ret = self.HitTest(evt_GetPosition(evt))
        if ret[0] == wx.NOT_FOUND:
            return bp.ButtonPanel.OnLeftDown(self, evt)

        bp.ButtonPanel.OnLeftDown(self, evt)
        btask = self.allbinfo[ret[0]].btask

        self._mouse_inside = True        
        self.OnButtonDown(evt, btask)

        win = self.GetTopLevelParent()
        canvas = win.canvas
        ax = win.canvas.axes_selection()
        if ax is None: return
        figax = ax.figobj
        if not figax.get_3d(): return

        wx.CallLater(dtime, self.timed_event, btask, canvas, ax)
        evt.Skip()

    def OnLeftUp(self, evt):
        ret = self.HitTest(evt_GetPosition(evt))
        if ret[0] == wx.NOT_FOUND:
            return bp.ButtonPanel.OnLeftUp(self, evt)

        bp.ButtonPanel.OnLeftUp(self, evt)
        btask = self.allbinfo[ret[0]].btask

        self._mouse_inside = False
        self.OnButtonUp(evt, btask)
        evt.Skip()
        
    def OnLeave(self, evt):
        self._mouse_inside = False
        evt.Skip()
        
    def OnEnter(self, evt):
        self._mouse_inside = True
        evt.Skip()
        
    def timed_event(self, btask, canvas, ax):

        def get_angles(limit1):
            rr = np.sqrt(limit1[0]**2 + limit1[1]**2)
            theta = np.arctan(rr/(limit1[2]+1e-5))
            if theta < 0:
                theta = np.pi + theta
            phi = np.arctan2(limit1[1], limit1[0])
            return theta, phi
        
        def get_norm(theta, phi):
            if theta > np.pi:
                theta = theta - np.pi
            elif theta < 0:
                theta = np.pi + theta

            vec = [np.sin(theta)*np.cos(phi),
                   np.sin(theta)*np.sin(phi),
                   np.cos(theta)]
            return vec

        if btask == 'plus_offset':
            limit1 = ax._lighting["clip_limit1"]
            limit2 = ax._lighting['clip_limit2']

            xmin, xmax = ax.get_xlim3d()
            ymin, ymax = ax.get_ylim3d()
            zmin, zmax = ax.get_zlim3d()
            nn  = np.sum(limit1*np.array([xmax-xmin, ymax-ymin, zmax-zmin]))

            delta = nn*delta_z

            if self._shift_down:
                limit2[0] = limit2[0] + delta
            else:
                limit2[0] = limit2[0] - delta
            ax._lighting['clip_limit2'] = limit2

        elif btask == 'plus_phi':
            th, ph = get_angles(ax._lighting['clip_limit1'])
            if self._shift_down:
                ph = ph  - delta_a/180*np.pi
            else:
                ph = ph  + delta_a/180*np.pi
            vec = get_norm(th, ph)
            ax._lighting['clip_limit1'] = vec

        elif btask == 'plus_theta':
            th, ph = get_angles(ax._lighting['clip_limit1'])
            limit2 = ax._lighting['clip_limit2']            
            if self._shift_down:
                th = th  + delta_a/180*np.pi            
                if th > np.pi:
                    limit2[1] = -limit2[1]
            else:
                th = th  - delta_a/180*np.pi
                if th < 0:
                    limit2[1] = -limit2[1]
                
            ax._lighting['clip_limit2'] = limit2
            vec = get_norm(th, ph)
            ax._lighting['clip_limit1'] = vec

        else:
            pass
        
        figax = ax.figobj
        figax.set_bmp_update(False)
        wx.CallAfter(canvas.draw)
        if self._mouse_inside:            
            wx.CallLater(dtime, self.timed_event, btask, canvas, ax)
        
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

    '''
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
    '''
    def refresh_button(self):

        self.Clear()
        for b in self.p0:
            self.AddButtonOrS(b)
        self.DoLayout()

#    def OnKeyUp(self, evt):
#       if evt.GetKeyCode() == wx.WXK_SHIFT:
#           if self.mode == 'zoom': self.SetZoomUpDown('Up')

    def OnButtonDown(self, evt, btask):
        pass

    def OnButtonUp(self, evt, btask):
        win = self.GetTopLevelParent()
        canvas = win.canvas
        ax = win.canvas.axes_selection()
        if ax is None: return

        figax = ax.figobj
        if not figax.get_3d(): return
        
        v = self.container
        if btask == 'yz_plane':
            ax._lighting['clip_limit1'] = [1, 0, 0]
            figax.set_bmp_update(False)
            wx.CallAfter(canvas.draw)
        elif btask == 'xy_plane':
            ax._lighting['clip_limit1'] = [0, 0, 1]
            figax.set_bmp_update(False)
            wx.CallAfter(canvas.draw)
        elif btask == 'xz_plane':
            ax._lighting['clip_limit1'] = [0, 1, 0]
            figax.set_bmp_update(False)
            wx.CallAfter(canvas.draw)
        elif btask == 'flip_sign':
            limit2 = ax._lighting['clip_limit2']
            limit2[1] = -limit2[1]
            ax._lighting['clip_limit2'] = limit2
            figax.set_bmp_update(False)
            wx.CallAfter(canvas.draw)
        elif btask == 'reset_cp':
            ax._lighting['clip_limit1'] = [1, 0, 0]
            ax._lighting['clip_limit2'] = [0., 1, 0]
            figax.set_bmp_update(False)
            wx.CallAfter(canvas.draw)
        else:
            
            pass   

    '''
    def reset_btn_toggle_bitmap(self):
        self.set_toggle('')
        self.set_bitmap2('')
        self.refresh_button()
    '''

    def place_bottoms(self):
        # self.Fit()
        psize = self.GetSize()
        csize = self.GetParent().GetSize()
        self.SetPosition((csize[0]-psize[0]-4,
                          4))

def add_cutplane_btns(parent):
    canvas = parent.canvas.canvas
    cutplanebtns = CutPlaneBar(canvas, wx.ID_ANY, container=parent)
    cutplanebtns.Show()

    return cutplanebtns
