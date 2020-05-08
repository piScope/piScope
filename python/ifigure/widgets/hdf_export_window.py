from __future__ import print_function
import os
import traceback
from collections import OrderedDict
import wx
import wx.dataview as dv
import wx.propgrid as pg
import six
import numpy as np
import time
import weakref
import traceback
try:
    #  for standalone testing (when running python hdf_export_window.py)
    from ifigure.utils.hdf_data_export import build_data,  hdf_data_export, set_all_properties_all, select_unique_properties_all
except:
    pass
import ifigure.events

from ifigure.utils.wx3to4 import PyDeadObjectError, menu_Append
'''
   helper window for HDF export

   HdfExportWindow(parent = <parent window>,
                   page = <figpage objct>)
'''
debug = False


class ObjectData(object):
    def __init__(self, data):
        self.data = data

    def GetData(self):
        return self.data

    def __repr__(self):
        return self.data.__repr__()


class HDFDataModel(dv.PyDataViewModel):
    def __init__(self, **kwargs):
        dv.PyDataViewModel.__init__(self)
        self.dataset = kwargs.pop('dataset', None)
        self.metadata = kwargs.pop('metadata', OrderedDict())
        self.export_flag = kwargs.pop('export_flag')
        # self.objmapper.UseWeakRefs(True)
        self.objs = []
        self.labels = {}

    def getobj(self, labels):
        if labels in self.labels:
            return self.labels[labels], True
        else:
            obj = ObjectData(labels)
            self.labels[labels] = obj
            return obj, False

    def GetChildren(self, parent, children):
        if debug:
            print('GetChildren')
        if not parent:
            num = 0
            for name in six.iterkeys(self.dataset):
                labels = (name,)
                obj, exist = self.getobj(labels)
                # if not exist:
                children.append(self.ObjectToItem(obj))
                if not labels in self.export_flag:
                    self.export_flag[labels] = True
                self.objs.append(obj)
                num = num + 1
            return num
        labels = self.ItemToObject(parent).GetData()
        p = self.dataset[labels[0]]
        for l in labels[1:]:
            p = p[l]
        if isinstance(p, dict):
            num = 0
            for newlabel in sorted(p.keys()):
                x = list(labels)
                x.append(newlabel)
                labels2 = tuple(x)
                obj, exist = self.getobj(labels2)
                # if not exist:
                children.append(self.ObjectToItem(obj))
                if not labels2 in self.export_flag:
                    self.export_flag[labels2] = self.export_flag[labels]
                self.objs.append(obj)
                num = num + 1
            return num
        return 0

    def GetParent(self, item):
        if debug:
            print('GetParent')
        if not item:
            return dv.NullDataViewItem

        ret = dv.NullDataViewItem
        obj = self.ItemToObject(item)
        labels = obj.data
        if len(labels) == 1:
            pass
        else:
            labels = obj.GetData()
            if labels[:-1] in self.labels:
                obj = self.labels[labels[:-1]]
                ret = self.ObjectToItem(obj)
        return ret

    def GetColumnCount(self):
        return 5

    def GetColumnType(self, col):
        mapper = {0: 'string',
                  1: 'bool',
                  2: 'string',
                  3: 'string',
                  4: 'string', }
        return mapper[col]

    def IsContainer(self, item):
        # The hidden root is a container
        if not item:
            return True
        # and if it is dict, the objects are containers
        labels = self.ItemToObject(item).GetData()
        p = self.dataset
        for l in labels:
            p = p[l]
        if isinstance(p, dict):
            return True
        # but everything else are not
        return False

    def GetValue(self, item, col):
        if debug:
            print('GetValue')
        labels = self.ItemToObject(item).GetData()
        p = self.dataset
        for l in labels:
            p = p[l]

        if col == 0:
            v = labels[-1]
            ret = v
        elif col == 1:
            ret = self.export_flag[labels]
        elif col == 2:
            if self.IsContainer(item):
                ret = ''
            else:
                ret = str(p)
                if len(ret) > 50:
                    ret = ret[:50] + '...'
        elif col == 3:
            if self.IsContainer(item):
                ret = ''
            else:
                if hasattr(p, 'shape'):
                    ret = str(p.shape)
                else:
                    ret = ''
        elif col == 4:
            p = 0
            d = self.metadata
            while labels[p] in d:
                d = d[labels[p]]
                dd = OrderedDict()
                for key in six.iterkeys(d):
                    if not isinstance(d[key], dict):
                        dd[key] = d[key]
                ret = str(dd)
                p = p+1
                if len(labels) <= p:
                    break
            else:
                ret = ''
            if self.IsContainer(item) and len(labels) != 1:
                ret = ''
            if ret.startswith('OrderedDict'):
                ret = ret[13:-2]  # tweak a visual ;D
        else:
            raise RuntimeError("unknown col")
        return ret

    def GetAttr(self, item, col, attr):
        labels = self.ItemToObject(item).GetData()
        if col == 0:
            attr.SetColour('blue')
            return True
        else:
            return False

    def SetValue(self, value, item, col):
        if debug:
            print('SetValue')
        labels = self.ItemToObject(item).GetData()
        p = self.dataset
        for l in labels:
            p = p[l]
        if col == 1:
            self.export_flag[labels] = value

            if value:
                for l2 in self.labels:
                    if len(l2) >= len(labels):
                        continue
                    if l2 == labels[:len(l2)]:
                        self.export_flag[l2] = value
                        obj = self.labels[l2]
                        item2 = self.ObjectToItem(obj)
                        self.ValueChanged(item2, col)
            if self.IsContainer(item):
                labels = self.ItemToObject(item).GetData()
                for l2 in self.labels:
                    if len(l2) <= len(labels):
                        continue
                    if l2[:len(labels)] == labels:
                        self.export_flag[l2] = value
                        obj = self.labels[l2]
                        item2 = self.ObjectToItem(obj)
                        self.ValueChanged(item2, col)

    def HasContainerColumns(self, item):
        return True


