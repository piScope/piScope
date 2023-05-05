from __future__ import print_function
#
#         figure_viewer (book viewer)
#         subset of ifigure_app.
#
#
#
#
#
#               09 02-03 thread monitor
#                  04    edge drag in section editor
#
# *******************************************
#     Copyright(c) 2012- S.Shiraiwa
# *******************************************
__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.2"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

from ifigure.utils.wx3to4 import (wxEmptyImage,
                                  menu_Append,
                                  menu_AppendSubMenu,
                                  image_SetAlpha,
                                  wxBitmapFromImage)
import wx
import sys
import os
import time
import webbrowser
import weakref
import platform
import ifigure.utils.pickle_wrapper as pickle
import wx.aui as aui
import ifigure
import ifigure.events
import ifigure.utils.cbook as cbook

from ifigure.widgets.canvas.ifigure_canvas import ifigure_canvas
from ifigure.widgets.property_editor import property_editor
from ifigure.widgets.panel_checkbox import PanelCheckbox
from ifigure.widgets.statusbar import StatusBar, StatusBarSimple
import ifigure.widgets.dialog as dialog
from ifigure.widgets.undo_redo_history import GlobalHistory, UndoRedoHistory, UndoRedoFigobjMethod

from ifigure.mto.fig_book import FigBook
from ifigure.mto.fig_page import FigPage
from ifigure.mto.fig_axes import FigAxes

from ifigure.widgets.book_viewer_interactive import BookViewerInteractive

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('BookViewer')

ID_KEEPDATA = wx.NewIdRef(count=1)
ID_HIDEAPP = wx.NewIdRef(count=1)
ID_WINDOWS = wx.NewIdRef(count=1)
ID_HDF_EXPORT = wx.NewIdRef(count=1)

if platform.system() == 'Darwin':
    def internal_idl(obj):
        if wx.UpdateUIEvent.CanUpdate(obj) and obj._menu_open:
            obj.UpdateWindowUI(wx.UPDATE_UI_FROMIDLE)
else:
    def internal_idl(obj):
        if wx.UpdateUIEvent.CanUpdate(obj):
            obj.UpdateWindowUI(wx.UPDATE_UI_FROMIDLE)


class FrameWithWindowList(wx.Frame):
    def __init__(self, *args, **kargs):
        self._atable = []
        if not 'style' in kargs:
            kargs['style'] = wx.DEFAULT_FRAME_STYLE
        kargs['style'] = kargs['style'] | wx.WS_EX_PROCESS_UI_UPDATES

        # initial size setting to avoid gtk_window_resize assersion
        kargs['size'] = (50, 50)

        super(FrameWithWindowList, self).__init__(*args, **kargs)

        self.menuBar = wx.MenuBar()
        self.ID_WINDOWS = -1

        parent = args[0]

        tw = wx.GetApp().TopWindow
        tw.windowlist.add_item(self)

        from ifigure.widgets.taskbar import get_piscope_icon
        self.SetIcon(get_piscope_icon())

        self.Bind(wx.EVT_UPDATE_UI, self.onUpdateUI)
        self.Bind(wx.EVT_ACTIVATE, self.onActivate)

        if platform.system() == 'Darwin':
            # Note:
            #   (from doc)
            #   wxWidgets tries to optimize update events on some platforms. On Windows and GTK+,
            #   events for menubar items are only sent when the menu is about to be shown, and not
            #   in idle time
            #
            # On MaOSX, we see too many UpdateWindowUI call. This reduces the
            # call of UpdateWindowUI from OnInternalild
            #
            self.Bind(wx.EVT_MENU_OPEN, self.onMenuOpen)
            self.Bind(wx.EVT_MENU_CLOSE, self.onMenuClose)
            self._menu_open = False

        wx.CallAfter(self.UpdateWindowUI)

    def OnInternalIdle(self):
        internal_idl(self)

    def onMenuOpen(self, evt):
        self._menu_open = True

    def onMenuClose(self, evt):
        self._menu_open = False

    '''
    def turn_on_updateui_event(self):
        pass
        #self.Bind(wx.EVT_UPDATE_UI, self.onUpdateUI)

    def turn_off_updateui_event(self):
        pass
        #self.Unbind(wx.EVT_UPDATE_UI)
    '''

    def onActivate(self, evt):
        if evt.GetActive():
            wx.GetApp().process_child_focus(self)

            from ifigure.utils.cbook import get_current_display_size

            w, h = self.GetPosition()
            w1 = w
            h1 = h
            sw, sh = self.GetSize()
            #print("window", w, h, sw, sh)
            check = [False, False, False, False]
            for i in range(wx.Display.GetCount()):
                x0, y0, xd, yd = wx.Display(i).GetGeometry()
                #print("display", x0, y0, xd, yd)
                #
                #  Make sure that window is "visible".
                #
                xm = 10
                ym = 25
                do_set = False
                if w > x0 + xm and w <= x0 + xd - xm and h > y0 + ym and h < y0 + yd - ym:
                    check[0] = True
                if w + sw > x0 + xm and w + sw <= x0 + xd - xm and h > y0 + ym and h < y0 + yd - ym:
                    check[1] = True
                if w > x0 + xm and w <= x0 + xd - xm and h + sh > y0 + ym and h + sh < y0 + yd - ym:
                    check[2] = True
                if w + sw > x0 + xm and w + sw <= x0 + xd - xm and h + sh > y0 + ym and h + sh < y0 + yd - ym:
                    check[3] = True

            if not any(check):
                dprint2("adjusting window position", (w, h))
                #self.SetPosition((w1, h1))
                self.SetPosition((10, 10))

        # if hasattr(self, 'canvas'):
        #    self.canvas.activate_canvas(evt.GetActive())

        evt.Skip()

    def onChildFocus(self, evt):
        evt.Skip()
        pass

    def onUpdateUI(self, evt):
        #        if evt.GetId() > 0 and evt.GetId() < 300:  print evt.GetId(), ID_KEEPDATA
        #        print evt.GetEventObject(), evt.GetId()
        if evt.GetId() in (wx.ID_COPY, wx.ID_PASTE):
            evt.Enable(True)
            self.copy_mi.Enable(True)
            self.paste_mi.Enable(True)
        elif evt.GetId() == ID_KEEPDATA:
            if self.book is None:
                evt.Enable(False)
            else:
                evt.Enable(True)
                evt.Check(self.book._keep_data_in_tree)
#            evt.GetEventObject().Check(True)
        elif evt.GetId() == self.ID_WINDOWS:
            m = self._windowmenu
            for item in m.GetMenuItems():
                m.DestroyItem(item)
            viewers = [x for x in wx.GetApp().TopWindow.viewers]
            if len(viewers) == 0:
                evt.Enable(False)

            else:
                evt.Enable(True)
                app = wx.GetApp().TopWindow
                if not app in viewers:
                    viewers.append(app)
                mm = []
                for v in viewers:
                    if v.book is None:
                        continue

                    def dummy(evt, viewer=v):
                        viewer.Raise()
                        evt.Skip()
                    mm.append((v.__repr__(),
                               'Bring '+v.__repr__() + ' front',
                               dummy, v == self))
                if len(mm) > 0:
                    for a, b, c, d in mm:
                        mmi = self.add_menu(
                            m, wx.ID_ANY, a, b, c, kind=wx.ITEM_CHECK)
                        if d:
                            mmi.Check(True)

        elif evt.GetId() == ID_HIDEAPP:
            app = wx.GetApp().TopWindow
            if app.IsShown():
                evt.SetText('Hide Main Window')
            else:
                evt.SetText('Show Main Window')
            if app is self:
                if len(app.viewers) == 0:
                    evt.Enable(False)
                elif len(app.viewers) == 1 and app.viewers[0] == self:
                    evt.Enable(False)
                else:
                    evt.Enable(True)
        else:
            evt.Skip()

    def add_menu(self, menu, wx_id, label, info, func, **kargs):
        f1 = menu.Append(wx_id, label, info, **kargs)
        self.Bind(wx.EVT_MENU, func, f1)
        return f1

    def insert_menu(self, menu, loc,  wx_id, label, info, func, **kargs):
        f1 = menu.Insert(loc, wx_id, label, info, **kargs)
        self.Bind(wx.EVT_MENU, func, f1)
        return f1

    def onNextWindow(self, evt):
        tw = wx.GetApp().TopWindow
        w = self
        while True:
            w = tw.windowlist.get_next(w)
            if w.IsShown():
                break
        w.Raise()
        wx.GetApp().raise_palette(w)
        w.SetFocus()

    def onPrevWindow(self, evt):
        tw = wx.GetApp().TopWindow
        w = self
        while True:
            w = tw.windowlist.get_prev(w)
            if w.IsShown():
                break
        w.Raise()
        wx.GetApp().raise_palette(w)
        w.SetFocus()

    def append_accelerator_table(self, value):
        self._atable.append(value)

    def set_accelerator_table(self):
        atable = wx.AcceleratorTable(self._atable)
        self.SetAcceleratorTable(atable)

    def append_help_menu(self):
        self.helpmenu = wx.Menu()
        self.menuBar.Append(self.helpmenu, "&Help")
        self.add_menu(self.helpmenu, wx.ID_ANY,
                      "Connect Help online...", "Open Wiki help",
                      self.onShowWiki)
