from __future__ import print_function

import wx
import sys
import six
import os
import weakref
import threading
import time
import traceback

from ifigure.utils.wx3to4 import tree_InsertItemBefore, wxNamedColour, tree_GetItemData, tree_SetItemData

import ifigure.utils.debug as debug
from ifigure.widgets.command_history import CommandHistory
from ifigure.widgets.textctrl_trunc import TextCtrlTrunc
from ifigure.widgets.consol import Consol
import ifigure.widgets.dialog as dialog
import ifigure.events
from ifigure.mto.py_contents import PyContents
from ifigure.mto.fig_page import FigPage
from ifigure.mto.py_module import PyModule
from ifigure.mto.py_script import PyScript
from ifigure.mto.treedict import TreeDict
from ifigure.mto.fig_obj import FigObj
from ifigure.utils.edit_list import EditListPanel
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from ifigure.widgets.shellvar_viewer import ShellVarViewer, ShellVarViewerDropTarget
from ifigure.widgets.var_viewerg2 import VarViewerG, VarViewerGDropTarget
from ifigure.utils.cbook import ImageFiles, Write2Main, BuildPopUpMenu

use_agw = False
if use_agw:
    import wx.lib.agw.aui as aui
else:
    import wx.aui as aui


dprint1, dprint2, dprint3 = debug.init_dprints('ProjTreeViewerAUI')


class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1,
                             style=wx.LC_REPORT | wx.LC_EDIT_LABELS)
        ListCtrlAutoWidthMixin.__init__(self)


class Message(object):
    pass


class TextCtrlPath(TextCtrlTrunc):
    def onKeyPressed(self, evt):
        self.pv._search_mode = True
        key = evt.GetKeyCode()
        if self.pv._search_mode:
            if key == wx.WXK_DOWN:
                wx.CallAfter(self.pv.search_td_down)
                return
            elif key == wx.WXK_UP:
                wx.CallAfter(self.pv.search_td_up)
                return
            elif key == wx.WXK_RETURN:
                wx.CallAfter(self.pv.exit_search_mode)
                return

        if 0 < key < 255:
            self._mode = 'through'
            wx.CallAfter(self.pv.search_td)
        TextCtrlTrunc.onKeyPressed(self, evt)
#        evt.Skip()

    def onKillFocus(self, evt):
        TextCtrlTrunc.onKillFocus(self, evt)
        wx.CallAfter(self.pv.exit_search_mode)


class ProjViewerDropTarget(wx.TextDropTarget):
    # obj is proj_viewer

    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj
        self.timer = wx.Timer(self.obj.tree, wx.ID_ANY)
        self._prev_item = None
        self._prev_dict = None
        self._timer_on = False
        self._motion_on = False
        self._item_at_start = None
        self._item_at_starte = None

    def OnTime(self, e):
        #        print "timer"

        x, y = self.obj.tree.ScreenToClient(wx.GetMousePosition())
        size = self.obj.tree.GetSize()
        if y < 0:
            self.ScrollUp()
            if y < -10:
                self.StopTimer()
            return
        elif y > size[1]:
            self.ScrollDown()
            if y > size[1]+10:
                self.StopTimer()
            return

        self._timer_on = False
        if self._item_at_start is not None:
            # collapse this item
            # print "collapse"
            self.obj.tree.Collapse(self._item_at_start)
        if self._item_at_starte is not None:
            # collapse this item
            # print "expand"
            self.obj.tree.Expand(self._item_at_starte)
        self._item_at_start = None
        self._item_at_starte = None

    def OnDragOver(self, x, y, default):
        item, flag = self.obj.tree.HitTest((x, y))

#        dictobj= self.obj.tree.GetPyData(item)
#        print item, dictobj, flag & wx.TREE_HITTEST_ABOVE, flag & wx.TREE_HITTEST_BELOW

#        print flag & wx.TREE_HITTEST_ONITEMLABEL
        if ((flag & wx.TREE_HITTEST_ONITEMINDENT) or
            (flag & wx.TREE_HITTEST_ONITEMBUTTON) or
                (flag & wx.TREE_HITTEST_TOLEFT)):
            if self._timer_on == False:
                self.obj.tree.Bind(wx.EVT_TIMER, self.OnTime)
#              if not hasattr(self, 'timer'):
#                 self.timer = wx.Timer(self.obj.tree, wx.ID_ANY)
                self.timer.Start(100)
                self._timer_on = True
                self._item_at_start = item
        else:
            # cancel action
            self._item_at_start = None

        if flag & wx.TREE_HITTEST_ONITEMLABEL:
            dictobj = self.obj.tree.GetPyData(item)
            if not isinstance(dictobj, TreeDict):
                return
            if self._prev_item is not None:
                self.obj.tree.SetItemDropHighlight(self._prev_item, False)
            self.obj.tree.SetItemDropHighlight(item)
            if self._prev_dict != dictobj:
                self.obj.varviewer.fill_list(dictobj)
            self._prev_item = item
            self._prev_dict = dictobj
            if self._timer_on == False:
                self.obj.tree.Bind(wx.EVT_TIMER, self.OnTime)
#              if not hasattr(self, 'timer'):
#                 self.timer = wx.Timer(self.obj.tree, wx.ID_ANY)
                self.timer.Start(100)
                self._timer_on = True
                self._item_at_starte = item

        else:
            pass

        return default

    def OnLeave(self):
        if self._prev_item is not None:
            self.obj.tree.SetItemDropHighlight(self._prev_item, False)

    def OnEnter(self, x, y, default):
        if self._motion_on == False:
            #          self.obj.tree.Bind(wx.EVT_MOTION, self.OnMotion)
            pass

        self._motion_on = True
        return default

    def StopTimer(self):
        dprint1("stop timer")
        if self.timer is not None:
            self.timer.Stop()
