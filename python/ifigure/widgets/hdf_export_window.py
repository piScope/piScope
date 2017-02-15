import os
import traceback
from collections import OrderedDict
import wx
import wx.dataview as dv
import six
import numpy as np
try:
   #  for standalone testing (when running python hdf_export_window.py)
   from ifigure.utils.hdf_data_export import build_data,  hdf_data_export
except:
   pass

'''
   helper window for HDF export

   HdfExportWindow(parent = <parent window>,
                   page = <figpage objct>)
'''
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
        self.export_flag = kwargs.pop('export_flag')
        self.objmapper.UseWeakRefs(True)
        self.objs = []
        self.labels = {}

    def getobj(self, labels):
        if labels in self.labels:
           return self.labels[labels]
        else:
           obj = ObjectData(labels)
           self.labels[labels] = obj
           return obj
    def GetChildren(self, parent, children):
        if not parent:
            num = 0            
            for name in six.iterkeys(self.dataset):
                labels =(name,)
                obj = self.getobj(labels)
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
                obj = self.getobj(labels2)                
                children.append(self.ObjectToItem(obj))
                if not labels2 in self.export_flag:
                    self.export_flag[labels2] = self.export_flag[labels]
                self.objs.append(obj)
                num = num + 1
            return num
        return 0
    
    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem

        ret =  dv.NullDataViewItem
        obj = self.ItemToObject(item)
        labels = obj.data
        if len(labels) == 1:
            pass
        else:
            labels = obj.GetData()
            if labels in self.labels:
                obj = self.labels[labels]
                ret = self.ObjectToItem(obj)
        return ret

    def GetColumnCount(self):
        return 4

    def GetColumnType(self, col):
        mapper = { 0 : 'string',
                   1 : 'bool',                   
                   2 : 'string',
                   3 : 'string',}
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
        if isinstance(p, dict): return True        
        # but everything else are not
        return False            

    def GetValue(self, item, col):
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
                if len(ret) > 50: ret = ret[:50] + '...'
        elif col == 3:
            if self.IsContainer(item):
                ret = ''
            else:
                if hasattr(p, 'shape'):
                    ret = str(p.shape)
                else:
                    ret = ''
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
        labels = self.ItemToObject(item).GetData()
        p = self.dataset        
        for l in labels:
            p = p[l]
        if col == 1:
            self.export_flag[labels] = value
            if value:
                for l2 in self.labels:
                   if len(l2) >= len(labels): continue                   
                   if l2 == labels[:len(l2)]:
                       self.export_flag[l2] = value
                       obj = self.labels[l2]
                       item2 = self.ObjectToItem(obj)
                       self.ValueChanged(item2, col)
            if self.IsContainer(item):
                labels = self.ItemToObject(item).GetData()
                for l2 in self.labels:
                   if len(l2) <= len(labels): continue
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
        title  = kargs.pop('title', 'HDF export')
        path = kargs.pop('path', os.path.join(os.getcwd(), 'data.hdf'))
        self.dataset = kargs.pop('dataset', None)

        if self.dataset is None:
            if page is None:  return
            self.dataset = build_data(page, verbose = False)

        style = (wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|
                 wx.RESIZE_BORDER)
        if parent is not None:
            style = style | wx.FRAME_FLOAT_ON_PARENT
                                
        wx.Frame.__init__(self, *args,
                          style = style, 
                          title = title, parent = parent)

        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.GetSizer().Add(hsizer, 1, wx.EXPAND, 0)
        panel = wx.Panel(self)
        hsizer.Add(panel, 1, wx.EXPAND)

        panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        sizer = panel.GetSizer()
        sizer_h =wx.BoxSizer(wx.HORIZONTAL)

        wildcard = "HDF(hdf)|*.hdf|Any|*.*"
        self.filepicker = wx.FilePickerCtrl(panel,
                                            style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL,
                                            path = path,
                                            wildcard = wildcard)
        self.dataviewCtrl = dv.DataViewCtrl(panel,
                                            style = (wx.BORDER_THEME
                                                     |dv.DV_ROW_LINES
                                                     |dv.DV_VERT_RULES
                                                     |dv.DV_MULTIPLE))
        self.export_flag = {}
        self.model = HDFDataModel(export_flag = self.export_flag,
                             dataset = self.dataset)
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
                                             width= 70,
                                             mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        c2 = self.dataviewCtrl.AppendTextColumn('value', 2, width = 100,
                                           mode=dv.DATAVIEW_CELL_ACTIVATABLE)       
        c3 = self.dataviewCtrl.AppendTextColumn('shape', 3,
                                           mode=dv.DATAVIEW_CELL_ACTIVATABLE)       
        for c in self.dataviewCtrl.Columns:
            c.Sortable = True
            c.Reorderable = True
        c1.Alignment = wx.ALIGN_CENTER

        #self.btn_load = wx.Button(self, label = 'Load')
        self.btn_export = wx.Button(panel, label = 'Export...')

        
        sizer.Add(self.filepicker, 0, wx.EXPAND|wx.ALL, 1)        
        sizer.Add(self.dataviewCtrl, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(sizer_h, 0, wx.EXPAND|wx.ALL|wx.ALIGN_RIGHT, 5)        


        #sizer_h.Add(self.btn_load, 0,   wx.EXPAND|wx.ALL, 1)
        sizer_h.AddStretchSpacer(prop = 1)
        sizer_h.Add(self.btn_export, 0, wx.EXPAND|wx.ALL, 1)


        self.Layout()
        self.Show()

      
#        self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED,
#                  self.onDataChanged, self.dataviewCtrl)
        self.Bind(wx.EVT_BUTTON, self.onExport, self.btn_export)
#    def onDataChanged(self, evt):
#        self.dataviewCtrl.Refresh()
#        evt.Skip()
    def onExport(self, evt):
        import ifigure.widgets.dialog as dialog        
        flags = self.export_flag
        path  = self.filepicker.GetPath()

        try:
            hdf_data_export(data =self.dataset,
                        export_flag = flags,
                        filename = path,
                        verbose = True)
        except:   
            dialog.showtraceback(parent = self,
                               txt='Failed to export HDF', 
                               title='Error during HDF export',
                               traceback=traceback.format_exc())
        
        self.Close()
        evt.Skip()



if __name__ == '__main__':
    '''
    sample data for testing
    '''
    import sys,os
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

    app = wx.App(redirect = False)
    w = HdfExportWindow(dataset = dataset)
    w.Show()
    app.MainLoop() 