#        self.add_menu(self.helpmenu, wx.ID_ANY,
#                     "Enter 'WHTA IS THIS?' mode","Click item in question",
#                      self.onHelpItem)

    def append_help2_menu(self, helpmenu):
        ## helpmenu = viewmenu
        helpmenu.AppendSeparator()
        self.add_menu(helpmenu, wx.ID_FORWARD,
                      "Next window (F1)", "Bring next window forward",
                      self.onNextWindow)
        self.add_menu(helpmenu, wx.ID_BACKWARD,
                      "Previous window (F2)",
                      "Bring previous window forward",
                      self.onPrevWindow)
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))

    def append_std_viewmenu2(self, helpmenu):
        ## helpmenu = viewmenu
        helpmenu.AppendSeparator()
        self.add_menu(helpmenu, wx.ID_FORWARD,
                      "Next window (F1)", "Bring next window forward",
                      self.onNextWindow)
        self.add_menu(helpmenu, wx.ID_BACKWARD,
                      "Previous window (F2)",
                      "Bring previous window forward",
                      self.onPrevWindow)
        self._windowmenu = wx.Menu()
        item = helpmenu.AppendSubMenu(self._windowmenu, 'Viewers...')
        self.ID_WINDOWS = item.GetId()
        #item = wx.MenuItem(helpmenu, ID_WINDOWS, 'Viewers...', subMenu=self._windowmenu)
        # helpmenu.Append(item)
        #menu_AppendSubMenu(helpmenu, ID_WINDOWS, 'Viewers...', self._windowmenu)

        #menu_Append(helpmenu, ID_WINDOWS, 'Viewers...', self._windowmenu)
        helpmenu.AppendSeparator()
        self.add_menu(helpmenu, ID_HIDEAPP,
                      "Hide App",
                      "Show/Hide App",
                      self.onToggleHideApp)
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
        self.append_accelerator_table(
            (wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))

    def onToggleHideApp(self, evt):
        app = wx.GetApp().TopWindow
        if app.IsShown():
            app.Hide()
        else:
            app.Show()
            app.Raise()

    def onShowWiki(self, e=None):
        from ifigure.ifigure_config import iFigureConfig
        url = iFigureConfig().setting['wikihelp_front']
        webbrowser.open(url)

    def onHelpItem(self, e=None):
        def walk_children(window):
            yield window
            for g in window.GetChildren():
                for w2 in walk_children(g):
                    yield w2

#        self._helpmode = not self._helpmode
        if True:
            self.hwindows = [w for w in walk_children(self)]
            for w in self.hwindows:
                self.Bind(wx.EVT_HELP, self.onHelp, w)
            self.ch = wx.ContextHelp()
#        else:
#            self.ch.EndContextHelp()

    def onHelp(self, evt):
        from ifigure.ifigure_config import iFigureConfig

        p = evt.GetEventObject()
        name = ''
        while p is not None:
            if p.__class__.__module__.startswith('ifigure.widgets'):
                name = 'PieScope:'+p.__class__.__name__
                break
            if hasattr(p, '_help_name'):
                name = 'PieScope:'+p._help_name
            p = p.GetParent()
        if name != "":
            base_url = iFigureConfig().setting['wikihelp_base']
            webbrowser.open(base_url+name)


class FramePlus(FrameWithWindowList):
    '''
    Frame plus is wx.Frame with force_layout
    and deffered_force_layout, which call
    force_layout after the next idle event.

    it also define self.finemenu and self.editmenu,
    and method to define cut/paste menu
    '''
    ID_COPY = wx.NewIdRef(count=1)
    ID_PASTE = wx.NewIdRef(count=1)
    ID_COPYS = wx.NewIdRef(count=1)
    ID_PASTES = wx.NewIdRef(count=1)

    def __init__(self, *args,  **kargs):
        nomenu = kargs.pop('nomenu', False)

        kargs["size"] = (10, 10)
        super(FramePlus, self).__init__(*args, **kargs)

        # Setting up the menu.
        if not nomenu:
            self.filemenu = wx.Menu()
            self.editmenu = wx.Menu()
            self.viewmenu = wx.Menu()
            self.plotmenu = wx.Menu()
            self.menuBar.Append(self.filemenu, "&File")
            self.menuBar.Append(self.editmenu, "&Edit")
            self.menuBar.Append(self.viewmenu, "&View")
            self.menuBar.Append(self.plotmenu, "Plot")

        self.previous_size = (-1, -1)
        self.previous_size2 = (-1, -1)

        self._use_samerange_mni = None
        self._use_samerange = False

        self._bind_idle = False
        self._attaching = False
        self.Bind(wx.EVT_SIZE, self.onResize)

    def onUpdateUI(self, evt):
        s = (FramePlus.ID_COPY, FramePlus.ID_PASTE,
             FramePlus.ID_COPYS, FramePlus.ID_PASTES)
        if evt.GetId() in s:
            evt.Enable(True)
            self.copy_mi.Enable(True)
            self.paste_mi.Enable(True)
            v = False if self.canvas._figure is None else True
            self.copy_mis.Enable(v)
            self.paste_mis.Enable(v)
        else:
            super(FramePlus, self).onUpdateUI(evt)

    def write_canvas_size_to_status_bar(self):
        size = self.canvas.GetSize()
        sb = self.GetStatusBar()
        if sb is not None and self.IsShown():
            self.GetTopLevelParent().SetStatusText('canvas size = '+str(size))

    def onResize(self, evt):
        #        print 'onResize BookViewer', self.GetSize()
        #        if self.book._screen_ratio_lock is not None:
        #             self.set_canvas_ratio(self.book._screen_ratio_lock)

        if self.book is not None and self.canvas._figure is not None:
            self.mouse_pos = wx.GetMouseState().GetPosition().Get()
            if not self._bind_idle:
                wx.CallLater(100, self.resize_idle)
            self._bind_idle = True
            self.write_canvas_size_to_status_bar()

        if self.canvas._cutplane_btns is not None:
            self.canvas._cutplane_btns.place_bottoms()

        evt.Skip()

    def resize_idle(self):
        #        print 'resize idle', self.HasCapture()
        ms = wx.GetMouseState()
        if ((ms.LeftIsDown() or ms.RightIsDown()) and
                (self.mouse_pos != ms.GetPosition().Get())):
            wx.CallLater(100, self.resize_idle)
            return
        wx.CallLater(100, self.call_draw_after_resize)
        self._bind_idle = False

    def call_draw_after_resize(self):
        if self.canvas._figure is None:
            return

        if self.book._screen_ratio_lock is not None:
            self.set_canvas_ratio(self.book._screen_ratio_lock)
            self.write_canvas_size_to_status_bar()

        if self.canvas._cutplane_btns is not None:
            self.canvas._cutplane_btns.place_bottoms()

        fig_page = self.canvas._figure.figobj
        fig_page.reset_axesbmp_update()
        # fig_page.onResize(None)
        self.book.onResize(None)
        self.canvas.draw_later()

    def add_cutpaste_menu(self,  m):
        '''
        add cut/paste menu
        normally m is self.editmenu
        '''
        self.add_menu(m, wx.ID_ANY, "Cut", "",
                      self.onCut)
        id1 = FramePlus.ID_COPY
        self.copy_mi = self.add_menu(m, id1, "Copy", "",
                                     self.onCopy)
        self.copy_mis = self.add_menu(m, FramePlus.ID_COPYS, "Copy Special...", "",
                                      self.onCopyS)

        m.AppendSeparator()
        id2 = FramePlus.ID_PASTE
        self.paste_mi = self.add_menu(m, id2, "Paste", "",
                                      self.onPaste)
        self.paste_mis = self.add_menu(m, FramePlus.ID_PASTES, "Paste Special...", "",
                                       self.onPasteS)

        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('C'), id1))
        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('V'), id2))

    def onCut(self, e):
        pass

    def onCopy(self, e):
        pass

    def onPaste(self, e):
        pass

    def onCopyS(self, e):
        pass

    def onPasteS(self, e):
        pass

    def deffered_force_layout(self):
        self.Bind(wx.EVT_IDLE, self.do_force_layout)

    def do_force_layout(self, event):
        self.Unbind(wx.EVT_IDLE)
        self._force_layout()

    def _force_layout(self):
        # dprint1('_force_layout')
        # trick to show graphic... ;D
        # self.Freeze()
        self.canvas.mpl_disconnect()
        size = self.GetSize()
        self.SetSize([size[0]+1, size[1]+1])
        self.SetSize(size)

        self.Layout()
        self.canvas.chain_layout()
        # update menu check box
        self.gui_tree.update_check()
        self.canvas.mpl_connect()
        # self.Thaw()


