from __future__ import print_function
#
#   Script Editor For ifigure
#
#   based on styled_text_control_demo2 in
#   wxpython demo
#
#   modificaiton:
#      2012. added aui.notebook panel
#
#   plan
#      emacs style key-binding
#      namelist syntax?
#
import time
import logging
import os
from ifigure.widgets.statusbar import StatusBarSimple
import sys
from ifigure.widgets.book_viewer import FramePlus, FrameWithWindowList, ID_HIDEAPP
from ifigure.widgets.syntax_styles import *
from ifigure.widgets.debugger import check_debugger_instance
from ifigure.widgets.debugger_core import add_breakpoint, rm_breakpoint, has_breakpoint, get_breakpoint
from ifigure.utils.wx3to4 import EVT_AUINOTEBOOK_TAB_RIGHT_UP, menu_Append, isWX3
import ifigure.widgets.dialog as dialog
from ifigure.utils.minifier import minify
import ifigure.events
import ifigure.utils
import ifigure.widgets.images as images
import wx.stc as stc
import keyword

import wx


use_agw = False
if use_agw:
    import wx.lib.agw.aui as aui
else:
    import wx.aui as aui


# ----------------------------------------------------------------------

demoText = ""

# ----------------------------------------------------------------------


if wx.Platform == '__WXMSW__':
    faces = {'times': 'Times New Roman',
             'mono': 'Courier New',
             'helv': 'Arial',
             'other': 'Comic Sans MS',
             'size': 10,
             'size2': 8,
             }
elif wx.Platform == '__WXMAC__':
    faces = {'times': 'Times New Roman',
             'mono': 'Monaco',
             'helv': 'Arial',
             'other': 'Comic Sans MS',
             'size': 12,
             'size2': 10,
             }
else:
    faces = {'times': 'Times',
             #              'mono' : 'Courier',
             'mono': 'Monospace',
             'helv': 'Helvetica',
             'other': 'new century schoolbook',
             'size': 12,
             'size2': 10,
             }

# ----------------------------------------------------------------------
DebugCurrentLine = 20
DebugBreakPoint = 21


def check_font_width():
    size = faces['size']
    font = wx.Font(pointSize=size, family=wx.DEFAULT,
                   style=wx.NORMAL,  weight=wx.NORMAL,
                   faceName='Consolas')
    dc = wx.ScreenDC()
    dc.SetFont(font)
    w, h = dc.GetTextExtent('A')
    return w, h


class PythonSTCPopUp(wx.Menu):
    def __init__(self, parent, reload=False):
        super(PythonSTCPopUp, self).__init__()
        self.parent = parent
        menus = [('Cut',  parent.onCut, None),
                 ('Copy', parent.onCopy, None),
                 ('Paste', parent.onPaste, None),
                 ('Delete', parent.onDeleteBack, None),
                 ('---', None, None,),
                 ('Select All', parent.onSelectAll, None),
                 ('Wrap', parent.onWrapText, None), ]
        if hasattr(parent.GetParent().GetParent(), 'ToggleFindPanel'):
            if not parent.GetParent().GetParent().get_findpanel_shown():
                menus.extend([('---', None, None,),
                              ('Find...', parent.onFindText, None), ])
        if parent.doc_name.endswith('.py'):
            menus = menus + [('---', None, None),
                             ('Shift region right', parent.onRegionRight, None),
                             ('Shift region left',  parent.onRegionLeft, None),
                             ('Format (autopep8)',  parent.onAutopep8, None), ]
            if parent.check_if_in_script_editor():
                if parent.get_td() is not None:
                    menus = menus + [
                        ('Run in Shell (F9)', parent.onRunAllText, None), ]
                sp, ep = parent.GetSelection()
                if sp != ep:
                    menus.append(('Run Selection in Shell (F8)',
                                  parent.onRunSelection, None))
                menus.append(('---', None, None))

            try:
                #                check_debugger_instance()
                line = parent.GetCurrentLine()
                if not has_breakpoint(parent.doc_name, line+1):
                    menus = menus + \
                        [('Set BreakPoint',   parent.onSetBP, None), ]
                else:
                    menus = menus + \
                        [('Clear BreakPoint', parent.onClearBP, None), ]
                if parent.is_debug_mode:
                    menus = menus + \
                        [('Hide debug setting', parent.HideDebug, None)]
                else:
                    menus = menus + \
                        [('Show debug setting', parent.ShowDebug, None)]
            except:
                pass
#                   menus = menus + [('Show debug setting', parent.ShowDebug, None)]

        def make_label(string):
            if self.parent._syntax.lower() == string.lower():
                return '^'+string
            else:
                return '*'+string
        menus.append(('---', None, None))
        menus.append(('+Syntax', None, None))
        menus.append((make_label('Python'), self.onSetPythonSyntax, None))
        menus.append((make_label('C'), self.onSetCSyntax, None))
        menus.append((make_label('Fortran'), self.onSetFortranSyntax, None))
        menus.append((make_label('F77'), self.onSetF77Syntax, None))
        menus.append((make_label('None'), self.onSetNoneSyntax, None))
        menus.append(('!', None, None))
        menus.append(('Toggle insert/overwrite', self.toggle_overtype, None))

#                menus = menus + [('--debugger di',   None, None),]
#       if parent.GetModify():
#            menus =  menus + [('---', None, None),
#                              ('Save', parent.onSave, None), ]
        if reload and parent.check_if_in_script_editor():
            menus.append(('---', None, None))
            menus = menus + [('Reload from File', parent.onReload, None)]
        ifigure.utils.cbook.BuildPopUpMenu(self, menus, eventobj=parent)

    def onSetPythonSyntax(self, evt):
        self.parent.set_syntax(syntax='python')

    def onSetF77Syntax(self, evt):
        self.parent.set_syntax(syntax='f77')

    def onSetFortranSyntax(self, evt):
        self.parent.set_syntax(syntax='fortran')

    def onSetCSyntax(self, evt):
        self.parent.set_syntax(syntax='c')

    def onSetNoneSyntax(self, evt):
        self.parent.set_syntax(syntax='none')

    def toggle_overtype(self, evt):
        value = not self.parent.GetOvertype()
        self.parent.SetOvertype(value)


