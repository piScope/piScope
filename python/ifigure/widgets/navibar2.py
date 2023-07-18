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

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty, UndoRedoFigobjProperty, UndoRedoFigobjMethod

from ifigure.utils.wx3to4 import image_GetAlpha, image_SetAlpha, image_SetOptionInt, evt_GetPosition, wxEmptyImage, wxStockCursor, wxCursorFromImage


def make_bitmap_with_bluebox(bitmap):
    # second bitmap has blue box around it
    h, w = bitmap.GetSize()
    image = bitmap.ConvertToImage()
    alpha = np.frombuffer(bytes(image_GetAlpha(image)),
                          dtype=np.uint8).reshape(w, h, -1)
    array = np.frombuffer(bytes(image.GetData()), dtype=np.uint8)
    array = array.copy()
    alpha = alpha.copy()

    array = array.reshape(w, h, -1)
    array[0, 1:-2, :1] = 0
    array[-1, 1:-2, :1] = 0
    array[1:-2, 0, :1] = 0
    array[1:-2, -1, :1] = 0

    array[1, 1, :1] = 0
    array[1, -2, :1] = 0
    array[-2, 1, :1] = 0
    array[-2, -2, :1] = 0

    array[1, 1, 2] = 255
    array[1, -2, 2] = 255
    array[-2, 1, 2] = 255
    array[-2, -2, 2] = 255

    array[0, 1:-2, 2] = 255
    array[-1, 1:-2, 2] = 255
    array[1:-2, 0, 2] = 255
    array[1:-2, -1, 2] = 255

    alpha[1:-2, -1] = 127
    alpha[1:-2, 0] = 127
    alpha[0, 1:-2] = 127
    alpha[-1, 1:-2] = 127
    alpha[1, 1] = 127
    alpha[1, -2] = 127
    alpha[-2, 1] = 127
    alpha[-2, -2] = 127
    image = wxEmptyImage(h, w)
    image.SetData(array.tobytes())
    image_SetAlpha(image, alpha)
    bitmap2 = image.ConvertToBitmap()

    return bitmap2


'''
button tasks
    ('pmode',           # task name
     'pmode.png',       # icon file
      1,                # toggle group id
     'plot mode',       # tips
      callable = None)  # method to be called when button is hit.
'''

three_d_bar = False
btasks0 = [  # ('previous', 'arrowleft.png', 0, 'previous page'),
    #        ('next',   'arrowright.png', 0,'next page'),
    #        ('---',    (10,10), 0, ''),
    #                   ('copy',   'copy.png', 0, ''),
    #                   ('paste',  'paste.png', 0, ''),
    ('pmode', 'pmode.png', 1, 'plot mode'),
    ('amode', 'amode.png', 1, 'annotation mode'),
    ('---', (10, 10), 0, ''), ]

btasks1_std2d_base = [('select', 'select.png', 1, 'select',),
                      ('zoom', 'zoom2.png', 1,
                       '\n'.join(['zoom', ' shift: zoom down', ' alt: menu to pick direction'])),
                      ('pan', 'arrowmove.png', 1, '\n'.join(
                          ['pan', ' shift: pan all']),),
                      ('cursor', 'cursor.png', 1, 'cursor',),
                      ('---', (10, 10), 0, ''), ]
btasks1_std2d = btasks1_std2d_base + [
    ('xlog', 'xlog.png', 0, 'toggle xlog',),
    ('ylog', 'ylog.png', 0, 'toggle ylog',),
    ('xauto', 'xauto.png', 0, 'autoscale x', ),
    ('yauto', 'yauto.png', 0, 'autoscale y', ),
    ('grid', 'grid.png', 0, 'toggle grid', ),
    ('nomargin', 'margin.png', 0, 'no margin mode', ), ]

btasks1_std3d_base = [('select', 'select.png', 1, 'select',),
                      ('zoom', 'zoom2.png', 1,
                       '\n'.join(['zoom', ' shift: zoom down', ' alt: menu to pick direction'])),
                      ('pan', 'arrowmove.png', 1, '\n'.join(
                          ['pan', ' shift: pan all']),),
                      ('cursor', 'cursor.png', 1, 'cursor',),
                      ('3dzoom', 'threed_rot.png', 1,
                       '3D zoom\n shift: pan\n alt: zoom',),
                      ('---', (10, 10), 0, ''), ]

