from __future__ import print_function
import wx
from ifigure.utils.cbook import parseStr
from ifigure.mto.py_code import PyData
from ifigure.mto.py_code import PyCode
from ifigure.mto.py_module import PyModule
from ifigure.mto.py_contents import NETCDFfile
import ifigure.events

import os
import re
import string
import sys
from numpy import *
from collections import OrderedDict
from netCDF4 import Dataset
######################################################
#         Setting for module file for py_module
#
#   General rule:
#      This file will be automatically loaded when
#      py_module object is created. Also, py_module
#      keeps track the file modification time. If
#      the file is updated, it will be automaticaaly
#      reloaded.


#      Strong recommendation : make module "independent".

#      Py_Modules does not check the dependency of
#      modules.
#      If moduels used in Py_Modules depends on
#      each other by for example module variable,
#      it will cause complicate  module loading
#      order-dependency problem.
#
#   name of module
module_name = 'netCDF'
class_name = 'netCDF'
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
menu = [("Import...",   "onLoadFile", True),
        ("Export...",   "onExportFile", False),
        ("Update Tree", "onUpdateTree", True),
        ("Update File", "onUpdateFile", True),        
        ("Check NC Format", "onCheckFormat", True),
        ("Write NC File", "onWriteNCFile", True), ]
method = ['onLoadFile', 'onUpdateTree', 'onUpdateFile',
          'onExportFile', 'onWriteNCFile', 'onCheckFormat',
          'init', 'init_after_load']
icon = 'data.png'
can_have_child = False
has_private_owndir = False
nosave_var0 = True
######################################################

modename = 'nc4_pathmode'
pathname = 'nc4_path'
extname = 'nc4_ext'


def init(self, *args, **kargs):
    #   a function called when py_module is initialized
    self.td.mk_owndir()
    if 'src' not in kargs:
        self.onLoadFile()
    # self.onLoadFile()


def do_load_netcdf_file(nm, g, keylist=None):

    if keylist is None:
        keylist = []

    nm["dimensions"] = NETCDFfile()
    nm["dimensions"].nc_path = keylist+["dimensions"]
    
    for dimname in g.dimensions:
        nm["dimensions"].var[dimname] = len(g.dimensions[dimname])
    for attname in g.ncattrs():
        nm.var[attname] = getattr(g, attname)

    nm["variables"] = NETCDFfile()
    nm["variables"].nc_path = keylist+["variables"]

    for varname in g.variables:
        nm["variables"][varname] = NETCDFfile()
        nm["variables"][varname].nc_path = keylist+["variables", varname]

        src = g.variables[varname]
        var = OrderedDict()
        var["dimensions"] = src.dimensions
        var["dtype"] = src.dtype
        var["ndim"] = src.ndim
        var["shape"] = src.shape
        for attname in src.ncattrs():
            var[attname] = getattr(src, attname)
        nm["variables"][varname].var = var
    # walk thorough all sub groups

    i = 1
    
    for sub_g in g.groups:
        #name = 'group'+str(i)
        name = sub_g
        #nm["variables"][name] = NETCDFfile()
        #nm["variables"][name].nc_path = keylist+["variables", name]
        #do_load_netcdf_file(nm["variables"][name], g[sub_g],
        #                    keylist=keylist+["variables", name])
        nm[name] = NETCDFfile()
        nm[name].nc_path = keylist+[name,]
        do_load_netcdf_file(nm[name], g[sub_g],
                            keylist=keylist+[name])
        i = i+1


def write_file(td, filename='/home/shiraiwa/test.nc',
               ignore_changes=False, format='NETCDF3_CLASSIC'):
    import numpy as np
    nm = td.getvar0()
    dtype2str = {np.dtype('float64'):  'f8',
                 np.dtype('float32'):  'f4',
                 np.dtype('int64'): 'i8',
                 np.dtype('int32'): 'i4',
                 np.dtype('int16'): 'i2',
                 np.dtype('int8'):  'i1',
                 np.dtype('uint64'): 'u8',
                 np.dtype('uint32'): 'u4',
                 np.dtype('uint16'): 'u2',
                 np.dtype('uint8'):  'u1',
                 np.dtype('S1'):  'S1', }

    rootgrp = Dataset(filename, 'w', format=format)
    for key in nm.var:
        setattr(rootgrp, key, nm.var[key])
    for key in nm['dimensions'].var:
        rootgrp.createDimension(key, nm['dimensions'].var[key])
    for key in nm["variables"]:
        dim = nm["variables"][key].var['dimensions']
        datatype = dtype2str[nm["variables"][key].var['dtype']]
        variable = rootgrp.createVariable(key, datatype, dim)
        for attr in nm["variables"][key].var:
            if not attr in ["dimensions", "dtype", "ndim", "shape"]:
                setattr(variable, attr, nm["variables"][key].var[attr])
        if ignore_changes or not nm["variables"][key]._data_loaded:
            variable[:] = nm["variables"][key].nc_eval(td)
        else:
            variable[:] = nm["variables"][key]._data

    rootgrp.close()
    print('write NC file completed. ' + filename)


