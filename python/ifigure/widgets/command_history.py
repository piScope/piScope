import wx
import wx.stc as stc
import keyword
#import  ifigure.icon.images as images
from ifigure.widgets.script_editor import faces, PythonSTC
import ifigure


class HistoryPopUp(wx.Menu):
    def __init__(self, parent, reload=False):
        super(HistoryPopUp, self).__init__()
        menus = [  # ('Cut',  parent.onCut, None),
            ('Copy', parent.onCopy, None),
            ('Copy To Shell', parent.onCopyToShell, None),
            #                 ('Paste', parent.onPaste, None),
            #                 ('Delete', parent.onDeleteBack, None),
            #                 ('---', None, None,),
            ('Select All', parent.onSelectAll, None),
            ('---', None, None,),
            ('Run Selection', parent.onRunSelection, None), ]

#                 ('Export to command history', parent.onExportHistoryToCommand, None)]
        ifigure.utils.cbook.BuildPopUpMenu(self, menus, eventobj=parent)


class LinePythonSTC(PythonSTC):
    def __init__(self, *args, **kargs):
        PythonSTC.__init__(self, *args, **kargs)
        self.MarkerSetForeground(1, 'GOLD')
        self.MarkerSetBackground(1, 'GOLD')
        self._marker1s = []
        self._margins = [self.GetMarginWidth(
            0), self.GetMarginWidth(1), self.GetMarginWidth(2)]
        self._get_down = -1
        self._line_down = -1
        self._marked_line = (-1, -1)
        self._dnd_started = False
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)

    def x2margin(self, x):
        if x < self._margins[0]:
            return 0
        elif (x >= self._margins[0] and
              x < self._margins[0] + self._margins[1]):
            return 1
        elif (x >= self._margins[0] + self._margins[1] and
              x < self._margins[0] + self._margins[1] + self._margins[2]):
            return 2
        else:
            return 3

    def OnKeyPressed(self, event):
        def SE_Cut():
            'cut for script editor'
            self.GetTopLevelParent().SetStatusText('cut')
            if self.GetSelectedText() == '':
                pos2 = self.GetCurrentPos()
                self.SetSelection(self._mark, pos2)
            self.Cut()
            self._ctrl_K = False
            return

        def SE_Copy():
            self.GetTopLevelParent().SetStatusText('copy')
            sel = self.GetSelection()
            if self.GetSelectedText() == '':
                pos2 = self.GetCurrentPos()
                self.SetSelection(self._mark, pos2)
            self.Copy()
            self.SetSelection(sel[0], sel[1])
            self._ctrl_K = False
            return

        if self.CallTipActive():
            self.CallTipCancel()
        if self.AutoCompActive():
            self.AutoCompCancel()

        key = event.GetKeyCode()
        if hasattr(event, 'RawControlDown'):
            controlDown = event.RawControlDown()
        else:
            controlDown = event.ControlDown()
        altDown = event.AltDown()

        if (self._search != 0 and
            not controlDown and
                not altDown):

            event.Skip()
            return
        if (self._search != 0 and
                not (key == 71 and controlDown)):   # not  control G
            # in search mode ctrl+S or ctrl+R are
            # the only option otherwise
            # it exits from search mode
            # ctrl+G in search mode is treated later...
            if key == wx.WXK_SHIFT:
                event.Skip()
                return
            if key == wx.WXK_CONTROL:
                event.Skip()
                return
            if key == wx.WXK_RAW_CONTROL:
                event.Skip()
                return
            if not ((key == 83 and controlDown) or
                    (key == 82 and controlDown)):
                self._search = 0
                self._search_st = -1
                self.set_search_text('')

        if key == wx.WXK_SPACE:
            self._mark = self.GetCurrentPos()
            self.GetTopLevelParent().SetStatusText('mark set')

        if key == 32:
            pass
        elif key == 68 and controlDown:  # ctrl + D (delete)
            self.CharRight()
            self.DeleteBackNotLine()
            return

        elif key == 67 and controlDown:  # ctrl + C (copy)
            SE_Copy()
            return

        elif key == 86 and controlDown:  # ctrl + V ( skip 10 lines)
            tmp = self.GetCurrentLine()
            c = 0
            while tmp < self.GetLineCount() and c < 10:
                #               print tmp, self.GetLineVisible(tmp)
                tmp = tmp+1
                if self.GetLineVisible(tmp):
                    c = c+1

            self.GotoLine(tmp)

            return

        elif key == 87 and event.AltDown():  # alt + W (copy)
            SE_Copy()
            return

        elif key == 69 and controlDown:  # ctrl + E (end of line)
            self.LineEnd()
            return
        elif key == 78 and controlDown:  # control + N (next command)
            self.LineDown()
            return
        elif key == 80 and controlDown:  # ctrl + P (prev command)
            self.LineUp()
            return
        elif key == 65 and controlDown:  # ctrl + A (beginning)
            self.Home()
            return
        elif key == 70 and controlDown:  # ctrl + F (forward)
            self.CharRight()
            return
        elif key == 66 and controlDown:  # ctrol + B (back)
            self.CharLeft()
            return
        elif key == 83 and controlDown:  # ctrl + S (search)
            #            print('forward search', self._search)

            if self._search == 0:
                self._search = 1
                self.set_search_text('')
                self._search_st = self.GetCurrentPos()
            else:
                self._search = 1

            tmp = self.GetCurrentPos()
            for i in range(len(self._search_txt)):
                self.CharRight()
            self.SearchAnchor()

            if self._search_txt != '':
                if self.SearchNext(0, self._search_txt) == -1:
                    self.set_search_status_text(fail=True)
                    self.SetCurrentPos(tmp)
                    self.SetSelectionEnd(tmp)
                    self.SetSelectionStart(tmp)
            self.EnsureCaretVisible()