class BookViewerFrame(FramePlus, BookViewerInteractive):
    '''
    book viewer frame is a frame with
    matplot and property editor

    '''
    ID_PM = [wx.NewIdRef(count=1) for x in range(16)]
    ID_EXPORTBOOK = wx.NewIdRef(count=1)
    ID_EXPORTBOOK_AS = wx.NewIdRef(count=1)
    ID_SAVEIMAGE = wx.NewIdRef(count=1)
    ID_BOOKNONE_CHECK = ID_PM + [ID_EXPORTBOOK, ID_EXPORTBOOK_AS, ID_SAVEIMAGE]
    ID_SAVEPROJAS = wx.NewIdRef(count=1)
    ID_SAVEPROJ = wx.NewIdRef(count=1)
    ID_LOCKSCALE = wx.NewIdRef(count=1)
    ID_SCREENRATIOLOCK = wx.NewIdRef(count=1)

    def __init__(self, *args, **kargs):

        # hisotry mode 0 : global history stack
        # 1 : histories are associated to window
        GlobalHistory().set_mode(1)
        self.history = UndoRedoHistory(self)

        ###
        if "book" in kargs:
            self.book = kargs["book"]
            del kargs["book"]
            self.book.set_open(True)
        else:
            self.book = None

        self.gui_tree = None
        self.canvas = None
        self.property_editor = None
        self.export_book_menu = None
        self.save_project_menu = None

        self.isattachable = kargs.pop('isattachable', True)
        self.isinteractivetarget = kargs.pop('isinteractivetarget', True)
        self.isismultipage = kargs.pop('ismultipage', True)

        self.ipage = 0
        self._del_book_from_proj = 0
        super(BookViewerFrame, self).__init__(*args, **kargs)
        BookViewerInteractive.__init__(self)

        self._sb_timer = wx.Timer(self)

    def __del__(self):
        '''
        make sure that history is cleared. so that
        references hold in hisotry becomes None
        '''
        if self.history is not None:
            self.history.clear()
        self.history = None

    def onUpdateUI(self, evt):
        id = evt.GetId()
        if id in BookViewerFrame.ID_BOOKNONE_CHECK:
            if self.book is None:
                evt.Enable(False)
            else:
                if (id == BookViewerFrame.ID_EXPORTBOOK):
                    if self.book.hasvar("original_filename"):
                        fname = self.book.getvar("original_filename")
                        if (fname is not None and
                            os.path.exists(fname) and
                                os.access(fname, os.W_OK)):
                            evt.Enable(True)
                        else:
                            evt.Enable(False)
                    else:
                        evt.Enable(False)
                else:
                    evt.Enable(True)
                if id == BookViewerFrame.ID_PM[14]:
                    if self.canvas._layout_mode:
                        evt.Check(True)
                    else:
                        evt.Check(False)
                elif id == BookViewerFrame.ID_PM[15]:
                    if self.canvas._frameart_mode:
                        evt.Check(True)
                    else:
                        evt.Check(False)
                elif id == BookViewerFrame.ID_LOCKSCALE:
                    if self.book._lock_scale:
                        evt.Check(True)
                    else:
                        evt.Check(False)
                elif id == BookViewerFrame.ID_SCREENRATIOLOCK:
                    if self.book._screen_ratio_lock is None:
                        evt.Check(False)
                    else:
                        evt.Check(True)
        elif (id == ID_HDF_EXPORT):
            if wx.GetApp().TopWindow.hdf_export_window is None:
                evt.Enable(True)
            else:
                evt.Enable(False)
        elif self.gui_tree.onUpdateUI(evt):
            pass
        else:
            if (id == BookViewerFrame.ID_SAVEPROJ):
                app = wx.GetApp().TopWindow
                top_hidden = (len(app.viewers) == 1 and
                              not app.IsShown())
                if top_hidden:
                    evt.Enable(False)
                    evt.Show(False)
                else:
                    if app.proj.getvar('filename') is not None:
                        evt.Enable(True)
                        evt.Show(True)
                    else:
                        evt.Enable(False)
            elif (id == BookViewerFrame.ID_SAVEPROJAS):
                app = wx.GetApp().TopWindow
                top_hidden = (len(app.viewers) == 1 and
                              not app.IsShown())
                if top_hidden:
                    evt.Enable(False)
                    evt.Show(False)
                else:
                    evt.Enable(True)
                    evt.Show(True)
            else:
                FramePlus.onUpdateUI(self, evt)

