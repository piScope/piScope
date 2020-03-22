from __future__ import print_function
#  Name   :py_code
#
#          base class for TreeDict which can
#          handle python code
#
#          py_code : add "run" to tree
#          py_script: provide script to tree
#          py_module: provide module (a set of fun)
#          py_data: container of data, can have its
#                   own module (derived from py_module)
#          py_model: container of model
#             run_all allows to run all script/modules
#             in sub tree
#
#  Inheritence
#          py_code -> py_script
#                  -> py_module -> py_data
#                  -> py_model
#
#  Example:
#
#           Params
#               - variables (data)
#           Genray-LH (model)
#               - G-file (gfile -< data )
#               - Input-file (namelist -< data)
#               - Connection (module)
#               - Solution (netcdf -< data)
#               - FigGenerator1 (script)
#               - FigGenerator2 (script)
#                        .
#                        .
#
#           Solver
#               - Loki Connection (module)
#               - Parameter Scan (script)
#               - Run Genray (module/script)
#
#
#
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
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
from ifigure.mto.threaded_worker import ThreadedWorker
from ifigure.widgets.canvas.file_structure import *
from ifigure.mto.treedict import TreeDict
import ifigure
import os
import time
import imp
import sys
import logging
import weakref
import shutil
import wx
import ifigure.utils.pickle_wrapper as pickle
import ifigure.utils.cbook as cbook
import ifigure.events
from ifigure.utils.edit_list import DialogEditList
from ifigure.mto.hg_support import HGSupport
from ifigure.mto.treedict import TreeDict
import ifigure.widgets.dialog as dialog
from ifigure.mto.hg_support import has_repo


class PyNamespace(TreeDict):
    _save_var = False

    def __init__(self, parent=None, src=None):
        TreeDict.__init__(self, parent=parent, src=src)

    @classmethod
    def get_namebase(self):
        return 'variables'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'variable.png')
        return [idx]

    def __del__(self):
        self._var = {}

    def get_locals(self, name):
        return self.getvar(name)

    def set_locals(self, name, var):
        self.setvar(name, var)

    def new_locals(self):
        self._var = dict()
        self._var_changed = True

    def get_shownvar(self):
        names = self.get_varlist()
        hiddennames = {"obj", "proj", "top",  "param",
                       "wdir", "app", "model", "stop",
                       "exit", "write_log", "kwargs", "args", "ans"}
        for n in hiddennames:
            if n in names:
                names.remove(n)
        for n in names:
            if n.startswith('__'):
                names.remove(n)
        return names


class AbsNamespacePointer(object):
    def __init__(self):
        return self.setvar('namespace', None)

    def get_ns(self):
        return self.eval('namespace')

    def has_ns(self):
        return self.eval('namespace') is not None

    def set_ns(self, obj):
        return self.setvar('namespace', '='+obj.get_full_path())


class AbsFileContainer(object):
    def onAddNewText(self, e=None):
        from ifigure.mto.py_file import PyText
        obj = PyText()
        iname = self.get_next_name('untitled')

        parent = self.get_app()
        ret, name = dialog.textentry(parent,
                                     "Enter a text name", "New text...", iname)
        self.add_child(name, obj)
        obj.mk_owndir()
        path = os.path.join(obj.owndir(), obj.name + '.txt')
        print(('creating file ', path))
        open(path, 'a').close()
        obj.set_path_pathmode(path)
        obj.store_mtime()

        w = None if e is None else e.GetEventObject()
        from ifigure.mto.treedict import str_td
        path = str_td(path)
        path.td = obj.get_full_path()
        ifigure.events.SendEditFileEvent(self, w=w, file=path)

        if e is not None:
            e.Skip()
        return obj

    def onAddOther(self, e=None):
        from ifigure.mto.py_file import PyFile
        file = ifigure.widgets.dialog.read(None, message="Select file")
        if file == '':
            return

        dlg = wx.MessageDialog(None,
                               'Do you want to copy file to the project?\n',
                               'Opening file',
                               wx.YES_NO)
        ret = dlg.ShowModal()
        dlg.Destroy()

        if ret == wx.ID_YES:
            if not self.has_owndir():
                self.mk_owndir()
            od = self.owndir()
            new_ofile = os.path.join(od, os.path.basename(file))
            shutil.copyfile(file, new_ofile)
            file = new_ofile

        obj = PyFile()
        base, ext = obj.split_ext(os.path.basename(file))
        name = self.get_next_name(base)
        self.add_child(name, obj)
        obj.mk_owndir()
        obj.set_path_pathmode(file)
        obj.store_mtime()
        if e is not None:
            e.Skip()
        return obj

    def set_extfolderpath(self, path):
        self.setvar('ext_folder', path)

    def add_extfolder(self, basepath):

        import ifigure.mto.py_script as py_script
        from ifigure.mto.py_extfile import make_external
        if not os.path.exists(basepath):
            raise ValueError("no such directory")
        basefolder = self.add_folder(os.path.basename(basepath))
        basefolder.set_extfolderpath(basepath)
        make_external(basefolder)
        basefolder.load_extfolder()


