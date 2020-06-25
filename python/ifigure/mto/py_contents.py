from __future__ import print_function
#  Name   :py_content
#
#      base class for contents, in which
#      tree datas are imported
#
#      it includes...
#        1) Namelist
#        2) EFIT Gfile
#        3) netcdf4
#        4) MDS plus tree
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#         was born sometime around 2012. 04
#         2012. 08 still keeps growing...
#
# *******************************************
#     Copyright(c) 2012- S. Shiraiwa
# *******************************************

import collections
import weakref
import sys
import time
from six.moves import queue as Queue
import ifigure.events
from ifigure.widgets.var_viewerg2 import VarViewerGValue
from ifigure.utils.cbook import SetText2Clipboard


class PyContents(collections.OrderedDict):
    def __init__(self, *arg, **karg):
        #       self._var0=None
        super(PyContents, self).__init__(*arg, **karg)

    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = PyContents(value)
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)


class NamelistVVV(VarViewerGValue):
    def get_drag_text2(self, key):
        ''' 
        text for dnd from var viewer
        '''
        text = self._path+',"'+key+'")'
        return text

    def OnCompareItems(self, t1, t2):
        return (list(t1[0]._var0.keys()).index(t1[1][0]) -
                list(t2[0]._var0.keys()).index(t2[1][0]))


class Namelist(PyContents):
    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = self.__class__(value)
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)

    def __getitem__(self, key):
        '''
        namelist ignores case
        '''
        if key in self:
            return PyContents.__getitem__(self, key)
        elif key.upper() in self:
            return PyContents.__getitem__(self, key.upper())
        elif key.lower() in self:
            return PyContents.__getitem__(self, key.lower())
        else:
            raise KeyError('Key is not found :'+key)

    def show_contents(self, tree, td, item, base=None, keylist=None):
        ''' 
        proj viwer helper method
        '''
        img = td.get_classimage()

        if base is None:
            base = self
        if keylist is None:
            keylist = []
        pitem = item
        for key in base:
            tree.SetItemHasChildren(pitem)
            pitem2 = tree.AppendItem(pitem, key, img)
            vv_val = self.get_varviewer_value(td, key)
            tree.SetPyData(pitem2, (td, (key, base[key]), vv_val))

    def hide_contents(self, tree, td, item):
        tree.DeleteChildren(item)
        tree.SetItemHasChildren(item, False)

    def get_drag_text1(self, pydata):
        ''' 
        text for dnd from proj viewer
        '''
        return pydata[0].get_full_path()+'.get_contents("'+pydata[1][0]+'")'

    def get_varviewer_value(self, td, key):
        var = td._var0[key]
        note = {}
        val = NamelistVVV(var, note)
        if isinstance(key, list):
            txt = '","'.join(key)
        else:
            txt = key
        val._path = td.get_full_path()+'.get_contents("'+txt+'"'
        return val


class MatfileVVV(NamelistVVV):
    pass


class MatData(dict):
    def __repr__(self):
        dataname = ['  ' + x for x in self if not x.startswith('__')]
        return "Matlab (.mat) data (derived from dict class). \n" + '\n'.join(dataname)


class Matfile(Namelist):
    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = Matfile(value)
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)

    def get_varviewer_value(self, td, key):
        var = td._var0[key]
        note = {}
        val = MatfileVVV(var, note)
        if isinstance(key, list):
            txt = '","'.join(key)
        else:
            txt = key
        val._path = td.get_full_path()+'.get_contents("'+txt+'"'
        return val


class IDLfileVVV(NamelistVVV):
    pass


class IDLData(PyContents):
    def __repr__(self):
        dataname = ['  ' + x for x in self if not x.startswith('__')]
        return "IDL (.sav) data (derived from dict class). \n" + '\n'.join(dataname)


