from __future__ import print_function
#  Name   :treedict
#
#          base class for all model_tree_object
#
from __future__ import print_function
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#         was born sometime around 2012. 04
#         2012. 08 still keeps growing...
#
# *******************************************
#     Copyright(c) 2012- S. Shiraiwa
# *******************************************

import collections
import weakref
import threading
import traceback
import ifigure.utils.cbook as cbook
import sys
import os
import shutil
import tarfile
import time
import wx
import six
import ifigure.utils.pickle_wrapper as pickle
import ifigure
from ifigure.utils.debug import dprint
import ifigure.ifigure_config as ifigure_config
import ifigure.events
import ifigure.widgets.dialog as dialog
import numpy as np
from ifigure.utils.wx3to4 import deref_proxy

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('TreeDict')

td_name_space = {}


def fill_td_name_space(filename):
    try:
        file, co, mtime = cbook.LoadScriptFile(filename)
        exec(co, {}, td_name_space)
    except:
        print('Failed to build script name space')
        print(traceback.format_exc())


def working_dir_exists_message1(path):
    m = 'Working directory already exists. Do you want to delete it to continue?\nwdir = ' + \
        str(path)
    return m


def working_dir_exists_message2(path):
    m = 'Working directory already exists. Do you want to delete it to continue?\nOtherwise, it will use the existing working directory.\nwdir = ' + \
        str(path) + \
        '\n[note: this could happen when project was not closed properly.]'
    return m


class str_td(str):
    def __init__(self, *args, **kargs):
        str.__init__(self)
        self._td = ''

    @property
    def td(self):
        return self._td

    @td.setter
    def td(self, value):
        self._td = value

# this metaclass forces to read class image file for each subclass


class BaseAttr(type):
    def __init__(cls, name, base, d):
        cls._image_load_done = False
        type.__init__(cls, name, base, d)


class TreeDict(object):
    # index number of object commonly used
    # among all classes derived from TreeDict
    __metaclass__ = BaseAttr
    _debug = 0
    _id_base = 0
    _save_var = True
    # _image_load_done=False
    _image_id = [-1]

    def __new__(cls, *args, **kargs):
        obj = object.__new__(cls)
        if not hasattr(cls, '_image_load_done'):
            cls._image_load_done = False
        # subclass's __new__ may be overwritten to implement
        # an extra procees such as the cancelation of object
        # creation. In such case, obj members may be edited
        # in subclass's __new__. Variables which is editable
        # during __new__ should be initialized here.

        # self._var stores generic variable "visible from user"
        # attribute variable
        obj._var = collections.OrderedDict()
        # description for attribute
        obj._note = collections.OrderedDict()

        # nodo variable is mostly
        # for subtree contents
        # if node vairialbe is used, _can_have_child must be
        # false
        obj._var0 = None
        obj._var0_show = False
        obj._name = ''
        obj._parent = None
        obj._nosave_var0 = False
        obj._can_have_child = True
        obj._has_private_owndir = True
        obj._genuine_name = ''     # this is the name shown in tree viewer
        # it is called genuine since when external folder
        # is loaded, this is the name of the file.
        # OTH, _name might be different to keep the project
        # tree structure valid
        # In such case, the object can not be renamed
        # self._d stores children
        obj._d = []
        return obj

    def __init__(self, parent=None, src=None):
        self._id = TreeDict._id_base
        self._name = 'treedict'

        if parent is not None:
            dprint2('treedict::__init__ is called with parent', parent)
        self.set_parent(parent)
        TreeDict._id_base = TreeDict._id_base+1
        self._status = ''
        self._items = []
        self._suppress = False
        # store if it is visible in tree viewer
        self._visible = False
        self._use_custom_image = False
        self._custom_image_load_done = False
        self._image_update = False
        self._custom_image_id = [-1]
        self._name_readonly = False
        self.__initialised = True
        self._save_mode = 0
        self._var_changed = False  # a flag to judge the need of updating var viewer

    def __repr__(self):
        return self.__class__.__name__+'('+self.get_full_path()+')'

    def compact_name(self):
        txt = self.get_full_path()
        if len(txt) < 32:
            return txt
        else:
            names = [x for x in reversed(
                [t._name for t in self.walk_tree_up()])]
            for x in range(len(names)-2):
                names[x+1] = '.'
                if len('.'.join(names)) < 32:
                    return '.'.join(names)
        return self.get_root_parent().name + '....' + self.name

    @classmethod
    def isTreeDict(self):
        return True

    @classmethod
    def isTreeLink(self):
        return False

    @classmethod
    def get_namebase(self):
        return 'treedict'

    @classmethod
    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        return None

    def can_have_child(self, child=None):
        return self._can_have_child

    def get_can_have_child(self):
        return self._can_have_child

    def set_can_have_child(self, value):
        self._can_have_child = value

    def ref(self):
        # this is to get self from weakref proxy object
        # additionally, proxy alive check uses a call
        # to this method....
        return self

    def classimage(self):
        if self._use_custom_image:
            return self.customimage()
        else:
            return self.classimage0()

    def get_classimage(self):
        img = self.classimage()
        if not self._suppress:
            return img[0]
        else:
            return img[1]

    @classmethod
    def classimage0(cls):
        if cls._image_load_done is False:
            cls._image_id = cls.load_classimage()
            cls._image_load_done = True
        return cls._image_id[0]

    def customimage(self):
        if self._custom_image_load_done is False:
            self._custom_image_id = self.load_customimage()
            self._custom_image_load_done = True
        if self._custom_image_id[0] == -1:
            return self.classimage0()
        return self._custom_image_id[0]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'no_icon.png')
        return [idx]

    @classmethod
    def is_movable(self):
        #  [0]: allow to change order under the same parent
        #  [1]: allow to move other place
        return (False, False)

    def destroy(self, clean_owndir=True):
        for name, child in self.get_children():
            child.destroy(clean_owndir=clean_owndir)
        # clean workdir
        if clean_owndir:
            if self._has_private_owndir:
                self.rm_owndir()
            else:
                self.clean_owndir()

        if self._parent is not None:
            self._parent._del_child(self)

        # clean var
        for key in self._var:
            self._var[key] = None

    def __getattr__(self, attr):
      # only attributes not starting with "_" are organinzed
      # in the tree
        if not attr.startswith("_"):
            idx = self.i_child(name=attr)
            if idx != -1:
                return self._d[idx]
            # print "making attr", attr
            # print self._name, self.get_full_path(), attr
            raise AttributeError('Tree member not found :'+attr+':'+str(self))
            # return self._d.setdefault(attr, TreeDict())
        raise AttributeError('Tree name should not start from "_"')

    def __setattr__(self, attr, val):
        if '_TreeDict__initialised' not in self.__dict__:
           #         this test allows attributes to be set in the __init__ method
            return object.__setattr__(self, attr, val)
        elif attr.startswith("_"):
            return object.__setattr__(self, attr, val)
        try:
            if val.isTreeDict():
                self.add_child(attr, val)
        except Exception:
            raise AttributeError("Do not make attribut "+attr)

    def __getstate__(self):
            # for pickling
        return self._d, self._attributes()

    def __getitem__(self, key):
        if self._var0 is not None:
            try:
                return self._var0[key]
            except:
                return self._var0
#           if isinstance(self._var0, collections.Hashable):
#               return self._var0[key]
#           else:
#               return self._var0
        else:
            raise TypeError('Object does not have var0')

    def __setitem__(self, key, value):
        # slicing weakref with [:] gives the 2nd...why?
        if (key == slice(None, None, None) or
                key == slice(0, 2147483647, None)):
            self._var0 = value
            ifigure.events.SendVar0ChangedEvent(self)
        else:
            if self._var0 is None:
                raise KeyError('Object does not have ver0')
            self._var0[key] = value

    def __setstate__(self, tp):
        # for unpickling
        d, l = tp
        self._d = d
        for name, obj in l:
            setattr(self, name, obj)

    def _process_kywd(self, kywds, key, defv):
        #        print 'in', kywds
        if key in kywds:
            self.setvar(key, kywds[key])
            del kywds[key]
        else:
            self.setvar(key, defv)
