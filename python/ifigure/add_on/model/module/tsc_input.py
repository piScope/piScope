from __future__ import print_function
import numpy as np
from ifigure.mto.py_contents import Namelist, TSCInputFile
from collections import OrderedDict
import os
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
module_name = 'tscinput_module'
class_name = 'tscinput_module'
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
menu = [("Import File...", "onLoadFile", True),
        ("Export File...", "onWriteFile", False),
        ("Update File", "onUpdateFile", False),
        ("Update Tree", "onUpdateTree", True),
        ("Plot Time Dependent Signals", "onPlotTimeDep", False),
        ("+TextEditor...", None,  False),
        ("View Original", "onOpenOrg", False),
        ("Edit File", "onOpenCurrent", False),
        ("!", None, False)]

method = ['tree2txt', 'onPlotTimeDep', 'onGenerateRestartInput',
          'onLoadFile', 'onWriteFile', 'onOpenOrg',
          'onOpenCurrent', 'onUpdateFile', 'onUpdateTree',
          'init']
icon = 'text.png'
######## Do not chage this field ####################
can_have_child = False
has_private_owndir = False
######################################################
modename = 'namelist_pathmode'
pathname = 'namelist_path'
extname = 'namelist_ext'


def init(self, *args, **kargs):
    if 'src' not in kargs:
        self.onLoadFile()


def split_line(s):
    #form2020= '(8e10.?)'
    d = 10
    ret = []
    for i in range(8):
        if s[d*i:d*(i+1)] != '':
            ret.append(s[d*i:d*(i+1)])
    return ret


def convert_array(arr):
    arr[0] = arr[0][0:2]
    for x in range(len(arr)-1):
        if arr[x+1].strip() == '':
            arr[x+1] = None
        else:
            arr[x+1] = float(arr[x+1])
    return arr


def load_file(file):
    fid = open(file, 'r')
    lines = fid.readlines()
    c = 0
#    nm = Namelist()
    nm = TSCInputFile()

    for line in lines:
        if line.startswith('!'):
            continue
        if line.startswith('c'):
            continue
        line = line.rstrip("\r\n")
        arr = split_line(line)
        try:
            arr = convert_array(arr)
            if arr[0] in nm:
                nm[arr[0]]['data'] = nm[arr[0]]['data'] + [arr[1:], ]
            else:
                d = TSCInputFile()
                d['data'] = [arr[1:], ]
                nm[arr[0]] = d
        except:
            print('conversion error of following line')
            print(line)
            print(arr)
        c = c+1
#        if c>20: break
    fid.close()

    if '11' in nm:
        # for acoef array
        od = nm['11']['data']
        d = TSCInputFile()
        for x in od:
            print(x)
            for i in range(int(x[1])):
                x = x + [0, 0, 0, 0, 0]  # safe gurad...
                label = ('0000'+str(int(x[0]+i)))[-4:]
                d[label] = x[2+i]
        d = TSCInputFile(sorted(list(d.items()), key=lambda t: t[0]))
        nm['11'] = d

    nm = TSCInputFile(sorted(list(nm.items()), key=lambda t: t[0]))
    nm = add_help(nm)
    return nm


def add_help(nm):
    import ifigure
    hfile = os.path.join(os.path.dirname(ifigure.__file__),
                         'add_on', 'model', 'module', 'tscinput_help.txt')
    d = {}
    fid = open(hfile, 'r')
    for line in fid.readlines():
        xy = line.split('\t')
        if len(xy) < 2:
            continue
        x = xy[0]
        y = xy[1]
        d[x[0:2]] = (x[2:].strip(), y)

    for key in nm:
        if key in d:
            nm[key]['name'] = d[key][0]
            nm[key]['format'] = d[key][1]
    nm._help = d
    return nm

#   file='/home/shiraiwa/PycharmProjects/ifigure/sample/genray.in'


