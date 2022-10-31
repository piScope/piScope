#
#   CSV (comma separated values) file
#       as of today, it supports a file in which
#          the first line is key
#          all columns has the same lenght
import numpy as np
import ifigure
import wx
import os
from ifigure.utils.edit_list import DialogEditList
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
#   name of module/class
module_name = 'csv_module'
class_name = 'csv_module'
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
menu = [("Import File...",   "onLoadFile", True),
        ("Export File...", "onWriteFile", True),
        ("Update Tree", "onUpdateTree", True),
        ("Convert to Float...", "onConvFloat", True),
        ("Convert to Integer...", "onConvInt", True),
        ("Convert to String...", "onConvStr", True)]

method = ['onLoadFile', 'onUpdateTree', 'onWriteFile',
          'onConvFloat', 'onConvStr', 'onConvInt',
          'ask_field',
          'init', 'init_after_load']

icon = 'data.png'
######## Do not chage this field ####################
can_have_child = True
has_private_owndir = True
######################################################

modename = 'csv_pathmode'
pathname = 'csv_path'
extname = 'csv_ext'
wildcard = 'csv(*.csv)|*.csv|Any|*'


def init(self, *args, **kargs):
    #   a function called when py_module is initialized
    self.td.mk_owndir()
    if 'src' not in kargs:
        self.onLoadFile()


def load_csv_file(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    if file == '':
        return
    # clean first

    for name, child in obj.get_children():
        child.destroy()

    import csv

    with open(file, 'rU') as csvfile:
        spamreader = csv.reader(csvfile, dialect='excel')
#                                delimiter=' ', quotechar='|')
        keys = next(spamreader)
        d = {k: [] for k in keys}
        for row in spamreader:
            for k, num in zip(keys, row):
                d[k].append(num)

    from ifigure.mto.py_code import PyData

    data = PyData()
    obj.add_child('data', data)
    for k in d:
        data.setvar(k, d[k])
#    nm = load_file(file)
#    if nm is None:
#         obj.setvar0(None)
#         return
#    obj.setvar0(d)


def export_csvfile(obj, filename):
    import csv
    var = obj.data.getvar()
    names = list(var.keys())
    with open(filename, 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|')# quoting=csv.QUOTE_MINIMAL)
        print(names)
        spamwriter.writerow(names)
        for k in range(len(var[names[0]])):
            data = [var[n][k] for n in names]
            spamwriter.writerow(data)


def onWriteFile(self, e=None):
    from ifigure.utils.addon_utils import onWriteFile
    app = wx.GetApp().TopWindow
    obj = self.td
    file = obj.get_root_parent().getvar('filename')
    if file is None:
        file = obj.path2fullpath(modename=modename,
                                 pathname=pathname)
    open_dlg = wx.FileDialog(app,
                             message='Save .csv file',
                             defaultDir=os.path.dirname(file),
                             defaultFile='untitled.csv',
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                             wildcard=wildcard)

    if open_dlg.ShowModal() != wx.ID_OK:
        open_dlg.Destroy()
        return
    else:
        filename = str(open_dlg.GetPath())
        open_dlg.Destroy()
    export_csvfile(obj, filename)


def onUpdateTree(self, e=None):
    obj = self.td
    load_csv_file(obj)


def onLoadFile(self, e=None, file=''):
    from ifigure.utils.addon_utils import onLoadFile

    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname)
        ret = True
    else:
        ret = onLoadFile(self.td, message="Select CSV File",
                         modename=modename,
                         pathname=pathname,
                         extname=extname,
                         wildcard='csv(*.csv)|*.csv|Any|*',
                         ask_org_copy=True)
    if ret:
        load_csv_file(self.td)
        ifigure.events.SendChangedEvent(self.td)


def init_after_load(self, olist, nlist):
    obj = self.td
    # load_csv_file(obj)


def ask_field(self, dest):
    vars = self.td.data.getvar()
    list6 = [["", "Select field to convert", 2],
             [None, None, 36, {'col': 4, 'labels': list(vars.keys())}], ]
    value = DialogEditList(list6, modal=True,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                           tip=None,
                           title="Convert to "+dest,
                           parent=self.td.get_app())
    checked = [x for x, b in value[1][1] if b]
    return value[0], checked


def onConvStr(self, evt):
    def conv(data, name):
        d = [str(x) for x in data.eval(name)]
        data.setvar(name, np.array(d))
    value, checked = self.ask_field('String')
    if value:
        for x in checked:
            conv(self.td.data, str(x))


def onConvFloat(self, evt):
    def conv(data, name):
        d = [float(x) for x in data.eval(name)]
        data.setvar(name, np.array(d).astype(float))
    value, checked = self.ask_field('Float')
    if value:
        for x in checked:
            conv(self.td.data, str(x))


def onConvInt(self, evt):
    def conv(data, name):
        d = [float(x) for x in data.eval(name)]
        data.setvar(name, np.array(d).astype(int))
    value, checked = self.ask_field('Integer')
    if value:
        for x in checked:
            conv(self.td.data, str(x))
