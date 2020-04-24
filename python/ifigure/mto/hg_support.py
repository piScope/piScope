from __future__ import print_function

'''
   HGSupport is subclass to add Mercurial support to
   TreeDict objects. Currently following classes has
   HGSupport. This class is intended to add HG capability to 
   TreeDict object which has its own folder. At present,
   following class has HG Support
      PyFolder
      PyModel   


   HGSupport provides...
    load_subtree_hg(parent, url='', name = '',  use_ssh=True):    
    HGSupport
       commit  
       revert  : discard all changes in tree and files 
       clone   : make clone outside the project directory
'''

from ifigure.utils.get_username import get_username
import os
import wx
import shutil
import ifigure.events
import traceback
import time
import subprocess
import shlex


from fnmatch import fnmatch
import ifigure.widgets.dialog as dialog
from ifigure.mto.treedict import TreeDict
from ifigure.utils.edit_list import DialogEditList

from ifigure.utils.cbook import isBinary

from ifigure.utils.wx3to4 import PyDeadObjectError, deref_proxy

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('HGSupport')

r_vname = 'mercurial_root'
p_vname = 'mercurial_path'
diffwindow = None
usr = get_username()

try:
    if 'LANG' in os.environ:
        org_lang = os.environ['LANG']
    else:
        org_lang = ''
    import hgapi
    hgapi.Repo._env = os.environ.copy()
    if 'LANG' in os.environ and org_lang != '':
       os.environ['LANG'] = org_lang

    has_hg = True
    
    def has_repo(obj):
        if not isinstance(obj, HGSupport):
            return False
        if not obj.has_owndir():
            return False
        return os.path.exists(os.path.join(obj.owndir(), '.hg'))

    def hg_check_all_incoming_outgoing(obj0, sb=None):
        #app = wx.GetApp().TopWindow

        updated_obj = []
        newer_obj = []
        both_obj = []
        for obj in obj0.get_root_parent().walk_tree(stop_at_ext=True):
            if has_repo(obj):
                url, root, path = obj.get_mercurial_url()
                if url is None:
                    continue
                print('checking incoming to ' + str(url))
                try:
                    repo = hgapi.Repo(obj.owndir())
                    l1, l2 = obj.hg_incoming_outgoing_changesets_list(
                        repo, url)
                    if len(l1) > 0:
                        obj._status = '!'
                        if url.startswith('ssh://'):
                            updated_obj.append((obj, len(l1), repo.hg_rev(),
                                                '?(remote)'))
                        else:
                            repo2 = hgapi.Repo(url)
                            updated_obj.append((obj, len(l1), repo.hg_rev(),
                                                repo2.hg_rev()))
                    else:
                        obj._status = ''
                    if len(l2) > 0:
                        if url.startswith('ssh://'):
                            newer_obj.append((obj, len(l2), repo.hg_rev(),
                                              '?(remote)'))
                        else:
                            repo2 = hgapi.Repo(url)
                            newer_obj.append((obj, len(l2), repo.hg_rev(),
                                              repo2.hg_rev()))
                    if len(l1) > 0 and len(l2) > 0:
                        both_obj.append(obj)
                except:
                    traceback.print_exc()
        return updated_obj, newer_obj, both_obj

    def hg_verify_all_repo(obj0):
        cwd = os.getcwd()
        broken_repo = []
        for obj in obj0.get_root_parent().walk_tree():
            if has_repo(obj):
                print('verifing repo at ' + str(obj))
                os.chdir(obj.owndir())
                p = subprocess.Popen(shlex.split('hg verify'),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     universal_newlines = True)
                aaa = p.stdout.readlines()
                for a in aaa:
                    if a.find('damaged') != -1:
                        print('broken repo at ' + str(obj))
                        broken_repo.append(obj)
                        break
        os.chdir(cwd)
        return broken_repo
        # app.proj_tree_viewer.update_widget()#_request2()

    def ask_new_url(parent):
        app0 = wx.GetApp().TopWindow
        ret, m = dialog.textentry(app0,
                                  "Enter new url", "Mercurial Clone",
                                  parent.value_suggestion())
        if not ret:
            return None
        return {'url': str(m)}

    def dlg_s():
        default_value = wx.GetApp().TopWindow.aconfig.setting['hg_default_url']
        return {'rule': ('connection', {'url': ''}),
                'pref':  'pref.hg_config',
                'varname': 'connection',
                'keyname': 'url',
                'def_value': default_value,
                'dialog':  ask_new_url}

    def rootpath2url(root, path):
        root = str(root)
        path = str(path)
        if root.startswith('ssh://'):
            url = root+'/' + path
        else:
            root = os.path.expanduser(root)
            url = os.path.join(root, path)
        return url

    def load_repo_treedata(obj):
        parent = obj.get_parent()
        name = obj._name
        owndir = obj.owndir()
        ichild = obj.get_ichild()
        fpath = os.path.join(owndir, ".tree_data_hg")
        if not os.path.exists(fpath):
            fpath = os.path.join(owndir, ".tree_data")