class PythonSTC(stc.StyledTextCtrl):

    fold_symbols = 2

    def __init__(self, parent, ID,
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0, syntax='python'):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)
        self._syntax = syntax
        self.doc_name = ''
        self.is_debug_mode = False
        self.file_mtime = 0

        self.CmdKeyAssign(ord('['), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord(']'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)
        self.CmdKeyAssign(ord('A'), stc.STC_SCMOD_CTRL, stc.STC_CMD_HOME)
        self.CmdKeyAssign(ord('E'), stc.STC_SCMOD_CTRL, stc.STC_CMD_LINEEND)
        self.CmdKeyAssign(ord('P'), stc.STC_SCMOD_CTRL, stc.STC_CMD_LINEUP)
        self.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_LINEDOWN)
        self.CmdKeyAssign(ord('F'), stc.STC_SCMOD_CTRL, stc.STC_CMD_CHARRIGHT)
        self.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_CHARLEFT)

        self.set_syntax(syntax=syntax)

        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0, 0)

        self.SetViewWhiteSpace(False)
        # self.SetBufferedDraw(False)
        # self.SetViewEOL(True)
        # self.SetEOLMode(stc.STC_EOL_CRLF)
        # self.SetUseAntiAliasing(True)

        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(78)
        self.SetTabWidth(4)
        self.SetUseTabs(False)

        # Setup a margin to hold fold markers
        # self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?
        self._font_ss_size = check_font_width()

        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginWidth(2, 12)
        self.SetMarginSensitive(2, True)
        self.SetMarginType(1, stc.STC_MARGIN_NUMBER | stc.STC_MARGIN_SYMBOL)
        self.GetLineCount()
        self.set_margin_width1()
        self.SetMarginMask(1, 1 << DebugCurrentLine)
        self.SetMarginType(0, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(0, 10)
        self.SetMarginMask(0, 1 << DebugBreakPoint)

        if self.fold_symbols == 0:
            # Arrow pointing right for contracted folders, arrow pointing down for expanded
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
                              stc.STC_MARK_ARROWDOWN, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
                              stc.STC_MARK_ARROW, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
                              stc.STC_MARK_EMPTY, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
                              stc.STC_MARK_EMPTY, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                              stc.STC_MARK_EMPTY,     "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                              stc.STC_MARK_EMPTY,     "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
                              stc.STC_MARK_EMPTY,     "white", "black")

        elif self.fold_symbols == 1:
            # Plus for contracted folders, minus for expanded
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
                              stc.STC_MARK_MINUS, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
                              stc.STC_MARK_PLUS,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
                              stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
                              stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                              stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                              stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
                              stc.STC_MARK_EMPTY, "white", "black")

        elif self.fold_symbols == 2:
            # Like a flattened tree control using circular headers and curved joins
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
                              stc.STC_MARK_CIRCLEMINUS,          "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
                              stc.STC_MARK_CIRCLEPLUS,           "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
                              stc.STC_MARK_VLINE,                "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
                              stc.STC_MARK_LCORNERCURVE,         "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                              stc.STC_MARK_CIRCLEPLUSCONNECTED,  "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                              stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
                              stc.STC_MARK_TCORNERCURVE,         "white", "#404040")

        elif self.fold_symbols == 3:
            # Like a flattened tree control using square headers
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
                              stc.STC_MARK_BOXMINUS,          "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
                              stc.STC_MARK_BOXPLUS,           "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
                              stc.STC_MARK_VLINE,             "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
                              stc.STC_MARK_LCORNER,           "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                              stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                              stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
                              stc.STC_MARK_TCORNER,           "white", "#808080")

        self.MarkerDefine(DebugCurrentLine, stc.STC_MARK_ARROW,  "red", "red")
        self.MarkerDefine(
            DebugBreakPoint,  stc.STC_MARK_CIRCLEMINUS, "red", "white")

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        self.Bind(wx.EVT_CHAR, self.onSearch)

        # added for  dnd
        self.Bind(stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
#        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
        #self.Bind(wx.EVT_ENTER_WINDOW, self.onMouseEnter)
        #self.Bind(wx.EVT_LEAVE_WINDOW, self.onMouseLeave)

        # this suppress default pop up on linux
        if hasattr(stc, "STC_POPUP_NEVER"):
            self.UsePopUp(stc.STC_POPUP_NEVER)

        self.SetCaretForeground("BLUE")

        # register some images for use in the AutoComplete box.
        self.RegisterImage(1, images.Smiles.GetBitmap())
        self.RegisterImage(2,
                           wx.ArtProvider.GetBitmap(wx.ART_NEW, size=(16, 16)))
        self.RegisterImage(3,
                           wx.ArtProvider.GetBitmap(wx.ART_COPY, size=(16, 16)))

        self._search = 0  # search mode
        self._search_text = ''  # search text
        self._search_st = -1  # start poisition of search
        self._mark = -1
        self._ctrl_K = False

        self.ctrl_X = False
        self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)

    def _exit_search_mode(self):
        self._mark = -1
        self._search = 0
        self.set_search_text('')
        self._search_st = -1

    def onSetFocus(self, evt):
        #print("set focus")
        evt.Skip()

    def onKillFocus(self, evt):
        self._exit_search_mode()
        #print("kill focus")
        evt.Skip()

    def onMouseEnter(self, evt):
        #print("mouse enter")
        evt.Skip()

    def onMouseLeave(self, evt):
        #print("mouse leave")
        evt.Skip()

    def onLeftDown(self, e):
        #print("left down")
        self._exit_search_mode()
        e.Skip()

    def set_syntax(self, syntax='python'):
        # print 'setting to ' + syntax
        self.reset_style()
        self._syntax = syntax
        if syntax == 'python':
            self.SetLexer(stc.STC_LEX_PYTHON)
            set_python_style(self)
        elif syntax == 'c':
            self.SetLexer(stc.STC_LEX_CPP)
            set_cpp_style(self)
        elif syntax == 'fortran':
            self.SetLexer(stc.STC_LEX_FORTRAN)
            set_fortran_style(self)
        elif syntax == 'f77':
            self.SetLexer(stc.STC_LEX_F77)
            set_f77_style(self)
        elif syntax == 'c++':
            self.SetLexer(stc.STC_LEX_CPP)
            set_cpp_style(self)
        elif syntax == 'none':
            self.SetLexer(stc.STC_LEX_NULL)
        else:
            if hasattr(wx.stc, 'STC_LEX_' + syntax.upper()):
                self.SetLexer(getattr(wx.stc, 'STC_LEX_' + syntax.upper()))
            else:
                self.SetLexer(stc.STC_LEX_NULL)

    def reset_style(self):
        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                          "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default
        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                          "fore:#440000,face:%(mono)s,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
                          "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,
                          "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,
                          "fore:#000000,back:#FF0000,bold")

    def SaveFile(self, file):
        cmtime = 0 if not os.path.exists(file) else os.path.getmtime(file)

        if cmtime > self.file_mtime:
            ret = dialog.message(
                self, 'File is changed after the file was read last time.\nDo you want to overwrite?.', 'File modified by someone', style=4)
            print(ret)
            if ret != 'yes':
                ret = dialog.message(
                    self, 'De you want to reload file?.', 'File modified by someone', style=4)
                if ret == 'yes':
                    try:
                        fid = open(file)
                        txt = open(file).read()
                        fid.close()
                        mtime = os.path.getmtime(file)
                        self.SetText(txt)
                        self.file_mtime = mtime
                    except Exception:
                        logging.exception("File Open Error"+file)
                        return
                return
        super(PythonSTC, self).SaveFile(file)
        self.file_mtime = os.path.getmtime(file)

    def SetText(self, *args, **kargs):
        # print 'Adjusting margin'
        super(PythonSTC, self).SetText(*args, **kargs)
        self.set_margin_width1()

    def onSearch(self, event):
        key = event.GetKeyCode()
        if self._search == 0:
            event.Skip()
            return
        if key >= 32 and key <= 127:
            self.set_search_text(self._search_txt+chr(key))
            if self._search == 1:
                if self._search_txt != '':
                    if self.SearchNext(0, self._search_txt) == -1:
                        self.set_search_status_text(fail=True)
                    self.EnsureCaretVisible()
            if self._search == 2:
                if self._search_txt != '':
                    if self.SearchPrev(0, self._search_txt) == -1:
                        self.set_search_status_text(fail=True)
                    self.EnsureCaretVisible()

    def set_search_text(self, txt):
        self._search_txt = txt
        self.set_search_status_text()

    def set_search_status_text(self, fail=False):
        frame = self.GetTopLevelParent()
        if not hasattr(frame, 'SetStatusText'):
            # without this wx4 may crush when exiting
            return

        if self._search == 2:
            header = 'Back searching  '
        elif self._search == 1:
            header = 'Forward searching  '
        else:
            header = 'Searching  '
        if self._search_txt == '':
            if self._search == 0:
                frame.SetStatusText('')
            else:
                frame.SetStatusText(header)
        else:
            if fail:
                frame.SetStatusText(header + self._search_txt + '... fail')
            else:
                frame.SetStatusText(header + self._search_txt)

    def set_margin_width1(self):
        cw = self.GetMarginWidth(1)

        if self.GetLineCount() >= 10000:
            xxxx = 5
        elif self.GetLineCount() >= 1000:
            xxxx = 4
        elif self.GetLineCount() >= 100:
            xxxx = 3
        elif self.GetLineCount() >= 10:
            xxxx = 2
        else:
            xxxx = 1
        nw = self._font_ss_size[0]*xxxx
        if self.is_debug_mode:
            nw = nw + 15
        if nw != cw:
            self.SetMarginWidth(1, nw)

    def run_text(self, sp, ep):
        l1 = self.LineFromPosition(sp)
        l2 = self.LineFromPosition(ep)

        # if ending of selection is the begining of line. ignore the
        # last line.
        if self.PositionFromLine(l2) == ep:
            l2 = l2 - 1

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
        line_count = len(line)

        txt = minify('\n'.join(line))
        line = txt.split('\n')
        w = len(line[0])-len(line[0].lstrip())
        for l in line:
            w = min([len(l)-len(l.lstrip()), w])
        line = [l[w:] for l in line]
        txt = '\n'.join(line)

        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
        if (hasattr(app, 'run_text') and
                txt != ''):
            if line_count > 1:
                app.shell.interp.set_batch_run_mode()
            app.run_text(txt)
            app.shell.interp.set_single_run_mode()
        return

    def onCopyToShell(self, evt):
        self.Copy()
        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
        app.shell.Paste()

    def onRunAllText(self, evt):
        td = self.get_td()
        if td is None:
            sp = 0
            ep = self.GetTextLength()
            self.run_text(sp, ep)
        else:
            app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
            if hasattr(app, 'run_text'):
                #app.run_text(td.get_full_path()+'()', no_exec=True)
                app.run_text(td.get_full_path()+'()')

    def get_EOL_txt(self):
        m = self.GetEOLMode()
        if m == wx.stc.STC_EOL_CR:
            return '\r'
        elif m == wx.stc.STC_EOL_LF:
            return '\n'
        else:
            return '\r\n'

    def onRunSelection(self, evt):
        sp, ep = self.GetSelection()
        self.run_text(sp, ep)

    def OnKeyPressed(self, event):
        def SE_Cut():
            # cut for script editor
            self.GetTopLevelParent().SetStatusText('cut')
            if self.GetSelectedText() == '':
                pos2 = self.GetCurrentPos()
                self.SetSelection(self._mark, pos2)
            self.Cut()
            self._ctrl_K = False
            return

        def SE_Copy():
            # copy for script editor
            self.GetTopLevelParent().SetStatusText('copy')
            sel = self.GetSelection()
            if self.GetSelectedText() == '':
                pos2 = self.GetCurrentPos()
                self.SetSelection(self._mark, pos2)
            self.Copy()
            self.SetSelection(sel[0], sel[1])
            self._ctrl_K = False
            return

        def SE_Paste():
            # paste for script editor
            self.GetTopLevelParent().SetStatusText('paste')
            sel = self.GetSelection()
            if self.GetSelectedText() == '':
                pos2 = self.GetCurrentPos()
                self.SetSelection(self._mark, pos2)
            self.Paste()
            self.SetSelection(sel[0], sel[1])
            self._ctrl_K = False
            return

        if self.CallTipActive():
            self.CallTipCancel()
        if self.AutoCompActive():
            self.AutoCompCancel()

        key = event.GetKeyCode()
        if key == 396:  # press control
            event.Skip()
            return
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
            if not ((key == 83 and controlDown) or
                    (key == 82 and controlDown)):
                self._search = 0
                self._search_st = -1
                self.set_search_text('')

        if key == wx.WXK_F8:    # F8 (run selected text)
            self.onRunSelection(event)
            return
        elif key == wx.WXK_F9:    # F9 (run text)
            self.onRunAllText(event)
            return
            # return
        elif key == wx.WXK_SPACE and controlDown:
            self._mark = self.GetCurrentPos()
            self.GetTopLevelParent().SetStatusText('mark set')
            return
        elif key == 88 and controlDown:  # ctrl + X (cut)
            self.ctrl_X = True
            self.GetTopLevelParent().SetStatusText('ctrl X+')
            return

        if key == wx.WXK_RETURN:
            self.set_margin_width1()
        if self.ctrl_X:
            if key == 83 and controlDown:  # save (C-S)
                self.GetTopLevelParent().SetStatusText('ctrl X + ctrl S')
                self.GetTopLevelParent().onSaveFile()
                wx.MilliSleep(300)
                self.GetTopLevelParent().SetStatusText('')
            elif key == 87 and controlDown:  # write (C-W)
                self.GetTopLevelParent().SetStatusText('ctrl X + ctrl W')
                self.GetTopLevelParent().onSaveFile(saveas=True)
                wx.MilliSleep(300)
            elif key == 70 and controlDown:  # open (C-F)
                self.GetTopLevelParent().SetStatusText('ctrl X + ctrl F')
                self.GetTopLevelParent().onOpenFile()
                wx.MilliSleep(300)
            elif key == 85:  # open (C-U)
                self.GetTopLevelParent().SetStatusText('Undo!')
                self.Undo()
            self.ctrl_X = False
            return

        if key == 32:
            pass
        elif key == 68 and controlDown:  # ctrl + D (delete)
            self.CharRight()
            self.DeleteBackNotLine()
            return

        elif key == 67 and controlDown:  # ctrl + C (copy)
            SE_Copy()
            return

        elif key == 86 and controlDown:  # ctrl + V (paste)
            self.PastePlus()
            return

