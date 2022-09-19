from __future__ import print_function
import weakref
import os
import traceback
import wx
import wx.grid
from ifigure.utils.eval_node import EvalNode
from ifigure.utils.cbook import ImageFiles, Write2Main, BuildPopUpMenu
from distutils.version import LooseVersion
from ifigure.utils.cbook import text_repr
import ifigure.widgets.dialog as dialog

from ifigure.utils.wx3to4 import isWX3, GridTableBase, TextEntryDialog

isWX_before_2_9 = LooseVersion(wx.__version__) < LooseVersion("2.9")

font_h = None
font_w = None
font = None


def set_default_font():
    size = 12
    font = wx.Font(pointSize=size, family=wx.DEFAULT,
                   style=wx.NORMAL,  weight=wx.NORMAL,
                   faceName='Consolas')
    globals()['font_label'] = wx.Font(pointSize=size, family=wx.DEFAULT,
                                      style=wx.NORMAL,  weight=wx.BOLD,
                                      faceName='Consolas')
    dc = wx.ScreenDC()
    dc.SetFont(font)
    w, h = dc.GetTextExtent('A')
    globals()['font_h'] = h*1.5
    globals()['font_w'] = w
    globals()['font'] = font


def get_varlist(td):
    if hasattr(td, 'get_shownvar'):
        names = td.get_shownvar()
    else:
        names = td.get_varlist()
    return names


class _PropertyGrid(wx.grid.Grid):
    def __init__(self, *args, **kargs):
        wx.grid.Grid.__init__(self, *args, **kargs)
        self.Bind(wx.EVT_SIZE, self.onSizeEvent)
#         colWindow = self.GetGridColLabelWindow()
#         colWindow.Bind(wx.EVT_PAINT, self.OnColPaint)

    def onSizeEvent(self, evt):
        evt.Skip()
        self.ForceRefresh()

    def SetTable(self, object, *attributes):
        if isWX3:
            self.tableRef = weakref.ref(object)
        else:
            self.tableRef = object
        return wx.grid.Grid.SetTable(self, object, *attributes)

    def GetTable(self):
        if isWX3:
            return self.tableRef()
        else:
            return self.tableRef

    # def OnPaint(self, evt):
    #    print("Here")


class VarViewerGValue(object):
    '''
    varialbe which can be edit by 
    varviwer
    '''

    def __init__(self, var, note):
        self._var = var
        self._note = note
        self._allow_eval = False

    def get_varlist(self):
        return list(self._var)

    def hasvar(self, name):
        return name in self._var

    def setvar(self, *args):
        if len(args) == 2:
            self._var[args[0]] = args[1]
        if len(args) == 1:
            if isinstance(args[0], dict):
                self._var = args[0]

    def getvar(self, name=None):
        if name is None:
            return self._var
        try:
            return self._var[name]
        except KeyError:
            return None

    def setnote(self, *args):
        if len(args) == 2:
            try:
                a = self._var[args[0]]
            except KeyError:
                return
            self._note[args[0]] = args[1]
        if len(args) == 1:
            self._note = args[0]

    def getnote(self, name=None):
        if name is None:
            return self._note
        try:
            return self._note[name]
        except KeyError:
            return ''

    def delvar(self, name):
        try:
            del self._var[name]
        except KeyError:
            pass
        try:
            del self._note[name]
        except KeyError:
            pass

    def get_drag_text2(self, key):
        ''' 
        text for dnd from var viewer. should be
        implemented at derived class
        '''
        pass


class TextDT(wx.TextDropTarget):
    pass


class VarViewerGDropTarget(wx.TextDropTarget):
    # obj is proj_viewer
    def __init__(self, obj):
        wx.TextDropTarget.__init__(self)
        self.obj = obj

    def OnDropText(self, x, y, indata):
        print("drop target")
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
            name = (get_varlist(treedict))[row]
            treedict.setvar(name, data)

        vv.fill_list(treedict)
        item = pv.dt1._prev_item
        if pv.dt1._prev_item is not None:
            pv.tree.SetItemDropHighlight(
                pv.dt1._prev_item, False)

        pv.tree.UnselectAll()
        if item is not None:
            pv.tree.SelectItem(item)


