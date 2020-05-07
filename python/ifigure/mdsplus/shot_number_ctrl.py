from __future__ import print_function
import six
import wx
import collections

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('iFigureCanvas')

from ifigure.utils.edit_list import TextDropTarget

color_map = {'g': 'green',
             'r': 'red',
             'b': 'blue',
             'k': 'black',
             'y': 'yellow',
             'm': 'magenta',
             'c': 'cyan'}
max_history = 15


class ShotNumberCtrl(wx.stc.StyledTextCtrl):
    def __init__(self, *args, **kargs):
        self._use_escape = True

        if not 'style' in kargs: kargs['style'] = 0
        kargs['style'] = kargs['style'] |  wx.TE_PROCESS_ENTER
        
        super(ShotNumberCtrl, self).__init__(*args, **kargs)
        
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyPressed)
        self.Bind(wx.EVT_TEXT_ENTER, self.onEnter)
        self.Bind(wx.EVT_LEFT_DOWN, self.onDragInit)
        self.Bind(wx.stc.EVT_STC_CHANGE, self.onContentChanged)
        dt1 = TextDropTarget(self)
        self.SetDropTarget(dt1)
        min_w = 30
        txt_w, txt_h = self.Parent.GetTextExtent('A')
        self.SetMinSize((txt_w*20, txt_h+5))
        self.SetMaxSize((-1, txt_h+5))
        self.SetUseHorizontalScrollBar(False)
        self.SetUseVerticalScrollBar(False)
        self.SetReadOnly(False)
        for x in range(3):
            self.SetMarginWidth(x, 0)
        self._key_history_st1 = collections.deque([], maxlen=max_history)
        self._key_history_st2 = collections.deque([], maxlen=max_history)
        self._len_order = 5
        self._single_mode = False

    def set_color_style(self, order):
        self._len_order = len(order)
        for i, x in enumerate(order):
            c = color_map[x] if x in color_map else x
            if isinstance(c, tuple):
                c = [c[0]*255, c[1]*255, c[2]*255, c[3]*255]
            self.StyleSetForeground(i, c)
        self.StyleSetForeground(10, (0, 0, 0, 0))

    def set_style_bits(self):
        txt = str(self.GetValue())

        pos = self.GetCurrentPos()
        sel1, sel2 = self.GetSelection()
        arr = [x.split(',') for x in txt.split(';')]
        
        if txt.startswith('='):
            sarr = [['\x10'*len(xx) for k, xx in enumerate(x)] for x in arr]
        else:
            sarr = [[chr(k % self._len_order)*len(xx)
                     for k, xx in enumerate(x)] for x in arr]

        sarr = '\x10'.join(['\x10'.join(x) for x in sarr])
        bbb =''.join([''.join(x) for x in zip(txt, sarr)])
        
        self.ClearAll()
        
        #dprint1("bbb=", bbb.__repr__())

        if six.PY3:
            bbb = memoryview(bbb.encode('latin-1'))
        self.AddStyledText(bbb)
        self.SetCurrentPos(pos)
        self.SetSelection(sel1, sel2)

    def SetSingleMode(self, value):
        self._single_mode = value

    def SetValue(self, value):
        if self._single_mode:
            wx.stc.StyledTextCtrl.SetValue(
                self, (value.split(','))[0].split(';')[0])
        else:
            wx.stc.StyledTextCtrl.SetValue(self, value)

    def onContentChanged(self, evt):
        self.Unbind(wx.stc.EVT_STC_CHANGE)
        try:
            self.set_style_bits()
        except:
            import traceback
            traceback.print_exc()
            pass
        self.Bind(wx.stc.EVT_STC_CHANGE, self.onContentChanged)

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
        elif key == 67 and controlDown:  # ctrl + C (copy)
            self.Copy()
            return
        elif key == 87 and controlDown:  # ctrl + X (cut)
            self.Cut()
            return
        elif key == 88 and controlDown:  # ctrl + W (cut)
            self.Cut()
            return
        elif key == 86 and controlDown:  # ctrl + V (paste)
            self.Paste()
            return
        elif key == 89 and controlDown:  # ctrl + Y (paste)
            self.Paste()
            return
        elif key == 70 and controlDown:  # ctrl + F
            self.SetInsertionPoint(self.GetInsertionPoint()+1)
            return
        elif key == 66 and controlDown:  # ctrl + B
            self.SetInsertionPoint(self.GetInsertionPoint()-1)
            return
        elif key == 65 and controlDown:  # ctrl + A (beginning)
            print('move to front')
            self.SetInsertionPoint(0)
            self.SetSelection(0, 0)
            return
        elif key == 69 and controlDown:  # ctrl + E
            self.SetInsertionPoint(self.GetLastPosition())
            return
        elif key == 75 and controlDown:  # ctrl + K
            ### works only for single line ###
            self.SetSelection(self.GetInsertionPoint(),
                              self.GetLastPosition())
            self.Cut()
            return
        elif key == 44:  # ','
            if self._single_mode:
                return
        elif key == 59:  # ';'
            if self._single_mode:
                return
        elif key == wx.WXK_UP:
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

        if key == wx.WXK_RETURN:
            evt = wx.PyCommandEvent(wx.EVT_TEXT_ENTER.typeId,
                                    self.GetId())
            wx.PostEvent(self.GetEventHandler(), evt)
            return

        event.Skip()

    def onEnter(self, evt):
        v = self.GetValue()
        self._key_history_st1.append(v)
        evt.Skip()


#    def onEnter(self, evt):
#        self.GetParent().send_event(self, evt)

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
