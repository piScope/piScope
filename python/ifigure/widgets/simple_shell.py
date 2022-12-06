from __future__ import print_function
from six.moves.queue import Queue, Empty
import wx.py.shell  # (wx4 removed this) wx.lib.shell
from threading import Timer, Thread
import time
from ifigure.utils.wx3to4 import isWX3
from os.path import expanduser, abspath
import wx
import ifigure
import os
import sys
import ifigure.utils.pickle_wrapper as pickle
import ifigure.server
import numpy as np

import ifigure.utils.debug as debug
from ifigure.mto.treedict import TreeDict
from ifigure.utils.cbook import text_repr
# shell_variable
EvtShellEnter = wx.NewEventType()
EVT_SHELL_ENTER = wx.PyEventBinder(EvtShellEnter, 1)

try:
    from ifigure.version import ifig_version
except:
    ifig_version = 'dev'

dprint1, dprint2, dprint3 = debug.init_dprints('SimpleShell')


ON_POSIX = 'posix' in sys.builtin_module_names

sx_print_to_consol = False


def enqueue_output(p, queue):
    while True:
        line = p.stdout.readline()
        queue.put(line)
        if p.poll() is not None:
            queue.put(p.stdout.read())
            break
    queue.put('process terminated')


def run_in_thread(p):
    q = Queue()
    t = Thread(target=enqueue_output, args=(p, q))
    t.daemon = True  # thread dies with the program
    t.start()

    lines = ["\n"]
    line = ''
    alive = True
    app = wx.GetApp().TopWindow
    if sx_print_to_consol:
        write_cmd = app.proj_tree_viewer.consol.log.AppendText
    else:
        write_cmd = app.shell.WriteTextAndPrompt
    while True:
        time.sleep(0.01)
        try:
            line = q.get_nowait()  # or q.get(timeout=.1)
        except Empty:
            if len(lines) != 0:
                wx.CallAfter(write_cmd, ''.join(lines))
            lines = []
        except:
            import traceback
            traceback.print_exc()
            break
        else:  # got line
            lines.append(line)
        if line.startswith('process terminated'):
            if len(lines) > 1:
                wx.CallAfter(write_cmd, ''.join(lines[:-1]))
            break
    return


def sx(strin=''):
    if strin == '':
        return
    if strin.startswith('cd '):
        dest = strin[3:]
        dest = abspath(expanduser(dest))
        os.chdir(dest)
        txt = os.getcwd()
    else:
        import subprocess as sp

        p = sp.Popen(strin, shell=True, stdout=sp.PIPE,
                     stderr=sp.STDOUT, universal_newlines=True)
        t = Thread(target=run_in_thread, args=(p,))
        t.daemon = True  # thread dies with the program
        t.start()
        # run_in_thread(p)
        #txt = ''.join(p.stdout.readlines())