btasks1_std3d = btasks1_std3d_base + [
    ('xauto', 'xauto.png', 0, 'autoscale x', ),
    ('yauto', 'yauto.png', 0, 'autoscale y', ),
    ('nomargin', 'margin.png', 0, 'no margin mode', ), ]

btasks2 = [  # ('selecta', 'select.bmp', 1, 'select'),
    ('text', 't.png', 1, 'insert text'),
    ('line', 'line.png', 1, 'insert line'),
    #                 ('curve2', 'curve.png', 1, 'insert curve'),
    ('curve', 'curve.png', 1, 'insert curve'),
    ('arrow', 'arrow.png', 1, 'insert arrow'),
    ('circle', 'circle.png', 1, 'insert circle'),
    ('rect', 'box.png', 1, 'insert rectangle'),
    ('legend', 'legend.png', 1, 'insert legend'),
    ('colorbar', 'colorbar.png', 1, 'insert colorbar'),
    ('eps', 'eps.png', 1, 'insert eps'), ]

btasks3 = [('copy_cb', 'copy.png', 0, 'copy image to clipboard'),
           ('save_pic', 'save_pic.png', 0, 'save graphic'),
           ('mail_pic', 'mail_pic.png', 0, 'mail graphic'),
           ('toggle_prop', 'form.png', 0, 'show property'),
           #         ('trash', 'trash.png', 0, 'delete page')
           ]

hotspot = {'zoom': [5, 5], 'circle': [8, 8], 'rect': [8, 8],
           'curve': [10, 10], 'curve2': [10, 10],
           'line': [2, 15], 'pan': [8, 8]}

zoom_crs = None
pan_crs = None


class TaskBtnList(list):
    def get_btn(self, name):
        for m in self:
            if m.btask == name:
                return m
        return


class FakeEvent(object):
    def GetEventObject(self):
        return self.obj

    def Skip(s):
        return


class ButtonInfo(bp.ButtonInfo):
    def __init__(self, *args, **kwargs):
        bp.ButtonInfo.__init__(self, *args, **kwargs)
        self.use_in_2d_menu = True
        self.use_in_3d_menu = True

    def GetBestSize(self):
        size = self.GetBitmap().GetSize()
        h = 26
        return (int((h - size[1]) / 2 + size[0]), int(h))


class ButtonPanel(bp.ButtonPanel):
    def DoGetBestSize(self):
        try:
            s = super(ButtonPanel, self).DoGetBestSize()
        except SystemError:
            #import traceback
            # traceback.print_stack()
            return 10, 10
        return s

    def Clear(self):
        # this is necessary for wxpython.2.9....
        self.Freeze()
        bp.ButtonPanel.Clear(self)
        # self.Thaw()

    def make_all_normal(self):
        for btn in self._vButtons:
            if not btn.IsEnabled():
                continue
            btn.SetStatus("Normal")


