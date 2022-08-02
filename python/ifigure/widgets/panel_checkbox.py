import wx
import weakref

from ifigure.utils.wx3to4 import menu_Append, menu_RemoveItem, menu_AppendItem
from ifigure.utils.cbook import FindFrame


class SplitterWindow(wx.SplitterWindow):
    pass


ID_LIST = {}


class PanelCheckbox(object):
    def __init__(self, panel, d):
        self.panelinfos = []
        self.child = []
        self.parent = None
        self.panel = panel
        self.visible = False
#        if self.panel.GetSizer() is None:
#            self.panel.SetSizer(wx.BoxSizer(d))
#        else:
#            self.panel.GetSizer().Add(wx.BoxSizer(d))
        self.panel.SetSizer(wx.BoxSizer(d))
        self.sash_pos = 10
        self._primary_client = None

    def onUpdateUI(self, evt):
        for pinfo, c in self.walk_tree():
            if "menu" not in pinfo:
                print(pinfo)
                continue
            if pinfo["menu"].GetId() == evt.GetId():
                if pinfo["toggle_menu"]:
                    evt.Enable(True)
                    evt.Show(True)
                else:
                    evt.Enable(False)
                    evt.Show(False)
                val = pinfo["panel"].IsShown()
                evt.Check(val)
#                print 'updating menu check', val
                return True
        return False

    def add_panel(self, cls, name, message, idx, keepsize=False, *args):
        """
           config = ("name": name, 
                     "member": PanelCheckBox() or panel

        """
        info = {"name": name,
                "message": message,
                "panel": cls(self.panel),
                "panel_size": None,
                "idx": idx,
                "primary": False,
                "secondary_hidden_together": False,
                "keepsize": keepsize,
                "toggle_menu": True}
        info["panel_size"] = info["panel"].GetSize()
        self.panelinfos.append(info)
        if len(args) == 0:
            args = [1, wx.EXPAND, 0]
        self.panel.GetSizer().Add(info["panel"], *args)
        return info["panel"]

    def set_primary(self, panel):
        for pinfo in self.panelinfos:
            if pinfo["panel"] == panel:
                pinfo["primary"] = True

    def hide_toggle_menu(self, panel):
        for pinfo, c in self.walk_tree():
            #         for pinfo in self.panelinfos:
            if pinfo["panel"] == panel:
                pinfo["toggle_menu"] = False

    def show_toggle_menu(self, panel):
        for pinfo, c in self.walk_tree():
            #         for pinfo in self.panelinfos:
            if pinfo["panel"] == panel:
                pinfo["toggle_menu"] = True

    def toggle_panel(self, panel, value):
        for pinfo, c in self.walk_tree():
            if pinfo["panel"] == panel:
                if pinfo["toggle_menu"]:
                    pinfo["menu_root"].Check(pinfo["menu"].GetId(), value)
                pinfo["panel"].Show(value)
                pinfo['h'](None)
                return

    def get_toggle(self, panel):
        for pinfo, c in self.walk_tree():
            if pinfo["panel"] == panel:
                return pinfo["panel"].IsShown()
        return None

    def add_splitter(self, dsplit, dsizer):
        #        self.sp = SplitterWindow(self.panel, -1, style=wx.SP_NOBORDER|wx.SP_LIVE_UPDATE)
        self.sp = SplitterWindow(self.panel, wx.ID_ANY,
                                 style=wx.SP_NOBORDER | wx.SP_LIVE_UPDATE | wx.SP_3DSASH,
                                 #                                 style = wx.SP_LIVE_UPDATE,
                                 size=(10, 10))
#                                 style = wx.SP_LIVE_UPDATE|wx.SP_3DSASH)
#        self.sp.SetSashSize(1)
        if dsplit == 'v':
            self.split_func = self.sp.SplitVertically
        else:
            self.split_func = self.sp.SplitHorizontally

        if dsizer == 'v':
            d = wx.VERTICAL
        else:
            d = wx.HORIZONTAL

        panel1 = wx.Panel(self.sp, wx.ID_ANY, style=wx.NO_BORDER)
        panel2 = wx.Panel(self.sp, wx.ID_ANY, style=wx.NO_BORDER)
        p1 = PanelCheckbox(panel1, d)
        p2 = PanelCheckbox(panel2, d)
        p1.parent = weakref.proxy(self)
        p2.parent = weakref.proxy(self)

        self.panel.GetSizer().Add(self.sp, 1, wx.EXPAND, 0)

        self.child = (p1, p2)

        self.sp.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onSashChanged)
        self.sp.Bind(wx.EVT_SPLITTER_DOUBLECLICKED, self.onSashChanged)
        self.sp.Bind(wx.EVT_SPLITTER_UNSPLIT, self.onSashChanged)

        self.sp.SetMinimumPaneSize(1)
