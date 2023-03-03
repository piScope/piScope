from __future__ import print_function
#################################################
#
#   NameList : PyData to hold a fortran namelist
#
#       Actual implementatin was done in
#       submodules
#################################################
import os
import re
import string
import wx
import shutil
from ifigure.utils.cbook import parseStr
from numpy import *
from collections import OrderedDict
from ifigure.mto.py_code import PyData
from ifigure.mto.py_contents import Namelist
######################################################
#         Setting for module file for py_module
#
#   General rule:
#      This file will be automatically loaded when
#      py_module object is created. Also, py_module
#      keeps track the file modification time. If
#      the file is updated, it will be automaticaaly
#      reloaded.
#
#
#      Strong recommendation : make module "independent".
#
#      Py_Modules does not check the dependency of
#      modules.
#      If moduels used in Py_Modules depends on
#      each other by for example module variable,
#      it will cause complicate  moduling
#      order-dependency problem.
#
#   name of module
module_name = 'namelist'
class_name = 'namelist'
#   module_evt_handler
#   functions which can be called from project tree
#
#    (menu name, function name, a flat to call skip()
#     after running function)
#
#   By default these function should return None
#   or True
#   if it return False, ifigure stops exectuion at
#   this module
#
menu = [("Import...", "onLoadFile", True),
        ("Export...", "onWriteFile", False),
        ("Update File", "onUpdateFile", False),
        ("Update Tree", "onUpdateTree", True),
        ("+TextEditor...", None,  False),
        ("View Original", "onOpenOrg", False),
        ("Edit File", "onOpenCurrent", False),
        ("!", None, False),
        ("+NameList...", None,  False),
        ("Add Section...", "onAddSec", False),
        ("Remove Section...", "onRmSec", False),
        ("Rename Section...", "onRenameSec", False),
        ("!", None, False)]

method = ['tree2txt', 'check_new_fileedit',
          'onLoadFile', 'onWriteFile', 'onOpenOrg',
          'onOpenCurrent', 'onUpdateFile', 'onUpdateTree',
          'onAddSec', 'onRmSec', 'onRenameSec',
          'init']
icon = 'text.png'
can_have_child = False
has_private_owndir = False
######################################################

modename = 'namelist_pathmode'
pathname = 'namelist_path'
extname = 'namelist_ext'


def init(self, *args, **kargs):
    obj = self.td
    obj.mk_owndir()
    nm = Namelist()
    obj.setvar0(nm)
    if 'src' not in kargs:
        self.onLoadFile()
    else:
        try:
            self.onUpdateTree()
        except:
            import traceback
            traceback.print_exc()


def split_arr(arr, pattern):
    ret = []
    for s in arr:
        ret = ret + re.split(pattern, s)

    ret2 = []
    for s in ret:
        if s != '':
            ret2 = ret2+[s]

    return ret2


def join_arr(arr, a, b):  # a='(', b=')'
    num = 0
    ret = []
    i = 0
    while i < len(arr):
        if arr[i] != a:
            ret = ret + [arr[i]]
        else:
            num = 0
            j = i+1
            tmp = arr[i]
            while (arr[j] == b and num == 0) is False:
                if arr[j] == a:
                    num = num+1
                if arr[j] == b:
                    num = num-1
                tmp = tmp+arr[j]
                j = j+1
            i = j
            tmp = tmp+arr[i]
            ret = ret + [tmp]
        i = i+1
    return ret


def join_arr2(arr, sep):
    ret = [arr[0]]
    i = 1
    while i < len(arr):
        flag = True
        for s in sep:
            if arr[i] == s:
                flag = False
        if flag:
            ret[-1] = ret[-1]+arr[i]
        else:
            ret = ret + [' ']
        i = i+1

    ret2 = []
    for s in ret:
        ret2 = ret2+[s.strip()]
    return ret2


def interpret_line(line):
    test = [line]
    test = split_arr(test, r'(")')
    test = split_arr(test, r'(,)')
    test = split_arr(test, r'(\()')
    test = split_arr(test, r'(\))')
    test = split_arr(test, r'(\s)')

    test = join_arr(test, '(', ')')
    test = join_arr(test, '"', '"')

    test = join_arr2(test, ', ')
    ret2 = []
    for s in test:
        if s != '':
            ret2 = ret2+[s]
    return ret2


