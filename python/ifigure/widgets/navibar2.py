import os,  wx, ifigure
import numpy as np
import wx.lib.platebtn as platebtn
import wx.lib.buttons as buttons
import wx.lib.agw.buttonpanel as bp
import ifigure.utils.cbook as cbook
from ifigure.mto.fig_axes import FigInsetAxes
import ifigure.widgets.dialog as dialog

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty,UndoRedoFigobjProperty,UndoRedoFigobjMethod

def make_bitmap_with_bluebox(bitmap):
        ### second bitmap has blue box around it
        h, w = bitmap.GetSize()
        image = bitmap.ConvertToImage()
        alpha = np.fromstring(image.GetAlphaData(), 
                              dtype=np.uint8).reshape(w, h, -1)
        array = np.fromstring(image.GetData(), 
                   dtype=np.uint8)
        array = array.reshape(w, h, array.shape[0]/w/h)
        array[0,   1:-2,  :1]  = 0 
        array[-1,  1:-2,  :1]  = 0
        array[1:-2,   0,  :1]  = 0
        array[1:-2,  -1,  :1]  = 0

        array[1,1,:1] = 0
        array[1,-2,:1] = 0
        array[-2,1,:1] = 0
        array[-2,-2,:1] = 0

        array[1,1,  2] = 255
        array[1,-2, 2] = 255
        array[-2,1, 2] = 255
        array[-2,-2,2] = 255

#        array[:2,:,1]=0
#        array[-2:,:,1]=0
#        array[:,:2,1]=0
#       array[:,-2:,1]=0
        array[0,   1:-2, 2]=255
        array[-1,  1:-2, 2]=255
        array[1:-2,   0, 2]=255
        array[1:-2,  -1, 2]=255

        alpha[1:-2,   -1] = 127
        alpha[1:-2,    0] = 127
        alpha[0,    1:-2] = 127
        alpha[-1,   1:-2] = 127
        alpha[1,1] = 127
        alpha[1,-2] = 127
        alpha[-2,1] = 127
        alpha[-2,-2] = 127
        image = wx.EmptyImage(h, w)
        image.SetData(array.tostring())
        image.SetAlphaData(alpha.tostring())
        bitmap2 = image.ConvertToBitmap()

        return bitmap2

    
three_d_bar = False
btasks0 = [#('previous', 'arrowleft.png', 0, 'previous page'),
           #        ('next',   'arrowright.png', 0,'next page'),
           #        ('---',    (10,10), 0, ''),
#                   ('copy',   'copy.png', 0, ''),
#                   ('paste',  'paste.png', 0, ''),
                   ('pmode',   'pmode.png', 1, 'plot mode'),
                   ('amode',   'amode.png', 1, 'annotation mode'),
                   ('---',    (10,10), 0, ''),]

btasks1=[('select', 'select.png', 1, 'select', True),
         ('zoom',   'zoom2.png', 1,
          '\n'.join(['zoom', ' shift: zoom down', ' alt: menu to pick direction']),
          True),
         ('pan',   'arrowmove.png', 1, '\n'.join(['pan', ' shift: pan all']), True),
         ('cursor',   'cursor.png', 1, 'cursor', True, True),
         ('3dzoom',   'threed_rot.png', 1, '3D zoom', False, True),]
         
btasks1.extend([
                ('---',    (10,10), 0, '', True),
                ('xlog',  'xlog.png', 0, 'toggle xlog', True, False),
                ('ylog',   'ylog.png', 0, 'toggle ylog', True, False),
                ('xauto',  'xauto.png', 0, 'autoscale x', True),
                ('yauto',  'yauto.png', 0, 'autoscale y', True),
                ('grid',   'grid.png', 0, 'toggle grid', True, False),
#                ('colorbar', 'colorbar.bmp', 0, 'color bar'),
                ('nomargin', 'margin.png', 0, 'no margin mode', True, True),])
#                ('3d',   'three_d.png', 0, '3D axis', False), ])