#        print 'out', kywds
        return kywds

    def _process_kywd2(self, kywds, key, defv):
        #        print 'in', kywds
        if key in kywds:
            val = kywds[key]
            del kywds[key]
        else:
            val = defv
#        print 'out', kywds
        return kywds, val

    def list_all(self):
        # easy to read string representation of data
        # print "generating string"
        rl = []
        
        from six import iteritems        
        for k, v in iteritems(self._getLeaves()):
            rl.append("%s = %s" % (k, v.__repr__()))
   #        return "\n".join(rl)
        return rl

    def _getLeaves(self, prefix=""):
        # getLeaves tree, starting with self
        # prefix stores name of tree node above
        prefix = prefix and prefix + "."
        rv = {}
        atl = self.get_childnames()
        for at in atl:
            ob = self.get_child(name=at)
            trv = ob._getLeaves(prefix+at)
            rv.update(trv)

        for at, ob in self._attributes():
            rv[prefix+at] = ob
        return rv

    def _attributes(self):
        # return 'lenaves' of the data tree
        # return self._d.items()
        return [(s._name, s) for s in self._d]
    #
    #  access routine to children
    #

    def get_childnames(self):
        names = []
        for child in self._d:
            names.append(child._name)
        return names

    def has_child(self, name):
        return self.get_childnames().count(name) != 0

    def get_children(self):
        return self._attributes()

    def num_child(self):
        return len(self._d)

    def get_ichild(self):
        i = self._parent.i_child(self)
        return i

    def i_child(self, obj=None, name=None):
        if name is not None:
            keys = self.get_childnames()
            if keys.count(name) == 0:
                return -1
            return keys.index(name)
        if obj is not None:
            #c = self._d.count(obj)
            #if c == 0:
            #    return -1
            try:
                idx = self._d.index(obj)
                return idx
            except ValueError:
                return -1
            #return idx
        return -1
    
    def get_child(self, idx=None, name=None):
        if idx is not None:
            if len(self._d) > idx > -1:
                return self._d[idx]
            else:
                return None
        if name is not None:
            names = self.get_childnames()
            c = names.count(name)
            if c == 0:
                return None
            idx = names.index(name)
            return self._d[idx]
        return None

    def get_first_child(self):
        return self.get_child(0)

    def get_last_child(self):
        return self.get_child(self.num_child()-1)

    def get_next_child(self, child):
        try:
            return self._d[self._d.index(child)]
        except:
            return None
#        idx = self.i_child(child)
#        if idx == -1 : return None
#        return self.get_child(idx+1)

    def get_prev_child(self, child):
        idx = self.i_child(child)
        if idx == -1:
            return None
        if idx == 0:
            return None
        return self.get_child(idx-1)

    def get_depth(self):
        n = 0
        p = self
        while p is not None:
            p = p.get_parent()
            n = n+1
        return n

    def isdescendant(self, kid):
        p = kid
        while p is not None:
            if self == p:
                return True
            p = p.get_parent()
        return False

    def get_relative_path(self, td):
        dprint1('get_relative_path is going to be obsolete, consider get_td_path')
        # find common parent
        k = 0
        p = self
        while p is not None:
            if p.isdescendant(td):
                break
            p = p.get_parent()
            k = k + 1
#        print 'common parent', p.get_full_path()
        a = [i for i in reversed([t._name for t in td.walk_tree_up()])]
        b = [i for i in reversed([t._name for t in p.walk_tree_up()])]
        return [".."]*k + a[len(b):]

    def get_td_path(self, td, fullpath=False):
        if fullpath:
            return td.get_full_path().split('.')
        # find common parent
        k = 0
        p = self
        while p is not None:
            if p.isdescendant(td):
                break
            p = p.get_parent()
            k = k + 1
#        print 'common parent', p.get_full_path()
        a = [i for i in reversed([t._name for t in td.walk_tree_up()])]
        b = [i for i in reversed([t._name for t in p.walk_tree_up()])]
        return ['.']+[".."]*k + a[len(b):]

    def resolve_td_path(self, path):
        # path = [".", "..","..", someting]
        # path = ["..","..", someting]
        if path[0] == '.':
            p = self
        else:
            p = self.get_root_parent()
        p2 = path[1:]

        for name in p2:
            if name == '..':
                p = p.get_parent()
            else:
                p = p.get_child(name=name)
        return p

    def _del_child(self, obj=None, idx=None, name=None):
        #
        #  this is not a fuction to be called directly.
        #  use destroy instead. it does not delete object
        #  instead unregister it from children list
        #
        if obj is not None:
            idx = self.i_child(obj=obj)
            if idx == -1:
                return
        elif name is not None:
            idx = self.i_child(name=name)
            if idx == -1:
                return

        self._d[idx].set_parent(None)
        del self._d[idx]

    def add_child(self, *args, **kargs):
        '''
           add_child(name, obj)
           add_child(obj) : name is not changed
           check potential conflict of method and child name
        '''
        from ifigure.utils.cbook import is_safename

        def name_check(newname, warning):
            fpath = self.get_full_path()+'.'+newname
            do_rename = False
            newname = '_'.join(newname.split(' '))
            if '.' in newname:
                newname = newname.split('.')[0]
                if not is_safename(newname):
                    warning.append(fpath + 'is skipped.')
                    return False, newname, do_rename
            if not is_safename(newname):
                if is_safename('renamed_'+newname):
                    newname = 'renamed_'+newname
                    do_rename = True
                    warning.append(fpath + 'is renamed in Tree.')
                else:
                    warning.append(fpath + 'is skipped.')
                    return False, newname, do_rename
            if newname.startswith('_'):
                newname = 'renamed_'+newname
                do_rename = True
                warning.append(fpath + 'is renamed in Tree.')
            return True, newname, do_rename

        print_warn = True if 'warning' in kargs else False
        warning = kargs.pop('warning', [])

        if len(args) == 2:
            name = str(args[0])  # avoid unicode name...
            obj = args[1]
        elif len(args) == 1:
            obj = args[0]
            name = obj.name
        if obj is not None:
            bname = name
            i = 0
            conflict = False
            if bname == '__pycache__':
                #print('skipping ' + bname)
                return
            flag, bname1, do_rename = name_check(bname, warning)
            if not flag:
                print('can not add '+name)
                return
            while hasattr(self, bname1):
                conflict = True
                warning.append(self.get_full_path() +
                               ' already has attr ' + bname1)
                bname1 = bname1 + str(i)
                i = i+1
            obj._genuine_name = bname
            obj.set_parent(self)     # this could raise error so do first
            self._d.append(obj)
            if self.is_suppress():
                obj.set_suppress(self.is_suppress())
            obj._name = bname1

            if conflict:
                warning[-1] = warning[-1]+'. Renamed to ' + bname

            #if print_warn: print('\n'.join(warning))
            return len(self._d)-1  # == self.i_child(obj)

        print("Empty object can not be added")

    def move(self, new_parent, keep_zorder=False):
        '''
        def move(self, new_parent, keep_zorder=False)
        move object under a new parent'
        '''
        p = self.get_parent()
        odir = self.owndir()
        if p is None:
            return
        p._del_child(obj=self)

        name = self.name
        if new_parent.get_childnames().count(name) != 0:
            name = new_parent.get_next_name(name)
        new_parent.add_child(name, self, keep_zorder=keep_zorder)

        ndir = self.owndir()
        if self._has_private_owndir:
            #        if self._can_have_child:
            #            dprint1('moving ', odir, ndir)
            if os.path.exists(odir):
                if not self.has_owndir():
                    self.mk_owndir()
                os.rename(odir, ndir)