#           return False
        else:
            obj.destroy(clean_owndir=False)
            fid = open(fpath, 'rb')
            fid = open(fpath, 'rb')
            td, olist, nlist = TreeDict().load(fid, keep_zorder=True)
            fid.close()
            parent.add_child(name, td, keep_zorder=True)
            parent.move_child(td.get_ichild(), ichild)
#           for obj in td.walk_tree():
#               obj.init_after_load(olist, nlist)

            for name, child in obj.get_children():
                for obj2 in child.walk_tree():
                    if has_repo(obj2):
                        load_repo_treedata(obj2)

    def handle_pure_file_repo(parent, name, dpath):
        #
        #  In this case, it makes a containing folder
        #  and gather *.py to make PyScript
        #  I should be handling other files here too?
        #
        from ifigure.mto.py_code import PyFolder
        from ifigure.mto.py_script import PyScript
        from ifigure.mto.py_file import PyText

        folder = parent.add_childobject(PyFolder, name)
        folder.setvar('include', [])
        folder.setvar('exclude', ['.tree_data_hg'])

        def fill_model_tree(parent, path):
            for file in os.listdir(path):
                if file.startswith('.'):
                    continue
                if file.endswith('.py'):
                    script = parent.add_childobject(PyScript, file[:-3])
                    script.load_script(os.path.join(path, file))
                elif file.endswith('.txt'):
                    txt = parent.add_childobject(PyText, file[:-4])
                    txt.setfile(os.path.join(path, file))
                elif os.path.isdir(os.path.join(path, file)):
                    folder = parent.add_childobject(PyFolder, file)
                    fill_model_tree(folder, os.path.join(path, file))
        fill_model_tree(folder, dpath)
        return folder

    def load_subtree_hg(parent, root='', path='', name='', overwrite=False,
                        run_setup=False, launch_gui=False):
        app = wx.GetApp().TopWindow
        if root == '':
            list6 = [
                ["root repository", None, 304, dlg_s()],
                ["source ", path, 0],
                ["destination", '', 0],
                [None, True, 3, {"text": 'Run setup script'}], ]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app,
                                   title='retrieve subtree from HG repo.')
            if not value[0]:
                return
            if not parent.has_owndir():
                parent.mk_owndir()

#           url = rootpath2url(
            root = str(value[1][0])
            path = str(value[1][1])
            name = str(value[1][2])
            run_setup = value[1][3]
            if name.strip() == '':
                name = value[1][1].split('/')[-1]
        else:
            if not parent.has_owndir():
                parent.mk_owndir()
            if name == '':
                name = path.split('/')[-1]

        if parent.has_child(name):
            if overwrite:
                parent.get_child(name=name).destroy()
            else:
                print(parent.get_full_path()+'.'+name + ' already exists.')
                obj = parent.get_child(name=name)
                _add_include_exclude(obj)
                return obj
        if path.startswith('/'):
            path = path[1:]
        url = rootpath2url(root, path)
        dpath = os.path.join(parent.owndir(), name)
        repo = hgapi.Repo(parent.owndir())
        try:
            repo2 = repo.hg_clone(url, dpath)
        except:
            print(url, dpath)
            dialog.showtraceback(parent=app,
                                 txt='Failed to clone subtree from '+url,
                                 title='Failed to clone',
                                 traceback=traceback.format_exc())

            return

        load_fpath = True
        fpath = os.path.join(dpath, ".tree_data_hg")
        if not os.path.exists(fpath):
            fpath = os.path.join(dpath, ".tree_data")
            if not os.path.exists(fpath):
                #
                #  In this case, it makes a containing folder
                #  and gather *.py to make PyScript
                #  I should be handling other files here too?
                #

                td = handle_pure_file_repo(parent, name, dpath)
                load_fpath = False
            else:
                dlg = wx.MessageDialog(None,
                                       'HG update succeeded but .tree_data_hg is not found.',
                                       'Old style for HG repo',
                                       wx.OK)
                ret = dlg.ShowModal()
                dlg.Destroy()
                del_old_treedata = True
        else:
            del_old_treedata = False
        if load_fpath:
            fid = open(fpath, 'rb')
            td, olist, nlist = TreeDict().load(fid, keep_zorder=True)
            fid.close()
            parent.add_child(name, td, keep_zorder=True)

            # for sub repo
            subrepos = []
            for name, child in td.get_children():
                #           print child
                for obj in child.walk_tree():
                    if has_repo(obj):
                        # print 'subrepo', obj
                        load_repo_treedata(obj)

            if del_old_treedata:
                os.remove(fpath)

            for obj in td.walk_tree():
                obj.init_after_load(olist, nlist)

        td.set_mercurial_url(root, path)

        for name, child in td.get_children():
            #           print child
            for obj in child.walk_tree():
                if has_repo(obj):
                    r = hgapi.Repo(obj.owndir())
                    latest = r.revisions(slice(-1, -1))[0].rev
                    current = r.hg_rev()
                    if latest > current:
                        dprint1('updating ' + str(obj) + ' ' +
                                str(r.hg_rev()) + '->' + str(latest))
                        obj.onHGupdate(evt=None, m=latest)

        if run_setup:
            #           try:
            if (td.has_child("scripts") and
                    td.scripts.has_child("setup")):
                #               wx.CallAfter(td.scripts.setup.Run)
                td.scripts.setup.Run()