#           this is to perform " skip 10 lines"
#            tmp=self.GetCurrentLine()
#            c = 0
#            while tmp < self.GetLineCount() and c < 10:
#               tmp=tmp+1
#               if self.GetLineVisible(tmp): c=c+1
#            self.GotoLine(tmp)
#
#            return

        elif key == 87 and controlDown:  # ctrl + W (cut)
            SE_Cut()
            return

        elif key == 87 and event.AltDown():  # alt + W (copy)
            SE_Copy()
            return

        # ctrl + K (cut the right of caret, delete line if the line is empty)
        elif key == 75 and controlDown:
            iline = self.GetCurrentLine()
            line = self.GetLine(iline)
            line = line.rstrip("\r\n")
            if len(line) != 0:
                self.LineEndExtend()
                self.Cut()
                self._ctrl_K = True
            else:
                self.LineDelete()
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
        elif key == 89 and controlDown:  # ctrl + Y (paste)
            self.PastePlus()
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

    def PastePlus(self):
        self.Paste()
#        if self._ctrl_K:
#           self.NewLine()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1 and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.PointFromPosition(braceOpposite)
            #self.Refresh(True, wxRect(pt.x, pt.y, 5,5))
            # print pt
            # self.Refresh(False)

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def onRegionLeft(self, evt):
        sline = self.GetFirstVisibleLine()
        sp, ep = self.GetSelection()
        l1 = self.LineFromPosition(sp)
        l2 = self.LineFromPosition(ep)

        EOL = self.GetEOLMode()
        if EOL == wx.stc.STC_EOL_CR:
            s = '\r'
        elif EOL == wx.stc.STC_EOL_CRLF:
            s = '\r\n'
        else:
            s = '\n'

        lines = self.GetText().split(s)
        lindent = min([len(lines[l1+x]) - len(lines[l1+x].lstrip())
                       for x in range(l2-l1+1)])
        for x in range(l2-l1+1):
            lines[l1+x] = lines[l1+x][lindent:]
        self.SetText(s.join(lines))
        self.ScrollToLine(sline)

    def onRegionRight(self, evt):
        sline = self.GetFirstVisibleLine()
        sp, ep = self.GetSelection()
        l1 = self.LineFromPosition(sp)
        l2 = self.LineFromPosition(ep)

        EOL = self.GetEOLMode()
        if EOL == wx.stc.STC_EOL_CR:
            s = '\r'
        elif EOL == wx.stc.STC_EOL_CRLF:
            s = '\r\n'
        else:
            s = '\n'
        lines = self.GetText().split(s)
        for x in range(l2-l1+1):
            lines[l1+x] = '    '+lines[l1+x]
        self.SetText(s.join(lines))
        self.ScrollToLine(sline)

    def onCopy(self, evt):
        self.Copy()

    def onPaste(self, evt):
        self.Paste()

    def onCut(self, evt):
        self.Cut()

    def onSelectAll(self, evt):
        self.SelectAll()

    def onDeleteBack(self, evt):
        self.DeleteBack()

    def onFindText(self, evt):
        p = self.GetParent().GetParent()
        if hasattr(p, 'ToggleFindPanel'):
            p.ToggleFindPanel()

    def onSetBP(self, evt):
        l = self.GetCurrentLine()+1
        add_breakpoint(self.doc_name, l)
        self.ShowDebug()
        self.ShowBreakpointMarker()

    def onClearBP(self, evt):
        l = self.GetCurrentLine()+1
        rm_breakpoint(self.doc_name, l)
        self.ShowBreakpointMarker()

    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True
        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def onDragInit(self, e):
        self.Unbind(wx.EVT_MOTION)
        sel = self.GetSelectedText()
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
        self.DeleteBack()
        tds.DoDragDrop(True)

    def OnStartDrag(self, evt):
        sel = self.GetSelectedText()
        if isWX3:
            evt.SetDragAllowMove(False)
        evt.SetDragText(sel)
        p = self
        while p.GetParent() is not None:
            p = p.GetParent()

        p._text_clip = sel