class IDLfile(Namelist):
    def __init__(self, *arg, **karg):
        self._var0 = {}
        super(IDLfile, self).__init__(*arg, **karg)

    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = IDLfile(value)
        else:
            value2 = value
        if hasattr(value, '_var0'):
            value2._var0 = value._var0
        super(PyContents, self).__setitem__(key, value2)

    def __getitem__(self, key):
        '''
        IDL data is either in _var0 or subtree(child)
        '''
        try:
            return PyContents.__getitem__(self, key)
        except:
            try:
                return self._var0.__getitem__(key)
            except:
                raise

    def show_contents(self, tree, td, item, base=None, keylist=None):
        ''' 
        proj viwer helper method
        '''
        img = td.get_classimage()

        if base is None:
            base = self
        if keylist is None:
            keylist = []
        self.make_contents_branch(tree, td, item, self, img)

    def make_contents_branch(self, tree, td, pitem, d, img,
                             keylist=None):
        if keylist is None:
            keylist = []
        for key in list(d.keys()):
            tree.SetItemHasChildren(pitem)
            pitem2 = tree.AppendItem(pitem, key, img)
            vv_val = self.get_varviewer_value(td, keylist+[key])
            tree.SetPyData(pitem2, (td, (keylist+[key], d[key]), vv_val))
            if isinstance(d[key], dict):
                keylist2 = [x for x in keylist]
                keylist2.append(key)
                self.make_contents_branch(tree, td, pitem2, d[key], img,
                                          keylist=keylist2)

    def get_drag_text1(self, pydata):
        ''' 
        text for dnd from proj viewer
        '''
        txt = '","'.join(pydata[1][0])
        return pydata[0].get_full_path()+'.get_contents("'+txt+'")'

    def get_varviewer_value(self, td, keylist):
        p = td[:]
        for k in keylist:
            p = p[k]

        var = {x: p[x] for x in list(p.keys()) if not isinstance(p[x], IDLfile)}

        note = {}
        val = IDLfileVVV(p._var0, note)
        val._td = td
        if isinstance(keylist, list):
            txt = '","'.join(keylist)
        else:
            txt = key
        val._path = td.get_full_path()+'.get_contents("'+txt+'"'
        return val


class EfitgfileVVV(NamelistVVV):
    pass


class Efitgfile(Namelist):
    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = Efitgfile(value)
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)

    def get_varviewer_value(self, td, key):
        var = td._var0[key]
        note = {}
        val = EfitgfileVVV(var, note)
        if isinstance(key, list):
            txt = '","'.join(key)
        else:
            txt = key
        val._path = td.get_full_path()+'.get_contents("'+txt+'"'
        return val


class EfitafileVVV(NamelistVVV):
    pass


class Efitafile(Namelist):
    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = Efitafile(value)
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)

    def get_varviewer_value(self, td, key):
        var = td._var0[key]
        note = {}
        val = EfitafileVVV(var, note)
        if isinstance(key, list):
            txt = '","'.join(key)
        else:
            txt = key
        val._path = td.get_full_path()+'.get_contents("'+txt+'"'
        return val


class MDSPlusTreeVVV(NamelistVVV):
    def get_drag_text2(self, key):
        ''' 
        text for dnd from var viewer
        '''
        text = self._td.get_full_path()+self._path+'.mds_eval("'+key + \
            '",'+self._td.get_full_path()+')'
        return text

    def OnCompareItems(self, t1, t2):
        klist = t1[1][0]
        p1 = t1[0]._var0
        for key in klist[:-1]:
            p1 = p1[key]
        p2 = t2[0]._var0
        klist = t2[1][0]
        for key in klist[:-1]:
            p2 = p2[key]

        return (list(p1.keys()).index(t1[1][0][-1]) -
                list(p2.keys()).index(t2[1][0][-1]))

    def tree_viewer_menu(self):
        if self.hasvar('mds_path'):
            return [("Show in MDSScope (1D)",  self.onScope1D, None),
                    ("Show in MDSScope (image)",  self.onScope2Di, None),
                    ("Show in MDSScope (contour)",  self.onScope2Dc, None),
                    ("Show in MDSScope (surface)",  self.onScope2Ds, None), ]

        else:
            return []

    def onScope1D(self, evt):
        from ifigure.mdsplus.fig_mds import FigMds

        path = self.getvar('mds_path').strip()
        obj = FigMds()
        obj.setvar("experiment", str(self._td.getvar('tree')))
        obj.setvar("default_node", '')
        data = collections.OrderedDict()
#       data["init"] = ''
        data["x"] = 'dim_of('+path+')'
        data["y"] = path
        data["z"] = ''
        data["xerr"] = ''
        data["yerr"] = ''
        obj.setvar("mdsvars", data)
        obj.setvar("title", '')
        obj.setvar("update", '')
        self._on_scope(obj)

    def onScope2Di(self, evt):
        self._on_scope_2D(evt, 'image', False)

    def onScope2Dc(self, evt):
        self._on_scope_2D(evt, 'contour', False)

    def onScope2Ds(self, evt):
        self._on_scope_2D(evt, 'surface', True)

    def _on_scope_2D(self, evt, type, threed):
        from ifigure.mdsplus.fig_mds import FigMds

        path = self.getvar('mds_path').strip()
        obj = FigMds()
        obj._plot_type = type
        obj.setvar("experiment", str(self._td.getvar('tree')))
        obj.setvar("default_node", '')
        data = collections.OrderedDict()
