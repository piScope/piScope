from __future__ import print_function
#  Name   :py_solver
#
#          various classes for defining solvers
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History : 2012 08 20 : extracted from py_code
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

import os
import wx
import time
import imp
import sys
import logging
import weakref
import shutil
import threading
import numpy as np
import ifigure.utils.pickle_wrapper as pickle
import ifigure
import ifigure.utils.cbook as cbook
import ifigure.widgets.dialog as dialog
from ifigure.mto.py_code import PyCode, PyModel, PyParam, PySol, AbsModuleContainer, AbsScriptContainer
from ifigure.mto.py_script import PyScript
from ifigure.mto.py_module import PyModule
import ifigure.events


from numpy import linspace


def onSettingList(solver):
    app = wx.GetApp().TopWindow

    model = ''
    if cbook.ProxyAlive(solver._model):
        model = solver._model.get_full_path()
    else:
        solver._model = None

    sol = ''
    if cbook.ProxyAlive(solver._sol):
        sol = solver._sol.get_full_path()
    else:
        solver._sol = None

    param = ''
    if cbook.ProxyAlive(solver._param):
        param = solver._param.get_full_path()
    else:
        solver._param = None

    list = [["", "Solver Setting", 2],
            ["Model", model, 0],
            ["Solution", sol, 0],
            ["Global", param, 0], ]
    return list


def setSetting(solver, value):
    app = solver.get_app()
    try:
        root = solver.get_root_parent()
        exec(root._name + ' = root')
        if len(value[1].split()) != 0:
            a = eval(value[1])
            if isinstance(a, PyModel):
                solver._model = weakref.proxy(a)
            else:
                dialog.message(app, 'Model should be PyModel', 'Error')
                solver._model = None
        if len(value[2].split()) != 0:
            b = eval(value[2])
            if isinstance(b, PySol):
                solver._sol = weakref.proxy(b)
            else:
                dialog.message(app, 'Sol should be PySol', 'Error')
                solver._sol = None
        if len(value[3].split()) != 0:
            b = eval(value[3])
            if isinstance(b, PyParam):
                solver._param = weakref.proxy(b)
            else:
                dialog.message(app, 'Parameter should be PyParam', 'Error')
                solver._param = None
    except Exception:
        logging.exception("Solver Setting Failed")


def init_sol(solver, sol=None, mode=0, tmpdir=None):
    '''
    mode = 0: standard mode
    mode = 1: mode 0 + backup tmpdir and return it to caller
    mode = 2: read data from tmpdir
    '''
    # cleaning folder
    if not cbook.ProxyAlive(solver._model):
        print("can not initialize solution folder. model is not spedified")
        solver._model = None
        return False

    if sol is None:
        if cbook.ProxyAlive(solver._sol):
            sol = solver._sol

    if sol is None:
        print("can not initialize solution folder. sol is not spedified")
        return False

    for name, child in sol.get_children():
        child.destroy()

    root = solver.get_root_parent()
    wdir = root.getvar('wdir')

    if mode != 2:
        fpath = os.path.join(wdir, '.tmp'+str(solver.id))
        if os.path.exists(fpath):
            os.remove(fpath)
        rm = solver._model.get_root_model()

        scripts = [obj for obj in rm.walk_tree() if isinstance(obj, PyScript)]
        for s in scripts:
            s._save_link = True
        flag, tmpdir = rm.save_subtree(fpath, maketar=False)
        for s in scripts:
            s._save_link = False
    else:
        shutil.copytree(tmpdir+'_bk', tmpdir)
    if mode == 1:
        shutil.copytree(tmpdir, tmpdir+'_bk')
    sol.load_subtree(tmpdir, usetar=False)
    sol.setvar('source_model', solver._model.get_root_model().get_full_path())