#           except:
#               dialog.showtraceback(parent = td.get_root_parent().app,
#                                    txt='Failed to run setup script',
#                                    title='Setup script failced',
#                                    traceback=traceback.format_exc())
        _add_include_exclude(td)
        return td

    def hg_add_no_binary(repo, dir, exclude=None, include=None):
        ##
        # take care of adding and removing files in
        # repo.
        # default action is include non-binary files.
        ##
        # exclude = a list of (text) files or dirs to be excluded
        # include = a list of (binary) files to be included
        ##
        addfile = []
        skipfile = []
        rmfile = []
        modfile = []

        if exclude is None:
            exclude = []
        if include is None:
            include = ['.tree_data_hg']

        s = repo.hg_status(clean=True)
        for item in s['!']:
            path = os.path.join(dir, item)
            repo.hg_remove(path)
            rmfile.append(item)
#       print s
#       print 'exclude', exclude
        for item in s['C']:
            path = os.path.join(dir, item)
            itemb = os.path.basename(item)
            if item in exclude or any(fnmatch(itemb, x) for x in exclude):
                repo.hg_remove(path)
                rmfile.append(item)
        for item in s['M']:
            path = os.path.join(dir, item)
            itemb = os.path.basename(item)
            if item in exclude or any(fnmatch(itemb, x) for x in exclude):
                repo.hg_remove(path)
                rmfile.append(item)
        s = repo.hg_status(clean=True)
        modfile = s['M']
        for item in s['?']:
            path = os.path.join(dir, item)
            itemb = os.path.basename(item)