#    def Close(self):
#        FramePlus.Close(self)
    def __repr__(self):
        txt = self.__class__.__name__
        if self.book is None:
            return txt + '(book=None)'
        else:
            return txt + '(book=' + self.book.__repr__() + ')'

    def clear_history(self):
        if self.history is not None:
            self.history.clear()
            self.history = None

    def close_book(self):
        self.clear_history()
        if self.book is not None:
            self.book.set_open(False)
            s = self.canvas.get_canvas_screen_size()
            self.book._screen_size = (s[0], s[1])
            self.canvas.set_figure(None)

    def adjust_frame_size(self):
        bk = self.book
        if (bk._screen_size[0] == 0 and
                bk._screen_size[1] == 0):
            return
        dx = bk._screen_size[0] - self.canvas.get_canvas_screen_size()[0]
        dy = bk._screen_size[1] - self.canvas.get_canvas_screen_size()[1]
        self.canvas.set_canvas_screen_size(bk._screen_size)
        s = self.GetSize()
        self.SetSize((s[0]+dx, s[1]+dy))

    def onKeepData(self, evt):
        self.book.toggle_keep_data()

    def add_bookmenus(self, editmenu, viewmenu):
        subm = wx.Menu()
        #menu_AppendSubMenu(editmenu, BookViewerFrame.ID_PM[0], 'Add Page', subm)
        if self.isismultipage:
            menu_AppendSubMenu(editmenu, wx.ID_ANY, 'Add Page', subm)
            self.add_menu(subm, BookViewerFrame.ID_PM[1],
                          "Before Current Page",
                          "add a new page before the current page", self.onAddPageB)
            self.add_menu(subm, BookViewerFrame.ID_PM[2],
                          "After Current Page",
                          "add a new page after the current page",  self.onAddPage)

            self.add_menu(editmenu, BookViewerFrame.ID_PM[3],
                          "Delete Page", "delete current page",
                          self.onDelPage)
            editmenu.AppendSeparator()
        self.add_menu(editmenu, ID_KEEPDATA,
                      "Keep Book in Tree",
                      "Book data is kept in tree when this window is closed",
                      self.onKeepData,
                      kind=wx.ITEM_CHECK)
        self.add_menu(viewmenu, BookViewerFrame.ID_PM[4],
                      "Next Page",  "next page",  self.onNextPage)
        self.add_menu(viewmenu, BookViewerFrame.ID_PM[5],
                      "Previous Page", "previous page",
                      self.onPrevPage)

    def add_std_plotmenu(self, plotmenu):
        self.add_menu(
            plotmenu, BookViewerFrame.ID_PM[6], 'Autoscale X', "", self.onXauto)
        self.add_menu(
            plotmenu, BookViewerFrame.ID_PM[7], 'Autoscale Y', "", self.onYauto)
        self.add_menu(plotmenu, BookViewerFrame.ID_PM[8], 'Autoscale all X', "",
                      self.onXauto_all)
        self.add_menu(plotmenu, BookViewerFrame.ID_PM[9], 'Autoscale all Y', "",
                      self.onYauto_all)
        self.add_menu(
            plotmenu, BookViewerFrame.ID_PM[10], 'All same X scale', "", self.onSameX)
        self.add_menu(
            plotmenu, BookViewerFrame.ID_PM[11], 'All same X (Y auto)', "", self.onSameX_autoY)
        self.add_menu(
            plotmenu, BookViewerFrame.ID_PM[12], 'All same Y scale', "", self.onSameY)
        plotmenu.AppendSeparator()
        self._use_samerange_mni = self.add_menu(plotmenu, BookViewerFrame.ID_PM[13],
                                                'Use same range in all pages', "",
                                                self.onSameRange, kind=wx.ITEM_CHECK)
        self._use_samerange_mni.Check(self._use_samerange)
        # self._lock_scale_mni = self.add_menu(plotmenu, BookViewerFrame.ID_LOCKSCALE,
        #                       "Lock scale", "",
        #                        self.onLockScale, kind = wx.ITEM_CHECK)
        # self._lock_scale_mni.Check(False)

        self.add_menu(plotmenu, BookViewerFrame.ID_PM[14],
                      "Layout mode", "",
                      self.onToggleLayoutMode, kind=wx.ITEM_CHECK)
        self.add_menu(plotmenu, BookViewerFrame.ID_PM[15],
                      "FrameArt mode", "",
                      self.onToggleFrameArtMode, kind=wx.ITEM_CHECK)

        # self.add_menu(plotmenu, BookViewerFrame.ID_PM[15],
        #                        "3D buttons", "",
        #                        self.onToggle3DMenu, kind = wx.ITEM_CHECK)

    def add_saveimage_menu(self, parent):
        self.add_menu(parent, BookViewerFrame.ID_SAVEIMAGE,
                      "Save Image", "Save Image",
                      self.onSaveImage)

    def add_exporthdf_menu(self, parent):
        self.add_menu(parent, ID_HDF_EXPORT,
                      "HDF data...", "Export HDF data.",
                      self.onExportHDF)

    def append_screen_ratio_menu(self, viewmenu):
        ratiomenu = wx.Menu()
        viewmenu.AppendSubMenu(ratiomenu, 'Canvas Size')
        #menu_Append(viewmenu, wx.ID_ANY, 'Canvas Size', ratiomenu)
        self.add_menu(ratiomenu, wx.ID_ANY,
                      "Aspect = 3:4", "set canvas x y ratio to 3:4",
                      self.onCanvasRatio3_4)
        self.add_menu(ratiomenu, wx.ID_ANY,
                      "Aspect = 9:16", "set canvas x y ratio to 9:16",
                      self.onCanvasRatio6_19)
        self.add_menu(ratiomenu, wx.ID_ANY,
                      "Set...", "set canvas size",
                      self.onCanvasSetSize)
        self.add_menu(ratiomenu, BookViewerFrame.ID_SCREENRATIOLOCK,
                      "Lock Ratio", "lock canvas ratio to current ratio",
                      self.onCanvasLockRatio,  kind=wx.ITEM_CHECK)

    def onCanvasLockRatio(self, evt):
        if self.book._screen_ratio_lock is None:
            cx, cy = self.canvas.GetSize()
            self.book._screen_ratio_lock = float(cy)/float(cx)
        else:
            self.book._screen_ratio_lock = None

    def onCanvasRatio6_19(self, evt):
        if self.book._screen_ratio_lock is not None:
            self.book._screen_ratio_lock = 9./16.
        self.set_canvas_ratio(9./16)
        evt.Skip()

    def onCanvasRatio3_4(self, evt):
        if self.book._screen_ratio_lock is not None:
            self.book._screen_ratio_lock = 3./4.
        self.set_canvas_ratio(3./4.)
        evt.Skip()

    def onCanvasSetSize(self, evt):
        cx, cy = self.canvas.GetSize()
        sx, sy = self.GetSize()
        dx = sx - cx
        dy = sy - cy

        from ifigure.utils.edit_list import EditListDialog
        ll = [["X: ", str(cx), 0],
              ["Y: ", str(cy), 0], ]
        dia = EditListDialog(self, wx.ID_ANY, 'Canvas Size', ll)
        dia.Centre()
        val = dia.ShowModal()
        value = dia.GetValue()
        if val != wx.ID_OK:
            dia.Destroy()
            return
        dia.Destroy()
        new_cx = int(value[-2])
        new_cy = int(value[-1])

        self.Freeze()
        self.SetSize((new_cx+dx, new_cy+dy))
        self.canvas.SetSize((new_cx, new_cy))
        self.write_canvas_size_to_status_bar()
        self.Thaw()

    def set_canvas_ratio(self, ratio):
        sx, sy = self.GetSize()
        cx, cy = self.canvas.GetSize()
        dx = sx - cx
        dy = sy - cy

        c1 = (cx, int(float(cx)*ratio))
        c2 = (int(float(cy)/ratio), cy)

        if abs(c1[1] - cy) > abs(c2[0]-cx):
            new_cx, new_cy = c2
        else:
            new_cx, new_cy = c1

        self.Freeze()
        self.SetSize((new_cx+dx, new_cy+dy))
        self.canvas.SetSize((new_cx, new_cy))
        self.write_canvas_size_to_status_bar()
        self.Thaw()

    def extra_canvas_range_menu(self):
        return []

    def get_use_samerange(self):
        return self._use_samerange

    def set_use_samerange(self, value):
        self._use_samerange = value
        self._use_samerange_mni.Check(self._use_samerange)

    def onLockScale(self, e):
        if self.book._lock_scale:
            self.book._lock_scale = False
        else:
            self.book._lock_scale = True

    def onToggleLayoutMode(self, e):
        if self.canvas._layout_mode:
            self.canvas.exit_layout_mode()
        else:
            self.canvas.enter_layout_mode()

    def onToggleFrameArtMode(self, e):
        if self.canvas._frameart_mode:
            self.canvas._frameart_mode = False
        else:
            self.canvas._frameart_mode = True

    def onToggle3DMenu(self, e):
        if self.canvas.toolbar.simple_bar:
            self.canvas.toolbar.Show3DMenu()
        else:
            self.canvas.toolbar.Hide3DMenu()

    def onSameRange(self, e):
        #        if not self._use_samerange_mni.IsChecked():
        #           self._use_samerange_mni.Check(False)
        #        else:
        #            self._use_samerange_mni.Check(True)
        p = self.book.get_page(self.ipage)
        hist = [UndoRedoFigobjMethod(
            p._artists[0], 'viewer_samerange_mode', self._use_samerange_mni.IsChecked())]
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(hist, menu_name='samerange mode')

    def onSameX(self, e):
        self.canvas.set_samex()

    def onSameX_autoY(self, e):
        self.canvas.set_samex_autoy()

    def onSameY(self, e):
        self.canvas.set_samey()

    def onXauto_all(self, e):
        self.canvas.set_xauto_all()

    def onYauto_all(self, e):
        self.canvas.set_yauto_all()

    def onXauto(self, e):
        self.canvas.set_xauto()

    def onYauto(self, e):
        self.canvas.set_yauto()

    def onCut(self, e):
        fc = self.FindFocus()
        if (fc is self.canvas.canvas or
                fc in self.canvas.canvas.GetChildren()):
            self.canvas.Cut()
        else:
            e.Skip()

    def onCopy(self, e):
        fc = self.FindFocus()
        if (fc is self.canvas.canvas or
                fc in self.canvas.canvas.GetChildren()):
            self.canvas.Copy()
            wx.GetApp().TopWindow.proj_tree_viewer.update_widget()
        else:
            e.Skip()

    def onCopyPage(self, e):
        self.canvas.copy_selection(obj=[self.canvas._figure.figobj])

    def onCopyAxes(self, e):
        if self.canvas.axes_selection() == None:
            return
        self.canvas.copy_selection(obj=[self.canvas.axes_selection().figobj])

    def onPaste(self, e):
        fc = self.FindFocus()
        if (fc is self.canvas.canvas or
                fc in self.canvas.canvas.GetChildren()):
            val = self.canvas.Paste()
            wx.GetApp().TopWindow.proj_tree_viewer.update_widget()
            return val
        else:
            e.Skip()
            return []

    def onPastePage(self, e):
        from ifigure.ifigure_config import canvas_scratch_page as csp
        self.canvas.paste_selection(cs=csp)
        ret = dialog.message(parent=self,
                             message='Do you want to replace page ?',
                             title="Paste Page",
                             style=4)
        if ret == 'yes':
            self.del_page(self.ipage)
            self.set_window_title()
#            ifigure.events.SendShowPageEvent(np, id)
        else:
            self.show_page(self.ipage+1)
            np = self.get_page(self.ipage)
            ifigure.events.SendShowPageEvent(np, self)
        self.canvas.draw()
        self.history.clear()
        wx.GetApp().TopWindow.proj_tree_viewer.update_widget()

    def onPasteAxes(self, e):
        from ifigure.ifigure_config import canvas_scratch_axes as csa
        self.canvas.paste_selection(cs=csa)
        self.canvas.draw()
        wx.GetApp().TopWindow.proj_tree_viewer.update_widget()

    def onCopyArea(self, e):
        from ifigure.ifigure_config import scratch as cs
        areas = self.canvas._figure.figobj.get_area()
        data = {"mode": 'area', "areas": areas}

        fid = open(cs+'_area', 'wb')
        pickle.dump(data, fid)
        fid.close()

    def onCopyToCB(self, e=None):
        '''
        Copy_to_Clipboard_mod copys the buffer data
        which does not have highlight drawn
        '''

        canvas = self.canvas.canvas
        figure_image = canvas.figure_image[0]
        h, w, d = figure_image.shape
        image = wxEmptyImage(w, h)
        image.SetData(figure_image[:, :, 0:3].tobytes())
        image_SetAlpha(image, figure_image[:, :, 3])
        bmp = wxBitmapFromImage(image)
        canvas.Copy_to_Clipboard_mod(pgbar=True,
                                     bmp=bmp)
        if e is not None:
            e.Skip()

    def onPasteArea(self, e):
        from ifigure.ifigure_config import scratch as cs
        if not os.path.exists(cs+'_area'):
            dlg = wx.MessageDialog(None,
                                   'Layout data does not exist.',
                                   'Error',  wx.OK)
            ret = dlg.ShowModal()
            dlg.Destroy()
            return
        fid = open(cs+'_area', 'r')
        data = pickle.load(fid)
        fid.close()
        self.canvas.set_area(data["areas"])
        self.draw()

    def onCopyS(self, e):
        from ifigure.utils.edit_list import DialogEditList
        s = {"style": wx.CB_DROPDOWN,
             "choices": ["Section", "Page", "Section Layout", "ToClipboard"]}
        list6 = [[None, 'Choose item to copy', 102., None],
                 [None, 'Section',  104,  s], ]

        value = DialogEditList(list6, modal=True,
                               title='copy special...',
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=self)
        if not value[0]:
            return
        idx = s['choices'].index(str(value[1][1]))
        if idx == 0:
            self.onCopyAxes(e)
        elif idx == 1:
            self.onCopyPage(e)
        elif idx == 2:
            self.onCopyArea(e)
        elif idx == 3:
            self.onCopyToCB(e)

    def onPasteS(self, e):
        from ifigure.utils.edit_list import DialogEditList
        s = {"style": wx.CB_DROPDOWN,
             "choices": ["Section",
                         "Page", "Section Layout",
                         "Paste to all sections", ]}
        list6 = [[None, 'Choose item to Paste', 102., None],
                 [None, 'Section',  104,  s], ]

        value = DialogEditList(list6, modal=True,
                               title='paste special...',
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=self)
        if not value[0]:
            return
        idx = s['choices'].index(str(value[1][1]))
        if idx == 3:
            fig_page = self.canvas._figure.figobj
            header = self.canvas.paste_selection(return_header=True)
            if header['mode'] != 'axesobj':
                ret = dialog.message(parent=self,
                                     message='Copied object can not be paste\n to section.',
                                     title="Paste to mutliple section",
                                     style=0)
                return
            self.canvas.unselect_all()
            hist = []
            finish_action = []
            for ax in fig_page.walk_axes():
                self.canvas.axes_selection = weakref.ref(ax._artists[0])
                status, h, f = self.canvas.paste_selection(return_history=True)
                if status is not None:
                    hist.extend(h)
                    finish_action.extend(f)
            if len(hist) == 0:
                return

            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(hist,
                                                           finish_action=finish_action, menu_name='paste all')
        elif idx == 0:
            self.onPasteAxes(e)
        elif idx == 1:
            self.onPastePage(e)
        elif idx == 2:
            self.onPasteArea(e)

    def onSaveImage(self, evt):
        self.canvas.save_pic()
        evt.Skip()

    def onExportHDF(self, evt):
        self.canvas.export_hdf()
        evt.Skip()

    def onNewBook(self, evt, viewer=None, proj=None, basename=None, **kwargs):
        if viewer is None:
            dprint1('onNewBook is called with viewer = None')
            dprint1('this function should be overwritten')
            return