btasks2=[#('selecta', 'select.bmp', 1, 'select'),
                 ('text',   't.png', 1, 'insert text'),
                 ('line',  'line.png',  1, 'insert line'),
#                 ('curve2', 'curve.png', 1, 'insert curve'),
                 ('curve', 'curve.png', 1, 'insert curve'),
                 ('arrow', 'arrow.png', 1, 'insert arrow'),
                 ('circle', 'circle.png', 1, 'insert circle'),
                 ('rect',   'box.png', 1, 'insert rectangle'),
                 ('legend', 'legend.png', 1, 'insert legend'),
                 ('colorbar', 'colorbar.png', 1, 'insert colorbar'),
                 ('eps', 'eps.png', 1, 'insert eps'),]

btasks3=[('copy_cb', 'copy.png', 0, 'copy image to clipboard'),
         ('save_pic', 'save_pic.png', 0, 'save graphic'),
         ('mail_pic', 'mail_pic.png', 0, 'mail graphic'),
         ('toggle_prop', 'form.png', 0, 'show property'),
#         ('trash', 'trash.png', 0, 'delete page')
         ]
 
hotspot = {'zoom':[5,5], 'circle':[8,8], 'rect':[8,8], 
           'curve':[10,10], 'curve2':[10,10], 
           'line':[2,15], 'pan':[8,8]}

zoom_crs = None
pan_crs = None

class TaskBtnList(list):
    def get_btn(self, name):
        for m in self:
            if m.btask == name: return m
        return 

class ButtonInfo(bp.ButtonInfo):
    def __init__(self, *args, **kwargs):
        bp.ButtonInfo.__init__(self, *args, **kwargs)
        self.use_in_2d_menu = True
        self.use_in_3d_menu = True
    def GetBestSize(self):
        size = self.GetBitmap().GetSize()
        h = 26
        return ((h-size[1])/2+size[0], h)
class ButtonPanel(bp.ButtonPanel):
    def DoGetBestSize(self):
        s = super(ButtonPanel,self).DoGetBestSize()
        return s

    def Clear(self):
        # this is necessary for wxpython.2.9....
        self.Freeze()
        bp.ButtonPanel.Clear(self)
#        self.Thaw()

class navibar(ButtonPanel):
    def __init__(self, parent, id=-1, text='', *args, **kargs):
        super(navibar, self).__init__(parent, id,  text, *args, **kargs)
        self.mode = ''    # mode of action (''=select, 'pan', 'zoom', 'text'....)
        self.ptype = ''   # palette type ('pmode', 'amode')
        self.rotmode = False
        self.three_d_bar = False

        self.p0  = self.make_button_group(self, btasks0)
        self.p1  = self.make_button_group(self, btasks1)
        self.p2  = self.make_button_group(self, btasks2)
        self.p3  = self.make_button_group(self, btasks3)
        self.btasks0 = btasks0[:]
        self.btasks1 = btasks1[:]
        self.btasks2 = btasks2[:]
        self.btasks3 = btasks3[:]
        self.SetPMode(skip_sc=True)
        self._extra_buttons = {}
        self.zoom_up_down = 'up'
        self.zoom_menu = 0    # 0 or 1
        self.pan_all = 0
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_KEY_DOWN,  self.OnKeyDown)
#        self.Bind(wx.EVT_KEY_UP,  self.OnKeyUp)

        from ifigure.ifigure_config import icondir
        if zoom_crs is None:
            from ifigure.utils.cbook import make_crs_list
            path1=os.path.join(icondir, '16x16', 'zoom2.png')
            path2=os.path.join(icondir, '16x16', 'zoom2minus.png')
            path3=os.path.join(icondir, '16x16', 'zoom2menu.png')
            path4=os.path.join(icondir, '16x16', 'zoom2minusmenu.png')
            globals()['zoom_crs'] = make_crs_list([path1, path2, path3, path4], 5, 5)
            path1=os.path.join(icondir, '16x16', 'arrowmove.png')
            path2=os.path.join(icondir, '16x16', 'arrowmove_all.png')
            globals()['pan_crs'] = make_crs_list([path1, path2,], 5, 5)
            path1=os.path.join(icondir, '16x16', 'threed_rot.png')
            globals()['threed_crs'] = make_crs_list([path1,], 5, 5)
        self.zoom_crs = zoom_crs
        self.pan_crs = pan_crs
        self.threed_crs = threed_crs
        self._curve_mode = 'pp'

    def add_extra_group1_button(self, idx, data, 
                                use_in_2d_menu = True, 
                                use_in_3d_menu = False):
        xx =list(data[:4])
        xx.append(use_in_2d_menu)
        xx.append(use_in_3d_menu)
        self.btasks1.insert(idx, xx)
        self.p1  = self.make_button_group(self, self.btasks1)
        self._extra_buttons[data[0]] = data[-1]
        self.SetPMode()

    def make_button_group(self, parent, btasks):
        bts = TaskBtnList()
        for items in btasks:
           btask, icon, tg, hint = items[:4]
           if btask == '---':
              bts.append('---') 
