from __future__ import print_function
import os
import wx
import logging
import shutil
import weakref
import ifigure
import ifigure.events
import ifigure.utils.cbook as cbook
import ifigure.mto.abs_module as abs_module
import ifigure.mto.py_code as py_code
import ifigure.add_on
import ifigure.widgets.dialog as dialog
from ifigure.mto.fileholder import FileHolder
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('PyModule')

#
#  the same as PyCode but different default icon
#
active_module = {}


class PyModule(py_code.PyCode, FileHolder):
    def __init__(self, *args, **kargs):
        self._obj = None
        self._can_have_child = False
        self._has_private_owndir = False
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

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_RETURN:
            return self.onEditModule
        return None

    def __getitem__(self, key):
        if hasattr(self._obj, '_getitem_'):
            return self._obj._getitem_(key)
        else:
            return super(py_code.PyCode, self).__getitem__(key)

    def destroy(self, clean_owndir=True):
        if self._obj is not None:
            if hasattr(self._obj, 'clean'):
                self._obj.clean()
            self._obj.unbind_method()
        self._obj = None
        super(py_code.PyCode, self).destroy(clean_owndir=clean_owndir)

    def can_have_child(self, child=None):
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

    def has_method(self, mname):
        return self._obj.has_method(mname)

    def call_method(self, mname, *args, **kargs):
        # equivalent to call _obj.mname(...)
        # but can call method by string
        logging.basicConfig(level=logging.DEBUG)
        try:
            return self._obj.run_method(mname, *args, **kargs)
        except Exception:
            raise ValueError
#            logging.exception("Module Method Call Failed")

    def call_function(self, fname, *args, **kargs):
        logging.basicConfig(level=logging.DEBUG)
        try:
            f = getattr(self._obj._m_co, fname)
            return f(*args, **kargs)
        except Exception:
            raise ValueError
#            logging.exception("Module Method Call Failed")

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
            self._has_private_owndir = True
            allow_only_one_active = False
            if hasattr(self._obj._m_co, 'can_have_child'):
                self._can_have_child = self._obj._m_co.can_have_child
            if hasattr(self._obj._m_co, 'has_private_owndir'):
                self._has_private_owndir = self._obj._m_co.has_private_owndir
            if hasattr(self._obj._m_co, 'nosave_var0'):
                self._nosave_var0 = self._obj._m_co.nosave_var0

            if hasattr(self._obj._m_co, 'allow_only_one_active'):
                allow_only_one_active = self._obj._m_co.allow_only_one_active
            if allow_only_one_active:
                if not file in active_module:
                    active_module[file] = []
                if not self in [m() for m in active_module[file] if m() is not None]:
                    if any([not m().is_suppress() for m in active_module[file] if m() is not None]):
                        self._status = 'off'
                        self.set_suppress(True)
                    active_module[file].append(weakref.ref(self))

            if self._first_load:
                if hasattr(self._obj, 'init'):
                    self._obj.init(*self._args, **self._kargs)
                self._first_load = False
        except:
            logging.exception("Module Method Call Failed")
            print(("PyModule: load_module failed:", file))
        return self

    def activate(self):
        file = self.path2fullpath()
        if file in active_module:
                # cleaning list first
            active_module[file] = [
                m for m in active_module[file] if m() is not None]
            for m in active_module[file]:
                m().set_suppress(True)
                m()._status = 'off'
            self.set_suppress(False)
            self._status = 'on'

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
                #
                if self.has_method('tree_viewer_menu'):
                    list = self.call_method('tree_viewer_menu')
                else:
                    list = self._obj.menu
                for item in list:
                    txt = item[0]
                    mname = item[1]

                    def xxx(e, method=mname, do_skip=item[2]):
                        self._obj.run_method(method, e)
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

#    def onProjTreeActivate(self, e):
#        self.onEditModule(e)
    def onEditModule(self, e):
        print(wx.GetKeyState(wx.WXK_CONTROL))
#        if wx.GetKeyState(wx.WXK_CONTROL):
#           self._obj.edit_module()
#           return
#        handler=self.get_root_parent().app.GetEventHandler()
#        evt=ifigure.events.TreeDictEvent(
#                    ifigure.events.EditFile,
#                    wx.ID_ANY)
#        evt.SetTreeDict(self)
        if self._obj is None:  # if compilation failed _obj is none
            fpath = self.path2fullpath()
        else:
            fpath = self._obj._m_file
        ifigure.events.SendEditFileEvent(self,
                                         w=e.GetEventObject(),
                                         file=fpath)
#        handler.ProcessEvent(evt)

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

        if hasattr(self._obj, 'init_after_load'):
            return self.call_method('init_after_load', olist, nlist)

    def rename(self, new,  ignore_name_readonly=False):
        osfile = self.path2fullpath()
        oname = self.name
        oowndir = self.owndir()
        super(PyModule, self).rename(
            new, ignore_name_readonly=ignore_name_readonly)

        sfile = self.path2fullpath()
        mode = self.getvar("pathmode")
        if mode == 'owndir':
            nsfile = os.path.join(self.owndir(), self.name+'.py')
            if os.path.exists(sfile):
                os.rename(sfile, nsfile)
                self.set_path_pathmode(nsfile)
            else:
                print(('can not find', sfile))

            # remove old pyc pyo
            if os.path.exists(sfile+'c'):
                os.remove(sfile+'c')
            if os.path.exists(sfile+'o'):
                os.remove(sfile+'o')
        else:
            nsfile = sfile
        param = {"oldname": osfile, "newname": nsfile}
        op = 'rename'
        file = self.path2fullpath()
        if file != '':
            self.load_module(file)
        ifigure.events.SendFileChangedEvent(self, operation=op,
                                            param=param)

        return
        # 2013 11 ( followin is an old routine)
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
            osfile = os.path.join(oowndir, self.getvar("path"))
            sfile = os.path.join(self.owndir(), self.getvar("path"))
            nsfile = os.path.join(self.owndir(), self.name+'.py')

            if os.path.exists(sfile):
                os.rename(sfile, nsfile)
                self.set_path_pathmode(nsfile)
                self.load_module(nsfile)
                param = {"oldname": osfile, "newname": nsfile}
                op = 'rename'
                ifigure.events.SendFileChangedEvent(self, operation=op,
                                                    param=param)

#           ifigure.events.SendChangedEvent(self)

    def get_filepath(self):
        try:
            pn = self._obj._m_co.pathname
            mn = self._obj._m_co.modename
            return self.path2fullpath(mn, pn)
        except:
            import traceback
            print(traceback.format_exc())
            return ''

    def set_contents(self, *args):
        if hasattr(self._obj._m_co, 'set_contents'):
            m = self._obj._m_co.set_contents
            return m(self, *args)
        else:
            return py_code.PyCode.set_contents(self, *args)
            
