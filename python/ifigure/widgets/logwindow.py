import wx
import sys
import time
import wx.aui as aui
import ifigure
import ifigure.events


class Logwindow(wx.MiniFrame):
    def __init__(self, *args, **kargs):
        self.threadlist = []
        # this is added not to have windows "always on parent"
        #        args2 = [x for x in args]
        #        args2[0] = None
        #        args = tuple(args2)
        ###
        wx.MiniFrame.__init__(self, *args,
                              style=wx.CAPTION |
                              wx.CLOSE_BOX |
                              wx.MINIMIZE_BOX |
                              wx.RESIZE_BORDER |
                              wx.FRAME_FLOAT_ON_PARENT)
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        vbox.Add(panel, 1, wx.EXPAND | wx.ALL, 5)

        self.nb = aui.AuiNotebook(panel)

        bpanel = wx.Panel(panel)
        button2 = wx.Button(bpanel, wx.ID_ANY, "Close Finished Thread Tab")
        button = wx.Button(bpanel, wx.ID_ANY, "Close")

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        panel.SetSizer(vbox)
        vbox.Add(self.nb, 1, wx.EXPAND)
        vbox.Add(bpanel, 0, wx.EXPAND | wx.ALL, 5)

        hbox.AddStretchSpacer()
        hbox.Add(button2, 0, wx.EXPAND | wx.ALL, 2)
        hbox.Add(button, 0, wx.EXPAND | wx.ALL, 2)
        bpanel.SetSizer(hbox)

        #sys.stdout = RedirectOutput(self.log)
        #sys.stderr = RedirectOutput(self.log)

        button.Bind(wx.EVT_BUTTON, self.onPanelClose)
        button2.Bind(wx.EVT_BUTTON, self.onCloseFinished)
        self.Bind(wx.EVT_CLOSE, self.onWindowClose)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE,
                  self.onPageClose)

        self.Layout()
        self.Centre()
        self.Hide()

        self.redirector = None
        #self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.check_thread)
        self.Bind(wx.EVT_ACTIVATE, self.onActivate)

    def set_redirector(self, redir):
        self.redirector = redir

    def watch_thread(self, evt):
        #        print 'watch thread', evt.thread
        # ev = ThreadStart event
        td = evt.GetTreeDict()
        log = wx.TextCtrl(self.nb, -1,
                          style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.nb.AddPage(log, evt.thread.name)
        self.redirector.add(evt.thread, log.AppendText)
        self.threadlist.append([evt.thread, td, log, 0])

        wx.CallLater(1000, self.check_thread)

        st = time.localtime(time.time())
        strt = time.strftime(" %b %d, %Y  %I:%M:%S", st)
        log.AppendText('thread registered at '+strt+'\n')

    def start_thread(self):
        c = 0
        for t, td, log, status in self.threadlist:
            if t.is_alive():
                c = c+1
        if c > self.GetParent().aconfig.setting['max_thread']:
            return

        i = 0
        for t, td, log, status in self.threadlist:
            if status == 0:
                t.start()
                # this is when we want to run the process in the main thread temtativcely...
                #t.run()
                st = time.localtime(time.time())
                strt = time.strftime(" %b %d, %Y  %I:%M:%S", st)
                log.AppendText('thread started at '+strt+'\n')
                self.threadlist[i][3] = 1
                break
            i = i+1

    def check_thread(self, evt=None):
        #        print 'check thread'
        restart = False
        deadlist = []
        waiting = False
        num_run = 0
        for t, td, log, status in self.threadlist:
            if t.is_alive() or status == 0:
                if status == 0:
                    waiting = True
                else:
                    num_run = num_run + 1
                restart = True
            else:
                td._status = ''
                ifigure.events.SendChangedEvent(td)
                st = time.localtime(time.time())
                strt = time.strftime(" %b %d, %Y  %I:%M:%S", st)
                log.AppendText('done....('+strt+')\n')
                self.redirector.rm(t)
                deadlist.append(t)

        for t in deadlist:
            self.threadlist = [x for x
                               in self.threadlist if x[0] != t]
        if restart:
            #print('restarting log window timer')
            wx.CallLater(1000, self.check_thread)
            #self.timer.Start(1000, oneShot=True)

        if waiting:
            if (num_run <
                    self.GetParent().aconfig.setting['max_thread']):
                self.start_thread()

    def check_thread_can_start(self, t):
        return True

    def onCloseFinished(self, e=None):
        ipage = self.nb.GetSelection()
        n = self.nb.GetPageCount()
        l = [True]*n
        for ipage in reversed(range(n)):
            p = self.nb.GetPage(ipage)

            keep = False
            for x in self.threadlist:
                if x[2] == p:
                    keep = True
            if not keep:

                self.nb.RemovePage(ipage)
                p.Destroy()

        return

    def onActivate(self, e):
        if e.GetActive():
            self.SetTransparent(255)
        else:
            self.SetTransparent(120)

    def onPanelClose(self, e=None):
        self.Hide()

    def onWindowClose(self, e=None):
        self.Hide()
        e.Veto()

    def call_remove_page(self, ipage, cpage):
        if (self.nb.GetPageCount() == cpage):
            self.nb.RemovePage(ipage)

    def onPageClose(self, e=None):
        ipage = self.nb.GetSelection()
        p = self.nb.GetPage(ipage)
        wx.CallAfter(self.call_remove_page, ipage, self.nb.GetPageCount())
        i = 0
        for x in self.threadlist:
            if x[2] == p:
                self.redirector.rm(x[0])
        self.threadlist = [x for x
                           in self.threadlist if x[2] != p]
