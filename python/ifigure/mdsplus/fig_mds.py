from __future__ import print_function
#  Name   :fig_mds
#
#          container to create and hold figures
#          for mdsplus system
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#
# *******************************************
#     Copyright(c) 2012- S. Shiraiwa
# *******************************************
import traceback
from collections import OrderedDict
import numpy as np

from ifigure.widgets.canvas.file_structure import *

import logging
import os
import weakref
import time
import threading
import ifigure.utils.cbook as cbook
import ifigure.utils.pickle_wrapper as pickle

from ifigure.mto.treedict import TreeDict
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.py_script import PyScript
from ifigure.mto.py_code import PyCode
from ifigure.mto.fig_grp import FigGrp


import ifigure.utils.geom as geom
import ifigure.events

from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from ifigure.mdsplus.filed_ndarray import FiledNDArray, FiledNDArrayAutoDel
from ifigure.mdsplus.mds_job import MDSjob
import wx
#
#  debug setting
#
import ifigure.utils.debug as debug
from .utils import parse_server_string
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigMds')
script_file_name = 'mdsscript.py'

panel_text = {'timetrace': 'required y\noptional x \n(x should monotonically increase)',
              'stepplot': 'required y\noptional x \n(x should monotonically increase)',
              'plot': 'required y\noptional x, xerr, yerr',
              'contour': 'required z\noptional x, y',
              'image': 'required z\noptional x, y',
              'axline': 'required either x or y',
              'axspan': 'required either x or y',
              'text': 'required s\noptional x, y',
              'surface': 'required z\noptional x, y',
              'noplot': ''}

required_variables = {'plot': ('y', 'x'),
                      'timetrace': ('y', 'x'),
                      'stepplot': ('y', 'x'),
                      'contour': ('z', 'x', 'y'),
                      'image': ('z', 'x', 'y'),
                      'surface': ('z', 'x', 'y'),
                      'axline': ('x', 'y'),
                      'axspan': ('x', 'y'),
                      'text': ('s', 'x', 'y'),
                      'noplot': tuple()}


def read_scriptfile(file):
    f = open(file, 'r')
    txt = ''
    while 1:
        line = f.readline()
        if not line:
            break
        txt = txt+line
    f.close()
    return txt


def write_scriptfile(file, txt):
    f = open(file, 'w')
    f.write(txt)
    f.close()
    return txt


def build_init_local_global_session(book):
    ana = MDSsession()
    server = book.getvar('mdsplus_server')

    if server is not None:
        s, p, t = parse_server_string(server)
#         job0 = MDSjob('reset', server)
#         ana.add_job([job0], 'reset')
        ana.add_job(
            [MDSjob('init', 'reset_private();reset_public();1')], 'reset_lg')
        ana.isec = 0
        ana.ishot = 0
        ana.ipage = 0
        ana.shot = 0
        ana.postprocess_done = True
        return ana
    else:
        return None


def add_connect_session(book, ana_group):
    ana = ana_group[0]
    expr = book.getvar('global_tdi')
    if expr is not None and expr != '' and book._use_global_tdi:
        job1 = MDSjob('value', expr, 'global_tdi')
#        print 'adding global tdi', expr
        ana_group.global_tdi = job1
    else:
        ana_group.global_tdi = None
    server = book.get_figbook().getvar('mdsplus_server')
    job0 = MDSjob('connection_mode', server)
    ana.add_job([job0], 'connection_mode', idx=0)
#    ana.postprocess_done = True
    return ana_group


def build_current_shot_session(book):
    ana = MDSsession()
    server = book.getvar('mdsplus_server')

    if server is not None:
        s, p, t = parse_server_string(server)
#         print s, p, t
        if t == '':
            # if tree name for shot number is not
            # specified
            return None

#         job0 = MDSjob('connection_mode', server)
#         ana.add_job([job0], 'connection_mode')
#        print t

#  this seems so slow
#         job1 = MDSjob('open', t,  0)
#         ana.add_job([job1], 'connection')
#         ana.add_job([MDSjob('value', '$SHOT')], 'shot')

#  equivalent to MDSVALUE('current_shot("treename")')
        ana.add_job([MDSjob('value', 'current_shot("'+t + '")')], 'shot')
        ana.isec = -1
        ana.ishot = -1
        ana.ipage = -1
        ana.shot = 0
        return ana
    else:
        return None


class MDSJobSet(list):
    def __init__(self, *args, **kargs):
        list.__init__(self, *args, **kargs)
        self.can_compress = True


class MDSsession(object):
    def __init__(self):
        self.jobs = MDSJobSet()
        self.jobnames = []
        self.result = {}
        self.ipage = -1
        self.w_id = -1
        self.pool = None
        self.done = False
        self.finished_count = -1
        self.job_count = 0
        self.running = False
        self.status = False
        self.postprocess = None
        self.skipped = False
        self.postprocess_done = False