#                shutil.move(odir, ndir)
        else:
            for item in set(self.ownitem()):
                shutil.move(os.path.join(odir, item),
                            os.path.join(ndir, item))

    def move_child(self, idx, idx2):
        if idx == idx2:
            # do nothing
            return
        item = self._d
        item = cbook.MoveItemInList(item, idx, idx2)
        self._d = item

    def find_by_id(self, id):
        root = self.get_root_parent()
        for obj in root.walk_tree():
            if obj.id == id:
                return obj
        return None

    def find_by_full_path(self, name):
        a = name.split('.')
        root = self.get_root_parent()
        if a[0] != root.name:
            return None
        p = root
        for name in a[1:]:
            p = p.get_child(name=name)
            if p is None:
                print(('can not find', name))
                return None
        return p

    def expand_path(self, name):
        '''
           expand path string like 'proj.model.*.scripts'
           and returns list of treedict
        '''
        a = name.split('.')
        root = self.get_root_parent()
        if a[0] != root.name:
            return []
        arr = [root]
        for name in a[1:]:
            arr2 = []
            for k, p in enumerate(arr):
                if name == '*':
                    arr2.extend(list(zip(*p.get_children())[1]))
                else:
                    p = p.get_child(name=name)
                    if p is not None:
                        arr2.append(p)
            arr = arr2
        return arr

    def set_parent(self, parent):
        self._parent = parent

    def get_parent(self):
        return self._parent

    def get_app(self):
        root = self.get_root_parent()
        app = root.app if hasattr(root, 'app') else None
        app = deref_proxy(app)
        return app

    def get_root_parent(self):
        if self.get_parent() is None:
            return self
        else:
            return (self.get_parent()).get_root_parent()

    def get_grand_parent(self):
        # return the parent of parent
        p = self.get_parent()
        if p is None:
            return None
        return p.get_parent()

    def get_full_path(self):
        names = reversed([t._name for t in self.walk_tree_up()])
        return '.'.join(names)
#        return self._do_get_full_path('')

    def _do_get_full_path(self, base):
        if base == '':
            base = self._name
        else:
            base = self._name+'.'+base
        if self._parent is not None:
            base = self._parent._do_get_full_path(base)
        return base

    def walk_tree(self, stop_at_ext=False):
        '''
        generator to wolk through tree
        '''
        from ifigure.mto.py_extfile import ExtMixIn
        yield self
        if stop_at_ext and isinstance(self, ExtMixIn):
            return
#       child=self.get_first_child()
        if len(self._d) == 0:
            return
        child = self._d[0]
        k = 0
        while child is not None:
            for x in child.walk_tree(stop_at_ext=stop_at_ext):
                yield x
#           child=self.get_next_child(child)
            k = k+1
            if len(self._d) == k:
                break
            child = self._d[k]

    def walk_tree_rev(self):
        '''
        generator to wolk through tree (reversed)
        '''
        child = self.get_last_child()
        while child is not None:
            for x in child.walk_tree_rev():
                yield x
            child = self.get_prev_child(child)
        yield self

    def walk_tree_up(self, cond=True):
        ''' 
        generator to walk tree upward from
        self. if cond is given, generator
        stops when the condition is satisefied.
        cond should  takes arguments, to which
        self is 
        '''
        k = cond
        if callable(cond):
            k = cond(self)
        if k:
            yield self
            if self.get_parent() is not None:
                for x in self.get_parent().walk_tree_up(cond=cond):
                    yield x

    def walk_tree_down(self, cond=True, top=None):
        ''' 
        generator to walk tree downward from
        top to self. if cond is given, generator
        stops when the condition is satisefied
        '''
        tmp = []
        for obj in self.walk_tree_up(cond=cond):
            tmp.append(obj)
            if tmp is top:
                break

        tmp2 = reversed(tmp)
        for item in tmp2:
            yield item

    def is_descendant(self, kid):
      # ture if kid is self's offspring
        p = kid.get_parent()
        while p is not None:
            if self == p:
                return True
            p = p.get_parent()
        return False

    def is_ascendant(self, parent):
        return parent.is_descendant(self)

    def find_common_parent(self, td_list):
        p = self
        while p is not None:
            flag = True
            for t in td_list:
                if t is None:
                    return self.get_root_parent()
                if p is t:
                    break
                if not p.is_descendant(t):
                    flag = False
                    break
            if flag:
                return p
            p = p.get_parent()
        return p
   #
   #   Variable/Note Setter and Getter
   #

    def get_varlist(self):
        return list(self._var)

    def hasvar(self, name):
        return name in self._var

    def setvar(self, *args):
        #       print self, args
        self._var_changed = True
        if len(args) == 2:
            self._var[args[0]] = args[1]
        if len(args) == 1:
            if isinstance(args[0], dict):
                self._var = args[0]

    def dynamic_names(self):
        return [key for key in self._var
                if cbook.isdynamic(self._var[key])]

    def eval(self, *args, **kargs):
        '''
        eval values in _var
        eval("x")  = evaluate "x"
        eval("x", "y", "z") = evaluate "x", "y", "z"
        eval() = return self._var0
        '''
        if 'np' in kargs:
            np = kargs['np']
        else:
            np = False
        if len(args) == 1:
            return self._eval(args[0], use_np=np)
        if len(args) == 0:
            return self._eval()
        return (self._eval(name, use_np=np) for name in args)

    def get_pyfolder(self):
        from ifigure.mto.py_code import PyFolder
        p = self
        while p is not None:
            if isinstance(p, PyFolder):
                return p
            p = p.get_parent()
        return None

    def get_pymodel(self):
        from ifigure.mto.py_code import PyModel
        p = self
        while p is not None:
            if isinstance(p, PyModel):
                return p
            p = p.get_parent()
        return None

    def get_figbook(self):
        from ifigure.mto.fig_book import FigBook
        p = self
        while p is not None:
            if isinstance(p, FigBook):
                return p
            p = p.get_parent()
        return None

    def get_figpage(self):
        from ifigure.mto.fig_page import FigPage
        p = self
        while p is not None:
            if isinstance(p, FigPage):
                return p
            p = p.get_parent()
        return None

    def get_figaxes(self):
        from ifigure.mto.fig_axes import FigAxes
        p = self
        while p is not None:
            if isinstance(p, FigAxes):
                return p
            p = p.get_parent()
        return None

    def get_variables(self):
        from ifigure.mto.py_code import AbsNamespacePointer
        p = self
        while p is not None:
            if isinstance(p, AbsNamespacePointer):
                return p
            p = p.get_parent()
        return None

    def get_namespace(self):
        p = self.get_variables()
        if p is None:
            return {}
        if p.has_ns():
            return p.get_ns()._var
        else:
            return {}

    def get_extfolderpath(self):
        from ifigure.mto.py_code import AbsFileContainer
        p = self
        namelist = []
        while p is not None:
            if isinstance(p, AbsFileContainer):
                if p.getvar('ext_folder') is not None:
                    namelist.append(p.getvar('ext_folder'))
                    return os.path.join(*list(reversed(namelist)))
                namelist.append(p._genuine_name)
            p = p.get_parent()

    def get_extfolderpathfolder(self):
        from ifigure.mto.py_code import AbsFileContainer
        p = self
        namelist = []
        while p is not None:
            if isinstance(p, AbsFileContainer):
                if p.getvar('ext_folder') is not None:
                    return p
            p = p.get_parent()

    def _eval(self, name='', use_np=False):
        try:
            root = self.get_root_parent()
            lc = {key: td_name_space[key] for key in td_name_space}
            lc[root.name] = root
            m = self.get_pymodel()
            if m is not None:
                lc['model'] = m
            if m is not None:
                lc['param'] = m.param
            m = self.get_figpage()
            if m is not None:
                lc['page'] = m
            m = self.get_figbook()
            if m is not None:
                lc['book'] = m

            if six.PY2 and isinstance(self._var[name], unicode):
                if self._var[name].startswith(u'='):
                    self._var[name] = str(self._var[name])
            if isinstance(self._var[name], str):
                if name == '':
                    value = self._var0
                    return self._var0
                if cbook.isdynamic(self._var[name]):
                    value = eval((self._var[name])[1:], lc, lc)
