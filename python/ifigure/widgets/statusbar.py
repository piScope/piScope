
import os
import time
import ifigure
import threading
import sys
import wx
import weakref
import numpy as np
from wx.lib.statbmp import GenStaticBitmap
import ifigure
import ifigure.utils.cbook as cbook
try:
    import resource
    has_resource_module = True
except ImportError:
    has_resource_module = False

# num_field=2


def memory_usage():
    if has_resource_module:
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == 'darwin':
            return mem/1024  # maxos
        else:
            return mem/1024  # linux
    else:
        if sys.platform == 'win32':
            from ifigure.utils.get_memory_usage_win import get_memory_usage
            return get_memory_usage()/1024/1024


# ---------------------------------------------------------------------------
class StatusBarPopup(wx.Menu):
    def __init__(self, parent):
        self.parent = parent

        super(StatusBarPopup, self).__init__()
        m = [["Use e", self.onFormatE, None],
             ["Use f", self.onFormatF, None],
             ("+Digits", None, None),
             ["*2", self.on2, None],
             ["*4", self.on4, None],
             ["*6", self.on6, None],
             ["*8", self.on8, None],
             ("!", None, None),
             ["Copy Text", self.onCopyText, None]]
        # print(ifigure._cursor_config["format"][3])
        if ifigure._cursor_config["format"][-2] == 'e':
            m[0][0] = '^Use e'
        else:
            m[1][0] = '^Use f'
        if ifigure._cursor_config["format"][3] == '2':
            m[3][0] = '^2'
        elif ifigure._cursor_config["format"][3] == '4':
            m[4][0] = '^4'
        elif ifigure._cursor_config["format"][3] == '6':
            m[5][0] = '^6'
        elif ifigure._cursor_config["format"][3] == '8':
            m[6][0] = '^8'
        cbook.BuildPopUpMenu(self, m)

    def onFormatE(self, evt):
        txt = ifigure._cursor_config["format"]
        ifigure._cursor_config["format"] = txt[:-2]+'e}'
        self.parent.refresh_cursor_string()

    def onFormatF(self, evt):
        txt = ifigure._cursor_config["format"]
        ifigure._cursor_config["format"] = txt[:-2]+'f}'
        self.parent.refresh_cursor_string()

    def on2(self, evt):
        txt = ifigure._cursor_config["format"]
        ef = txt[-2]
        ifigure._cursor_config["format"] = '{:.2'+ef+'}'
        self.parent.refresh_cursor_string()

    def on4(self, evt):
        txt = ifigure._cursor_config["format"]
        ef = txt[-2]
        ifigure._cursor_config["format"] = '{:.4'+ef+'}'
        self.parent.refresh_cursor_string()

    def on6(self, evt):
        txt = ifigure._cursor_config["format"]
        ef = txt[-2]
        ifigure._cursor_config["format"] = '{:.6'+ef+'}'
        self.parent.refresh_cursor_string()

    def on8(self, evt):
        txt = ifigure._cursor_config["format"]
        ef = txt[-2]
        ifigure._cursor_config["format"] = '{:.8'+ef+'}'
        self.parent.refresh_cursor_string()

    def onCopyText(self, evt):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(
                wx.TextDataObject(self.parent.GetStatusText()))
            wx.TheClipboard.Close()


class StatusBarWithXY(wx.StatusBar):
    def __init__(self, parent, id, *args, **kargs):
        self.mem = 0
#        self.disk = 0
        self.nproc = 0
        wx.StatusBar.__init__(self, parent, id, *args, **kargs)

        self.sizeChanged = False
        self.Bind(wx.EVT_SIZE, self.OnSize)
#        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self._owner_bk = None
        self.Fit()

    def set_xy_string(self, x, y):
        f = ifigure._cursor_config["format"]
        txt = ('x: '+f.format(np.float64(x)) +
               ' y: '+f.format(np.float64(y)))
        self.SetStatusText(txt, 0)

    def show_cursor_string(self, owner):
        f = ifigure._cursor_config["format"]
        data = owner._cursor_data
        s = []
        col = ['(r) ', '(b) ']
        for k, d in enumerate(data):
            if len(d) == 3:
                s.append('x:'+col[k]+f.format(np.float64(d[0])) +
                         ' y:'+col[k]+f.format(np.float64(d[1])) +
                         ' z:'+col[k]+f.format(np.float64(d[2])))
            if len(d) == 2:
                s.append('x:'+col[k]+f.format(np.float64(d[0])) +
                         ' y:'+col[k]+f.format(np.float64(d[1])))
        try:
            dx = f.format(data[1][0]-data[0][0])
            dy = f.format(data[1][1]-data[0][1])
            txt_delta = 'dx: ' + dx + ' dy: '+dy
            s.append(txt_delta)
        except:
            pass
        self.SetStatusText(', '.join(s), 0)
        self._owner_bk = weakref.ref(owner)

    def refresh_cursor_string(self):
        if self._owner_bk is None:
            return
        if self._owner_bk() is None:
            return
        self.show_cursor_string(self._owner_bk())
        self.Refresh()

    def OnRightUp(self, evt):
        if self.GetTopLevelParent().book is None:
            return
        self.popup = StatusBarPopup(self)
        self.PopupMenu(self.popup,
                       [evt.GetX(), evt.GetY()])
        self.popup.Destroy()

    def OnToggleProp(self, event):
        top = self.GetTopLevelParent()
        top.toggle_property()

    def OnSize(self, evt):
        self.Reposition()  # for normal size events