#       self.batchmode = True ## batch mode submit all job at once
    def __repr__(self):
        return 'MDSSession: '+str([job for job in self.jobs])

    def add_job(self, jobs, name, idx=None):
        if idx is None:
            self.jobs.append(jobs)
            self.jobnames.append(name)
        else:
            self.jobs.insert(idx, jobs)
            self.jobnames.insert(idx, name)
        self.result[name] = None
        self.job_count = self.job_count + 1

    def get_result(self, name):
        i = self.jobnames.index(name)
        return self.result[i]

    def set_result(self, flag, value):
        self.result = value
        extra = {}
        for key in self.result:
            if isinstance(self.result[key], FiledNDArray):
                self.result[key].__class__ = FiledNDArrayAutoDel
                try:
                    extra[key+'_catalog'] = self.result[key]
                    self.result[key] = self.result[key].restore()
                except:
                    print(traceback.format_exc())
                    self.result['error message'] = ['failed to file transfar']
        for key in extra:
            self.result[key] = extra[key]
        self.done = True
        self.running = False
        self.status = flag
        if len(value['error message']) != 0:
            self.status = False

    def print_jobs(self):
        for job in self.jobs:
            for j in job:
                j.print_job()

    def txt_jobs(self):
        v = []
        for job in self.jobs:
            for j in job:
                v.append(j.txt_job())
        return v


        # this is an option to generate FigXXX
def_plot_options = {'plot': (('',), {'color': 'auto',
                                     'markersize': 3,
                                     'markerfacecolor': 'auto',
                                     'markeredgecolor': 'auto'}),
                    'timetrace': (('',), {'color': 'auto',
                                          'markersize': 3,
                                          'markerfacecolor': 'auto',
                                          'markeredgecolor': 'auto'}),
                    'stepplot': (('',), {'color': 'auto',
                                         'markersize': 3,
                                         'markerfacecolor': 'auto',
                                         'markeredgecolor': 'auto'}),
                    'contour': ((7,), dict()),
                    'image': (tuple(), dict()),
                    'axline': (tuple(), dict()),
                    'axspan': (tuple(), dict()),
                    'text': (tuple(), dict()),
                    'surface': (tuple(), dict()), }