#        os.remove(fpath)

    if not sol.has_child('parameters'):
        sol.add_child('parameters', PyParam())
    if cbook.ProxyAlive(solver._param):
        #            psetting = root.setting.parameters
        param = solver._param
        vars = param.getvar_copy()
        sol.parameters.setvar(vars)
    if mode == 1:
        return True, tmpdir
    return True


def check_ref(solver):
    if not hasattr(solver._model, 'isTreeDict'):
        solver._model = None
    if not hasattr(solver._sol, 'isTreeDict'):
        solver._sol = None
    if not hasattr(solver._param, 'isTreeDict'):
        solver._param = None


class PySolver(PyCode, AbsModuleContainer, AbsScriptContainer):
    '''
     PySolver is a top node of solver tree 
    '''

    def __init__(self, parent=None, src=None):
        self._model = None
        self._sol = None
        self._param = None
        self._thread = None
        super(PySolver, self).__init__(parent=None, src=None)

    @classmethod
    def isPySolver(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'solver'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'solver.png')
        return [idx1]

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_F9:
            return self.onRun
        return None

    def get_pysol(self, parent):
        return [child for name, child in parent.get_children()
                if isinstance(child, PySol)]

    def onAddSolver(self, e=None):
        '''
        add generic solver object.
        this option is used when building
        solver tree from scratch.
        '''
        sc = BaseSolver()
        name = self.get_next_name(sc.get_namebase())
        self.add_child(name, sc)
        if e is not None:
            e.Skip()

    def onAddStdSolver(self, e=None):
        sc = PyStdSolver()
        name = self.get_next_name(sc.get_namebase())
        self.add_child(name, sc)
        sc.load_default_script()
        if e is not None:
            e.Skip()

    def onAddParametric(self, e=None):
        sc = PyParametric()
        name = self.get_next_name(sc.get_namebase())
        self.add_child(name, sc)
        sc.load_default_script()
        if e is not None:
            e.Skip()

    def onAddOptimizer(self, e=None):
        sc = PyOptimizer()
        name = self.get_next_name(sc.get_namebase())
        self.add_child(name, sc)
        sc.load_default_script()
        if e is not None:
            e.Skip()

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        return [  # ('Run   (F9)', self.onRun, None),
            ('+Add Solver', None, None),
            ('Standard Solver', self.onAddStdSolver, None),
            ('Parametric Solver', self.onAddParametric, None),
            ('Optimizer', self.onAddOptimizer, None),
            ('Custom Solver', self.onAddSolver, None),
            ('!',  None, None),
            ('---', None, None)] + \
            super(PyCode, self).tree_viewer_menu()

    def module_addon_list(self):
        base_mod = 'ifigure.add_on.solver.module'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_module_menu(mod_path)
        menu.append(('New Module ...', self.onAddNewModule, None))
        return menu

    def script_addon_list(self):
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_script_menu(mod_path)
        menu.append(('New Script ...', self.onAddNewScript, None))
        return menu

    #   save/load
#    def save_data(self, fid):
#        h2={}
#        if self.model is not None: h2["model"]=self.model.id
#        if self.sol is not None: h2["sol"]=self.sol.id
#        pickle.dump(h2, fid)

    def load_data(self, fid):
        h2 = pickle.load(fid)
        self.setvar("load_property", h2)

    def save_data2(self, data):
        def get_right_path(self, obj):
            if self.isdescendant(obj):
                return self.get_td_path(obj)
            else:
                return self.get_td_path(obj, True)
        check_ref(self)
        h2 = {}