def string_split_ig(s, sep):
    t = re.split(sep, s)
    id = range(len(t))
    id = reversed(id)
    for i in id:
        if t[i] == '':
            del t[i]
    return t


def eval_form2020(s):
    #form2020= '(5e16.9)'
    d = 16
    ret = []
    for i in range(5):
        if s[d*i:d*(i+1)] != '':
            ret.append(float(s[d*i:d*(i+1)]))
    return ret


def readandstrip(f):
    line = f.readline()
    line = line.rstrip("\r\n")
    return line


def load_array_form2020(f, size):
    k = 0
    arr = []
    while (k < size):
        arr = arr+eval_form2020(readandstrip(f))
        k = k+5
    return array(arr)


def load_matrix_form2020(f, size1, size2):
    k = 0
    arr = []
    while k < size1*size2:
        arr = arr+eval_form2020(readandstrip(f))
        k = k+5
    return array(arr).reshape(size1, size2)


def load_file(file=None):
    #   file='/home/shiraiwa/PycharmProjects/ifigure/sample/genray.in'
    def get_line(f):
        line0 = f.readline()
#      print line0
        if not line0:
            return False, '', ''
        if line0.find('!') != -1:
            line0 = line0[:line0.find('!')]
#         print line0
        line0 = line0.rstrip("\r\n")
        line0 = ' '.join(line0.split())
        if line0.endswith('/'):
            line = line0[:-1]
        else:
            line = line0
        return True, line, line0
    f = open(file, 'r')

    # namelist section
    nm = Namelist()
    sec = None
    end_flag = False
    while 1:

        flag, line, line0 = get_line(f)
#      print line0
        if not flag:
            break
        if line == '':
            continue

        if (line.startswith('&') and
                line[:4].lower() != '&end'):
            while line[1] == ' ':
                line = line[:1] + line[2:]
            s = string_split_ig(line, ' |,')
            sec = s[0][1:]
            #print("entring section", sec)
            nm[sec] = OrderedDict()
            if len(s) > 1:
                line = ' '.join(s[1:])
            else:
                continue
        if sec is None:
            continue  # skip unitl first &*** starts

        sall = interpret_line(line)
        i = 0
        while i < len(sall):
            if sall[i].find('=') != -1:
                if sall[i] == '=':    # '='
                    sall[i-1] = sall[i-1]+'='
                    del sall[i]
                    continue
                if sall[i].startswith('='):  # '=value'
                    sall[i-1] = sall[i-1]+'='
                    sall[i] = sall[i][1:]

                    continue
                if sall[i].endswith('='):
                    print(sall[i])
                    i = i+1
                    continue  # 'name='
                k = sall[i].split('=')
                sall[i] = k[0]+'='
                sall.insert(i+1, k[1])
            i = i+1

        for s in sall:
            if s[:4].lower() == '&end':
                sec = None
#           print('breaking')
                break
            if s.find('=') != -1:
                k = s.split('=')
                varname = k[0]
#          s[0]=k[1]
#          print s
#          if s[0] is '': del s[0]
#          print 'create dict key', sec, varname
                nm[sec][varname] = []
                if s.endswith('/'):
                    sec = None
                continue
        # for lines without 'xxxx = '

            nm[sec][varname] = nm[sec][varname]+parseStr(s)
        if line0.endswith('/'):
            sec = None
    f.close()
    return nm