#        e.Skip()


    def onRightDown(self, evt):
        #print("right down")
        evt.Skip()

    def onRightUp(self, evt):
        #print("right up")
        reload = False
        if self.check_if_in_script_editor():
            app = wx.GetApp().TopWindow
            sc = app.script_editor
            ipage = app.script_editor.get_ipage(self)
            if ipage != -1:
                file = sc.file_list[ipage]
                reload = self.check_fileisnewer(file)
        m = PythonSTCPopUp(self, reload=reload)
        self.PopupMenu(m,
                       (evt.GetX(), evt.GetY()))
        m.Destroy()
        # evt.Skip()

    def ShowDebugMargin(self, enter):
        if enter:
            if self.is_debug_mode:
                return
            self._org_w = self.GetMarginWidth(0)
            self.SetMarginWidth(0, self._org_w + 12)
            self.is_debug_mode = True
            self.ShowBreakpointMarker()
        else:
            if not self.is_debug_mode:
                return
            self.SetMarginWidth(0, self._org_w)
            self.MarkerDeleteAll(DebugCurrentLine)
            self.MarkerDeleteAll(DebugBreakPoint)
            self.is_debug_mode = False
        self.set_margin_width1()

    def HideDebug(self, *args):
        self.ShowDebugMargin(False)

    def ShowDebug(self, *args):
        self.ShowDebugMargin(True)

    def ShowBreakpointMarker(self):
        self.MarkerDeleteAll(DebugBreakPoint)
        if not self.is_debug_mode:
            return
        for l in get_breakpoint(self.doc_name):
            self.MarkerAdd(l-1, DebugBreakPoint)

    def check_if_in_script_editor(self):
        app = wx.GetApp().TopWindow
        return app.script_editor.get_ipage(self) >= 0

    def get_td(self):
        app = wx.GetApp().TopWindow
        sc = app.script_editor
        ipage = app.script_editor.get_ipage(self)
        if ipage == -1:
            return

        file = sc.file_list[ipage]
        try:
            fullpath = file.td
            app = wx.GetApp().TopWindow
            td = app.proj.find_by_full_path(fullpath)
            return td
        except:
            return

    def onReload(self, evt):
        self.reload()

    def reload(self):
        app = wx.GetApp().TopWindow
        sc = app.script_editor
        ipage = app.script_editor.get_ipage(self)
        if ipage == -1:
            return

        sline = self.GetFirstVisibleLine()
        file = sc.file_list[ipage]

        fid = open(file)
        txt = fid.read()
        fid.close()
        mtime = os.path.getmtime(file)
        self.SetText(txt)
        self.file_mtime = mtime
        self.SetSavePoint()
        self.ScrollToLine(sline)

    def check_fileisnewer(self, file):
        cmtime = 0 if not os.path.exists(file) else os.path.getmtime(file)
        return cmtime > self.file_mtime

    def onWrapText(self, evt):
        import textwrap

        sline = self.GetFirstVisibleLine()
        sp, ep = self.GetSelection()
        l1 = self.LineFromPosition(sp)
        l2 = self.LineFromPosition(ep)

        EOL = self.GetEOLMode()
        if EOL == wx.stc.STC_EOL_CR:
            s = '\r'
        elif EOL == wx.stc.STC_EOL_CRLF:
            s = '\r\n'
        else:
            s = '\n'

        lines = self.GetText().split(s)

        # this case process all lines
        if l1 == 0 and l2 == 0:
            l1 = 0
            l2 = len(lines)-1

        for x in range(l1, l2+1):
            lines[x] = s.join(textwrap.wrap(lines[x], width=60))

        self.SetText(s.join(lines))

        self.ScrollToLine(sline)

        evt.Skip()

    def onAutopep8(self, evt):
        import autopep8

        sline = self.GetFirstVisibleLine()

        txt = self.GetText()

        txt = autopep8.fix_code(txt)

        self.SetText(txt)

        self.ScrollToLine(sline)

        evt.Skip()