#           print item
            for item2 in exclude:
                if item2 == '':
                    continue
                if (fnmatch(itemb, item2) or
                        path.find(os.path.join(dir, item2)) != -1):
                    dprint1('skipping folder ', item)
                    skipfile.append(item)
                    break

            else:
                print((isBinary(path), path))
                if isBinary(path):
                    if item in include or any(fnmatch(itemb, x) for x in include):
                        repo.hg_add(path)
                        addfile.append(item)
                    else:
                        dprint1('skipping binary', item)
                        skipfile.append(item)
                else:
                    if item in exclude or any(fnmatch(itemb, x) for x in exclude):
                        dprint1('skipping text', item)
                        skipfile.append(item)
                    else:
                        repo.hg_add(path)
                        addfile.append(item)

        txt = ('*added*\n  ' + '\n  '.join(addfile) + '\n*removed*\n  ' +
               '\n  '.join(rmfile) + '\n*skipped*\n  '+'\n  '.join(skipfile) +
               '\n*modified*\n  ' + '\n  '.join(modfile))

        return addfile, rmfile, skipfile, txt

    def _add_include_exclude(obj):
        if not obj.hasvar('include'):
            obj.setvar('include', ['.tree_data_hg'])
        if not obj.hasvar('exclude'):
            obj.setvar('exclude', [])

    def update_to_latest(obj, rev=False):
        '''
        pull -> update

        if rev push is performed
        '''

        url, root, path = obj.get_mercurial_url()

        # pull
        ocwd = os.getcwd()

        os.chdir(obj.owndir())
        repo = hgapi.Repo(obj.owndir())
        if not rev:
            repo.hg_pull(url)
            obj.hg_set_projtreeviewer_status(repo=repo)
            latest = repo.revisions(slice(-1, -1))[0].rev
        else:
            repo.hg_push(url)
            repo2 = hgapi.Repo(url)
            latest = repo2.revisions(slice(-1, -1))[0].rev
            repo2.hg_update(int(latest))
        os.chdir(ocwd)

        #app = wx.GetApp().TopWindow
        #tv = app.proj_tree_viewer
        # tv.update_widget()

        # update
        if not rev:
            new_obj = obj.onHGupdate(None, latest)
            return latest, new_obj
        else:
            return latest, url

    class HGSupport(object):
        def __init__(self):
            self._hg_rev_str = None

        def get_repo(self):
            try:
                return hgapi.Repo(self.owndir())
            except:
                return None

        def onHGturnon(self, evt):
            if not self.has_owndir():
                self.mk_owndir()
            if not self._save_tree_data():
                return

            tv = evt.GetEventObject()
            _add_include_exclude(self)
            list = [["Include", ','.join(self.getvar('include')), 0, None],
                    ["Exclude", ','.join(self.getvar('exclude')), 0, None],
                    [None, '(Note) List binary files to be included and text files to be exlcuded.',
                     2, None]]
            tv.OpenPanel(list, self, '_do_make_hg')

        def _do_make_hg(self, value):
            app = wx.GetApp().TopWindow
            try:
                self.setvar('include', [x.strip()
                                        for x in str(value[0]).split(',')])
                self.setvar('exclude', [x.strip()
                                        for x in str(value[1]).split(',')])
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to set include/exclude',
                                     title='Failure',
                                     traceback=traceback.format_exc())
                return
            repo = hgapi.Repo(self.owndir())
            repo.hg_init()
            self.update_hgsub()
            addfile, rmfile, skipfile, txt = hg_add_no_binary(repo,
                                                              self.owndir(),
                                                              include=self.getvar(
                                                                  'include'),
                                                              exclude=self.getvar('exclude'))
            dlg = wx.MessageDialog(None, txt, "HG add/remove", wx.OK)
            ret = dlg.ShowModal()
            dlg.Destroy()
            self._image_update = False
            _add_include_exclude(self)
            tv = app.proj_tree_viewer
            tv.update_widget()

        def onHGturnoff(self, evt=None, confirm=True):
            if not self.has_owndir():
                return
            if confirm:
                dlg = wx.MessageDialog(wx.GetApp().TopWindow,
                                       "Are you really sure to delete the repository information?\nThis is undoable",
                                       "Deleting HG repository information", wx.YES_NO)
                ret = dlg.ShowModal()
                dlg.Destroy()
                if ret != wx.ID_YES:
                    return

            odir = self.owndir()
            files = ['.tree_data_hg', '.hg', '.hgsubs']
            for file in files:
                path = os.path.join(odir, file)
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            names = [r_vname, p_vname, 'include', 'exclude']
            for name in names:
                if self.hasvar(name):
                    self.delvar(name)
            self._image_update = False
            self._hg_rev_str = None
            if evt is not None:
                evt.Skip()

        def onHGcommit(self, evt):
            app = wx.GetApp().TopWindow
            list6 = [
                ["messsage", 'commit-#xxx', 0, None],
                #               ["user", os.getenv("USER"), 0, None]]
                ["user", usr, 0, None]]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG commit')
            if not value[0]:
                return

            no_treedata = True if '.tree_data_hg' in self.getvar(
                'exclude') else False
            self.do_commit(str(value[1][0]), user=str(
                value[1][1]), no_treedata=no_treedata)
            self.hg_set_projtreeviewer_status()
            evt.Skip()

        def onHGclone(self, evt):
            app = wx.GetApp().TopWindow
            name = self.getvar('mercurial_path')
            if name is None:
                name = self._name
            l2 = [["commit message", '',  0, None], ]
            list6 = [
                ["root repository", None, 304, dlg_s()],
                ["name", name, 0, None],
                #               [None, (False, ['change #1']),  27,
                #                      ({"text": 'commit modification'},
                #                      {"elp": l2},)],
                [None, True,  3, {"text": 'change source tree to the new clone'}]]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG clone')
            if not value[0]:
                return
            if not self.update_hgsub():
                return