class ShellBase(wx.py.shell.Shell):
    def Paste(self):

        if sys.platform == 'darwin':
            import wx
            data = wx.TextDataObject()
            if wx.TheClipboard.Open():
                wx.TheClipboard.GetData(data)
                txt = data.GetText()
                wx.TheClipboard.Close()
            else:
                txt = ''
            self.write(txt)
        else:
            return super(ShellBase, self).Paste()

    def OnKeyDown(self, evt):

        if evt.GetKeyCode() == wx.WXK_UP:
            self.OnHistoryReplace(1)
            return
        if evt.GetKeyCode() == wx.WXK_DOWN:
            self.OnHistoryReplace(-1)
            return

        if hasattr(evt, 'RawControlDown'):
            mod = (evt.RawControlDown() +
                   evt.AltDown()*2 +
                   evt.ShiftDown()*4 +
                   evt.MetaDown()*8)
        else:
            mod = (evt.ControlDown() +
                   evt.AltDown()*2 +
                   evt.ShiftDown()*4 +
                   evt.MetaDown()*8)

        if evt.GetKeyCode() == 78 and mod == 1:  # control + N (next command)
            #          self.OnHistoryReplace(-1)
            self.LineDown()
            return
        if evt.GetKeyCode() == 80 and mod == 1:  # ctrl + P (prev command)
            #          self.OnHistoryReplace(1)
            self.LineUp()
            return
        if evt.GetKeyCode() == 68 and mod == 1:  # ctrl + D (delete)
            self.CharRight()
            self.DeleteBackNotLine()
            self.st_flag = True
            return
        if evt.GetKeyCode() == 70 and mod == 1:  # ctrl + F (forward)
            self.CharRight()
            return
        if evt.GetKeyCode() == 66 and mod == 1:  # ctrol + B (back)
            self.CharLeft()
            return
        if evt.GetKeyCode() == 89 and mod == 1:  # ctrl + Y (paste)
            self.Paste()
            self.st_flag = True
            return
        if evt.GetKeyCode() == 87 and mod == 1:  # ctrl + W (cut)
            self.Cut()
            self.st_flag = True
            return
        if evt.GetKeyCode() == 87 and mod == 2:  # alt + W (copy)
            self.Copy()
            self.st_flag = True
            return
        if evt.GetKeyCode() == 90 and mod == 1:  # ctrl + Z (cut)
            self.st_flag = True
            import ifigure.events
            ifigure.events.SendUndoEvent(self.lvar["proj"], w=self)
            return
        if evt.GetKeyCode() == 69 and mod == 1:  # ctrl + E (end of line)
            self.LineEnd()
            return
        if evt.GetKeyCode() == 75 and mod == 1:  # ctrl + K (cut the rest)
            self.LineEndExtend()
            self.Cut()
            self.st_flag = True
            return
        if evt.GetKeyCode() == 65 and mod == 1:  # ctrl + A (beginning)
            self.Home()
            self.CharRight()
            self.CharRight()
            self.CharRight()
            self.CharRight()
            return

        if evt.GetKeyCode() == wx.WXK_RETURN:
            self.st_flag = True

        if (evt.ControlDown() == False and
            evt.AltDown() == False and
            evt.MetaDown() == False and
            evt.GetKeyCode() > 31 and
                evt.GetKeyCode() < 127):
            self.st_flag = True
#       print 'setting search text', self.st, self.historyIndex
        super(ShellBase, self).OnKeyDown(evt)


class simple_shell_droptarget(wx.TextDropTarget):
    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj

    def OnDropText(self, x, y, indata):
        app = self.obj.GetTopLevelParent()
        txt = app._text_clip
        app._text_clip = ''
#        print txt, x, y
        txt.strip('\n\r')
        txt = '\n... '.join(txt.split('\n'))

        pos = self.obj.PositionFromPoint(wx.Point(x, y))
        self.obj.GotoPos(pos)
        self.obj.write(txt)
        self.obj.GotoPos(pos+len(txt))
        if isWX3:
            wx.CallAfter(self.obj.SetSTCFocus, True)
            wx.CallLater(100, self.obj.SetFocus)
        return True
        # return super(simple_shell_droptarget, self).OnDropText(x, y, indata)

    def OnDragOver(self, x, y, default):
        self.obj.DoDragOver(x, y, default)
        return super(simple_shell_droptarget, self).OnDragOver(x, y, default)


class FakeSimpleShell(wx.Panel):
    def __init__(self, parent=None, *args, **kargs):
        super(FakeSimpleShell, self).__init__(parent, *args, **kargs)
        self.ch = None  # command history panel

#       self.chistory=collections.deque(maxlen=100)
        self.lvar = {}
        self._no_record = False

    def set_command_history(self, panel):
        self.ch = panel

    def set_proj(self, proj):
        self.lvar["proj"] = proj

    def set_tipw(self, w):
        self.tipw = w

    def write_history(self):
        # save last 300 command history
        from ifigure.ifigure_config import rcdir
        file = os.path.join(rcdir, "command_history")
        f = open(file, 'wb')
        f.close()

