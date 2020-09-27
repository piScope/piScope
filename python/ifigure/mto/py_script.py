from __future__ import print_function
#
#  Name   : py_script
#
#          mto to hold a script in the tree
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History : 0.5 sometime around Apr. 2012
#            0.6 stop() command
#            0.7 8/30/12 keyborad interupt
#
from ifigure.mto.treelink import TreeLink
import collections
import weakref
import os
import logging
import wx
import threading
import types
import shutil
import multiprocessing
import sys
import traceback
import ifigure.utils.pickle_wrapper as pickle
from ifigure.mto.py_code import PyCode
import ifigure.utils.cbook as cbook
import ifigure
import ifigure.events
import ifigure.widgets.dialog as dialog
from ifigure.mto.fileholder import FileHolder

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('PyScript')

txt1 = '(job involving GUI access, such as graphics generation,\nshould not use this option.)'


class ScriptStop(Exception):
    def __init__(self, message=''):
        super(Exception, self).__init__()
        self.message = message

    def __str__(self):
        return repr(self.messge)


class ExitScript(Exception):
    def __init__(self, message=''):
        super(Exception, self).__init__()
        self.message = message

    def __str__(self):
        return repr(self.message)


def stop(message=''):
    raise ScriptStop(message)


def exit(message=''):
    raise ExitScript(message)


class AnsHolder(object):
    def get_ansfunc(self):
        self._ans = None

        def ans(value=None, obj=self):
            obj._ans = value
            raise ExitScript('')
        return ans

    def get_ansfunc_array(self, l):
        self._ans = [None]*l
        ret = [None]*l
        for k in range(l):
            def ans(value, obj=self, i=k):
                obj._ans[i] = value
                raise ExitScript('')
            ret[k] = ans
        return ret

    def RunA(self, *args, **kargs):
        self.Run(*args, **kargs)
        if 'ans' in kargs:
            obj = kargs['ans'].__defaults__[1]
        else:
            obj = self
        val = obj._ans
        obj._ans = None
        #val =  self._ans
        #self._ans = None
        return val

    def __call__(self, *args, **kargs):
        return self.RunA(*args, **kargs)

    @property
    def ans(self):
        return self._ans


class AbsScript(object):
    #
    #  interface to run python script
    #  this part should be independent from
    #  GUI and tree structure.
    #    provide
    #        automatic update check
    #        launch editor
    #
    def __init__(self):
        #        self._script_file=''
        self._script = ''
        self._script_co = None
        self._script_mtime = 0.
        self._debug = 0

    def is_objectold(self, obj):
        script_file = obj.path2fullpath()
        if script_file == '':
            return False
        if (os.path.getmtime(script_file) >
                self._script_mtime):
            return True
        return False

    def run_script(self, obj=None, top=None, param=None,
                   wdir=None, app=None, model=None,
                   **kargs):

        script_file = obj.path2fullpath()
        logging.basicConfig(level=logging.DEBUG)
        if script_file == '':
            return

        if (os.path.getmtime(script_file) >
                self._script_mtime):
            self.load_script(script_file)
        if self._script_co is not None:
            debug = self._debug

            def write_log(*args):
                top.write_log(obj, model, *args)

            lc = obj.get_namespace()
            lc2 = {"obj": obj, "proj": top, "top": top,  "param": param,
                   "wdir": wdir, "app": app, "model": model,  "stop": stop,
                   "exit": exit, "write_log": write_log}
            for key in lc2:
                lc[key] = lc2[key]
            for key in kargs:
                lc[key] = kargs[key]

            self._debug = 0  # make sure that next time will run in normal mode
            try:
                if debug == 0:
                    exec(self._script_co, lc, lc)
                elif debug == 1:
                    import pdb
                    pdb.run(self._script_co, lc, lc)
                elif debug == 2:
                    app.script_editor.RunSED(
                        self._script_co, lc, lc, script_file)

            except ExitScript:
                return True
            except ScriptStop as e:
                print(('Script execution stops : ', e.message))
                return False
            except Exception:
                print('script exectuion failed')
                print(traceback.format_exc())
                return False
                #logging.exception("Script Execution Failed")
            return True

    def load_script(self, file):
        if file is None:
            return
        if file == '':
            return
        try:
            a, b, c = cbook.LoadScriptFile(file)
            self._script = a
            self._script_co = b
            self._script_mtime = c
        except:
            self._script = ''
            self._script_co = None
            self._script_mtime = -1

            print('Failed to compile script '+file)
            print(traceback.format_exc())
            return traceback.format_exc()
        return ''

