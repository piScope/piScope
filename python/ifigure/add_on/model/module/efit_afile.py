from ifigure.utils.cbook import parseStr
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
import wx
import os
import re
import string
import logging
import shutil
from numpy import *
from collections import OrderedDict
from ifigure.mto.py_contents import Efitafile

from ifigure.utils.read_afile import read_afile

######################################################
#         Setting for module file for py_module
#   name of module/class
module_name = 'EFIT_Afile'
class_name = 'EFIT_Afile'
#   module_evt_handler
#   functions which can be called from project tree
#
#    (menu name, function name, a flat to call skip()
#     after running function)
#

menu = [("Import File...", "onLoadFile", True),
        ("Update Tree...", "onUpdateTree", True),
        ("+TextEditor...", None,  False),
        ("View Original File", "onOpenOrg", False),
        ("Edit File", "onOpenCurrent", False),
        ("!", None, False)]
method = ['init',
          'txt2tree',
          'onLoadFile',
          'onOpenOrg',  'onUpdateTree']

icon = 'data.png'
can_have_child = False
has_private_owndir = False
######################################################
modename = 'afile_pathmode'
pathname = 'afile_path'
extname = 'afile_ext'


def init(self, *args, **kargs):
    if "src" not in kargs:
        self.onLoadFile(file='')


def load_file(file=None):
    values = read_afile(file)

    nm = Efitafile()
    nm["contents"] = values

    return nm


def load_afile(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    if file == '':
        return
    for name, child in obj.get_children():
        child.destroy()

    nm = load_file(file)
    obj.setvar0(nm)


def txt2tree(self, filename, txt):
    '''
    save txt to file and load it
    '''
    self_obj = self.td
    if not self_obj.has_owndir():
        self_obj.mk_owndir()

    if os.path.basename(filename) == filename:
        path = os.path.join(self_obj.owndir(), filename)
    else:
        path = filename

    fid = open(path, 'w')
    fid.write(txt)
    fid.close()

    self.td.set_path_pathmode(path, modename, pathname, extname)
    load_afile(self.td)


def onUpdateTree(self, event=None):
    load_afile(self.td)


def onLoadFile(self, e=None, file=''):
    from ifigure.utils.addon_utils import onLoadFile

    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname)
        ret = True
    else:
        ret = onLoadFile(self.td, message="Select A-File",
                         modename=modename,
                         pathname=pathname,
                         extname=extname)
    if not ret:
        return False

    load_afile(self.td)


def onOpenOrg(self, e=None):
    from ifigure.utils.addon_utils import onOpenOrg
    onOpenOrg(self.td)


def onOpenCurrent(self, e=None):
    from ifigure.utils.addon_utils import onOpenCurrent
    onOpenCurrent(self.td, modename=modename,
                  pathname=pathname)