#        from ifigure.widgets.book_viewer import BookViewer
        if proj is not None:
            book = proj.onAddBook(basename=basename)
        else:
            book = self.book.get_root_parent().onAddBook(basename=basename)
        i_page = book.add_page()
        page = book.get_page(i_page)
        page.add_axes()
        page.realize()
        page.set_area([[0, 0, 1, 1]])
        ifigure.events.SendOpenBookEvent(book, w=self,
                                         viewer=viewer, **kwargs)
        ifigure.events.SendChangedEvent(book, w=self)

    def onSaveBook(self, evt, path=''):
        if path == '':
            path = self.book.getvar("original_filename")
            if path is None:
                self.onSaveBookAs(evt)
        if path == '':
            return
        print("saving to " + path)
        s = self.canvas.get_canvas_screen_size()
        self.book._screen_size = (s[0], s[1])
        # print 'book size', self.book._screen_size
        self.book.save_subtree(path, compress=True)
        self.book.setvar("original_filename", path)
        self.set_window_title()

    def onSaveBookAs(self, evt):
        save_dlg = wx.FileDialog(None, message="Enter BookFile Name",
                                 defaultDir=os.getcwd(),
                                 defaultFile='book_file',
                                 wildcard="BookFile (*.bfz)|*.bfz",
                                 style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if save_dlg.ShowModal() == wx.ID_OK:
            path = save_dlg.GetPath()
            if path[-4:] != '.bfz':
                path = path+'.bfz'
            print("saving to " + path)
            self.onSaveBook(evt, path=path)
#           self.update_exportas_menu()
        save_dlg.Destroy()

    def _onloadbook(self, path):
        print('_onloadbook do nothing')
        return
    #        bk = self.book.get_parent().load_subtree(path, compress=True)
    #    if not isinstance(bk, FigBook): return

    #    self.ipage = 0
    #    bk.realize()
    #    bk.setvar("original_filename", path)

    #   if mode == 0:
    #        self.book.set_open(False)
    #        obk = self.book
    #        self.book = bk
    #        self.book.set_open(True)
    #        self.open_book(use_bookframesize=True)
    #        obk.destroy()
    #    elif mode == 1:
    #        return bk

    def onLoadBook(self, evt, mode=0, proj=None, file=''):
        '''
        mode = 0 : destroy present contents
        mode = 1 : append new book to tree
        '''
        if file == '':
            open_dlg = wx.FileDialog(None, message="Select book (.bfz) project to open",
                                     wildcard='*.bfz', style=wx.FD_OPEN)
            if open_dlg.ShowModal() == wx.ID_OK:
                file = open_dlg.GetPath()
                open_dlg.Destroy()
            else:
                open_dlg.Destroy()
                return

        if proj is not None:
            bk = proj.load_subtree(file, compress=True)
        else:
            if self.book is not None:
                bk = self.book.get_parent().load_subtree(file, compress=True)

        if not isinstance(bk, FigBook):
            return

        self.ipage = 0
#           bk.realize()
        bk.setvar("original_filename", file)

        if mode == 0:
            if self.book is not None:
                self.book.set_open(False)
                obk = self.book
            else:
                obk = None
            self.book = bk
            self.book.set_open(True)
            self.open_book(use_bookframesize=True)
            if obk is not None:
                obk.destroy()
        elif mode == 1:
            return bk
        ifigure.events.SendChangedEvent(self.book, w=self)

    def onLoadBookNew(self, evt, viewer=None, proj=None, **kwargs):
        if viewer is None:
            dprint1('onLoadBookNew is called with viewer = None')
            dprint1('this function should be overwritten')
            return
        bk = BookViewerFrame.onLoadBook(self, evt, mode=1, proj=proj)
        if bk is None:
            return
        ifigure.events.SendOpenBookEvent(bk,
                                         w=self,
                                         viewer=viewer, **kwargs)

    def onAddPageB(self, e=None):
        self.onAddPage(e, before=True)

    def onAddPage(self, e=None, before=None):
        np = self.new_page()
        new_ipage = self.add_page(np, before=before)
#        ipage=self.ipage+1
        self.show_page(new_ipage)
        if e is not None:
            id = e.GetEventObject()
        else:
            id = self
        ifigure.events.SendChangedEvent(np, None, True)
        ifigure.events.SendShowPageEvent(np, id)
        self.deffered_force_layout()

    def onDelPage(self, e):
        pbook = self.book
        num_page = pbook.num_page()
        if num_page == 1:
            dlg = wx.MessageDialog(None,
                                   'This is the last page, and you cannot delete it.',
                                   'Delete Page',
                                   wx.OK)
            ret = dlg.ShowModal()
            dlg.Destroy()
            # need to have at least one page
            return
        ipage = self.ipage
        self.del_page(ipage)

        ifigure.events.SendChangedEvent(self.book, None, True)
        self.deffered_force_layout()
#        ifigure.events.SendShowPageEvent(page, id)

    def num_page(self):
        return self.book.num_page()

    def onNextPage(self, e):
        num_page = self.num_page()
        if self.ipage == num_page-1:
            return
        ifigure.events.SendShowPageEvent(self.book, self, '1')

    def onPrevPage(self, e):
        if self.ipage == 0:
            return
        ifigure.events.SendShowPageEvent(self.book, self, '-1')

    def onAppPreference(self, e):
        from ifigure.widgets.dlg_preference import dlg_preference
        tw = wx.GetApp().TopWindow
        components = tw.get_components()
        dlg_preference(components, self)
        for c in components:
            c.save_setting()

    def append_save_project_menu(self, m):
        self.save_project_menu = self.add_menu(m,
                                               BookViewerFrame.ID_SAVEPROJ,
                                               "Save Project", "Save project",
                                               self.onSaveProject)
        self.add_menu(m, BookViewerFrame.ID_SAVEPROJAS,
                      "Save Project As...", "Save project",
                      self.onSaveProjectAs)
        app = wx.GetApp().TopWindow
        self.save_project_menu.Enable(app.save_project_menu.IsEnabled())

    def onSaveProject(self, e):
        app = wx.GetApp().TopWindow
        app.onSave(e)

    def onSaveProjectAs(self, e):
        app = wx.GetApp().TopWindow
        app.onSaveAs(e)

    # by default attach to main is off
    def onAttachFigure(self, e):
        pass

    def adjust_attach_menu(self):
        pass

    def draw(self, *args, **kwargs):
        self.canvas.draw(*args, **kwargs)

    def draw_all(self):
        self.canvas.draw_all()

    def last_draw_time(self):
        return self.canvas._last_draw_time

    def get_axes(self, ipage=None, iaxes=None):
        f_page = self.get_page(ipage=ipage)

        naxes = f_page.num_axes()
        if naxes == 0:
            # no axes exist...
            return
        if iaxes is None:
            ax = self.canvas.axes_selection()
            if ax is None:
                iaxes = 0
            else:
                from ifigure.mto.fig_axes import FigColorBar
                if isinstance(ax.figobj, FigColorBar):
                    return ax.figobj.get_parent()
                return ax.figobj
#        else:
        f_axes = f_page.get_axes(iaxes)
        return f_axes

    def set_axes(self, fig_axes):
        self.canvas.set_axes_selection(fig_axes._artists[0])
        self.canvas.unselect_all()

    def get_page(self, ipage=None):
        if ipage is None:
            # place figobj into current page
            figure = self.canvas.get_figure()
            if figure is None:
                return None
            f_page = figure.figobj
        else:
            f_page = self.book.get_page(ipage)
        return f_page

    def del_page(self, ipage=None):
        if ipage is None:
            ipage = self.ipage

        if self.ipage == ipage:
            if (self.ipage + 1) == self.book.num_page():
                newipage = self.ipage-1
            else:
                newipage = self.ipage+1
        else:
            newipage = self.ipage

        f_page = self.get_page(ipage)   # page to be gone
        new_f_page = self.get_page(newipage)  # page to be shown
        self.show_page(newipage)
        self.book.del_page(f_page)
        self.ipage = self.book.i_page(new_f_page)
#        num_page=self.book.num_page()
#        ipage = min([newipage, num_page-1])
#        ipage = max([0, ipage])
#        print('new ipage', self.ipage)

    def add_page(self, *argc, **kargs):
        '''
        add page to pbook and return index
        of the newly added page
       '''
        before = kargs['before'] if 'before' in kargs else None
        name, page = cbook.ParseNameObj(*argc)
        if name is None:
            name = self.book.get_next_name('page')
        if page is None:
            ipage = self.book.add_page(name)
            page = self.book.get_page(ipage)
        else:
            ichild = self.book.add_child(name, page)
        ipage = self.book.i_page(page)
        cpage = self.book.get_page(self.ipage)

        idx = self.book.i_child(page)
        if before:
            idx2 = self.book.i_child(cpage)
        else:
            idx2 = self.book.i_child(cpage)+1
        self.book.move_child(idx, idx2)
        return self.book.i_page(page)

    def show_page(self, ipage=0, last=False, first=False):

        f_page = self.book.get_page(self.ipage)
        if f_page is None:
            return
        if f_page.isempty():
            f_page.realize()
#        self.realize_all_page()
        self.ipage = ipage
        if last is True:
            self.ipage = len(self.book.get_children())-1
        if first is True:
            self.ipage = 0
#        self.realize()
        if self.book.num_page() == 0:
            self.book.set_open(False)
            return
        if not self.book.isOpen:
            self.book.set_open(True)
        self._rebuild_ifigure_canvas()
        self._link_canvas_property_editor()
        self.gui_tree.primary_client(self.canvas)

        wx.CallAfter(self.SendSizeEvent)
        # self.deffered_force_layout()

    def new_page(self):
        new_page = FigPage()
        new_page.add_axes()
        new_page.realize()
        new_page.set_area([[0, 0, 1, 1]])
        return new_page

    def set_section(self, *args, **kargs):
        f_page = self.get_page()
        f_page.set_section(*args, **kargs)
#        self.canvas.canvas.draw()

    def update_exportas_menu(self):
        return
#       This task was done by UpdateUI (2014. 03 S.Shiraiwa)
#        if self.export_book_menu is None: return
#        if self.book is None :
#           self.export_book_menu.Enable(False)
#           return
#        if self.book.hasvar("original_filename"):
#           fname = self.book.getvar("original_filename")
#           if (os.path.exists(fname) and
#               os.access(fname, os.W_OK)):
#               self.export_book_menu.Enable(True)
#        else:
#           self.export_book_menu.Enable(False)

    def realize_all_page(self):
        if any([page.isempty() for page in self.book.walk_page()]):
            pgb = dialog.progressbar(self,
                                     'drawing all pages', 'please wait...',
                                     self.book.num_page())
            for k, v in enumerate(self.book.get_children()):
                fname, f_page = v
                if f_page.isempty():
                    f_page.realize()
                pgb.Update(k)
            pgb.Destroy()

    def open_book(self, use_bookframesize=False):
        self.update_exportas_menu()
        f_page = self.book.get_page(self.ipage)
        if f_page is None:
            return
#        self.realize_all_page()
        if f_page.isempty():
            f_page.realize()
        figure = f_page.get_artist(idx=0)
        figure.canvas = self.canvas.canvas
        org_fig = self.canvas.get_figure()
#        print org_fig.figobj.get_full_path()
#        if org_fig is not None: print org_fig.get_figwidth()
        self.canvas.set_figure(figure)

        if org_fig is not None:
            if (org_fig.get_figwidth() != figure.get_figwidth() or
                    org_fig.get_figheight() != figure.get_figheight()):
                self.canvas.canvas._onSize(None, nocheck=True)
#        if org_fig is not None: print org_fig.get_figwidth()
#        wx.PostEvent(self.canvas.canvas, wx.SizeEvent())
        self.canvas.unselect_all()
        self.canvas.axes_selection = cbook.WeakNone()
        if use_bookframesize:
            self.adjust_frame_size()
        self.canvas.canvas.draw()
        self.set_window_title()

        self.book._viewer_class = self.__class__.__name__
        self.book._viewer_module = self.__class__.__module__

    def _rebuild_ifigure_canvas(self):
        if self.canvas is not None:
            # this part is to change page w/o rebuilding
            # canvas widget....
            # self.canvas.unselect_all()
            # self.canvas.mpl_disconnect()
            self.open_book()
            if self.nsec() > 0:
                self.isec(0)
            return

        f_page = self.book.get_page(self.ipage)
        if f_page is not None:
            if f_page.isempty():
                f_page.generate_artist()
            figure = f_page.get_artist(idx=0)
        else:
            figure = None
        self.canvas = ifigure_canvas(parent=self.panel1,
                                     figure=figure)
        f_page.realize_children()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.canvas, 1, wx.EXPAND)