from wx.py.interpreter import Interpreter
class MyInterp(Interpreter):
    '''
    runsource is modified to perfrom the runsource with either symbol='exec' or 'single'

    'single' is an orignal mode
    'exec' is used to run multiple statement at once. this is useful when we run
     segment of script written in scripteditor
    '''
    def __init__(self, *args, **kwargs):
        Interpreter.__init__(self, *args, **kwargs)
        self._runsouce_mode = 'single'

    def set_single_run_mode(self):
        self._runsouce_mode = 'single'

    def set_batch_run_mode(self):
        self._runsouce_mode = 'exec'

    def runsource(self, source):
        """Compile and run source code in the interpreter."""
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr = \
                   self.stdin, self.stdout, self.stderr

        # we do this using "exec"
        more = super(Interpreter, self).runsource(source, symbol=self._runsouce_mode)

        # this was original
        #more = InteractiveInterpreter.runsource(self, source)

        # If sys.std* is still what we set it to, then restore it.
        # But, if the executed source changed sys.std*, assume it was
        # meant to be changed and leave it. Power to the people.
        if sys.stdin == self.stdin:
            sys.stdin = stdin
        else:
            self.stdin = sys.stdin
        if sys.stdout == self.stdout:
            sys.stdout = stdout
        else:
            self.stdout = sys.stdout
        if sys.stderr == self.stderr:
            sys.stderr = stderr
        else:
            self.stderr = sys.stderr
        return more

class SimpleShell(ShellBase):
    #   arrow key up/down are trapped to work as history
    #   this might be possible by configuration file!?
    #
    SHELL = None

    def __init__(self, parent=None):
        self.ch = None  # command history panel

#       self.chistory=collections.deque(maxlen=100)
        self.lvar = {}
        self._no_record = False

        sc = os.path.join(os.path.dirname(ifigure.__file__), 'startup.py')
        txt = '    --- Welcome to piScope ('+ifig_version+')---'
        super(SimpleShell, self).__init__(parent,
                                          locals=self.lvar,
                                          startupScript=sc,
                                          introText=txt,
                                          InterpClass=MyInterp)

        if os.getenv('PYTHONSTARTUP') is not None:
            file = os.getenv('PYTHONSTARTUP')
            if os.path.exists(file):
                dprint1('running startup file', file)
                txt = 'Running user startup file '+file
                self.push('print %r' % txt)
                #self.execfile(file, globals(), self.lvar)
                self.execStartupScript(file)

        self.SetDropTarget(simple_shell_droptarget(self))

        from ifigure.ifigure_config import rcdir
        file = os.path.join(rcdir, "command_history")
        try:
            f = open(file, 'rb')
            self.history = pickle.load(f)
            f.close()
        except Exception:
            import traceback
            traceback.print_exc()
            print("Can not load command history file")

        if self.history[-1] != '#end of history':
            self.history.append('#end of history')

        SimpleShell.SHELL = self
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)
        self.st = ''  # search txt
        self.st_flag = False

        self._auto_complete = True

    def onSetFocus(self, evt):
        evt.Skip()

    def onKillFocus(self, evt):
        evt.Skip()

    def setBuiltinKeywords(self):
        '''
        this overwrite the origial setBuiltinKeywords
        '''
        from six.moves import builtins
        builtins.exit = builtins.quit = \
            self.quit
        builtins.forceexit = builtins.forcequit = \
            self.forcequit

        builtins.sx = sx

    def set_command_history(self, panel):
        self.ch = panel

    def quit(self):
        '''
        exit piscope
        '''
        self.GetTopLevelParent().onQuit()

    def forcequit(self):
        '''
        Terminate piScope (kill command is called)
        '''
        import os
        pid = os.getpid()
        os.system('kill '+str(pid))

    def set_proj(self, proj):
        self.lvar["proj"] = proj

    def write_history(self):
        # save last 300 command history
        from ifigure.ifigure_config import rcdir
        file = os.path.join(rcdir, "command_history")
        f = open(file, 'wb')
        h = self.history[0:1000]
        h.append(self.history[-1])
        pickle.dump(h, f)
        f.flush()
        f.close()

    def autoCompleteShow(self, command, offset=0):
        #
        #   add treeobject method to menu
        #   only does autocomplete when caret is at the end of line
        #
        if self._auto_complete:
            if (self.GetCurrentPos() !=
                    self.GetLineEndPosition(self.GetCurrentLine())):
                return
            """Display auto-completion popup list."""
            self.AutoCompSetAutoHide(self.autoCompleteAutoHide)
            self.AutoCompSetIgnoreCase(self.autoCompleteCaseInsensitive)
            list = self.interp.getAutoCompleteList(command,
                                                   includeMagic=self.autoCompleteIncludeMagic,
                                                   includeSingle=self.autoCompleteIncludeSingle,
                                                   includeDouble=self.autoCompleteIncludeDouble)
            try:
                self.lvar['_tmp_'] = None
                txt = 'if isinstance(command, TreeDict): _tmp_=' + \
                    command+'get_children()'
                code = compile(txt, '<string>', 'exec')
                exec(code, globals(), self.lvar)
            except:
                pass

            if self.lvar['_tmp_'] is not None:
                list = list + [x[0] for x in self.lvar['_tmp_']]
                list.sort(lambda x, y: cmp(x.upper(), y.upper()))
            if list:
                options = ' '.join(list)
                #offset = 0