#        self.sp.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.onSashChanging)
#        self.sp.Bind(wx.EVT_SCROLLBAR, self.onSashDragged)
        return p1, p2

    def onSashChanging(self, evt):
        pass
#        print 'SashChanging'
#        if (self.child[0].panel.IsShown() and
#            self.child[1].panel.IsShown()):
#            self.sash_pos=self.sp.GetSashPosition()
#        frame = FindFrame(self.panel)
#        frame.SendSizeEvent()

    def onSashChanged(self, evt):
        if (self.child[0].panel.IsShown() and
                self.child[1].panel.IsShown()):
            self.sash_pos = self.sp.GetSashPosition()
#            print 'writing sash pos',  id(self),self.sash_pos
        if not self.child[0].panel.IsShown():
            for pinfo, c in self.child[0].walk_tree():
                pinfo["panel"].Hide()
        if not self.child[1].panel.IsShown():
            for pinfo, c in self.child[1].walk_tree():
                pinfo["panel"].Hide()

        if (not self.child[0].panel.IsShown() or
                not self.child[1].panel.IsShown()):
            self.root_parent().update_check()

        frame = FindFrame(self.panel)
        frame.SendSizeEvent()

    def root_parent(self):
        if self.parent is None:
            return self
        else:
            return self.parent.root_parent()

    def walk_tree(self):
        for c in self.child:
            for p, x in c.walk_tree():
                yield p, x
        for pi in self.panelinfos:
            yield pi, self

    def _make_menu(self, root2, pinfos):
        for i, pinfo, cb in pinfos:
            #            m = root2.Append(wx.ID_ANY, pinfo["name"],
            if not pinfo["message"] in ID_LIST:
                ID_LIST[pinfo["message"]] = wx.NewIdRef(count=1)
            id = ID_LIST[pinfo["message"]]

            m = root2.Append(id, pinfo["name"],
                             'Show '+pinfo["message"],
                             kind=wx.ITEM_CHECK)

            def menu_handler(evt, pinfo=pinfo, cb=cb):
                self.menu_handler(evt, pinfo, cb)

            pinfo["menu"] = m
            pinfo["menu_root"] = root2
            pinfo["h"] = menu_handler

    def _apply_toggle(self, root2, pinfos):
        for i, pinfo, cb in pinfos:
            id = root2.FindItem(pinfo["name"])
            if id != wx.NOT_FOUND and not pinfo["toggle_menu"]:
                menu_RemoveItem(root2, pinfo["menu"])
            elif id == wx.NOT_FOUND and pinfo["toggle_menu"]:
                menu_AppendItem(root2, pinfo["menu"])

    def append_menu(self, root, use_panel_menu=False):
        pinfos = sorted([(p[0]["idx"], p[0], p[1])
                         for p in self.walk_tree()])

        if not use_panel_menu:
            self.panel_menu = root
            self._make_menu(root, pinfos)
            self._apply_toggle(root, pinfos)
        else:
            root2 = wx.Menu()
            self.panel_menu = root2
            menu_Append(root, wx.ID_ANY, 'Panels', root2)
            self._make_menu(root2, pinfos)
            self._apply_toggle(root2, pinfos)

    def rebuild_menu(self):
        pinfos = sorted([(p[0]["idx"], p[0], p[1])
                         for p in self.walk_tree()])
        root2 = self.panel_menu
        self._apply_toggle(root2, pinfos)
#        self.update_check()

    def primary_client(self, *args):
        if len(args) == 0:
            return self.root_parent()._primary_client()
        else:
            self.root_parent()._primary_client = weakref.ref(args[0])

    def menu_handler(self, evt, pinfo=None, cb=None):
        #self == root
        app = FindFrame(pinfo["panel"])
        app.Unbind(wx.EVT_SIZE)
#        app.Freeze()
        pc = self.primary_client()
        s1 = pc.GetClientSize()
        # self.panel.Show() #### do I need this ?????

        flag = (pinfo["menu"].IsChecked() if pinfo["toggle_menu"]
                else pinfo["panel"].IsShown())
#        print pinfo["panel"]
        if flag:
            pinfo["panel"].Show()
            if pinfo["keepsize"] == 'b':
                frame = FindFrame(pinfo["panel"])
                s = frame.GetSize()
                frame.SetSize((s[0], s[1]+pinfo["panel_size"][1]))
            if pinfo["primary"]:
                for pinfo2 in cb.panelinfos:
                    if (pinfo2 is not pinfo):
                        if pinfo["secondary_hidden_together"]:
                            #                          print 'showing', pinfo2["panel"]
                            pinfo2["panel"].Show()
                        pinfo2["menu"].Enable()

        else:
            pinfo["panel"].Hide()
            pinfo["panel_size"] = pinfo["panel"].GetSize()
            if pinfo["primary"]:
                pinfo["secondary_hidden_together"] = False
                for pinfo2 in cb.panelinfos:
                    if pinfo2 is not pinfo:
                        if pinfo2["panel"].IsShown():
                            pinfo["secondary_hidden_together"] = True
                            pinfo2["panel"].Hide()
                        pinfo2["menu"].Enable(False)

        self.update_check()
        self.root_parent().set_splitters()
        s2 = pc.GetClientSize()
        p = pinfo["panel"]
        while p is not None:
            p.Layout()
            p = p.GetParent()
        app.Layout()
        s3 = pc.GetClientSize()