class navibar(ButtonPanel):
    def __init__(self, parent, id=-1, text='', *args, **kargs):
        super(navibar, self).__init__(parent, id, text, *args, **kargs)
        # mode of action (''=select, 'pan', 'zoom', 'text'....)
        self.mode = ''
        self.ptype = ''   # palette type ('pmode', 'amode')
        self.rotmode = False
        self.three_d_bar = False

        self.p1_btns = {'std2d': self.make_button_group(self, btasks1_std2d),
                        'std3d': self.make_button_group(self, btasks1_std3d), }

        self.p1_choice = ['std2d', 'std3d']
        self.p1_std_tasks = [btasks1_std2d[:],
                             btasks1_std3d[:], ]

        self._extra_buttons = {}          # store callbacks
        self._extra_buttons_refresh = {}  # store button refresh

        self.p0 = self.make_button_group(self, btasks0)
        self.p2 = self.make_button_group(self, btasks2)
        self.p3 = self.make_button_group(self, btasks3)

        self.SetPMode(skip_sc=True)

        self.zoom_up_down = 'up'
        self.zoom_menu = 0    # 0 or 1
        self.pan_all = 0
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
#        self.Bind(wx.EVT_KEY_UP,  self.OnKeyUp)

        from ifigure.ifigure_config import icondir
        from ifigure.utils.cbook import make_crs_list

        if zoom_crs is None:
            path1 = os.path.join(icondir, '16x16', 'zoom2.png')
            path2 = os.path.join(icondir, '16x16', 'zoom3minus.png')
            path3 = os.path.join(icondir, '16x16', 'zoom2menu.png')
            path4 = os.path.join(icondir, '16x16', 'zoom2minusmenu.png')
            globals()['zoom_crs'] = make_crs_list(
                [path1, path2, path3, path4], 5, 5)
            path1 = os.path.join(icondir, '16x16', 'arrowmove.png')
            path2 = os.path.join(icondir, '16x16', 'arrowmove_all.png')
            globals()['pan_crs'] = make_crs_list([path1, path2, ], 5, 5)
            path1 = os.path.join(icondir, '16x16', 'threed_rot.png')
            globals()['threed_crs'] = make_crs_list([path1, ], 5, 5)
        self.zoom_crs = zoom_crs
        self.pan_crs = pan_crs
        self.threed_crs = threed_crs
        self._curve_mode = 'pp'

    @property
    def p1(self):
        if self.three_d_bar:
            return self.p1_btns[self.p1_choice[1]]
        else:
            return self.p1_btns[self.p1_choice[0]]

    def install_palette(self, name, tasks0, mode='2D', refresh=None):
        '''
        tasks shou

        '''
        # we use taskname + '_' + name to avoid name conflict
        tasks = []
        for t in tasks0:
            if t[0] == '---':
                tasks.append(t)
            else:
                tasks.append([t[0] + '_' + name] + list(t[1:]))

        if mode == '2D':
            btasks = btasks1_std2d_base + list(tasks)
        else:
            btasks = btasks1_std3d_base + list(tasks)
        self.p1_btns[name] = self.make_button_group(self,
                                                    btasks)

        for t in tasks:
            self._extra_buttons[t[0]] = t[-1]
        if refresh is not None:
            self._extra_buttons_refresh[name] = refresh

        evt = FakeEvent()
        evt.obj = self

        tg = set([btnl.tg for btnl in self.p1_btns[name]
                  if isinstance(btnl, bp.ButtonInfo)])
        for t in tg:
            if t == 0:
                continue
            if t == 1:
                continue
            btnls = [b for b in self.p1_btns[name] if (isinstance(b, bp.ButtonInfo)
                                                       and b.tg == t)]
            btnls[0].SetBitmap(btnls[0].bitmap2)
            self._extra_buttons[btnls[0].btask](evt)
            for b in btnls[1:]:
                b.SetBitmap(b.bitmap1)

    def use_palette(self, name, mode='2D'):
        if mode == '2D':
            self.p1_choice[0] = name
        else:
            self.p1_choice[1] = name
        self.SetPMode()

    def use_std_palette(self):
        self.p1_choice = ['std2d', 'std3d']
        self.SetPMode()

    def refresh_palette(self):
        for name in self.p1_choice:
            if name in self._extra_buttons_refresh:
                self._extra_buttons_refresh[name](self,
                                                  self.p1_btns[name])

    def add_extra_group1_button(self, idx, data,
                                use_in_2d_menu=True,
                                use_in_3d_menu=False):
        xx = list(data[:4])
        if use_in_2d_menu:
            self.p1_std_tasks[0].insert(idx, xx)
            self.p1_btns['std2d'] = self.make_button_group(self,
                                                           self.p1_std_tasks[0])
        if use_in_3d_menu:
            self.p1_std_tasks[1].insert(idx, xx)
            self.p1_btns['std3d'] = self.make_button_group(self,
                                                           self.p1_std_tasks[1])

        self._extra_buttons[data[0]] = data[-1]
        self.SetPMode()

    def make_button_group(self, parent, btasks):
        from ifigure.ifigure_config import icondir

        bts = TaskBtnList()
        for items in btasks:
            btask, icon, tg, hint = items[:4]
            if btask == '---':
                bts.append('---')
#              bts.AddSpacer(icon)
                continue
            path = icon if os.path.isabs(icon) else os.path.join(icondir,
                                                                 '16x16', icon)
            if icon[-3:] == 'png':
                im = wx.Image(path, wx.BITMAP_TYPE_PNG)
                image = im.ConvertToBitmap()
