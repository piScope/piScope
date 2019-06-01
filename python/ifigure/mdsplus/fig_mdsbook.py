'''

   FigMDSBook

   this class supports "save without data"

   FigMDSBook is made on-the-fly when book is
   opend by MDSScope. 

   When Book is closed it is conveted back to
   normal FigBook, this means if book is closed,
   piscope will save figure data. 
   For book to be saved w/o data, MDSScope should
   keep the book opened.

'''
from ifigure.mto.fig_book import FigBook
from ifigure.mdsplus.fig_mds import FigMds
from ifigure.mto.figobj_param import FigobjParam, FigobjData
from ifigure.utils.setting_parser import iFigureSettingParser as SettingParser

import wx


def convert2figmdsbook(book):
    book.__class__ = FigMDSBook
    if not hasattr(book, '_parallel_page'):
        book._parallel_page = True
    if not hasattr(book, '_parallel_shot'):
        book._parallel_shot = True
    if not hasattr(book, '_parallel_sec'):
        book._parallel_sec = True
    if not hasattr(book, '_use_global_tdi'):
        book._use_global_tdi = False
    if not hasattr(book, '_worker'):
        book._worker = ''


def convert2figbook(book):
    book.__class__ = FigBook


def prepare_dwglobal(book):
    '''
    set global parameters 
    '''
    from ifigure.mdsplus.mdsscope import n_global
    names = ('experiment', 'default_node', 'x', 'y', 'z', 'xerr',
             'yerr', 'title', 'event')
    values = ('', '', '', '', '', '', '', '', '')
    names2 = ('shot', 'global_defaults', 'xmax', 'ymax',
              'xmin', 'ymin', 'x.grid_lines', 'y.grid_lines',
              'global_choice', 'color_order',
              'mpanalysis', 'shot_global', 'use_shot_global',
              'event')
    values2 = ('-1', 0, None, None, None, None, 7, 7,
               [1]*16, ['black', 'red', 'blue', 'g', 'yellow'],
               False, '', False, '')
    gsettings = {n: [v]*n_global for n, v in zip(names, values)}
    gsettings['_flag'] = [[], [], [], []]
    if not book.has_child('dwglobal'):
        #            param = FigobjParam()
        param = FigobjData()
#            param = FigMdsData()
        book.add_child('dwglobal', param)
        param.setvar('globalsets', gsettings)
    elif isinstance(book.dwglobal, FigobjParam):
        var = book.dwglobal.getvar().copy()
        book.dwglobal.destroy()
        param = FigobjData()
        book.add_child('dwglobal', param)
        param.setvar(var)

    for n, v in zip(names2, values2):
        if not book.dwglobal.hasvar(n):
            book.dwglobal.setvar(n, v)
    gs = book.dwglobal.getvar('globalsets')
    if not '_flag' in gs:
        gs['_flag'] = [[], [], [], [], ]

    return book.dwglobal


def convert2figmdsbook2(book):
    #            for page in self.book.walk_page():
    prepare_dwglobal(book)
    if not book.hasvar('mdsplus_server'):
        p = SettingParser()
        v = p.read_setting('mdsplus.default_mdsserver')
        book.setvar('mdsplus_server',
                    v['server'])
#                                 'direct::CMOD')
    if not book.hasvar('mdsscript_main'):
        book.setvar('mdsscript_main', True)
    if not book.hasvar('mdsscope_nticks'):
        book.setvar('mdsscope_nticks', [10, 10])
    if not book.hasvar('mdsscope_autogrid'):
        book.setvar('mdsscope_autogrid', True)
    if not book.hasvar('mdsscope_listenevent'):
        book.setvar('mdsscope_listenevent', True)
    if not book.hasvar('dwscope_filename'):
        book.setvar('dwscope_filename', '')
    if not book.hasvar('global_tdi'):
        book.setvar('global_tdi', '')
    if not book.hasvar('global_tdi_event'):
        book.setvar('global_tdi_event', '')
    convert2figmdsbook(book)
    return book


def new_figmdsbook():
    book = FigBook()
    i_page = book.add_page()
    page = book.get_page(i_page)
    page.add_axes()
    page.realize()
    page.set_area([[0, 0, 1, 1]])

    return convert2figmdsbook2(book)


def add_scopebook(parent, name):
    book = new_figmdsbook()
    parent.add_child(name, book)
    return book


class FigMDSBook(FigBook):
    def add_commonvar(self, vars,  experiment='',
                      default_node='',
                      name='common_vars'):
        '''
        vars = (('psirz', '\\ANALYSIS::TOP:EFIT.RESULTS.G_EQDSK:PSIRZ'), 
         ('rgrid', 'dim_of(\\ANALYSIS::TOP:EFIT.RESULTS.G_EQDSK:PSIRZ)'), 
         ('zgrid', 'dim_of(\\ANALYSIS::TOP:EFIT.RESULTS.G_EQDSK:PSIRZ, 1)'), 
         ('efit_time', 'dim_of(\\ANALYSIS::TOP:EFIT.RESULTS.G_EQDSK:PSIRZ, 2)'), 
         ('fpol', '\\ANALYSIS::TOP:EFIT.RESULTS.G_EQDSK:FPOL'))
        '''
        from ifigure.mdsplus.fig_mdsdata import FigMdsData
        from collections import OrderedDict

        names = self.dwglobal.getvar('shot_global')
        a = [x for x in names.split(',') if len(x.strip()) != 0]
        self.dwglobal.setvar('shot_global', ','.join(a+name.split(',')))
        self.dwglobal.setvar('use_shot_global', True)
        vars = OrderedDict(vars)
        self.add_child(name, FigMdsData())
        cc = self.get_child(name=name)
        cc.setvar('mdsvars', vars)
        cc.setvar('experiment', experiment)
        cc.setvar('default_node', default_node)

    def save2(self, fid=None, olist=None):
        d = self.set_compact_savemode(1)
        olist = FigBook.save2(self, fid=fid, olist=olist)
        self.set_compact_savemode(0, d)
        return olist

    def save_data2(self, data):
        # the first element is version code
        from ifigure.mdsplus.mdsscope import MDSScope
        app = wx.GetApp().TopWindow
        viewer = app.find_bookviewer(self)
        if isinstance(viewer, MDSScope):
            viewer.set_book_scope_param()
        keys = ('_scope_param', '_parallel_page', '_parallel_shot', '_parallel_sec',
                '_use_global_tdi', '_worker')
        param = {key: getattr(self,  key) for key in
                 keys if hasattr(self, key)}
        data['FigMdsBook'] = (1, {}, param)
#        print param
        data = super(FigMDSBook, self).save_data2(data)
        return data

    def load_data2(self, data):
        if 'FigMdsBook' in data:
            v = data['FigMdsBook'][2]
            # print v
            for key in v:
                setattr(self, key, v[key])
        super(FigMDSBook, self).load_data2(data)

    def set_open(self, value):
        ''' 
        make sure to convert to figbook.
        also all loaded data are lost when it is closed.
        '''
        if value is False:
            self.set_compact_savemode(1)
            convert2figbook(self)
        FigBook.set_open(self, value)

    def set_compact_savemode(self, mode, ret=None):
        if mode == 1:
            ret = {}
            for obj in self.walk_tree():
                if isinstance(obj.get_parent(), FigMds):
                    #                    print obj.get_full_path()
                    ret[obj] = obj.prepare_compact_savemode()
                    obj._save_mode = mode
            return ret
        else:
            for obj in self.walk_tree():
                if obj in ret:
                    obj._save_mode = mode
                    obj._var = ret[obj]