#  this decorator
class doc_decorator(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kargs):
        return self.func.__call__(self.obj, *args, **kargs)

    def __get__(self, instance, owner):
        self.cls = owner
        self.obj = instance
        self.__call__.__func__.__doc__ = instance._run_doc
        return self.__call__


class PyScriptLink(TreeLink, AnsHolder):
    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'script_link.png')
        return [idx]

    def __call__(self, *args, **kargs):
        model = self.get_pymodel()
        kargs['model'] = model
        kargs['ans'] = self.get_ansfunc()

        if self.is_linkalive:
            t = self.get_linkobj()
            return t.__call__(*args, **kargs)

    def Run(self, *args, **kargs):
        model = self.get_pymodel()
        kargs['model'] = model
        kargs['ans'] = self.get_ansfunc()

        if self.is_linkalive:
            t = self.get_linkobj()
            return t.Run(*args, **kargs)

    def Debug(self, *args, **kargs):
        model = self.get_pymodel()
        kargs['model'] = model
        kargs['ans'] = self.get_ansfunc()

        if self.is_linkalive:
            t = self.get_linkobj()
            return t.Debug(*args, **kargs)

    def do_run(self, *args, **kargs):
        return self.Run(*args, **kargs)

    def do_run_f(self, *args, **kargs):
        model = self.get_pymodel()
        kargs['model'] = model
        kargs['ans'] = self.get_ansfunc()

        if self.is_linkalive:
            t = self.get_linkobj()
            return t.do_run_f(*args, **kargs)

    def do_run_t(self, e, *args, **kargs):
        model = self.get_pymodel()
        kargs['model'] = model
        kargs['ans'] = self.get_ansfunc()

        if self.is_linkalive:
            t = self.get_linkobj()
            return t.do_run_t(e, *args, **kargs)

    def tree_viewer_menu(self):
        return [('+Script', None, None),
                ('Run (F9)', self.onRunQuick, None),
                ('Run...', self.onRunFull, None),
                ('Edit...', self.onEditScript, None),
                ('!', None, None),
                ('---', None, None)] + \
            super(TreeLink, self).tree_viewer_menu()

    def onRunQuick(self, e):
        if not self.is_linkalive:
            return
        t = self.get_linkobj()

        ns = self.get_root_parent().app.shell.lvar.copy()
        args = t.getvar('script_args')
        kargs = t.getvar('scriptk_kwargs')
        if kargs is None:
            kargs = '{}'
        if args is None:
            args = '()'
        try:
            args = eval(args, ns, ns)
        except Exception:
            args = ()
        kargs = t.getvar('scriptk_kwargs')
        try:
            kargs = eval(kargs, ns, ns)
        except Exception:
            kargs = {}
        self.do_run_f(*args, **kargs)

    def onRunFull(self, e):
        if not self.is_linkalive:
            return
        t = self.get_linkobj()

        args = t.getvar('script_args')
        if args is None:
            args = '()'
        kargs = t.getvar('scriptk_kwargs')
        if kargs is None:
            kargs = '{}'
        shellvar = self.get_root_parent().app.shell.lvar

        # the following makes a crash
        list = [["", "Run script ("+self.compact_name()+")", 2],
                ["Args", str(args), 100, {'ns': shellvar}],
                ["Kwargs", str(kargs), 100, {'ns': shellvar}],
                #                ["model variable", self.getvar('script_model'), 0, {}],
                ["Use thread", False, 3,
                 {"text": txt1, "expand": True}]]

        self.get_root_parent().app.proj_tree_viewer.OpenPanel(list, self, 'handle_run_full',
                                                              event=e)
        e.Skip()

    def handle_run_full(self, value, event=None):
        if not self.is_linkalive:
            return

        t = self.get_linkobj()
        t.setvar('script_args', value[1][0])
        t.setvar('script_kwargs', value[2][0])

        kargs = value[2][1]
        kargs['model'] = self.get_pymodel()
        if value[3]:
            wx.CallAfter(self.do_run_t, event, *(value[1][1]), **kargs)
        else:
            wx.CallAfter(self.do_run_f,  *(value[1][1]), **kargs)

    def onEditScript(self, evt):
        if self.is_linkalive:
            t = self.get_linkobj()
            t.onEditScript(evt)

    def init_after_load(self, olist, nlist):
        xxx = super(PyScriptLink, self).init_after_load(olist, nlist)
        self._status = ''
        return xxx