class HdfExportWindow(wx.Frame):
    def __init__(self, *args, **kargs):
        page = kargs.pop('page', None)
        parent = kargs.pop('parent', None)
        title = kargs.pop('title', 'HDF export')
        path = kargs.pop('path', os.path.join(os.getcwd(), 'data.hdf'))
        dataset = kargs.pop('dataset', None)
        metadata = kargs.pop('metadata', OrderedDict())
        export_flag = kargs.pop('export_flag', {})
        if dataset is None:
            if page is None:
                return
            dataset, metadata, export_flag = build_data(page,
                                                        verbose=False,
                                                        metadata=metadata,
                                                        export_flag=export_flag)
        style = (wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX |
                 wx.RESIZE_BORDER)
        if parent is not None:
            style = style | wx.FRAME_FLOAT_ON_PARENT

        wx.Frame.__init__(self, *args,
                          style=style,
                          title=title, parent=parent,
                          size=(400, 500))

        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.GetSizer().Add(hsizer, 1, wx.EXPAND, 0)
        panel = wx.Panel(self)
        hsizer.Add(panel, 1, wx.EXPAND)

        panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        sizer = panel.GetSizer()
        sizer_h = wx.BoxSizer(wx.HORIZONTAL)

        wildcard = "HDF(hdf)|*.hdf|Any|*.*"
        self.filepicker = wx.FilePickerCtrl(panel,
                                            style=wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL,
                                            path=path,
                                            wildcard=wildcard)
        self.sp = wx.SplitterWindow(panel, wx.ID_ANY,
                                    style=wx.SP_NOBORDER | wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        self.dataviewCtrl = dv.DataViewCtrl(self.sp,
                                            style=(wx.BORDER_THEME
                                                   | dv.DV_ROW_LINES
                                                   | dv.DV_VERT_RULES))

        self.model = HDFDataModel(export_flag=export_flag,
                                  dataset=dataset,
                                  metadata=metadata)
        self.dataviewCtrl.AssociateModel(self.model)

        self.tr = tr = dv.DataViewTextRenderer()
        c0 = dv.DataViewColumn("name",   # title
                               tr,        # renderer
                               0,         # data model column
                               width=200)
        self.dataviewCtrl.AppendColumn(c0)

#        self.dataviewCtrl.AppendTextColumn('name', 0,
#                                           width = 150,
#                                           mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        c1 = self.dataviewCtrl.AppendToggleColumn('export', 1,
                                                  width=70,
                                                  mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        c2 = self.dataviewCtrl.AppendTextColumn('value', 2, width=100,
                                                mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        c3 = self.dataviewCtrl.AppendTextColumn('shape', 3,
                                                mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        #c4 = self.dataviewCtrl.AppendTextColumn('metadata', 4,
        #                                        mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        for c in self.dataviewCtrl.Columns:
            c.Sortable = True
            c.Reorderable = True
        c1.Alignment = wx.ALIGN_CENTER

        #from ifigure.widgets.var_viewerg2 import _PropertyGrid

        self.grid = pg.PropertyGrid(self.sp)

        #self.btn_load = wx.Button(self, label = 'Load')
        self.choices = ['Options...', 'No Property',
                        'Minimum properties',
                        'All properties']
        self.cb = wx.ComboBox(panel, wx.ID_ANY,
                              style=wx.TE_PROCESS_ENTER | wx.CB_READONLY,
                              choices=self.choices)
        self.cb.SetValue(self.choices[0])
        self.btn_export = wx.Button(panel, label='Export...')

        sizer.Add(self.filepicker, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(self.sp, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(sizer_h, 0, wx.EXPAND | wx.ALL, 5)

        #sizer_h.Add(self.btn_load, 0,   wx.EXPAND|wx.ALL, 1)
        sizer_h.Add(self.cb, 0,   wx.EXPAND | wx.ALL, 1)
        sizer_h.AddStretchSpacer(prop=1)
        sizer_h.Add(self.btn_export, 0, wx.EXPAND | wx.ALL, 1)

        self.Layout()
        self.Show()

        self.sp.SetMinimumPaneSize(30)
        self.sp.SplitHorizontally(self.dataviewCtrl, self.grid)
        self.sp.SetSashPosition(300)
#        self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED,
#                  self.onDataChanged, self.dataviewCtrl)
        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED,
                  self.onSelChanged, self.dataviewCtrl)

        # self.Bind(dv.EVT_DATAVIEW_ITEM_COLLAPSING,
        #          self.onCollapsing, self.dataviewCtrl)

        self.grid.Bind(pg.EVT_PG_CHANGED,
                       self.onPGChanged,  self.grid)
        self.Bind(wx.EVT_BUTTON, self.onExport, self.btn_export)
        self.Bind(wx.EVT_COMBOBOX, self.onCBHit, self.cb)
        self.Bind(wx.EVT_CLOSE, self.onWindowClose)

        self.page = page
        wx.GetApp().TopWindow.hdf_export_window = self

    def onCBHit(self, evt):
        flags = self.model.export_flag
        dataset = self.model.dataset
        idx = self.choices.index(str(self.cb.GetValue()))

        self.cb.SetValue(self.choices[0])
        if idx == 1:
            set_all_properties_all(flags, False)
        elif idx == 2:
            select_unique_properties_all(self.page, dataset, flags)
        elif idx == 3:
            set_all_properties_all(flags, True)
        else:
            pass
        self.Refresh()
        evt.Skip()

    def onTD_Selection(self, evt):
        w = evt.GetEventObject()
        if w is self:
            return

        td = evt.GetTreeDict()
        name = self.page.name + '.' + '.'.join(self.page.get_td_path(td)[1:])

        item = self.dataviewCtrl.GetSelection()
        try:
            clabels = self.model.ItemToObject(item).GetData()
        except:
            clabels = (self.page.name, )

        if clabels[0] == name:
            return
        if (name,) in self.model.labels:
            obj, flag = self.model.getobj((name,))
            item = self.model.ObjectToItem(obj)
            self.dataviewCtrl.Select(item)

    def onSelChanged(self, evt):
        # print('onSelChanged')
        item = self.dataviewCtrl.GetSelection()
        try:
            labels = self.model.ItemToObject(item).GetData()
        except:
            self.grid.Clear()
            self.dataviewCtrl.UnselectAll()
            return
        metadata = self.model.metadata
        self.grid_target = None
        p = 0
        d = metadata
        dd = OrderedDict()
        while labels[p] in d:
            d = d[labels[p]]
            dd = OrderedDict()
            for key in six.iterkeys(d):
                if not isinstance(d[key], dict):
                    dd[key] = d[key]
            ret = dd, d
            p = p+1
            if len(labels) <= p:
                break
        else:
            ret = None
        if self.model.IsContainer(item) and len(labels) != 1:
            ret = None
        self.grid.Clear()
        for key in six.iterkeys(dd):
            prop = pg.StringProperty(str(key), value=str(dd[key]))
            self.grid.Append(prop)
        self.grid_target = d

        names = labels[0].split('.')
        if len(names) > 1:
            figobj = self.page
            for name in names[1:]:
                figobj = figobj.get_child(name=name)
            if len(figobj._artists) > 0:
                sel = [weakref.ref(figobj._artists[0])]
                ifigure.events.SendSelectionEvent(figobj, self, sel)
        evt.Skip()

    def onPGChanged(self, evt):
        prop = self.grid.GetSelection()
        if self.grid_target is not None:
            self.grid_target[prop.GetLabel()] = str(prop.GetValue())
        evt.Skip()

    def onExport(self, evt):
        import ifigure.widgets.dialog as dialog
        flags = self.model.export_flag
        dataset = self.model.dataset
        metadata = self.model.metadata
        path = self.filepicker.GetPath()
        try:
            hdf_data_export(data=dataset,
                            metadata=metadata,
                            export_flag=flags,
                            filename=path,
                            verbose=True)
            print('HDF export finished : '+path)
        except:
            dialog.showtraceback(parent=self,
                                 txt='Failed to export HDF',
                                 title='Error during HDF export',
                                 traceback=traceback.format_exc())
        dialog.message(parent=self, style=0,
                       message='Export finished')
        # self.Close()
        evt.Skip()

    def onWindowClose(self, evt):
        wx.GetApp().TopWindow.hdf_export_window = None
        evt.Skip()


if __name__ == '__main__':
    '''
    sample data for testing
    '''
    import sys
    import os
    dataset = OrderedDict()
    dataset['page1'] = {}
    dataset['page1']['property'] = {}
    dataset['page1']['property']['bgcolor'] = 'red'
    dataset['page1']['property']['frame'] = 'False'
    dataset['page1.axes1'] = {}
    dataset['page1.axes1']['property'] = {}
    dataset['page1.axes1']['property']['xlabel'] = 'time'
    dataset['page1.axes1.plot1'] = {}
    dataset['page1.axes1.plot1']['data1'] = {}
    dataset['page1.axes1.plot1']['data1']['xdata'] = np.arange(30)
    dataset['page1.axes1.plot1']['data1']['ydata'] = np.arange(30)

    app = wx.App(redirect=False)
    w = HdfExportWindow(dataset=dataset)
    w.Show()
    app.MainLoop()