#    def turn_on_debugger(self):
#        app = wx.GetApp().TopWindow.script_editor.d_panel.CheckDebuggerInstance()
# ----------------------------------------------------------------------


class TextDropTarget(wx.TextDropTarget):
    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj

    def OnDropText(self, x, y, indata):
        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
#        app=self.obj.GetTopLevelParent()
        txt = app._text_clip
        app._text_clip = ''
        #self.obj.DoDropText(x, y, txt)
        pos = self.obj.PositionFromPoint(wx.Point(x, y))
        self.obj.InsertText(pos, txt)

        if isWX3:
            wx.CallAfter(self.obj.SetSTCFocus, True)
            wx.FutureCall(100, self.obj.SetFocus)
        return True
        # return super(TextDropTarget, self).OnDropText(x, y, indata)

    def OnDragOver(self, x, y, default):
        self.obj.DoDragOver(x, y, default)
        return super(TextDropTarget, self).OnDragOver(x, y, default)


class Notebook(aui.AuiNotebook):
    '''
    extend notebook so that each page knows its title.
    A user can pass documnet name (normally file full path)
    to SetPageText, AddPage.
    '''

    def AddPage(self, p, txt, doc_name='', **kargs):
        p.doc_name = doc_name
        txt = '{:>3s}'.format(txt)
        aui.AuiNotebook.AddPage(self, p, txt, **kargs)

    def SetPageText(self, ipage, txt,  doc_name=''):
        self.GetPage(ipage).doc_name = doc_name
        txt = '{:>3s}'.format(txt)
        aui.AuiNotebook.SetPageText(self, ipage, txt)

    def GetPageText(self, idx, *args, **kargs):
        return str(aui.AuiNotebook.GetPageText(self, idx, *args, **kargs)).strip()

    def get_doc_name(self, ipage):
        p = self.GetPage(ipage)
        return p.doc_name

    def set_doc_name(self, ipage, name):
        p = self.GetPage(ipage)
        p.doc_name = name

    def SetPageTextModifiedMark(self, ipage, value):
        txt = self.GetPageText(ipage)
        doc_name = self.get_doc_name(ipage)
        if value and not txt.startswith('*'):
            self.SetPageText(ipage, '*'+txt, doc_name=doc_name)
        if not value and txt.startswith('*'):
            self.SetPageText(ipage, txt[1:], doc_name=doc_name)


class ScriptEditor(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.NO_BORDER)
        logging.basicConfig(level=logging.DEBUG)

        self.sp = wx.SplitterWindow(self, wx.ID_ANY,
                                    style=wx.SP_NOBORDER | wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        from ifigure.widgets.find_panel import PanelWithFindPanel
        self.nb_panel = PanelWithFindPanel(self.sp)
        self.nb = Notebook(self.nb_panel,
                           style=(aui.AUI_NB_DEFAULT_STYLE |
                                  aui.AUI_NB_CLOSE_ON_ACTIVE_TAB |
                                  aui.AUI_NB_WINDOWLIST_BUTTON),)

        self.nb_panel.GetSizer().Add(self.nb, 1, wx.ALL | wx.EXPAND)

        self._last_update = -1
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.sp, 1, wx.EXPAND)

        from ifigure.widgets.debugger import DebuggerPanel
        self.d_panel = DebuggerPanel(self.sp, wx.ID_ANY)
        self._d_shown = False
        self._first_open_style = None
        self._d_requests = []
        self.SetSizer(sizer)
        self.file_list = []
        self.page_list = []

        self.ic = 0
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onClose)

        self.Bind(EVT_AUINOTEBOOK_TAB_RIGHT_UP, self.onTabRightUp)

        self.ShowDebugPanel()
        self.HideDebugPanel()
        self.Fit()