class PyCode(TreeDict):
    def __init__(self, parent=None, src=None):
        self._break_before = False
        self._break_after = False
        self._run_done = False
        self._manual_only = False
        super(PyCode, self).__init__(parent=parent, src=src)

    @classmethod
    def isPyCode(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'code'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'script.png')
        return [idx1]

    def is_manualonly(self):
        return self._manual_only

    def run_pycode(self, e=None):
        if self._break_before:
            self._break_before = False
            return None
        # Run script
        self.do_run()

        if self._break_after:
            self._break_after = False
            return None
        return True

    def do_run(self):
        # should be overwritten
        pass

    def run_till_this(self, e=None):
        # model overwrite run so that
        # it walks throuth its sub tree and run all
        gp = self._find_grand_py_model()
        self._break_after = True
        gp.run_pycode()

    def run_before_this(self, e=None):
        gp = self._find_grand_py_model()
        self._break_before = True
        gp.run_pycode()

    def run_children(self):
        for child in self.get_children():
            if hasattr(child, 'run_pycode'):
                child.run_pycode()

    def get_root_model(self):
        def check1(obj):
            return isinstance(obj, PyModel)

        def check2(obj):
            return not isinstance(obj, PyModel)

        x = None
        for x in self.walk_tree_up(cond=check2):
            pass
        if x is not None:
            p = x.get_parent()
        else:
            p = self
        if p is None:
            return None
        if check1(p):
            for x in p.walk_tree_up(cond=check1):
                pass
            return x
        else:
            return None

    def _find_grand_py_model(self):
        parent = self.get_parent()
        try:
            if parent.PyModel():
                return parent._find_grand_py_model()
        except Exception:
            return self

#
#   Routines for TreeViewer
#
    def tree_viewer_menu(self):
        return super(PyCode, self).tree_viewer_menu()
      # return MenuString, Handler, MenuImage
      # thie following menu is suppressed until this capability
      # is necessary...
        return [('+Run...', None, None),
                ('Preceeding Steps', self.run_before_this, None),
                ('Until This Step',  self.run_till_this, None),
                ('Only This Step', self.run_pycode, None),
                ('!', None, None),
                ('---', None, None)] + \
            super(PyCode, self).tree_viewer_menu()

# save/load
    def save_data(self, fid=None):
        pass

    def load_data(self, fid=None):
        pass


class PyData(PyCode):
    '''
    PyData is the same as PyCode but different
    default icon
    '''
    @classmethod
    def isPyData(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'data'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'data.png')
        return [idx1]

    def tree_viewer_menu(self):
      # return MenuString, Handler, MenuImage
        return super(PyCode, self).tree_viewer_menu()

    def append_data(self, d):
        for k in d:
            self.setvar(k, d[k])


