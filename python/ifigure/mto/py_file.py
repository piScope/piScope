from __future__ import print_function
#
#  Name   : py_fiile
#
#          mto to hold a file
#
#          py_file : generic (non-text) files
#          py_text : text files (add edit menu)
#
#          there are five file path modes
#
#              std:  in ifigure (root = ifigure)
#              wdir: in project dir (root = wdir)
#              owndir: in object dir (root = self.owndir())
#              home: in home dir (root = home dirctory)
#              abs : elsewhere (root = '/')
#
#          the order of check priority is as follows
#              owndir
#              wdir
#              std
#              home
#              abs
#
#          among these fivce, std|home|abs is external file
#          mode.
#
#          it also check time stamp of file for version
#          control
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
#  History : 0.5 sometime around Apr. 2012
#            0.6 stop() command
#            0.7 8/30/12 keyborad interupt
#
from ifigure.mto.treedict import TreeDict
import ifigure.utils.cbook as cbook
import ifigure
import ifigure.events
import ifigure.widgets.dialog as dialog
from ifigure.mto.fileholder import FileHolder
import os
import logging
import wx
import threading
import types
import shutil
import multiprocessing


class PyFile(TreeDict, FileHolder):
    def __init__(self, parent=None, script='', src=None):
        super(PyFile, self).__init__(parent=parent, src=src)
        self._can_have_child = False
        self._has_private_owndir = False
        self.setvar("file_pathmode", '')
        self.setvar("file_path", '')
        self.setvar("file_ext", '')

    @classmethod
    def get_namebase(self):
        return 'file'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'file.png')
        return [idx1]

    @classmethod
    def can_have_child(self, child=None):
        return False

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        app = self.get_root_parent().app
        m = [('+File', None, None), ]
        if self.getvar('file_ext') in app.helper.setting['ext'].split(','):
            m.append(('Open', self.onOpenWithHelper, None))
        m = m + [
            ('Set File...', self.onSetFile, None),
            ('Import File...', self.onImportFile, None),
            ('Export File...', self.onExportFile, None),
            ('!', None, None),
            ('---', None, None)] + \
            super(PyFile, self).tree_viewer_menu()
        return m

#    def onRename(self, evt):
#        super(PyScript, self).onRename(evt)
    def onOpenWithHelper(self, e):
        fpath = self.path2fullpath('file_pathmode', 'file_path')
        if fpath == '':
            return
        app = self.get_root_parent().app
        ext = self.getvar('file_ext')

        com = app.helper.setting[ext]
        root = os.path.dirname(os.path.dirname(ifigure.__path__[0]))
        bin = os.path.join(root, 'bin')
        com = com.replace('{bin}', bin)
#        com = com.replace('{0}',   '"'+fpath+'"')
        com = com.replace('{0}',   fpath)
        import subprocess
        import shlex
        print(com)
        subprocess.Popen(com, shell=True)