#        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onPageChanged)

    def get_filelist(self):
        return self.file_list

    def get_ipage(self, p):
        if p in self.page_list:
            return self.page_list.index(p)
        return -1

    def NewFile(self):
        p = PythonSTC(self.nb, -1)
        p.SetDropTarget(TextDropTarget(p))
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)
        if self.ic == 0:
            txt = ''
        else:
            txt = str(self.ic)
        self.ic = self.ic+1

        file = 'untitled'+txt
        self.nb.AddPage(p, os.path.basename(file), doc_name=file)
        ipage = self.nb.GetPageIndex(p)
        self.nb.SetPageToolTip(ipage, file)
        self.file_list.append('.'+file+'~')
        self.page_list.append(p)
        self.Show()
        # app=self.GetTopLevelParent()
        # app._force_layout()
        if self._first_open_style is not None:
            if self._first_open_style:
                app = wx.GetApp().TopWindow
                app.onDetachEditor(None)
            self._first_open_style = None

    def OpenFile(self, file=None, readonly=False):

        if file is None:
            open_dlg = wx.FileDialog(None, message="Select file to open",
                                     style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            if open_dlg.ShowModal() != wx.ID_OK:
                open_dlg.Destroy()
                return
            file = open_dlg.GetPath()
            open_dlg.Destroy()

        # first try to open file
        if self.file_list.count(file) != 0:
            # file is already open
            idx = self.file_list.index(file)
            try:
                ipage = self.nb.GetPageIndex(self.page_list[idx])
                self.nb.SetSelection(ipage)
                return
            except Exception:
                # if page is already deleted
                del self.file_list[idx]
                del self.page_list[idx]
        try:
            fid = open(file)
            txt = fid.read()
            fid.close()
            mtime = os.path.getmtime(file)
        except Exception:
            logging.exception("File Open Error"+file)
            return
        p = PythonSTC(self.nb, -1)
        p.SetDropTarget(TextDropTarget(p))
        try:
            p.SetText(txt)
            p.file_mtime = mtime
            p.SetReadOnly(readonly)
        except UnicodeDecodeError:
            logging.exception("Opening File Failed. Ignoring invalid bytes")
            p.SetText(unicode(txt, errors='ignore'))
            pass
        p.EmptyUndoBuffer()
        p.Colourise(0, -1)

        # line numbers in the margin
#        p.SetMarginType(1, stc.STC_MARGIN_NUMBER)
#        p.SetMarginWidth(1, 25)
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.onModified, p)

        if readonly:
            doc_name = file+'(ro)'
        else:
            doc_name = file
        tag = os.path.basename(doc_name)
        self.nb.AddPage(p, tag, doc_name=doc_name, select=True)
        ipage = self.nb.GetPageIndex(p)
        self.nb.SetPageToolTip(ipage, file)
        wx.CallAfter(self.nb.SetSelection, ipage)
        self.file_list.append(file)
        self.page_list.append(p)

        if self._first_open_style is not None:
            if self._first_open_style:
                app = wx.GetApp().TopWindow
                app.onDetachEditor(None)
            self._first_open_style = None

#        self.Show()
#        self.Refresh()
#        app=self.GetTopLevelParent()
#        app.deffered_force_layout()

    def SaveAll(self):
        for ipage in range(len(self.page_list)):
            self.SaveFile(ipage=ipage)

    def SaveFile(self, saveas=False, ipage=None):
        if ipage is None:
            ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        if not p in self.page_list:
            self.onModified(None)
            return
        idx = self.page_list.index(p)
        save_file = False
        if saveas:
            open_dlg = wx.FileDialog(None,
                                     message="Select file to save",
                                     style=wx.FD_SAVE)
            if open_dlg.ShowModal() == wx.ID_OK:
                file = open_dlg.GetPath()
                save_file = True
                open_dlg.Destroy()
            else:
                open_dlg.Destroy()
                return

        if p.GetModify() and not save_file:
            if (self.file_list[idx].startswith('.') and
                    self.file_list[idx].endswith('~')):
                # untitled case....
                open_dlg = wx.FileDialog(None,
                                         message="Select file to save",
                                         style=wx.FD_SAVE)
                if open_dlg.ShowModal() == wx.ID_OK:
                    file = open_dlg.GetPath()
                    save_file = True
                open_dlg.Destroy()
            else:
                # already saved file...
                file = self.file_list[idx]
                if os.path.exists(file):
                    save_file = True
                else:
                    dlg = wx.MessageDialog(None,
                                           file + ' does not exist anymore',
                                           'File does not exist',
                                           wx.OK)
                    ret = dlg.ShowModal()

        if save_file:
            #            print("saving to ....", file)
            if wx.Platform == '__WXMSW__':
                p.ConvertEOLs(wx.stc.STC_EOL_CRLF)
            else:
                p.ConvertEOLs(wx.stc.STC_EOL_LF)
            p.SaveFile(file)
            self.nb.SetPageText(ipage, os.path.basename(file),
                                doc_name=file)
            self.nb.SetPageToolTip(ipage, file)
            self.file_list[idx] = file
            p.SetSavePoint()
        self.onModified(None)

    def close_all_pages(self):
        self.file_list = []
        self.page_list = []
        while self.nb.GetPageCount() > 0:
            self.nb.RemovePage(self.nb.GetPageCount()-1)
        self.nb.DeleteAllPages()

    def check_if_need_save(self, p):
        if p.GetModify():
            idx = self.page_list.index(p)
            if (self.file_list[idx].startswith('.') and
                    self.file_list[idx].endswith('~')):
                return False, True
            else:
                return True, True
        return False, False

    def close_page(self, ipage):
        p = self.nb.GetPage(ipage)
        if not p in self.page_list:
            # somehow page is already closed...?
            return

        idx = self.page_list.index(p)

        if p.GetModify():
            dlg = wx.MessageDialog(None,
                                   'Do you want to save?',
                                   'Buffer modified',
                                   wx.YES_NO | wx.CANCEL)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret == wx.ID_YES:
                self.SaveFile()
            if ret == wx.ID_NO:
                pass
            if ret == wx.ID_CANCEL:
                return

        delfile = self.file_list[idx]
        del self.page_list[idx]
        del self.file_list[idx]

        wx.CallAfter(self.call_remove_page, ipage, self.nb.GetPageCount())
        self.nb.DeletePage(ipage)

        app = wx.GetApp().TopWindow
        if app.proj is None:
            return
        ifigure.events.SendCloseFileEvent(app.proj,
                                          w=e.GetEventObject(),
                                          file=delfile)

    def onTabRightUp(self, e):
        ipage = self.nb.GetSelection()
        file = self.file_list[ipage]
        fullpath = ''

        try:
            fullpath = file.td
        except:
            return
        if fullpath != '':
            app = wx.GetApp().TopWindow
            td = app.proj.find_by_full_path(fullpath)
            app.proj_tree_viewer.set_td_selection(td)

    def onClose(self, e):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        if not p in self.page_list:
            # somehow page is already closed...?
            return
        idx = self.page_list.index(p)

        if p.GetModify():
            dlg = wx.MessageDialog(None,
                                   'Do you want to save?',
                                   'Buffer modified',
                                   wx.YES_NO | wx.CANCEL)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret == wx.ID_YES:
                self.SaveFile()
            if ret == wx.ID_NO:
                pass
            if ret == wx.ID_CANCEL:
                e.Veto()
                return
        delfile = self.file_list[idx]
        del self.page_list[idx]
        del self.file_list[idx]

        # make sure to remove a page on linux...
        wx.CallAfter(self.call_remove_page, ipage, self.nb.GetPageCount())
        app = wx.GetApp().TopWindow
        e.Skip()
        if app.proj is None:
            return
        ifigure.events.SendCloseFileEvent(app.proj,
                                          w=e.GetEventObject(),
                                          file=delfile)

    def call_remove_page(self, ipage, cpage):
        if (self.nb.GetPageCount() == cpage):
            self.nb.RemovePage(ipage)

    def switch_wdir(self, owdir, nwdir):
        #        print owdir, nwdir
        #        print self.file_list
        new_list = []
        for item in self.file_list:
            if len(item) < len(owdir):
                new_list.append(item)
                continue
            if item[:len(owdir)] != owdir:
                new_list.append(item)
                continue
            else:
                new_list.append(nwdir + item[len(owdir):])
        self.file_list = new_list

    def onModified(self, e=None):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        self.nb.SetPageTextModifiedMark(ipage, p.GetModify())

    def onTD_FileChanged(self, evt):
        param = evt.param
        # print param["oldname"]
        # print self.file_list
        if param["oldname"] in self.file_list:
            idx = self.file_list.index(param["oldname"])
            self.file_list[idx] = param["newname"]
            ipage = self.nb.GetPageIndex(self.page_list[idx])
            print(os.path.basename(param["newname"]))
            self.nb.SetPageText(ipage, os.path.basename(param["newname"]),
                                doc_name=param["newname"])
            self.nb.SetPageToolTip(ipage, param["newname"])

    def onFileSystemChanged(self, evt=None):
        if evt.time < self._last_update:
            return