#              bts.AddSpacer(icon)
              continue
           from ifigure.ifigure_config import icondir
           path=os.path.join(icondir, '16x16', icon)
           if icon[-3:]=='png':
              im = wx.Image(path, wx.BITMAP_TYPE_PNG)
              image = im.ConvertToBitmap()
#              im = im.ConvertToGreyscale()
#              im = im.ConvertToMono(0,0,0)
              if im.HasAlpha(): im.ConvertAlphaToMask()
              if btask in hotspot:       
                  im.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot[btask][0]) 
                  im.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot[btask][1]) 
              crs =  wx.CursorFromImage(im)
           if icon[-3:]=='bmp':
              im = wx.Image(path, wx.BITMAP_TYPE_BMP)
              image = im.ConvertToBitmap()
              if im.HasAlpha(): im.ConvertAlphaToMask()
              crs =  wx.CursorFromImage(im)
           #image.SetSize((8,8))
#           btnl = ButtonInfo(self, wx.NewId(), image)
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
               btnl.use_in_2d_menu  = items[4] 
           if len(items) > 5:
               btnl.use_in_3d_menu  = items[5] 
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
        ret = self.HitTest(evt.GetPositionTuple())
        if ret[0]==wx.NOT_FOUND:
            return super(navibar, self).OnLeftUp(evt)            
        
        super(navibar, self).OnLeftUp(evt)                    
        btask = self.allbinfo[ret[0]].btask    
        self.OnRightButton(evt, btask)

    def OnRightButton(self, evt, btask):
        if btask == 'mail_pic': self.MailPicRight(evt)
        elif btask == 'curve':  self.CurveRight(evt)
        elif btask == 'grid':  self.ToggleGridRight(evt)

    def OnLeftUp(self, evt):
        ret = self.HitTest(evt.GetPositionTuple())
        if ret[0]==wx.NOT_FOUND:
            return super(navibar, self).OnLeftUp(evt)            
        
        super(navibar, self).OnLeftUp(evt)                    
        btask = self.allbinfo[ret[0]].btask    
        self.OnButton(evt, btask)

    def OnButton(self, evt, btask):
        frame =  cbook.FindFrame(self)
        btnl = [x for x in self.allbinfo if x.btask == btask][0]
        #        btnl = evt.GetEventObject()
        evt.SetEventObject(self)

        if btask == 'trash': frame.onDelPage(evt)
        elif btask == 'pmode': 
             self.ExitInsertMode()
             self.SetPMode()
        elif btask == 'amode': 
             self.ExitInsertMode()
             self.SetAMode()
        elif btask == 'select': self.SetSelect()
        elif btask == 'zoom': self.SetZoom(btnl)
        elif btask == 'pan': self.SetPan(btnl)
        elif btask == 'cursor': self.SetCursor()
        elif btask == '3dzoom': self.Set3DZoom(btnl)
        elif btask == 'next': frame.onNextPage(evt)
        elif btask == 'previous': frame.onPrevPage(evt)
        elif btask == 'xlog': self.SetXlog()
        elif btask == 'ylog': self.SetYlog()
        elif btask == 'xauto': self.SetXAuto()
        elif btask == 'yauto': self.SetYAuto()
        elif btask == 'save_pic': self.SavePic()
        elif btask == 'mail_pic': self.MailPic()
        elif btask == 'toggle_prop': self.ToggleProp()
        elif btask == 'copy_cb': self.CopyToCB()
