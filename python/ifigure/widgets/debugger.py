from __future__ import print_function
from ifigure.widgets.simple_shell import ShellBase
import wx
import os
import wx.py.shell  # (wx4 removed this) wx.lib.shell
from wx.py.interpreter import Interpreter as IP

from ifigure.utils.wx3to4 import panel_SetToolTip
_wait = False
_test_shell = True


def exit_wait():
    globals()['_wait'] = False


def set_wait():
    globals()['_wait'] = True


def is_waiting():
    return _wait


panel = None


def check_debugger_instance():
    if panel is None:
        raise ValueError("debugger is not yet instanciated")
    else:
        panel.CheckDebuggerInstance()


class DebuggerInterpreter(IP):

    def __init__(self, *args, **kargs):
        IP.__init__(self, *args, **kargs)
        self._g_dict = {}
        self._l_dict = {}

    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        try:
            exec(code, self._l_dict, self._g_dict)
        except SystemExit:
            raise
        except:
            self.showtraceback()
        else:
            from code import softspace
            import sys
            if softspace(sys.stdout, 0):
                print()


class DebugShell(ShellBase):
    def __init__(self, parent, id):
        self.lvar = {}
        super(DebugShell, self).__init__(
            parent, id, InterpClass=DebuggerInterpreter)
        self.clear_window()

    def clear_window(self):
        self.clear()
        self.prompt()

    def setBuiltinKeywords(self):
        '''
        in order not to overwrite quit/exit command
        '''
        pass

    def push(self, command, silent=False):
        frame = self.GetParent().frame

        if frame is not None:
            self.interp._g_dict = frame.f_globals
            self.interp._l_dict = frame.f_locals
            super(DebugShell, self).push(command, silent=silent)


class DebuggerPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kargs):
        wx.Panel.__init__(self, parent, id,
                          style=wx.FRAME_FLOAT_ON_PARENT | wx.CLOSE_BOX)

        self.frame = None
        self._status = 'stop'
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        msizer = wx.BoxSizer(wx.HORIZONTAL)
#       msizer = wx.BoxSizer(wx.HORIZONTAL)
#       msizer2 = wx.BoxSizer(wx.VERTICAL)
#       msizer2.Add(msizer, 1, wx.EXPAND)
        self.GetSizer().Add(msizer, 0, wx.EXPAND)
        d_labels = ['s', 'n', 'r', 'c', 'q']
        d_tips = ['step', 'next', 'return', 'continue',  'quit']
        d_buttons = [wx.Button(self, wx.ID_ANY, size=(40, 20)) for
                     button in d_labels]

        for b, l, t in zip(d_buttons, d_labels, d_tips):
            b.SetLabel(" "+l+" ")
            panel_SetToolTip(b, t)
            msizer.Add(b, 0, wx.ALL, 1)

            def call_debug_button(evt, obj=self, label=l):
                obj.onDebugButton(evt, label)
            self.Bind(wx.EVT_BUTTON, call_debug_button, b)

        from ifigure.utils.edit_list import TextCtrlCopyPasteGeneric

        if _test_shell:
            self.txt = DebugShell(self, wx.ID_ANY)
        else:
            self.txt = TextCtrlCopyPasteGeneric(self, wx.ID_ANY, '',
                                                style=wx.TE_PROCESS_ENTER)
        #self.Bind(wx.EVT_TEXT_ENTER, self.onTextEnter, self.txt)

        msizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.GetSizer().Add(msizer2, 1, wx.ALL | wx.EXPAND, 0)
        msizer2.Add(self.txt, 1, wx.ALL | wx.EXPAND, 0)
        self.st = wx.StaticText(self, wx.ID_ANY, ' '*50)
        self.st.Wrap(300)
        msizer.Add(self.st, 1, wx.ALL | wx.EXPAND, 1)

        self.d_buttons = d_buttons
        self.d = None
        self.Layout()
        self.Hide()
        self.Fit()
        globals()['panel'] = self
#       bdb.set_trace()

#   def Show(self):
#       for b in self.d_buttons:
#           b.Show()
#       wx.Panel.Show(self)

#   def Hide(self):
#       for b in self.d_buttons:
#           b.Hide()
#       wx.Panel.Hide(self)

    def onTextEnter(self, evt):
        if is_waiting():
            txt = str(self.txt.GetValue())
            if txt != '':
                try:
                    #                   print(eval(txt, self.frame.f_globals,
                    #                                 self.frame.f_locals))
                    exec(compile(txt, 'text', 'exec'), self.frame.f_globals, self.frame.f_locals)
                except:
                    print('evaluation failed')

    def onDebugButton(self, evt, l):
        if l == 's':  # step
            self.d.set_step()
            exit_wait()
        elif l == 'n':
            self.d.set_next(self.frame)
            exit_wait()
        elif l == 'c':
            self.d.set_continue()
            exit_wait()
        elif l == 'r':
            self.d.set_return(self.frame)
            exit_wait()
        elif l == 'p':
            from ifigure.widgets.dialog import textentry
            txt = str(self.txt.GetValue())
            if txt != '':
                try:
                    print(eval(txt, self.frame.f_globals,
                               self.frame.f_locals))
                except:
                    print('evaluation failed')
        elif l == 'q':
            self.StopDebugger()

    def StopDebugger(self):
        self.d.set_quit()
        exit_wait()
        self._status = 'stop'
        print('exiting debug mode')
        self.exit_debug_mode()

#   def CheckDebuggerInstance(self):
#       if self.d is None:
#           from ifigure.widgets.debugger_core import get_debugger
#           self.d = get_debugger(self)

    def Run(self, script_co, l1, l2, file, call_back):
        #       script_file = script.path2fullpath()
        #       file = self.d.canonic(script_file)
        #       print self.d
        if self.d is not None:
            return

        from ifigure.widgets.debugger_core import get_debugger
        self.d = get_debugger(self)
        self._status = 'running'
        self._file = file
        self._call_back = call_back
        self._call_count = 0
        self.target_code = None
        self.d.run(script_co, l1, l2)
        if self._status != 'stop':
            self.StopDebugger()

    def setStatus(self, mode, frame, *args):
        if self.target_code is None:
            self.target_code = frame.f_code
            self.target_frame = frame
        self.mode = mode
        self.args = args
        self.frame = frame

    def handle_user_line(self, frame):
        self.setStatus('line', frame)
#       if self.target_code.co_filename != frame.f_code.co_filename: return
        wx.GetApp().TopWindow.open_editor_panel()
        editor = self.GetParent().GetParent()
        if editor.get_current_file() != frame.f_code.co_filename:
            editor.GoDebugMode(frame.f_code.co_filename, enter=True)
        editor.ShowDebugCurrentLine(frame.f_code.co_filename,
                                    frame.f_lineno)

        self.st.SetLabel(os.path.basename(frame.f_code.co_filename) +
                         ', line#:' + str(frame.f_lineno))

        self.Layout()
        set_wait()
        while is_waiting():
            wx.Yield()

    def handle_user_return(self, frame, return_value):
        print(('return', frame, return_value, self._call_count))
        if self._call_count > 0:
            self._call_count = self._call_count - 1
        else:
            self._status = 'stop'
            print(('exiting debug mode : return value = ', return_value))
            self.exit_debug_mode()

    def handle_user_call(self, frame, return_value):
        self._call_count = self._call_count + 1

    def handle_user_exception(self, frame, exc_info):
        self._status = 'stop'
        print(('exiting debug mode : exception info = ', exc_info))
        self.exit_debug_mode()

    def exit_debug_mode(self):
        self._call_back()
        self.d = None

    @property
    def status(self):
        return self._status