class PyScript(PyCode, FileHolder, AnsHolder):
    def __init__(self, parent=None, script='', src=None):
        self._script = AbsScript()
        self._simplemenu = False
        super(PyScript, self).__init__(parent=parent, src=src)
 #       self.setvar("script file", None)
        self.setvar("background", False)
        self.setvar("script_args", '()')
        self.setvar("script_kwargs", '{}')
        self.setvar("script_model", '')
        self._script.load_script(None)
        self._can_have_child = False
        self._has_private_owndir = False
        self._run_doc = ''
        self._save_link = False

    @classmethod
    def isPyScript(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'script'

    def classimage(self):
        if PyScript._image_load_done is False:
            PyScript._image_id = self.load_classimage()
            PyScript._image_load_done = True

        if self.getvar('pathmode') == 'owndir':
            return PyScript._image_id[0]
        else:
            return PyScript._image_id[1]


    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'script.png')
        idx2 = cbook.LoadImageFile(path, 'script_ext.png')
        return [idx1, idx2]

    @classmethod
    def can_have_child(self, child=None):
        return False

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_F9:
            return self.onRunQuick
        if key == wx.WXK_RETURN:
            return self.onEditScript
        return None

    def on_runf_menu(self, evt):
        return self.onRunF()

    @doc_decorator
    def Run(self, *args, **kargs):
        if self.getvar("background") and self._script._debug == 0:
            return self.do_run_t(None, *args,   **kargs)
        else:
            return self.do_run_f(*args, **kargs)

    def RunT(self, *args, **kargs):
        return self.do_run_t(None, *args,   **kargs)

#    def Debug1(self,  *args, **kargs):
#        self._script._debug = 1
#        wx.CallAfter(self.Run, *args, **kargs)

    def Debug(self,  *args, **kargs):
        se = wx.GetApp().TopWindow.script_editor
        if not se.CheckDebuggerStatus():
            ret = dialog.message(
                self, 'Debugger is running.', 'Please wait', 0)
            return
        self._script._debug = 2
        se.GoDebugMode(self.path2fullpath(), enter=True)
        wx.CallAfter(self.Run, *args, **kargs)

    def do_run(self, *args, **kargs):
        return self.Run(*args, **kargs)

    def do_run_f(self, *args, **kargs):

        if 'model' in kargs:
            model = kargs['model']
            ans = kargs['ans']
            del kargs['model']
            del kargs['ans']
        else:
            model = self.get_pymodel()
            ans = self.get_ansfunc()
        p = model
        param = None
        while p is not None:
            if p.has_child('param'):
                param = p.param
                break
            p = p.get_parent()
        if param is None:
            if self.get_root_parent().has_child('parameters'):
                param = self.get_root_parent().has_child('parameters')

        kargs = {"obj": self,
                 "top": self.get_root_parent(),
                 "app": self.get_root_parent().app,
                 "wdir": self.get_root_parent().getvar("wdir"),
                 "model": model,
                 "param": param,
                 "ans": ans,
                 "args": args,
                 "kwargs": kargs}

        if self._suppress is False:
            val = self._script.run_script(**kargs)
            ifigure.events.SendChangedEvent(self)
            return val
        else:
            dprint1('script is suppressed')

    def do_run_t(self, e, *args, **kargs):
        app = wx.GetApp().TopWindow
        maxt = app.aconfig.setting['max_thread']