#           del self.timer
        self._prev_item = None
        self._prev_dict = None
        self._timer_on = False
        self._motion_on = False
        self._item_at_start = None
        self._item_at_starte = None

    def OnDropText(self, x, y, data):
        self.StopTimer()
        try:
            app = self.obj.tree.GetTopLevelParent()
            data = app._text_clip
            app._text_clip = ''

        except Exception:
            print("error in processing dnd in wx.tree")
            return False
        if self._prev_item is not None:
            self.obj.tree.SetItemDropHighlight(self._prev_item, False)
        self._prev_item = None
        data = str(data)
        return True

    def ScrollUp(self):
        if "wxMSW" in wx.PlatformInfo:
            self.obj.tree.ScrollLines(-1)
        else:
            first = self.obj.tree.GetFirstVisibleItem()
            prev = self.obj.tree.GetPrevSibling(first)
            if prev:
                # drill down to find last expanded child
                while self.obj.tree.IsExpanded(prev):
                    prev = self.obj.tree.GetLastChild(prev)
            else:
                # if no previous sub then try the parent
                prev = self.obj.tree.GetItemParent(first)

            if prev:
                self.obj.tree.ScrollTo(prev)
            else:
                self.obj.tree.EnsureVisible(first)

    def ScrollDown(self):
        if "wxMSW" in wx.PlatformInfo:
            self.obj.tree.ScrollLines(1)
        else:
            # first find last visible item by starting with the first
            next = None
            last = None
            item = self.obj.tree.GetFirstVisibleItem()
            while item:
                if not self.obj.tree.IsVisible(item):
                    break
                last = item
                item = self.obj.tree.GetNextVisible(item)

            # figure out what the next visible item should be,
            # either the first child, the next sibling, or the
            # parent's sibling
            if last:
                if self.obj.tree.IsExpanded(last):
                    next = self.obj.tree.GetFirstChild(last)[0]
                else:
                    next = self.obj.tree.GetNextSibling(last)
                    if not next:
                        prnt = self.obj.tree.GetItemParent(last)
                        if prnt:
                            next = self.obj.tree.GetNextSibling(prnt)

            if next:
                self.obj.tree.ScrollTo(next)
            elif last:
                self.obj.tree.EnsureVisible(last)


class ProjTreeViewerPopUp(wx.Menu):
    def __init__(self, parent, dictobj):
        super(ProjTreeViewerPopUp, self).__init__()
        self.parent = parent
        menus = dictobj.tree_viewer_menu()
        if not hasattr(dictobj, '_var0'):
            BuildPopUpMenu(self, menus, eventobj=parent)
            return
        if not isinstance(dictobj._var0, PyContents):
            item = parent.tree.GetSelection()
