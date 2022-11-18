from __future__ import print_function
import weakref
import os
import traceback
import wx
import wx.grid
from ifigure.utils.eval_node import EvalNode
from ifigure.utils.cbook import ImageFiles, Write2Main, BuildPopUpMenu
import ifigure.widgets.dialog as dialog

from ifigure.widgets.var_viewerg2 import _PropertyGrid
from ifigure.utils.wx3to4 import isWX3, GridTableBase
# class _PropertyGrid( wx.grid.Grid ):
#     def __init__(self, *args, **kargs):
#         wx.grid.Grid.__init__(self, *args, **kargs)
#         self.Bind(wx.EVT_SIZE, self.onSizeEvent)
#     def onSizeEvent(self, evt):
#         self.ForceRefresh()
#     def SetTable( self, object, *attributes ):
#         self.tableRef = weakref.ref( object )
#         return wx.grid.Grid.SetTable(self, object, *attributes )
#     def GetTable( self ):
#         return self.tableRef()


class ShellVarViewerDropTarget(wx.TextDropTarget):
    # obj is proj_viewer
    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj

    def OnDropText(self, x, y, indata):
        print(type(indata))

        # this is ad-hoc....!
        app = self.obj.GetTopLevelParent()
        indata = app._text_clip
        app._text_clip = ''

        data = '='+str(indata)
        try:
            print(str(indata))
            obj = EvalNode(str(indata))
            # print obj
            if obj.isTreeDict():
                data = data + '[:]'
        except Exception:
            pass
        pv = self.obj
        vv = pv.varviewer

        row = vv.grid.YToRow(y + vv.grid.GetViewStart()[1] *
                             vv.grid.GetScrollPixelsPerUnit()[1])
        if row == -1:
            return
        #        row=vv.grid.YToRow(y)
        gt = vv.grid.GetTable()
        treedict = gt.GetTreeDict()
        if treedict is None:
            return
        if row == -1:
            name = 'link'
            p = 1
            name1 = name+str(p)
            while treedict.getvar(name1) is not None:
                p = 1+p
                name1 = name+str(p)
            treedict.setvar(name1, data)

        else:
            name = (treedict.get_varlist())[row]
            treedict.setvar(name, data)

        vv.fill_list(treedict)
        item = pv.dt1._prev_item
        if pv.dt1._prev_item is not None:
            pv.tree.SetItemDropHighlight(
                pv.dt1._prev_item, False)

        pv.tree.UnselectAll()
        if item is not None:
            pv.tree.SelectItem(item)


class ShellVarViewerPopUp(wx.Menu):
    def __init__(self, parent):
        super(ShellVarViewerPopUp, self).__init__()
        self.parent = parent
        labels = self._cb_label()
        menus = []
        for i, l in enumerate(labels):
            def func(evt, parent=parent, idx=i):
                parent._selection[idx] = not parent._selection[idx]
                parent.update_table()
            menus.append((l, func, None))
        gt = self.parent.grid.GetTable()
        txt = ['*', '*']
        if gt._sort == 0:
            txt[0] = '^'
        elif gt._sort == 1:
            txt[1] = '^'
        menus.extend([('+Sort', None, None),
                      (txt[0] + 'Up',   self.onSortUp, None),
                      (txt[1] + 'Down', self.onSortDown, None),
                      ('!',    None, None)])
        BuildPopUpMenu(self, menus)

    def _cb_label(self):
        names = ['variables', 'func', 'module']
        onoffs = ['hide ' if x else 'show ' for x in self.parent._selection]
        return [onoff+name for onoff, name in zip(onoffs, names)]

    def onSortUp(self, e):
        gt = self.parent.grid.GetTable()
        if gt._sort == 0:
            gt._sort = -1
        else:
            gt._sort = 0
        self.parent.Refresh()

    def onSortDown(self, e):
        gt = self.parent.grid.GetTable()
        if gt._sort == 1:
            gt._sort = -1
        else:
            gt._sort = 1
        self.parent.Refresh()