#        print len(app.logw.threadlist), maxt
        if len(app.logw.threadlist) < maxt:
            #aargs = [model] + list(args)
            t = threading.Thread(target=self.do_run_f, args=args, kwargs=kargs)
            self._status = 'launching...'
            # useProcessEvent is True so that threadlist in logw is
            # updated
            ifigure.events.SendThreadStartEvent(self, w=self.get_app(),
                                                thread=t,
                                                useProcessEvent=True)
        else:
            wx.CallLater(1000, self.do_run_t, e, *args, **kargs)
        if e is not None:
            e.Skip()

    def call(self, name, *args, **kargs):
        '''
        call function in script file
             call(fname, *args, **kargs)
        note:
           this is a hacky program and use of this
           method should be restricted to write
           something temporary. For more permanent 
           implementation, put function in py_module
           or use an usual "import....". 

        restriction:
           default arguments can not be used.
        '''
        f = self.get_function(name)
        if f is None:
            return
        return f(*args, **kargs)

    def get_function(self, name):
        '''
        call function in script file
             call(fname, *args, **kargs)
        note:
           this is a hacky program and use of this
           method should be restricted to write
           something temporary. For more permanent 
           implementation, put function in py_module
           or use an usual "import....". 

        restriction:
           default arguments can not be used.
        '''
        code = None
        for code in self._script._script_co.co_consts:
            if isinstance(code, types.CodeType):
                if code.co_name is name:
                    break

        if code is None:
            raise AttributeError("Function does not exist:  "+name)
        else:
            #
            #            import types
            #
            def hack():
                pass
            hack.__code__ = code
            hack.__name__ = name
            return hack

    def onRunQuick(self, e):
        ns = self.get_root_parent().app.shell.lvar.copy()
        args = self.getvar('script_args')
        kargs = self.getvar('scriptk_kwargs')
        if kargs is None:
            kargs = '{}'
        if args is None:
            args = '()'
        try:
            args = eval(args, ns, ns)
        except Exception:
            args = ()
        kargs = self.getvar('scriptk_kwargs')
        try:
            kargs = eval(kargs, ns, ns)
        except Exception:
            kargs = {}
        self.do_run_f(*args, **kargs)

    def onRunFull(self, e, title='Run script'):
        args = self.getvar('script_args')
        if args is None:
            args = '()'
        kargs = self.getvar('scriptk_kwargs')
        if kargs is None:
            kargs = '{}'