#                  value = eval()
                    if use_np and not isinstance(value, np.ndarray):
                        if value is None:
                            return None
                        if hasattr(value, '__iter__'):
                            value = np.array(value)
                            if value.ndim == 0:
                                return None
                            return value
                        else:
                            return value
                    return value
                return self._var[name]
            value = self._var[name]
            if use_np and not isinstance(value, np.ndarray):
                if value is None:
                    return None
                if hasattr(value, '__iter__'):
                    value = np.array(value)
                    if value.ndim == 0:
                        return None
                    return value
                else:
                    return value
            return value
        except Exception:
            print(sys.exc_info())
#          pass
        return None

    def getvar(self, *args):
        if len(args) == 0:
            return self._var
        try:
            if len(args) == 1:
                return self._var[args[0]]
            else:
                return tuple([(self._var[name] if name in self._var else None) for name in args])
        except KeyError:
            if len(args) == 1:
                return None
            return [None]*len(args)

    def getvar_copy(self):
        var = self.getvar()
        d = collections.OrderedDict()
        for key in var:
            d[key] = var[key]
        return d

    def compare_vars(self, td):
        """
        compare vars stored in two tree dicts
        """
        print(("comparing", self.get_full_path(), td.get_full_path()))
        diff = cbook.DictDiffer(self.getvar(), td.getvar())

    def setnote(self, *args):
        '''
        setnote('xxx', 'xxx is yyy')
        '''
        if len(args) == 2:
            try:
                a = self._var[args[0]]
            except KeyError:
                print(("!!!", self.get_full_path(), " does not have ", name))
                return
            self._note[args[0]] = args[1]
        if len(args) == 1:
            self._note = args[0]

    def getnote(self, name=None):
        if name is None:
            return self._note
        try:
            return self._note[name]
        except KeyError:
            return ''

    def delvar(self, name):
        try:
            del self._var[name]
        except KeyError:
            pass
        try:
            del self._note[name]
        except KeyError:
            pass

    #
    #   methods relating to var0
    #
    def setvar0(self, value):
        self._var0 = value
        ifigure.events.SendVar0ChangedEvent(self)

    def getvar0(self): return self[:]

    def get_contents(self, *args, **kargs):
        from ifigure.mto.py_contents import PyContents
        if not isinstance(self._var0, PyContents):
            return None
        contents = self._var0
        for key in args:
            contents = contents[key]
        if hasattr(contents, 'eval'):
            return contents.eval(self, **kargs)
        return contents

    def set_contents(self, *args):
        from ifigure.mto.py_contents import PyContents
        if not isinstance(self._var0, PyContents):
            return None
        contents = self._var0
        if len(args) > 2:
            for key in args[:-2]:
                contents = contents[key]
        contents[args[-2]] = args[-1]

    def get_drag_text2(self, key):
        ''' 
        text for dnd from var viewer
        '''
        return self.get_full_path()+'.eval("'+key+'")'

    #
    #  suppress
    #
    def set_suppress(self, val):
        p = self.get_parent()
        if p is None:
            return
        if (p.is_suppress() and val == False):
            print('parent object is suppressed, can not unsuppress the object')
            return
        self._suppress = val
        self._image_update = False
        for name, child in self.get_children():
            child.set_suppress(val)

    def is_suppress(self):
        return self._suppress

    @property
    def isSuppressed(self):
        return self._suppress

    #
    #  visibility in tree viewer
    #
    def set_visible(self, val):
        self._visible = val

    def is_visible(self):
        return self._visible

    #
    #   menu in tree viewer
    #
    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        if not wx.GetApp().TopWindow.appearanceconfig.setting['show_suppress_menu']:
            menu = []
        else:
            if self._suppress:
                menu = [('-Suppress',   self.onSuppress, None),
                        ('Unsuppress', self.onUnSuppress, None),
                        ('Delete...', self.onDelete, None)]
            else:
                menu = [('Suppress',   self.onSuppress, None),
                        ('-Unsuppress', self.onUnSuppress, None),
                        ('Delete...', self.onDelete, None)]

        if self._name_readonly:
            menu.append(('-Rename...', self.onRename, None))
        else:
            menu.append(('Rename...', self.onRename, None))
        from ifigure.mto.py_extfile import ExtMixIn
        if not isinstance(self, ExtMixIn):
            from ifigure.mto.hg_support import has_hg
            if self.can_have_child():
                menu.append(('+Import Subtree', None, None))
                mm = [('From File...', self.onLoadSubTree, None), ]
                if has_hg:
                    mm.append(('From Repository...', self.onLoadSubTreeHG,
                               None))
                if hasattr(self, 'onAddExtFolder'):
                    mm.append(('From Folder...', self.onAddExtFolder, None))
                menu.extend(mm)
                menu.append(('!', None, None))
                if (self.hasvar('subtree_path') and
                        os.path.exists(self.getvar('subtree_path'))):
                    menu.append(('Export Subtree', self.onSaveSubTree, None))
                else:
                    menu.append(('-Export Subtree', None, None))
                menu.append(('+Export As...', None, None))
                menu.append(('Subtree...', self.onSaveSubTreeAs, None))
                if self.has_owndir():
                    menu.append(('Files...', self.onExportFiles, None))
                menu.append(('!', None, None))
            else:
                if (self.hasvar('subtree_path') and
                        os.path.exists(self.getvar('subtree_path'))):
                    menu.append(
                        ('Export '+self._name, self.onSaveSubTree, None))
                else:
                    menu.append(('-Export '+self._name, None, None))
                menu.append(('Export '+self._name + ' As...',
                             self.onSaveSubTreeAs, None))

        from ifigure.mto.py_code import PyFolder

        if self.can_have_child(PyFolder()):
            if isinstance(self, ExtMixIn):
                menu.append(
                    ('Reload File Tree...', self.onReloadExtTree, None))
                menu.append(
                    ('Change Dir. to here', self.onChangeDirToExt, None))
            menu.append(('New Folder...', self.onAddFolder, None))
        return menu

    def onDelete(self, event):
        self.destroy()
        event.Skip()

    def onSuppress(self, event):
        self.set_suppress(True)
        event.Skip()

    def onUnSuppress(self, event):
        self.set_suppress(False)
        event.Skip()

    def dlg_ask_newname(self):
        app = self.get_app()
        ret, new_name = dialog.textentry(app,
                                         "Enter a new name", "Rename...", self.name)
        if ret:
            p = self.get_parent()
            if p is not None:
                if hasattr(p, new_name):
                    ret = dialog.message(app,
                                         'attribute name (' + new_name +
                                         ') is already used',
                                         'Name Conflict',
                                         0)
                    return None
                if new_name == 'tmp':
                    ret = dialog.message(app,
                                         'attribute name (' +
                                         new_name + ') is reserved',
                                         'Reserved Name',
                                         0)
                    return None
            return new_name

    def onRename(self, event):
        new_name = self.dlg_ask_newname()
        if new_name is not None:
            flag = self.rename(new_name)
            ifigure.events.SendChangedEvent(self)

    def onSaveSubTree(self, e):
        if (self.hasvar('subtree_path') and
                os.path.exists(self.getvar('subtree_path'))):
            path = self.getvar('subtree_path')
            print('exporting subtree to '+path)
            self.save_subtree(path)
        else:
            self.onSaveSubTreeAs(e)

    def onSaveSubTreeAs(self, e):
        path = dialog.write(defaultfile=self.name+'.pfs',
                            wildcard='*.pfs')
        if path == '':
            return
        if path[-4:] != '.pfs':
            path = path+'.pfs'
        print('exporting subtree to '+path)
        self.save_subtree(path)
        self.setvar('subtree_path', path)

    def onExportFiles(self, e):
        path = dialog.writedir(parent=e.GetEventObject(),
                               message='Select directory to save files',)

        if path == '':
            return
        path = os.path.join(path, self._name)
        print('exporting files to '+path)
        import shutil
        shutil.copytree(self.owndir(), path)

    def onLoadSubTree(self, e):
        path = dialog.read(wildcard='*.pfs')
        if path == '':
            return
        child = self.load_subtree(path)
        if child is not None:
            child.setvar('subtree_path', path)
        e.Skip()

    def onLoadSubTreeHG(self, e):
        from ifigure.mto.hg_support import load_subtree_hg
        load_subtree_hg(self)
        e.Skip()

    def onAddFolder(self, event=None, name=''):
        from ifigure.mto.py_code import PyFolder
        app = self.get_app()
        if name == '':
            ret, new_name = dialog.textentry(app,
                                             "Enter Foler Name", "Add Folder...", 'folder')
        else:
            ret = True
            new_name = name
        if ret:
            if self.has_child(new_name):
                ret = dialog.message(app,
                                     new_name + ' is already used',
                                     'Name Conflict',
                                     0)
                return
            obj = PyFolder()
            self.add_child(new_name, obj, keep_zorder=True)
        ifigure.events.SendChangedEvent(self)

    #
    #  utilitiy to add child object
    #
    def add_childobject(self, cls, name, *args, **kargs):
        if self.has_child(name):
            name = self.get_next_name(name)
        try:
            obj = cls(*args, **kargs)
            idx = self.add_child(name, obj, keep_zorder=True)
            o = self.get_child(name=name)
            if o is not None:
                return o
            return self.get_child(idx=idx)
        except:
            import traceback
            traceback.print_exc()
            return

    #
    #   get_new_name
    #
    def get_next_name(self, header):
        keys = self.get_childnames()
        return cbook.GetNextName(keys, header)

    #
    #   rename
    #
    def is_renamable(self):
        return self._name_readonly

    def set_namereadonly(self,  value=True):
        self._name_readonly = value

    def rename(self, new, ignore_name_readonly=False):
        # rename tree object

        # this routine does..
        #   1) check name conflict in tree
        #   2) check owndir conflict

        #
        # root can not be renamed
        from ifigure.utils.cbook import is_safename
        if self._name_readonly and not ignore_name_readonly:
            raise AttributeError("Name read only :" + self.__repr__())
        if not is_safename(new):
            dprint1(new + ' can not be used as variable name')
            return False
        if self._name == new:
            return True
        if self.get_parent() is None:
            return False
        if hasattr(self.get_parent(), new):
            print(self.get_parent().get_full_path() + ' already has attr ' + new)
            return False
        if self._name != self._genuine_name:
            dprint1('Cannot rename since object has different screen name')
            return False

        keys = self.get_parent().get_childnames()
        if keys.count(new) != 0:
            print(' name is already used')
            return False

        rename_owndir = False
        if self.has_owndir():
            od = self.owndir()
            rename_owndir = True
        old = self._name
        self._name = new
        self._genuine_name = new
        ifigure.events.SendSimpleTDEvent(None, td=self, w=None,
                                         useProcessEvent=False,
                                         code='Rename')

        if (self.has_owndir() and  # self._can_have_child
                self._has_private_owndir):
            print(' name seems to be used in the past')
            print(' delete ' + self.has_owndir() + ' manually')
            self._name = old
            return False
        if (rename_owndir and
                self._has_private_owndir):
            #            self._can_have_child):
            os.rename(od, self.owndir())
        return True

    #
    #   own directory....
    #
    def mk_owndir(self):
        if self.has_owndir():
            return