#       data["init"] = ''
        data["x"] = 'dim_of('+path+')'
        data["y"] = 'dim_of('+path+', 1)'
        data["z"] = path
        data["xerr"] = ''
        data["yerr"] = ''
        obj.setvar("mdsvars", data)
        obj.setvar("title", '')
        obj.setvar("update", '')
        self._on_scope(obj, threed)

    def _on_scope(self, obj, threed=False):
        #       print self.getvar('mds_path')
        #       print self._td.get_full_path(), self._path
        from ifigure.interactive import scope

#       book = scope()
        viewer = scope()
        book = viewer.book
        viewer.set_mdsshot(self._td.getvar('shot'))
        p = book.get_page(0)
        a = p.get_axes(0)
        a.set_3d(threed)
        name = a.get_next_name(obj.get_namebase())
        a.add_child(name, obj)
        obj.realize()

        ifigure.events.SendPVAddFigobj(a)
        ifigure.events.SendChangedEvent(a, w=viewer.canvas)


class MDSPlusTree(Namelist):
    #   def __init__(self, top, *arg, **karg):
    #       self._td = weakref.ref(top)
    def __init__(self, *arg, **karg):
        super(Namelist, self).__init__(*arg, **karg)

    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            #          value2=MDSPlusTree(self._td(), value)
            value2 = MDSPlusTree(value)
            if hasattr(value, 'mds_path'):
                value2.mds_path = value.mds_path
        else:
            value2 = value
        super(PyContents, self).__setitem__(key, value2)

    def show_contents(self, tree, td, item, base=None, keylist=None):
        ''' 
        proj viwer helper method
        '''
        img = td.get_classimage()

        if base is None:
            base = self
        if keylist is None:
            keylist = []
        self.make_contents_branch(tree, td, item, self, img)

    def make_contents_branch(self, tree, td, pitem, d, img,
                             keylist=None):
        if keylist is None:
            keylist = []
        for key in list(d.keys()):
            tree.SetItemHasChildren(pitem)
            pitem2 = tree.AppendItem(pitem, key, img)
            vv_val = self.get_varviewer_value(td, keylist+[key])
            tree.SetPyData(pitem2, (td, (keylist+[key], d[key]), vv_val))
            if isinstance(d[key], dict):
                keylist2 = [x for x in keylist]
                keylist2.append(key)
                self.make_contents_branch(tree, td, pitem2, d[key], img,
                                          keylist=keylist2)

    def get_varviewer_value(self, td, keylist):
        p = td[:]
        for k in keylist:
            p = p[k]
        if hasattr(p, 'mds_path'):
            val = MDSPlusTreeVVV({"value": "*", "mds_path": p.mds_path},  {})
        else:
            val = MDSPlusTreeVVV({"value": "*"},  {})
        txt = '","'.join(keylist)
        if not isinstance(td, weakref.ProxyType):
            td = weakref.proxy(td)
        val._td = td
        val._path = '.get_contents("'+txt+'")'
        return val

    def get_drag_text1(self, pydata):
        ''' 
        text for dnd from proj viewer
        '''
        txt = '","'.join(pydata[1][0])
        return pydata[0].get_full_path()+'.get_contents("'+txt+'")'

    def get_info(self):
        print(('getting info', self.mds_path))

    def eval(self, td, **kargs):
        return self.mds_eval(td, **kargs)

    def mds_eval(self, td, key='value', maxwait=60, shot=None, debug=False):
        '''
            key : 'value', 'dim0', 'dim1'
        '''
#       import ifigure.utils.mdsplusr as mds
        if debug:
            print(('eval', key, self.mds_path))

#       td = self._td()
        if key == "value":
            expr = self.mds_path
        elif key == "dim0":
            expr = 'dim_of('+self.mds_path+',0)'
        elif key == "dim1":
            expr = 'dim_of('+self.mds_path+',1)'

        tree = td.getvar("tree")
        if shot is None:
            shot = td.eval("shot")
        server = td.getvar('mdsplus_server')
        if server is None:
            server = td.get_parent().getvar('mdsplus_server')
        from ifigure.mdsplus.mdsscope import MDSWorkerPool

        if MDSWorkerPool().pool is None:
            MDSWorkerPool().Reset()
        pool = MDSWorkerPool().pool