#        self.do_run_t(e, *args, **kargs)
#        return
        shellvar = self.get_root_parent().app.shell.lvar
        # the following makes a crash
        list = [["", "Run script ("+self.compact_name()+")", 2],
                ["Args", str(args), 100, {'ns': shellvar}],
                ["Kwargs", str(kargs), 100, {'ns': shellvar}],
                ["model variable", self.getvar('script_model'), 0, {}],
                ["Use thread", False, 3,
                 {"text": txt1, "expand": True}]]

        self.get_root_parent().app.proj_tree_viewer.OpenPanel(list, self, 'handle_run_full',
                                                              title=title, event=e)
        e.Skip()

    def handle_run_full(self, value, event=None):
        self.setvar('script_args', value[1][0])
        self.setvar('script_kwargs', value[2][0])
        self.setvar('script_model', str(value[3]))
        if str(value[3]).strip() == '':
            models = [self.get_pymodel()]
        else:
            models = self.expand_path(str(value[3]))

        if len(models) == 1:
            anses = [self.get_ansfunc()]
        else:
            anses = self.get_ansfunc_array(len(models))
        for ans, m in zip(anses, models):
            kargs = value[2][1]
            kargs['model'] = m
            kargs['ans'] = ans

            if value[4] and self._script._debug == 0:
                wx.CallAfter(self.do_run_t, event, *(value[1][1]), **kargs)
            else:
                wx.CallAfter(self.do_run_f,  *(value[1][1]), **kargs)

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        flag = ''
        if self._script is not None:
            d = self._script._debug
            try:
                if self._script.is_objectold(self):
                    file = self.path2fullpath()
                    self.load_script(file)
            except:
                dprint1('Script loading failed ' + str(self))
                flag = '*'
        else:
            d = 0
        a = ['0', '1', '2']
        a[d] = '-'+a[d]

        se = wx.GetApp().TopWindow.script_editor
        dflag = '' if se.CheckDebuggerStatus() else '-'

        if self._simplemenu:
            return [('+Script', None, None),
                    (flag+'Run (F9)', self.onRunQuick, None),
                    (flag+'Run...', self.onRunFull, None),
                    (flag+'Edit...', self.onEditScript, None),
                    ('Import File...', self.onImportScriptFile, None),
                    (flag+'Export File...', self.onExportScriptFile, None),
                    (dflag+'Debug...', self.onDebug2, None),
                    ('!', None, None),
                    ('---', None, None)] + \
                super(PyCode, self).tree_viewer_menu()
        else:
            m = [('+Script', None, None),
                 ('Run (F9)', self.onRunQuick, None),
                 ('Run...', self.onRunFull, None), ]
            if not self._is_in_pysol():
                m.append((flag+'Run at Sol...', self.onRunAtSol, None))
            m.extend([(flag+'Edit...', self.onEditScript, None),
                      ('Import File...', self.onImportScriptFile, None),
                      (flag+'Export File...', self.onExportScriptFile, None),
                      (flag+'Update scripts in Sol...', self.onExportToSol, None),
                      #               ('+Degug...', None, None),
                      #               ('Run in PDB', self.onDebug1, None),
                      (dflag+'Debug...', self.onDebug2, None),
                      #               ('Import File', self.onImportScriptFile, None),
                      #               ('!', None, None),
                      #               ('+Run Mode', None, None),
                      #               ('-'*self.is_manualonly()+'Manual Only', self.onManual, None),
                      #               ('-'*(not self.is_manualonly())+'Auto', self.onAuto, None),
                      #               ('!', None, None),
                      ('!', None, None),
                      ('---', None, None)])
            m = m + super(PyScript, self).tree_viewer_menu()
            return m