#        print 'onFileSystemchanged', evt
        do_reload = evt.reload
#        print evt.GetTreeDict()
        # self.Freeze()
        file_list = self.file_list[:]
        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
#        app=self.GetTopLevelParent()
        do_layout = False
        for file in file_list:
            #           if file.find(evt.owndir) == -1:
            #               continue
            #           I can not do this because tree may be renamed...
            #           print os.path.exists(file)
            if not os.path.exists(file):
                idx = self.file_list.index(file)
                ipage = self.nb.GetPageIndex(self.page_list[idx])
                self.nb.DeletePage(ipage)
                del self.page_list[idx]
                del self.file_list[idx]
                if len(self.file_list) == 0:
                    # self.Hide()
                    do_layout = True

                ifigure.events.SendCloseFileEvent(app.proj,
                                                  w=self,
                                                  file=file)
            else:
                try:
                    fid = open(file)
                    txt = fid.read()
                    fid.close()
                except Exception:
                    logging.exception("File Open Error"+file)
                    continue
                if not do_reload:
                    continue
                idx = self.file_list.index(file)
                ipage = self.nb.GetPageIndex(self.page_list[idx])
                self.nb.GetPage(ipage).SetText(txt)
                self.nb.GetPage(ipage).SetSavePoint()
        # self.Thaw()

        if do_layout:
            app._force_layout()
        self._last_update = time.time()

    def get_current_file(self):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        return p.doc_name

    #
    #  debugger extention
    #
    def GoDebugMode(self, file, enter=True):
        if not file in self.file_list:
            self.OpenFile(file=file)
#        app=self.GetTopLevelParent()
        app = wx.GetApp().TopWindow  # self.GetTopLevelParent()
        idx = self.file_list.index(file)
        ipage = self.nb.GetPageIndex(self.page_list[idx])
        p = self.nb.GetPage(ipage)
        if enter:
            p.ShowDebug()
            self.nb.SetSelection(ipage)
            for ipage in range(self.nb.GetPageCount()):
                self.SaveFile(saveas=False, ipage=ipage)
                p = self.nb.GetPage(ipage)
                p.SetReadOnly(True)
#            print app.gui_tree.get_toggle(self)
#            if not app.gui_tree.get_toggle(self):
#                print 'requst'
            if self.GetTopLevelParent() == app:
                wx.CallAfter(app.gui_tree.toggle_panel, self,  True)
        else:
            p.HideDebug()
            for ipage in range(self.nb.GetPageCount()):
                p = self.nb.GetPage(ipage)
                if not p.doc_name.endswith('(ro)'):
                    p.SetReadOnly(False)

    def GoDebugModePresent(self, file, enter=True):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        self.GoDebugMode(p, enter)

    def ShowDebugPanel(self):
        if not self._d_shown:
            self.d_panel.txt.clear_window()
            self.sp.SplitHorizontally(self.nb_panel, self.d_panel)
#            self.nb.Layout()
#            self.d_panel.layout()
#            self.GetSizer().Add(self.d_panel, 1, wx.EXPAND)
            self.d_panel.Show()
            self._d_shown = True
        self.Layout()

    def HideDebugPanel(self):
        if self._d_shown:
            self.sp.Unsplit()
            self.nb.Layout()
#           self.GetSizer().Detach(self.d_panel)
#           self.d_panel.Hide()
            self._d_shown = False
        self.Layout()

    def CheckDebuggerStatus(self):
        return self.d_panel.status == 'stop'

    def QueueSEDRequest(self, *args):
        self._d_requests.append(args)
        wx.CallLater(1000, self.RunSEDRequest)

    def RunSEDRequest(self, *args):
        #        import threading
        #        print 'RunSEDRequest', threading.current_thread().name
        if len(self._d_requests) == 0:
            return
        if self.d_panel.status == 'stop':
            args = self._d_requests.pop(0)
            self.RunSED(*args)
            if len(self._d_requests) != 0:
                wx.CallLater(1000, self.RunSEDRequest)
        else:
            wx.CallLater(1000, self.RunSEDRequest)

    def RunSED(self, co, lc1, lc2, file):
        #        self.d_panel.CheckDebuggerInstance()
        if self.d_panel.status == 'stop':
            def call_back(obj=self, f=file):
                for ipage in range(self.nb.GetPageCount()):
                    self.nb.GetPage(ipage).HideDebug()
                obj.GoDebugMode(f, enter=False)
                obj.HideDebugPanel()

            self.GoDebugMode(file, enter=True)
            self.ShowDebugPanel()
            self.d_panel.Run(co, lc1, lc2, file, call_back)
        else:
            ret = dialog.message(self, 'Debugger is running.',
                                 'Please wait', 0)

            return

    def ShowDebugCurrentLine(self, file, line):
        if not file in self.file_list:
            return
        idx = self.file_list.index(file)
        ipage = self.nb.GetPageIndex(self.page_list[idx])
        p = self.nb.GetPage(ipage)
        p.MarkerDeleteAll(DebugCurrentLine)
        p.ShowBreakpointMarker()
        #p.MarkerDelete(line-1, DebugBreakPoint)
        p.MarkerAdd(line-1, DebugCurrentLine)
        p.GotoLine(line-1)