#       w, wid = pool.get_worker()
#       if w is None:
#           print 'worker not available'
#           return

        from ifigure.mdsplus.fig_mds import MDSsession
        from ifigure.mdsplus.mds_job import MDSjob
        from ifigure.mdsplus.mdsscope import AnaGroup, GlobalCounter

        ana = MDSsession()
        job0 = MDSjob('connection_mode', server)
        ana.add_job([job0], 'connection_mode', idx=0)
        job1 = MDSjob('open', tree,  int(shot))
        ana.add_job([job1], 'connection')
        ana.add_job([MDSjob('value', expr)], 'value')

#       ana.start_job(pool, wid)
        ana_group = AnaGroup(True, [ana])
        gc = GlobalCounter(0,  td)
        ana_group.gc = gc
        ana_group.func = self.call_back
#       self.queue = Queue.Queue()
        pool.submit_ana_group(ana_group)

#       self.queue.get(True, 5)
#       ana_group, idx = pool.check_ana_group_done()
#       ana = ana_group[0]
#       if ana.check_finished():
        count = 0
        while count < 10:
            time.sleep(1)
            if ana.status:
                break
            count = count + 1
        if ana.status:
            return ana.result['value']

        print('Error in reading data')
        return None

    def call_back(self, *args, **kargs):
        pass
#       print 'call_back is called'
#       self.queue.put('')


class NETCDFfileVVV(NamelistVVV):
    def get_drag_text2(self, key):
        ''' 
        text for dnd from var viewer
        '''
        text = self._td.get_full_path()+self._path+'.var["'+key+'"]'
        return text

    def OnCompareItems(self, t1, t2):
        klist = t1[1][0]
        p1 = t1[0]._var0
        for key in klist[:-1]:
            p1 = p1[key]
        p2 = t2[0]._var0
        klist = t2[1][0]
        for key in klist[:-1]:
            p2 = p2[key]

        return (list(p1.keys()).index(t1[1][0][-1]) -
                list(p2.keys()).index(t2[1][0][-1]))

    def tree_viewer_menu(self):
        if self._content()._data_loaded:
            m = [("Show as plot",  self.onScope1D, None),
                 ("Show as image",  self.onScope2Di, None),
                 ("Show as contour",  self.onScope2Dc, None),
                 ("Show as surface",  self.onScope2Ds, None),
                 ("Export Content Object",  self.onExportContent, None),
                 ("Erase data on Memory",  self.onEraseDataOnMem, None),
                 ("Copy path",  self.onCopyPath, None), ]
        else:
            m = [("Show as plot",  self.onScope1D, None),
                 ("Show as image",  self.onScope2Di, None),
                 ("Show as contour",  self.onScope2Dc, None),
                 ("Show as surface",  self.onScope2Ds, None),
                 ("Export Content Object",  self.onExportContent, None),
                 ("Load data to Memory",  self.onLoadData2Mem, None),
                 ("Copy path",  self.onCopyPath, None), ]

        return m

    def onScope1D(self, evt):
        from ifigure.mto.fig_plot import FigPlot
        y = self._content().nc_eval(self._td)
        obj = FigPlot(y)
        self._on_scope(obj, False)

    def onScope2Di(self, evt):
        from ifigure.mto.fig_image import FigImage
        z = self._content().nc_eval(self._td)
        obj = FigImage(z)
        self._on_scope(obj, False)

    def onScope2Dc(self, evt):
        from ifigure.mto.fig_contour import FigContour
        z = self._content().nc_eval(self._td)
        obj = FigContour(z)
        self._on_scope(obj, False)

    def onScope2Ds(self, evt):
        from ifigure.mto.fig_surface import FigSurface
        z = self._content().nc_eval(self._td)
        obj = FigSurface(z)
        self._on_scope(obj, True)

    def _on_scope(self, obj, threed=False):
        #       print self.getvar('mds_path')
        #       print self._td.get_full_path(), self._path
        from ifigure.interactive import figure

        book = figure()
        viewer = book.get_root_parent().app.find_bookviewer(book)

        p = book.get_page(0)
        a = p.get_axes(0)
        a.set_3d(threed)
        name = a.get_next_name(obj.get_namebase())
        a.add_child(name, obj)
        obj.realize()

        ifigure.events.SendPVAddFigobj(a)
        ifigure.events.SendChangedEvent(a, w=viewer.canvas)

    def onLoadData2Mem(self, evt):
        self._content().load2mem(self._td)

    def onEraseDataOnMem(self, evt):
        self._content().erase_mem()

    def onExportContent(self, evt):
        app0 = wx.GetApp().TopWindow
        ret, m = dialog.textentry(app0,
                                  "Enter variable name", "Export Content Object", 'content')
        if not ret:
            return None
        self._td.write2shell(self._content(), m)

    def onCopyPath(self, evt):
        full_path = self._td.get_full_path()
        text = full_path + self._path+'.nc_eval('+full_path+')'

        SetText2Clipboard(text)