#    def onDebug1(self, e):
#        self._script._debug = 1
#        self.onRunQuick(e)

    def onDebug2(self, e):
        se = wx.GetApp().TopWindow.script_editor
        if not se.CheckDebuggerStatus():
            ret = dialog.message(
                self, 'Debugger is running.', 'Please wait', 0)
            return
        self._script._debug = 2
        se.GoDebugMode(self.path2fullpath(), enter=True)
        self.onRunFull(e, title='Debug run...')

    def onManual(self, e):
        self._manual_only = True

    def onAuto(self, e):
        self._manual_only = False

    def _is_in_pysol(self):
        from ifigure.mto.py_code import PySol
        p = self
        while p is not None:
            if isinstance(p, PySol):
                return True
            p = p.get_parent()
        return False

    def _make_list1(self, sol_list, p):
        from ifigure.mto.py_code import PySol
        for name, child in p.get_children():
            if isinstance(child, PySol):
                src = child.getvar('source_model')
                if src is not None:
                    src = self.find_by_full_path(src)
                    if src is not None:
                        if src.is_descendant(self):
                            sol_list.append(child.get_full_path())
                self._make_list1(sol_list, child)
        return sol_list

    def _make_list2(self, sol_list, p):
        from ifigure.mto.py_code import PySol
        if isinstance(p, PySol):
            src_name = p.getvar('source_model')
            if src_name is not None:
                src = self.find_by_full_path(src_name)
                if src is not None:
                    if src.is_descendant(self):
                        sol_list.append((p, src_name))
        for name, child in p.get_children():
            sol_list = self._make_list2(sol_list, child)
        return sol_list

    def _ask_at_sol_conditionl(self, e):
        from ifigure.mto.py_code import PySol
        proj = self.get_root_parent()
        sol_list = self._make_list1([], proj)

        if len(sol_list) == 0:
            dlg = wx.MessageDialog(self.get_app(),
                                   "No solution based on this model is found",
                                   "Error", wx.OK | wx.ICON_INFORMATION)
            ans = dlg.ShowModal()
            dlg.Destroy()
            return

        shellvar = proj.app.shell.lvar
        list = [[None, "Run at SOL ("+self.compact_name()+")", 2],
                ["sol", sol_list[0], 4, {'style': wx.CB_DROPDOWN,
                                         'choices': sol_list}],
                ["Args", '()', 100, {'ns': shellvar}],
                ["Kwargs", '{}', 100, {'ns': shellvar}],
                ["Use thread", False, 3,
                 {"text": txt1, "expand": True}]]
        return list

    def _find_script_in_sol(self, sol, src_name):
        model = self.find_by_full_path(src_name)
#        path =  [model.name]+ model.get_relative_path(self)
        path = [model.name] + model.get_td_path(self)[1:]
        obj = sol
        for name in path[:-1]:
            obj = obj.get_child(name=name)
        script = obj.get_child(name=path[-1])
        if script is None:
            if not obj.has_owndir():
                obj.mk_owndir()
            script = PyScript()
            obj.add_child(path[-1], script)
            fpath = os.path.join(script.owndir(), path[-1]+'.py')
            script.set_path_pathmode(fpath)
            print(('creating...', script))
            ifigure.events.SendChangedEvent(script, w=wx.GetApp().TopWindow)
        return script

    def onRunAtSol(self, e, title='Run at sol'):
        self._script._debug = 0
        list = self._ask_at_sol_conditionl(e)
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(
            list, self, 'handle_run_at_sol', title=title)

    def handle_run_at_sol(self, value):
        proj = self.get_root_parent()
        base_sol = str(value[1])
        sol_list = self._make_list2([], proj.find_by_full_path(base_sol))
        for sol, src_name in sol_list:
            script = self._find_script_in_sol(sol, src_name)
            print(('running...', script.get_full_path()))  # value
            if value[4]:
                wx.CallAfter(script.do_run_t, None, *
                             (value[2][1]), **(value[3][1]))
            else:
                #                script.do_run_f(*(value[2][1]), **(value[3][1]))
                wx.CallAfter(script.do_run_f,  *(value[2][1]), **(value[3][1]))

    def _select_sol(self, e):
        from ifigure.mto.py_code import PySol
        proj = self.get_root_parent()
        sol_list = self._make_list1([], proj)

        if len(sol_list) == 0:
            dlg = wx.MessageDialog(self.get_app(),
                                   "No solution based on this model is found",
                                   "Error", wx.OK | wx.ICON_INFORMATION)
            ans = dlg.ShowModal()
            dlg.Destroy()
            return

        shellvar = proj.app.shell.lvar
        list = [["", "Select Sol", 2],
                [" ", sol_list[0], 4, {'style': wx.CB_DROPDOWN,
                                       'choices': sol_list}], ]
        return list

    def onExportToSol(self, e):
        list = self._select_sol(e)
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.OpenPanel(list, self, 'handle_export_to_sol')

    def handle_export_to_sol(self, value):
        proj = self.get_root_parent()
        base_sol = str(value[1])
        sol_list = self._make_list2([], proj.find_by_full_path(base_sol))
        src_file = FileHolder.path2fullpath(self)
        for sol, src_name in sol_list:
            script = self._find_script_in_sol(sol, src_name)
            print(('updating...', script))
            dest_file = FileHolder.path2fullpath(script)
            shutil.copyfile(src_file, dest_file)

