import wx, sys, weakref, threading
import wx.aui as aui

class RedirectOutput(object): 
    def __init__(self, stdout, stderr):

        self.stdout = stdout
        self.stderr = stderr
        self.redirect_list=[]
        ### store normal stdout/stderr
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

    def turn_on(self): 
        if self.sys_stdout != self.stdout:
            sys.stdout = self
            sys.stderr = self
     
    def turn_off(self):
        sys.stdout  = self.sys_stdout
        sys.stderr = self.sys_stderr

    def write(self, string): 
        t = threading.current_thread()
        for x in self.redirect_list:
            if x[0] == t:
                   ##Do not put a print statement here!!## 
                wx.CallAfter(x[1], string) 
                if t.name == 'MainThread':
                    try:
                        self.stdout.write(string)
                    except IOError: ### may fail to write to stdout on macapplet
                        pass
                return
                   #if string != "\n": 
                        #wx.MessageBox(string, "Error!") 
        if t.name == 'MainThread':
            try:
               self.stdout.write(string)
            except IOError: ### may fail to write to stdout on macapplet
               pass
        else:
            if string == '\n':
                wx.CallAfter(self.stdout.write, string)
            else:
                wx.CallAfter(self.stdout.write, 'Thread ('+t.name+ '):'+string)

    def add(self, t, method):
        self.redirect_list.append((t, method))
  
    def rm(self, t):
        self.redirect_list = [x for x 
            in self.redirect_list if x[0] != t]
    def flush(self):
        if hasattr(self.stdout, 'flush'):
             self.stdout.flush()