#        hbox.Add(self.property_editor, 0)
        self.panel1.SetSizer(hbox)
#        self.Layout()
        self.set_window_title()
        if self.nsec() > 0:
            self.isec(0)

    def _link_canvas_property_editor(self):
        self.property_editor.set_canvas(self.canvas)
        self.canvas.set_property_editor(self.property_editor)

    def set_window_title(self):
        if self.book is None:
            self.SetTitle('')
            return
        title = self.book.get_full_path()+'(page '+str(self.ipage+1)+')'
        self.SetTitle(title)

    def BindTreeDictEvents(self):
        self.Bind(ifigure.events.TD_EVT_EDITFILE,
                  self.onTD_EditFile)
        self.Bind(ifigure.events.TD_EVT_CLOSEFILE,
                  self.onTD_CloseFile)
        self.Bind(ifigure.events.TD_EVT_CHANGED,
                  self.onTD_Changed)
        self.Bind(ifigure.events.TD_EVT_VAR0CHANGED,
                  self.onTD_Var0Changed)
        self.Bind(ifigure.events.TD_EVT_ARTIST_SELECTION,
                  self.onTD_Selection)
        self.Bind(ifigure.events.TD_EVT_ARTIST_REPLACE,
                  self.onTD_Replace)
        self.Bind(ifigure.events.TD_EVT_THREAD_START,
                  self.onTD_ThreadStart)
        self.Bind(ifigure.events.TD_EVT_SHOWPAGE,
                  self.onTD_ShowPage)
        self.Bind(ifigure.events.TD_EVT_RANGECHANGED,
                  self.onTD_RangeChanged)
        self.Bind(ifigure.events.TD_EVT_OPENBOOK,
                  self.onTD_OpenBook)
        self.Bind(ifigure.events.TD_EVT_CLOSEBOOK,
                  self.onTD_CloseBook)
        self.Bind(ifigure.events.TD_EVT_FILECHANGED,
                  self.onTD_FileChanged)
        self.Bind(ifigure.events.TD_EVT_IAXESSELECTION,
                  self.onTD_IAxesSelection)
        self.Bind(ifigure.events.TD_EVT_NEWHISTORY, self.onNewHistory)

    def onNewHistory(self, evt):
        history = self.history
        history.flush_entry()
#        self.canvas.nodraw_on()
#        self.canvas.draw()
#        self.canvas.draw_later()

        wx.CallLater(100, self.property_editor.update_panel)
        wx.GetApp().TopWindow.set_proj_saved(False)

    def onTD_EditFile(self, evt):
        pass

    def onTD_CloseFile(self, evt):
        pass

    def onTD_Changed(self, evt):
        pass

    def onTD_Var0Changed(self, evt):
        pass

    def onTD_Selection(self, evt):
        pass

    def onTD_SelectionInFigure(self, evt):
        td = evt.GetTreeDict()
        name = td.name
        self.set_status_text(name, timeout=5000)

    def onTD_Replace(self, evt):
        #        print 'replace event, bookviewer'
        self.canvas.onTD_Replace(evt)
        self.property_editor.onTD_Replace(evt)
        # do somework to palette and canvas....
        pass

    def onTD_ThreadStart(self, evt):
        pass

    def onTD_ShowPage(self, evt):
        dt = evt.GetTreeDict()  # dt fig_page
        if isinstance(dt, FigPage):
            self.book.set_open(False)
            dt.get_root_parent().set_pbook(dt.get_parent())
            self.book = dt.get_parent()
            ipage = self.book.i_page(dt)
        elif dt == self.book:
            ipage = self.ipage
        else:
            return
        num_page = self.book.num_page()
        if evt.inc == '-1':
            ipage = max([self.ipage-1, 0])
        elif evt.inc == '1':
            ipage = min([self.ipage+1, num_page-1])
        elif evt.inc == 'first':
            ipage = 0
        elif evt.inc == 'last':
            ipage = num_page-1
        else:
            pass

        self.show_page(ipage)
        self.canvas.exit_layout_mode()
        self.property_editor.onTD_ShowPage(evt)

        bmp_w, bmp_h = (self.canvas.canvas.figure_image[0].shape[0],
                        self.canvas.canvas.figure_image[0].shape[1])
        canvas_h, canvas_w = self.canvas.canvas.GetSize()
        if bmp_h != canvas_h or bmp_w != canvas_w:
            self.deffered_force_layout()

        f_page = self.get_page(ipage)
        ifigure.events.SendPageShownEvent(f_page)

    def onTD_RangeChanged(self, evt):
        pass

    def onTD_OpenBook(self, evt):
        pass

    def onTD_CloseBook(self, evt):
        pass

    def onTD_FileChanged(self, evt):
        pass

    def onTD_IAxesSelection(self, evt):
        self.canvas.i_axesselection(evt.callback, evt.figaxes)

    def onCloseDeleteBook(self, evt=None):
        self._del_book_from_proj = 1
        self.Close()

    def onClose(self, evt=None):
        self._del_book_from_proj = 2
        self.Close()

    def viewer_canvasmenu(self):
        return []

    def append_undoredo_menu(self, editmenu):
        undo_mi = self.add_menu(editmenu, wx.ID_UNDO,
                                "Can't undo", "Undo previous edit to figure",
                                self.onUndo)
        redo_mi = self.add_menu(editmenu, wx.ID_REDO,
                                "Can't redo", "Redo an edit to figure",
                                self.onRedo)
        self.append_accelerator_table((wx.ACCEL_CTRL,  ord('Z'), wx.ID_UNDO))
        self.append_accelerator_table((wx.ACCEL_CTRL | wx.ACCEL_SHIFT,  ord('Z'),
                                       wx.ID_REDO))
        self.history.set_undo_redo_menu_item(undo_mi, redo_mi)
        self.history.update_menu_item()