#        if self.model is not None: h2["model"]=self.model.id
#        if self.sol is not None: h2["sol"]=self.sol.id
#        if self.param is not None: h2["param"]=self.param.id
        if self._model is not None:
            h2["model_path"] = get_right_path(self, self._model)
        if self._sol is not None:
            h2["sol_path"] = get_right_path(self, self._sol)
        if self._param is not None:
            h2["param_path"] = get_right_path(self, self._param)
        data['PySolver'] = (1, h2)

        data = super(PySolver, self).save_data2(data)
        return data

    def load_data2(self, data):
        h2 = data['PySolver'][1]
        self.setvar("load_property", h2)
        super(PySolver, self).load_data2(data)

    def init_after_load(self, olist, nlist):
        h2 = self.getvar("load_property")
        if "model" in h2:
            oid = h2["model"]
            self._model = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "sol" in h2:
            oid = h2["sol"]
            self._sol = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "param" in h2:
            oid = h2["param"]
            self._param = self.resolve_olist_nlist_map(oid, olist, nlist)

        if "model_path" in h2:
            self._model = self.resolve_td_path(h2["model_path"])
        if "sol_path" in h2:
            self._sol = self.resolve_td_path(h2["sol_path"])
        if "param_path" in h2:
            self._param = self.resolve_td_path(h2["param_path"])

        self.delvar("load_property")

    @property
    def model(self):
        return self._model

    @property
    def sol(self):
        return self._sol

    @property
    def param(self):
        return self._param


class BaseSolver(PySolver):
    '''
    this solver expose all menues
    so that user can setup whatever he/she wants
    '''

    def __init__(self, *args, **kargs):
        PySolver.__init__(self, *args, **kargs)
        self._queue = None    # queue used in solver script

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        return [('Run  (F9)', self.onRun, None),
                ('+Add Module',  None, None)] + \
            self.module_addon_list() + \
            [('!',  None, None),
                ('+Add Script',  None, None)] + \
            self.script_addon_list() + \
            [('!',  None, None),
                ('Setting...', self.onSetting, None),
                ('Initialize Solution', self.onInitSol, None),
                ('---', None, None)] + \
            super(PyCode, self).tree_viewer_menu()

    def load_default_script(self):
        pass

    def onRun(self, e=None):

        if not self.is_valid_setting():
            return
        val = self.init_sol()
        if not val:
            return
        self.solver_script.Run()
        if e is not None:
            e.Skip()
        return

    def onInitSol(self, e):
        if not cbook.ProxyAlive(self._model):
            ret = dialog.message(None,
                                 'Set working model in setting panel',
                                 'Model is not specified',
                                 )
            return

        val = self.init_sol()
#        if not cbook.ProxyAlive(self._param):
#            ret=dialog.message(None,
#                      'global parameter is not specified and was not copied',
#                      'Warning: No global parameter copied')
        ifigure.events.SendChangedEvent(self, e.GetEventObject())

    def is_valid_setting(self):
        return True

    def init_sol(self):
        return init_sol(self)

    def creat_sol(self):
        '''
        add a new sol folder
        '''
        root = self.get_root_parent()
        sol_exist = False
#        if not cbook.ProxyAlive(self._sol):
#           print "creating solution folder"
        root.set_psol(None)
        root = self.get_root_parent()
        root.onAddSol()
        psol = root.psol
        self._sol = psol
        psol.setvar("solver", self.get_full_path())
        return psol, sol_exist

    def get_target_model(self, model, solbase):
        modelbase = model.get_root_model()
        path = [model.name]
        while (model.get_full_path() !=
               modelbase.get_full_path()):
            model = model.get_parent()
            path = [model.name]+path

        sol = solbase
        for name in path:
            sol = sol.get_child(name=name)
        return sol

    def onSetting(self, e):
        list = onSettingList(self)
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')

    def setSetting(self, value):
        setSetting(self, value)

    def get_workers(self):
        return [w for name, w in self.get_children() if isinstance(w, PySol)]


class PyStdSolver(BaseSolver):
    ''' 
    standard solver is almost same as the base solver.
    it has an additional run scriopt already.
    '''

    def __init__(self, *args, **kargs):
        super(PyStdSolver, self).__init__(self, *args, **kargs)
        self._use_def_merger = True

    @classmethod
    def get_namebase(self):
        return 'stdsolver'

    def load_default_script(self):
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'run_stdsolver.py')
        sc = PyScript()
        self.add_child('solver_script', sc)
        sc.import_script(file)
        self.add_default_mergesol_script()

    def add_default_mergesol_script(self):
        if self.has_child('merge_sol'):
            return
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'merge_sol_std.py')
        sc = PyScript()
        self.add_child('merge_sol', sc)
        sc._name_readonly = True
        sc.import_script(file)