class ScriptEditorFrame(FrameWithWindowList):
    def __init__(self, *args, **kargs):
        kargs["style"] = (wx.CAPTION |
                          wx.CLOSE_BOX |
                          wx.MINIMIZE_BOX |
                          wx.MAXIMIZE_BOX |
                          wx.RESIZE_BORDER)
        # |wx.FRAME_FLOAT_ON_PARENT)

        ###
        super(ScriptEditorFrame, self).__init__(*args, **kargs)
        self.filemenu = wx.Menu()
        self.editmenu = wx.Menu()
        self.viewmenu = wx.Menu()
        self.menuBar.Append(self.filemenu, "&File")
        self.menuBar.Append(self.editmenu, "&Edit")
        self.menuBar.Append(self.viewmenu, "&View")

        newmenu = wx.Menu()
        menu_Append(self.filemenu, wx.ID_ANY, 'New', newmenu)
        self.add_menu(newmenu, wx.ID_ANY,
                      "Script", "Create new script in Project",
                      self.onNewScript)
        self.add_menu(newmenu, wx.ID_ANY,
                      "Text", "Create new text in Project",
                      self.onNewText)
        self.add_menu(newmenu, wx.ID_ANY,
                      "non-project Text", "Create new untitled text (file is not stored in project)",
                      self.onNewDoc)
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Open...",
                      "open current window",
                      self.onOpenDoc)
        self.filemenu.AppendSeparator()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Close Document",
                      "close current window",
                      self.onCloseDoc)
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Save",
                      "save current window",
                      self.onSaveDoc)
        self.filemenu.AppendSeparator()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Close Editor",
                      "close editor window",
                      self.onClose)
        self.filemenu.AppendSeparator()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Quit piScope", " Terminate the program",
                      self.onQuit)
        self.add_undoredo_menu(self.editmenu)
        self.editmenu.AppendSeparator()
        self.add_cutpaste_menu(self.editmenu)
        self._attach_menu = self.add_menu(self.viewmenu, wx.ID_ANY,
                                          "Attach to MainWindow",
                                          "close the editor window and open it in the main app window",
                                          self.onAttachEditor)
        self.add_std_viewmenu(self.viewmenu)
        self.append_help_menu()

        self._se = None
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.set_accelerator_table()

        self.sb = StatusBarSimple(self)
        self.SetStatusBar(self.sb)

        self.SetSize((400, 300))
        self.SetTitle('Editor')
        self.Layout()
        self.Bind(wx.EVT_UPDATE_UI, self.onUpdateUI)
        self.Bind(wx.EVT_CLOSE, self.onWindowClose)
        self.Show()

    def onUpdateUI(self, evt):
        if evt.GetId() == wx.ID_COPY:
            evt.Enable(True)
        elif evt.GetId() == wx.ID_PASTE:
            evt.Enable(True)
        evt.Skip()

    def get_script_editor(self):
        return self._se

    def set_script_editor(self, se):
        se.Reparent(self)
        self.GetSizer().Add(se, 1, wx.EXPAND)
        self._se = se
        self.Layout()

    def add_cutpaste_menu(self,  m):
        self.add_menu(m, wx.ID_ANY, "Cut", "",  self.onCut)
        self.copy_mi = self.add_menu(m, wx.ID_COPY, "Copy", "",
                                     self.onCopy)
        self.paste_mi = self.add_menu(m, wx.ID_PASTE, "Paste", "",
                                      self.onPaste)
        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('C'), wx.ID_COPY))
        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('V'), wx.ID_PASTE))

    def add_std_viewmenu(self, helpmenu):
        ## helpmenu = viewmenu
        helpmenu.AppendSeparator()
        self.add_menu(helpmenu, wx.ID_FORWARD,
                      "Next window (F1)", "Bring next window forward",
                      self.onNextWindow)
        self.add_menu(helpmenu, wx.ID_BACKWARD,
                      "Previous window (F2)",
                      "Bring previous window forward",
                      self.onPrevWindow)
        helpmenu.AppendSeparator()
        self.add_menu(helpmenu, ID_HIDEAPP,
                      "Hide App",
                      "Show/Hide App",
                      self.onToggleHideApp)
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))

    def add_undoredo_menu(self, editmenu):
        undo_mi = self.add_menu(editmenu, wx.ID_UNDO,
                                "Undo", "Undo previous edit",
                                self.onUndo)
        redo_mi = self.add_menu(editmenu, wx.ID_REDO,
                                "Redo", "Redo an edit ",
                                self.onRedo)
        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('Z'), wx.ID_UNDO))
        self.append_accelerator_table((wx.ACCEL_CTRL | wx.ACCEL_SHIFT,
                                       ord('Z'), wx.ID_REDO))

    def attach_editor_to_main(self, open_editor=True):
        if self._se is None:
            return
        self.GetSizer().Detach(self._se)
        self._se = None
        app = wx.GetApp().TopWindow
        app.attach_editor(open_editor)

    def onUndo(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        p = self._se.nb.GetPage(ipage)
        p.Undo()

    def onRedo(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        p = self._se.nb.GetPage(ipage)
        p.Redo()

    def onCut(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        p = self._se.nb.GetPage(ipage)
        p.onCut(e)

    def onCopy(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        p = self._se.nb.GetPage(ipage)
        p.onCopy(e)

    def onPaste(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        p = self._se.nb.GetPage(ipage)
        p.onPaste(e)

    def onAttachEditor(self, e):
        self.attach_editor_to_main(open_editor=True)
        self.Close()

    def onClose(self, e):
        self.Close()

    def onWindowClose(self, e):
        print('script editor closing')
        self.attach_editor_to_main(open_editor=False)
        e.Skip()

    def onNewScript(self, e):
        app = wx.GetApp().TopWindow
        obj = app.proj.onAddNewScript(parent=self)
        app.proj_tree_viewer.update_widget()

    def onNewText(self, e):
        app = wx.GetApp().TopWindow
        obj = app.proj.onAddNewText()
        app.proj_tree_viewer.update_widget()

    def onNewDoc(self, e):
        if self._se is None:
            return
        self._se.NewFile()

    def onOpenDoc(self, e):
        if self._se is None:
            return
        self._se.OpenFile()

    def onCloseDoc(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        self._se.close_page(ipage)

    def onSaveDoc(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        self._se.SaveFile(saveas=False, ipage=ipage)

    def onSaveFile(self, e=None, saveas=False):
        self._se.SaveFile(saveas=False)

    def onSaveAsDoc(self, e):
        if self._se is None:
            return
        ipage = self._se.nb.GetSelection()
        self._se.SaveFile(saveas=True, ipage=ipage)

    def onQuit(self, evt=None):
        wx.GetApp().TopWindow.Close()