#        print s1, s2,  s3
        if pinfo["keepsize"] == 'b':
            frame = FindFrame(pinfo["panel"])
            s = frame.GetSize()
            frame.SetSize((s[0], s[1]-(s2[1]-s1[1])))
        elif pinfo["keepsize"] == 'r':
            frame = FindFrame(pinfo["panel"])
            s = frame.GetSize()
            frame.SetSize((s[0]-(s3[0]-s1[0]), s[1]))
        elif pinfo["keepsize"] == 'l':
            frame = FindFrame(pinfo["panel"])
            s = frame.GetSize()
            p = frame.GetPosition()
            frame.SetPosition((p[0]+(s3[0]-s1[0]), p[1]))
            frame.SetSize((s[0]-(s3[0]-s1[0]), s[1]))
        else:
            app.SendSizeEvent()
#        app.Thaw()
#        app.Raise()
        app.Bind(wx.EVT_SIZE, app.onResize)

    def bind_handler(self, obj):
        for pinfo, c in self.walk_tree():
            if not pinfo["toggle_menu"]:
                continue
            obj.Bind(wx.EVT_MENU, pinfo["h"],
                     pinfo["menu"])

    def get_sashposition(self, p=None):
        if p is None:
            p = []

        if len(self.child) != 0:
            for c in self.child:
                p = c.get_sashposition(p)
            p.append(self.sash_pos)
        return p

    def set_sashposition(self, pos, i=None):
        if i is None:
            i = 0
        if len(self.child) != 0:
            for c in self.child:
                i = c.set_sashposition(pos, i)
            self.sp.SetSashPosition(pos[i])
            if pos[i] != 0:
                self.sash_pos = pos[i]
            else:
                self.sash_pos = 10
#           print pos[i], self.sp.GetSashPosition()
            i = i+1
        return i

    def get_showhide(self):
        return [pinfo["panel"].IsShown() for pinfo, c in self.walk_tree()]

    def set_showhide(self, p, panel=None):
        i = 0
        for pinfo, c in self.walk_tree():
            if (panel is None or
                    panel == pinfo["panel"]):
                pinfo["panel"].Show(p[i])
                c.panel.Show()
                i = i + 1

    def update_check(self):
        return
        for pinfo, c in self.walk_tree():
            if not pinfo["toggle_menu"]:
                continue
            val = pinfo["panel"].IsShown()
            pinfo["menu_root"].Check(pinfo["menu"].GetId(), val)
#            pinfo["menu"].Check(val)

    def set_splitters(self):
        #        self.sash_pos = max([10, self.sash_pos])
        for c in self.child:
            c.set_splitters()
        self.visible = False
        if len(self.child) == 0:
            for pinfo in self.panelinfos:
                #              print pinfo["panel"]
                #              print pinfo["panel"].IsShown()
                if pinfo["panel"].IsShown():
                    self.visible = True
        else:
            if (self.child[0].visible and
                    self.child[1].visible):
                if not self.sp.IsSplit():
                    self.split_func(self.child[0].panel,
                                    self.child[1].panel)
                    # print self.sash_pos
                    self.sp.SetSashPosition(self.sash_pos)
#                  print 'setting sash pos', id(self), self.sash_pos
                self.visible = True
            elif self.child[0].visible:
                if self.sp.IsSplit():
                    self.sash_pos = self.sp.GetSashPosition()
#                  print 'writing sash pos2', id(self),  self.sash_pos
                    self.sp.Unsplit(self.sp.GetWindow2())
                else:
                    self.split_func(self.child[0].panel,
                                    self.child[1].panel)
                    self.sp.SetSashPosition(self.sash_pos)
                    self.sp.Unsplit(self.sp.GetWindow2())
                self.visible = True
            elif self.child[1].visible:
                if self.sp.IsSplit():
                    self.sash_pos = self.sp.GetSashPosition()
#                  print 'writing sash pos3', id(self), self.sash_pos
                    self.sp.Unsplit(self.sp.GetWindow1())
                else:
                    self.split_func(self.child[0].panel,
                                    self.child[1].panel)
                    self.sp.SetSashPosition(self.sash_pos)
                    self.sp.Unsplit(self.sp.GetWindow1())
                self.visible = True