#           if value[1][2][0]:
#               if not self.do_commit(str(value[1][2][1])): return
            url = rootpath2url(str(value[1][0]), str(value[1][1]))

            ocwd = os.getcwd()
            os.chdir(self.owndir())
            try:
                repo = hgapi.Repo(self.owndir())
                if not url.startswith('ssh://'):
                    # for local repo, check if directory exists
                    dirname = os.path.dirname(url)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                repo.hg_clone('.', url)
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to clone subtree to '+url,
                                     title='Failed to clone',
                                     traceback=traceback.format_exc())
            if value[1][2]:
                self.set_mercurial_url(str(value[1][0]), str(value[1][1]))
            os.chdir(ocwd)

        def onHGpush(self, evt):
            app = wx.GetApp().TopWindow
            url, root, path = self.get_mercurial_url()
            if url is not None:
                root = root
                name = path
            else:
                root = None
                name = self._name

            list6 = [
                ["root repository", root, 304, dlg_s()],
                ["name", name, 0, None],
                [None, True, 3, {"text": 'Perform HG update'}], ]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG push')
            if not value[0]:
                return
            if not self.update_hgsub():
                return
            url = rootpath2url(str(value[1][0]), str(value[1][1]))

            ocwd = os.getcwd()
            os.chdir(self.owndir())
            try:
                urlbk, rootbk, pathbk = self.get_mercurial_url()
                repo = hgapi.Repo(self.owndir())
                self.set_mercurial_url(str(value[1][0]), str(value[1][1]))
                repo.hg_push(url)
                if value[1][2] and not url.startswith('ssh'):
                    repo2 = hgapi.Repo(url)
                    latest = repo2.revisions(slice(-1, -1))[0].rev
                    repo2.hg_update(int(latest))
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to push',
                                     title='Failed to push',
                                     traceback=traceback.format_exc())
            self.set_mercurial_url(rootbk, pathbk)
            os.chdir(ocwd)

        def onHGpull(self, evt):
            url, root, path = self.get_mercurial_url()
            if url is not None:
                root = root
                name = path
            else:
                root = None
                name = self._name
            app = wx.GetApp().TopWindow
            list6 = [
                ["root repository", root, 304, dlg_s()],
                ["name", name, 0, None], ]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG pull')
            if not value[0]:
                return

            url = rootpath2url(str(value[1][0]), str(value[1][1]))

            ocwd = os.getcwd()
            os.chdir(self.owndir())
            try:
                repo = hgapi.Repo(self.owndir())
                repo.hg_pull(url)
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to pull',
                                     title='Failed to pull',
                                     traceback=traceback.format_exc())
            os.chdir(ocwd)
            self.set_mercurial_url(str(value[1][0]), str(value[1][1]))
            self.hg_set_projtreeviewer_status(repo=repo)
#           self.setvar('mercurial_url', url
            evt.Skip()

        def onHGIncoming(self, evt):

            url, root, path = self.get_mercurial_url()
            if url is not None:
                root = root
                name = path
            else:
                root = None
                name = self._name
            app = wx.GetApp().TopWindow
            list6 = [
                ["root repository", root, 304, dlg_s()],
                ["name", name, 0, None], ]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG incoming')
            if not value[0]:
                return

            url = rootpath2url(str(value[1][0]), str(value[1][1]))
            ocwd = os.getcwd()
            os.chdir(self.owndir())
            try:
                repo = hgapi.Repo(self.owndir())
                l1, l2 = self.hg_incoming_outgoing_changesets_list(repo, url)
                if len(l1) > 0:
                    self._status = '!'
                    out = repo.hg_command('incoming', url)
                    dialog.showtraceback(parent=app,
                                         txt=out,
                                         title='Incoming changeset',
                                         traceback=traceback.format_exc())
                else:
                    self._status = ''
                    dialog.showtraceback(parent=app,
                                         txt='No incoming change',
                                         title='Incoming changeset',
                                         traceback=traceback.format_exc())

            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to hg_command',
                                     title='Failed to hg_command',
                                     traceback=traceback.format_exc())
            os.chdir(ocwd)
