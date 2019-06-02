from __future__ import print_function
import ifigure.utils.cbook as cbook
import ifigure
import os
import sys
import weakref
import logging
import threading
import ifigure.utils.pickle_wrapper as pickle
from ifigure.mto.treedict import TopTreeDict, TreeDict
from ifigure.mto.py_code import PyParam, AbsModuleContainer, AbsScriptContainer, AbsFileContainer
from ifigure.mto.py_code import PyModel
from ifigure.mto.py_solver import PySolver
from ifigure.mto.py_code import PySol
from ifigure.mto.fig_book import FigBook

import ifigure.widgets.dialog as dialog

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('ProjectTop')

lock = threading.Lock()


class PySetting(TreeDict, AbsModuleContainer, AbsScriptContainer):
    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'setting.png')
        return [idx]

    @classmethod
    def get_namebase(self):
        return 'setting'

    @classmethod
    def isPySetting(self):
        return True

    def tree_viewer_menu(self):
        from ifigure.mto.py_code import PyParam
        has_pyparam = False
        for name, child in self.get_children():
            if isinstance(child, PyParam):
                has_pyparam = True
                break
        if has_pyparam:
            v = [('-Add Parameters', self.onAddParam, None), ]
        else:
            v = [('Add Parameters', self.onAddParam, None), ]
     # return MenuString, Handler, MenuImage
        return v + [('+Add Module',  None, None)] + \
            self.module_addon_list() + \
            [('!',  None, None),
             ('+Add Script',  None, None)] + \
            self.script_addon_list() + \
            [('!',  None, None),
             ('---',  None, None)] +     \
            super(PySetting, self).tree_viewer_menu()

    def module_addon_list(self):
        base_mod = 'ifigure.add_on.setting.module'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_module_menu(mod_path)
        menu.append(('New Module...', self.onAddNewModule, None))
        return menu

    def script_addon_list(self):
        base_mod = 'ifigure.add_on.setting.script'
        mod_path = cbook.GetModuleDir(base_mod)
        menu = self.build_module_menu(mod_path)
        menu.append(('New Script...', self.onAddNewScript, None))
        return menu

    def onAddParam(self, evt):
        obj = PyParam()
        name = 'parameters'
        self.add_child(name, obj)
        evt.Skip()


class ProjectTop(TopTreeDict, AbsScriptContainer, AbsFileContainer):
    '''
    root object of treedict (data tree object)
    '''

    def __init__(self, src=None):
        #
        #  variable to specify "present" subtrees.
        #
        self._pbook = None
        self._pmodel = None
        self._psetting = None
        self._psolver = None
        self._psol = None
        self._saved = False

        super(ProjectTop, self).__init__(src=src)
        self._name = 'proj'

        if src is None:
            setting = PySetting()
            self.add_child('setting', setting)
            param = PyParam()
            setting.add_child('parameters', param)

    def set_saved(self, value):
        self._saved = value