def load_namelistfile(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    if file == '':
        return

    for name, child in obj.get_children():
        child.destroy()

    nm = load_file(file)
    print(('reading file', file))
    obj.setvar0(nm)
    mtime = os.path.getmtime(file)
    obj.setvar('namelist_mtime', mtime)


def tree2txt(self):
    '''
    make tree to txt and update owndir file
    '''

    td = self.td
    var0 = td[:]
    txt = []
    for key0 in var0:

        txt.append(' &'+key0+'\n')
        var = var0[key0]

        for key in var:
            line = ' '+key+' = '

            for el in var[key]:
                if len(line) + len(str(el)) > 73:
                    txt.append(line+'\n')
                    line = '    '
                line = line + ' '+str(el)
            txt.append(line+'\n')
        txt.append(' &end\n \n')

    txt2 = ''.join(txt)

    return txt2


def check_new_fileedit(self, no_dialog=False, force_load=False):
    '''
    check if file is edited since the last loading

    by default, it asks if a user wants to reload
    otherwise, it returns status. In the latter case,
    a program needs to reload by itself later 
    '''
    obj = self.td
    if (obj.get_mtime(modename='namelist_pathmode', pathname='namelist_path') >
            obj.getvar('namelist_mtime')):
        if not no_dialog:
            dlg = wx.MessageDialog(None,
                                   'File is newer than tree data, Do you want to reload?',
                                   'Old tree data',
                                   wx.OK | wx.CANCEL)
            if dlg.ShowModal() == wx.ID_OK:
                self.onUpdateTree()
                dlg.Destroy()
                return True
            else:
                return False
        else:
            if force_load:
                #               print('loading namelist from file')
                self.onUpdateTree()
                return True
            else:
                return False
    return True


def onUpdateTree(self, e=None):
    obj = self.td
    load_namelistfile(self.td)


def onLoadFile(self, e=None, file=''):
    from ifigure.utils.addon_utils import onLoadFile

    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname)
        ret = True
    else:
        ret = onLoadFile(self.td, message="Select Namelist File",
                         modename=modename,
                         pathname=pathname,
                         extname=extname)
    if ret:
        load_namelistfile(self.td)


def onWriteFile(self, e=None, filename=''):
    from ifigure.utils.addon_utils import onWriteFile

    txt = self.tree2txt()
    onWriteFile(self.td, filename=filename,
                txt=txt,
                message='Enter Namelist File Name')


def onUpdateFile(self, e=None, *args, **kargs):
    obj = self.td
    file = self.td.path2fullpath(modename=modename,
                                 pathname=pathname)
    file_check = os.path.join(obj.owndir(), obj.name)

    if file == '':
        file = file_check
        try:
            self.onWriteFile(filename=file)
            obj.set_path_pathmode(file, modename, pathname, extname)
        except:
            print('file save failed')
            traceback.print_exc()
    else:
        self.onWriteFile(filename=file)


def onOpenOrg(self, e=None, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenOrg
    onOpenOrg(self.td)


def onOpenCurrent(self, e=None, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenCurrent
    onOpenCurrent(self.td, modename=modename,
                  pathname=pathname)


def onAddSec(self, e):
    import ifigure.widgets.dialog as dialog

    parent = e.GetEventObject()
    ret, name = dialog.textentry(parent,
                                 "Enter section name",
                                 "Add Section...", 'section')
    if not ret:
        return

    var0 = self.td.getvar0()
    if not name in var0:
        var0[name] = Namelist()
        app = wx.GetApp().TopWindow
        app.proj_tree_viewer.update_content_widget(self.td)


def onRmSec(self, e):
    import ifigure.widgets.dialog as dialog

    parent = e.GetEventObject()
    var0 = self.td.getvar0()
    ret, name = dialog.textselect(parent,
                                  "Select section name",
                                  "Remove Section...",
                                  choices=list(var0.keys()))
    if not ret:
        return

    del var0[name]
    app = wx.GetApp().TopWindow
    app.proj_tree_viewer.update_content_widget(self.td)


def onRenameSec(self, e):
    import ifigure.widgets.dialog as dialog
    parent = e.GetEventObject()
    var0 = self.td.getvar0()
    ret, name = dialog.textselect(parent,
                                  "Select section name",
                                  "Rename Section...",
                                  choices=list(var0.keys()))
    if not ret:
        return
    ret, name1 = dialog.textentry(parent,
                                  "Enter new section name",
                                  "Rename Section...", name+'_renamed')
    if not ret:
        return

    var0[name1] = var0[name]
    del var0[name]
    app = wx.GetApp().TopWindow
    app.proj_tree_viewer.update_content_widget(self.td)