class FigMds(FigGrp):
    def __init__(self, *args, **kargs):
        if 'dwplot' in kargs:
            dwplot = kargs['dwplot']
            del(kargs['dwplot'])
        else:
            dwplot = {}
        self._mds_debug = False
        self._var_mask = []
        self._plot_type = 'noplot'
        self._plot_type = 'timetrace'
        self._session_editor = None
        self._shot = {}  # place to store analized shot
        self._shots_expr = []
        self._shot_expr = []  # this may not necessary?
        self._analysis_flag = dict()  # stores if analysis for ishot succeeded
        # a place holder most likely overwritten by
        self._color_order = ['black', 'red']
        # scope
        self._debug_ana = False
        super(FigMds, self).__init__(*args, **kargs)
        self.setvar('plot_options', def_plot_options.copy())

        # call import even when dwplot is empty so that
        # it set up variables in _var
        self.import_dwplot(dwplot)

    def isDraggable(self):
        return False

    def import_dwplot(self, dwplot):
        def read_dwplot(name, dwplot):
            if name in dwplot:
                return dwplot[name]
            return ''

        self._plot_type = 'timetrace'
        self.setvar("experiment", read_dwplot('experiment', dwplot))
        self.setvar("default_node",  read_dwplot('default_node', dwplot))

        # this is an option to generate FigXXX
        plot_options = self.getvar('plot_options')
        if 'show_mode' in dwplot:
            if int(dwplot['show_mode']) == 2:
                plot_options['timetrace'] = (('-o',),
                                             def_plot_options['timetrace'][1].copy())
                plot_options['stepplot'] = (('-o',),
                                            def_plot_options['stepplot'][1].copy())

            elif int(dwplot['show_mode']) == 1:
                plot_options['timetrace'] = (('s',),
                                             def_plot_options['timetrace'][1].copy())
                plot_options['stepplot'] = (('s',),
                                            def_plot_options['stepplot'][1].copy())
        #plot_options['timetrace'] = plot_options['plot']
        self.setvar('plot_options', plot_options)

        data = OrderedDict()
        varnames = required_variables[self._plot_type]
        for name in varnames:
            data[name] = read_dwplot(name, dwplot)
        self.setvar("mdsvars", data)
        self.setvar("title", read_dwplot('title', dwplot))
        self.setvar("event", read_dwplot('event', dwplot))

        stepplot = read_dwplot('step_plot', dwplot)
        if stepplot != '' and int(stepplot) == 1:
            self._plot_type = 'stepplot'

        self.setp('dw_extra', read_dwplot('global_defaults', dwplot))

        range_data = ((read_dwplot('xmin', dwplot),
                       read_dwplot('xmax', dwplot)),
                      (read_dwplot('ymin', dwplot),
                       read_dwplot('ymax', dwplot)))
        self._default_xyrange = {'flag': (False, False),
                                 'tdi': range_data,
                                 'value': ((-1, 1), (-1, 1))}
        self.apply_mdsrange()

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'mdsplus.png')
        return [idx]

    @classmethod
    def isFigMds(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'mdsplus'

    @classmethod
    def property_in_palette(self):
        #        return ["mdsfiguretype","mdssource","mdsevent", "mdsrange"]
        return ["mdssource", ]

    def get_mdsevent(self, a=None):
        return self.getvar('event')

    def set_mdsevent(self, value, a=None):
        self.setvar('event', value)
        # update viewers event wait list (if it is opened by mdsscope)
        if value != '':
            book = self.get_figbook()
            if book is None:
                return
            import wx
            v = wx.GetApp().TopWindow.find_bookviewer(book)
            if v is None:
                return
            if hasattr(v, 'make_event_dict'):
                v.make_event_dict()

    def get_artist_extent(self, a=None):
        ax = self.get_container()
        if ax is None:
            return [None]*4
        x1, y1 = ax.transAxes.transform((0, 0))
        x2, y2 = ax.transAxes.transform((1, 1))
        return [x1, x2, y1, y2]

    def canvas_menu(self):
        return []  # ("Data Setting...",  self.onDataSetting, None)]

    def tree_viewer_menu(self):
        return ([("Data Setting...",  self.onDataSetting, None),
                 ("Script...",  self.onEditScript, None),
                 ("---",  None, None)] +
                super(FigGrp, self).tree_viewer_menu())

    def onDataSetting(self, evt, noapply=False):
        if self._session_editor is not None:
            try:
                self._session_editor.Raise()
                return
            except:
                pass
        from ifigure.mdsplus.dlg_mdssession import DlgMdsSession
        p = evt.GetEventObject().GetTopLevelParent()
        data = self.getvar('mdsvars')
        cb = self.data_setting_closed
        self._session_editor = DlgMdsSession(p, data=data,
                                             figmds=self,
                                             cb=cb,
                                             noapply=noapply)
        self._session_editor.set_required_variables(
            required_variables[self._plot_type])
        evt.Skip()

    def data_setting_closed(self, value):
        self.set_mdsfiguretype(value[0], None)
        self.set_mdsrange(value[1], None)
        self.set_mdsevent(value[2], None)

    def applyDlgData(self, data):
        self.setvar('mdsvars', data)

    def onEditScript(self, evt):
        if not self.has_owndir():
            self.mk_owndir()
        filename = 'mdsscript.py'
        self.setvar('pathmode', 'owndir')
        self.setvar('path', filename)
        filepath = os.path.join(self.owndir(), filename)
        if not os.path.exists(filepath):
            fid = open(filepath, 'w')
            fid.close()
        super(FigMds, self).onEditScript(evt)

    def clean_mdsdata(self):
        for name, child in self.get_children():
            child.destroy()

    def mdssession_job(self, shot=None, dwglobal=None,
                       startup=None):
        '''
        evaluate mds expression 
        shot : shot list
        dw_global : figobjparam which stores global setting
        '''
        if shot == 'm':
            shot = -1
        if shot == 'n':
            shot = -1

        def get_mdsexpr(name, ls, gs):
            if name in ls and not name in self._var_mask:
                exp = ls[name]
            else:
                exp = ''
            if (exp is None or
                    exp == '') and (gs is not None):
                exp = gs[name]
            if exp is None:
                return ''
            if sum([len(x.strip()) for x in exp.split('\n')]) == 0:
                exp = ''
            return exp

        def check_node_in_exp(exp, node):
            node = node.strip()
            if len(node) == 0:
                return True
            if node[0] != '\\':
                return True
            if node.find('::') == -1:
                return True
            try:
                if node[1:node.index('::')].upper() == exp.upper():
                    return True
                return False
            except:
                return False

        exp = get_mdsexpr('experiment', self.getvar(), dwglobal)
        node = ''
        if (self.getvar('default_node') is None or
                self.getvar('default_node') == ''):
            if (self.getvar('experiment') == '' or
                    self.getvar('experiment') is None):
                # if both default node and experiment is blank
                node = get_mdsexpr('default_node', self.getvar(), dwglobal)
            else:
                node = ''
        else:
            node = self.getvar('default_node')
        check = exp.upper()
#       for item in dwglobal['_flag']:
#            print 'need to run this', item

        # special handleing for x, y, and z

        y_expr = get_mdsexpr('y', self.getvar('mdsvars'), dwglobal)
        x_expr = get_mdsexpr('x', self.getvar('mdsvars'), dwglobal)
        z_expr = get_mdsexpr('z', self.getvar('mdsvars'), dwglobal)
        title_expr = get_mdsexpr('title', self.getvar(), dwglobal)

        dim_of_expr = []
        if (x_expr == '' or x_expr == None) and y_expr != '':
            #            tmp = y_expr.split('\n')[-1]
            #            if tmp.endswith(';'): tmp = tmp[:-1]
            #            if tmp.find('=') != -1:
            #               tmp = tmp[:(tmp.find('='))]
            #            x_expr = 'dim_of('+tmp+')'
            #            dim_of_expr.append('x')
            #            x_expr = 'y,0'+y_expr
            x_expr = 'dim_of(_piscopevar)'
            dim_of_expr.append('y')
#            y_expr = '_piscopevar=('+y_expr+')'
        elif ((x_expr == '' or x_expr == None) and
              (y_expr == '' or y_expr == None) and
              (z_expr != '')):
            #            dim_of_expr.append('x')
            #            dim_of_expr.append('y')
            #            x_expr = 'z,0'+z_expr
            #            y_expr = 'z,1'+z_expr

            #            tmp = z_expr.split('\n')[-1]
            #            if tmp.endswith(';'): tmp = tmp[:-1]
            #            if tmp.find('=') != -1:
            #               tmp = tmp[:(tmp.find('='))]
            #            x_expr = 'dim_of('+tmp+',0)'
            #            y_expr = 'dim_of('+tmp+',1)'

            x_expr = 'dim_of(_piscopevar)'
            y_expr = 'dim_of(_piscopevar,1)'
            dim_of_expr.append('z')
#            z_expr = '_piscopevar=('+y_expr+')'

        def_names = ['x', 'y', 'z']

        vars = self.getvar('mdsvars')
        other_expr = [(key, vars[key]) for key in vars if not key in def_names]
        pos_txt = self.getvar('posvars')

        ana = MDSsession()
        if not (x_expr == '' and y_expr == '' and z_expr == '' and
                len(other_expr) == 0):
            server = self.get_figbook().getvar('mdsplus_server')
            job1 = [MDSjob('open', exp,  shot)]
            ana.add_job(job1, 'connection')
#            if node == '': node = "\\"+exp.split(',')[-1]+"::TOP"
#            print '**** default node *****', node
            if node != '':
                job2 = MDSjob('defnode', node)
                ana.add_job([job2], 'def_node')
#            if self.getvar('posvars') is not None:
#                 ana.add_job([MDSjob('value', self.getvar('posvars'))], 'pos')
            if pos_txt is None:
                ana.add_job(
                    [MDSjob('value', '_shot = '+str(shot))],    'shot_number')
            else:
                ana.add_job([MDSjob('value', pos_txt + ';' + '_shot = '+str(shot))],
                            'shot_number')
#            print ana.jobs, ana.jobnames
            if dwglobal is not None:
                for item in dwglobal['_flag']:
                    ana.add_job([MDSjob('value', dwglobal[item])], item)
#                print MDSjob('value', dwglobal[item], item)
            if z_expr != '':
                ana.add_job([MDSjob('value', z_expr)], 'z')
            if y_expr != '':
                if 'y' in dim_of_expr:
                    #                    ana.add_job([MDSjob('dim_of', y_expr)], 'y')
                    ana.add_job([MDSjob('valuesig', y_expr)], 'y')
                else:
                    ana.add_job([MDSjob('value', y_expr)], 'y')
            if x_expr != '':
                if 'x' in dim_of_expr:
                    ana.add_job([MDSjob('valuesig', x_expr)], 'x')
                else:
                    ana.add_job([MDSjob('value', x_expr)], 'x')
            for key, expr in other_expr:
                if expr.strip() != '':
                    ana.add_job([MDSjob('valuesig', expr)], key)
        if self._debug_ana:
            print(ana)
        can_compress = True if self._plot_type == 'timetrace' else False
        txt = self.make_script(shot, startup=startup)
        if txt is not None:
            if not self.get_script_local():
                ana.add_job([MDSjob('script_txt', txt)], 'ans')
            else:
                can_compress = False

        # if title_expr is not enclosed by '"', then put it.
        if title_expr == '':
            title_expr = '""'
            jobname = 'novalue'
        else:
            if title_expr[0] != '"' and title_expr[-1] != '"':
                title_expr = '"'+title_expr + '"'
            jobname = 'value'
        if True:
            shots_expr = self.make_shots_expr()
            if pos_txt is None:
                ana.add_job(
                    [MDSjob(jobname, '_shots = "'+shots_expr+'"')], 'shots')
            else:
                ana.add_job([MDSjob(jobname,
                                    pos_txt + ';' + '_shots = "'+shots_expr+'"')],  'shots')
            ana.add_job([MDSjob(jobname, title_expr)], 'title')
        ana.jobs.can_compress = can_compress
        return ana

    def make_script(self, shot, short=False, startup=None):
        if (self.has_owndir() and
                self.hasvar('path')):
            fname = os.path.join(self.owndir(), self.getvar('path'))
            if os.path.exists(fname):
                txt = read_scriptfile(fname)
                if short:
                    return txt
                txt = 'shot = ' + str(shot) + '\n'+txt
                if self.getvar('posvars') is not None:
                    txt = self.getvar('posvars')+'\n'+txt
                if startup is not None:
                    txt = read_scriptfile(startup) + '\n' + txt
                return txt

    def erase_mdsdata(self):
        for name, child in self.get_children():
            child.destroy()
        self.set_bmp_update(False)

    def reset_shots_expr(self):
        self._shots_expr = []

    def append_shots_expr(self, ss):
        self._shots_expr.append(str(ss))

    def make_shots_expr(self):
        return ','.join(self._shots_expr)

    def postprocess_data(self, ana, viewer,
                         color_order=['red', 'blue', 'yellow'],
                         ):
        def set_auto_color_to_color(kargs, name, col):
            if (not name in kargs) or (kargs[name] == 'auto'):
                kargs[name] = col
            return kargs

        from ifigure.mto.fig_plot import FigPlot, TimeTrace, StepPlot
        from ifigure.mto.fig_contour import FigContour
        from ifigure.mto.fig_image import FigImage
        from ifigure.mto.fig_surface import FigSurface
        from ifigure.mto.fig_axline import FigAxline
        from ifigure.mto.fig_axspan import FigAxspan
        from ifigure.mto.fig_text import FigText

        self._color_order = color_order
        dprint2('process_data', self)
        if ana.skipped:
            if ana.do_title:
                self.process_title(ana)
            return True

        if (self.isempty() and
            not self.get_figaxes().isempty() and
                not self._suppress):
            self.generate_artist()
#        app = self.get_app()
#        ax = self.get_container()
#        fig_ax = ax.figobj

        ishot = ana.ishot

        self._analysis_flag[ishot] = False
        col = color_order[ishot % len(color_order)]

        for x in range(ishot - self.num_child()+1):
            plot_options = self.getvar('plot_options')
            if self._plot_type == 'plot':
                kargs = plot_options['plot'][1].copy()
                kargs = set_auto_color_to_color(kargs, 'color', col)
                kargs = set_auto_color_to_color(kargs, 'markerfacecolor', col)
                kargs = set_auto_color_to_color(kargs, 'markeredgecolor', col)
                obj = FigPlot([0], [0],
                              *(plot_options['plot'][0]),
                              **kargs)
            elif self._plot_type == 'timetrace':
                kargs = plot_options['timetrace'][1].copy()
                kargs = set_auto_color_to_color(kargs, 'color', col)
                kargs = set_auto_color_to_color(kargs, 'markerfacecolor', col)
                kargs = set_auto_color_to_color(kargs, 'markeredgecolor', col)
                obj = TimeTrace([0], [0],
                                *(plot_options['timetrace'][0]),
                                **kargs)
            elif self._plot_type == 'stepplot':
                kargs = plot_options['stepplot'][1].copy()
                kargs = set_auto_color_to_color(kargs, 'color', col)
                kargs = set_auto_color_to_color(kargs, 'markerfacecolor', col)
                kargs = set_auto_color_to_color(kargs, 'markeredgecolor', col)
                obj = StepPlot([0], [0],
                               *(plot_options['stepplot'][0]),
                               **kargs)
            elif self._plot_type == 'contour':
                obj = FigContour([0, 1], [0, 1], np.arange(4).reshape(2, 2),
                                 *(plot_options['contour'][0]))
            elif self._plot_type == 'image':
                obj = FigImage(np.zeros([2, 2]))
            elif self._plot_type == 'surface':
                obj = FigSurface(np.zeros([2, 2]))
            elif self._plot_type == 'axspan':
                obj = FigAxspan([0, 1])
            elif self._plot_type == 'axline':
                obj = FigAxline(np.zeros([1]))
            elif self._plot_type == 'text':
                obj = FigText(0, 0, '')
            name = self._plot_type + str(self.num_child()+1)
            self.add_child(name, obj)
            obj.set_container_idx(self._container_idx)
            obj.set_suppress(True)
        if self.get_script_local():
            txt = self.make_script(ana.shot, short=True)
            debug_mode = viewer.debug_mode
            if txt is not None:
                try:
                    vars = viewer.get_globals_for_figmds(ana.shot)
#                  print vars
                    for key in vars:
                        ana.result[key] = vars[key]
                    for key in viewer.startup_values:
                        ana.result[key] = viewer.startup_values[key]
                    ana.result['shot'] = ana.shot
                    if self.getvar('posvars') is not None:
                        a = {}
                        b = {}
                        exec(self.getvar('posvars'), a, b)
                        for key in b:
                            ana.result[key] = b[key]
                    filepath = os.path.join(self.owndir(), script_file_name)
                    from ifigure.widgets.debugger_core import get_breakpoint
                    code = compile(txt, filepath, 'exec')
                    if (len(get_breakpoint(filepath)) != 0 and debug_mode):
                        app = wx.GetApp().TopWindow
                        se = app.script_editor
                        import threading
                        if not se.CheckDebuggerStatus():
                            se.QueueSEDRequest(code, viewer.g, ana.result,
                                               filepath)
#                          print threading.current_thread().name
#                          wx.Yield()
#                          time.sleep(3)
                        else:
                            se.RunSED(code, viewer.g, ana.result, filepath)
                    else:
                        exec(code, viewer.g, ana.result)
                except:
                    dprint1('error occured when processing data by script')
                    print('error occured when processing data by following script')
                    print('#####')
                    print(txt)
                    print('#####')
                    print(traceback.format_exc())
                    self.change_suppress(True, self.get_child(ishot))
                    return False

        if ana.do_title:
            self.process_title(ana)
        if self._plot_type == 'plot':
            self._update_plot(ana, ishot)  # , color_order)
        elif self._plot_type == 'timetrace':
            self._update_plot(ana, ishot)  # , color_order)
        elif self._plot_type == 'stepplot':
            self._update_plot(ana, ishot)  # , color_order)
        elif self._plot_type == 'contour':
            self._update_contour(ana, ishot)
        elif self._plot_type == 'image':
            self._update_image(ana, ishot)
        elif self._plot_type == 'surface':
            self._update_surface(ana, ishot)
        elif self._plot_type == 'axspan':
            self._update_axspan(ana, ishot)
        elif self._plot_type == 'axline':
            self._update_axline(ana, ishot)
        elif self._plot_type == 'text':
            self._update_text(ana, ishot)

        obj = self.get_child(idx=ishot)
        if obj.is_suppress():
            return False

        obj._data_extent = None
        try:
            if (self.get_figaxes() is not None):
                self.get_figaxes().adjust_axes_range()
        except:
            dprint1("failed in adjusting axes at postprocess_data, continuing...")
            pass
        return True

    def process_title(self, ana):
        ishot = ana.ishot
        obj = self.get_child(idx=ishot)
        if 'title' in ana.result:
            fig_ax = self.get_figaxes()
            if len(fig_ax._artists) == 0:
                v = fig_ax.getp('title_labelinfo')
                # print v
                if v[0] != ana.result['title']:
                    v[0] = ana.result['title']
                    fig_ax.set_title(v, None)
                    fig_ax.set_bmp_update(False)
#                v[0] = ana.result['title']
#                fig_ax.set_title(v, None)
            else:
                a = fig_ax._artists[0]
                v = fig_ax.get_title(a)
                if v[0] != ana.result['title']:
                    v[0] = ana.result['title']
                    fig_ax.set_title(v, a)
                    fig_ax.set_bmp_update(False)
        if obj is not None:
            self.change_suppress(False, obj)
        else:
            print('process tiltle error')
            print(ana)
            print(obj)
            print(ishot)

    def call_refresh_artist(self, ishot):
        obj = self.get_child(idx=ishot)

        # this happens if plot type is changed
        if obj is None:
            return

        if (not obj.is_suppress() and
                not self.get_figaxes().isempty()):
            obj.refresh_artist_data()
            if self._plot_type == 'plot':
                if len(obj._artists) != 0:
                    col = self._color_order[ishot % len(self._color_order)]
                    opt = self.getvar('plot_options')['plot'][1]
                    if opt['color'] == 'auto':
                        obj._artists[0].set_color(col)
                    if opt['markerfacecolor'] == 'auto':
                        obj._artists[0].set_markerfacecolor(col)
                    if opt['markeredgecolor'] == 'auto':
                        obj._artists[0].set_markeredgecolor(col)
            elif self._plot_type == 'timetrace':
                if len(obj._artists) != 0:
                    col = self._color_order[ishot % len(self._color_order)]
                    opt = self.getvar('plot_options')['timetrace'][1]
                    if opt['color'] == 'auto':
                        obj._artists[0].set_color(col)
                    if opt['markerfacecolor'] == 'auto':
                        obj._artists[0].set_markerfacecolor(col)
                    if opt['markeredgecolor'] == 'auto':
                        obj._artists[0].set_markeredgecolor(col)

    def _en_numpy(self, v, name, s=True):
        from ifigure.utils.cbook import isiterable, isndarray
        if not name in v:
            return None, s and False
        if isiterable(v[name]) and not isndarray(v[name]):
            try:
                v[name] = np.array(v[name])
            except:
                return v[name], True and s
        return v[name], True and s

    def _update_plot(self, ana, ishot):  # , color_order):
        x, s = self._en_numpy(ana.result, 'x')
        y, s = self._en_numpy(ana.result, 'y', s)
        if not s:
            dprint2('Incorrect data to update plot :'+self.get_full_path())
            dprint2(ana.result.__repr__())
            obj = self.get_child(idx=ishot)
            self.change_suppress(True, obj)
            return
        try:
            obj = self.get_child(idx=ishot)
            if y is not None:
                if x is not None:
                    if len(x.shape) > 1:
                        x = x.flatten()
                    if len(y.shape) > 1:
                        y = y.flatten()
                    if x.size < y.size:
                        y = y[0:x.size]
                    if x.size > y.size:
                        x = x[0:y.size]
                    if x.ndim == 0:
                        x = np.array([x])
                    if y.ndim == 0:
                        y = np.array([y])
                    obj.setvar('x', x)
                    obj.setvar('y', y)
                    if 'x_catalog' in ana.result:
                        obj.setvar('x_catalog', ana.result['x_catalog'])
                    else:
                        obj.delvar('x_catalog')
                    if 'y_catalog' in ana.result:
                        obj.setvar('y_catalog', ana.result['y_catalog'])
                    else:
                        obj.delvar('y_catalog')

#               obj._is_decimate = True
                    obj.setp('use_var', True)
                else:
                    if len(y.shape) > 1:
                        y = y.flatten()
                    x = obj.getvar('x')
                    if x.size < y.size:
                        y = y[0:x.size]
                    if x.size > y.size:
                        x = x[0:y.size]
                    if y.ndim == 0:
                        y = np.array([y])
                    obj.setvar('y', y)
                    obj.setp('use_var', True)
                self.change_suppress(False, obj)
#           obj.set_suppress(False)
                obj._mpl_cmd = 'plot'
                from ifigure.mto.fig_plot import FigPlot, TimeTrace, StepPlot
                if (not isinstance(obj, TimeTrace) and
                        not isinstance(obj, StepPlot)):
                    if 'yerr' in ana.result:
                        yerr, s = self._en_numpy(ana.result, 'yerr')
                        obj._mpl_cmd = 'errorbar'
                        obj.setvar('yerr', yerr)
                    if 'xerr' in ana.result:
                        xerr, s = self._en_numpy(ana.result, 'xerr')
                        obj._mpl_cmd = 'errorbar'
                        obj.setvar('xerr', xerr)
                if self._suppress:
                    self.set_suppress(True)
                self._analysis_flag[ishot] = True
            else:
                logging.basicConfig(level=logging.DEBUG)
                logging.exception('session failed in visualization step')
                self.change_suppress(True, obj)
                ana.print_jobs()
                return
        except Exception:
            logging.basicConfig(level=logging.DEBUG)
            logging.exception('error in post processing')
            print(ana.result)
            obj.setvar('x', [0])
            obj.setvar('y', [0])
            obj.setp('use_var', True)
            self.change_suppress(True, obj)
#           if not obj.is_suppress():
#               obj.refresh_artist_data()

    def _update_axspan(self, ana, ishot):
        obj = self.get_child(idx=ishot)
        obj.setp('use_var', True)
        obj.setvar('x', [])
        obj.setvar('y', [])
        sup = True
        if 'x' in ana.result:  # x direction
            x, s = self._en_numpy(ana.result, 'x')
            obj.setvar('x', x)
            obj._data_extent = None
            sup = False
        if 'y' in ana.result:  # y direction
            y, s = self._en_numpy(ana.result, 'y')
            obj.setvar('y', y)
            obj._data_extent = None
            sup = False
        obj.set_suppress(sup)
        if self._suppress:
            self.set_suppress(True)
        self._analysis_flag[ishot] = not sup

    def _update_axline(self, ana, ishot):
        # print ana
        obj = self.get_child(idx=ishot)
        obj.setp('use_var', True)
        obj.setvar('x', [])
        obj.setvar('y', [])
        sup = True
        if 'x' in ana.result:  # x direction
            x, s = self._en_numpy(ana.result, 'x')
            obj.setvar('x', x)
            obj._data_extent = None
            sup = False
        if 'y' in ana.result:  # y direction
            y, s = self._en_numpy(ana.result, 'y')
            # print 'y', s
            obj.setvar('y', y)
            obj._data_extent = None
            sup = False
        obj.set_suppress(sup)
        if self._suppress:
            self.set_suppress(True)
        self._analysis_flag[ishot] = not sup

    def _update_surface(self, ana, ishot):
        self._update_contour(ana, ishot)

    def _update_image(self, ana, ishot):
        self._update_contour(ana, ishot)

    def _update_contour(self, ana, ishot):
        x, s = self._en_numpy(ana.result, 'x')
        y, s = self._en_numpy(ana.result, 'y', s)
        z, s = self._en_numpy(ana.result, 'z', s)
        if not s:
            dprint2('Incorrect data to update contour/image :' +
                    self.get_full_path())
            dprint2(ana.result.__repr__())
            self.suppress_ishot(ishot)
#           obj = self.get_child(idx=ishot)
#           self.change_suppress(True, obj)
            return
        try:
            obj = self.get_child(idx=ishot)
            if z is not None:
                if y is None:
                    y = np.arange(z.shape[0])
                if x is None:
                    x = np.arange(z.shape[1])
                obj.setvar('x', x)
                obj.setvar('y', y)
                obj.setvar('z', z)
                obj.setp('use_var', True)
                obj.set_suppress(False)
                if self._suppress:
                    self.set_suppress(True)
                self._analysis_flag[ishot] = True
            else:
                logging.basicConfig(level=logging.DEBUG)
                logging.exception('session failed in visualization step')
                self.change_suppress(True, obj)
                ana.print_jobs()
                return
        except:
            logging.basicConfig(level=logging.DEBUG)
            logging.exception('error in post processing')
            obj.setvar('z', np.zeros([2, 2]))
            obj.setvar('x', [0, 1])
            obj.setvar('y', [0, 1])
            obj.setp('use_var', True)
            self.change_suppress(True, obj)
#           if not obj.is_suppress():
#              obj.refresh_artist_data()

    def _update_text(self, ana, ishot):
        try:
            obj = self.get_child(idx=ishot)
            obj.setvar('s', ana.result['s'])
            x, y = obj.get_gp_point(0)
            if 'x' in ana.result:
                obj.setvar('x', ana.result['x'])
            else:
                obj.setvar('x', x)
            if 'y' in ana.result:
                obj.setvar('y', ana.result['y'])
            else:
                obj.setvar('y', y)
            obj.setp('use_var', True)
            if self._suppress:
                self.set_suppress(False)
            self._analysis_flag[ishot] = True
        except:
            logging.basicConfig(level=logging.DEBUG)
            logging.exception('error in post processing')
            obj.setvar('s', '')
#            obj.setvar('x', )
#            obj.setvar('y', [0,1])
            obj.setp('use_var', True)
            self.change_suppress(True, obj)

    def active_plots(self, l):
        if len(self._d) > l:
            for plot in self._d[l:]:
                self.change_suppress(True, plot)

    def eval_mdstitle(self):
        title = self.getvar('title')
        return title

    def set_mdssource(self, value, a):
        # a is not used
        for name, val in value:
            if name in self.getvar("mdsvars"):
                self.getvar("mdsvars")[name] = str(val)
            elif self.hasvar(name):
                self.setvar(name, str(val))

    def get_mdssource(self, a):
        # a is not used
        #        return {"data":
        #               [self.getvar("experiment"),
        #                self.getvar("default_node"),
        #                self.getvar("mdsvars")["x"],
        #                self.getvar("mdsvars")["y"],
        #                self.getvar("mdsvars")["z"],
        #                self.getvar("mdsvars")["xerr"],
        #                self.getvar("mdsvars")["yerr"],
        #                self.getvar("title"),
        #                self.getvar("update")],
        return {"figmds": self,
                "posvars": self.getvar("posvars")}


#    def handle_axes_change(self,evt = None):
#        for name, child in self.get_children():
#            child.handle_axes_change(evt)

    def apply_mdsrange(self, x=None, y=None):
        if x is None:
            x = [None, None]
        if not self._default_xyrange['flag'][0]:
            try:
                x = [float(m) for m in self._default_xyrange['tdi'][0]]
            except:
                pass
        if y is None:
            y = [None, None]
        if not self._default_xyrange['flag'][1]:
            try:
                y = [float(m) for m in self._default_xyrange['tdi'][1]]
            except:
                pass
        self._default_xyrange['value'] = (x, y)

    def set_mdsrange(self, value, a):
        self._default_xyrange['flag'] = (value[0][0], value[1][0])
        self._default_xyrange['tdi'] = (value[0][1], value[1][1])
        self.apply_mdsrange()
        return

    def get_mdsrange(self, a):
        v = ((self._default_xyrange['flag'][0],
              self._default_xyrange['tdi'][0]),
             (self._default_xyrange['flag'][1],
              self._default_xyrange['tdi'][1]))

        return v

    def set_mdsfiguretype(self, value, a=None):
        if self._plot_type != value:
            self.erase_mdsdata()
        ovalue = self._plot_type
        self._plot_type = value
        if self._session_editor is not None:
            self._session_editor.set_required_variables(
                required_variables[self._plot_type])

        figaxes = self.get_figaxes()

        threed_item = ['surface']
        flag1 = False
        if (ovalue in threed_item and
                not value in threed_item):
            flag1 = True
        if (not ovalue in threed_item and
                value in threed_item):
            flag1 = True

#        print value, ovalue, flag1
        if not flag1:
            return

        flag = False
        for obj in figaxes.walk_tree():
            if isinstance(obj, FigMds):
                if obj._plot_type in threed_item:
                    flag = True
                    break
        figaxes.set_3d(flag)
        ifigure.events.SendPVDrawRequest(self)

    def get_mdsfiguretype(self, a=None):
        return self._plot_type

    def get_script_local(self, a=None):
        v = self.get_figbook().getvar('mdsscript_main')
        if v is not None:
            return v
        return True

    def change_suppress(self, value, obj):
        if value == obj._suppress:
            return
#            if not value and not obj.isempty(): return
#            if value and obj.isempty(): return
        obj.set_suppress(value)

    def suppress_ishot(self, ishot):
        obj = self.get_child(ishot)
#        print 'suppressing ', obj, ishot
        if obj is not None:
            obj.set_suppress(True)
            obj.realize()

    def set_suppress_all(self, value):
        for name, child in self.get_children():
            child.set_suppress(value)

    def is_all_suppressed(self):
        return all([child._suppress for name, child in self.get_children()])

    def eval_shotstr(self, txt, prevshot, current):
        mode = ''
        if txt.startswith('*'):
            txt = txt[1:]
            mode = '*'
        if txt.startswith('-'):
            txt = 'p'+txt
        elif txt.startswith('+'):
            txt = 'p'+txt

        lc = {'c': current, 'p': prevshot, 'm': -1}
        if self.getvar("posvars") is not None:
            exec(self.getvar("posvars"), {}, lc)
        if txt.strip() == '':
            return 0, prevshot
        try:
            val = eval(txt, {}, lc)
        except:
            print('Failed to evaluate shot text')
            print(('shot text', txt))
            print(('name space', lc))
            # print traceback.format_exc()
            return None, None
        if 0 < val < 1000:
            val = (prevshot/1000)*1000 + val
        else:
            prevshot = val
        if val == -1:
            val = 'm'
            if mode == '*':
                val = 'n'
            prevshot = current
        else:
            if mode == '*':
                val = -abs(val)
#        print val, prevshot
        return val, prevshot

    def save2(self, fid=None, olist=None):
        return super(FigMds, self).save2(fid=fid, olist=olist)
        if olist is None:
            olist = []

        h2 = {"name": self.__class__.__name__,
              "module": self.__class__.__module__,
              "num_child": self.num_child(),
              "sname": self.name,
              "id": self.id,
              "var0": self._var0,
              "var": self._var,
              "note": self._note,
              "format": 2}
#        if self._save_mode == 1:
#            h2["num_child"] = 0
#        print h2
        if fid is not None:
            pickle.dump(h2, fid)
        c = olist.count(self.id)
        if c == 0:
            data = self.save_data2({})
            pickle.dump(data, fid)
            olist.append(self.id)
        else:
            pass
#        if self._save_mode == 1:
#            return olist
        for name, child in self.get_children():
            olist = child.save2(fid, olist)
        return olist

    def save_data2(self, data):
        # the first element is version code
        param = {"_plot_type":          self._plot_type,
                 "_default_xyrange":    self._default_xyrange,
                 "_var_mask":    self._var_mask}
        if self.get_figbook().has_child('dwglobal'):
            dwglobal = {'globalsets': self.get_figbook(
            ).dwglobal.getvar('globalsets')}
        else:
            dwglobal = None
        data['FigMds'] = (1, {}, param, dwglobal)
        data = super(FigMds, self).save_data2(data)
        return data

    def load_data2(self, data):
        def check_default_options(mode, name, v):
            if not mode in opt:
                opt[mode] = def_plot_options[mode]
            opt[mode][1][name] = v
        if 'FigMds' in data:
            val = data['FigMds'][1]
            for key in val:
                self.setp(key, val[key])
            if len(data['FigMds']) > 2:
                param = data['FigMds'][2]
                for key in param:
                    if hasattr(self, key):
                        setattr(self, key, param[key])
            if len(data['FigMds']) > 3:
                self.setp('loaded_dwglobal', data['FigMds'][3])

        super(FigMds, self).load_data2(data)

        # adjustment for backword compatibility
        opt = self.getvar('plot_options')
        check_default_options('plot', 'color', 'auto')
        check_default_options('plot', 'markerfacecolor', 'auto')
        check_default_options('plot', 'markeredgecolor', 'auto')
        check_default_options('timetrace', 'color', 'auto')
        check_default_options('timetrace', 'markerfacecolor', 'auto')
        check_default_options('timetrace', 'markeredgecolor', 'auto')
        check_default_options('stepplot', 'color', 'auto')
        check_default_options('stepplot', 'markerfacecolor', 'auto')
        check_default_options('stepplot', 'markeredgecolor', 'auto')

    def write_script(self, script):
        if not self.has_owndir():
            self.mk_owndir()
        filename = 'mdsscript.py'
        self.setvar('pathmode', 'owndir')
        self.setvar('path', filename)
        fname = os.path.join(self.owndir(),
                             self.getvar('path'))
        from ifigure.mdsplus.fig_mds import write_scriptfile
        write_scriptfile(fname, script)

    def remove_script(self):
        if (self.has_owndir() and
                self.hasvar('path')):
            fname = os.path.join(self.owndir(), self.getvar('path'))
            if os.path.exists(fname):
                os.remove(fname)
                self.delvar('pathmode')
                self.delvar('path')

    def picker_a(self, a, evt):
        s = [child._suppress for name, child in self.get_children()]
        if len(s) == 0 or all(s):
            if self._artists[0].contains(evt):
                return False, {}
            else:
                return True, {"child_artist": self._artists[0]}
        return super(FigMds, self).picker_a(a, evt)