#              im = im.ConvertToGreyscale()
#              im = im.ConvertToMono(0,0,0)
                if im.HasAlpha():
                    im.ConvertAlphaToMask()
                if btask in hotspot:
                    image_SetOptionInt(
                        im, wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot[btask][0])
                    image_SetOptionInt(
                        im, wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot[btask][1])
                crs = wxCursorFromImage(im)
            elif icon[-3:] == 'bmp':
                im = wx.Image(path, wx.BITMAP_TYPE_BMP)
                image = im.ConvertToBitmap()
                if im.HasAlpha():
                    im.ConvertAlphaToMask()
                crs = wxCursorFromImage(im)

            btnl = ButtonInfo(self, wx.ID_ANY, image)
            btnl.custom_cursor = crs
            btnl.btask = btask
            btnl.bitmap1 = image
            btnl.bitmap2 = make_bitmap_with_bluebox(image)
            btnl.tg = tg
            if hint != '':
                btnl.SetShortHelp(hint)
            if tg > 0:
                btnl.SetKind('toggle')
            bts.append(btnl)
            #           def func(evt, btask=btask): return self.OnButton(evt, btask)
            #           parent.Bind(wx.EVT_BUTTON, func, btnl)
        return bts

#    def OnKeyUp(self, evt):
#       if evt.GetKeyCode() == wx.WXK_SHIFT:
#           if self.mode == 'zoom': self.SetZoomUpDown('Up')

    def OnKeyDown(self, evt):
        if evt.GetKeyCode() == wx.WXK_SHIFT:
            if self.mode == 'zoom':
                self.ToggleZoomUpDown()
            elif self.mode == 'pan':
                self.TogglePanAll()
        elif evt.GetKeyCode() == wx.WXK_ALT:
            if self.mode == 'zoom':
                self.ToggleZoomMenu()

    def OnRightUp(self, evt):
        ret = self.HitTest(evt_GetPosition(evt))
        if ret[0] == wx.NOT_FOUND:
            return super(navibar, self).OnLeftUp(evt)

        super(navibar, self).OnLeftUp(evt)
        btask = self.allbinfo[ret[0]].btask
        self.OnRightButton(evt, btask)

    def OnRightButton(self, evt, btask):
        if btask == 'mail_pic':
            self.MailPicRight(evt)
        elif btask == 'curve':
            self.CurveRight(evt)
        elif btask == 'grid':
            self.ToggleGridRight(evt)

    def OnLeftUp(self, evt):
        ret = self.HitTest(evt_GetPosition(evt))
        if ret[0] == wx.NOT_FOUND:
            return super(navibar, self).OnLeftUp(evt)

        super(navibar, self).OnLeftUp(evt)
        btask = self.allbinfo[ret[0]].btask
        self.OnButton(evt, btask)

    def OnButton(self, evt, btask):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)
        
        frame = cbook.FindFrame(self)
        btnl = [x for x in self.allbinfo if x.btask == btask][0]
        #        btnl = evt.GetEventObject()
        evt.SetEventObject(self)

        if btask == 'trash':
            frame.onDelPage(evt)
        elif btask == 'pmode':
            self.ExitInsertMode()
            self.SetPMode()
        elif btask == 'amode':
            self.ExitInsertMode()
            self.SetAMode()
        elif btask == 'select':
            self.SetSelect()
        elif btask == 'zoom':
            self.SetZoom(btnl)
        elif btask == 'pan':
            self.SetPan(btnl)
        elif btask == 'cursor':
            self.SetCursor()
        elif btask == '3dzoom':
            self.Set3DZoom(btnl)
        elif btask == 'next':
            frame.onNextPage(evt)
        elif btask == 'previous':
            frame.onPrevPage(evt)
        elif btask == 'xlog':
            self.SetXlog()
        elif btask == 'ylog':
            self.SetYlog()
        elif btask == 'xauto':
            self.SetXAuto()
        elif btask == 'yauto':
            self.SetYAuto()
        elif btask == 'save_pic':
            self.SavePic()
        elif btask == 'mail_pic':
            self.MailPic()
        elif btask == 'toggle_prop':
            self.ToggleProp()
        elif btask == 'copy_cb':
            self.CopyToCB()