class AbsModuleContainer(object):
    # routines for mto which contains modules
    def onAddModule(self, e=None):
        import ifigure.mto.py_module as py_module
        child = py_module.PyModule()
        name = self.get_next_name(child.get_namebase())
        idx = self.add_child(name, child)
        if e is not None:
            e.Skip()

    def onAddNewModule(self, e=None, module_type=None):
        '''
        new module
        copy template to owndir
        open it by editor
        '''

        import ifigure.mto.py_module as py_module
        if module_type is None:
            dlg = wx.MessageDialog(self.get_app(),
                                   "Does the new module have its own directory? \n"
                                   "Or does it share the same directory as its parent? \n",
                                   "NewModule", wx.YES_NO | wx.ICON_INFORMATION)
            ans = dlg.ShowModal()
            dlg.Destroy()
            module_type = 1 if ans == wx.ID_YES else 2

        child = py_module.PyModule()
        if module_type == 1:
            temp = os.path.join(
                ifigure.__path__[0], 'template', 'new_module.py')
            child._can_have_child = True
            child._has_private_owndir = True
        else:
            temp = os.path.join(
                ifigure.__path__[0], 'template', 'new_module_nochild.py')
            child._can_have_child = False
            child._has_private_owndir = False
        name = self.get_next_name(child.get_namebase())
        idx = self.add_child(name, child)

        child.mk_owndir()
        dest = os.path.join(child.owndir(), name+'.py')
        shutil.copyfile(temp, dest)

        print(('loading...', dest))
        child.load_module(dest)

        w = None
        if e is not None:
            w = e.GetEventObject()
        from ifigure.mto.treedict import str_td
        dest = str_td(dest)
        dest.td = child.get_full_path()
        ifigure.events.SendEditFileEvent(self, w=w, file=dest)

        if e is not None:
            e.Skip()
        return child

    def add_absmodule(self, file, *args, **kargs):
        from ifigure.mto.py_module import PyModule
        child = PyModule(*args, **kargs)
        name = os.path.basename(os.path.splitext(file)[0])
        name = self.get_next_name(name)
        idx = self.add_child(name, child)
        child.load_module(file)
        return child

    def add_std_modelmodule(self, file, *args, **kargs):
        base_mod = 'ifigure.add_on.model.module'
        mod_path = cbook.GetModuleDir(base_mod)
        file = os.path.join(mod_path, file+'.py')
        return self.add_absmodule(file, *args, **kargs)

    def onAddAbsModule(self, e, file=None):
        self.add_absmodule(file)
        print(('loading add-on', file))
        e.Skip()

    def build_module_menu(self, mod_path):
        menu = []
        for file in os.listdir(mod_path):
            if (file.endswith('.py') and file.startswith('_') is False and
                    file.startswith('.') is False):
                txt = cbook.FileNameToClass(file)

                def xxx(e, file=os.path.join(mod_path, file)):
                    self.onAddAbsModule(e, file)
                menu.append((txt, xxx, None))
        return menu