#         import traceback
#         traceback.print_stack()

    def get_saved(self):
        return self._saved

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'sun.png')
        return [idx]

    def write_log(self, *args):
        lock.acquire()
        name = os.path.join(self.eval("wdir"), 'log')
        fid = open(name, 'a+')
        import datetime
        import threading
        txt1 = '::'.join([datetime.datetime.now().strftime(
            "%Y_%m_%d_%H_%M"), threading.current_thread().name]) + '\n'
        fid.write(txt1)
        fid.write('\n'.join(['   '+str(x) for x in args]))
        fid.write('\n')
        fid.close()
        lock.release()

    def clear_log(self):
        name = os.path.join(self.eval("wdir"), 'log')
        fid = open(name, 'w')
        fid.write('')
        fid.close()

    def show_log(self):
        name = os.path.join(self.eval("wdir"), 'log')
        fid = open(name, 'r')
        print(''.join(fid.readlines()))
        fid.close()

    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        from ifigure.mto.hg_support import has_hg

        menu = [
            ('+Add...', None, None),
            ('Book',   self.onAddBook, None),
            ('Text',   self.onAddNewText, None),
            ('+Script...',  None, None), ] + \
            self.script_template_list() + \
            [('!',  None, None),
             ('+Modeling...', None, None),
             ('Setting', self.onAddSetting, None),
             ('Model', self.onAddModel, None),
             ('Solver',   self.onAddSolver, None),
             ('Solution',   self.onAddSol, None),
             ('!', None, None),
             ('Other File...',   self.onAddOther, None),
             ('!', None, None),
             ('Setting...',   self.onSetting, None),
             ('---',   None, None), ]

        if has_hg:
            menu.append(('Check Package Updates',
                         self.onCheckPackageUpdate, None))
        menu.append(('+Import Subtree', None, None))
        mm = [('From File...', self.onLoadSubTree, None), ]
        if has_hg:
            mm.append(('From Repository...', self.onLoadSubTreeHG,
                       None))
        if hasattr(self, 'onAddExtFolder'):
            mm.append(('From Folder...', self.onAddExtFolder, None))
        menu.extend(mm)
        menu.append(('!', None, None))
        menu.extend([('Export All Subtree', self.onExportAllSubTree, None),
                     ('New Folder...', self.onAddFolder, None)])

        return menu

    @classmethod
    def isProjectTop(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'proj'

    def destroy(self, clean_owndir=True):
        self._pbook = None
        self._pmodel = None
        self._psetting = None
        self._psolver = None
        self._psol = None
        super(ProjectTop, self).destroy(clean_owndir=clean_owndir)

    def onCheckPackageUpdate(self, e):
        from ifigure.mto.hg_support import hg_check_all_incoming_outgoing, hg_verify_all_repo
        broken_repo = hg_verify_all_repo(self)
        if len(broken_repo) != 0:
            txt = ['Some repo are broken\n'] + \
                '\n'.join(['  ' + str(o) for o in broken_repo])
            ret = dialog.message(e.GetEventObject(), txt, 'Broken Repo', 0)
            return
        updated_obj, newer_obj, both_obj = hg_check_all_incoming_outgoing(self)
        #app = wx.GetApp().TopWindow
        # app.proj_tree_viewer.update_widget()#_request2()

        labels = ['pull  ' + obj.get_full_path() + '(local:'+str(rev) + ' <<-- repo' + str(rev2) + ')' for obj, l, rev, rev2 in updated_obj] + \
            ['push ' + obj.get_full_path() + '(local:'+str(rev) + ' -->> repo: ' +
             str(rev2) + ')' for obj, l, rev, rev2 in newer_obj]
        if len(labels) == 0:
            ret = dialog.message(e.GetEventObject(),
                                 'No update is found', 'No Update', 0)
            return
        # print labels, e.GetEventObject()
        from ifigure.utils.checkbox_panel import checkbox_panel
        value = checkbox_panel(e.GetEventObject(), col=1, labels=labels,
                               values=[True]*len(updated_obj) +
                               [False]*len(newer_obj),
                               message='Select packages to update',
                               title='Package updage', blabel='Update')

        if value is None:
            return
        from ifigure.mto.hg_support import update_to_latest
        for i, v in enumerate(value):
            label, flag = v
            if flag:
                if i < len(updated_obj):
                    new_rev, new_obj = update_to_latest(updated_obj[i][0])
                    dprint1(str(new_obj)+'was updated to ' + str(new_rev))
                else:
                    new_rev, url = update_to_latest(
                        newer_obj[i-len(updated_obj)][0], rev=True)
                    dprint1('repo('+url+') was updated to ' + str(new_rev))
        # dprint1('skipping')
        e.Skip()  # this will update widget

    def onSetting(self, e):
        id = e.GetEventObject()
        app = id.GetTopLevelParent()

        setting = ''
        model = ''
        solver = ''
        sol = ''
        book = ''

        if cbook.ProxyAlive(self._psetting):
            setting = self._psetting.get_full_path()
        if cbook.ProxyAlive(self._pmodel):
            model = self._pmodel.get_full_path()
        if cbook.ProxyAlive(self._psolver):
            solver = self._psolver.get_full_path()
        if cbook.ProxyAlive(self._psol):
            sol = self._psol.get_full_path()
        if cbook.ProxyAlive(self._pbook):
            book = self._pbook.get_full_path()

        list = [["", "Project Setting", 2],
                ["Setting", setting, 0],
                ["Model", model, 0],
                ["Solver", solver, 0],
                ["Solution", sol, 0],
                ["Book",  book, 0]]

        app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')

    def setSetting(self, value):
        logging.basicConfig(level=logging.DEBUG)

        root = self.get_root_parent()
        exec(root._name + ' = root')
        if len(value[1]) != 0:
            try:
                b = eval(value[1])
                b.isPySetting()
                self._psetting = weakref.proxy(b)
            except Exception:
                self._psetting = None
                logging.exception("")
        if len(value[2]) != 0:
            try:
                b = eval(value[2])
                b.isPyModel()
                self._pmodel = weakref.proxy(b)
            except Exception:
                self._pmodel = None
                logging.exception("")
        if len(value[3]) != 0:
            try:
                b = eval(value[3])
                b.isPySolver()
                self._psolver = weakref.proxy(b)
            except Exception:
                self._psolver = None
                logging.exception("")
        if len(value[4]) != 0:
            try:
                b = eval(value[4])
                b.isPySol()
                self._psol = weakref.proxy(b)
            except Exception:
                self._psol = None
                logging.exception("")
        if len(value[5]) != 0:
            try:
                b = eval(value[5])
                b.isFigBook()
                self._pbook = weakref.proxy(b)
            except Exception:
                self._pbook = None
                logging.exception("")

    def set_psetting(self, a):
        self._psetting = None
        if a is not None:
            self._psetting = weakref.proxy(a)

    def set_pmodel(self, a):
        self._pmodel = None
        if a is not None:
            self._pmodel = weakref.proxy(a)

    def set_pbook(self, a):
        self._pbook = None
        if a is not None:
            self._pbook = weakref.proxy(a)

    def set_psol(self, a):
        self._psol = None
        if a is not None:
            self._psol = weakref.proxy(a)

    def set_psolver(self, a):
        self._psolver = None
        if a is not None:
            self._psolver = weakref.proxy(a)

    def num_book(self):
        return self._countSomething('isFigBook')

    def num_model(self):
        return self._countSomething('isPyModel')

    def num_solver(self):
        return self._countSomething('isPySolver')

    def num_sol(self):
        return self._countSomething('isPySol')

    def num_setting(self):
        return self._countSomething('isPySetting')

    @property
    def psetting(self):
        return self._psetting

    @property
    def pmodel(self):
        return self._pmodel

    @property
    def pbook(self):
        return self._pbook

    @property
    def psolver(self):
        return self._psolver

    @property
    def psol(self):
        return self._psol

    #
    #  Pulldown Menu
    #
    def onAddNewScript(self, e=None, **kargs):
        child = AbsScriptContainer.onAddNewScript(self, e, **kargs)
        if child is not None:
            child._simplemenu = True
        return child

    def onAddSetting(self, e=None):
        setting = PySetting()
        self._onAddSomething(setting,
                             ['isPySolver', 'isFigBook', 'isPyModel', 'isPySol'])
        if not cbook.ProxyAlive(self._psetting):
            self._psetting = weakref.proxy(setting)
        if e is not None:
            e.Skip()
        return setting

    def onAddModel(self, e=None):
        model = PyModel()
        basename = model.get_namebase()
        name = self.get_next_name(basename)
        if e is not None:
            id = e.GetEventObject()
            app = id.GetTopLevelParent()
            ret, new_name = dialog.textentry(app,
                                             "Enter the name of new model",
                                             "Add Model", name)
            if not ret:
                return
        else:
            new_name = name
        self._onAddSomething(model, ['isPySolver', 'isFigBook', 'isPySol'],
                             name=new_name)
        if not cbook.ProxyAlive(self._pmodel):
            self._pmodel = weakref.proxy(model)
        if e is not None:
            e.Skip()
        return model

    def onAddSolver(self, e=None):
        solver = PySolver()
        self._onAddSomething(solver, ['isFigBook', 'isPySol'])
        if not cbook.ProxyAlive(self._psolver):
            self._psolver = weakref.proxy(solver)
        if e is not None:
            e.Skip()
        return solver

    def onAddSol(self, e=None):
        sol = PySol()
        self._onAddSomething(sol, ['isFigBook'])
        if not cbook.ProxyAlive(self._psol):
            self._psol = weakref.proxy(sol)
        if e is not None:
            e.Skip()
        return sol

    def onAddBook(self, e=None, basename=None):
        book = FigBook()
        self._onAddSomething(book, basename=basename)
        if not cbook.ProxyAlive(self._pbook):
            self._pbook = weakref.proxy(book)
        if e is not None:
            e.Skip()
        return book

    def onAddExtFolder(self, evt):
        from ifigure.widgets.dialog import readdir
        dir = readdir(parent=evt.GetEventObject(),
                      message='Select external folder to import')
        if dir == '':
            return
        self.add_extfolder(dir)
        if evt is not None:
            evt.Skip()

    def _onAddSomething(self, item, methods=None, basename=None, name=None):
        if name is None:
            if basename is None:
                basename = item.get_namebase()
            name = self.get_next_name(basename)
        idx = self.add_child(name, item)
        if methods is None:
            return

        idx2 = 0
        for name, child in self.get_children():
            for m in methods:
                if getattr(child, m, None) is not None:
                    self.move_child(idx, idx2)
                    return
            idx2 = idx2+1

    def _countSomething(self, method=None):
        c = 0
        for name, child in self.get_children():
            if getattr(child, method, None) is not None:
                c = c+1
        return c

    def add_folder(self, name):
        from ifigure.mto.py_code import PyFolder
        return self.add_childobject(PyFolder, name)

    def add_book(self, name):
        from ifigure.mto.fig_book import FigBook
        return self.add_childobject(FigBook, name)

    def add_script(self, name):
        from ifigure.mto.py_script import PyScript
        return self.add_childobject(PyScript, name)

    def add_data(self, name):
        from ifigure.mto.py_code import PyData
        return self.add_childobject(PyData, name)

    def add_model(self, name):
        '''
        add a new model
        '''
        from ifigure.mto.py_code import PyModel
        return self.add_childobject(PyModel, name)

    def add_file(self, name):
        from ifigure.mto.py_file import PyFile
        return self.add_childobject(PyFile, name)

    def add_text(self, name):
        from ifigure.mto.py_file import PyText
        return self.add_childobject(PyText, name)

    def add_solver(self, name):
        return self.add_childobject(PySolver, name)

    def reorder_top_level(self):
        d = {'book': [],
             'model': [],
             'solver': [],
             'sol': [],
             'setting': [],
             'others': []}
        for name, child in self.get_children():
            if isinstance(child, PySetting):
                d['setting'].append(child)
            elif isinstance(child, FigBook):
                d['book'].append(child)
            elif isinstance(child, PyModel):
                d['model'].append(child)
            elif isinstance(child, PySol):
                d['sol'].append(child)
            elif isinstance(child, PySolver):
                d['solver'].append(child)
            else:
                d['others'].append(child)
        self._d = d['setting']+d['model'] + \
            d['solver']+d['sol']+d['book']+d['others']

    def load_subtree(self, filename, keep_zorder=True, message=None,
                     compress=False, usetar=True):

        ret = super(ProjectTop, self).load_subtree(filename,
                                                   keep_zorder=keep_zorder,
                                                   message=message,
                                                   compress=compress,
                                                   usetar=usetar)
        self.reorder_top_level()
        return ret

    def save_data(self, fid):
        h2 = {}
        if cbook.ProxyAlive(self._psetting):
            h2["isetting"] = self._psetting.id
        if cbook.ProxyAlive(self._pmodel):
            h2["imodel"] = self._pmodel.id
        if cbook.ProxyAlive(self._psolver):
            h2["isolver"] = self._psolver.id
        if cbook.ProxyAlive(self._pbook):
            h2["ibook"] = self._pbook.id
        if cbook.ProxyAlive(self._psol):
            h2["isol"] = self._psol.id
        pickle.dump(h2, fid)

    def load_data(self, fid):
        h2 = pickle.load(fid)
        self.setvar("load_property", h2)

    def save_data2(self, data):
        def get_right_path(self, obj):
            if self.isdescendant(obj):
                return self.get_td_path(obj)
            else:
                return self.get_td_path(obj, True)

        h2 = {}
#         if cbook.ProxyAlive(self._psetting): h2["isetting"]=self._psetting.id
#         if cbook.ProxyAlive(self._pmodel): h2["imodel"]=self._pmodel.id
#         if cbook.ProxyAlive(self._psolver): h2["isolver"]=self._psolver.id
#         if cbook.ProxyAlive(self._pbook): h2["ibook"]=self._pbook.id
#         if cbook.ProxyAlive(self._psol): h2["isol"]=self._psol.id
        if cbook.ProxyAlive(self._psetting):
            h2["isetting_path"] = get_right_path(self, self._psetting)
        if cbook.ProxyAlive(self._pmodel):
            h2["imodel_path"] = get_right_path(self, self._pmodel)
        if cbook.ProxyAlive(self._psolver):
            h2["isolver_path"] = get_right_path(self, self._psolver)
        if cbook.ProxyAlive(self._pbook):
            h2["ibook_path"] = get_right_path(self, self._pbook)
        if cbook.ProxyAlive(self._psol):
            h2["isol_path"] = get_right_path(self, self._psol)
        data['ProjectTop'] = (1, h2)
        return data

    def load_data2(self, data):
        self.setvar("load_property", data['ProjectTop'][1])

    def onExportAllSubTree(self, e):
        from ifigure.mto.py_code import PyModel

        for child in self.walk_tree():
            #             if isinstance(child, PyModel):
            if (child.hasvar('subtree_path') and
                    os.path.exists(child.getvar('subtree_path'))):
                path = child.getvar('subtree_path')
                print('exporting subtree to '+path)
                child.save_subtree(path)

    def init_after_load(self, olist, nlist):
        #
        #  init_after_load is initialization
        #  after loading entire tree
        #
        #  note: self.get_child would fail
        #        if it is issued in load_data,
        #        since children are not yet
        #        loaded.
        #
        h2 = self.getvar("load_property")

        if "isetting" in h2:
            oid = h2["isetting"]
            self._psetting = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "imodel" in h2:
            oid = h2["imodel"]
            self._pmodel = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "isolver" in h2:
            oid = h2["isolver"]
            self._psolver = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "ibook" in h2:
            oid = h2["ibook"]
            self._pbook = self.resolve_olist_nlist_map(oid, olist, nlist)
        if "isol" in h2:
            oid = h2["isol"]
            self._psol = self.resolve_olist_nlist_map(oid, olist, nlist)

        if "isetting_path" in h2:
            self._psetting = self.resolve_td_path(h2["isetting_path"])
        if "imodel_path" in h2:
            self._pmodel = self.resolve_td_path(h2["imodel_path"])
        if "isolver_path" in h2:
            self._psolver = self.resolve_td_path(h2["isolver_path"])
        if "ibook_path" in h2:
            self._pbook = self.resolve_td_path(h2["ibook_path"])
        if "isol_path" in h2:
            self._psol = self.resolve_td_path(h2["isol_path"])

        self.delvar("load_property")

        if self._pbook is None:
            print(("??? self._pbook is None", "adjusting ..."))
            if self.num_book() == 0:
                self.onAddBook()
            else:
                for name, child in self.get_children():
                    if isinstance(child, FigBook):
                        self.set_pbook(child)
            print(self._pbook)