#        elif btask == 'colorbar': self.ToggleCB()
        elif btask == 'grid':
            self.ToggleGrid()
        elif btask == 'nomargin':
            self.ToggleNoMargin()
        elif btask == '3d':
            self.Toggle3D()
        elif btask in self._extra_buttons:
            self.onHitExtra(evt, btnl)
        elif btask == 'line':
            self.GetParent().exit_layout_mode()  # just in case...
            if btnl.GetToggled():
                self._set_bitmap2(self.p2, self.p2.index(btnl))
                self.LineInsert(btask, btnl)
                self.SetInsertMode(btask, btnl)
            else:
                self.ExitInsertMode()
                #               self.SetAMode()
        elif btask == 'curve' and self._curve_mode == 'pp':
            self.GetParent().exit_layout_mode()  # just in case...
            if btnl.GetToggled():
                self._set_bitmap2(self.p2, self.p2.index(btnl))
                self.Curve2Insert(btask, btnl)
                self.SetInsertMode(btask, btnl)
            else:
                self.ExitInsertMode()
                #               self.SetAMode()
        else:
            self.GetParent().exit_layout_mode()  # just in case...
            if btnl.GetToggled():
                self._set_bitmap2(self.p2, self.p2.index(btnl))
                self.mode = btask
                self.SetInsertMode(btask, btnl)
            else:
                self.ExitInsertMode()
                #              self.SetAMode()

    def SetInsertMode(self, btask, btnl):
        for p in self.p2:
            if p != btnl:
                p.SetToggled(False)

        p = btnl
        sc = wxStockCursor(wx.CURSOR_WAIT)
        self.GetParent().canvas.SetCursor(p.custom_cursor)
