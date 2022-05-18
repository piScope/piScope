import wx
import sys
import weakref
import threading
import traceback
import wx.aui as aui


class RedirectOutput(object):
    def __init__(self, stdout, stderr):

        self.stdout = stdout
        self.stderr = stderr
        self.redirect_list = []
        # store normal stdout/stderr
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

    def turn_on(self):
        if self.sys_stdout != self.stdout:
            sys.stdout = self
            sys.stderr = self

    def turn_force_on(self):
        sys.stdout = self
        sys.stderr = self

    def turn_off(self):
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr

    def write(self, string):
        try:
            self.do_write(string)
        except:
            self.turn_off()
            traceback.print_exc()
            self.turn_on()

    def _safe_write(self, string):
        if hasattr(self.stdout, 'write'):
            self.stdout.write(string)
        else:
            self.sys_stdout.write(string)

    def do_write(self, string):
        t = threading.current_thread()
        for x in self.redirect_list:
            if x[0] == t:
                   ##Do not put a print statement here!!##
                wx.CallAfter(x[1], string)
                if t.name == 'MainThread':
                    try:
                        self._safe_write(string)
                    except IOError:  # may fail to write to stdout on macapplet
                        raise
                return
                # if string != "\n":
                #wx.MessageBox(string, "Error!")
        if t.name == 'MainThread':
            try:
                self._safe_write(string)
            except IOError:  # may fail to write to stdout on macapplet
                raise
        else:
            if string == '\n':
                wx.CallAfter(self._safe_write, string)
            else:
                wx.CallAfter(self._safe_write, 'Thread ('+t.name + '):'+string)

    def add(self, t, method):
        self.redirect_list.append((t, method))

    def rm(self, t):
        self.redirect_list = [x for x
                              in self.redirect_list if x[0] != t]

    def flush(self):
        if hasattr(self.stdout, 'flush'):
            self.stdout.flush()