#        sc.setvar("task", 2)

    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        l = [('Run  (F9)', self.onRun, None),
             ('Setting...', self.onSetting, None),
             ('Initialize Solution', self.onInitSol, None), ]
        return l + [('---', None, None), ] + \
            super(PyCode, self).tree_viewer_menu()

    def onAbort(self, evt):
        self._queue.put('abort job')

    def onRun(self, e=None):
        if not self.is_valid_setting():
            return

        if self._sol:
            ret = dialog.message(
                message="Solution folder exists. Do you want to erase it?\n (No: New Sol, Yes:Overwrite, Cancel:Stop)", style=5)
            if ret == 'cancel':
                return
            if ret == 'yes':
                self._sol.destroy()
            ifigure.events.SendChangedEvent(self, wx.GetApp().TopWindow)

        self.init_sol()
        self.solver_script.Run()
        if e is not None:
            e.Skip()
        return

    def init_sol(self, sol=None):
        if sol is None:
            psol, sol_exist = self.creat_sol()
        else:
            print("error: sol is supposed to be None here")
            return

        for x in [x for x in self.walk_tree() if isinstance(x, PySol)]:
            x.destroy()

        ps = PySol()
        self.add_child('worker', ps)
        ps.add_child('parameters', PyParam())

        ifigure.events.SendChangedEvent(self)
        return True

    def onSetting(self, e):
        list = onSettingList(self)
        list = list + [
            [None,  self._use_def_merger, 3,
                {"text": "Use standard merger", "expand": True}], ]
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')

    def setSetting(self, value):
        setSetting(self, value)
        self._use_def_merger = value[4]

    def save_data2(self, data):
        vars = ('_use_def_merger', )
        h2 = {key: getattr(self, key) for key in vars}
        data['PyStdSolover'] = (1, h2)
        data = super(PyStdSolver, self).save_data2(data)
        return data

    def load_data2(self, data):
        super(PyStdSolver, self).load_data2(data)
        if 'PyStdSolver' in data:
            h2 = data['PyStdSolver'][1]
            for key in h2:
                setattr(self, key, h2[key])


class PyParametric(BaseSolver):
    ''' 
    parametric solver is for parametric scan.
    it has an addional setting field _param_names
    and modifier module, which modify the model
    based on parameter
    '''

    def __init__(self, *args, **kargs):
        super(PyParametric, self).__init__(self, *args, **kargs)
        self._pname = None
        self._pvalue = None
        self._num_worker = 2
        self._expand_itertools_product = False
        self._expand_lhs = False
        self._expand_lhs_parmas = [10, "center"]
        self._use_def_merger = False
        self.setvar("param name", ("name1", "name2"))
        self.setvar("param value", ((1, 1), (1, 2), (2, 1), (2, 2)))
#        self.setvar("use thread", False)
    @classmethod
    def get_namebase(self):
        return 'parametric'

    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        l = [('Run  (F9)', self.onRun, None),
             ('Setting...', self.onSetting, None),
             ('Initialize Solution', self.onInitSol, None),
             ('Solve All Cases', self.onSolveAllCases, None),
             ('Solve Cases...', self.onSolveCases, None), ]
        if self._queue is not None:
            l.append(('Abort', self.onAbort, None))
        return l + [('---', None, None), ] + \
            super(PyCode, self).tree_viewer_menu()

    def onAbort(self, evt):
        self._queue.put('abort job')

    def load_default_script(self):
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'run_parametric.py')
        sc = PyScript()
        self.add_child('solver_script', sc)
        sc._name_readonly = True
        sc.import_script(file)
        sc.setvar("task", 2)
        self.add_default_mergesol_script()

    def add_default_mergesol_script(self):
        if self.has_child('merge_sol'):
            return
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'merge_sol_parametric.py')
        sc = PyScript()
        self.add_child('merge_sol', sc)
        sc._name_readonly = True
        sc.import_script(file)
