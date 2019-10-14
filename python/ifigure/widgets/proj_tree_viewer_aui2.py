from __future__ import print_function
import wx
import sys
import weakref
import wx.aui as aui
from ifigure.utils.cbook import ImageFiles, Write2Main, BuildPopUpMenu
from ifigure.widgets.var_viewerg import VarViewerG, VarViewerGDropTarget
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from ifigure.utils.edit_list import EditListPanel
from ifigure.mto.fig_obj import FigObj
import ifigure.events


class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(
            self, parent, -1, style=wx.LC_REPORT | wx.LC_EDIT_LABELS)
        ListCtrlAutoWidthMixin.__init__(self)


class ProjViewerDropTarget(wx.TextDropTarget):
    # obj is proj_viewer
    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj
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

#        print flag & wx.TREE_HITTEST_ONITEMLABEL
        if ((flag & wx.TREE_HITTEST_ONITEMINDENT) or
            (flag & wx.TREE_HITTEST_ONITEMBUTTON) or
                (flag & wx.TREE_HITTEST_TOLEFT)):
            if self._timer_on == False:
                self.obj.tree.Bind(wx.EVT_TIMER, self.OnTime)
                if not hasattr(self, 'timer'):
                    self.timer = wx.Timer(self.obj.tree, wx.ID_ANY)
                    self.timer.Start(100)
                self._timer_on = True
                self._item_at_start = item
        else:
            # cancel action
            self._item_at_start = None

        if flag & wx.TREE_HITTEST_ONITEMLABEL:
            dictobj = self.obj.tree.GetPyData(item)
            if self._prev_item is not None:
                self.obj.tree.SetItemDropHighlight(self._prev_item, False)
            self.obj.tree.SetItemDropHighlight(item)
            if self._prev_dict != dictobj:
                self.obj.varviewer.fill_list(dictobj)
            self._prev_item = item
            self._prev_dict = dictobj
            if self._timer_on == False:
                self.obj.tree.Bind(wx.EVT_TIMER, self.OnTime)
                if not hasattr(self, 'timer'):
                    self.timer = wx.Timer(self.obj.tree, wx.ID_ANY)
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
        print("stop timer")
        if self.timer is not None:
            self.timer.Stop()
            del self.timer
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
            pass
        if self._prev_item is not None:
            self.obj.tree.SetItemDropHighlight(self._prev_item, False)
        self._prev_item = None
        data = str(data)

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
        menus = menus+[('---', None, None),
                       ('ExpandAll', self.onExpandChild, None),
                       ('Copy Path', self.onCopyPath, None),
                       ('Refresh', self.onRefresh, None)]

        BuildPopUpMenu(self, menus)
        return

    def onRefresh(self, e):
        self.parent.update_widget()

    def onExpandChild(self, e):
        tv = (e.GetEventObject()).parent
        item = tv.tree.GetSelection()
        tv.tree.ExpandAllChildren(item)

    def onCopyPath(self, e):
        tv = (e.GetEventObject()).parent
        item = tv.tree.GetSelection()
        dictobj = tv.tree.GetPyData(item)
        tx = 'ifigure.'+dictobj.get_full_path()
        app = tv.GetTopLevelParent()
        app.shell.CopyText(len(tx), tx)


class ProjTreeViewer(wx.Panel):
    def __init__(self, parent=None):
        """Constructor"""

        super(ProjTreeViewer, self).__init__(parent)
        self._drag_start = False
        self.panel = None

#        sizer=wx.BoxSizer(wx.VERTICAL)
#        self.SetSizer(sizer)
#        self.splitter=wx.SplitterWindow(self)
#        sizer.Add(self.splitter, 1, wx.EXPAND)
#        self.nb = aui.AuiNotebook(self, style=aui.AUI_NB_TAB_SPLIT|
#                                              aui.AUI_NB_TAB_MOVE|
#                                              aui.AUI_NB_SCROLL_BUTTONS)

        ### make tree ###
        self.tree = wx.TreeCtrl(self, wx.ID_ANY,
                                wx.DefaultPosition,
                                (-1, -1), wx.TR_HAS_BUTTONS)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
