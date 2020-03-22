from __future__ import print_function
#
#   AbsModule
#
#   object to encapsulate an class
#
#      self._m_file : module file name
#      self._m_co   : code object
#      self._m_mtime: time stamp
#      self.td      : proxy to mto containing module
#

import logging
import imp
import os
import weakref
import traceback
import ifigure.utils.cbook as cbook


def load_module_file(file):
    logging.basicConfig(level=logging.DEBUG)
    try:
        m = imp.load_source('ifigure.add_on.tmp', file)
        name = m.module_name
        m = imp.load_source('ifigure.add_on.'+name, file)
        mtime = os.path.getmtime(file)
        return m, mtime
    except Exception:
        print(('Module loading failed: ', file))
        print(traceback.format_exc())

    return None, 0


class AbsModule(object):
    def __new__(cls, file=None, obj=None, *args, **kargs):
        if file is None:
            return None

        m, mtime = load_module_file(file)

        if obj is not None:
            td = weakref.proxy(obj)
        else:
            td = None

        typ = type(m.module_name, (AbsModule, ),
                   dict(_m_co=m, _m_file=file,
                        _m_mtime=mtime, _td=td))
        obj = object.__new__(typ, *args, **kargs)

        return obj

    def __init__(self, *args, **kargs):
        self._debug = 0
        self._register_method()
        setattr(self._m_co, 'debug', self._debug)

    def __getitem__(self, key):
        if hasattr(self, '__getitem__'):
            return self.__getitem__(key)

    def __del__(self):
        if hasattr(self, 'clean'):
            m = getattr(self, 'clean')
            m()

    def _register_method(self):
        from types import MethodType
        #
        #   registoer class method based on
        #   _module_co
        #
        logging.basicConfig(level=logging.DEBUG)
        if hasattr(self._m_co, 'menu'):
            self._menu = self._m_co.menu
            if hasattr(self._m_co, 'icon'):
                self._icon = self._m_co.icon
            else:
                self._icon = ''

        self._module_method = []
        try:
            if hasattr(self._m_co, 'method'):
                for mname in self._m_co.method:
                    m = getattr(self._m_co, mname)
#               object.__setattr__(self, mname,
#                     m.__get__(self, self.__class__))
                    object.__setattr__(self, mname,
#                                       MethodType(m, self, self.__class__))
                                       MethodType(m, self))
                    self._module_method.append(mname)
#               print "adding method:", mname

        except Exception:
            logging.exception("Module Loading Failed")

    def has_method(self, fname):
        if self.check_filenew():
            self.load_module()
        try:
            m = getattr(self, fname)
            return True
        except:
            pass
        return False

    def run_method(self, fname, *extra, **kextra):
        logging.basicConfig(level=logging.DEBUG)
        if self.check_filenew():
            self.load_module()
        try:
            m = getattr(self, fname)
            return m(*extra,  **kextra)
        except Exception:
            logging.exception("Calling module function failed")

    def run_init(self, obj, *extra, **kextra):

        logging.basicConfig(level=logging.DEBUG)

        fname = self._m_co.module_init
        if fname is None:
            return
        try:
            func = getattr(self._m_co, fname)
            func(obj, *extra, **kextra)
        except Exception:
            logging.exception(" Module initialize failed")

    def unbind_method(self):
        if self._m_co is not None:
            # need to unload all method/functions
            # hasattr(self._m_co,'method'):
            for mname in self._module_method:
                if hasattr(self, mname):
                    delattr(self, mname)
                if hasattr(self._m_co, mname):
                    delattr(self._m_co, mname)
#               print "deleteing method:", mname

    def set_debug(self, level):
        self._debug = level
        setattr(self._m_co, 'debug', self._debug)

    def get_debug(self):
        return self._debug

    def load_module(self):
        print(('Loading Module File :', self._m_file))
        self.unbind_method()
        self._m_co, self._m_mtime = load_module_file(self._m_file)
        if self._m_co is not None:
            self._register_method()
            setattr(self._m_co, 'debug', self._debug)

    def check_filenew(self):
        if self._m_file == '':
            return False
        if os.path.exists(self._m_file):
            return (os.path.getmtime(self._m_file) >
                    self._m_mtime)
        else:
            return False

    def edit_module(self):
        cbook.LaunchEmacs(self._m_file)

    @property
    def menu(self):
        return self._menu

    @property
    def td(self):
        return self._td
