from __future__ import print_function

import os
import wx
import logging
import shutil
import ifigure
import ifigure.events
import ifigure.utils.cbook as cbook
import ifigure.mto.abs_module as abs_module
import ifigure.mto.py_code as py_code
import ifigure.add_on
import ifigure.widgets.dialog as dialog
from ifigure.mto.py_contents import PyContents
#
#  the same as PyCode but different default icon
#


class PyModuleD(PyContents, pypy_code.PyCode):
    def __init__(self, *args, **kargs):
        self._obj = None
        self._can_have_child = True
        self._first_load = True
        self._args = args
        self._kargs = kargs
        super(PyModule, self).__init__(*args, **kargs)

    @classmethod
    def isPyModule(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'module'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'cog.png')
        return [idx1]

#    def __getitem__(self, key):
#        if hasattr(self._obj, '_getitem_'):
#           return self._obj._getitem_(key)
#        else:
#           return super(py_code.PyCode, self).__getitem__(key)

    def destroy(self):
        if self._obj is not None:
            if hasattr(self._obj, 'clean'):
                self._obj.clean()
            self._obj.unbind_method()
        self._obj = None
        super(py_code.PyCode, self).destroy()

    def can_have_child(self):
        return self._can_have_child

    def load_customimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, self._obj._icon)
#       print 'loading custom icon'
        return [idx1]

    def do_run(self, e=None):
        if self._suppress is False:
            return self._module.run_func('onRun', self)

    def call(self, name, *args, **kargs):
        '''
        call module function/method :
             call(fname, *args, **kargs)
        '''
        if hasattr(self._obj, name):
            return self.call_method(name,  *args, **kargs)
        else:
            return self.call_function(name, *args, **kargs)

    def call_method(self, mname, *args, **kargs):
        # equivalent to call _obj.mname(...)
        # but can call method by string
        logging.basicConfig(level=logging.DEBUG)
        try:
            return self._obj.run_method(mname, *args, **kargs)
        except Exception:
            logging.exception("Module Method Call Failed")

    def call_function(self, fname, *args, **kargs):
        logging.basicConfig(level=logging.DEBUG)
        try:
            f = getattr(self._obj._m_co, fname)
            return f(*args, **kargs)
        except Exception:
            logging.exception("Module Method Call Failed")

    def load_module(self, file):
        try:
            self.set_path_pathmode(file)
            self._obj = abs_module.AbsModule(file=file, obj=self)
            if self._obj._icon != '':
                self._use_custom_image = True
                self._custom_image_load_done = False
            else:
                self._use_custom_icon = False

            # self._name=self._obj._m_co.class_name
            if self._parent is not None:
                names = self._parent.get_childnames()
                if names.count(self._obj._m_co.class_name) != 0:
                    self._name = self.get_parent().get_next_name(self._obj._m_co.class_name)

            self._can_have_child = True
            if hasattr(self._obj._m_co, 'can_have_child'):
                self._can_have_child = self._obj._m_co.can_have_child
            if self._first_load:
                if hasattr(self._obj, 'init'):
                    self._obj.init(*self._args, **self._kargs)
                self._first_load = False
        except:
            logging.exception("Module Method Call Failed")
            print(("PyModule: load_module failed:", file))
        return self

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        menu = []
        if self._obj is None:
            try:
                self.init_after_load()
            except Exception:
                logging.exception("Module Loading Failed")

        try:
            if self._obj is not None:
                if self._obj.check_filenew():
                    self._obj.load_module()

                list = self._obj.menu
                for item in list:
                    txt = item[0]
                    mname = item[1]

                    def xxx(e, method=mname, do_skip=item[2]):
                        self._obj.run_method(method)
                        if do_skip:
                            e.Skip()
                    menu.append((txt, xxx, None))
        except Exception:
            logging.exception("Module Loading Failed")

        if self._obj is not None:
            d = self._obj.get_debug()
        else:
            d = 0
        a = ['0', '1', '2']
        a[d] = '-'+a[d]
        return menu + \
            [('---', None, None),
             ('+Module', None, None),
                ('Edit File', self.onEditModule, None),
                ('Select File', self.onSelectModuleFile, None),
                ('Import File', self.onImportModuleFile, None),
                ('Export File', self.onExportModuleFile, None),
                ('+Set Degug Level', None, None),
                (a[0], self.onDebug0, None),
                (a[1], self.onDebug1, None),
                (a[2], self.onDebug2, None),
                #               ('Import File', self.onImportScriptFile, None),
                ('!', None, None),
                ('!', None, None),
                ('---', None, None)] + \
            super(PyModule, self).tree_viewer_menu()

    def onDebug0(self, e):
        self._obj.set_debug(0)

    def onDebug1(self, e):
        self._obj.set_debug(1)

    def onDebug2(self, e):
        self._obj.set_debug(2)

    def onEditModule(self, e):
        if wx.GetKeyState(wx.WXK_CONTROL):
            self._obj.edit_module()
            return
        handler = self.get_root_parent().app.GetEventHandler()
        evt = ifigure.events.TreeDictEvent(
            ifigure.events.EditFile,
            wx.ID_ANY)
        evt.SetTreeDict(self)
        if self._obj is None:  # if compilation failed _obj is none
            evt.file = self.path2fullpath()
        else:
            evt.file = self._obj._m_file
        handler.ProcessEvent(evt)

    def onSelectModuleFile(self, e=None):
        open_dlg = wx.FileDialog(None, message="Select module",
                                 wildcard='*.py', style=wx.FD_OPEN)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            raise ValueError
        file = open_dlg.GetPath()
        self.load_module(file)
        open_dlg.Destroy()

    def onImportModuleFile(self, e=None):
        file = dialog.read(None, message="Select Module",
                           wildcard='*.py')
        mode, path = self.fullpath2path(file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Import should import from somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return
        self.import_module(file)

    def onExportModuleFile(self, e=None):
        opath = self.path2fullpath()
        file = dialog.write(None, defaultfile=opath,
                            message="Select script",
                            wildcard='*.py')
        if file == '':
            return
        mode, path = self.fullpath2path(file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Export should export to somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return

        shutil.copyfile(opath, file)

    def import_module(self, file):
        '''
        import *.py file from outside of wdir
        the location of original file will be
        saved to "orgpath", "orgpathmode"
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

        self.setvar("orgpath", str(path))
        self.setvar("orgpathmode", str(mode))

        if not self.has_owndir():
            self.mk_owndir()
        file2 = os.path.join(self.owndir(), self.name+'.py')
        shutil.copyfile(file, file2)

        self.load_module(file2)

    def init_after_load(self, olist=None, nlist=None):
        #        print "loading", self.getvar("module file")
        name = self._name
        file = self.path2fullpath()
        if file != '':
            self.load_module(file)
        self._name = name

    def rename(self, new):
        oname = self.name
        super(PyModule, self).rename(new)
        mode = self.getvar("pathmode")
        if (mode == 'wdir'):
            # 2012. 08. 24  this should not happen.
            # py_module should always
            # use pathmode=owndir or
            # outside of wdir
            print("pathmode is not owndir")
            print("rename may not work properly")
            return
        if (oname != self.name and
                mode == 'owndir'):
            sfile = os.path.join(self.owndir(), self.getvar("path"))
            nsfile = os.path.join(self.owndir(), self.name+'.py')

            if os.path.exists(sfile):
                os.rename(sfile, nsfile)
                self.set_path_pathmode(nsfile)
                self.load_module(nsfile)

            ifigure.events.SendChangedEvent(self)