#        print 'changing cursor'
        #

    def ExitInsertMode(self):
        #        print 'exiting insert mode'
        sc = wxStockCursor(wx.CURSOR_DEFAULT)
        self.GetParent().canvas.SetCursor(sc)
        self.mode = ''
        self.SetAMode()
        self._set_bitmap2(self.p2, -1)
        self.ptype = 'pmode'

    @property
    def abutton(self):
        return self.p0.get_btn('amode')

    @property
    def pbutton(self):
        return self.p0.get_btn('pmode')

    @property
    def iabutton(self):
        return self.p0.index(self.p0.get_btn('amode'))

    @property
    def ipbutton(self):
        return self.p0.index(self.p0.get_btn('pmode'))

    def SetAMode(self):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)
        
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self.pbutton.SetStatus('Normal')
        self.abutton.SetStatus('Toggled')
        self.pbutton.SetToggled(False)
        self.abutton.SetToggled(True)
        self._set_bitmap2(self.p0, self.iabutton)
        for p in self.p2:
            p.SetToggled(False)
            p.SetStatus('Normal')
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p2:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.ptype = 'amode'
        self.GetParent()._show_cursor = False
        sc = wxStockCursor(wx.CURSOR_DEFAULT)
        self.GetParent().canvas.SetCursor(sc)

    def SetPMode(self, skip_sc=False):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)
        
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self.pbutton.SetStatus('Toggled')
        self.abutton.SetStatus('Normal')
        self.pbutton.SetToggled(True)
        self.abutton.SetToggled(False)
        self._set_bitmap2(self.p0, self.ipbutton)
        for b in self.p0:
            self.AddButtonOrS(b)

        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.SetSelect(skip_sc=skip_sc)
        self.ptype = 'pmode'
        self.GetParent()._show_cursor = False

    def SetSelect(self, skip_sc=False):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)
        
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 0)
        self._set_toggle(0)
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p1:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = ''
        self.GetParent()._show_cursor = False
        if not skip_sc:
            sc = wxStockCursor(wx.CURSOR_DEFAULT)
            self.GetParent().canvas.SetCursor(sc)

    def _set_bitmap2(self, array, index):
        for p in array:
            if isinstance(p, str):
                continue
            if p.tg < 2:
                p.SetBitmap(p.bitmap1)
        if index > -1:
            array[index].SetBitmap(array[index].bitmap2)

    def GoZoom(self):
        btnl = [x for x in self.allbinfo if x.btask == 'zoom'][0]
        self.SetZoom(btnl)

    def GoPan(self):
        btnl = [x for x in self.allbinfo if x.btask == 'pan'][0]
        self.SetPan(btnl)

    def SetZoom(self, btnl):
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)

        self.Clear()
        self._set_bitmap2(self.p1, 1)
        self._set_toggle(1)
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p1:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'zoom'
        self.GetParent()._show_cursor = False
        self.zoom_up_down = 'up'
        self.zoom_menu = 0
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode()  # just in case...
        asel = self.GetParent().axes_selection
        if asel is None:
            return
        a = asel()
        if a is None:
            return
        if a.figobj is None:
            return
        if a.figobj.get_3d():
            self.GetParent().set_3dzoom_mode(True, pan_btn=11,
                                             zoom_btn=1, rotate_btn=10)

    def SetPan(self, btnl):
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 2)
        self._set_toggle(2)
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p1:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'pan'
        self.pan_all = 0
        self.GetParent()._show_cursor = False
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode()  # just in case...

        asel = self.GetParent().axes_selection
        if asel is None:
            return
        a = asel()
        if a is None:
            return
        if a.figobj is None:
            return
        if a.figobj.get_3d():
            self.GetParent().set_3dzoom_mode(True, pan_btn=1,
                                             zoom_btn=11, rotate_btn=10)

    def SetCursor(self):
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 3)
        self._set_toggle(3)
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p1:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'cursor'
        self.GetParent()._show_cursor = True
        sc = wxStockCursor(wx.CURSOR_DEFAULT)
        self.GetParent().canvas.SetCursor(sc)
        self.GetParent().exit_layout_mode()  # just in case...

    def Set3DZoom(self, btnl):
        self.Clear()
        self._set_bitmap2(self.p1, 4)
        self._set_toggle(4)
        for b in self.p0:
            self.AddButtonOrS(b)
        for b in self.p1:
            self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3:
            self.AddButtonOrS(b)
        self.DoLayout()
        self.rotmode = True
        self.GetParent().set_3dzoom_mode(True)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode()  # just in case...
        self.mode = '3dzoom'
        self.GetParent()._3d_rot_mode = 0

    def Set3DZoomCursor(self):
        self.GetParent().canvas.SetCursor(self.threed_crs[0])

    def SetPanCursor(self):
        self.GetParent().canvas.SetCursor(self.pan_crs[0])

    def SetZoomCursor(self):
        self.GetParent().canvas.SetCursor(self.zoom_crs[0])

    def _set_toggle(self, idx):
        mmm = 6
        for i in range(mmm):
            if self.p1[i] == '---':
                return
            if idx != i:
                self.p1[i].SetStatus('Normal')
                self.p1[i].SetToggled(False)
            else:
                self.p1[i].SetStatus('Toggled')
                self.p1[i].SetToggled(True)

    def Clear(self):
        self.allbinfo = []
        super(navibar, self).Clear()

    def AddButtonOrS(self, b):
        if isinstance(b, bp.ButtonInfo):
            self.AddButton(b)
            self.allbinfo.append(b)
        else:
            self.AddSeparator()

    def Show3DMenu(self):
        if self.three_d_bar:
            return
        self.three_d_bar = True
        globals()['three_d_bar'] = True
        if self.ptype == 'pmode':
            self.SetPMode()

    def Hide3DMenu(self):
        if not self.three_d_bar:
            return
        self.three_d_bar = False
        globals()['three_d_bar'] = False
        if self.ptype == 'pmode':
            self.SetPMode()

    def SetXYlog(self, name):
        asel = self.GetParent().axes_selection
        if asel is None:
            return
        a = asel()
        if a is None:
            return

        fig_axes = a.figobj
        p = fig_axes.get_axis_param(name)
        value = p.get_rangeparam()