#        if not self._can_have_child:
        if not self._has_private_owndir:
            self._parent.mk_owndir()
            return
        path = self.get_root_parent().getvar("wdir")
        l = self.get_full_path().split('.')
#        if len(l) < 2: return
#        for item in l[1:]:
        for item in l:
            path = os.path.join(path, item)
            if not os.path.exists(path):
                os.mkdir(path)

    def rm_owndir(self):
        #        if not self._can_have_child:return
        if not self._has_private_owndir:
            return
        if self.has_owndir():
            try:
                shutil.rmtree(self.owndir())
            except Exception:
                pass

    def rm(self, file):
        '''
        remove a file in owndir
        '''
        try:
            #            if self.owndir() is None: return
            #            if file is None: return
            if os.path.exists(os.path.join(self.owndir(), file)):
                os.remove(os.path.join(self.owndir(), file))
                ifigure.events.SendFileSystemChangedEvent(self)
        except Exception:
            import traceback
            traceback.print_exc()

    def clean_owndir(self):
        def rmgeneric(path, __func__):
            try:
                __func__(path)
            except OSError:
                print(('Remove error', path))

        def removeall(path):
            if not os.path.isdir(path):
                return
            files = os.listdir(path)
            for x in files:
                fullpath = os.path.join(path, x)
                if os.path.isdir(fullpath):
                    removeall(fullpath)
                    f = os.rmdir
                    rmgeneric(fullpath, f)
                elif os.path.isfile(fullpath):
                    f = os.remove
                    rmgeneric(fullpath, f)

#       if self._can_have_child:
        ifigure.events.SendFileSystemChangedEvent(self)

        if self._has_private_owndir:
            removeall(self.owndir())
        else:
            for item in self.ownitem():
                path = os.path.join(self.owndir(), item)
                if not os.path.exists(path):
                    continue
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

    def owndir(self):
        from ifigure.ifigure_config import rcdir
        wdir = self.get_root_parent().getvar("wdir")
        if self.get_root_parent().getvar("wdir") is None:
            return os.path.join(rcdir, 'Should not exist')
        l = self.get_full_path().split('.')
        if self._has_private_owndir:
            #        if self._can_have_child:
            l2 = [wdir]+l
        else:
            l2 = [wdir]+l[:-1]
        return os.path.join(*l2)

    def has_owndir(self):
        return os.path.exists(self.owndir())

    def ls_owndir(self):
        if not self.has_owndir():
            self.mk_owndir()
        return os.listdir(self.owndir())

    def lsl_owndir(self, command='ls -l'):
        '''
        works only on unix
        '''
        import subprocess as sp
        if not self.has_owndir():
            self.mk_owndir()
        d = os.getcwd()
        print(sp.Popen(command, stdout=sp.PIPE, shell=True).stdout.read())
        os.chdir(d)
    #
    #  write2shell : write variable to shell
    #

    def write2shell(self, value, name):
        '''
        write variable to shell
        '''
        root = self.get_root_parent()
        if not hasattr(root, 'app'):
            return
        if root.app is None:
            return
        flag = True if name in root.app.shell.lvar else False
        root.app.shell.lvar[name] = value
#        txt = 'Data exported as ' + name
#        root.app.shell.push('print %r' % txt, silent = True)
        return flag

    #
    #  save/load
    #     save and load are entry point, actual
    #     save/load action depndent on derived
    #     class is implemented in _do_***_data
    #
    #     note: format version
    #        1: old format, each class can write multiple
    #           pickle data.
    #        2: save_data2/load_data2
    #             save_data2 returns a dictionary to
    #             be pickled once.
    #           each object always does two pickle actions
    #           one for header, the other for data
    #           probably easier to extend.

    def save(self, fid=None, olist=None):
        return self.save2(fid, olist)

    def save_data(self, fid=None):
        h2 = {}
        pickle.dump(h2, fid)

    def save2(self, fid=None, olist=None):
        if olist is None:
            olist = []

        h2 = {"name": self.__class__.__name__,
              "module": self.__class__.__module__,
              "num_child": self.num_child(),
              "sname": self.name,
              "id": self.id,
              "var0": self._var0,
              "note": self._note,
              "format": 2}
        if self._save_var:
            h2["var"] = self._var