class VarViewerGPopUp(wx.Menu):
    def __init__(self, parent):
        super(VarViewerGPopUp, self).__init__()
        self.parent = parent
        row = self.parent._startrow2
        if row != -1:
            gt = self.parent.grid.GetTable()
            txt = ['*', '*']
            if gt.sort == 0:
                txt[0] = '^'
            elif gt.sort == 1:
                txt[1] = '^'
            menus = [('Add...',    self.onAdd, None),
                     ('Duplicate...', self.onDuplicate, None),
                     ('Delete', self.onDelete, None),
                     ('Rename...', self.onRename, None),
                     ('+Sort', None, None),
                     (txt[0] + 'Up',   self.onSortUp, None),
                     (txt[1] + 'Down', self.onSortDown, None),
                     ('!',    None, None)]

            obj = gt.GetTreeDict()
            name = (get_varlist(obj))[row]
            if hasattr(obj, '_local_vars'):
                if name in obj._local_vars:
                    menus.append(('^Ignore Global', self.onToggleLocal, None))
                else:
                    menus.append(('*Ignore Global', self.onToggleLocal, None))
        else:
            menus = [('Add...',    self.onAdd, None), ]
        BuildPopUpMenu(self, menus)

    def onSortUp(self, e):
        gt = self.parent.grid.GetTable()
        if gt.sort == 0:
            gt.sort = -1
        else:
            gt.sort = 0
        self.parent.Refresh()

    def onSortDown(self, e):
        gt = self.parent.grid.GetTable()
        if gt.sort == 1:
            gt.sort = -1
        else:
            gt.sort = 1
        self.parent.Refresh()

    def onDuplicate(self, e):
        row = self.parent._startrow2
        if row == -1:
            return
        gt = self.parent.grid.GetTable()
        obj = gt.GetTreeDict()
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)
        dlg = TextEntryDialog(self.parent.GetTopLevelParent(),
                              "Enter the name of variable", "Duplicate variable", name+"_duplicated")
        if dlg.ShowModal() == wx.ID_OK:
            new_name = str(dlg.GetValue())
            if new_name != name:
                var = obj.getvar(name)
                obj.setvar(new_name, var)
#               obj.delvar(name)
                gt.SetTreeDict(obj)
        dlg.Destroy()

    def onAdd(self, e):
        row = self.parent._startrow2
        dlg = TextEntryDialog(self.parent.GetTopLevelParent(),
                              "Enter the name of variable", "Add variable", "")
        if dlg.ShowModal() == wx.ID_OK:
            new_name = str(dlg.GetValue())
            gt = self.parent.grid.GetTable()
            obj = gt.GetTreeDict()
            if row == -1:
                obj.setvar(new_name, None)
                gt.SetTreeDict(obj)
            else:
                name = (get_varlist(obj))[row]
                name = gt.get_row_name(row)
                if name.count(new_name) == 0:
                    obj.setvar(new_name, None)
                    gt.SetTreeDict(obj)
                else:
                    print("variable "+new_name + " exist!")
        dlg.Destroy()

    def onDelete(self, e):
        row = self.parent._startrow2
        if row == -1:
            return

        gt = self.parent.grid.GetTable()
        obj = gt.GetTreeDict()
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)

        ret = dialog.message(parent=self.parent.GetTopLevelParent(),
                             message='Do you want to delete ' + name + '?',
                             title="Delete variable",
                             style=4)
        if ret != 'yes':
            return
        obj.delvar(name)
        if hasattr(obj, '_local_vars'):
            if name in obj._local_vars:
                obj._local_vars.remove(name)
        gt.SetTreeDict(obj)

    def onToggleLocal(self, e):
        row = self.parent._startrow2
        if row == -1:
            return
        gt = self.parent.grid.GetTable()
        obj = gt.GetTreeDict()
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)
        if name in obj._local_vars:
            obj._local_vars.remove(name)
        else:
            obj._local_vars.append(name)

    def onRename(self, e):
        row = self.parent._startrow2
        if row == -1:
            return
        gt = self.parent.grid.GetTable()
        obj = gt.GetTreeDict()
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)

        dlg = TextEntryDialog(self.parent.GetTopLevelParent(),
                              "Enter the name of variable", "Add variable", name+"_rename")
        if dlg.ShowModal() == wx.ID_OK:
            new_name = str(dlg.GetValue())
            if new_name != name:
                var = obj.getvar(name)
                obj.setvar(new_name, var)
                obj.delvar(name)
                gt.SetTreeDict(obj)
                if (hasattr(obj, '_local_vars') and
                        name in obj._local_vars):
                    obj._local_vars.remove(name)
                    obj._local_vars.append(new_name)
        dlg.Destroy()