def load_tscinputfile(obj):
    file = obj.path2fullpath(modename=modename,
                             pathname=pathname)

    if file == '':
        return

    for name, child in obj.get_children():
        child.destroy()

    nm = load_file(file)

    print(('reading file', file))
    obj.setvar0(nm)

# def fromat_float(num):
#'{: 10.2e}'.format(item)


def tree2txt(self, var0=None):
    def data2lines(key, data):
        lines = []
        for d in data:
            l = key + ' '*(10-len(key))

            for item in d:
                if item is None:
                    l = l + ' '*10
                else:
                    txt = '{: 10.3e}'.format(item)
                    # len(txt)
                    l = l + '{: 10.3e}'.format(item)
            lines.append(l+'\n')
        return lines

    def data2lines_11(key, data):
        lines = []
        for d in data:
            l = str(int(key))
            l = l + ' '*(10-len(l))
            for item in d:
                if item is None:
                    l = l
                else:
                    txt = '{: 10.3e}'.format(item)
                    # len(txt)
                    l = l + txt
            lines.append(l+'\n')
        return lines

    if var0 is None:
        var0 = self.td.getvar0()
    txt = ['c ... title card\n', 'c produced by piscope input generator\n', 'c\n']

    for key0 in list(var0.keys()):
        if key0 == '11':
            for key1 in var0[key0]:
                if key1 == 'name':
                    continue
                if key1 == 'format':
                    continue
                txt.extend(data2lines_11(
                    key0, [[int(key1), 1, var0[key0][key1]]]))
        else:
            txt.extend(data2lines(key0, var0[key0]['data']))

    txt2 = ''.join(txt)
    return txt2


def onGenerateRestartInput(self, e=None, filename='inputa',
                           update_card=None, stop_time=None):
    print(('here', update_card, stop_time))
    var0 = self.td.getvar0()
    if update_card is not None:
        d = TSCInputFile()
        d['00'] = var0['00']
        d['00']['data'][0][0] = 1.0  # restart
        for x in update_card:
            d[x] = var0[x]
        if stop_time is not None:
            d['11'] = TSCInputFile()
            d['11']['0029'] = float(stop_time)
        d['99'] = var0['99']
    txt = self.tree2txt(var0=d)
    filename = os.path.join(self.td.owndir(), filename)
    print(filename)
    self.onWriteFile(e=None, filename=filename, txt=txt)


def onUpdateTree(self, e=None):
    obj = self.td
    load_tscinputfile(self.td)


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
        load_tscinputfile(self.td)


def onWriteFile(self, e=None, filename='', txt=None):
    from ifigure.utils.addon_utils import onWriteFile

    if txt is None:
        txt = self.tree2txt()
    onWriteFile(self.td, filename=filename,
                txt=txt,
                message='Enter Namelist File Name')


def onUpdateFile(self, e=None, *args, **kargs):
    file = self.td.path2fullpath(modename=modename,
                                 pathname=pathname)
    self.onWriteFile(filename=file)


def onOpenOrg(self, e=None, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenOrg
    onOpenOrg(self.td)


def onOpenCurrent(self, e=None, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenCurrent
    onOpenCurrent(self.td, modename=modename,
                  pathname=pathname)


def onPlotTimeDep(self, e=None, *args, **kargs):
    def plot_data(time, data):
        x = np.array(time, dtype='float').flatten()
        y = np.array(data, dtype='float').flatten()

        x = [t for t in x if not np.isnan(t)]
        y = [t for t in y if not np.isnan(t)]

        return np.array(x), np.array(y)

    help = self.td._var0._help
    data = self.td._var0
    import ifigure.interactive as plt

    plt.figure()
    time = data['18']['data']
    new_plot = True
    for key in help:
        if not key in data:
            continue
        if key == '18':
            continue
        x, y = help[key]
        if y.startswith('-'):
            if not new_plot:
                plt.addpage()
            try:
                xdata, ydata = plot_data(time, data[key]['data'])
                plt.plot(xdata, ydata)
                plt.title(x)
                new_plot = False
            except:
                print(('failed to generate picture for', key))
                new_plot = True
    pass
