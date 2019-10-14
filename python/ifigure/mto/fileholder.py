'''
   FileHolder is a unitiliy class to support file
   in project tree

   goal of this utility is to provide

   conversion between fullpath <-> pathmode, path, ext
   provide a routine to file time stamp
'''
import os
import ifigure
from os.path import expanduser


class FileHolder(object):
    def split_ext(self, path):
        arr = path.split('.')
        base = arr[0]
        ext = '.'.join(arr[1:])
        return base, ext

    # utility to convert fullpath to path
    def set_path_pathmode(self, path,
                          modename='pathmode',
                          pathname='path',
                          extname='ext', checklist=None):
        if path == '':
            return
        pathmode, subpath = self.fullpath2path(path, checklist=checklist)
        self.setvar(modename, pathmode)
        self.setvar(pathname, subpath)
        base, ext = self.split_ext(subpath)
        self.setvar(extname, ext)
        if pathmode == 'owndir':
            if not pathname in self._items:
                self._items.append(pathname)
        else:
            if pathname in self._items:
                self._items.remove(pathname)

    def fullpath2path(self, path, checklist=None):
        '''
           script path is managed by using the
           combination of pathmode and path.
           pathmode can be one of the following
           choice
              std:  in ifigure (root = ifigure)
              wdir: in project dir (root = wdir)
              owndir: in object dir (root = self.owndir())
              usrdir: in usr_script dir
              home: in home dir (root = home dirctory)
              abs : elsewhere (root = '/')
              extfolder ; in libary path
              proj: in proj file dir 
                    (root = os.path.dirname(proj.getvar('filename'))
           path shows the relative path to the root
        '''
        import ifigure

        #### these field are not used anymore (2012.07) ####
        if self.getvar("module file") is not None:
            self.delvar("module file")
        if self.getvar("script file") is not None:
            self.delvar("script file")
        ####################################################

        # first check if owndir is used
        # if os.path.dirname(path) == self.owndir():
        #   pathmode = 'owndir'
        #   subpath = os.path.basename(path)
        #   return pathmode, subpath

        # check other possibility
        if checklist is None:
            checklist = ['owndir', 'wdir', 'std',
                         'usrpath', 'extfolder', 'proj', 'home']

        pathmode = 'abs'
        subpath = path

        def get_base(mode):
            if mode == 'owndir':
                base = self.owndir()
            elif mode == 'wdir':
                base = self.get_root_parent().getvar("wdir")
            elif mode == 'std':
                base = os.path.dirname(ifigure.__file__)
            elif mode == 'usrpath':
                base = self.get_root_parent(
                ).app.config.setting['usr_addon_dir']
                base = os.path.expanduser(base)
            elif mode == 'proj':
                base = self.get_root_parent().getvar('filename')
                if base is None:
                    return False
                base = os.path.dirname(base)
            elif mode == 'extfolder':
                base = self.get_extfolderpath()
                if base is None:
                    return False
                #base = os.path.dirname(base)
            elif mode == 'home':
                base = expanduser("~")
#                base = os.path.abspath(os.getenv('HOME'))
            else:
                return False
            return base

        def check_path_mode_match(path, base):
            c1 = os.path.commonprefix([base, path])
            if os.path.exists(c1):
                c1 = os.path.abspath(c1)  # omit finishing '/'
                if c1 == base:
                    subpath = path[len(base):]
                    return True, subpath[1:]
            return False, ''

        for mode in checklist:
            base = get_base(mode)
            if base == False:
                continue
#            print 'how about', mode
#            print base
            check, subpath = check_path_mode_match(path, base)
#            print check, subpath
            if check:
                return mode, subpath

        return 'abs', path

        '''     
        base = self.get_root_parent().getvar("wdir")
        c1 = os.path.commonprefix([base, path])
        if os.path.exists(c1):
           c1 = os.path.abspath(c1) # omit finishing '/'
           if c1== base:
              pathmode = 'wdir'
              subpath = path[len(base):]
              return pathmode, subpath[1:]

        base = os.path.dirname(ifigure.__file__)
        c1 = os.path.commonprefix([base, path])
        if os.path.exists(c1):
           c1 = os.path.abspath(c1) # omit finishing '/'
           if c1== base:
              pathmode = 'std'
              subpath = path[len(base):]
              return pathmode, subpath[1:]
 
        base = self.get_root_parent().app.config.setting['usr_addon_dir']
        base = os.path.expanduser(base)
        c1 = os.path.commonprefix([base, path])  
        if os.path.exists(c1):
           if c1 == base:
              pathmode = 'usrpath'
              subpath = path[len(base):]
              return pathmode, subpath[1:]

        base = self.get_root_parent().getvar('filename')            
        base = os.path.dirname(base)
        c1 = os.path.commonprefix([base, path])  
        if os.path.exists(c1):
           if c1 == base:
              pathmode = 'proj'
              subpath = path[len(base):]
              return pathmode, subpath[1:]

        base = os.path.abspath(os.getenv('HOME'))
        c1 = os.path.commonprefix([base, path])  
        if os.path.exists(c1):
           if c1 == base:
              pathmode = 'home'
              subpath = path[len(base):]
              return pathmode, subpath[1:]
        '''

    def path2fullpath(self, modename='pathmode', pathname='path'):
        #        print 'entering path2fullpath'
        from os.path import expanduser
        mode = 'std'
        if self.hasvar(modename):
            mode = self.getvar(modename)
        else:
            return ''
        if mode == 'std':
            base = os.path.dirname(ifigure.__file__)
        elif mode == 'wdir':
            base = self.get_root_parent().getvar('wdir')
        elif mode == 'home':
            base = os.getenv('HOME')
        elif mode == 'owndir':
            base = self.owndir()
        elif mode == 'extfolder':
            base = self.get_extfolderpath()
            if base is None:
                base = '/'
            base = expanduser(base)
        elif mode == 'usrpath':
            base = self.get_root_parent().app.config.setting['usr_addon_dir']
            base = os.path.expanduser(base)
#           if not os.path.isabs(base):
#              base = os.path.join(os.path.abspath(os.getenv('HOME')), base)
        elif mode == 'proj':
            base = self.get_root_parent().getvar('filename')
            base = os.path.dirname(base)
        else:
            base = '/'
#        print mode, path

        from ifigure.utils.cbook import isstringlike
        if (self.hasvar(pathname)):
            # this check is to recovery from a bug
            # once introduced before.
            if not isstringlike(self.getvar(pathname)):
                self.delvar(pathname)
                return ''
            return os.path.join(base, self.getvar(pathname))
        else:
            return ''

    def get_mtime(self, modename='pathmode', pathname='path'):
        return os.path.getmtime(self.path2fullpath(modename, pathname))

    def store_mtime(self, mname='mtime', modename='pathmode', pathname='path'):
        mtime = self.get_mtime(modename=modename, pathname=pathname)
        self.setvar(mname, mtime)

    def isExternalFileNewer(self, mname='mtime', modename='pathmode', pathname='path'):
        if self.isInternalFile():
            return False
        cmtime = os.path.getmtime(self.path2fullpath(
            modename='pathmode', pathname='path'))
        if self.getvar(mname) is None:
            return False
        return (cmtime > self.getvar(mname))

    def isInternalFile(self):
        if (self.getvar('file_pathmode') == 'wdir' or
                self.getvar('file_pathmode') == 'owndir'):
            return True
        return False