class NETCDFfile(Namelist):
    class_version = 1.0

    def __init__(self, *arg, **karg):
        self.var = collections.OrderedDict()
        self.nc_path = []
        self.version = self.__class__.class_version
        self._data = None
        self._data_loaded = False

        super(PyContents, self).__init__(*arg, **karg)

    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if isinstance(value, collections.OrderedDict):
            value2 = NETCDFfile(value)
        else:
            value2 = value

        super(PyContents, self).__setitem__(key, value2)

    def show_contents(self, tree, td, item, base=None, keylist=None):
        ''' 
        proj viwer helper method
        '''
        img = td.get_classimage()
        if base is None:
            base = self
        if keylist is None:
            keylist = []
        self.make_contents_branch(tree, td, item, img)

    def make_contents_branch(self, tree, td, pitem, img,
                             keylist=None):
        if keylist is None:
            keylist = []
        for key in list(self.keys()):
            tree.SetItemHasChildren(pitem)
            pitem2 = tree.AppendItem(pitem, key, img)
            vv_val = self[key].get_varviewer_value(td, keylist+[key])
            tree.SetPyData(pitem2, (td, (keylist+[key], self[key]),
                                    vv_val))
            # self[key].nc_path=keylist+[key]
            if isinstance(self[key], dict):
                keylist2 = [x for x in keylist]
                keylist2.append(key)
                self[key].make_contents_branch(tree, td, pitem2,
                                               img, keylist=keylist2)

    def get_varviewer_value(self, td, keylist):
        val = NETCDFfileVVV(self.var, {})
        txt = '"]["'.join(keylist)
        if not isinstance(td, weakref.ProxyType):
            td = weakref.proxy(td)
        val._td = td  # weakref.proxy(td)
        val._content = weakref.ref(self)
        val._path = '[:]["'+txt+'"]'
        return val

    def get_drag_text1(self, pydata):
        ''' 
        text for dnd from proj viewer
        '''
        txt = '","'.join(pydata[1][0])
        return pydata[0].get_full_path()+'.get_contents("'+txt+'")'

    def nc_eval(self, td):
        from netCDF4 import Dataset

        fpath = td.path2fullpath(modename='nc4_pathmode',
                                 pathname='nc4_path')
        g0 = Dataset(fpath, 'r', format='NETCDF4')
        g = g0
        for i in range(len(self.nc_path)-1):
            if hasattr(g, self.nc_path[i]):
                g = getattr(g, self.nc_path[i])
            else:
                g = g.__getitem__(self.nc_path[i])
        if g is not None:
            v = g[self.nc_path[-1]][:]
            g0.close()
            return v
        else:
            g0.close()
            return None

    def load2mem(self, td):
        value = self.nc_eval(td)
        self._data = value
        self._data_loaded = True

    def erase_mem(self):
        self._data = None
        self._data_loaded = False

    def eval(self, td):
        return self.nc_eval(td)


class TSCInputFile(Namelist):
    class_version = 1.0

    def show_contents(self, tree, td, item, base=None, keylist=None):
        ''' 
        proj viwer helper method
        '''
        img = td.get_classimage()

        if base is None:
            base = self
        if keylist is None:
            keylist = []
        pitem = item
        for key in list(base.keys()):
            tree.SetItemHasChildren(pitem)
            if 'name' in self[key]:
                extra = '('+self[key]['name']+')'
            else:
                extra = ''

            pitem2 = tree.AppendItem(pitem, key+extra, img)
            vv_val = self.get_varviewer_value(td, key)
            tree.SetPyData(pitem2, (td, (key, base[key]), vv_val))