class VarViewerGridTable(GridTableBase):
    def __init__(self, obj, grid):
        GridTableBase.__init__(self)

        class Tmp(object):
            pass
        t = Tmp()
        self._obj = weakref.ref(t)
        del t
        self.sort = -1
        self._grid = grid
        self.currentRows = 0
        self.currentCols = self.GetNumberCols()

        self.SetTreeDict(obj)

    def getGrid(self):
        return self._grid

    def SetTreeDict(self, obj):
        if obj is None:
            class Tmp(object):
                pass
            obj = Tmp()
            self._obj = weakref.ref(obj)
            del obj
        else:
            self._obj = weakref.ref(obj)
        self.ResetView()

    def GetTreeDict(self):
        return self._obj()

    def GetNumberRows(self):
        """Return the number of rows in the grid"""
        obj = self._obj()
        if obj is None:
            return 0
        return len(obj.getvar())

    def GetNumberCols(self):
        """Return the number of columns in the grid"""
        return 4

    def IsEmptyCell(self, row, col):
        """Return True if the cell is empty"""
        return False

    def GetTypeName(self, row, col):
        """Return the name of the data type of the value in the cell"""
        # return None
        return 'string'

    def GetValue(self, row, col):
        """Return the value of a cell"""
        obj = self._obj()
        if obj is None:
            return ""
        names = get_varlist(obj)
        name = self.get_row_name(row)
        if row >= len(names):
            return ''
        if col == 0:
            val = obj.getvar(name)
            txt = text_repr(val)
            return txt
        if col == 1:
            val = obj.getvar(name)
            try:
                if val.startswith('='):
                    return "expression"
            except:
                pass
            #typstr = str(type(val))
            #txt = typstr[5:]
            #txt = txt[:-1]
            return type(val).__name__
        if col == 2:
            val = obj.getvar(name)
            if hasattr(val, 'shape'):
                return str(val.shape)
            else:
                return ''
        if col == 3:
            txt = obj.getnote(name)
            from ifigure.mto.py_code import PyParam
            if isinstance(obj, PyParam):
                path = obj.eval_all_keys(path=True)
                if names[row] in path:
                    arr = path[name]
                    if arr[-1][1] is not obj:
                        txt = txt + '('+arr[-1][1].get_full_path() + ')'
            return txt

        # self._list_str.append(obj.get_full_path()+'.getvar("'+key+'")')
        # self._keys=varss.keys()

    def SetValue(self, row, col, value):
        """Set the value of a cell"""
        pass

    def GetColLabelValue(self, col):
        if col == 0:
            v = 'value'
        elif col == 1:
            v = 'type'
        elif col == 2:
            v = 'shape'
        elif col == 3:
            v = 'description'