#                 self.AutoCompSetMaxWidth(3)
                self.AutoCompShow(offset, options)

#            super(SimpleShell, self).autoCompleteShow(command, offset=offset)

    def autoCallTipShow(self, command, insertcalltip=True, forceCallTip=False):
        #        super(SimpleShell, self).autoCallTipShow(*args, **kargs)
        #        return
        (name, argspec, tip) = self.interp.getCallTip(command)
        self._no_record = False
        self.tipw.update(name, argspec, tip)
        if not self.autoCallTip and not forceCallTip:
            return
        if not self._auto_complete:
            return
        startpos = self.GetCurrentPos()
        if argspec and insertcalltip and self.callTipInsert:
            self.write(argspec + ')')
            endpos = self.GetCurrentPos()
            self.SetSelection(startpos, endpos)
        return

        name = str(command).split('(')[-2]
        s = ''
        for c in name:
            if not c.isalnum() and c != '.' and c != '_':
                s = c
        if s != '':
            name = name.split(s)[-1]

        self._no_record = True
        self.lvar['_tmp_'] = None
        txt = '_tmp_='+name
        try:
            code = compile(txt, '<string>', 'exec')
            exec(code, globals(), self.lvar)
        except:
            #           dprint1(txt)
            pass
#        try:
#           self.push(txt, True)
#        except:
#           pass
        self._no_record = False
        if '_tmp_' in self.lvar:
            self.tipw.update(self.lvar['_tmp_'])

    def set_tipw(self, w):
        self.tipw = w

    def OnHistoryInsert(self, step):
        #       print "history insert", step
        super(SimpleShell, self).OnHistoryInsert(step)

    def OnHistoryReplace(self, step):
        # print "history replace", step
        if self.st_flag:
            txt, pos = self.GetCurLine()
            self.st = self.getCommand(txt)
            self.st_flag = False
#       print self.st, self.historyIndex
        if self.st != '':
            tmp_idx = self.historyIndex
            rep = 0
            fail_flag = False
            while (-2 < tmp_idx < len(self.history)):
                rep = rep + step
                tmp_idx = tmp_idx + step
                try:
                    st = self.history[tmp_idx]
                    if st[0:len(self.st)] == self.st:
                        break
                except:
                    fail_flag = True
            if not fail_flag:
                super(SimpleShell, self).OnHistoryReplace(rep)
            return