class ShellVarViewerGridTable(GridTableBase):
    def __init__(self, obj, grid):
        GridTableBase.__init__(self)
        self._obj = []
        self._grid = grid
        self._sort = -1
        self.currentRows = 0
        self.currentCols = self.GetNumberCols()

    def getGrid(self):
        return self._grid

    def set_variable_list(self, obj):
        self._obj = obj
        self.ResetView()

    def GetNumberRows(self):
        """Return the number of rows in the grid"""
        return len(self._obj)

    def GetNumberCols(self):
        """Return the number of columns in the grid"""
        return 3

    def IsEmptyCell(self, row, col):
        """Return True if the cell is empty"""
        return False

    def GetTypeName(self, row, col):
        """Return the name of the data type of the value in the cell"""
        # return None
        return 'string'

    def GetValue(self, row, col):
        """Return the value of a cell"""
        if row >= len(self._obj):
            return ''
        name = self.get_row_name(row)
        for x in self._obj:
            if x[0] == name:
                return x[col+1]
#        return self._obj[row][col+1]

    def SetValue(self, row, col, value):
        """Set the value of a cell"""
        pass

    def GetColLabelValue(self, col):
        if col == 0:
            return 'type'
        if col == 1:
            return 'value'
        if col == 2:
            return 'shape'

    def GetRowLabelValue(self, row):
        if row >= len(self._obj):
            return ''
        return self.get_row_name(row)

    def get_row_name(self, row):
        #        print self._obj
        #        if obj is None: return ''
        names = [x[0] for x in self._obj]
        if row >= len(names):
            return ''
        if self._sort == -1:
            return names[row]
        elif self._sort == 0:
            return sorted(names)[row]
        elif self._sort == 1:
            return [x for x in reversed(sorted(names))][row]

    def GetAttr(self, row, col, someExtraParameter):
        attr = wx.grid.GridCellAttr()
        if (col == 1 or col == 0):
            attr.SetReadOnly(1)
            return attr
        return None

    def ResetView(self):
        """Trim/extend the control's rows and update all values"""
        grid = self.getGrid()
        grid.BeginBatch()
        for current, new, delmsg, addmsg in [
            (self.currentRows, self.GetNumberRows(
            ), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self.currentCols, self.GetNumberCols(
            ), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(self, delmsg, new, current-new)
                # for i in range(current-new):
                grid.ProcessTableMessage(msg)
                self.currentRows = new
            elif new > current:
                msg = wx.grid.GridTableMessage(self, addmsg,  new-current)
                grid.ProcessTableMessage(msg)
                self.currentRows = new
        self.UpdateValues()
        if len(self._obj) == 0:
            ml = 8
        else:
            ml = max([len(x[0]) for x in self._obj])
            grid.SetRowLabelSize(ml*10)  # 10 is an ad-hoc number
        grid.EndBatch()

        # print 'current row', self.currentRows

        # The scroll bars aren't resized (at least on windows)
        # Jiggling the size of the window rescales the scrollbars
        w, h = grid.GetSize()
        grid.SetSize((w+1, h))
        grid.SetSize((w, h))

        grid.ForceRefresh()

    def fit_col_width(self):
        grid = self.getGrid()
        w, h = grid.GetClientSize()
        d = w - grid.GetRowLabelSize()-grid.GetColSize(1) - grid.GetColSize(0)
        grid.SetColSize(2, max([d, 80]))

    def UpdateValues(self):
        """Update all displayed values"""
        msg = wx.grid.GridTableMessage(self,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.getGrid().ProcessTableMessage(msg)
        self.getGrid().ClearSelection()

    def IssueDoDragDrop(self, row):
        if len(self._obj) == 0:
            return ""
        text = self.get_row_name(row)

        app = self._grid.GetTopLevelParent()
        app._text_clip = text
        if not wx.TheClipboard.IsOpened():
            wx.TheClipboard.Open()
            data = wx.TextDataObject()
            data.SetText(text)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()

        tdo = wx.TextDataObject(text)
        src = self._grid.GetGridRowLabelWindow()
        tds = wx.DropSource(src)
        tds.SetData(tdo)
        tds.DoDragDrop(True)


class ShellVarViewer(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        #        self.st1 = wx.StaticText(self, label=' = ')
        #        self.ct1 = wx.TextCtrl(self, wx.ID_ANY, value="", style=wx.TE_PROCESS_ENTER)

        self._selection = [True, False, False]  # vars, func, module, class
        # sizer0=wx.BoxSizer(wx.HORIZONTAL)
        # sizer0.Add(self.st1, 0, wx.ALL, 1)
        # sizer0.Add(self.ct1, 0, wx.ALL, 1)
        self.grid = _PropertyGrid(self)
#        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(3, 0)
        self.grid.SetTable(ShellVarViewerGridTable(None, self.grid))
        #   self.ct1.SetDropTarget(wx.TextDropTarget())

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        modes = ['copy', 'paste', 'trash']
        for mode in modes:
            if mode == 'text':
                self.tc_path = TextCtrlPath(self, wx.ID_ANY, '')
                self.tc_path.pv = self
#              self.tc_path.Bind(wx.EVT_KEY_DOWN, self.onKeyPressed, self.tc_path)
                bottom.Add(self.tc_path, 1, wx.EXPAND | wx.ALL, 1)
            else:
                from ifigure.ifigure_config import icondir
                path = os.path.join(icondir, '16x16', mode+'.png')
                image = wx.Image(path, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
                bt = wx.BitmapButton(self, -1, image)
                bt.SetToolTip(wx.ToolTip(mode))
                if mode == 'trash':
                    bottom.AddStretchSpacer()
                    bottom.Add(bt, 0)
                else:
                    bottom.Add(bt, 0)

                def func(e, mode=mode): return self.onButton(e, mode)
                self.Bind(wx.EVT_BUTTON, func, bt)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        #   sizer.Add(sizer0, 0, wx.EXPAND, 0)
        sizer.Add(self.grid, 1, wx.EXPAND, 0)
        sizer.Add(bottom, 0, wx.EXPAND)
        #   self.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.onEdit)
        #   self.ct1.Bind(wx.EVT_TEXT_ENTER, self.onEditValue)

        rowWindow = self.grid.GetGridRowLabelWindow()
        colWindow = self.grid.GetGridColLabelWindow()
        self._potentialDrag = False
        self._startrow = None  # param for drag'n'drop
        self._startrow2 = -1  # param for popup menu
        rowWindow.Bind(wx.EVT_LEFT_DOWN, self.OnDragGridLeftDown)
        rowWindow.Bind(wx.EVT_LEFT_UP, self.OnDragGridLeftUp)
        rowWindow.Bind(wx.EVT_RIGHT_UP, self.OnRightRelease)
        rowWindow.Bind(wx.EVT_RIGHT_DOWN, self.OnRightPress)

        colWindow.Bind(wx.EVT_RIGHT_UP, self.OnRightRelease)
        colWindow.Bind(wx.EVT_RIGHT_DOWN, self.OnRightPress)

        self.Bind(wx.grid.EVT_GRID_COL_SIZE, self.onGridSize)
        self.grid.Bind(wx.EVT_SIZE, self.onGridSize)

    #   self.Bind(wx.grid.EVT_GRID_BEGIN_DRAG, self.OnBeginDrag)

    def onButton(self, evt, mode):
        from ifigure.ifigure_config import vv_scratch
        import ifigure.utils.pickle_wrapper as pickle

        idx = self.grid.GetSelectedRows()
        if len(idx) == 0 and mode != 'paste':
            return
        gt = self.grid.GetTable()
        obj = gt._obj

        if mode == 'copy':
            names = [str(self.grid.GetRowLabelValue(d)) for d in idx]
            self.GetTopLevelParent().set_status_text(
                'Copy ' + ', '.join(names), timeout=3000)
            try:
                fid = open(vv_scratch, 'wb')
                data = {n: self.shell.get_shellvar(n) for n in names}
                pickle.dump(data, fid)
                fid.close()
            except:
                dialog.showtraceback(parent=self,
                                     txt='Failed to copy',
                                     title='Failed to copy',
                                     traceback=traceback.format_exc())
        elif mode == 'paste':
            fid = open(vv_scratch, 'rb')
            data = pickle.load(fid)
            fid.close()
            for key in data:
                if self.shell.has_shellvar(key):
                    dlg = wx.MessageDialog(None,
                                           'Do you want to overwrite '+key + '?',
                                           'Variable already existws',
                                           wx.OK | wx.CANCEL)
                    ret = dlg.ShowModal()
                    dlg.Destroy()
                    if ret != wx.ID_OK:
                        continue
                self.GetTopLevelParent().set_status_text('Paste tree variable', timeout=3000)
                self.shell.set_shellvar(key, data[key])
            self.update()
        elif mode == 'trash':
            names = [str(self.grid.GetRowLabelValue(d)) for d in idx]
            dlg = wx.MessageDialog(None,
                                   'Do you want to delete ' +
                                   ', '.join(names) + '?',
                                   'Deleting variable',
                                   wx.OK | wx.CANCEL)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret == wx.ID_OK:
                for n in names:
                    self.shell.del_shellvar(n)
                self.GetTopLevelParent().set_status_text(
                    'Deltete '+', '.join(names), timeout=3000)
                wx.CallAfter(self.update)

    def onGridSize(self, evt):
        self.grid.GetTable().fit_col_width()
        self.grid.ForceRefresh()

    def update(self, shell=None):
        if shell is not None:
            self.shell = shell
        self._varlist = self.shell.list_locals()
        self.update_table()
        #        self.ct1.SetValue('')

    def update_table(self):
        if self._selection[0]:
            l1 = [v for v in self._varlist if (
                v[1] != 'function' and v[1] != 'module' and v[1] != 'class')]
        else:
            l1 = []
        if self._selection[1]:
            l1.extend([v for v in self._varlist if v[1] == 'function'])
        if self._selection[2]:
            l1.extend([v for v in self._varlist if v[1] == 'module'])
        self.grid.GetTable().set_variable_list(l1)

    def SetDropTarget(self, tg):
        self.grid.GetGridWindow().SetDropTarget(tg)
#       uncomment this makes crush on MacOSX
#        self.grid.GetGridRowLabelWindow().SetDropTarget(tg)

    def OnDragGridLeftDown(self, e):
        # this is to convert y to row. need to adjust
        # scroll.....
        row = self.grid.YToRow(e.GetY() + self.grid.GetViewStart()[1] *
                               self.grid.GetScrollPixelsPerUnit()[1])
        if row == -1:
            return
        self._startrow = row
        self._potentialDrag = True
        rowWindow = self.grid.GetGridRowLabelWindow()
        rowWindow.Bind(wx.EVT_MOTION, self.OnDragGridMotion)

        e.Skip()

    def OnDragGridLeftUp(self, e):
        """We are not dragging anymore, so unset the potentialDrag flag"""
        self._potentialDrag = False
        rowWindow = self.grid.GetGridRowLabelWindow()
        rowWindow.Unbind(wx.EVT_MOTION)

        e.Skip()

    def OnRightPress(self, e):
        row = self.grid.YToRow(e.GetY() + self.grid.GetViewStart()[1] *
                               self.grid.GetScrollPixelsPerUnit()[1])
#        row=self.grid.YToRow(e.GetY())
        self._startrow2 = row

    def OnRightRelease(self, e):
        row = self.grid.YToRow(e.GetY() + self.grid.GetViewStart()[1] *
                               self.grid.GetScrollPixelsPerUnit()[1])
#        row=self.grid.YToRow(e.GetY())
        if self._startrow2 != row:
            # press and release happend at different row
            self._startrow2 = row
            return

        m = ShellVarViewerPopUp(self)
        self.PopupMenu(m,
                       e.GetPosition())
        m.Destroy()

    def OnDragGridMotion(self, e):
        rowWindow = self.grid.GetGridRowLabelWindow()
        rowWindow.Unbind(wx.EVT_MOTION)
        self._potentialDrag = False
        if self._startrow is None:
            return

        gt = self.grid.GetTable()
        gt.IssueDoDragDrop(self._startrow)

        e.Skip()

    def setdroptarget(self, proj_viewer):
        dt2 = ShellVarViewerDropTarget(proj_viewer)
        self.SetDropTarget(dt2)

    def Copy(self, e=None):
        idx = self.grid.GetSelectedRows()
        if len(idx) == 0:
            return
        text = str(self.grid.GetRowLabelValue(idx[0]))

        if not wx.TheClipboard.IsOpened():
            wx.TheClipboard.Open()
            data = wx.TextDataObject()
            data.SetText(text)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()

    def Paste(self, e=None):
        '''
        can not paste to shellvar viewer
        '''
        pass