#        self.nb.AddPage(self.tree, 'Project Tree')
        self.tree.parent = self
        self.dt1 = ProjViewerDropTarget(self)
        self.tree.SetDropTarget(self.dt1)

        im = ImageFiles()
        self.tree.SetIndent(8)
        self.tree.SetImageList(im.get_imagelist())

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnItemRightClick)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)
        self.Bind(wx.EVT_TREE_SEL_CHANGING, self.OnSelChanging)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag)
        self.Bind(wx.EVT_MENU, self.OnMenu)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.OnKeyDown)
        self.tree.GetTopLevelParent().Bind(wx.EVT_MOUSE_CAPTURE_LOST, lambda x: None)

    def init_sash_pos(self):
        return
        # self.splitter.SetSashPosition(200)

    def get_proj(self):
        app = self.GetTopLevelParent()
        return app.proj

    def update_widget(self):
        sel = self.tree.GetSelection()
        if sel is not None:
            sdict = self.tree.GetPyData(sel)
        else:
            sdict = None

        proj = self.get_proj()
        if proj is None:
            self.tree.DeleteAllItems()
            return
        if sdict is None:
            sdict = proj  # default select proj

        croot = self.tree.GetRootItem()
        if self.tree.GetPyData(croot) is None:
            self.tree.DeleteAllItems()
            croot = self.tree.AddRoot(proj.name)
            self.tree.SetPyData(croot,  self.get_proj())

        #
        #  remove item from tree viewer
        #
        while self.remove_item_from_tree():
            pass
        #
        #  add item to tree viewer
        #
        while self.add_item_to_tree():
            pass
        #
        #  refresh tree name...
        #
        for item in self.walk_treectrl(croot):
            treedict = self.tree.GetPyData(item)
            name = treedict.name
            if treedict.status != '':
                label = name+' ('+treedict.status+')'
            else:
                label = name
            self.tree.SetItemText(item, label)

        self.varviewer.fill_list(sdict)
        return

    def walk_treectrl(self, item):
        yield item
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            for x in self.walk_treectrl(child):
                yield x
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def OnButton(self, e):
        pass

    def OnKeyDown(self, e):
        "map delete to selcting delete in pull down"
        if e.GetKeyCode() == 8:
            item = self.tree.GetSelection()
            dictobj = self.tree.GetPyData(item)
            dictobj.onDelete(e)

            if isinstance(dictobj, FigObj):
                self.GetTopLevelParent().draw()
            else:
                self.update_widget()

    def OnExpandItem(self, e):
        #        print "change visible (expand)"
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if dictobj is None:
            return
        for name, child in dictobj.get_children():
            child.set_visible(True)

    def OnCollapseItem(self, e):
        #        print "change visible (collapse)"
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if dictobj is None:
            return
        for name, child in dictobj.get_children():
            child.set_visible(False)

    def OnItemRightClick(self, e):
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if dictobj is None:
            return
        menus = dictobj.tree_viewer_menu()
        if menus is None:
            return None

        m = ProjTreeViewerPopUp(self, dictobj)
        self.PopupMenu(m,
                       e.GetPoint())
        m.Destroy()

    def OnSelChanged(self, e):
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
        if dictobj is None:
            return
        self.varviewer.fill_list(dictobj)
        if isinstance(dictobj, FigObj):
            if len(dictobj._artists) != 0:
                sel = [weakref.ref(dictobj._artists[0])]
                ifigure.events.SendSelectionEvent(dictobj, self, sel)

    def OnSelChanging(self, e):
        if self._drag_start:
            self._drag_start = False
            e.Veto()

    def OnMenu(self, e):
        self.update_widget()

    def OnBeginDrag(self, e):
        item = e.GetItem()
        dictobj = self.tree.GetPyData(item)
#        self.dragItem = e.GetItem()
        app = self.tree.GetTopLevelParent()
        app._text_clip = dictobj.get_full_path()
        text = dictobj.get_full_path() if six.PY3 else unicode(dictobj.get_full_path())
        tdo = wx.TextDataObject(text)
        tds = wx.DropSource(self.tree)
        tds.SetData(tdo)
        tds.DoDragDrop(True)
#        self.tree.Unselect()
        self._drag_start = True
        e.Skip()

    def OnEndDrag(self, e):
        print("OnEndDrag")
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
        text = self.GetItemText(old)
#        self.Delete(old)
#        self.InsertItem(parent, new, text)

    def OpenPanel(self, list, obj=None, callback=None):
        if self.panel is not None:
            self.ClosePanel()
        self.panel = wx.Panel(self, wx.ID_ANY)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(vbox)
        self.elp = EditListPanel(self.panel, list)
        vbox.Add(self.elp, 0, wx.EXPAND |
                 wx.ALIGN_CENTER | wx.RIGHT | wx.LEFT, 1)
        button = wx.Button(self.panel, wx.ID_ANY, "Apply")
        vbox.Add(button, 0, wx.ALIGN_RIGHT | wx.ALIGN_TOP)
        button.Bind(wx.EVT_BUTTON, self.onPanelApply)