def load_file(fname, check_format=False):
    import subprocess
    import shlex

    # read file
    compress = False
    if fname[-3:] == '.gz':
        command = 'gunzip '+fname
#       print command
        p = subprocess.Popen(shlex.split(command))
        p.wait()
        compress = True
        fname2 = fname[:-3]
#       print fname2
        if not os.path.exists(fname2):
            print(('!!!!!!!!!!!! netcdf file is not found', fname2))
            return
        g = Dataset(fname2, 'r')
    else:
        #       print fname
        if not os.path.exists(fname):
            print(('!!!!!!!!!!!! netcdf file is not found', fname))
            return
        g = Dataset(fname, 'r')
    if check_format:
        f = g.data_model
        g.close()
        return f
    nm = NETCDFfile()
    
    do_load_netcdf_file(nm, g)
    g.close()
    if compress:
        command = 'gzip '+fname2
        print(command)
        subprocess.Popen(shlex.split(command))
    return nm
#    obj.setvar0(nm)


def load_netcdf_file(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    if file == '':
        return
    # clean first
    for name, child in obj.get_children():
        child.destroy()

    nm = load_file(file)
    if nm is None:
        obj.setvar0(None)
        return
    obj.setvar0(nm)


def onWriteNCFile(self, e=None):
    open_dlg = wx.FileDialog(wx.GetApp().TopWindow,
                             message='Enter New NC file',
                             style=wx.FD_SAVE,
                             wildcard='NETCDF3_CLASSIC|*.nc|NETCDF3_64Bit|*.nc|NETCDF4(HDF5 with CDF4API)|*.hdf|NETCDF4_CLASIC(only CDF3)|*.hdf')
    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return
    else:
        filename = str(open_dlg.GetPath())
        idx = open_dlg.GetFilterIndex()
        open_dlg.Destroy()
    format = ('NETCDF3_CLASSIC', 'NETCDF3_64BIT',
              'NETCDF4', 'NETCDF4_CLASSIC')[idx]
    write_file(self.td, filename=filename, format=format)


def onCheckFormat(self, e=None):
    obj = self.td
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)
    if file == '':
        return
    format = load_file(file, check_format=True)
    print(format)


def onUpdateTree(self, e=None):
    obj = self.td
    load_netcdf_file(obj)
    
def onUpdateFile(self, e=None):
    obj = self.td
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)
    if file == '':
        return
    
    file2 = os.path.join(os.path.dirname(file),
                         '_tmp_'+os.path.basename(file))
    format = load_file(file, check_format=True)
    write_file(self.td, filename=file2, format=format)
    os.rename(file2, file)
    

def onLoadFile(self, e=None, file=''):
    from ifigure.utils.addon_utils import onLoadFile

    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname)
        ret = True
    else:
        ret = onLoadFile(self.td, message="Select NETCDF4 File",
                         modename=modename,
                         pathname=pathname,
                         extname=extname,
                         wildcard='nc(*.nc)|*.nc|nc.gz(*.nc.gz)|*.nc.gz|cdf(*.cdf)|*.cdf|Any|*',
                         )
    if ret:
        load_netcdf_file(self.td)
        ifigure.events.SendChangedEvent(self.td)


def onExportFile(self, evt=None):
    '''
    for now, it just copies the file
    '''
    obj = self.td
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)
    dir = os.path.expanduser('~')
    open_dlg = wx.FileDialog(wx.GetApp().TopWindow,
                             message='Enter file name to save',
                             defaultDir=dir,
                             defaultFile=os.path.basename(file),
                             wildcard='Any|*',
                             style=wx.FD_SAVE)
    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return
    else:
        filename = str(open_dlg.GetPath())
        open_dlg.Destroy()
    import shutil
    shutil.copyfile(file, filename)


def init_after_load(self, olist, nlist):
    obj = self.td
    load_netcdf_file(obj)


def set_contents(self, *args):
    obj = self[:]
    for x in args[:-1]:
        obj = obj[x]
    obj._data_loaded = True
    obj._data = args[-1]