#            self.Bind(wx.EVT_CHAR, self.onSearch)
            return

        elif key == 82 and controlDown:  # ctrl + R (search)
            if self._search == 0:
                self._search = 2
                self.set_search_text('')
                self._search_st = self.GetCurrentPos()
            else:
                self._search = 2
            self.SearchAnchor()
            if self._search_txt != '':
                if self.SearchPrev(0, self._search_txt) == -1:
                    self.set_search_status_text(fail=True)
            self.EnsureCaretVisible()
#            self.Bind(wx.EVT_CHAR, self.onSearch)
            return

        elif key == 71 and controlDown:  # ctrl + G (exit search)
            self._mark = -1
            self._search = 0
            self.set_search_text('')
#            self.SetCurrentLine(self._search_st[0])
            if self._search_st != -1:
                self.SetCurrentPos(self._search_st)
                self.SetSelectionEnd(self._search_st)
                self.SetSelectionStart(self._search_st)
                self.EnsureCaretVisible()
            self._search_st = -1
#            self.Unbind(wx.EVT_CHAR)
            return
        event.Skip()

    def update_marker(self, l1, l2):
        if len(self._marker1s) != 0:
            self.MarkerDeleteAll(1)
            self._marker1s = []
            if l1 == l2:
                return
        for x in range(l2-l1+1):
            self._marker1s.append(self.MarkerAdd(l1+x, 1))
        self._marked_line = (l1, l2)

    def reset_selection(self):
        sels, sele = self.GetSelection()
        self.SetSelection(sels, sele)
        self.Refresh()

    def onLeftDown(self, e):
        self._line_down = self.LineFromPosition(
            self.PositionFromPoint(e.GetPosition()))
        self._get_down = self.PositionFromPoint(e.GetPosition())
        e.Skip()

    def onLeftUp(self, e):
        #        print 'left up'
        #        print self.PositionFromPoint(e.GetPosition())
        if self._get_down == self.PositionFromPoint(e.GetPosition()):
            st, et = self.GetSelection()
#            print 'here', st, et
#            print self.LineFromPosition(st)
#            print self.LineFromPosition(self.PositionFromPoint(e.GetPosition()))
            if (st != et and
                self.LineFromPosition(st) ==
                    self.LineFromPosition(self.PositionFromPoint(e.GetPosition()))):
                wx.CallAfter(self.SetSelection, self._get_down, self._get_down)