#        v = v+ u'\u2206'
        return v

    def GetRowLabelValue(self, row):
        obj = self._obj()
        if obj is None:
            return ""
        names = get_varlist(obj)
        if row >= len(names):
            super(VarViewerGridTable, self).GetRowLabelValue(row)
        return self.get_row_name(row)

    def get_row_name(self, row):
        obj = self._obj()
        if obj is None:
            return ''
        names = get_varlist(obj)
        if row >= len(names):
            return ''
        if self.sort == -1:
            return names[row]
        elif self.sort == 0:
            return sorted(names)[row]
        elif self.sort == 1:
            return [x for x in reversed(sorted(names))][row]

    def GetAttr(self, row, col, someExtraParameter):
        attr = wx.grid.GridCellAttr()
        obj = self._obj()
        if obj is None or row >= len(get_varlist(obj)):
            super(VarViewerGridTable, self).GetAttr(row, col,
                                                    someExtraParameter)
        if (col == 1 or col == 0 or col == 2):
            attr.SetReadOnly(1)
        if obj is not None:
            name = self.get_row_name(row)
            from ifigure.mto.py_code import PyParam
            if isinstance(obj, PyParam):
                path = obj.eval_all_keys(path=True)
                if name in path:
                    arr = path[name]
                    if arr[-1][1] is not obj:
                        attr.SetBackgroundColour('#707070')
                if name in obj._local_vars:
                    attr.SetBackgroundColour('#ffff00')
        return attr

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
        obj = self._obj()
        if obj is not None:
            if len(get_varlist(obj)) == 0:
                ml = 8
            else:
                ml = max([len(x) for x in get_varlist(obj)])