#           self.set_mercurial_url(str(value[1][0]), str(value[1][1]))
            self.hg_set_projtreeviewer_status(repo=repo)
            evt.Skip()

        def onHGOutgoing(self, evt):
            url, root, path = self.get_mercurial_url()
            if url is not None:
                root = root
                name = path
            else:
                root = None
                name = self._name
            app = wx.GetApp().TopWindow
            list6 = [
                ["root repository", root, 304, dlg_s()],
                ["name", name, 0, None], ]

            value = DialogEditList(list6, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG outgoing')
            if not value[0]:
                return

            url = rootpath2url(str(value[1][0]), str(value[1][1]))
            ocwd = os.getcwd()
            os.chdir(self.owndir())
            try:
                repo = hgapi.Repo(self.owndir())
                l1, l2 = self.hg_incoming_outgoing_changesets_list(repo, url)
                if len(l2) > 0:
                    out = repo.hg_command('outgoing', url)
                    dialog.showtraceback(parent=app,
                                         txt=out,
                                         title='Outgoing changeset',
                                         traceback=traceback.format_exc())
                else:
                    self._status = ''
                    dialog.showtraceback(parent=app,
                                         txt='No outgoing change',
                                         title='Outgoing changeset',
                                         traceback=traceback.format_exc())

            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to hg_command',
                                     title='Failed to hg_command',
                                     traceback=traceback.format_exc())
            os.chdir(ocwd)
            self.set_mercurial_url(str(value[1][0]), str(value[1][1]))
            self.hg_set_projtreeviewer_status(repo=repo)
            evt.Skip()

        def onHGDiff(self, evt=None):
            app = wx.GetApp().TopWindow
            repo = self.get_repo()
            latest = repo.revisions(slice(-1, -1))[0].rev
            current = repo.hg_rev()
            ll = [[None, 'Enter revision numbers to compare', 2, None],
                  ["revision (older)", str(current), 0, None],
                  ["revision (newer)", str(latest), 0, None],
                  [None, 'newer == "", diff against working dir.', 2, None],
                  [None, 'older == newer, diff between the latest and current', 2, None], ]

            value = DialogEditList(ll, modal=True,
                                   style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                   tip=None,
                                   parent=app, title='HG diff')
            if not value[0]:
                return
            a = str(value[1][1])
            b = str(value[1][2])
            if b == '':
                args = (str(a),)
            elif int(a) != int(b):
                args = (str(a), str(b),)
            elif int(a) == int(b):
                args = tuple()
            try:
                res = repo.hg_diff(*args)
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to hg_diff',
                                     title='Failed to hg_diff',
                                     traceback=traceback.format_exc())
            if globals()['diffwindow'] is not None:
                try:
                    globals()['diffwindow'].Destroy()
                except PyDeadObjectError:
                    pass
                globals()['diffwindow'] = None
            from ifigure.widgets.hgdiff_window import HGDiffWindow
            globals()['diffwindow'] = HGDiffWindow(res, wx.GetApp().TopWindow)

        def onHGupdate(self, evt=None, m=None):
            repo = hgapi.Repo(self.owndir())
            app0 = wx.GetApp().TopWindow
            if m is None:
                latest = repo.revisions(slice(-1, -1))[0].rev
                ret, m = dialog.textentry(app0,
                                          "Enter revision #", "Mercurial Update", str(latest))
                if not ret:
                    return None
            status = repo.hg_status()
            for key in status:
                if key == '?':
                    continue
                if len(status[key]) != 0:
                    print(status)
                    ret, m = dialog.message(app0,
                                            "Local repo status is not clean. \n(" +
                                            self.get_full_path()+')',
                                            "Mercurial Update Error")
                    self.hg_set_projtreeviewer_status(repo)