#        subprocess.Popen(shlex.split(com))
#        import os
#        os.system(

    def onEdit(self, e):
        fpath = self.path2fullpath('file_pathmode', 'file_path')
        if fpath == '':
            return
        ifigure.events.SendEditFileEvent(self,
                                         w=e.GetEventObject(),
                                         file=fpath)

    def onSetFile(self, e):
        file = dialog.read(None, message="Select file")
        self.setfile(file)

    def setfile(self, file):
        if (file != '' and
                os.path.exists(file)):
            self.set_path_pathmode(file)
            self.store_mtime('file_mtime')

    def onImportFile(self, e):
        '''
        import file from outside project directory
        pathmode will be set to 'owndir'
        '''

        file = dialog.read(None, message="Select file")
        if file == '':
            return
        mode, path = self.fullpath2path(file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Import should import from somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return
        self.import_file(file)

    def onExportFile(self, e):
        opath = self.path2fullpath('file_pathmode', 'file_path')

        file = dialog.write(None, defaultfile=opath,
                            message="Enter file name")
        if file == '':
            return
        mode, path = self.fullpath2path(file)
        if (mode == 'wdir' or mode == 'owndir'):
            m = 'Export should export to somewhere outside project directory',
            ret = dialog.message(None, message=m,
                                 title='Import error')
            return

        shutil.copyfile(opath, file)

    def export_file(self, file):
        '''
        export scirpt file to file.
        the destination should be outside
        of wdir
        '''
        path = self.path2fullpath('file_pathmode', 'file_path')
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

    def import_file(self, file):
        '''
        import *.py file from outside of wdir
        the location of original file will be
        saved to "orgpath", "orgpathmode"
        '''
        mode, path = self.fullpath2path(file)
        base, ext = self.split_ext(path)

        if mode == 'wdir':
            # do nothing in this case
            print('can not import from wdir')
            return
        if mode == 'owndir':
            # do not write inside proj directory
            print('can not import from owndir')
            return

        self.setvar("file_orgpath", str(path))
        self.setvar("file_orgpathmode", str(mode))
        self.setvar("file_ext", str(ext))

        if not self.has_owndir():
            self.mk_owndir()
        file2 = os.path.join(self.owndir(), self.name+'.'+ext)
        shutil.copyfile(file, file2)

        self.setvar("file_pathmode", 'owndir')
        self.setvar("file_path", self.name+'.'+ext)
        self.store_mtime('file_mtime')

    def rename(self, new, ignore_name_readonly=False):
        path = self.getvar("file_path")
        base, ext = self.split_ext(path)
        ooname = self.path2fullpath('file_pathmode', 'file_path')
        super(PyFile, self).rename(
            new, ignore_name_readonly=ignore_name_readonly)

        oname = self.path2fullpath('file_pathmode', 'file_path')
        self.setvar("file_path", self.name+'.'+ext)
        nname = self.path2fullpath('file_pathmode', 'file_path')

        if oname != nname:
            os.rename(oname, nname)
            self.set_path_pathmode(nname)
            param = {"oldname": ooname, "newname": nname}
            op = 'rename'
            ifigure.events.SendFileChangedEvent(self, operation=op,
                                                param=param)

#           ifigure.events.SendChangedEvent(self)

    # utility to convert fullpath to path
    def set_path_pathmode(self, path,
                          modename='file_pathmode',
                          pathname='file_path',
                          extname='file_ext'):
        ''' 
        this is to overwrite default var
        '''
        return super(PyFile, self).set_path_pathmode(path, modename,
                                                     pathname, extname)

    def store_mtime(self, name='file_mtime', modename='file_pathmode', pathname='file_path'):
        ''' 
        this is to overwrite default var
        '''
        return super(PyFile, self).store_mtime('file_mtime',
                                               'file_pathmode',
                                               'file_path')

    def path2fullpath(self, modename='pathmode', pathname='path'):
        ''' 
        this is to overwrite default var
        '''
        return super(PyFile, self).path2fullpath('file_pathmode', 'file_path')

    def init_after_load(self, olist, nlist):
        try:
            if self.isExternalFileNewer('file_mtime', 'file_pathname', 'file_path'):
                self._status = '!! external file changed'
            else:
                self._status = ''
        except:
            self._status = '!! filenew check error'


class PyText(PyFile):
    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'text.png')
        return [idx1]

    @classmethod
    def get_namebase(self):
        return 'text'

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_RETURN:
            return self.onEdit
        return None

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        return [('+File', None, None),
                ('Edit', self.onEdit, None),
                ('Set File...', self.onSetFile, None),
                ('Import File...', self.onImportFile, None),
                ('Export File...', self.onExportFile, None),
                ('Export Text to Shell',  self.onExportToShell, None),
                ('!', None, None),
                ('---', None, None)] + \
            super(PyFile, self).tree_viewer_menu()

    def onExportToShell(self, evt):
        fpath = self.path2fullpath('file_pathmode', 'file_path')
        fid = open(fpath, 'r')
        lines = fid.readlines()
        fid.close()

        id = evt.GetEventObject()
        app = id.GetTopLevelParent()
        ret, new_name = dialog.textentry(app,
                                         "Enter the name of new variable",
                                         "Export Text File to Shell", "")
        if ret:
            flag = self.write2shell(lines, new_name)
            app.shell.SendShellEnterEvent()
        e.Skip()  # call update project tree widget