#        sc.setvar("task", 2)

    def is_valid_setting(self):
        if (self._pname is None or
                self._pvalue is None):
            return False
        return True

    def init_sol(self, sol=None):
        if not self.is_valid_setting():
            return
        if sol is None:
            psol, sol_exist = self.creat_sol()
        else:
            print("error: sol is supposed to be None here")
            return

        vname = self._pname
        value = self._pvalue
        use_worker = self._num_worker > 0
        name_base = 'case'

        for name, child in psol.get_children():
            child.destroy()

        parent = psol
#        print [x for x in self.walk_tree() if isinstance(x, PySol)]
        for x in [x for x in self.walk_tree() if isinstance(x, PySol)]:
            x.destroy()
        if use_worker:
            #            for x in range(self._num_worker):
            #                ps = PySol()
            #                self.add_child('worker'+str(x), ps)
            value = self._pvalue[:self._num_worker]
            name_base = 'worker'
            parent = self

        i = 0

        app = wx.GetApp().TopWindow
        pgb = dialog.progressbar(app,
                                 'prepareing '+str(len(value)) +
                                 ' sol folders',
                                 'initialize sol', len(value))

        check = True
        for i, v in enumerate(value):
            ps = PySol()
            parent.add_child(name_base + str(i), ps)
            ps.setvar("name", vname)
            ps.setvar("value", v)
            if i == 0:
                flag, tmpdir = init_sol(self, sol=ps, mode=1)
                check = check and flag
            else:
                check = check and init_sol(self, sol=ps, mode=2,
                                           tmpdir=tmpdir)
            pgb.Update(i)
        shutil.rmtree(tmpdir+'_bk')
        pgb.Destroy()
        ifigure.events.SendChangedEvent(self)
        return check

    def print_cases(self):
        print(self._pvalue)

    def onRun(self, evt):
        if not self.is_valid_setting():
            return
        if self._sol:
            ret = dialog.message(
                message="Solution folder exists. Do you want to erase it?\n(No: New Sol, Yes:Overwrite, Cancel:Stop)", style=5)
            if ret == 'cancel':
                return
            if ret == 'yes':
                self._sol.destroy()
            ifigure.events.SendChangedEvent(self, wx.GetApp().TopWindow)

        self.init_sol()
        sc = self.solver_script
        self._run_cases = [True]*len(self._pvalue)
        sc.setvar("task", 2)
        sc.do_run()
        sc.setvar("task", 2)
        if evt is not None:
            evt.Skip()

    def onApplyModifier(self, evt):
        sc = self.solver_script
        sc.setvar("task", 1)
        sc.do_run()
        sc.setvar("task", 2)

    def onSolveAllCases(self, evt):
        sc = self.solver_script
        self._run_cases = [True]*len(self._pvalue)
        sc.setvar("task", 2)
        sc.do_run()
        sc.setvar("task", 2)

    def onSolveCases(self, evt):
        shellvar = self.get_root_parent().app.shell.lvar
        l = [["", "Enter Case Index", 2],
             ["Index", '[1]', 100, {'ns': shellvar}], ]
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(l, self, 'run_cases')

    def run_cases(self, value=None, index=None):
        self._run_cases = [False]*len(self._pvalue)
        if value is not None:
            for x in value[1][1]:
                self._run_cases[x] = True
        elif index is not None:
            for x in index:
                self._run_cases[x] = True

        sc = self.solver_script
        sc.setvar("task", 2)
        sc.do_run()
        sc.setvar("task", 2)

    def apply_modifier(self, modifier, case_xx, i):
        sols = self.get_pysol(self._sol)
        num = len(sols)