#                    self._status = '!'
                    return None

            repo.hg_update(int(m))

            parent = self.get_parent()
            owndir = self.owndir()
            name = self._name
            ichild = self.get_ichild()
            url, root, path = self.get_mercurial_url()

            self.destroy(clean_owndir=False)

            del_old_treedata = False
            load_fpath = True

            fpath = os.path.join(owndir, ".tree_data_hg")
            if not os.path.exists(fpath):
                fpath = os.path.join(owndir, ".tree_data")
                if not os.path.exists(fpath):
                    print((url, root, path))
                    td = handle_pure_file_repo(parent, name, owndir)
                    load_fpath = False
                else:
                    dlg = wx.MessageDialog(None,
                                           'HG update succeeded but .tree_data_hg is not found.',
                                           'Old style for HG repo',
                                           wx.OK)
                    ret = dlg.ShowModal()
                    dlg.Destroy()
                    fpath = os.path.join(owndir, ".tree_data")
                    del_old_treedata = True
            if load_fpath:
                fid = open(fpath, 'rb')
                td, olist, nlist = TreeDict().load(fid, keep_zorder=True)
                fid.close()
                parent.add_child(name, td, keep_zorder=True)
            parent.move_child(td.get_ichild(), ichild)
            if load_fpath:
                for obj in td.walk_tree():
                    obj.init_after_load(olist, nlist)
            if del_old_treedata:
                os.remove(fpath)

            if url is not None:
                td.set_mercurial_url(root, path)
            if evt is not None:
                #               evt.GetEventObject().update_widget_request2()
                ifigure.events.SendFileSystemChangedEvent(parent, reload=True)
                evt.Skip()
            return td

        def onHGMakeRepo(self, evt):
            app0 = wx.GetApp().TopWindow
            ret, m = dialog.textentry(app0,
                                      "Enter variable name", "Create repo object", 'repo')
            if not ret:
                return None
            repo = hgapi.Repo(self.owndir())
            self.write2shell(repo, m)

        def onHGreload(self, evt):
            path = self.eval("mercurial_path")
            root = self.eval("mercurial_root")
            name = self.name
            parent = self.get_parent()
            i2 = self.get_ichild()
            child = load_subtree_hg(parent, root=root, path=path, name=name,
                                    overwrite=True)
            i1 = child.get_ichild()
            parent.move_child(i1, i2)
            evt.Skip()

        def onHGrevertall(self, evt):
            dlg = wx.MessageDialog(None,
                                   'Do you discard all changes since the last commit?',
                                   'Revert',
                                   wx.OK | wx.CANCEL)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret != wx.ID_OK:
                return

            d = self.owndir()
            fpath = os.path.join(d, ".hg_data_hg")
            if not os.path.exists(os.path.join(d, ".hg")):
                return  # not a repo

            ichild = self.get_ichild()

            owndir = self.owndir()
            name = self._name
            parent = self.get_parent()
            repo = hgapi.Repo(owndir)
            # repo.hg_revert(True)
            repo.hg_revert(all)
            self.hg_set_projtreeviewer_status(repo=repo)
            # puting the tree back
            vars = self.getvar().copy()
            self.destroy(clean_owndir=False)
            if not os.path.exists(fpath):
                #
                #  In this case, it makes a containing folder
                #  and gather *.py to make PyScript
                #  I should be handling other files here too?
                #
                print(vars)
                td = handle_pure_file_repo(parent, name, owndir)
                td.setvar(vars)
                load_fpath = False
            else:
                load_fpath = True
            if load_fpath:
                fid = open(fpath, 'rb')
                td, olist, nlist = TreeDict().load(fid, keep_zorder=True)
                fid.close()
                parent.add_child(td._name, td, keep_zorder=True)
            parent.move_child(td.get_ichild(), ichild)
            if load_fpath:
                for obj in td.walk_tree():
                    obj.init_after_load(olist, nlist)

            for item in repo.hg_status()['?']:
                os.remove(os.path.join(d, item))
            ifigure.events.SendFileSystemChangedEvent(parent, reload=True)
            evt.Skip()

        def onHGSetting(self, evt):
            list = [["Include", ', '.join(self.getvar('include')), 0, None],
                    ["Exclude", ', '.join(self.getvar('exclude')), 0, None],
                    [None, '(Note) List binary files to be included and text files to be exlcuded.',
                     2, None]]
            tv = evt.GetEventObject()
            tv.OpenPanel(list, self, 'handle_hg_setting',
                         event=evt)

        def handle_hg_setting(self, value, event=None):
            app = wx.GetApp().TopWindow
            try:
                self.setvar('include', [x.strip()
                                        for x in str(value[0]).split(',')])
                self.setvar('exclude', [x.strip()
                                        for x in str(value[1]).split(',')])
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to set include/exclude',
                                     title='Failure',
                                     traceback=traceback.format_exc())

        def hg_projtreeviewer_status(self):
            if self._hg_rev_str is None:
                self.hg_set_projtreeviewer_status()
            return self._hg_rev_str

        def hg_set_projtreeviewer_status(self, repo=None, flag=''):
            print("checking HG", self.owndir())
            if repo is None:
                repo = hgapi.Repo(self.owndir())
            l = self.hg_changesets_list(repo=repo)
            if len(l) == 0:
                self._hg_rev_str = '(rev.-1)'
                return