#        self.sizeChanged = True

        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.

        wx.CallAfter(self.Reposition)
#    def OnIdle(self, evt):
#        if self.sizeChanged:
#            self.Reposition()

    def Reposition(self, evt):
        pass


class StatusBar(StatusBarWithXY):
    def __init__(self, parent):
        num_icon, icons, handler = self._get_params()
        self.mem = 0
        self.icon = []
        self.nproc = 0

        super(StatusBar, self).__init__(parent, -1)

        # This status bar has three fields
        self.SetFieldsCount(num_icon+2)
        # Sets the three fields to be relative widths to each other.
        self.SetStatusWidths([-1]+[20]*num_icon+[140])

        # Field 0 ... just text
        self.SetStatusText("welcome...", 0)

        # This will fall into field 1 (the second field)
        self.icon = [None]*num_icon
        from ifigure.ifigure_config import icondir
        for i in range(num_icon):
            path = os.path.join(icondir, '16x16', icons[i])
            self.icon[i] = GenStaticBitmap(self, wx.ID_ANY,
                                           bitmap=wx.Bitmap(path))
            self.icon[i].Bind(wx.EVT_LEFT_DOWN, handler[i])
#            hint does not work for staticbitmap??
#            self.icon[i].SetToolTip(wx.ToolTip(icons[i][:-4]))

        # set the initial position of the checkbox
        self.Reposition()

        # timer for what...?

        self.timer = wx.PyTimer(self.notify)
        self.timer.Start(2000)
        self.notify()

    def _get_params(self):
        num_icon = 2
        icons = ('log.png', 'help.png')  # form.png
        handler = (self.OnToggleLog, self.OnToggleTip)  # self.OnToggleProp
        return num_icon, icons, handler

    # Handles events from the timer we started in __init__().
    # We're using it to drive a 'clock' in field 2 (the third field).
    def notify(self):
        if self:
            mem = memory_usage()
            if sys.platform == 'darwin':
                self.mem = mem/1024  # maxos
            else:
                self.mem = mem/1024  # linux
            self.nproc = threading.activeCount()
            self.SetStatusText(self.make_txt(), len(self.icon)+1)
        else:
            self.timer.Stop()

    def make_txt(self):
        return (str(self.nproc) + ' proc / ' +
                str(self.mem) + ' MB ')
#                str(self.disk) + ' MB')

    # the log
    def OnToggleLog(self, event):
        top = self.GetTopLevelParent()
        logw = top.logw
        if logw.IsShown():
            logw.Hide()
        else:
            logw.Show()
            logw.Raise()

    def OnToggleTip(self, event):
        top = self.GetTopLevelParent()
        tipw = top.tipw
        if tipw.IsShown():
            tipw.Hide()
        else:
            tipw.Show()
            tipw.Raise()

#    def OnSize(self, evt):
#        self.Reposition()  # for normal size events
#        self.sizeChanged = True
#    def OnIdle(self, evt):
#        if self.sizeChanged:
#            self.Reposition()

    # reposition the checkbox

    def Reposition(self):
        for i in range(len(self.icon)):
            rect = self.GetFieldRect(1+i)
            self.icon[i].SetPosition((rect.x, (rect.height-16)//2+1+rect.y))
  #      self.txt.SetPosition((rect.x, rect.y))
        self.sizeChanged = False


class StatusBarSimple(StatusBarWithXY):
    def notify(self):
        pass

    def __init__(self, parent):
        super(StatusBarSimple, self).__init__(parent, -1)

        # This status bar has three fields
        self.SetFieldsCount(1)
        # Sets the three fields to be relative widths to each other.
        self.SetStatusWidths([-1])

        # Field 0 ... just text
        self.SetStatusText("welcome...", 0)

    def Reposition(self):
        self.sizeChanged = False