#    def run_all_sol(self, sol, src_name, bg, *args, **kargs):

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key

        '''
#        if not self._simplemenu:

        if key == wx.WXK_F9:
            return self.onRunQuick
        return super(PyScript, self).pv_kshortcut(key)

#        return None
#    def onRename(self, evt):
#        super(PyScript, self).onRename(evt)

    def onEditScript(self, e):
        fpath = FileHolder.path2fullpath(self)
        if fpath == '':
            return
        self._script.load_script(fpath)
#        app = self.get_root_parent().app
#        if app.helper.setting['use_editor']:
#            txt = app.helper.setting['editor'].format(fpath)
#            print txt
#            os.system(txt)
# else:
        from ifigure.mto.treedict import str_td
        fpath = str_td(fpath)
        fpath.td = self.get_full_path()
        ifigure.events.SendEditFileEvent(self,
                                         w=e.GetEventObject(),
                                         file=fpath)

    def onImportScriptFile(self, e=None, file=None):
        from ifigure.utils.addon_utils import onLoadFile
        ret = onLoadFile(self, message="Enter script file name",
                         modename='pathmode',
                         pathname='path',
                         extname='.py',
                         reject_loc=['wdir', 'owndir'],
                         file=file,
                         wildcard='*.py')

        if not ret:
            return
        file = self.path2fullpath()
        if self.getvar('pathmode') == 'owndir':
            newname = str(os.path.basename(file).split('.')[0])
            self.rename(newname)
        else:
            self.load_script(file)
#        ifigure.events.SendFileSystemChangedEvent(self)
#        self.load_script(file)
        return
        file = dialog.read(None, message="Select script",
                           wildcard='*.py')
        mode, path = FileHolder.fullpath2path(self, file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Import should import from somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return
        self.import_script(file)

    def onExportScriptFile(self, e):
        opath = self.path2fullpath()
        file = dialog.write(None, defaultfile=opath,
                            message="Enter script file name",
                            wildcard='*.py')
        if file == '':
            return
        mode, path = FileHolder.fullpath2path(self, file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Export should export to somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return
        path = FileHolder.path2fullpath(self)
        shutil.copyfile(path, file)

    def export_script(self, file):
        '''
        export scirpt file to file.
        the destination should be outside
        of wdir
        '''
        path = self.path2fullpath()
        mode, path0 = self.fullpath2path(file)
        if mode == 'wdir':
            # do not write inside proj directory
            print('can not export to wdir')
            return
        if mode == 'owndir':
            # do not write inside proj directory
            print('can not export to owndir')
            return

        shutil.copyfile(path, file)

    def import_script(self, file, copy_file=True):
        '''
        import *.py file from outside of wdir
        the location of original file will be
        saved to "ofile_path", "ofile_pathmode"
        '''
        mode, path = self.fullpath2path(file)
        if mode == 'wdir':
            # do nothing in this case
            print('can not import from wdir')
            return
        if mode == 'owndir':
            # do not write inside proj directory
            print('can not import from owndir')
            return

        self.setvar("ofile_path", str(path))
        self.setvar("ofile_pathmode", str(mode))

        if copy_file:
            if not self.has_owndir():
                self.mk_owndir()
            file2 = os.path.join(self.owndir(), self.name+'.py')
            shutil.copyfile(file, file2)
            self.load_script(file2)
        else:
            self.remove_ownitem(items=['path'])
            self.set_path_pathmode(path,  mode,  'path', '.py',
                                   checklist=['proj', 'home', 'abs'])
            self.load_script(file)

    def set_breakpoint(self, line, set=True):
        from ifigure.widgets.debugger_core import add_breakpoint, rm_breakpoint
        from ifigure.widgets.debugger import check_debugger_instance

        check_debugger_instance()
        path = FileHolder.path2fullpath(self)
        if set:
            add_breakpoint(path, line)
        else:
            rm_breakpoint(path, line)

    def get_breakpoint(self):
        from ifigure.widgets.debugger_core import get_breakpoint
        from ifigure.widgets.debugger import check_debugger_instance

        check_debugger_instance()
        path = FileHolder.path2fullpath(self)
        return get_breakpoint(path)

    def load_script(self, file):
        self.set_path_pathmode(file)
        err = self._script.load_script(file)
        if self._script._script_co is not None:
            self.set_doc(file)
        return err

    def set_doc(self, file):
        fid = open(file, 'r')

        doc = []
        l = 0
        doc_exist = False
        for x in fid.readlines():
            if ((x.startswith('"""') and l == 0) or
                    (x.startswith("'''") and l == 0)):
                doc_exist = True
            if ((x.startswith('"""') and l != 0) or
                    (x.startswith("'''") and l != 0)):
                doc.append(x)
                break
            if not doc_exist:
                break
            doc.append(x)
            l = l + 1
        doc = ''.join(doc)
        self._run_doc = doc
        self.__doc__ = doc
        fid.close()

    def has_script(self):
        file = self.path2fullpath()
        if (file != '' and
                os.path.exists(file)):
            return True
        return False

    def init_after_load(self, olist, nlist):
        #        print "loading", self.getvar("module file")
        name = self._name
        file = self.path2fullpath()