#        elif btask == 'colorbar': self.ToggleCB()
        elif btask == 'grid': self.ToggleGrid()
        elif btask == 'nomargin': self.ToggleNoMargin()
        elif btask == '3d': self.Toggle3D()
        elif btask in self._extra_buttons:
           self._extra_buttons[btask]()
        elif btask == 'line': 
           self.GetParent().exit_layout_mode() # just in case...
           if btnl.GetToggled():
               self._set_bitmap2(self.p2, self.p2.index(btnl))
               self.LineInsert(btask,btnl)
               self.SetInsertMode(btask, btnl)
           else:
               self.ExitInsertMode()
               #               self.SetAMode()
        elif btask == 'curve' and self._curve_mode == 'pp': 
           self.GetParent().exit_layout_mode() # just in case...
           if btnl.GetToggled():
               self._set_bitmap2(self.p2, self.p2.index(btnl))
               self.Curve2Insert(btask,btnl)
               self.SetInsertMode(btask, btnl)
           else:
               self.ExitInsertMode()
               #               self.SetAMode()
        else:
           self.GetParent().exit_layout_mode() # just in case...
           if btnl.GetToggled():
              self._set_bitmap2(self.p2, self.p2.index(btnl))
              self.mode= btask 
              self.SetInsertMode(btask, btnl)
           else:
              self.ExitInsertMode()
              #              self.SetAMode()

    def SetInsertMode(self, btask, btnl):
        for p in self.p2:
            if p != btnl: p.SetToggled(False)

        p = btnl
        sc = wx.StockCursor(wx.CURSOR_WAIT)
        self.GetParent().canvas.SetCursor(p.custom_cursor)
#        print 'changing cursor'
              #
    def ExitInsertMode(self):
