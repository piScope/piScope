from __future__ import print_function
import os
import wx
import ifigure
import ifigure.widgets.dialog as dialog
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('PyExtFile')

from ifigure.mto.py_code import PyFolder, PyData
from ifigure.mto.py_file import PyFile, PyText
from ifigure.mto.py_script import PyScript
from ifigure.mto.treedict import TreeDict

class ExtMixIn(object):
    def owndir(self):
        extfolderpath = self.get_extfolderpath()
        return extfolderpath

    def has_owndir(self):
        if self.owndir() is None:
            return False
        return os.path.exists(self.owndir())

    def destroy(self, clean_owndir=False, force_clean=False):
        if force_clean:
            TreeDict.destroy(self, clean_owndir=True)
        else:
            TreeDict.destroy(self, clean_owndir=False)

    def onRename(self, evt):
        ret = dialog.message(wx.GetApp().TopWindow,
                             'Rename to this object is not implemented',
                             'Not Inmplemented',
                             0)
        return


class PyExtFolder(ExtMixIn, PyFolder):
    def owndir(self):
        extfolderpath = self.get_extfolderpath()
        if extfolderpath is None:
            return PyFolder.owndir(self)
        else:
            return extfolderpath

    def classimage(self):
        if PyFolder._image_load_done is False:
            PyFolder._image_id = self.load_classimage()
            PyFolder._image_load_done = True
        return PyFolder._image_id[2]

    def add_child(self, *args, **kwagrs):
        idx = super(PyExtFolder, self).add_child(*args, **kwagrs)
        if idx is not None:
            obj = self.get_child(idx=idx)
            make_external(obj)

    def mk_owndir(self):
        if self.has_owndir():
            return
#        if not self._can_have_child:
        if not self._has_private_owndir:
            self._parent.mk_owndir()
            return
        path = self.owndir()
        if (self.get_parent().get_extfolderpath() is not None and
                not self.get_parent().has_owndir()):
            self.get_parent().mk_owndir()

        if not os.path.exists(path):
            os.mkdir(path)

    def load_extfolder(self):
        basepath = self.get_extfolderpath()
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
                    child = PyScript()
                    idx = p.add_child(newname, child, warning=warning)
                    child.set_path_pathmode(fpath, checklist=['extfolder'])
                    # child.import_script(fpath)
#                    script.onImportScriptFile(file = fpath)
        for x in warning:
            if len(x) != 0:
                print(x)

    def reload_ext_tree(self):
        for name, child in self.get_children():
            child.destroy()
        self.load_extfolder()

    def onReloadExtTree(self, evt):
        self.reload_ext_tree()
        evt.Skip()

    def onChangeDirToExt(self, ext):
        os.chdir(self.owndir())

    def onRename(self, evt):
        new_name = self.dlg_ask_newname()
        if new_name is None:
            return
        for name, child in self.get_parent().get_children():
            if child._genuine_name == new_name:
                raise ValueError("The name is already used")
        osfile = self.owndir()
        self._genuine_name = new_name
        nsfile = self.owndir()
        os.rename(osfile, nsfile)
        evt.Skip()

    def init_after_load(self, olist, nlist):
        dprint1("loading ext directory : " + self.owndir())
        self.reload_ext_tree()


class PyExtScript(ExtMixIn, PyScript):
    def set_parent(self, parent):
        if parent is not None and not isinstance(parent, PyExtFolder):
            raise AttributeError("ExtScript's Parent should be ExtFolder")
        PyScript.set_parent(self, parent)

    def rename(self, new, ignore_name_readonly=False):
        for name, child in self.get_parent().get_children():
            if child._genuine_name == new:
                raise ValueError("The name is already used")

        osfile = self.path2fullpath()
        self._genuine_name = new
        self.setvar('path', new+'.py')
        nsfile = self.path2fullpath()
        os.rename(osfile, nsfile)
        param = {"oldname": osfile, "newname": nsfile}
        op = 'rename'

        self.load_script(self.path2fullpath())
        ifigure.events.SendFileChangedEvent(self, operation=op,
                                            param=param)

        return

    def onRename(self, ext):
        PyScript.onRename(self, ext)

    def set_path_pathmode(self, file,
                          modename='pathmode',
                          pathname='path',
                          extname='ext', checklist=None):
        return PyScript.set_path_pathmode(self, file,
                                          modename='pathmode',
                                          pathname='path',
                                          extname='ext', checklist=['extfolder'])


class PyExtFile(ExtMixIn, PyFile):
    def set_parent(self, parent):
        if parent is not None and not isinstance(parent, PyExtFolder):
            raise AttributeError("ExtFile's Parent should be ExtFolder")
        PyFile.set_parent(self, parent)

    pass


class PyExtText(ExtMixIn, PyText):
    def set_parent(self, parent):
        if parent is not None and not isinstance(parent, PyExtFolder):
            raise AttributeError("ExtText's Parent should be ExtFolder")
        PyText.set_parent(self, parent)

    pass


class PyExtData(ExtMixIn, PyData):
    def set_parent(self, parent):
        if parent is not None and not isinstance(parent, PyExtFolder):
            raise AttributeError("ExtData's Parent should be ExtFolder")
        PyData.set_parent(self, parent)


def make_external(obj):
    if isinstance(obj, PyFolder):
        obj.__class__ = PyExtFolder
    elif isinstance(obj, PyScript):
        obj.__class__ = PyExtScript
    elif isinstance(obj, PyText):
        obj.__class__ = PyExtText
    elif isinstance(obj, PyFile):
        obj.__class__ = PyExtFile
    elif isinstance(obj, PyData):
        obj.__class__ = PyExtData
    else:
        pass