#        print file
        if (file != '' and
                os.path.exists(file)):
            self.load_script(file)
        self._name = name
        self._status = ''

    def reload_script(self):
        file = self.path2fullpath()
#        print file
        if (file != '' and
                os.path.exists(file)):
            return self.load_script(file)
        return ''

    def onProjTreeActivate(self, e):
        self.onEditScript(e)

    def rename(self, new,  ignore_name_readonly=False):
        osfile = self.path2fullpath()
        oname = self.name
        oowndir = self.owndir()

        super(PyScript, self).rename(
            new, ignore_name_readonly=ignore_name_readonly)

        sfile = self.path2fullpath()
        mode = self.getvar("pathmode")
        if mode == 'owndir':
            nsfile = os.path.join(self.owndir(), self.name+'.py')
            if os.path.exists(sfile):
                os.rename(sfile, nsfile)
                self.set_path_pathmode(nsfile)
            if os.path.exists(sfile+'c'):
                os.remove(sfile+'c')
            if os.path.exists(sfile+'o'):
                os.remove(sfile+'o')
        else:
            nsfile = sfile
        param = {"oldname": osfile, "newname": nsfile}
        op = 'rename'

        self.load_script(self.path2fullpath())
        ifigure.events.SendFileChangedEvent(self, operation=op,
                                            param=param)

        return

    def save2(self, fid=None, olist=None):
        if self._save_link:
            return self.save2_link(fid=fid, olist=olist)
        else:
            return super(PyScript, self).save2(fid=fid, olist=olist)

    def save2_link(self, fid=None, olist=None):
        obj = PyScriptLink(obj=self)
        h2 = {"name": obj.__class__.__name__,
              "module": obj.__class__.__module__,
              "num_child": 0,
              "sname": self.name,
              "id": self.id,
              "var0": None,
              "var": collections.OrderedDict(),
              "note": collections.OrderedDict(),
              "format": 2}
#        print h2
        if fid is not None:
            pickle.dump(h2, fid)

        c = olist.count(self.id)
        if c == 0:
            data = obj.save_data2({})
            pickle.dump(data, fid)
            olist.append(self.id)
        else:
            pass

        return olist