#        print m
        ov = str(value[3])
        if ov == 'log':
            scale = 'linear'
        if ov == str('linear'):
            scale = 'log'

        canvas = self.GetParent()
        requests = canvas.make_xyauto_request(fig_axes, name, scale=scale)
        requests[fig_axes] = fig_axes.compute_new_range(
            request=requests[fig_axes])
        canvas.send_range_action(requests, 'range')

    def SetXlog(self):
        self.SetXYlog('x')

    def SetYlog(self):
        self.SetXYlog('y')

    def SetXAuto(self):
        self.GetParent().set_xauto()

    def SetYAuto(self):
        self.GetParent().set_yauto()

    def SavePic(self):
        self.GetParent().save_pic()

    def MailPic(self):
        self.GetParent().mail_pic()

    def MailPicRight(self, evt):
        def mailpic_set_pdf(evt, self=self):
            self.GetParent()._mailpic_format = 'pdf'

        def mailpic_set_eps(evt, self=self):
            self.GetParent()._mailpic_format = 'eps'

        def mailpic_set_svg(evt, self=self):
            self.GetParent()._mailpic_format = 'svg'

        def mailpic_set_jpeg(evt, self=self):
            self.GetParent()._mailpic_format = 'jpeg'

        def mailpic_set_png(evt, self=self):
            self.GetParent()._mailpic_format = 'png'

        def mailpic_set_pdfall(evt, self=self):
            self.GetParent()._mailpic_format = 'pdfall'

        def mailpic_set_gifanim(evt, self=self):
            self.GetParent()._mailpic_format = 'gifanim'
        data = ['eps', 'pdf', 'svg', 'png', 'jpeg', 'pdfall', 'gifanim']
        idx = data.index(self.GetParent()._mailpic_format)
        m = wx.Menu()
        menus = [
            ['EPS', mailpic_set_eps, None],
            ['PDF', mailpic_set_pdf, None],
            ['SVG', mailpic_set_svg, None],
            ['PNG', mailpic_set_png, None],
            ['JPEG', mailpic_set_jpeg, None],
            ['Multipage PDF', mailpic_set_pdfall, None],
            ['Animated Gif', mailpic_set_gifanim, None], ]
        menus[idx][0] = '^' + menus[idx][0]

        cbook.BuildPopUpMenu(m, menus)
        x, y = evt_GetPosition(evt)
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def CurveRight(self, evt):
        def curve_set_freehand(evt, self=self):
            self._curve_mode = 'fh'

        def curve_set_pickpoints(evt, self=self):
            self._curve_mode = 'pp'
        data = ['pp', 'fh']
        idx = data.index(self._curve_mode)
        m = wx.Menu()
        menus = [
            ['PickPoints', curve_set_pickpoints, None],
            ['Freehand', curve_set_freehand, None], ]

        menus[idx][0] = '^' + menus[idx][0]
        cbook.BuildPopUpMenu(m, menus)
        x, y = evt_GetPosition(evt)
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def CopyToCB(self):
        '''
        Copy_to_Clipboard_mod copys the buffer data
        which does not have highlight drawn
        '''
        frame = self.GetTopLevelParent()
        frame.onCopyToCB(None)

    def ToggleGridRight(self, evt):
        asel = self.GetParent().axes_selection
        if asel is None:
            return
        a = asel()
        if a is None:
            return
        ax = a.figobj
        value = ax.getp('grid')

        def grid_x(evt, self=self):
            value[0] = not value[0]
            ax.set_grid(value)
            a.figobj.set_bmp_update(False)
            canvas = self.GetParent().canvas
            canvas.draw()

        def grid_y(evt, self=self):
            value[1] = not value[1]
            ax.set_grid(value)
            a.figobj.set_bmp_update(False)
            canvas = self.GetParent().canvas
            canvas.draw()

        m = wx.Menu()
        menus = [
            ['X', grid_x, None],
            ['Y', grid_y, None], ]
        cbook.BuildPopUpMenu(m, menus)
        x, y = evt_GetPosition(evt)
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def ToggleGrid(self):
        asel = self.GetParent().axes_selection

        if asel is None:
            return
        a = asel()
        if a is None:
            return
        ax = a.figobj
        value = ax.getp('grid')
        value[0] = not value[0]
        value[1] = not value[1]
        ax.set_grid(value)
        a.figobj.set_bmp_update(False)
        canvas = self.GetParent().canvas
        canvas.draw()

    def ToggleNoMargin(self):
        figure = self.GetParent().get_figure()
        figure.figobj.set_nomargin(not figure.figobj.get_nomargin())
        canvas = self.GetParent().canvas
        property_editor = self.GetParent().property_editor
        canvas.draw()
        property_editor.update_panel()

    def Toggle3D(self):
        asel = self.GetParent().axes_selection
        if asel is None:
            return
        a = asel()
        if a is not None:
            figobj = a.figobj

            if figobj is None:
                return
            if a.figobj.get_3d():
                if sum([len(x._member) for x in figobj._zaxis]) != 0:
                    dialog.message(self, 'panel has 3D plot', 'error')
                    return
                figobj.set_3d(False)
            else:
                figobj.set_3d(True)