#            if parent.tree.IsExpanded(item):
#               menus=menus+[('---', None, None),
#                        ('Collapse All', self.onCollapseChild, None),
#                        ('Copy Path', self.onCopyPath, None),
#                        ('Refresh', self.onRefresh, None)]
#            else:
            menus = menus+[('---', None, None),
                           ('Expand All', self.onExpandChild, None),
                           ('Copy Path', self.onCopyPath, None),
                           ('+Move...', None, None),
                           ('Up',   self.onMoveUp, None),
                           ('Down', self.onMoveDown, None), ]
            if dictobj.num_child() != 0:
                menus = menus + [
                    ('Sort Children (up)', self.onSortUp, None),
                    ('Sort Children (down)', self.onSortDown, None), ]
            menus = menus + [
                ('!', None, None),
                #                        ('Move...', self.onMove, None),
                ('Refresh widget', self.onRefresh, None)]

        else:
            if dictobj._var0_show:
                menus = menus+[('---', None, None),
                               ('Hide Contents', self.onHideContents, None),
                               ('Copy Path', self.onCopyPath, None),
                               ('Refresh widget', self.onRefresh, None)]
            else:
                menus = menus+[('---', None, None),
                               ('Show Contents', self.onShowContents, None),
                               ('Copy Path', self.onCopyPath, None),
                               ('Refresh widget', self.onRefresh, None)]

        BuildPopUpMenu(self, menus, eventobj=parent)
        return

    def onRefresh(self, e):
        self.parent.update_widget()

    def onExpandChild(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        tv.tree.ExpandAllChildren(item)

    def onCollapseChild(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        tv.tree.CollapseAllChildren(item)

    def onMove(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        data = tv.tree.GetPyData(item)
        if not isinstance(data, TreeDict):
            return
        tv._move_mode = True

    def onMoveUp(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        data = tv.tree.GetPyData(item)
        if not isinstance(data, TreeDict):
            return
        if data._parent is None:
            return
        data._parent.move_child(data.get_ichild(),
                                max([0, data.get_ichild()-1]))
        tv.update_widget()

    def onSortUp(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        td = tv.tree.GetPyData(item)
        if not isinstance(td, TreeDict):
            return
        td.sort_children_up()
        tv.update_widget()

    def onSortDown(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        td = tv.tree.GetPyData(item)
        if not isinstance(td, TreeDict):
            return
        td.sort_children_down()
        tv.update_widget()

    def onMoveDown(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        data = tv.tree.GetPyData(item)
        if not isinstance(data, TreeDict):
            return
        if data._parent is None:
            return
        data._parent.move_child(data.get_ichild(),
                                min([data._parent.num_child()-1, data.get_ichild()+1]))
        tv.update_widget()

    def onCopyPath(self, e):
        '''
        '''
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        data = tv.tree.GetPyData(item)
        if isinstance(data, TreeDict):
            tx = str(data.get_full_path())
        else:
            tx = str(data[0]._var0.get_drag_text1(data))

        if not wx.TheClipboard.IsOpened():
            wx.TheClipboard.Open()
            data = wx.TextDataObject()
            data.SetText(tx)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()

    def onShowContents(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        dictobj = tv.tree.GetPyData(item)
        tv.show_contents(dictobj, item)

    def onHideContents(self, e):
        tv = e.GetEventObject()
        item = tv.tree.GetSelection()
        dictobj = tv.tree.GetPyData(item)
        tv.hide_contents(dictobj, item)


class TreeCtrl(wx.TreeCtrl):
    def OnCompareItems(self, item1, item2):
        t1 = self.GetPyData(item1)
        t2 = self.GetPyData(item2)
        if isinstance(t1, TreeDict):
            try:
                return (t1.get_parent().i_child(t1) -
                        t2.get_parent().i_child(t2))
            except:
                print((t1, t2))
                return False
        else:
            return t1[2].OnCompareItems(t1, t2)

    def GetPyData(self, *args):
        try:
            o = super(self.__class__, self)
            val = tree_GetItemData(o, *args)
            return val
        except:
            return None

    def SetPyData(self, *args, **kwargs):
        o = super(self.__class__, self)
        return tree_SetItemData(o, *args, **kwargs)


#    def SelectItem(self, *args, **kargs):
#        wx.TreeCtrl.SelectItem(self, *args, **kargs)
#        print 'Selcting', args
#        traceback.print_stack()
if use_agw:
    class myAgwAuiNotebook(wx.lib.agw.aui.AuiNotebook):
        def OnTabBeginDrag(self, evt):
            #        self.CaptureMouse()
            super(myAgwAuiNotebook, self).OnTabBeginDrag(evt)
            evt.Skip()

        def OnTabEndDrag(self, evt):
            self.CaptureMouse()
            super(myAgwAuiNotebook, self).OnTabEndDrag(evt)
            evt.Skip()


class ProjTreeViewer(wx.Panel):

    def __init__(self, parent=None):
        """Constructor"""

        super(ProjTreeViewer, self).__init__(parent)
        self._drag_start = False
        self._update_request = False
        self._last_updage = 0
        self._search_txt = ''
        self._search_mode = False
        self.panel = None

#        sizer=wx.BoxSizer(wx.VERTICAL)
#        self.SetSizer(sizer)
#        self.splitter=wx.SplitterWindow(self)
#        sizer.Add(self.splitter, 1, wx.EXPAND)

        if use_agw:
            self.nb = myAgwAuiNotebook(self, style=aui.AUI_NB_TAB_SPLIT |
                                       aui.AUI_NB_TAB_MOVE |
                                       aui.AUI_NB_TAB_FLOAT |
                                       aui.AUI_NB_SCROLL_BUTTONS |
                                       aui.AUI_NB_TAB_EXTERNAL_MOVE)
        else:
            self.nb = aui.AuiNotebook(self, style=aui.AUI_NB_TAB_SPLIT |
                                      aui.AUI_NB_TAB_MOVE |
                                      aui.AUI_NB_SCROLL_BUTTONS)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # panel1 (tree)
        p = wx.Panel(self.nb)
        p.SetBackgroundColour(wxNamedColour('White'))
        p.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self._move_mode = False
        self.tree = TreeCtrl(p, wx.ID_ANY,
                             wx.DefaultPosition, (1, 1),
                             wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        p.GetSizer().Add(self.tree, 1, wx.EXPAND)
        self.nb.AddPage(p, 'Project Tree')
        self.tree.parent = self.nb
        self.dt1 = ProjViewerDropTarget(self)
        self.tree.SetDropTarget(self.dt1)

        im = ImageFiles()
        self.tree.SetIndent(16)
        self.tree.SetImageList(im.get_imagelist())

        # panel1 (bottons)
        bottom = wx.BoxSizer(wx.HORIZONTAL)
        # self.bt_panel.SetSizer(bottom)

        modes = ['expand', 'copy', 'paste', 'text', 'trash']
        self.buttons = [None]*len(modes)
        for kk, mode in enumerate(modes):
            if mode == 'text':
                self.tc_path = TextCtrlPath(p, wx.ID_ANY, '')
                self.tc_path.pv = self
#              self.tc_path.Bind(wx.EVT_KEY_DOWN, self.onKeyPressed, self.tc_path)
                bottom.Add(self.tc_path, 1, wx.EXPAND | wx.ALL, 1)
            else:
                from ifigure.ifigure_config import icondir
                path = os.path.join(icondir, '16x16', mode+'.png')
                image = wx.Image(path, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
                bt = wx.BitmapButton(p, -1, image)
                bt.SetToolTip(wx.ToolTip(mode))
                if mode == 'trash':
                    #                 bottom.AddStretchSpacer()
                    bottom.Add(bt, 0)
                else:
                    bottom.Add(bt, 0)
                self.buttons[kk] = bt
                def func(e, mode=mode): return self.OnButton(e, mode)
                self.Bind(wx.EVT_BUTTON, func, bt)
        p.GetSizer().Add(bottom, 0, wx.EXPAND)

#        sizer.Add(self.tree, 1, wx.EXPAND)

        # panel2 (variable viewer)
        # panel2-2 (shell variable viewer)
        self.varviewer = VarViewerG(self.nb)
        self.svarviewer = ShellVarViewer(self.nb)
        dt2 = VarViewerGDropTarget(self)
        self.varviewer.SetDropTarget(dt2)
        self.nb.AddPage(self.varviewer, 'Tree Variables')
        self.nb.AddPage(self.svarviewer, 'Shell Variables')

        wx.CallAfter(self.nb.Split, 0, wx.TOP)
        # panel3 (consol)

        self.consol = Consol(self.nb)
        self.log = self.consol.log
        self.ch = CommandHistory(self.nb)

        top = self.GetTopLevelParent()
#        top.redirector.add(threading.current_thread(),
#                                 self.log.AppendText)

        self.nb.AddPage(self.consol, 'Console')
        self.nb.AddPage(self.ch, 'History')

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING,
                  self.OnExpandItem)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING,
                  self.OnCollapseItem)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK,
                  self.OnItemRightClick)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED,
                  self.OnItemActivated)
        self.Bind(wx.EVT_TREE_SEL_CHANGED,
                  self.OnSelChanged)
        self.Bind(wx.EVT_TREE_SEL_CHANGING,
                  self.OnSelChanging)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG,
                  self.OnBeginDrag)
        self.Bind(wx.EVT_TREE_END_DRAG,
                  self.OnEndDrag)
        self.Bind(wx.EVT_MENU, self.OnMenu)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.OnKeyDown)
#        self.tree.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus, self.tree)
#        self.tree.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus, self.tree)

        top = self.tree.GetTopLevelParent()
        top.Bind(wx.EVT_MOUSE_CAPTURE_LOST, lambda x: None)

        self._first_click = False
        self.timer = wx.Timer(self, wx.ID_ANY)

    def onKeyPressed(self, evetn):
        print('process at viewer')
#    def init_sash_pos(self):
#        return
#        #self.splitter.SetSashPosition(200)

    def get_command_history(self):
        return self.ch

    def get_shellvar_viewer(self):
        return self.svarviewer

    def get_var_viewer(self):
        return self.varviewer

    def get_proj(self):
        app = self.GetTopLevelParent()
        return app.proj

    def update_widget_request(self, delay=3000, no_set_selection=False):
        if not self._update_request:
            wx.CallLater(int(delay), self.update_widget0,
                         no_set_selection=no_set_selection)
            self._update_request = True

    def update_widget_request2(self, time=0, no_set_selection=False):
        #        print  self._last_update,  time, self._update_request
        if (self._last_update < time):
            self.update_widget(no_set_selection=no_set_selection)

    def update_widget(self, no_set_selection=False):
        if not self._update_request:
            self.update_widget0(no_set_selection=no_set_selection)

    def update_widget0(self, no_set_selection=False):
        self._update_request = False
        sel = self.tree.GetSelection()
        if sel is not None:
            sdict = self.tree.GetPyData(sel)
        else:
            sdict = None

        proj = self.get_proj()
        if proj is None:
            self.tree.DeleteAllItems()
            return
        if (isinstance(sdict, TreeDict) and
                proj.is_descendant(sdict)):
            sdict2 = proj
        else:
            sdict2 = proj  # default select proj

        t0 = time.time()
        croot = self.tree.GetRootItem()
        if self.tree.GetPyData(croot) is None:
            self.tree.DeleteAllItems()
            croot = self.tree.AddRoot(proj.name)
            self.tree.SetPyData(croot,  self.get_proj())

#        print time.time()-t0; t0=time.time()
        #
        #  remove item from tree viewer
        #
        while self.remove_item_from_tree():
            pass
        self.rearrange_item()
#        print time.time()-t0; t0=time.time()
        #
        #  add item to tree viewer
        #
        while self.add_item_to_tree():
            pass
#        print time.time()-t0; t0=time.time()
        #
        #  refresh tree name...
        #
        sdict_found = False
        for item in self.walk_treectrl(croot):
            treedict = self.tree.GetPyData(item)
            if treedict is sdict:
                sdict_found = True
            if not isinstance(treedict, TreeDict):
                continue
            name = treedict.name if treedict._genuine_name == '' else treedict._genuine_name
            if treedict.isTreeLink():
                l = treedict.get_linkobj()
                if l is not None:
                    if l.name == name:
                        name = '-> ' + l.name
                    else:
                        name = name + '-> ' + l.name
                else:
                    name = name + '-> None'
            from ifigure.mto.hg_support import HGSupport, has_repo
            if has_repo(treedict) and isinstance(treedict, HGSupport):
                name = name + treedict.hg_projtreeviewer_status()

            if treedict.status != '':
                label = name+' ('+treedict.status+')'
            else:
                label = name
                if treedict.get_auto_status_str() != '':
                    label = label + ' (' + treedict.get_auto_status_str() + ')'
#               label = name
            olabel = self.tree.GetItemText(item)
            if olabel != label:
                self.tree.SetItemText(item, label)
            if not treedict._image_update:
                img = treedict.get_classimage()
                self.tree.SetItemImage(item, img)
                treedict._image_update = True
            if treedict.is_suppress():
                self.tree.SetItemTextColour(item,
                                            wxNamedColour('Grey'))
            else:
                self.tree.SetItemTextColour(item,
                                            wxNamedColour('Black'))

#        print time.time()-t0; t0=time.time()
#        print sdict.get_full_path()
        if not sdict_found:
            sdict = sdict2

        if not no_set_selection:
            wx.CallAfter(self.set_td_selection, sdict)
#        if isinstance(sdict, TreeDict):
#            self.varviewer.fill_list(sdict)
#        else:
#            self.varviewer.fill_list(sdict[2])
        self._last_update = time.time()
        return

    def walk_treectrl(self, item):
        if isinstance(self.tree.GetPyData(item), TreeDict):
            yield item
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            for x in self.walk_treectrl(child):
                if isinstance(self.tree.GetPyData(x), TreeDict):
                    yield x
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def Cut(self, e=None):
        self.Copy(e)

    def Copy(self, e=None):
        from ifigure.ifigure_config import st_scratch
        fc = self.FindFocus()
        while fc != self:
            if hasattr(fc, 'Copy'):
                fc.Copy()
                return
            fc = fc.GetParent()
        self.copy_tree_item()

    def copy_tree_item(self):
        from ifigure.ifigure_config import st_scratch
        item = self.tree.GetSelection()
        obj = self.tree.GetPyData(item)
        if not isinstance(obj, TreeDict):
            return False
        else:
            obj.save_subtree(st_scratch)
        return True

    def Paste(self, e=None):
        from ifigure.ifigure_config import st_scratch
        fc = self.FindFocus()
        while fc != self:
            if hasattr(fc, 'Paste'):
                fc.Paste()
                return
            fc = fc.GetParent()

        item = self.tree.GetSelection()
        obj = self.tree.GetPyData(item)
        if not isinstance(obj, TreeDict):
            return

        self.paste_tree_item()

    def paste_tree_item(self):
        item = self.tree.GetSelection()
        obj = self.tree.GetPyData(item)
        from ifigure.ifigure_config import st_scratch
        if (isinstance(obj, TreeDict) and
                os.path.exists(st_scratch)):
            m = Message()
            child = obj.load_subtree(st_scratch, message=m)
            if child is not None:
                self.update_widget()
            else:
                ret = dialog.message(None,
                                     m.txt,
                                     'Error : Load subtree',
                                     0)
            return True
        else:
            return False
#                   dialog.message(self, 'object can not have this type of child', 'error')

    def OnButton(self, e, mode):
        from ifigure.ifigure_config import st_scratch
#        print 'hit button', mode
        item = self.tree.GetSelection()
        obj = self.tree.GetPyData(item)
        if not isinstance(obj, TreeDict):
            return
        if mode == 'expand':
            if self.tree.IsExpanded(item):
                self.tree.CollapseAllChildren(item)
            else:
                self.tree.ExpandAllChildren(item)
        if mode == 'copy':
            if isinstance(obj, TreeDict):
                obj.save_subtree(st_scratch)
        if mode == 'paste':
            if (isinstance(obj, TreeDict) and
                    os.path.exists(st_scratch)):
                m = Message()
                child = obj.load_subtree(st_scratch, message=m)
                if child is not None:
                    self.update_widget()
                else:
                    ret = dialog.message(None,
                                         m.txt,
                                         'Error : Load subtree',
                                         0)
#                   dialog.message(self, 'object can not have this type of child', 'error')
                    return

        if mode == 'trash':
            if obj == obj.get_root_parent():
                return
            parent = obj.get_parent()
            ichild = obj.get_ichild()
            if ichild == parent.num_child()-1:
                ichild = ichild - 1
            else:
                ichild = ichild + 1
            if ichild >= 0:
                next_sel = parent.get_child(idx=ichild)
            else:
                next_sel = parent

            from ifigure.mto.fig_book import FigBook
            books = [x for x in obj.walk_tree()
                     if isinstance(x, FigBook)]
            for book in books:
                viewer = wx.GetApp().TopWindow.find_bookviewer(book)
                if viewer is not None:
                    viewer.close()
            if obj.get_extfolderpath() is not None:
                ret = dialog.message(self,
                                     "Do you really want to delete exteranl files?",
                                     "Delete External File",
                                     5)
                if ret == 'cancel':
                    return
                if ret == 'yes':
                    # this should be only place to delete
                    obj.destroy(force_clean=True)
                    # external file
                else:
                    obj.destroy(force_clean=False)  # obj disappears from tree.
            else:
                obj.onDelete(e)
            if isinstance(obj, FigObj):
                book = obj.get_figbook()
                if book is not None:
                    viewer = wx.GetApp().TopWindow.find_bookviewer(book)
                    if viewer is not None:
                        viewer.draw()
            else:
                self.update_widget()

            # select item
            wx.CallAfter(self.set_td_selection, next_sel)

    def OnKeyDown(self, e):
        '''
        map delete to selcting delete in pull down
        '''
        key = e.GetKeyCode()
        item = self.tree.GetSelection()
        if key == 8:
            #    delete item in tree by delete key...(too dangerous)
            #            if dictobj == dictobj.get_root_parent():
            #                return
            #            dictobj.onDelete(e)
            #            if isinstance(dictobj, FigObj):
            #               self.GetTopLevelParent().draw()
            #            self.update_widget()
            return
        elif key == wx.WXK_DOWN:
            new_item = self.tree.GetNextVisible(item)
            if new_item.IsOk():
                self.tree.SelectItem(new_item)
            return
        elif key == wx.WXK_UP:
            new_item = self.tree.GetPrevSibling(item)
            if new_item.IsOk():
                self.tree.SelectItem(new_item)
            else:
                new_item = self.tree.GetItemParent(item)
                if new_item.IsOk():
                    self.tree.SelectItem(new_item)
            return
        dictobj = self.tree.GetPyData(item)
        if not isinstance(dictobj, TreeDict):
            return
        m = dictobj.pv_kshortcut(key)
        if m is not None:
            m(e)
        if key == wx.WXK_RETURN:
            '''
            this if chain should be reverse-order
            of object inheritence
            '''

    def search_td(self):
        name = self.tc_path.GetValue()
        self._search_txt = name
        self._search_mode = True
        self.GetTopLevelParent().set_status_text('searching...:' + name,
                                                 timeout=None)
        item = self.tree.GetSelection()
        dictobj = self.tree.GetPyData(item)

        hit = dictobj.search(name)
        if hit is not None:
            self.set_td_selection(hit)

    def search_td_down(self):
        name = self._search_txt
        item = self.tree.GetSelection()
        dictobj = self.tree.GetPyData(item)

        hit = dictobj.search(name, include_self=False)
        if hit is not None:
            self.set_td_selection(hit)

    def search_td_up(self):
        name = self._search_txt
        item = self.tree.GetSelection()
        dictobj = self.tree.GetPyData(item)

        hit = dictobj.search(name, dir=1, include_self=False)
        if hit is not None:
            self.set_td_selection(hit)

    def exit_search_mode(self):
        self._search_txt = ''
        self._search_mode = False
        self.GetTopLevelParent().set_status_text('', timeout=None)
        item = self.tree.GetSelection()
        obj = self.tree.GetPyData(item)
        self.set_tc_path(obj)


#    def OnKillFocus(self, e):
#        self._search_txt = ''
#        self.GetTopLevelParent().set_status_text('', timeout=None)

    def OnExpandItem(self, e):
        #        print "change visible (expand)"
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if not isinstance(dictobj, TreeDict):
            return
        for name, child in dictobj.get_children():
            child.set_visible(True)

    def OnCollapseItem(self, e):
        #        print "change visible (collapse)"
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if not isinstance(dictobj, TreeDict):
            return
        for name, child in dictobj.get_children():
            child.set_visible(False)

    def OnItemRightClick(self, e):
        item = e.GetItem()
        data = self.tree.GetPyData(item)
        m = None
        if isinstance(data, TreeDict):
            m = ProjTreeViewerPopUp(self, data)
        elif hasattr(data[-1], 'tree_viewer_menu'):
            m = ProjTreeViewerPopUp(self, data[-1])
        if m is None:
            return None

        self.PopupMenu(m,
                       e.GetPoint())
        m.Destroy()

    def OnItemActivated(self, e):
        def reset_first_click(e, obj=self):
            obj.timer.Stop()
            obj.Unbind(wx.EVT_TIMER)
            obj._first_click = False
        item = e.GetItem()
        data = self.tree.GetPyData(item)
        m = None
        from ifigure.mto.py_script import PyScript

        if self._first_click == False:
            self._first_click = True
            self.Bind(wx.EVT_TIMER, reset_first_click, self.timer)
            # allow 0.3s interval for DC
            self.timer.Start(300, wx.TIMER_ONE_SHOT)
            e.Skip()
        else:
            if hasattr(data, 'onProjTreeActivate'):
                data.onProjTreeActivate(e)
            self._first_click = False

    def get_selection(self):
        try:
            item = self.tree.GetSelection()
            return self.tree.GetPyData(item)
        except:
            return None

    def change_selection(self, pydata):
        if not self._changed_flag:
            return
        from ifigure.mto.py_extfile import ExtMixIn
        if isinstance(pydata, ExtMixIn):
            self.buttons[1].Enable(False)
            self.buttons[2].Enable(False)
        else:
            self.buttons[1].Enable(True)
            self.buttons[2].Enable(True)
        self.set_tc_path(pydata)
        if not isinstance(pydata, TreeDict):
            self.varviewer.fill_list(pydata[2])
            return
        else:
            self.varviewer.fill_list(pydata)
            if isinstance(pydata, FigObj):
                if len(pydata._artists) != 0:
                    sel = [weakref.ref(pydata._artists[0])]
                    ifigure.events.SendSelectionEvent(pydata, self, sel)

    def OnSelChanged(self, e):
        item = e.GetItem()
        pydata = self.tree.GetPyData(item)
        self._changed_flag = True
        wx.CallLater(100, self.change_selection, pydata)

    def OnSelChanging(self, e):
        if self._drag_start:
            self._drag_start = False
            e.Veto()

    def OnMenu(self, e):
        self.update_widget()

    def OnBeginDrag(self, e):
        if self._move_mode:
            e.Allow()
            return
        item = e.GetItem()
        data = self.tree.GetPyData(item)
        app = self.tree.GetTopLevelParent()

        if isinstance(data, TreeDict):
            t = str(data.get_full_path())
        else:
            t = str(data[0]._var0.get_drag_text1(data))
        app._text_clip = t
        if not wx.TheClipboard.IsOpened():
            wx.TheClipboard.Open()
            data = wx.TextDataObject()
            data.SetText(t)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()

        text = t if six.PY3 else unicode(t)

        self._changed_flag = False
        tdo = wx.TextDataObject(text)
        tdo._source = self
        tds = wx.DropSource(self.tree)
        tds.SetData(tdo)
        tds.DoDragDrop(True)
#        self.tree.Unselect()
        self._drag_start = True
        e.Skip()

    def OnEndDrag(self, e):
        if self._move_mode:
            self._move_mode = False
            return
#        print "OnEndDrag"
#        self.tree.Unselect()
        Write2Main(e, "ev")
        if not e.GetItem().IsOk():
            return
        # Make sure this memeber exists.
        try:
            old = self.dragItem
        except:
            return

        # Get the other IDs that are involved
        new = e.GetItem()
        parent = self.GetItemParent(new)
        if not parent.IsOk():
            return
        text = self.GetItemText(old).split(' ')[0]
#        self.Delete(old)
#        self.InsertItem(parent, new, text)

    def get_defaultpanelstyle(self):
        return wx.STAY_ON_TOP | wx.DEFAULT_DIALOG_STYLE

    def OpenPanel(self, list, obj=None, callback=None, title='title',
                  style=None,
                  **kargs):
        if self.panel is not None:
            self.ClosePanel()

#        self.panel = wx.Panel(self, wx.ID_ANY)
        style = style if style is not None else self.get_defaultpanelstyle()
        self.panel = wx.Dialog(self, wx.ID_ANY, title, style=style)

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.panel.SetSizer(vbox)
        vbox.Add(hbox2, 1, wx.EXPAND | wx.ALL, 1)

        self.elp = EditListPanel(self.panel, list)
        hbox2.Add(self.elp, 1, wx.EXPAND | wx.RIGHT | wx.LEFT, 1)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        button = wx.Button(self.panel, wx.ID_ANY, "Cancel")
        button2 = wx.Button(self.panel, wx.ID_ANY, "Apply")
        hbox.Add(button, 0, wx.EXPAND)
        hbox.AddStretchSpacer()
        hbox.Add(button2, 0, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 5)
        button2.Bind(wx.EVT_BUTTON, self.onPanelApply)
        button.Bind(wx.EVT_BUTTON, self.onPanelClean)
#        self.panel.Layout()
        size = self.panel.GetSize()
        self.panel.SetSizeHints(minH=-1, minW=size.GetWidth())
        self.panel.Show()
        self.panel.Layout()
        self.panel.CenterOnScreen()

#        sizer = self.GetSizer()
#        sizer.Add(self.panel, 1, wx.EXPAND)

#        self.GetTopLevelParent()._force_layout()
        self.callback = callback
        self.callback_kargs = kargs
        self.callback_obj = weakref.proxy(obj, self.onPanelClean)
        wx.CallAfter(self.panel.Fit)

    def onPanelApply(self, e):
        if self.callback_obj is not None:
            m = getattr(self.callback_obj, self.callback)
            self.ClosePanel()
            m(self.elp.GetValue(), **self.callback_kargs)
        else:
            self.ClosePanel()

    def onPanelClean(self, ref):
        if self.panel is not None:
            self.ClosePanel()
            #print('panel clean')

    def ClosePanel(self):
        #        self.GetSizer().Remove(self.panel)
        #        self.panel.Destroy()

        if self.panel.IsBeingDeleted():
            self.panel = None
            return
        p = self.panel.GetTopLevelParent()
        if not p.IsBeingDeleted():
            # p.GetSizer().Remove(p)
            p.Destroy()
            if not self.IsBeingDeleted():
                pp = self.GetTopLevelParent()
                if not pp.IsBeingDeleted():
                    pp._force_layout()
        self.panel = None

    def set_td_selection(self, t0):
        #        print 'set_td_selection', t0
        croot = self.tree.GetRootItem()
        for item in self.walk_treectrl(croot):
            #            print item, self.tree.GetPyData(item)
            if t0 == self.tree.GetPyData(item):
                break

        # unbind temprorary to avoid change of event generation
        self.Unbind(wx.EVT_TREE_SEL_CHANGED)
        self.tree.SelectItem(item)
        dictobj = self.tree.GetPyData(item)
        if isinstance(dictobj, TreeDict):
            self.varviewer.fill_list(dictobj)
            self.set_tc_path(dictobj)
        else:
            self.varviewer.fill_list(dictobj[2])
            self.set_tc_path(dictobj)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)

    def onTD_Selection(self, evt):
        #        print 'onTD_Selection', evt.selections
        if len(evt.selections) < 2:
            t0 = evt.GetTreeDict()
            self.set_td_selection(t0)

    def remove_item_from_tree(self):
        croot = self.tree.GetRootItem()
        for item in self.walk_treectrl(croot):
            treedict = self.tree.GetPyData(item)
            if not isinstance(treedict, TreeDict):
                return False
#          (2015. 02. 0 4 This section is not used..??)
#           if treedict is None:
#                rm_list.append(item)
#                self.tree.Delete(item)
#                return True
            if (treedict.get_full_path() !=
                    self.item_path(item)):
                self.tree.Delete(item)
                return True
            if (treedict.get_parent() is None and
                    treedict is not self.get_proj()):
                self.tree.Delete(item)
                return True
        return False

    def item_path(self, item):
        path = []
        p = item
        croot = self.tree.GetRootItem()
        while p != croot:
            path = [self.tree.GetItemText(p).split(' ')[0]]+path
            p = self.tree.GetItemParent(p)
        path = [self.tree.GetItemText(p).split(' ')[0]]+path
        return '.'.join(path)

    def leaf_list(self, item):
        ret = ()
        name = ()
        p = self.tree.GetItemParent(item)
        p_td = self.tree.GetPyData(p)

        fc, ck = self.tree.GetFirstChild(p)
        while fc:
            ret = ret+(fc,)
            name = name + (self.tree.GetItemText(fc),)
            fc = self.tree.GetNextSibling(fc)

        p.DeleteChildren()
        name2 = p_td.get_childnames()
        for n in name2:
            if name.count[n] == 0:
                continue
            i = name.index[n]
            p.AppendItem(ret[i])

    def rearrange_item(self):
        croot = self.tree.GetRootItem()
        for item in self.walk_treectrl(croot):
            self.tree.SortChildren(item)

    def add_item_to_tree(self):
        croot = self.tree.GetRootItem()
        oge_list = [item for item in self.walk_treectrl(croot)]
        #oge = iter(oge_list)
        nge_list = [item for item in self.get_proj().walk_tree()]
        nge = iter(nge_list)
        oindex = -1
        nindex = -1  # index of last time

        ntd = self.get_proj()
        otd = ntd
        ntd2 = ntd
        otd2 = ntd
        oitem = croot
        while True:
            try:
                ntd2 = next(nge)
                nindex = nindex + 1
                oindex = oindex + 1
                if len(oge_list) > oindex:
                    oitem2 = oge_list[oindex]
                    otd2 = self.tree.GetPyData(oitem2)
                    # if not isinstance(otd2, TreeDict): continue
                else:
                    otd2 = None
#           print ntd2, otd2
                if ntd2 is not otd2:
                    #              if otd2 is not None: print otd2.get_full_path()

                    if ntd2.get_parent() is ntd:
                        #                 print "adding first child", ntd2.get_full_path()
                        self.fill_sub_tree(oitem, ntd2, oge_list, oindex,
                                           sel_dict=None, first=True)
                        otd2 = self.tree.GetPyData(oge_list[oindex])
                        if ntd2 is not otd2:
                            print('something is wrong')
                            break
                        else:
                            ntd = ntd2
                            otd = otd2
                            oitem = oge_list[oindex]
                            continue

                    pitem = self.tree.GetItemParent(oitem)
                    while (self.tree.GetPyData(pitem)
                           is not ntd2.get_parent()):
                        oitem = pitem
                        pitem = self.tree.GetItemParent(pitem)

#              print "adding sibling", ntd2.get_full_path()
#              print "next to", self.tree.GetPyData(oitem).get_full_path()
                    self.fill_sub_tree(
                        pitem,
                        ntd2, oge_list, oindex,
                        sel_dict=None, sib=oitem)
                    otd2 = self.tree.GetPyData(oge_list[oindex])
                    if ntd2 is not otd2:
                        print('something is wrong')
                        break
                    else:
                        ntd = ntd2
                        otd = otd2
                        oitem = oge_list[oindex]
                        continue
                ntd = ntd2
                otd = otd2
                oitem = oitem2
            except StopIteration:
                #             print '###final result'
                #             print  [self.tree.GetPyData(item) for item in self.walk_treectrl(croot)]
                return False


#        print 'final result (fake)'
#        print  [self.tree.GetPyData(item) for item in self.walk_treectrl(croot)]
        return False

    def fill_sub_tree(self, pitem, treedict,
                      oge_list, oindex,  sel_dict=None,
                      sib=None, first=False):

        name = treedict.name

        from ifigure.mto.hg_support import HGSupport, has_repo
        if has_repo(treedict) and isinstance(treedict, HGSupport):
            name = name + treedict.hg_projtreeviewer_status()

        if treedict.status != '':
            label = name + ' ('+treedict.status+')'
        else:
            label = name
            if treedict.get_auto_status_str() != '':
                label = label + ' (' + treedict.get_auto_status_str() + ')'
#             label = name
#         print label
        img = treedict.get_classimage()
#         print 'adding '+treedict.get_full_path()
        if sib is None:
            if first is True:
                parent2 = tree_InsertItemBefore(self.tree, pitem, 0,
                                                label, img)
            else:
                parent2 = self.tree.AppendItem(pitem, label, img)
        else:
            parent2 = self.tree.InsertItem(pitem, sib, label, img)
        oge_list.insert(oindex, parent2)
        oindex = oindex + 1

        if treedict is sel_dict:
            self.tree.SelectItem(parent2)
        if treedict.is_suppress():
            self.tree.SetItemTextColour(parent2,
                                        wxNamedColour('Grey'))
#         if treedict.can_have_child():
        if treedict.num_child() != 0:
            self.tree.SetItemHasChildren(parent2)

        self.tree.SetPyData(parent2, treedict)
        if treedict.isTreeLink():
            l = treedict.get_linkobj()
            if l is not None:
                tx = l.name
            else:
                tx = 'None'
            if name == tx:
                self.tree.SetItemText(parent2,
                                      '-> ' + tx)
            else:
                self.tree.SetItemText(parent2,
                                      name + '-> ' + tx)
#            self.tree.SetItemItalic(parent2, True)
        else:
            for n2, child in treedict.get_children():
                oindex = self.fill_sub_tree(parent2, child, oge_list, oindex,
                                            sel_dict=sel_dict)
                # self.tree.Expand(parent2)

        if treedict.is_visible():
            self.tree.Expand(pitem)
        if isinstance(treedict._var0, PyContents):
            if treedict._var0_show:
                self.show_contents(treedict, parent2)
        return oindex

    def add_item_to_tree_org(self):
        croot = self.tree.GetRootItem()
        oge = self.walk_treectrl(croot)
        nge = self.get_proj().walk_tree()

        ntd = self.get_proj()
        otd = ntd
        ntd2 = ntd
        otd2 = ntd
        oitem = croot
        while True:
            try:
                ntd2 = next(nge)
                try:
                    oitem2 = next(oge)
                    otd2 = self.tree.GetPyData(oitem2)
                    # if not isinstance(otd2, TreeDict): continue
                except Exception:
                    otd2 = None

                if ntd2 is not otd2:
                    #              if otd2 is not None: print otd2.get_full_path()

                    if ntd2.get_parent() is ntd:
                        #                 print "adding first child", ntd2.get_full_path()
                        self.fill_sub_tree_org(oitem, ntd2,
                                               sel_dict=None, first=True)
                        break

                    pitem = self.tree.GetItemParent(oitem)
                    while (self.tree.GetPyData(pitem)
                           is not ntd2.get_parent()):
                        oitem = pitem
                        pitem = self.tree.GetItemParent(pitem)

                    print("adding sibling", ntd2.get_full_path())
                    print("next to", self.tree.GetPyData(oitem).get_full_path())
                    nindex = self.fill_sub_tree_org(
                        pitem,
                        ntd2,
                        sel_dict=None, sib=oitem)
                    break
                ntd = ntd2
                otd = otd2
                oitem = oitem2
            except StopIteration:
                return False

        return True

    def fill_sub_tree_org(self, pitem, treedict, sel_dict=None,
                          sib=None, first=False):

        name = treedict.name

        from ifigure.mto.hg_support import HGSupport, has_repo
        if has_repo(treedict) and isinstance(treedict, HGSupport):
            name = name + treedict.hg_projtreeviewer_status()

        if treedict.status != '':
            label = name+' ('+treedict.status+')'
        else:
            label = name
        img = treedict.get_classimage()
        if sib is None:
            if first is True:
                parent2 = tree_InsertItemBefore(self.tree. pitem, 0,
                                                label, img)
            else:
                parent2 = self.tree.AppendItem(pitem, label, img)
        else:
            parent2 = self.tree.InsertItem(pitem, sib, label, img)
        if treedict is sel_dict:
            self.tree.SelectItem(parent2)
        if treedict.is_suppress():
            self.tree.SetItemTextColour(parent2,
                                        wxNamedColour('Grey'))

        if treedict.num_child() != 0:
            self.tree.SetItemHasChildren(parent2)

        self.tree.SetPyData(parent2, treedict)
        if treedict.isTreeLink():
            l = treedict.get_linkobj()
            if l is not None:
                tx = l.name
            else:
                tx = 'None'
            if name == tx:
                self.tree.SetItemText(parent2,
                                      '-> ' + tx)
            else:
                self.tree.SetItemText(parent2,
                                      name + '-> ' + tx)
#            self.tree.SetItemItalic(parent2, True)
        else:
            for n2, child in treedict.get_children():
                self.fill_sub_tree_org(parent2, child,
                                       sel_dict=sel_dict)
                # self.tree.Expand(parent2)

        if treedict.is_visible():
            self.tree.Expand(pitem)
        if isinstance(treedict._var0, PyContents):
            if treedict._var0_show:
                self.show_contents(treedict, parent2)

    def update_content_widget(self, td):
        croot = self.tree.GetRootItem()
        oge = self.walk_treectrl(croot)
        for item in oge:
            data = self.tree.GetPyData(item)
            if not isinstance(data, TreeDict):
                continue
            if (data._var0_show and data.get_full_path() == td.get_full_path()):
                self.hide_contents(td, item)
                self.show_contents(td, item)

    def show_contents(self, td, item):
        td._var0.show_contents(self.tree,  td, item)
        td._var0_show = True

    def hide_contents(self, td, item):
        td._var0.hide_contents(self.tree,  td, item)
        td._var0_show = False

    def set_tc_path(self, obj):
        if self._search_mode:
            return

        if isinstance(obj, TreeDict):
            self.tc_path.Enable(True)
            self.tc_path.SetValue(obj.get_full_path())
        else:
            self.tc_path.Enable(True)