#        vbox.SetSizeHints(self)
#        elp.GetSizer().SetSizeHints(self)

        sizer = self.GetSizer()
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.GetTopLevelParent()._force_layout()
        self.callback = callback
        self.callback_obj = weakref.proxy(obj, self.onPanelClean)

    def onPanelApply(self, e):
        if self.callback_obj is not None:
            m = getattr(self.callback_obj, self.callback)
            m(self.elp.GetValue())
            self.ClosePanel()
        else:
            self.ClosePanel()

    def onPanelClean(self, ref):
        if self.panel is not None:
            self.ClosePanel()
            print('panel clean')

    def ClosePanel(self):
        self.GetSizer().Remove(self.panel)
        self.panel.Destroy()
        self.GetTopLevelParent()._force_layout()
        self.panel = None

    def onTD_Selection(self, evt):
        if len(evt.selections) < 2:
            croot = self.tree.GetRootItem()
            t0 = evt.GetTreeDict()
            print(t0)
            for item in self.walk_treectrl(croot):
                if t0 == self.tree.GetPyData(item):
                    break

            # unbind temprorary to avoid change of event generation
            self.Unbind(wx.EVT_TREE_SEL_CHANGED)
            self.tree.SelectItem(item)
            dictobj = self.tree.GetPyData(item)
            if dictobj is not None:
                self.varviewer.fill_list(dictobj)
            self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)

    def remove_item_from_tree(self):
        croot = self.tree.GetRootItem()
        for item in self.walk_treectrl(croot):
            treedict = self.tree.GetPyData(item)
            print(treedict.get_full_path())
            print(self.item_path(item))
            if treedict is None:
                # rm_list.append(item)
                self.tree.Delete(item)
                return True
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
            path = [self.tree.GetItemText(p)]+path
            p = self.tree.GetItemParent(p)
        path = [self.tree.GetItemText(p)]+path
        return '.'.join(path)

    def add_item_to_tree(self):
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
                except Exception:
                    otd2 = None

                if ntd2 is not otd2:
                    #              if otd2 is not None: print otd2.get_full_

                    if ntd2.get_parent() is ntd:
                        #                 print "adding first child", ntd2.get_full_path()
                        self.fill_sub_tree(oitem, ntd2,
                                           sel_dict=None, first=True)
                        break

                    pitem = self.tree.GetItemParent(oitem)
                    while (self.tree.GetPyData(pitem)
                           is not ntd2.get_parent()):
                        oitem = pitem
                        pitem = self.tree.GetItemParent(pitem)

#              print "adding sibling", ntd2.get_full_path()
#              print "next to", self.tree.GetPyData(oitem).get_full_path()
                    self.fill_sub_tree(
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

    def fill_sub_tree(self, pitem, treedict, sel_dict=None,
                      sib=None, first=False):

        name = treedict.name
        if treedict.status != '':
            label = name+' ('+treedict.status+')'
        else:
            label = name
        img = treedict.classimage()
        if sib is None:
            if first is True:
                parent2 = self.tree.InsertItemBefore(pitem, 0,
                                                     label, img)
            else:
                parent2 = self.tree.AppendItem(pitem, label, img)
        else:
            parent2 = self.tree.InsertItem(pitem, sib, label, img)
        if treedict is sel_dict:
            self.tree.SelectItem(parent2)
        if treedict.is_suppress():
            self.tree.SetItemTextColour(parent2,
                                        wx.NamedColour('Grey'))
        if treedict.can_have_child():
            self.tree.SetItemHasChildren(parent2)

        self.tree.SetPyData(parent2, treedict)
        if treedict.isTreeLink():
            l = treedict.get_linkobj()
            if l is not None:
                tx = l.name
            else:
                tx = 'None'
            self.tree.SetItemText(parent2,
                                  '-> '+name + '(' + tx + ')')
        else:
            for n2, child in treedict.get_children():
                self.fill_sub_tree(parent2, child,
                                   sel_dict=sel_dict)
                # self.tree.Expand(parent2)

        if treedict.is_visible():
            self.tree.Expand(pitem)