class AbsScriptContainer(object):
    # routines for mto which contains script
    def onAddScript(self, e=None):
        import ifigure.mto.py_script as py_script
        child = py_script.PyScript()
        name = self.get_next_name(child.get_namebase())
        idx = self.add_child(name, child)
        if e is not None:
            e.Skip()

    def onAddNewScript(self, e=None, name='', temp='', parent=None, dest=None):
        # new script
        # copy template to owndir
        # open it by editor
        import ifigure.mto.py_script as py_script
        if temp == '':
            temp = os.path.join(
                ifigure.__path__[0], 'template', 'script', '_blank_script.py')

        child = py_script.PyScript()
        if name == '':
            iname = '_'.join([x for x in os.path.basename(temp)[
                             :-3].split('_') if len(x) != 0])
            if parent is None:
                parent = self.get_app()
            ret, name = dialog.textentry(parent,
                                         "Enter a script name", "New Script...", iname)
            if not ret:
                return
            if self.has_child(name):
                name = self.get_next_name(name)
        idx = self.add_child(name, child)

        if dest is None:
            child.mk_owndir()
            dest = child.owndir()
        dest = os.path.join(dest, name+'.py')
        i = 1
        while os.path.exists(dest):
            name0 = name+str(i)+'.py'
            dest = os.path.join(child.owndir(), name0)
            i = i + 1
        shutil.copyfile(temp, dest)
        child.load_script(dest)

        w = None
        if e is not None:
            w = e.GetEventObject()
        from ifigure.mto.treedict import str_td
        dest = str_td(dest)
        dest.td = child.get_full_path()
        ifigure.events.SendEditFileEvent(self, w=w, file=dest)

        if e is not None:
            e.Skip()
        return child

    def onAddAbsScript(self, e, file=None, name=None):
        from ifigure.mto.py_script import PyScript
        child = PyScript()
        if name is None:
            name = self.get_next_name(child.get_namebase())
        if self.has_child(name):
            print('doing here')
            name = self.get_next_name(name)
        idx = self.add_child(name, child)
        #print('loading add-on', file)
        child.load_script(file)

    def onAddScriptFromFile(self, e):

        file = dialog.read(None, message="Select script",
                           wildcard='*.py')
        if file == '':
            e.Skip()
            return
        # this call is just import check..
        from ifigure.mto.py_script import PyScript
        tmp_child = PyScript()
        idx = self.add_child('_tempraroy_script', tmp_child)
        mode, path = tmp_child.fullpath2path(file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Import should import from somewhere outside project directory'
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return

        if not file.endswith('.py'):
            m = 'Script fils should be a .py file'
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return
        name = os.path.basename(file)[:-3]

        from ifigure.widgets.dlg_fileimportmode import DlgFileimportmode

        copy, modes, copy_org = DlgFileimportmode(self,
                                                  parent=e.GetEventObject())
        if copy:
            newfile = os.path.join(self.owndir(), os.path.basename(file))
            if not self.has_owndir():
                self.mk_owndir()
            shutil.copyfile(file, newfile)
            file = newfile
            modes = ['owndir']
        mode, path = tmp_child.fullpath2path(file, modes)
        tmp_child.destroy()
        self.onAddAbsScript(e, file=file, name=name)
        e.Skip()

    def build_script_menu(self, mod_path):
        menu = []
        for file in os.listdir(mod_path):
            if (file.endswith('.py') and file.startswith('_') is False and
                    file.startswith('.') is False):
                txt = cbook.FileNameToClass(file)

                def xxx(e, file=os.path.join(mod_path, file)):
                    self.onAddAbsScript(e, file)
                menu.append((txt, xxx, None))
        return menu

    def build_script_menu2(self, mod_path):
        menu = []
        for file in os.listdir(mod_path):
            if (file.endswith('.py') and file.startswith('_') is False and
                    file.startswith('.') is False):
                txt = cbook.FileNameToClass(file)

                def xxx(e, file=os.path.join(mod_path, file)):
                    self.onAddNewScript(e, temp=file)
                menu.append((txt, xxx, None))
        return menu

    def script_template_list(self):
        base_mod = 'ifigure.template.script'
        mod_path = cbook.GetModuleDir(base_mod)
        from ifigure.ifigure_config import usr_script_template_dir

        menu = []
        menu.append(('Blank Script...', self.onAddNewScript, None))
        menu.append(('From File...', self.onAddScriptFromFile, None))
        menu.append(('+From Template...', None, None))
        menu.extend(self.build_script_menu2(mod_path))
        menu.extend(self.build_script_menu2(usr_script_template_dir))
        menu.append(('!', None, None))

        return menu


class PyModel(PyCode, AbsModuleContainer, AbsScriptContainer,
              AbsFileContainer, ThreadedWorker, HGSupport,
              AbsNamespacePointer):
    # PyModel is a top node of code tree
    # script must be empty other than
    # loading global variable to its
    # attribute
    def __init__(self, parent=None, src=None):
        self._run_script = ''
        self._gui_script = ''
        self._finish_script = ''
        self._cleanup_script = ''

        super(PyModel, self).__init__(parent=parent, src=src)
        HGSupport.__init__(self)
        ThreadedWorker.__init__(self)
        AbsNamespacePointer.__init__(self)
        if src is None:
            param = PyParam()
            self.add_child('param', param)

    @classmethod
    def isPyModel(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'model'

    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'model.png')
        idx2 = cbook.LoadImageFile(path, 'model_hg.png')
        return [idx1, idx2]

    def classimage(self):
        if PyModel._image_load_done is False:
            PyModel._image_id = self.load_classimage()
            PyModel._image_load_done = True
        if has_repo(self):
            return PyModel._image_id[1]
        else:
            return PyModel._image_id[0]

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_F9:
            return self.onRun
        return None

    def Clean(self, event=None):
        self.do_clean()

    def do_gui(self):
        s, f, c, g = self.eval_script_location()
        if g is not None:
            g.do_run()

    def do_finish(self, *args):
        '''
        script to merge solution to PySol
        args = index, sol for parametric 
        '''
        s, f, c, g = self.eval_script_location()
        if f is not None:
            f.do_run(*args)

    def do_run(self):
        s, f, c, g = self.eval_script_location()
        if s is not None:
            if self._run_verbose:
                print(('Entering :', self.name))
                print(('   Running ', s.get_full_path()))
            s.do_run()

    def do_clean(self):
        s, f, c, g = self.eval_script_location()
        if c is not None:
            c.do_run()
        for name, treeobj in self.get_children():
            if isinstance(treeobj, PyModel):
                print(("Entering : ", name))
                treeobj.do_clean()

    def walk_model(self):
        for name, child in self.get_children():
            if isinstance(child, PyModel):
                yield child

    def tree_viewer_menu(self):
        from ifigure.mto.hg_support import has_hg
      # return MenuString, Handler, MenuImage
        s, f, c, g = self.eval_script_location()
        ss = '-' if s is None else ''
        ff = '-' if f is None else ''
        cc = '-' if c is None else ''
        gg = '-' if g is None else ''
        ll = '-' if self.has_ns() else ''

        menu = [('+Model', None,  None),
                (ss+'Run Model (F9)',   self.onRun, None),
                (gg+'Open GUI',    self.onGUI, None),
                (cc+'Run Clean',   self.onClean, None),
                ('!',  None, None),
                ('+Add...', None, None),
                ('Book',  self.onAddBook, None),
                ('Text',  self.onAddNewText, None),
                ('Data',  self.onAddData, None),
                ('Model', self.onAddModel, None),
                (ll+'Variables', self.onAddNewNamespace, None),
                ('+Script...',  None, None)] + \
            self.script_template_list() + \
            [('!',  None, None),
             ('+Module...',  None, None)] + \
            self.module_addon_list() + \
            [('!',  None, None),
                ('Other Files...', self.onAddOther, None),
                ('!',  None, None),
                ('Setting...', self.onSetting, None),
                ('---', None, None)]
        menu = self.add_hg_menu(menu)
        menu = menu + super(PyCode, self).tree_viewer_menu()
        return menu

    def onRun(self, e):
        self.Run(e)
        e.Skip()

    def onClean(self, e):
        self.Clean(e)
        e.Skip()

    def onGUI(self, e):
        self.do_gui()
        e.Skip()

    def eval_setting_str(self, txt):
        if len(txt) == 0:
            return None
        if txt[0] == '=':
            # expression is stored as it is
            try:
                root = self.get_root_parent()
                ldict = locals().copy()              
                exec(root.name + '= self.get_root_parent()', globals(),ldict)
                exec('ret'+txt, globals(),ldict)
                ret = ldict['ret']                
            except:
                import traceback
                traceback.print_exc()
                ret = None
        else:
            if txt.startswith('.'):
                txt = self.get_full_path()+txt
            try:
                root = self.get_root_parent()
                ldict = locals().copy()
                exec(root.name + '= self.get_root_parent()', globals(),ldict)
                exec('ret='+txt, globals(),ldict)
                ret = ldict['ret']
            except:
                import traceback
                traceback.print_exc()
                ret = None
        return ret

    def eval_script_location(self):
        return (self.eval_setting_str(self._run_script),
                self.eval_setting_str(self._finish_script),
                self.eval_setting_str(self._cleanup_script),
                self.eval_setting_str(self._gui_script))

    def onProjTreeActivate(self, e):
        #        pass
        self.onSetting(e)

    def onSetting(self, e):
        id = e.GetEventObject()
        app = id.GetTopLevelParent()

        r = self._run_script
        f = self._finish_script
        c = self._cleanup_script
        g = self._gui_script
        w = self._run_after

        list = [["", "Model Setting", 2],
                ["Run Script ", r, 0],
                ["GUI Script ", g, 0],
                ["Finish Script", f, 0],
                ["Cleanup Script", c, 0],
                ["Run after...", w, 0],
                [None, "(proj.model.script or .script)", 2],
                ["Threading", self._background, 3,
                 {"text": 'run this model in a separate thread'}],
                ["Run mode", self._run_mode, 3,
                 {"text": 'run a top level model script alone'}],
                ["Verbose", self._run_verbose, 3,
                 {"text": 'generate extra debug output'}]]

        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')

    def setSetting(self, value):
        self._run_script = str(value[1])
        self._gui_script = str(value[2])
        self._finish_script = str(value[3])
        self._cleanup_script = str(value[4])
        self._run_after = str(value[5])
        self._background = value[7]
        self._run_mode = value[8]
        self._run_verbose = value[9]

    def set_guiscript(self, value):
        self._gui_script = value

    def set_runscript(self, value):
        self._run_script = value

    def set_finishscript(self, value):
        self._finish_script = value

    def set_cleanupscript(self, value):
        self._cleanup_script = value

    def get_guiscript(self):
        return self.eval_setting_str(self._gui_script)

    def get_runscript(self):
        return self.eval_setting_str(self._run_script)

    def get_finishscript(self):
        return self.eval_setting_str(self._finish_script)

    def get_cleanupscript(self):
        return self.eval_setting_str(self._cleanup_script)

    def onAddBook(self, e):
        from ifigure.mto.fig_book import FigBook
        book = FigBook()
        name = self.get_next_name('book')
        self.add_child(name, book)
        e.Skip()  # call update project tree widget

    def onAddNewNamespace(self, e=None):
        ns = PyNamespace()
        if self.has_child('variables'):
            name = self.get_next_name('variables')
        else:
            name = 'variables'
        self.add_child(name, ns)
        self.set_ns(ns)
        if e is not None:
            e.Skip()  # call update project tree widget

    def onAddData(self, e):
        id = e.GetEventObject()
        app = id.GetTopLevelParent()
        ret, name = dialog.textentry(app,
                                     "Enter a data name",
                                     "New Data...", "data")
        if not ret:
            return
        data = PyData()
        name = self.get_next_name(name)
        self.add_child(name, data)
        e.Skip()  # call update project tree widget

    def onAddModel(self, e):
        id = e.GetEventObject()
        app = id.GetTopLevelParent()
        ret, new_name = dialog.textentry(app,
                                         "Enter the name of new model",
                                         "Add Model", "")
        if ret:
            child = PyModel()
            imodel = self.add_child(new_name, child)
            child.onAddFolder(name='scripts')
        e.Skip()  # call update project tree widget

    def onAddExtFolder(self, evt):
        from ifigure.widgets.dialog import readdir
        dir = readdir(parent=evt.GetEventObject(),
                      message='Select external folder to import')
        if dir == '':
            return
        self.add_extfolder(dir)
        if evt is not None:
            evt.Skip()

    def add_folder(self, name):
        return self.add_childobject(PyFolder, name)

    def add_book(self, name):
        from ifigure.mto.fig_book import FigBook
        return self.add_childobject(FigBook, name)

    def add_data(self, name):
        return self.add_childobject(PyData, name)

    def add_model(self, name, cls=None):
        if cls is None:
            cls = PyModel
        return self.add_childobject(cls, name)

    def add_file(self, name):
        from ifigure.mto.py_file import PyFile
        return self.add_childobject(PyFile, name)

    def add_text(self, name):
        from ifigure.mto.py_file import PyText
        return self.add_childobject(PyText, name)

    def module_addon_list(self):
        base_mod = 'ifigure.add_on.model.module'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_module_menu(mod_path)
        menu.append(('New Module...', self.onAddNewModule, None))
        return menu

    def script_addon_list(self):
        base_mod = 'ifigure.add_on.model.script'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_script_menu(mod_path)
        menu.append(('New Script...', self.onAddNewScript, None))
        return menu

    def save_data2(self, data=None):
        if data is None:
            data = {}
        h2 = {"r": self._run_script,
              "f": self._finish_script,
              "c": self._cleanup_script,
              "g": self._gui_script,
              "background": self._background,
              "run_after": self._run_after,
              "run_mode": self._run_mode,
              "run_verbose": self._run_verbose}
        data['PyModel'] = (1, h2)
        return super(PyModel, self).save_data2(data)

    def load_data2(self, data):
        h2 = data['PyModel'][1]
        if "r" in h2:
            self._run_script = h2["r"]
        if "c" in h2:
            self._cleanup_script = h2["c"]
        if "f" in h2:
            self._finish_script = h2["f"]
        if "g" in h2:
            self._gui_script = h2["g"]
        if "background" in h2:
            self._background = h2["background"]
        if "run_after" in h2:
            self._run_after = str(h2["run_after"])
        if "run_mode" in h2:
            self._run_mode = h2["run_mode"]
        if "run_verbose" in h2:
            self._run_verbose = h2["run_verbose"]
        return super(PyModel, self).load_data2(data)


class PyParam(PyCode):
    '''
    PyParams is a object which provide an convenient way to
    specify a parameter sets. Each model can have one PyParam
    and evaluation of PyParam can be overwritten.


    '''

    def __init__(self, parent=None, src=None):
        super(PyParam, self).__init__(parent=None, src=None)
        self._name_readonly = True
        self._manual_only = True
        self._local_vars = []

    @classmethod
    def isPyParam(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'param'

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'pi.png')
        return [idx1]

    def run_pycode(self):
        # PyParam has nothing to run
        pass

    def tree_viewer_menu(self):
      # return MenuString, Handler, MenuImage
        list = super(PyCode, self).tree_viewer_menu()
        for i in range(len(list)):
            if list[i][0] == 'Delete':
                list[i] = ('-Delete', None, None)
                break
        for i in range(len(list)):
            if list[i][0] == 'Suppress':
                list[i] = ('-Suppress', None, None)
                break
        for i in range(len(list)):
            if list[i][0] == 'Unsuppress':
                list[i] = ('-Unsuppress', None, None)
                break

        return [('Print All Variables', self.onPrint, None),
                ('Export to Main', self.onExport, None),
                ('Import from Main', self.onImport, None),
                ('---', None, None)] + \
            list

    def eval_all_keys(self, path=False):
        d = {}  # dict to make unique set....
        if self.get_parent() is None:
            '''
            safty if paranet is None
            '''
            if path:
                return d
            else:
                return list(d.keys())

        for item in self.get_parent().walk_tree_up():
            for name, child in item.get_children():
                if isinstance(child, PyParam):
                    for key in child.getvar():
                        if key not in d:
                            d[key] = [(child.get_full_path(), child)]
                        else:
                            d[key].append((child.get_full_path(), child))
                    break
        try:
            item = self.get_root_parent().setting.parameters
            if item is self:
                if path:
                    return d
                else:
                    return list(d.keys())

        except:
            if path:
                return d
            else:
                return list(d.keys())

        for key in item.getvar():
            if key not in d:
                d[key] = (item.get_full_path(), item)
            else:
                d[key].append((item.get_full_path(), item))
        if path:
            return d
        return list(d.keys())

    def set(self, name, var):
        d = self.eval_all_keys(path=True)
        if not name in d:
            target = self
        else:
            for x in d[name]:
                if name in x[1]._local_vars:
                    break
            target = x[1]
#            target = d[name][-1][1]
        TreeDict.setvar(target, name,  var)

    def get(self, name):
        return self.eval(name)

    def eval(self, name):
        '''
        params._var can be overwritten by upper level
        '''
        if not name in self._var:
            print(('Warning : PyParam::get: Variable is not set at this PyParam,',
                   name, ':', self.get_full_path()))

        d = self.eval_all_keys(path=True)
        if not name in d:
            return None
        for path, obj in d[name]:
            if name in obj._local_vars:
                break
        val = TreeDict.eval(obj, name)
        return val

    def onPrint(self, e):
        d = self.eval_all_keys(path=True)
        for key in d:
            print((key, 'defined as...'))
            for x in d[key]:
                val = x[1]._var[key]
                if isinstance(val, str):
                    if val.startswith('='):
                        val = eval(val[1:])

                print(('   ', str(val), ' at ',  x[1].get_full_path()))

    def onExport(self, e):
        d = {}
        for key in self.eval_all_keys():
            d[key] = self.eval(key)
        list = [["", "Enter Variable Name to Export", 2],
                ["Name", "var", 0]]
        flag, value = DialogEditList(list)
        if flag:
            self.write2shell(d,  value[1])

    def onImport(self, e):
        list = [["", "Enter Variable Name to Import", 2],
                ["Name", "var", 0]]
        flag, value = DialogEditList(list)
        if flag:
            var = cbook.ReadFromMain(value[1])
            for key in var:
                self.setvar(key, var[key])

    def onDelete(self, e=None):
        # prohibit delete pyparam interactively
        pass

    def save_data2(self, data=None):
        if data is None:
            data = {}
        h2 = {"_local_vars": self._local_vars, }
        data['PyParam'] = (1, h2)
        return super(PyParam, self).save_data2(data)

    def load_data2(self, data):
        if not 'PyParam' in data:
            return
        h2 = data['PyParam'][1]
        for key in h2:
            setattr(self, key, h2[key])
        return super(PyParam, self).load_data2(data)

    def set_var_local(self, name, flag=True):
        if flag:
            if not name in self._local_vars:
                self._local_vars.append(name)
        else:
            if name in self._local_vars:
                del self._local_vars[name]

    def delvar(self, name):
        PyCode.delvar(self, name)
        if name in self._local_vars:
            self._local_vars.remove(name)


class PyFolder(TreeDict, AbsModuleContainer, AbsScriptContainer,
               AbsFileContainer, HGSupport):
    def __init__(self, *args, **kargs):
        super(PyFolder, self).__init__(*args, **kargs)
        HGSupport.__init__(self)

    @classmethod
    def isPyFolder(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'folder'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'folder.png')
        idx2 = cbook.LoadImageFile(path, 'folder_hg.png')
        idx3 = cbook.LoadImageFile(path, 'folder_ext.png')
        return [idx1, idx2, idx3]

    def classimage(self):
        if PyFolder._image_load_done is False:
            PyFolder._image_id = self.load_classimage()
            PyFolder._image_load_done = True
        if has_repo(self):
            return PyFolder._image_id[1]
        elif self.getvar('ext_folder') is not None:
            return PyFolder._image_id[2]
        else:
            return PyFolder._image_id[0]

    def tree_viewer_menu(self):
        from ifigure.mto.hg_support import has_hg
        # return MenuString, Handler, MenuImage
        menu = [
            ('Add Text',   self.onAddNewText, None),
            ('+Add Script...',  None, None)] + \
            self.script_template_list() + \
            [('!',  None, None),
             ('Other File...',   self.onAddOther, None),
             ('---', None, None)]
        menu = self.add_hg_menu(menu)
        menu = menu + super(PyFolder, self).tree_viewer_menu()
        return menu

    def add_folder(self, name):
        return self.add_childobject(PyFolder, name)

    def add_book(self, name):
        from ifigure.mto.fig_book import FigBook
        return self.add_childobject(FigBook, name)

    def add_data(self, name):
        return self.add_childobject(PyData, name)

    def add_file(self, name):
        from ifigure.mto.py_file import PyFile
        return self.add_childobject(PyFile, name)

    def add_text(self, name):
        from ifigure.mto.py_file import PyText
        return self.add_childobject(PyText, name)

    def onAddNewScript(self, *args, **kwargs):
        if self.get_extfolderpath() is None:
            super(PyFolder, self).onAddNewScript(*args, **kwargs)
        else:
            kwargs['dest'] = self.get_extfolderpath()
            super(PyFolder, self).onAddNewScript(*args, **kwargs)

    def onAddExtFolder(self, evt):
        from ifigure.widgets.dialog import readdir
        dir = readdir(parent=evt.GetEventObject(),
                      message='Select library directory to import')
        if dir == '':
            return
        self.add_extfolder(dir)
        if evt is not None:
            evt.Skip()

    def load_script_folder(self, basepath, skip_underscore=False):
        from ifigure.mto.py_script import PyScript
        warning = []
        for dirpath, dirname, filenames in os.walk(basepath):
            if '.' in os.path.basename(dirpath):
                continue
            dirname = [x for x in dirname if not '.'in x]
            relpath = os.path.relpath(dirpath, basepath)
            if relpath == '.':
                relpath = ''
            p = self

            tmp = relpath.split(os.sep)
            if any(['.' in x for x in tmp]):
                continue
            for name in relpath.split(os.sep):
                if name == '':
                    continue
                p = p.get_child(name=name)

            for name in dirname:
                obj = PyFolder()
                p.add_child(name, obj, warning=warning)
            for f in filenames:
                fpath = os.path.join(dirpath, f)

                if fpath.endswith('.py'):
                    newname = str(os.path.basename(fpath).split('.')[0])
                    if skip_underscore and newname.startswith('_'):
                        continue
                    child = PyScript()
                    idx = p.add_child(newname, child, warning=warning)
                    child.import_script(fpath)
#                    script.onImportScriptFile(file = fpath)
        for x in warning:
            if len(x) != 0:
                print(x)


class PySol(TreeDict):
    """
    PySol is a folder to store solution
    """

    def __init__(self, *args, **kargs):
        self._lock = None
        TreeDict.__init__(self, *args, **kargs)

    @classmethod
    def isPySol(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'solution'

    @classmethod
    def can_have_child(self, child=None):
        return True

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'data.png')
        return [idx1]

    def tree_viewer_menu(self):
        has_pyparam = False
        for name, child in self.get_children():
            if isinstance(child, PyParam):
                has_pyparam = True
                break

        # return MenuString, Handler, MenuImage
        if has_pyparam:
            return [('-Add Parameters', self.onAddParam, None), ] + \
                super(PySol, self).tree_viewer_menu()
        else:
            return [('Add Parameters', self.onAddParam, None), ] + \
                super(PySol, self).tree_viewer_menu()

    def onAddParam(self, evt):
        obj = PyParam()
        name = 'parameters'
        self.add_child(name, obj)
        evt.Skip()  # call update project tree widget

    def aquire_lock(self, *args, **kargs):
        import threading
        if self._lock is None:
            self._lock = threading.Lock()
        self._lock.acquire(*args, **kargs)

    def release_lock(self):
        self._lock.release()