#               wx.CallAfter(self.update_marker, 0,0)
#               self.SetSelection(0,0)
                e.Skip()
                return
        l1 = self.LineFromPosition(self._get_down)
        l2 = self.LineFromPosition(self.PositionFromPoint(e.GetPosition()))
#        print(l1, l2)
        ls = min([l1, l2])
        le = max([l1, l2])
        if ls == 0:
            st = 0
        else:
            st = self.GetLineEndPosition(ls-1) + 1
        et = self.GetLineEndPosition(le)

        wx.CallAfter(self.SetSelection, st, et)
#        wx.CallAfter(self.update_marker, l1, l2)
        e.Skip()

    def onDragInit(self, e):
        self.Unbind(wx.EVT_MOTION)

    def OnStartDrag(self, evt):
        sel = self.GetSelectedText()
        sel = '\n'.join([x[1:]
                         for x in sel.split('\n') if not x.startswith("'''")])
        # evt.SetDragAllowMove(False)
        evt.SetDragText(sel)
        p = self
        while p.GetParent() is not None:
            p = p.GetParent()

        p._text_clip = sel

    def onRightUp(self, evt):
        m = HistoryPopUp(self)
        self.PopupMenu(m,
                       (evt.GetX(), evt.GetY()))
        m.Destroy()

    def onExportHistoryToCommand(self):
        pass

    def onCopyToShell(self, evt):
        '''
        need to over write to remove leading space 
        '''
        sp, ep = self.GetSelection()
        l1 = self.LineFromPosition(sp)
        l2 = self.LineFromPosition(ep)
        line = []
        eol = self.get_EOL_txt()
        if l1 == l2:
            line = self.GetTextRange(sp, ep)
            if len(line) == 0:
                return
            line = [line]
        else:
            for i in range(l2-l1+1):
                line.append(str(self.GetLine(l1+i)).strip(eol))
        if len(line) == 0:
            return
        line = [x[1:] for x in line if not x.startswith("'''")]

        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
        for i, x in enumerate(line):
            self.CopyText(len(x), x)
            app.shell.Paste()
            if i != len(line)-1:
                app.shell.NewLine()


class CommandHistory(wx.Panel):
    def __init__(self, parent, *args, **kargs):
        super(CommandHistory, self).__init__(parent, *args, **kargs)
        self.log = LinePythonSTC(
            self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.log.SetSelectionMode(wx.stc.STC_SEL_LINES)

        self.log.SetReadOnly(True)
#        sys.stdout = RedirectOutput(self.log)
#        sys.stderr = RedirectOutput(self.log)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.clear_text()

#        self.log.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
#        self.log.Bind(wx.EVT_LEFT_UP, self.onLeftUp)

    def Copy(self):
        self.log.Copy()

    def Cut(self):
        # map cut to copy
        self.log.Copy()

    def Paste(self):
        pass
        # self.log.Copy()

    def date_string(self):
        import datetime
        return "''' " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + "\n'''\n"

    def savetofile(self, filename=''):
        fid = open(filename, 'w')
        txt = self.log.GetText()
        fid.write(txt)
        fid.close()

    def loadfromfile(self, filename=''):
        fid = open(filename, 'r')
        lines = fid.readlines()
        fid.close()
        self.log.SetReadOnly(False)
        self.log.SetText(''.join(lines))
        self.log.SetReadOnly(True)
        self.append_text(self.date_string(), no_indent=True)

    def clear_text(self):
        self.log.SetReadOnly(False)
        self.log.SetText(self.date_string())
        self.log.SetReadOnly(True)

    def append_text(self, new_txt, no_indent=False):
        self.log.SetReadOnly(False)
        txt = self.log.GetText()
        if (not txt.endswith('\n') and
                txt[-2:] != '\n\n'):
            txt += '\n'
        if no_indent:
            txt += str(new_txt)
        else:
            for x in new_txt.split('\n'):
                txt += ' '+str(x) + '\n'
            txt = txt[:-1]
        l = self.log.GetFirstVisibleLine()
        self.log.SetText(txt)
        self.log.SetReadOnly(True)
        self.log.ScrollToLine(l)