#        self.append_accelerator_table((wx.ACCEL_NORMAL,  wx.WXK_F2, wx.ID_BACKWARD))
#        self.append_accelerator_table((wx.ACCEL_NORMAL,  wx.WXK_F1, wx.ID_FORWARD))

    def onUndo(self, e):
        ifigure.events.SendUndoEvent(self.book, w=self)

    def onRedo(self, e):
        ifigure.events.SendRedoEvent(self.book, w=self)

    def set_status_text(self, txt, timeout=1000):
        sb = self.GetStatusBar()
        if sb is None:
            return

        def reset_status_text(self, top=self):
            top.Unbind(wx.EVT_TIMER)
            if top is not None:
                top.SetStatusText('')

        self.SetStatusText(txt)
        if timeout is not None:
            self.Bind(wx.EVT_TIMER, reset_status_text)
            self._sb_timer.Start(timeout, oneShot=True)

    def save_animgif(self, filename='animation.gif',
                     show_page=None, duration=None, dither=None, pages='all'):
        if show_page is None:
            def show_page(args):
                import wx
                import time
                k = args[0]
                book = args[1]
                book.show_page(k)
                book.draw()
                time.sleep(0.01)

        if dither is not None:
            import warnings
            warnings.warn(
                "dither is deprecated. not used anymore.", FutureWarning)

        if duration is None:
            from ifigure.utils.edit_list import DialogEditList
            l = [["Frame Speed(s/frame)", str(0.5),  0, {'noexpand': True}], ]

            value = DialogEditList(l, parent=self,
                                   title="GIF animation...",
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
            if not value[0]:
                return

            duration = float(value[1][0])

        pages = range(self.num_page()) if pages == 'all' else pages
        param = [(k, self) for k in pages]

        from ifigure.utils.gif_animation import save_animation
        print('saveing gif animation...'+filename)

        save_animation(show_page, param, self.canvas, filename=filename,
                       duration=duration)

    def save_animpng(self, filename='animation.png', show_page=None,
                     duration=None, pages='all'):
        if show_page is None:
            def show_page(args):
                import wx
                import time
                k = args[0]
                book = args[1]
                book.show_page(k)
                book.draw()
                time.sleep(0.01)

        if duration is None:
            from ifigure.utils.edit_list import DialogEditList
            l = [["Frame Speed(s/frame)", str(0.5), 0, {'noexpand': True}],
                 ]
            value = DialogEditList(l, parent=self,
                                   title="PNG animation...",
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
            if not value[0]:
                return
            duration = float(value[1][0])*1000.

        pages = range(self.num_page()) if pages == 'all' else pages
        param = [(k, self) for k in pages]

        from ifigure.utils.png_animation import save_animation
        print('saveing png animation...'+filename)
        save_animation(show_page, param, self.canvas,
                       filename=filename, duration=duration)

    def save_multipdf(self, filename='figure_allpage.pdf',
                      show_page=None):
        if show_page is None:
            def show_page(*args):
                import wx
                import time
                k = args[0]
                self.show_page(k)
                self.draw()
                time.sleep(0.01)

        param = []
        ret0 = '.'.join(filename.split('.')[:-1])

        from PyPDF2 import PdfFileReader, PdfFileWriter

        output = PdfFileWriter()
        image_dpi = wx.GetApp().TopWindow.aconfig.setting['image_dpi']

        from ifigure.matplotlib_mod.mpl_utils import call_savefig_method

        for k in range(self.num_page()):
            #print('printing page: ' + str(k))
            show_page(k)
            self.draw()
            name = ret0+'_'+str(k)+'.pdf'
            call_savefig_method(self.canvas, 'print_pdf', name, dpi=image_dpi)

            page = PdfFileReader(name)
            output.addPage(page.getPage(0))

        with open(filename, 'wb') as output_stream:
            output.write(output_stream)

        for k in range(self.num_page()):
            #print("removing", ret0+'_'+str(k)+'.pdf')
            os.remove(ret0+'_'+str(k)+'.pdf')

    def isPropShown(self):
        pe = self.property_editor
        return self.gui_tree.get_toggle(pe)

    def isPanel1Shown(self):
        pe = self.panel1
        return self.gui_tree.get_toggle(pe)

    def toggle_property(self):
        pe = self.property_editor

        if self.isPanel1Shown():
            '''
            when showing panel, it issues an event so that
            the information shown on panels are
            properly updated
            '''
            self.gui_tree.toggle_panel(pe, not self.isPropShown())
            if len(self.canvas.selection) == 1:
                if self.canvas.selection[0]() is not None:
                    td = self.canvas.selection[0]().figobj
                    ifigure.events.SendSelectionEvent(td, self.canvas,
                                                      self.canvas.selection)
            else:
                if self.canvas.axes_selection() is None:
                    if self.isec() != -1:
                        ax = self.get_axes(iaxes=self.isec())
                        self.canvas.set_axes_selection(ax._artists[0])
                if self.canvas.axes_selection() is not None:
                    ifigure.events.SendSelectionEvent(self.canvas.axes_selection().figobj,
                                                      self.canvas,
                                                      self.canvas.selection)
                else:
                    figure = self.canvas.get_figure()
                    ifigure.events.SendSelectionEvent(figure.figobj,
                                                      self.canvas,
                                                      self.canvas.selection)
#        wx.CallAfter(self.canvas.draw_later)

    def add_closemenu(self, filemenu):
        self.add_menu(filemenu, wx.ID_ANY,
                      "Close", "Close window",
                      self.onClose)
#        self.add_menu(filemenu, wx.ID_ANY,
#                     "Close + Delete Book", "Close window and delete book data",
#                      self.onCloseDeleteBook)
        self.Bind(wx.EVT_CLOSE, self.onWindowClose)

    def add_quitemenu(self, filemenu):
        self.add_menu(filemenu, wx.ID_ANY,
                      "Quit piScope", " Terminate the program",
                      self.onQuit)

    def onQuit(self, evt=None):
        wx.GetApp().TopWindow.Close()

    def onWindowClose(self, evt=None):
        # print("onWindowClose", self)
        # stop timer for statusbar
        self._sb_timer.Stop()
        self.Unbind(wx.EVT_TIMER)

        bk = self.book
        self.close_book()

        ifigure.events.SendCloseBookEvent(bk, w=self)
        if ((bk is not None and not bk._keep_data_in_tree) or
                (self._del_book_from_proj == 1 and bk is not None)):
            if not self._attaching:
                ifigure.events.SendPVDeleteFigobj(bk)
            self._attaching = False
        if evt is not None:
            if not evt.CanVeto():
                self.Destroy()
            evt.Skip()

        self.canvas.close()

#    def close_figurebook(self):
#        self.onWindowClose()
    def install_toolbar_palette(self, name, tasks,  mode='2D', refresh=None):
        self.canvas.install_toolbar_palette(name, tasks,  mode, refresh)

    def use_toolbar_palette(self, name, mode='2D'):
        self.canvas.use_toolbar_palette(name, mode)

    def use_toolbar_std_palette(self):
        self.canvas.use_toolbar_std_palette()

    def refresh_toolbar_buttons(self):
        self.canvas.toolbar.refresh_palette()

    def set_hl_color(self, value):
        assert len(value) == 3,  "Highlight color should be RGB (lenght = 3)"
        self.canvas.hl_color = tuple(value)


class BookViewer(BookViewerFrame):
    def __init__(self, *args, **kargs):
        parent = args[0]
        title = args[2]
        gl = kargs.pop('gl', False)
        if gl:
            ifigure_canvas.turn_on_gl = gl
        kargs["style"] = (wx.CAPTION |
                          wx.CLOSE_BOX |
                          wx.MINIMIZE_BOX |
                          wx.MAXIMIZE_BOX |
                          wx.RESIZE_BORDER)
        # |wx.FRAME_FLOAT_ON_PARENT)
        if "show_prop" in kargs:
            show_prop = kargs["show_prop"]
            del kargs["show_prop"]
        else:
            show_prop = False
        if "hide_window" in kargs:
            hide_window = kargs["hide_window"]
            del kargs["hide_window"]
        else:
            hide_window = False

        # this is added not to have windows "always on parent"
        args2 = [x for x in args]
        #args2[0] = None
        args = tuple(args2)
        ###
        super(BookViewer, self).__init__(*args, **kargs)

        self.threadlist = []
#        panel = wx.Panel(self)
        self.timer = None
        self.ipage = 0

        self.InitUI(parent, title, show_prop, hide_window)
        self.BindTreeDictEvents()
#        self.Thaw()
        self.property_editor.set_sizehint()
        self.update_exportas_menu()
        self.adjust_frame_size()
        self.SetPosition((50, 50))
        self.nobookdelete = False

        self.SetMenuBar(self.menuBar)

    def InitUI(self, parent, title, show_prop, hide_window=False):
        # A Statusbar in the bottom of the window
        self.sb = StatusBarSimple(self)
        self.SetStatusBar(self.sb)

        # define splitter panel tree

        # valid panel p1, p22, p121, p122
        self.gui_tree = PanelCheckbox(self, wx.HORIZONTAL)
#        p1, p2 = self.gui_tree.add_splitter('v', 'h')

        # make all panels
        self.panel1 = self.gui_tree.add_panel(wx.Panel,
                                              "Figure", "Figure", 0)
        self.gui_tree.set_primary(self.panel1)
        self.gui_tree.hide_toggle_menu(self.panel1)
        self.property_editor = self.gui_tree.add_panel(property_editor,
                                                       "Property", "Property",
                                                       1, 'r', 0, wx.ALL | wx.EXPAND, 0)

        #
        self.canvas = None
        self._rebuild_ifigure_canvas()
        self._link_canvas_property_editor()
        self.gui_tree.primary_client(self.canvas)
        # File Menu
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "New Figure", "Create Book",
                      self.onNewBook)
        openmenu = wx.Menu()
        self.filemenu.AppendSubMenu(openmenu, 'Open')
        #menu_Append(self.filemenu, wx.ID_ANY, 'Open', openmenu)
        self.add_menu(openmenu, wx.ID_OPEN,
                      "Book...",
                      "Import Book file (.bfz). Current book is deleted from project",
                      self.onLoadBook)
        self.add_menu(openmenu, wx.ID_ANY,
                      "Book in new window...",
                      "Import Book file (.bfz), New book data will be added to project",
                      self.onLoadBookNew)
        self.filemenu.AppendSeparator()
        self.append_save_project_menu(self.filemenu)
        exportmenu = wx.Menu()
        self.filemenu.AppendSubMenu(exportmenu, 'Export...')
        #menu_Append(self.filemenu, wx.ID_ANY, 'Export...', exportmenu)
        self.export_book_menu = self.add_menu(exportmenu,
                                              BookViewerFrame.ID_EXPORTBOOK,
                                              "Export Book", "Export Book",
                                              self.onExportBook)
        self.add_menu(exportmenu, BookViewerFrame.ID_EXPORTBOOK_AS,
                      "Export Book As...", "Export Book",
                      self.onExportBookAs)
        self.add_saveimage_menu(exportmenu)
        self.add_exporthdf_menu(exportmenu)
        self.filemenu.AppendSeparator()
        self.add_menu(self.filemenu, wx.ID_ANY,
                      "Preference...", "Piescope preference...",
                      self.onAppPreference)
        self.filemenu.AppendSeparator()
        self.add_closemenu(self.filemenu)
        self.add_quitemenu(self.filemenu)
        self.add_std_plotmenu(self.plotmenu)

        # help menu
        self.append_help_menu()

        # Edit Menu
        self.append_undoredo_menu(self.editmenu)
        self.editmenu.AppendSeparator()
        self.add_cutpaste_menu(self.editmenu)

        self.gui_tree.append_menu(self.viewmenu)
        self.viewmenu.AppendSeparator()
        self.gui_tree.update_check()
        self.gui_tree.bind_handler(self)

#        if property_editor.screen_width is not None:
#           self.gui_tree.set_showhide([True, False])
        self.gui_tree.set_splitters()

        self.editmenu.AppendSeparator()
        self.add_bookmenus(self.editmenu, self.viewmenu)

        # add full screen to view menu

        if self.isattachable:
            self.viewmenu.AppendSeparator()
            self._attach_menu = self.add_menu(self.viewmenu, wx.ID_ANY,
                                              "Attach to MainWindow",
                                              "close thie figure window and show the same book in main app window",
                                              self.onAttachFigure)
            self.adjust_attach_menu()
        self.viewmenu.AppendSeparator()
        self.add_menu(self.viewmenu, wx.ID_ANY,
                      "Full Screen", "switch to full screen mode",
                      self.onFullScreen2)
        self.add_menu(self.viewmenu, wx.ID_ANY,
                      "Full Screen (No Toolbar)", "switch to full screen mode",
                      self.onFullScreen)
        self.append_screen_ratio_menu(self.viewmenu)
        self.append_std_viewmenu2(self.viewmenu)
        # Adding the MenuBar to the Frame content.

        # self.property_editor.set_sizehint()
        self.gui_tree.toggle_panel(self.property_editor, show_prop)

        self.SetSize([400, 300])
        self.Layout()
        self.set_accelerator_table()
        if not hide_window:
            self.Show(True)

        # self.deffered_force_layout()

    def set_window_title(self):
        super(BookViewer, self).set_window_title()
        if self.book is None:
            return
        title = self.GetTitle()
        name = self.book.getvar('original_filename')
        if name is None:
            name = self.book.name
        else:
            name = os.path.basename(name)
        title = ':'.join([name, title])
        self.SetTitle(title)

    def onNewBook(self, evt, veiwer=None):
        super(BookViewer, self).onNewBook(evt,
                                          viewer=BookViewer)

    def onExportBook(self, evt):
        self.onSaveBook(evt)

    def onExportBookAs(self, evt):
        self.onSaveBookAs(evt)

    def onLoadBookNew(self, evt):
        #        from ifigure.widgets.book_viewer import BookViewer
        super(BookViewer, self).onLoadBookNew(evt,
                                              viewer=BookViewer)

    def onFullScreen2(self, evt=None, value=True):
        self.onFullScreen(evt=evt, value=value, no_toolbar=False)

    def onFullScreen(self, evt=None, value=True, no_toolbar=True):
        if value:
            if self.isPropShown():
                self.toggle_property()

            # this is to support multiple screen
            from ifigure.utils.cbook import get_current_display_size
            x0, y0, xd, yd = get_current_display_size(self)
            xc, yc = self.canvas.canvas.bitmap.GetSize()
            ratio = min([float(xd)/float(xc), float(yd)/float(yc)])
            for p in self.book.walk_page():
                p.set_figure_dpi(int(p.getp('dpi')*ratio))

            w = xd
            h = yd
            if (xd - xc*ratio) > 4:
                w = int((xd - xc*ratio)/2)
                self.canvas.show_spacer(w=w, h=h,
                                        direction=wx.HORIZONTAL)
            elif (yd - yc*ratio) > 4:
                h = int((yd - yc*ratio)/2)
                self.canvas.show_spacer(w=w, h=h,
                                        direction=wx.VERTICAL)
            else:
                self.canvas.show_spacer(w=-1, h=-1,
                                        direction=None)

            if no_toolbar:
                self.canvas.full_screen(True)
            self.ShowFullScreen(True)
            self.canvas.turn_on_key_press()
        else:
            for p in self.book.walk_page():
                p.set_figure_dpi(p.getp('dpi'))
            self.canvas.hide_spacer()
            self.canvas.full_screen(False)
            self.canvas.turn_off_key_press()
            self.ShowFullScreen(False)

    def onTD_ShowPage(self, evt):
        if not evt.BookViewerFrame_Processed:
            super(BookViewer, self).onTD_ShowPage(evt)
            evt.BookViewerFrame_Processed = True
            evt.SetEventObject(self)
        evt.Skip()
#    def onClose(self, e=None):
#        self.nobookdelete=True
#        self.Close()

    def attach_to_main(self):
        '''
        attach to main window. it closes if a figure is
        already open in the main window
        '''
        self.onAttachFigure(None)
        w = wx.GetApp().TopWindow
        return w

    def onAttachFigure(self, e):
        w = wx.GetApp().TopWindow
        book = self.book
        ipage = self.ipage
        aviewer = w.aviewer
        self._attaching = True
        self.onClose(e)
        w.open_book_in_appwindow(book, ipage=ipage)
        w.canvas.draw_all()
        if aviewer is self:
            w.aviewer = w

    def adjust_attach_menu(self):
        if not self.isattachable:
            return
        w = wx.GetApp().TopWindow
        if w.book is None:
            self._attach_menu.Enable(True)
        else:
            self._attach_menu.Enable(False)