#        pgb = dialog.progressbar(self.get_root_parent().app,
#                    'prepareing '+str(num)+ ' sol folders',
#                    'initialize sol', num)

        vname = self._pname
        value = self._pvalue

#        for i, case_xx in enumerate(sols):
        case_xx.setvar("name", vname)
        case_xx.setvar("value", value[i])
        n = case_xx.getvar("name")
        if (not isinstance(n, list) and
                not isinstance(n, tuple)):
            n = (n,)
        v = case_xx.getvar("value")
        if (not isinstance(v, list) and
                not isinstance(v, tuple)):
            v = (v,)
        modifier(case_xx, n, v)
#        pgb.Update(i)
#        pgb.Destroy()

    def get_expand_setting_value(self):
        expand = 'Expand...'
        if self._expand_itertools_product:
            expand = 'Product'
        if self._expand_lhs:
            expand = 'LatinHyperCube'
        data = [expand,
                [None,],
                [None,],
                [None, str(self._expand_lhs_parmas[0]), self._expand_lhs_parmas[1]],]
        return data
    
    def call_lhs(self, params, xlimits):
        num = int(params[0])
        method = params[1]
        
        from smt.sampling_methods import LHS

        try:
            xlimits = np.array(list(xlimits))            
            sampling = LHS(xlimits=xlimits, criterion=method)            
            x = sampling(num)
            
        except BaseException:
            import traceback
            traceback.print_exc()

            print("Error!")
            print("LHS was called with following parameters...")
            print(num, method, xlimits)
            return []
        ## I need to transform it to tuple...;D
        return tuple([tuple(xx) for xx in x])

    def onSetting(self, e):
        list = onSettingList(self)
        txt1 = str(self.getvar("param name"))
        txt2 = str(self.getvar("param value"))
        shellvar = self.get_root_parent().app.shell.lvar

        expand_values = self.get_expand_setting_value()
        print("value here", expand_values)
        ss1 = {"style": wx.CB_READONLY,
               "choices":["center", "maximin", "centermaximin", "correlation",
                          "c", "m", "cm", "corr", "ese"]}
        list = list + [
            ["Parameter Names", txt1, 100, {'ns': shellvar}],
            ["Parameter Values", txt2, 100, {'ns': shellvar}],
            [None,  expand_values, 34, [{'text': "",
                                'call_fit': False, 
                                'choices': ['Expand...',
                                            'Product',
                                            'LatinHyperCube',],},
                     {'elp':[(None, "Parameters are used As-Is", 2, None)]},
                     {'elp':[(None, "Parameters are expanded using Itertools.product", 2, None)]},
                     {'elp':[(None, "Parameters are expanded using smt.sampling_methods.LHS", 2, None),
                             ("#points", "10", 0, None),
                             ("method", "center", 4, ss1)
                      ]},]],
            #[None,  self._expand_itertools_product, 3,
            # {"text": "Expand parameters by itertool.product", "expand": True}],
            [None,  self._use_def_merger, 3,
             {"text": "Use standard merger", "expand": True}],
            [None,  self._num_worker > 0, 3,
             {"text": "Use workers", "expand": True}],
            ["Number of workers", str(abs(self._num_worker)), 0], ]
#                ["Use multiple thread", txt3, 1 ]]
        app = wx.GetApp().TopWindow

        style = app.proj_tree_viewer.get_defaultpanelstyle()
        style = wx.RESIZE_BORDER|style
        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting',
                                       title='Parametric sweep',
                                       style=style)

    def setSetting(self, value):
        setSetting(self, value)
        self.setvar("param name", str(value[4][0]))
        self.setvar("param value", str(value[5][0]))

        self._pname = value[4][1]

        self._expand_itertools_product = False
        self._expand_lhs = False
        
        if value[6][0] == 'Product':
            import itertools
            self._expand_itertools_product = True
            self._pvalue = tuple(itertools.product(*(value[5][1])))
        elif value[6][0] == 'LatinHyperCube':
            import itertools
            self._expand_lhs = True
            self._expand_lhs_parmas = value[6][3][1:]
            self._pvalue = self.call_lhs(value[6][3][1:], value[5][1])
        else:
            self._pvalue = value[5][1]
        self._num_worker = abs(
            int(value[9])) if value[8] else -abs(int(value[8]))
        self._use_def_merger = value[7]