#           if self.hg_has_uncommitedchange(repo =None):
#              flag = '*'
#           else:
            try:
                self._hg_rev_str = '(rev.'+str(repo.hg_rev()) + \
                    '/'+str(max(l)) + flag+')'
            except:
                import traceback
                traceback.print_exc()
                self._hg_rev_str = '(rev. ???/'+str(max(l)) + flag+')'

        def hg_has_uncommitedchange(self, repo=None):
            if repo is None:
                repo = hgapi.Repo(self.owndir())
            st = repo.hg_status()
            for key in st:
                if len(st[key]) != 0:
                    return True
            return False

        def hg_changesets_list(self, repo=None):
            if repo is None:
                repo = hgapi.Repo(self.owndir())
            lines = repo.hg_log().split('\n')
            return [int(l.split(':')[1]) for l in lines if l.find('changeset') != -1]

        def hg_incoming_outgoing_changesets_list(self, repo=None, url='default'):
            if repo is None:
                repo = hgapi.Repo(self.owndir())
            try:
                lines1 = repo.hg_command('incoming', url).split('\n')
                incoming = [int(l.split(':')[1])
                            for l in lines1 if l.find('changeset') != -1]
            except:
                import traceback
                if 'no changes found' in traceback.format_exc():
                    incoming = []
                else:
                    traceback.print_exc()
                    return [], []
            try:
                lines2 = repo.hg_command('outgoing', url).split('\n')
                outgoing = [int(l.split(':')[1])
                            for l in lines2 if l.find('changeset') != -1]
            except:
                import traceback
                if 'no changes found' in traceback.format_exc():
                    outgoing = []
                else:
                    traceback.print_exc()
                    return incoming, []
            return incoming, outgoing

        def _save_tree_data(self):
            fpath = os.path.join(self.owndir(), ".tree_data_hg")
            try:
                fid = open(fpath, 'wb')
                self.save2(fid)
                fid.close()
                return True
            except IOError as error:
                dprint1('Failed to create current tree data')
                return False

        def set_mercurial_url(self, root, path):
            root = str(root)
            path = str(path)
            url = rootpath2url(root, path)
            self.setvar(r_vname, root)
            self.setvar(p_vname, path)
            return url

        def get_mercurial_url(self):
            root = self.getvar(r_vname)
            path = self.getvar(p_vname)
            if root is None:
                return None, None, None
            url = rootpath2url(root, path)
            return url, root, path

        def get_hg_pathinfo(self):
            url, root, path = self.get_mercurial_url()
            pathdir = '/'.join(path.split('/')[:-1])
            pathbase = path.split('/')[-1]
            return url, root, path, pathdir, pathbase

        def update_hgsub(self):
            res = []
            for name, child in self.get_children():
                try:
                    if has_repo(child):
                        url, root, path = child.get_mercurial_url()
                        if url is None:
                            dlg = wx.MessageDialog(None,
                                                   'Subrepo is not yet cloned. Failed to create .subrepo file',
                                                   'Failed to update .subrepo',
                                                   wx.OK | wx.CANCEL)
                            ret = dlg.ShowModal()
                            dlg.Destroy()
                            return False
                        res.append((name, url, root, path))

                except:
                    pass
            fpath = os.path.join(self.owndir(), '.hgsub')
            if len(res) == 0:
                if os.path.exists(fpath):
                    os.remove(fpath)
            else:
                f = open(fpath, 'wb')
                for name, url, root, path in res:
                    txt = name + ' = ' + url
#                  print txt
                    f.write(txt + '\n')
                f.close()
            return True

        def do_commit(self, m, user='', no_treedata=False):
            if not no_treedata:
                if not self._save_tree_data():
                    return
            app = wx.GetApp().TopWindow
            repo = hgapi.Repo(self.owndir())
            try:
                addfile, rmfile, skipfile, txt = hg_add_no_binary(repo, self.owndir(),
                                                                  include=self.getvar('include'), exclude=self.getvar('exclude'))
                dlg = wx.MessageDialog(None, txt, "HG add/remove", wx.OK)
                ret = dlg.ShowModal()
                dlg.Destroy()

                repo.hg_commit('"'+m+'"', user=user)
            except:
                dialog.showtraceback(parent=app,
                                     txt='Failed to commit changes',
                                     title='Failed to commit',
                                     traceback=traceback.format_exc())
                return False
            return True

        def add_hg_menu(self, menu):
            if self.get_extfolderpath() is not None:
                return menu
            if has_hg:
                if has_repo(self):
                    menu = menu + [('+hg...', None, None),
                                   ('Commit', self.onHGcommit, None),
                                   ('Clone...', self.onHGclone, None),
                                   ('Push...', self.onHGpush, None),
                                   ('Pull...', self.onHGpull, None),
                                   ('Update...', self.onHGupdate, None),
                                   ('+more...', None, None),
                                   ('Revert...', self.onHGrevertall, None),
                                   ('Check Incoming', self.onHGIncoming, None),
                                   ('Check Outgoing', self.onHGOutgoing, None),
                                   ('Diff...', self.onHGDiff, None),
                                   ('Make repo object in Shell...',
                                    self.onHGMakeRepo, None),
                                   ('Setting...', self.onHGSetting, None),
                                   ('Reload Repo', self.onHGreload, None),
                                   ('Delete Repo', self.onHGturnoff, None),
                                   ('!', None, None),
                                   ('!', None, None),
                                   ('---', None, None)]
                else:
                    menu = menu + [('+hg...', None, None),
                                   ('Turn on HG', self.onHGturnon, None),
                                   ('!', None, None),
                                   ('---', None, None)]
            else:
                menu = menu + [('+hg...', None, None),
                               ('-Mercurial is not enabld', None, None),
                               ('!', None, None),
                               ('---', None, None)]
            return menu

    class HGFileSupport(object):
        def add_hg_menu(self, menu):
            if has_hg:
                menu = menu + [('+hg...', None, None),
                               ('Revert', self.onHGcommit, None),
                               ('!', None, None),
                               ('---', None, None)]
            else:
                return menu

        def onHGrevert(self, evt):
            pass

except:
    import traceback
    print(traceback.print_exc())
    has_hg = False

    def has_repo(obj):
        return False