#        print h2
        if self._nosave_var0:
            h2["var0"] = None
        if fid is not None:
            pickle.dump(h2, fid)
        c = olist.count(self.id)
        if c == 0:
            data = self.save_data2({})
            pickle.dump(data, fid)
            olist.append(self.id)
        else:
            pass

        for name, child in self.get_children():
            olist = child.save2(fid, olist)
        return olist

    def save_data2(self, data=None):
        # first data is version, each class file can
        # define version
        if data is None:
            data = {}
        param = {'_status': self._status,
                 '_items':  [x for x in set(self._items)],
                 '_can_have_child':  self._can_have_child,
                 '_has_private_owndir':  self._has_private_owndir,
                 '_suppress':  self._suppress,
                 '_name_readonly':  self._name_readonly,
                 '_genuine_name': self._genuine_name, }
        data['TreeDict'] = (1, param)
        if not self.check_ownitem_exists():
            print("incomplete own items" + str(self))
        return data

    def load(self, fid, olist=None, nlist=None,
             parent=None, keep_zorder=False):
        #
        #  loading from file is a bit triky,
        #  since it appears that you need to have
        #  an object made before loading. Actually,
        #  this routine read contents in file and
        #  put it into a new object. It returns
        #  the new object and self itself will be
        #  discard in the caller.
        #
        if olist is None:
            olist = []
        if nlist is None:
            nlist = []

        try:
            h2 = pickle.load(fid)
        except:
            import traceback
            traceback.print_exc()
            traceback.print_stack()
            return None, olist, nlist

        c = olist.count(h2["id"])
        if c == 0:
            mod = __import__(h2["module"])
            md = sys.modules[h2["module"]]
            the_class = getattr(md, h2["name"])

            # print "loading ", the_class
            obj = the_class(src=fid)
            obj._name = h2["sname"]
            obj._var0 = h2["var0"]
#           if isinstance(obj._var0, PyContents):
#               obj._var0.set_td(obj)
            if "var" in h2:
                for key in h2["var"]:
                    obj._var[key] = h2["var"][key]
            obj._note = h2["note"]
            if 'format' in h2:
                dprint2('Fileformat ', h2["format"])
                if h2["format"] == 1:
                    obj.load_data(fid)
                else:
                    try:
                        data = pickle.load(fid)
                        obj.load_data2(data)
                    except:
                        import traceback
                        traceback.print_exc()
            else:
                obj.load_data(fid)

            olist.append(h2["id"])
            nlist.append(obj.id)
        else:
            idx = olist.index(h2["id"])
            raise ValueError("Treedata is entangled...!?")
            # obj=parent.find_child(id=nlist[idx])

        for i in range(0, h2["num_child"]):
            try:
                child, olist, nlist = TreeDict().load(fid,
                                                      olist=olist, nlist=nlist,
                                                      parent=obj, keep_zorder=keep_zorder)
            except:
                import traceback
                traceback.print_exc()
                #print('File broken !!!!!')
                break

            if child is not None:
                obj.add_child(child, keep_zorder=keep_zorder)
#            if child._name == 'book7': break
#        print 'returning', obj
        return obj, olist, nlist

    def load_data(self, fid=None):
        h2 = pickle.load(fid)

    def load_data2(self, data):
        if not "TreeDict" in data:
            return
        d = data["TreeDict"]
        if len(d) > 1:
            ### this is a ugly patch to fix a bug once exists ###
            if '_items' in d[1]:
                d[1]['_items'] = [x for x in set(d[1]['_items'])]
            ###
            for key in d[1]:
                setattr(self, key, d[1][key])

    def remove_ownitem(self, items=None):
        items = self.ownitem(items)
        for item in items:
            self.rm(item)

    def check_ownitems(self):
        for obj in self.walk_tree():
            for item in obj.ownitem():
                fpath = os.path.join(obj.owndir(), item)
                if not os.path.exists(fpath):
                    print("not found :" + fpath)

    def check_ownitem_exists(self):
        for item in self.ownitem():
            fpath = os.path.join(self.owndir(), item)
            if not os.path.exists(fpath):
                return False
        return True

    def init_after_load(self, olist, nlist):
        pass

    def resolve_olist_nlist_map(self, oid, olist, nlist):
        if olist.count(oid) == 0:
            return None
        idx = olist.index(oid)
        nid = nlist[idx]
        obj = self.find_by_id(nid)
        if obj is not None:
            return weakref.proxy(obj)
        return None

    def copy_tree(self, fid):
        self.save(fid)

    def paste_tree(self, fid):
        obj, ol, nl = TreeDict().load(fid)
        name = obj.get_next_name(obj.get_namebase())
        if obj.name != name:
            print(("renaming object name", obj.name, "->", name))
        self.add_child(name, obj)
        return obj, ol, nl

    def duplicate(self, new_parent, new_name='', save_script_link=False,
                  ignore_name_readonly=True):
        '''
        duplicate self under a new parent with new_name
        duplicate(self, new_parent, new_name, save_script_link=False)
        '''
        from ifigure.ifigure_config import st_scratch
        from ifigure.mto.py_script import PyScript

        name = threading.current_thread().name
        if new_name == '':
            new_name = self.name
#        sc = st_scratch + '_' + str(os.getpid()) + name
        sc = os.path.join(self.get_root_parent().getvar('wdir'),
                          '.duplicate_sc_'+name)

        if save_script_link:
            scripts = [obj for obj in self.walk_tree()
                       if isinstance(obj, PyScript)]
            for s in scripts:
                s._save_link = True
        flag, tmpdir = self.save_subtree(sc, maketar=False)
        if save_script_link:
            for s in scripts:
                s._save_link = False

        child = new_parent.load_subtree(tmpdir, usetar=False)  # st_scratch)
        if child.name != new_name:
            child.rename(new_name, ignore_name_readonly=ignore_name_readonly)

    # utilities to load/save subtree from/to file
    def save_subtree(self, filename, compress=False, maketar=True):
            # save data to temporary directory
        dname = '.###_'+os.path.basename(filename)
        tmpdir = os.path.join(os.path.dirname(filename), dname)
        if os.path.exists(tmpdir):
            m = working_dir_exists_message1(str(tmpdir))
            ret = dialog.message(None,
                                 m,
                                 'Working Directory already exists.',
                                 2)
            if ret == 'ok':
                shutil.rmtree(tmpdir)
            else:
                return False
        os.mkdir(tmpdir)
        if self.has_owndir() and self.get_extfolderpath() is None:
            if self._has_private_owndir:
                #            if self._can_have_child:
                dd = os.path.join(tmpdir, self.name)
                if os.path.exists(dd):
                    shutil.rmtree(dd)
                shutil.copytree(self.owndir(), dd)
            else:
                for item in self.ownitem():
                    #                    print('coping', os.path.join(self.owndir(), item),  os.path.join(tmpdir, item))
                    shutil.copyfile(os.path.join(self.owndir(), item),
                                    os.path.join(tmpdir, item))

        fpath = os.path.join(tmpdir, ".tree_data")
#         dprint1(fpath)
        try:
            fid = open(fpath, 'wb')
            self.save2(fid)
            fid.close()
        except IOError as error:
            print(traceback.format_exc())
            return False
        if not maketar:
            return True, tmpdir

        # make tar or tar.gz file
        if compress:
            mode = 'w:gz'
        else:
            mode = 'w'
        fid = open(filename, 'wb')
        tfid = tarfile.open(mode=mode, fileobj=fid)
        basename = os.path.basename(tmpdir)
        for item in os.listdir(tmpdir):
            dprint1('adding item ' + str(item))
            tfid.add(os.path.join(tmpdir, item),
                     arcname=os.path.join(basename, item))
            dprint1('(done)')
        tfid.close()
        fid.close()

        shutil.rmtree(tmpdir)
        return True

    def load_subtree(self, filename, keep_zorder=True, message=None,
                     compress=False, usetar=True):
        '''
        load contents of filename and
        added as self's child
        '''
        if usetar:
            filenamet = filename
            if compress:
                mode = 'r:gz'
            else:
                mode = 'r'
            fid = open(filenamet, 'rb')
            tfid = tarfile.open(mode=mode, fileobj=fid)