#          while (-2 < self.historyIndex < len(self.history)):
#             super(SimpleShell, self).OnHistoryReplace(step)
#             if self.historyIndex == -1: break
#             if self.historyIndex == len(self.history)-1: break
#             try:
#                 st = self.history[self.historyIndex]
#             except:
#                 print len(self.history), self.historyIndex
#                 import traceback
#                 traceback.print_exc()
#                 break
#             if st[0:len(self.st)] == self.st:
#                 break
        else:
            super(SimpleShell, self).OnHistoryReplace(step)

    def list_func(self):
        llist = self.list_locals()
        for objname, t in llist:
            if t == 'function':
                print(objname)

    def get_shellvar(self, name):
        return self.lvar[name]

    def set_shellvar(self, name, value):
        self.lvar[name] = value

    def del_shellvar(self, name):
        del self.lvar[name]

    def has_shellvar(self, name):
        return name in self.lvar

    def list_locals(self):
        import types

        llist = []
        # tlist = {getattr(types, name):
        #         str(getattr(types, name)).split("'")[1]
        #         for name in dir(types) if not name.startswith('_')}

        for key in self.lvar:
            if not key.startswith('_'):
                val = self.lvar[key]
                t0 = type(val).__name__
                text = text_repr(val)
                try:
                    hasshape = hasattr(val, 'shape')
                except:
                    import traceback
                    traceback.print_exc()
                    hasshape = False

                if hasshape:
                    llist.append((key, t0, text, str(val.shape)))
                else:
                    llist.append((key, t0, text, ''))

                #                for t, name in tlist:
                #                    if t0 == t:
                #                       llist.append((key, name,))
                #                       break
        return llist

    def list_module(self):
        pass

    def execute_text(self, text):
        self.Execute(text)
        return

    def execute_and_hide_main(self, text):
        self.Execute(text)
        self.Execute('import wx;wx.GetApp().TopWindow.goto_no_mainwindow()')

    def onLeftDown(self, e):
        self.Bind(wx.EVT_MOTION, self.onDragInit)
        e.Skip()

    def onLeftUp(self, e):
        self.Unbind(wx.EVT_MOTION)
        e.Skip()

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
        tds.DoDragDrop(True)

    def SendShellEnterEvent(self):
        evt = wx.PyCommandEvent(EvtShellEnter)
        handler = self.GetEventHandler()
        wx.PostEvent(handler, evt)

    def addHistory(self, *args, **kargs):
        #        print  args, kargs
        if args[0].startswith('sx'):
            args = list(args)
            try:
                args[0] = '!'+args[0].split('"')[1]
            except IndexError:
                return
            args = tuple(args)
        if self._no_record:
            return
        wx.py.shell.Shell.addHistory(self, *args, **kargs)
#        print wx.GetApp().IsMainLoopRunning()
        if wx.GetApp().IsMainLoopRunning():
            self.SendShellEnterEvent()
        if self.ch is not None:
            try:
                self.ch.append_text(args[0])
            except UnicodeError:
                print("unicode error")
                pass

    def toggle_overtype(self, evt):
        value = not self.GetOvertype()
        self.SetOvertype(value)

    def GetContextMenu(self):
        menu = super(SimpleShell, self).GetContextMenu()
        menu.AppendSeparator()
        if self.tipw.IsShown():
            f1 = menu.Append(wx.ID_ANY, "Hide Help")
            self.Bind(wx.EVT_MENU, self.onHideHelp, f1)
        else:
            f1 = menu.Append(wx.ID_ANY, "Show Help")
            self.Bind(wx.EVT_MENU, self.onShowHelp, f1)

        if self.GetOvertype():
            f1 = menu.Append(wx.ID_ANY, "Insert Mode")
            self.Bind(wx.EVT_MENU, self.toggle_overtype, f1)
        else:
            f1 = menu.Append(wx.ID_ANY, "Overwrite Mode")
            self.Bind(wx.EVT_MENU, self.toggle_overtype, f1)

        if self._auto_complete:
            f2 = menu.Append(wx.ID_ANY, "Auto Complete Off")
            self.Bind(wx.EVT_MENU, self.onAutoCompOff, f2)
        else:
            f2 = menu.Append(wx.ID_ANY, "Auto Complete On")
            self.Bind(wx.EVT_MENU, self.onAutoCompOn, f2)

        return menu

    def onShowHelp(self, evt):
        self.tipw.Show()

    def onHideHelp(self, evt):
        self.tipw.Hide()

    def onAutoCompOn(self, evt):
        self._auto_complete = True

    def onAutoCompOff(self, evt):
        self._auto_complete = False

    def WriteTextAndPrompt(self, txt):
        self.WriteText(txt)
        self.prompt()
