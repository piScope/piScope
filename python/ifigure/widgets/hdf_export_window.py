import os
import traceback
import wx
import wx.dataview as dv
import six
from ifigure.utils.hdf_data_export import build_data,  hdf_data_export

'''
   HDFExportWindow(page = 


'''
class HDFDataModel(dv.PyDataViewModel):
    def __init__(self, **kwargs):
        dv.PyDataViewModel.__init__(self)
        self.dataset = kwargs.pop('dataset', None)
        self.export_flag = kwargs.pop('export_flag')
        #self.objmapper.UseWeakRefs(True)
        
    def GetChildren(self, parent, children):
        if not parent:
            num = 0            
            for name in six.iterkeys(self.dataset):
                obj =(name,)
                children.append(self.ObjectToItem(obj))
                self.export_flag[obj] = True
                num = num + 1
            return num
        
        labels = self.ItemToObject(parent)
        p = self.dataset[labels[0]]
        for l in labels[1:]:
            p = p[l]
        if isinstance(p, dict):
            num = 0
            for newlabel in sorted(p.keys()):
                print newlabel
                x = list(labels)
                x.append(newlabel)
                obj = tuple(x)
                children.append(self.ObjectToItem(obj))
                self.export_flag[obj] = True                
                num = num + 1
            return num
        return 0
    
    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem

        labels = self.ItemToObject(item)
        if len(labels) == 1:
            return dv.NullDataViewItem
        else:
            return self.ObjectToItem(labels[:-1])
    def GetColumnCount(self):
        print 'GetColumnCount'
        return 4
    def GetColumnType(self, col):
        print 'GetColumnType'        
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
        labels = self.ItemToObject(item)
        p = self.dataset
        for l in labels:
            p = p[l]
        if isinstance(p, dict): return True        
        # but everything else are not
        return False            

    def GetValue(self, item, col):
        labels = self.ItemToObject(item)
        p = self.dataset
        for l in labels:
            p = p[l]
            
        if col == 0:
            v = labels[-1]
            ret = v
        elif col == 1:
            ret = self.export_flag[labels]
        elif col == 2:
            ret = str(p)
        elif col == 3:
            if hasattr(p, 'shape'):
                ret = str(p.shape)
            else:
                ret = ''
        else:
            pass
        return ret
    def SetValue(self, value, item, col):

        labels = self.ItemToObject(item)
        print value, labels
        p = self.dataset        
        for l in labels:
            p = p[l]
        if col == 1:
            self.export_flag[labels] = value

class HdfExportWindow(wx.Frame):
    def __init__(self, *args, **kargs):
        page = kargs.pop('page', None)
        if page is None:  return
        parent = kargs.pop('parent', None)
        title  = kargs.pop('title', 'HDF export')
        path = kargs.pop('path', os.path.join(os.getcwd(), 'data.hdf'))

        self.dataset = build_data(page, verbose = False)

        style = (wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|
                 wx.RESIZE_BORDER)
        if parent is not None:
            style = style | wx.FRAME_FLOAT_ON_PARENT
                                
        wx.Frame.__init__(self, *args,
                          style = style, 
                          title = title, parent = parent)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        sizer = self.GetSizer()
        sizer_h =wx.BoxSizer(wx.HORIZONTAL)

        wildcard = "HDF(hdf)|*.hdf|Any|*.*"
        self.filepicker = wx.FilePickerCtrl(self,
                                            style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL,
                                            path = path,
                                            wildcard = wildcard)
        self.dataviewCtrl = dv.DataViewCtrl(self,
                                            style = (dv.DV_VERT_RULES|
                                                     dv.DV_MULTIPLE))
        self.dataviewCtrl.AppendTextColumn('name', 0,
                                           width = 150)
        self.dataviewCtrl.AppendToggleColumn('export', 1,
                                             width= 40,
                                             mode=dv.DATAVIEW_CELL_EDITABLE)
        self.dataviewCtrl.AppendTextColumn('value', 2, width = 100)
        self.dataviewCtrl.AppendTextColumn('shape', 3)        
        
        #self.btn_load = wx.Button(self, label = 'Load')
        self.btn_export = wx.Button(self, label = 'Export...')

        
        sizer.Add(self.filepicker, 0, wx.EXPAND|wx.ALL, 1)        
        sizer.Add(self.dataviewCtrl, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(sizer_h, 0, wx.EXPAND|wx.ALL|wx.ALIGN_RIGHT, 5)        


        #sizer_h.Add(self.btn_load, 0,   wx.EXPAND|wx.ALL, 1)
        sizer_h.AddStretchSpacer(prop = 1)
        sizer_h.Add(self.btn_export, 0, wx.EXPAND|wx.ALL, 1)


        self.Layout()
        self.Show()


        self.export_flag = {}
        model = HDFDataModel(export_flag = self.export_flag,
                             dataset = self.dataset)
        self.dataviewCtrl.AssociateModel(model)
        model.DecRef()

        self.Bind(wx.EVT_BUTTON, self.onExport, self.btn_export)
        
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