#             print "checking file contents..."

            for member in tfid.getmembers():
                if str(os.path.basename(member.name)) == ".tree_data":
                    org_dir = os.path.dirname(member.name)
                    break
            else:
                print("invalid file")
                tfid.close()
                fid.close()
                return None

#             tar_xpath = os.path.dirname(filenamet)
#             tar_xpath2 = os.path.join(os.path.dirname(filenamet), org_dir)
            wdir = self.get_root_parent().getvar('wdir')
            tar_xpath = wdir
            tar_xpath2 = os.path.join(wdir, org_dir)

            if os.path.exists(tar_xpath2):
                m = working_dir_exists_message1(str(tar_xpath2))
                ret = dialog.message(None,
                                     m,
                                     'Working Directory already exists.',
                                     2)

                if ret == 'ok':
                    shutil.rmtree(tar_xpath2)
                else:
                    tfid.close()
                    fid.close()
                    return None

            tfid.extractall(path=tar_xpath)
            tfid.close()
            fid.close()

        else:
            tar_xpath2 = filename

        fpath = os.path.join(tar_xpath2, ".tree_data")
        fid = open(fpath, 'rb')
        try:
            td, olist, nlist = TreeDict().load(fid, keep_zorder=True)
        except:
            app = wx.GetApp().TopWindow
            dialog.showtraceback(parent=app,
                                 txt='Failed to load subtree',
                                 title='Fail to load',
                                 traceback=traceback.format_exc())

#         print olist, nlist
        fid.close()

        oname = td._name
        names = self.get_childnames()

        top = self.get_root_parent()

        # dirty if switch...;D
        from ifigure.mto.py_code import PyFolder
        from ifigure.mto.py_extfile import PyExtFolder, ExtMixIn
        if isinstance(td, ExtMixIn):
            tmp_obj = PyExtFolder()
        else:
            tmp_obj = PyFolder()

        top.add_child('tmp', tmp_obj, keep_zorder=True)

        imodel = tmp_obj.add_child(oname, td, keep_zorder=keep_zorder)

#         print time.time()-t0
        # move owndir
        if td._has_private_owndir:
            #         if td._can_have_child:
            fpath = os.path.join(tar_xpath2, oname)
            if os.path.exists(fpath):
                #                if not td.has_owndir(): td.mk_owndir()
                #                this may not work if two are not in the same filesystem
                #                os.rename(fpath, td.owndir())
                shutil.move(fpath, td.owndir())
        else:
            if td.has_item():
                td.mk_owndir()
            for item in td.ownitem():
                fpath = os.path.join(tar_xpath2, item)
                if os.path.exists(fpath):
                    shutil.move(fpath,
                                os.path.join(td.owndir(), item))
#         print time.time()-t0

        if names.count(oname) != 0:
            td.rename(self.get_next_name(oname+'_loaded'),
                      ignore_name_readonly=True)

#         if not td._can_have_child and td.has_item(): self.mk_owndir()
        if not td._has_private_owndir and td.has_item():
            self.mk_owndir()

        try:
            td.move(self, keep_zorder=True)
        except:
            traceback.print_exc()
            if message is not None:
                message.txt = (str(td) + ' can not paste under ' +
                               str(self))
            else:
                traceback.print_exc()
            td.destroy()
            tmp_obj.destroy()
            shutil.rmtree(tar_xpath2)
            return None

        tmp_obj.destroy()

        for obj in td.walk_tree(stop_at_ext=True):
            obj.init_after_load(olist, nlist)

        # delete temporary directory
        shutil.rmtree(tar_xpath2)

        if not self.can_have_child(td):
            if message is not None:
                message.txt = (str(td) + ' can not paste under ' +
                               str(self))
            td.destroy()
            return None
#         print time.time()-t0
        return td

    def random_tmp_name(self, seed='1'):
        # generate a random string for an initial work dir
        from datetime import datetime
        import hashlib
        strtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S. %f")
        # print strtime
        m = hashlib.md5()
        bytechar = (strtime+str(seed)).encode('latin-1')
        m.update(bytechar)
        txt = m.hexdigest()
        return txt

    def has_item(self):
        return len(self._items) != 0

    def ownitem(self, items=None):
        '''
        return ownitems' path. 
        Without argumetns, it returns the list of paths.
        With argument of items it returns paths only specified by
        the argument. 
        Note, if getvar returns None, it is excluded
        '''
        if items is None:
            return [self.getvar(x) for x in self._items if self.getvar(x) is not None]
        else:
            return [self.getvar(x) for x in items
                    if self.getvar(x) is not None and x in self._items]

    def prepare_compact_savemode(self):
        return self._var

    def sort_children_up(self):
        names = self.get_childnames()
        for i, name in enumerate(sorted(names)):
            oi = self.i_child(name=name)
            self.move_child(oi, i)

    def sort_children_down(self):
        names = self.get_childnames()
        names = [i for i in reversed(sorted(names))]
        for i, name in enumerate(names):
            oi = self.i_child(name=name)
            self.move_child(oi, i)

    def sort_var_up(self):
        self._var = collections.OrderedDict(sorted([(k, self._var[k])
                                                    for k in self._var]))

    def sort_var_down(self):
        self._var = collections.OrderedDict(reversed(sorted([(k, self._var[k])
                                                             for k in self._var])))

    def search(self, txt, dir=0, include_self=True):
        start = False
        if dir == 0:
            g = self.get_root_parent().walk_tree
        else:
            g = self.get_root_parent().walk_tree_rev
        for x in g():
            if x is self:
                start = True
                if not include_self:
                    continue
            if not start:
                continue
            if x._name.upper().find(txt.upper()) != -1:
                return x
        return None

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def get_auto_status_str(self):
        return ''


class TopTreeDict(TreeDict):

    #   This class defines the capability which only tree
    #   top should have
    #      Event handling for
    #         Save/Load, Cut/Paste

    def __init__(self, src=None):
        self._focus = None
        self._app = None   # proxy to app
        super(TopTreeDict, self).__init__()
        self._name_readonly = True
        self.setvar("filename", None)
        self.setnote("filename", "name of file")

        cond = True
        while cond:
            if src is not None:
                return
            txt = self.random_tmp_name()

#           wdir=os.path.join(ifigure_config.rcdir,
#                     '###untitled_'+txt)
            wdir = os.path.join(ifigure_config.tempdir,
                                '###untitled_'+txt)

            #print("preparing working dir : checking " + wdir)
            time.sleep(0.5)
            if os.path.exists(wdir) == False:
                os.mkdir(wdir)
                os.mkdir(os.path.join(wdir, '.trash'))
                cond = False
        self.setvar("wdir", wdir)
        self.setnote("wdir", "working directory")

    @classmethod
    def isTopTreeDict(self):
        return True

    def get_namebase(self):
        return 'toptreedict'

    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        return None

    def get_trash(self):
        wdir = self.getvar("wdir")
        return os.path.join(wdir, '.trash')

    def set_app(self, app):
        self._app = weakref.proxy(app)

    @property
    def app(self):
        return self._app

#    def GetFocus(self):
#        pass
#    def SetFocus(self):
#        pass

    def onCut(self, e):
        pass

    def onPaste(self, e):
        pass

    def onCopy(self, e):
        pass

    def onProjTreeActivate(self, e):
        pass

    def SaveToFile(self, filename, opath=None):
        # save data to temporary directory
        old_wdir = self.getvar("wdir")
        old_filename = self.getvar("filename")

        self._set_work_dir(filename)
        d = self.getvar("wdir")

        if old_wdir != d:
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(old_wdir, d)

        fpath = os.path.join(d, ".tree_data")
        try:
            fid = open(fpath, 'wb')
            #  this save should include
            #  writing all files including on-memory scripts
            #  to files.
            self.save(fid)
            fid.close()
        except IOError as error:
            return False

        # set proj.filename
        self.setvar("filename", filename)