#        print 'exiting insert mode'
        sc = wx.StockCursor(wx.CURSOR_DEFAULT)
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
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p2: self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.ptype = 'amode'
        self.GetParent()._show_cursor = False
        sc = wx.StockCursor(wx.CURSOR_DEFAULT)
        self.GetParent().canvas.SetCursor(sc)

    def SetPMode(self, skip_sc=False):
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self.pbutton.SetStatus('Toggled')
        self.abutton.SetStatus('Normal')
        self.pbutton.SetToggled(True)
        self.abutton.SetToggled(False)
        self._set_bitmap2(self.p0, self.ipbutton)
        for b in self.p0: self.AddButtonOrS(b)

        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.SetSelect(skip_sc = skip_sc)
        self.ptype = 'pmode'
        self.GetParent()._show_cursor = False

    def SetSelect(self, skip_sc = False):
        if self.rotmode:
           self.rotmode = False
           self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 0)
        self._set_toggle(0)
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p1: self.AddButtonOrS(b)                            
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = ''
        self.GetParent()._show_cursor = False
        if not skip_sc:
            sc = wx.StockCursor(wx.CURSOR_DEFAULT)
            self.GetParent().canvas.SetCursor(sc)

    def _set_bitmap2(self, array, index):
        for p in array:
            if isinstance(p, str): continue
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
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p1: self.AddButtonOrS(b)                    
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'zoom'
        self.GetParent()._show_cursor = False
        self.zoom_up_down = 'up'
        self.zoom_menu = 0
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode() # just in case...
        asel = self.GetParent().axes_selection
        if asel is None: return
        a = asel()
        if a is None: return
        if a.figobj.get_3d():
             self.GetParent().set_3dzoom_mode(True, pan_btn = 11, 
                                        zoom_btn = 1, rotate_btn = 10)

    def SetPan(self,btnl):
        if self.rotmode:
            self.rotmode = False
            self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 2)
        self._set_toggle(2)
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p1: self.AddButtonOrS(b)            
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'pan'
        self.pan_all = 0
        self.GetParent()._show_cursor = False
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode() # just in case...

        asel = self.GetParent().axes_selection
        if asel is None: return
        a = asel()
        if a is None: return
        if a.figobj.get_3d():
             self.GetParent().set_3dzoom_mode(True, pan_btn = 1, 
                                        zoom_btn = 11, rotate_btn = 10)

    def SetCursor(self):
        if self.rotmode:
           self.rotmode = False
           self.GetParent().set_3dzoom_mode(False)
        self.Clear()
        self._set_bitmap2(self.p1, 3)
        self._set_toggle(3)
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p1: self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.mode = 'cursor'
        self.GetParent()._show_cursor = True
        sc = wx.StockCursor(wx.CURSOR_DEFAULT)
        self.GetParent().canvas.SetCursor(sc)
        self.GetParent().exit_layout_mode() # just in case...

    def Set3DZoom(self, btnl):
        self.Clear()
        self._set_bitmap2(self.p1, 4)
        self._set_toggle(4)
        for b in self.p0: self.AddButtonOrS(b)
        for b in self.p1: self.AddButtonOrS(b)
        self.AddSpacer()
        for b in self.p3: self.AddButtonOrS(b)
        self.DoLayout()
        self.rotmode = True
        self.GetParent().set_3dzoom_mode(True)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)
        self.GetParent().exit_layout_mode() # just in case...
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
            if self.p1[i] == '---': return
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
           if not self.three_d_bar:
              if not b.use_in_2d_menu: return
           if self.three_d_bar:
              if not b.use_in_3d_menu: return

           self.AddButton(b)
           self.allbinfo.append(b)
        else:
           self.AddSeparator()

    def Show3DMenu(self):
        if self.three_d_bar: return            
        self.three_d_bar = True
        globals()['three_d_bar'] = True
        if self.ptype == 'pmode': self.SetPMode()

    def Hide3DMenu(self):
        if not self.three_d_bar: return            
        self.three_d_bar = False
        globals()['three_d_bar'] = False
        if self.ptype == 'pmode': self.SetPMode()

    def SetXYlog(self, name):
        asel = self.GetParent().axes_selection
        if asel is None: return
        a = asel()
        if a is None: return

        fig_axes = a.figobj
        p = fig_axes.get_axis_param(name)
        value = p.get_rangeparam()