#           grid.SetRowLabelSize(ml*10) #10 is an ad-hoc number
            grid.SetRowLabelSize((ml+2)*(font_w)+10)
        grid.EndBatch()

        # print 'current row', self.currentRows

        # The scroll bars aren't resized (at least on windows)
        # Jiggling the size of the window rescales the scrollbars
        h, w = grid.GetSize()
        grid.SetSize((h+1, w))
        grid.SetSize((h, w))
        grid.ForceRefresh()

    def fit_col_width(self):
        grid = self.getGrid()
        w, h = grid.GetClientSize()
        d = (w - grid.GetRowLabelSize()-grid.GetColSize(1) - grid.GetColSize(0)
             - grid.GetColSize(2))
        grid.SetColSize(3, max([d, 80]))

    def UpdateValues(self):
        """Update all displayed values"""
        msg = wx.grid.GridTableMessage(self,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.getGrid().ProcessTableMessage(msg)
        self.getGrid().ClearSelection()

    def IssueDoDragDrop(self, row):
        obj = self._obj()
        if obj is None:
            return ""

        name = self.get_row_name(row)
        text = obj.get_drag_text2(name)

        app = self._grid.GetTopLevelParent()
        app._text_clip = text

        tdo = wx.TextDataObject(text)
        src = self._grid.GetGridRowLabelWindow()
        tds = wx.DropSource(src)
        tds.SetData(tdo)
        tds.DoDragDrop(True)


class VarViewerG(wx.Panel):
    def __init__(self, parent):
        set_default_font()
        wx.Panel.__init__(self, parent)
        st1 = wx.StaticText(self, label=' = ')
        self.ct1 = wx.TextCtrl(self, value="",
                               style=wx.TE_PROCESS_ENTER)
        self.bx1 = wx.CheckBox(self, -1, 'Expression', (10, 10))
        sizer0 = wx.BoxSizer(wx.HORIZONTAL)
        sizer0.Add(st1, 0, wx.ALL, 1)
        sizer0.Add(self.ct1, 1, wx.ALL | wx.EXPAND, 1)
        sizer0.Add(self.bx1, 0, wx.ALL, 1)
        self.grid = _PropertyGrid(self)

        self.grid.CreateGrid(3, 0)
        self.grid.SetDefaultCellFont(font)
        self.grid.SetLabelFont(globals()['font_label'])
        self.grid.SetColLabelSize(int(font_h))
        self.grid.SetDefaultRowSize(int(font_h), True)
        self.grid.EnableDragColSize(True)
        self.grid.SetTable(VarViewerGridTable(None, self.grid))
        self.ct1.SetDropTarget(TextDT())

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
        sizer.Add(sizer0, 0, wx.EXPAND, 0)
        sizer.Add(self.grid, 1, wx.EXPAND, 0)
        sizer.Add(bottom, 0, wx.EXPAND)

        if isWX_before_2_9:
            pass
        else:
            self.Bind(wx.grid.EVT_GRID_CELL_CHANGING, self.onEdit)
        self.ct1.Bind(wx.EVT_TEXT_ENTER, self.onEditValue)

        rowWindow = self.grid.GetGridRowLabelWindow()
        self._potentialDrag = False
        self._startrow = None  # param for drag'n'drop
        self._startrow2 = -1  # param for popup menu
        rowWindow.Bind(wx.EVT_LEFT_DOWN, self.OnDragGridLeftDown)
        rowWindow.Bind(wx.EVT_LEFT_UP, self.OnDragGridLeftUp)
        rowWindow.Bind(wx.EVT_RIGHT_UP, self.OnRightRelease)
        rowWindow.Bind(wx.EVT_RIGHT_DOWN, self.OnRightPress)
#        rowWindow.Bind(wx.EVT_MOTION, self.OnRightRelease)

        self.grid.Bind(wx.EVT_SIZE, self.onGridSize)
        self.Bind(wx.grid.EVT_GRID_COL_SIZE, self.onGridSize)
#        self.Bind(wx.grid.EVT_GRID_BEGIN_DRAG, self.OnBeginDrag)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, lambda x: None)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.onGridLClick)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.onGridLDClick)

        # this allows to select row always...
        try:
            self.grid.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        except:  # wxPython 4.1.0
            self.grid.SetSelectionMode(wx.grid.Grid.GridSelectRows)

    def onGridLClick(self, evt):
        row = evt.GetRow()
        self._startrow = row

        self.grid.SelectRow(row)
        # self.grid.SetSelectionMode(wx.grid.Grid.wxGridSelectCells)
        self.set_expression_field(row)
        evt.Skip()

    def onGridLDClick(self, evt):
        print('Grid DClick')
        evt.Skip()

    def onButton(self, evt, mode):
        from ifigure.ifigure_config import vv_scratch
        import ifigure.utils.pickle_wrapper as pickle

        idx = self.grid.GetSelectedRows()
        if len(idx) == 0 and mode != 'paste':
            return
        gt = self.grid.GetTable()
        obj = gt.GetTreeDict()

        if mode == 'copy':
            name = str(self.grid.GetRowLabelValue(idx[0]))
            names = [str(self.grid.GetRowLabelValue(d)) for d in idx]

            self.GetTopLevelParent().set_status_text(
                'Copy ' + ', '.join(names), timeout=3000)
            try:
                fid = open(vv_scratch, 'wb')
                #data = {name: obj.getvar(name)}
                data = {n: obj.getvar(n) for n in names}
                pickle.dump(data, fid)
                fid.close()
            except:
                dialog.showtraceback(parent=self,
                                     txt='Failed to copy',
                                     title='Failed to copy',
                                     traceback=traceback.format_exc())
        elif mode == 'paste':
            if not os.path.exists(vv_scratch):
                dialog.showtraceback(parent=self,
                                     txt='paste data does not exists',
                                     title='Failed to paste',
                                     traceback='')
                return
            fid = open(vv_scratch, 'rb')
            data = pickle.load(fid)
            fid.close()
            for key in data:
                if obj.hasvar(key):
                    dlg = wx.MessageDialog(None,
                                           'Do you want to overwrite '+key + '?',
                                           'Variable already existws',
                                           wx.OK | wx.CANCEL)
                    ret = dlg.ShowModal()
                    dlg.Destroy()
                    if ret != wx.ID_OK:
                        continue
                self.GetTopLevelParent().set_status_text('Paste tree variable', timeout=3000)
                obj.setvar(key, data[key])
                obj._var_changed = True
            self.update()
        elif mode == 'trash':
            name = str(self.grid.GetRowLabelValue(idx[0]))
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
                    obj.delvar(n)
                obj._var_changed = True
                self.GetTopLevelParent().set_status_text('Deltete ' +
                                                         ', '.join(names), timeout=3000)
                wx.CallAfter(self.update)

#        text = obj.get_drag_text2(name)

    def onGridSize(self, evt):
        self.grid.GetTable().fit_col_width()
        self.grid.ForceRefresh()

    def fill_list(self, obj):  # obj = TREEDICT
        gt = self.grid.GetTable()
        gt.SetTreeDict(obj)
        self.ct1.SetValue('')

    def update(self):
        gt = self.grid.GetTable()
        cobj = gt.GetTreeDict()
        try:
            if hasattr(cobj, '_var_changed'):
                if cobj._var_changed:
                    #                   print 'Reset Viewer', cobj
                    gt.ResetView()
                cobj._var_changed = False
        except:
            import traceback
            traceback.print_exc()
            pass

    def onEdit(self, e):
        row = e.GetRow()
        col = e.GetCol()

        obj = self.grid.GetTable().GetTreeDict()
        names = get_varlist(obj)

        if col == 3:  # edit desecription
            if row < len(names):
                key = names[row]
#               print e.GetString()
#               print self.grid.GetCellValue(row, col)
                obj._note[key] = str(e.GetString())

        self.fill_list(obj)

    def onEditValue(self, e):
        row = self._startrow
        gt = self.grid.GetTable()
        obj = gt.GetTreeDict()
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)
        if self.bx1.GetValue():
            val = '='+str(self.ct1.GetValue())
        else:
            val = eval(str(self.ct1.GetValue()))
        obj.setvar(name, val)
        self.grid.ForceRefresh()

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

        row = self.grid.YToRow(e.GetY() + self.grid.GetViewStart()[1] *
                               self.grid.GetScrollPixelsPerUnit()[1])
        # row=self.grid.YToRow(e.GetY())
        if row == -1:
            return
        self.set_expression_field(row)
        '''
        gt=self.grid.GetTable()
        obj=gt.GetTreeDict()
        name=(get_varlist(obj))[row]
        name = gt.get_row_name(row)
        val=obj.getvar(name)
        txt=str(val)
        if ((isinstance(val, str) or isinstance(val, unicode)) and
               not val.startswith('=')):
               txt='"'+txt+'"'

        if txt.startswith('='):
           self.ct1.SetValue(txt[1:])
           self.bx1.SetValue(True)
        else:
           self.ct1.SetValue(txt)
           self.bx1.SetValue(False)
        '''
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
        m = VarViewerGPopUp(self)
        self.PopupMenu(m,
                       e.GetPosition())
        m.Destroy()

    def OnDragGridMotion(self, e):
        rowWindow = self.grid.GetGridRowLabelWindow()
        rowWindow.Unbind(wx.EVT_MOTION)
        self._potentialDrag = False
        if self._startrow is None:
            return

        #print("Start drag")
        gt = self.grid.GetTable()
        gt.IssueDoDragDrop(self._startrow)

        e.Skip()

    def setdroptarget(self, proj_viewer):
        dt2 = VarViewerGDropTarget(proj_viewer)
        self.SetDropTarget(dt2)

    def Copy(self, e=None):
        idx = self.grid.GetSelectedRows()
        if len(idx) == 0:
            return
        name = str(self.grid.GetRowLabelValue(idx[0]))
        gt = self.grid.GetTable()
        obj = gt.GetTreeDict()
        text = obj.get_drag_text2(name)

        from ifigure.utils.cbook import SetText2Clipboard
        SetText2Clipboard(text)

    def Paste(self, e=None):
        '''
        can not paste to shellvar viewer
        '''
        pass

    def set_expression_field(self, row):
        gt = self.grid.GetTable()
        obj = gt.GetTreeDict()
        names = get_varlist(obj)
        if len(names) < row:
            return
        name = (get_varlist(obj))[row]
        name = gt.get_row_name(row)
        val = obj.getvar(name)
        txt = str(val)

        from ifigure.utils.cbook import isstringlike
        if (isstringlike(val) and not val.startswith('=')):
            txt = '"'+txt+'"'

        if txt.startswith('='):
            self.ct1.SetValue(txt[1:])
            self.bx1.SetValue(True)
        else:
            self.ct1.SetValue(txt)
            self.bx1.SetValue(False)