#           figobj.reset_artist()
            canvas = self.GetParent().canvas
            canvas.draw()
            self.GetParent().set_axes_selection(figobj._artists[0])

    def LineInsert(self, btask, btnl):
        self.mode = 'line'
        self.GetParent().line_insert()
        for p in self.p2:
            if p != btnl:
                p.SetToggled(False)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)

    def Curve2Insert(self, btask, btnl):
        self.mode = 'curve2'
        self.GetParent().line_insert(mode=1)
        for p in self.p2:
            if p != btnl:
                p.SetToggled(False)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)

    def ToggleCB(self):
        asel = self.GetParent().axes_selection
        psel = self.GetParent().selection

        if asel is None:
            return
        a = asel()
        if a is None:
            return

        artists = [p() for p in psel]
        ax = a.figobj

        if len(artists) == 0:
            if False in [p.has_cbar() for p in ax._caxis]:
                for k, p in enumerate(ax._caxis):
                    if not p.has_cbar():
                        p.show_cbar(ax, offset=-0.1 * k)
            else:
                for p in ax._caxis:
                    p.hide_cbar(ax)
        else:
            figobjs = [a.figobj for a in artists]
            for figobj in figobjs:
                if figobj is None:
                    continue
                if hasattr(figobj, 'has_cbar'):  # check if cbar user
                    if figobj.has_cbar():
                        figobj.hide_cbar()
                    else:
                        index = ax._caxis.index(figobj.get_caxisparam())
                        figobj.get_caxisparam().show_cbar(ax, offset=-0.1 * index)
        canvas = self.GetParent().canvas
        canvas.draw()
        ifigure.events.SendChangedEvent(ax, w=canvas)

    def ToggleProp(self):
        top = self.GetTopLevelParent()
        top.toggle_property()

    def ToggleZoomUpDown(self):
        self.zoom_up_down = 'up' if self.zoom_up_down == 'down' else 'down'
        self._set_zoomcxr()

    def ToggleZoomForward(self):
        # up -> donw if it is already down return False
        if self.zoom_up_down == 'up':
            self.ToggleZoomUpDown()
            return True
        else:
            return False

    def ToggleZoomBackward(self):
        # down -> up if it is already up return False
        if self.zoom_up_down == 'down':
            self.ToggleZoomUpDown()
            return True
        else:
            return False

    def ToggleZoomMenu(self):
        self.zoom_menu = 1 if self.zoom_menu == 0 else 0
        self._set_zoomcxr()

    def TogglePanAll(self):
        self.pan_all = 1 if self.pan_all == 0 else 0
        self._set_pancxr()

    def onHitExtra(self, evt, btnl):
        btask = btnl.btask
        if btnl.tg == 0:
            self._extra_buttons[btask](evt)
            return
        else:
            btnls = [b for b in self.p1 if (isinstance(b, bp.ButtonInfo)
                                            and b.tg == btnl.tg)]
            self._extra_buttons[btask](evt)
            for b in btnls:
                if b == btnl:
                    b.SetToggled(True)
                    b.SetBitmap(b.bitmap2)
                else:
                    b.SetToggled(False)
                    b.SetBitmap(b.bitmap1)

    def ClickP1Button(self, name):
        '''
        programatically click a button, whose
        task is name
        '''
        p1 = self.p1
        if self.three_d_bar:
            choice = self.p1_choice[1]
        else:
            choice = self.p1_choice[0]

        pt = None
        for info in self.p1:
            if isinstance(info, str):
                continue
            if (info.btask == name or
                    info.btask == name + '_' + choice):
                rect = info.GetRect()
                pt = wx.Point(int(rect[0] + rect[1] / 2.),
                              int(rect[1] + rect[3] / 2.))

        if pt is None:
            return
        evt1 = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
        evt2 = wx.MouseEvent(wx.wxEVT_LEFT_UP)
        evt1.SetEventObject(self)
        evt2.SetEventObject(self)
        evt1.SetPosition(pt)
        evt2.SetPosition(pt)
        self.ProcessEvent(evt1)
        self.ProcessEvent(evt2)
        self.Refresh()
        wx.CallLater(100, self.make_all_normal)

    def _set_zoomcxr(self):
        if self.zoom_up_down == 'up':
            self.GetParent().canvas.SetCursor(
                self.zoom_crs[0 + self.zoom_menu * 2])
        else:
            self.GetParent().canvas.SetCursor(
                self.zoom_crs[1 + self.zoom_menu * 2])

    def _set_pancxr(self):
        self.GetParent().canvas.SetCursor(self.pan_crs[self.pan_all])