#         if old_wdir != d:
#              self._delete_tempdir(old_wdir)
        fid = open(os.path.join(d, '.filename'), 'w')
        fid.write(filename)
        fid.close()
        print("done....(save)")

        from ifigure.utils.mp_tarzip import MPTarzip
        success = MPTarzip().Run(filename, d, old_wdir)

        if not success:
            self.setvar("filename", old_filename)
            self.getvar("wdir", old_wdir)            

        return success

    def LoadFromFile(self, filename, sb=None):
        if sb is not None:
            sb.SetStatusText("loading project file " + filename, 0)
            sb.Refresh()
        fid = open(filename, 'rb')
        tfid = tarfile.open(mode='r:gz', fileobj=fid)
#         sys.stdout.write("checking file contents...")
        print("checking file contents...")
        for member in tfid.getmembers():
            if str(os.path.basename(member.name)) == ".tree_data":
                org_dir = os.path.dirname(member.name)
                break
        else:
            sys.stdout.write("invalid file\n")
#             print("invalid file")
            tfid.close()
            fid.close()
            return None

        tar_xpath2 = self._work_dirname(filename)
        tar_xpath = os.path.join(tar_xpath2, org_dir)
#         tar_xpath2 = os.path.join(os.path.dirname(filename), org_dir)

        do_expand = True

        crash_file = self._check_crash_file(filename)
        if crash_file != '':
            m = working_dir_exists_message2(str(crash_file))
            ret = dialog.message(None, m, '', 5)
            if ret == 'yes':
                shutil.rmtree(crash_file)
                if len(os.listdir(os.path.dirname(crash_file))) == 0:
                    #                  dprint1('deleting', os.path.dirname(crash_file))
                    shutil.rmtree(os.path.dirname(crash_file))
            elif ret == 'no':
                tfid.close()
                fid.close()
                trash = os.path.join(crash_file, '.trash')
                if os.path.exists(trash):
                    shutil.rmtree(trash)
#              dprint1('moving', crash_file, tar_xpath2)
                shutil.move(crash_file, tar_xpath2)
                if len(os.listdir(os.path.dirname(crash_file))) == 0:
                    #                 dprint1('deleting', os.path.dirname(crash_file))
                    shutil.rmtree(os.path.dirname(crash_file))
                do_expand = False
            else:
                tfid.close()
                fid.close()
                return
        if do_expand:
            os.mkdir(tar_xpath2)
            # print 'expanding to', tar_xpath2
            tfid.extractall(path=tar_xpath2)
            tfid.close()
            fid.close()
            for item in os.listdir(tar_xpath):
                src = os.path.join(tar_xpath, item)
                dst = os.path.join(tar_xpath2, item)
                shutil.move(src, dst)
            shutil.rmtree(tar_xpath)

        fpath = os.path.join(tar_xpath2, ".tree_data")
        fid = open(fpath, 'rb')

        real_top, olist, nlist = TreeDict().load(fid, keep_zorder=True)
#         print olist, nlist
        fid.close()
#         sys.stdout.write("done (load)\n")
        print("done....(load)")

        self.CloseProject()

        real_top.setvar("filename", str(filename))
        real_top.setvar("wdir", str(tar_xpath2))
        real_top._app = self._app
        os.mkdir(os.path.join(tar_xpath2, '.trash'))
        fid = open(os.path.join(tar_xpath2, '.filename'), 'w')
        fid.write(filename)
        fid.close()

        if sb is not None:
            sb.SetStatusText("initializing model :"+filename, 0)
            sb.Refresh()
        print("initializing model...")
        for obj in real_top.walk_tree(stop_at_ext=True):
            obj.init_after_load(olist, nlist)
        print("done....(init) " + str(real_top))

        return real_top

    def CloseProject(self):
        path = self.getvar("filename")
        wdir = self.getvar("wdir")
        if wdir is not None:
            self._delete_tempdir(wdir)
        self.destroy()

    def _check_crash_file(self, file):
        from ifigure.ifigure_config import tempdir_base
        from ifigure.utils.pid_exists import pid_exists

        crashed_process = []
        for item in os.listdir(tempdir_base):
            if item.startswith('pid'):
                pid = int(item[3:])
                if not pid_exists(pid):
                    #       try:
                    #          os.kill(pid, 0)
                    #       except OSError:
                    dname = os.path.join(tempdir_base, item)
                    for item2 in os.listdir(dname):
                        f = os.path.join(tempdir_base, item,
                                         item2, '.filename')
                        if os.path.exists(f):
                            fid = open(f, 'r')
                            l = fid.readline()
                            fid.close()
                            if str(l) == str(file):
                                return os.path.join(tempdir_base, item, item2)
        return ''

    def _set_work_dir(self, path):
        d = self._work_dirname(path)
        self.setvar("wdir", d)

    def _work_dirname(self, path):
        #        base=os.path.dirname(path)
        #        dname='.###ifigure_'+os.path.basename(path)
        #        d=os.path.join(base, dname)
        dname = '.###ifigure' + \
            '_'.join((os.path.splitdrive(str(path))[1]).split(os.sep))
        d = os.path.join(ifigure_config.tempdir, dname)
        return d

    def _delete_tempdir(self, old_wdir):
        #print("deleting temporary dir " + old_wdir)
        try:
            shutil.rmtree(old_wdir)
        except:
            print('failed to delete temporary directory')
            import __main__
            __main__.xxx.append(old_wdir)
            pass
        # os.rmdir(old_wdir)

    def memorized_data(self):
        '''
        list of memorized data when tree_obj is
        destoried.
        '''
        return []


#
#   example
#
if __name__ == '__main__':
    print("Demonstration")
    ##
    # Point of this class
    ##
    ##     children is stored in OrderedDict
    # adder need to be implemented to add a
    # child

    root = TreeDict()
    root.add_child("test", TreeDict())
    root.add_child("test2", TreeDict())
    root.test.add_child("test3", TreeDict())

    print(("root", root))
    print(("root.test", root.test))
    print(("root.test.test3", root.test.test3))
    print(("root.test2", root.test2))

    gen = root.walk_tree()
    print(gen.next().get_full_path())
    print(gen.next().get_full_path())
    print(gen.next().get_full_path())
    print(gen.next().get_full_path())
    print(gen.next().get_full_path())


if __name__ == '__main__':
    print("Demonstration")
    ##
    # Point of this class
    ##
    ##     children is stored in OrderedDict
    # adder need to be implemented to add a
    # child

    page = FigPage()
    page.add_axes('axes_1')
    page.add_axes('axes_2')
    page.axes1.add_plot()

    # or you can add this way
    plot = FigPlot()
    page.axes1.add_plot("plot_1", plot)

    # in this case you need to apply figobj

    page.axes1.add_figobj("plot2")

    #  attribute setting
    page.setp('area', [0, 1, 0, 1])
    print(page.getp("area"))

    # if you do  getp_all, pay attention that
    # the returned value is the SAME object
    att = page.getp_all()
    print(att)
    att["area"] = [0, 0, 0, 0]
    a = page.getp("area")
    print(a)

    ### this generate tree list ###
    print(page.list_all())

    # can access read-only member
    # if getter is properly set
    print(page.axes1.plot.id)

    #   page.axes1.plot.id=100
    #   this will cause error (read-only)

    print(page.axes1.plot)

    ### this is not allowed
    #  in other word, all members are read-only
    #  page.axes1.plot.id2=3
    #  page.axes1.plot.test.id2=3
    #
    # you can still do this but are not supposed to do
    #  Do not create "_" private member.
    #  page.axes1._test=3
    # if you did not the above, the nexe will cause error
    # print page.axes1._test

   #   print dir(page.axes1.plot)