#        print m
        ov =  str(value[3])
        if ov == 'log':
           scale = 'linear'
        if ov == str('linear'):
           scale = 'log'

        canvas = self.GetParent()
        requests = canvas.make_xyauto_request(fig_axes, name, scale = scale)
        requests[fig_axes] = fig_axes.compute_new_range(request = requests[fig_axes])
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
        data =  ['eps', 'pdf', 'svg', 'png', 'jpeg', 'pdfall', 'gifanim']
        idx = data.index(self.GetParent()._mailpic_format)
        m = wx.Menu()
        menus =[
                ['EPS',  mailpic_set_eps, None],
                ['PDF',  mailpic_set_pdf, None],
                ['SVG',  mailpic_set_svg, None],
                ['PNG',  mailpic_set_png, None],
                ['JPEG',  mailpic_set_jpeg, None],
                ['Multipage PDF',  mailpic_set_pdfall, None],
                ['Animated Gif',  mailpic_set_gifanim, None],]
        menus[idx][0] = '^'+ menus[idx][0]
        
        cbook.BuildPopUpMenu(m, menus)
        x,y = evt.GetPositionTuple()
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def CurveRight(self, evt):
        def curve_set_freehand(evt, self=self):
            self._curve_mode = 'fh'
        def curve_set_pickpoints(evt, self=self):
            self._curve_mode = 'pp'
        data =  ['pp', 'fh']
        idx = data.index(self._curve_mode)
        m = wx.Menu()
        menus =[
                ['PickPoints', curve_set_pickpoints, None],
                ['Freehand',   curve_set_freehand, None],]

        menus[idx][0] = '^'+ menus[idx][0]
        cbook.BuildPopUpMenu(m, menus)
        x,y = evt.GetPositionTuple()
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def CopyToCB(self):
        '''
        Copy_to_Clipboard_mod copys the buffer data
        which does not have highlight drawn
        '''
        canvas = self.GetParent().canvas
        figure_image = canvas.figure_image[0]
        h, w, d  = figure_image.shape
        image = wx.EmptyImage(w, h)
        image.SetData(figure_image[:,:,0:3].tostring())
        image.SetAlphaData(figure_image[:,:,3].tostring())
        bmp = wx.BitmapFromImage(image)
        canvas.Copy_to_Clipboard_mod(pgbar=True,
                                     bmp=bmp)

    def ToggleGridRight(self, evt):
        asel = self.GetParent().axes_selection
        if asel is None: return
        a = asel()
        if a is None: return
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
        menus =[
                ['X',  grid_x, None],
                ['Y',  grid_y, None],]
        cbook.BuildPopUpMenu(m, menus)
        x,y = evt.GetPositionTuple()
        self.PopupMenu(m, [x, y])
        m.Destroy()

    def ToggleGrid(self):
        asel = self.GetParent().axes_selection
        
        if asel is None: return
        a = asel()
        if a is None: return
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
        if asel is None: return
        a = asel()
        if a is not None:
           figobj = a.figobj

           if figobj is None: return 
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
        

    def LineInsert(self,btask,btnl):
        self.mode= 'line'
        self.GetParent().line_insert()
        for p in self.p2:
            if p != btnl: p.SetToggled(False)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)

    def Curve2Insert(self,btask,btnl):
        self.mode= 'curve2'
        self.GetParent().line_insert(mode = 1)
        for p in self.p2:
            if p != btnl: p.SetToggled(False)
        self.GetParent().canvas.SetCursor(btnl.custom_cursor)

    def ToggleCB(self):
        asel = self.GetParent().axes_selection
        psel = self.GetParent().selection

        if asel is None: return
        a = asel()
        if a is None: return
    
        artists = [p() for p in psel]
        ax = a.figobj
  
        if len(artists) == 0:
            if False in [p.has_cbar() for p in ax._caxis]:
                for k, p in enumerate(ax._caxis):
                    if not p.has_cbar(): p.show_cbar(ax, offset=-0.1*k)
            else:
                for p in ax._caxis:
                    p.hide_cbar(ax)
        else:
            figobjs = [a.figobj for a in artists]
            for figobj in figobjs:
                if figobj is None: continue
                if hasattr(figobj, 'has_cbar'): # check if cbar user
                    if figobj.has_cbar():
                        figobj.hide_cbar()
                    else:
                        index = ax._caxis.index(figobj.get_caxisparam())
                        figobj.get_caxisparam().show_cbar(ax, offset = -0.1*index)
        canvas = self.GetParent().canvas
        canvas.draw()
        ifigure.events.SendChangedEvent(ax, w = canvas)

    def ToggleProp(self):
        top = self.GetTopLevelParent()
        top.toggle_property()

    def ToggleZoomUpDown(self):
        self.zoom_up_down = 'up' if self.zoom_up_down == 'down' else 'down'
        self._set_zoomcxr()

    def ToggleZoomMenu(self):
        self.zoom_menu = 1 if self.zoom_menu == 0 else 0
        self._set_zoomcxr()

    def TogglePanAll(self):
        self.pan_all = 1 if self.pan_all == 0 else 0
        self._set_pancxr()

    def _set_zoomcxr(self):
        if self.zoom_up_down == 'up':
           self.GetParent().canvas.SetCursor(self.zoom_crs[0 + self.zoom_menu*2])
        else:
           self.GetParent().canvas.SetCursor(self.zoom_crs[1 + self.zoom_menu*2])

    def _set_pancxr(self):
        self.GetParent().canvas.SetCursor(self.pan_crs[self.pan_all])