#        if value[6] == 'on':
#            use_thread = self.setvar("use thread", True)
#        else:
#            use_thread = self.setvar("use thread", False)

    def save_data2(self, data):
        vars = ('_expand_itertools_product', '_pname',
                '_pvalue', '_num_worker', '_use_def_merger')
        h2 = {key: getattr(self, key) for key in vars}
        data['PyParametric'] = (1, h2)
        data = super(PyParametric, self).save_data2(data)
        return data

    def load_data2(self, data):
        super(PyParametric, self).load_data2(data)
        if 'PyParametric' in data:
            h2 = data['PyParametric'][1]
            for key in h2:
                setattr(self, key, h2[key])


class PyOptimizer(PyStdSolver):
    def __init__(self, *args, **kargs):
        super(PyOptimizer, self).__init__(*args, **kargs)
        self.setvar("param name", ("name1", "name2"))
        self.setvar("init_value", (1, 1))
        self.setvar("opt_kwrds", {})
        self._pname = ('name1', 'name2')
        self._init_value = (1, 1)
        self._cost = '.cost'

    @classmethod
    def get_namebase(self):
        return 'optimizer'

    def load_default_script(self):
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'run_optimizer.py')
        sc = PyScript()
        self.add_child('solver_script', sc)
        sc.import_script(file)
        self.add_default_mergesol_script()
        self.add_default_cost_script()

    def add_default_cost_script(self):
        if self.has_child('cost'):
            return
        base_mod = 'ifigure.add_on.solver.script'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, 'cost_optimizer.py')
        sc = PyScript()
        self.add_child('cost', sc)
        sc._name_readonly = True
        sc.import_script(file)
#        sc.setvar("task", 2)

    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        l = super(PyOptimizer, self).tree_viewer_menu()
        if self._queue is not None:
            l.insert(3, ('Abort', self.onAbort, None))
        return l

    def onSetting(self, e):
        list = onSettingList(self)
        txt1 = str(self.getvar("param name"))
        txt2 = str(self.getvar("init_value"))
        txt3 = str(self.getvar("opt_kwrds"))
        shellvar = self.get_root_parent().app.shell.lvar

        list = list + [
            ["Parameter Names", txt1, 100, {'ns': shellvar}],
            ["Initial Values", txt2, 100, {'ns': shellvar}],
            ["Optimize kwrds", txt3, 100, {'ns': shellvar}],
            ["Cost", '.cost', 0],
            [None,  self._use_def_merger, 3,
                {"text": "Use standard merger", "expand": True}], ]

        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')

    def setSetting(self, value):
        setSetting(self, value)
        self.setvar("param name", str(value[4][0]))
        self.setvar("init_value", str(value[5][0]))
        self.setvar("opt_kwrds", str(value[6][0]))

        self._pname = value[4][1]
        self._init_value = value[5][1]
        self._opt_kargs = value[6][1]
        self._cost = str(value[7])
        self._use_def_merger = value[8]

    def onAbort(self, evt):
        self._queue.put('abort job')

    def save_data2(self, data):
        vars = ('_pname', '_cost',
                '_opt_kargs', '_init_value', '_use_def_merger')
        h2 = {key: getattr(self, key) for key in vars}
        data['PyOptimizer'] = (1, h2)
        data = super(PyOptimizer, self).save_data2(data)
        return data

    def load_data2(self, data):
        super(PyOptimizer, self).load_data2(data)
        if 'PyOptimizer' in data:
            h2 = data['PyOptimizer'][1]
            for key in h2:
                setattr(self, key, h2[key])
