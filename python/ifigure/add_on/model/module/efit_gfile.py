from __future__ import print_function

'''
  read gfile

     2015 09 22
        Sign of Bt and Ip is positive when it orients
        to anti-clockwise direction when viewing the tokamak
        from top to bottom.

        gfile cpasma and bcnter is negative when they
        are clockwise (viewing from top)
        IOW, gfile uses the R, phi, Z cylindrical coordinate system.
       
        In gfile, psi is written as if it is always 
        increase from the center to the edge. For positive
        current (in the R, phi, Z cylindrical coordinate system),
        psi should DECREASE as it goes outward to have a 
        correct sign of Br, Bz. This module, flipps the sign 
        of psirz, ffprim, and pprime when Ip in g-file header
        is >0. Note that safety factor is still always positive.

     2015 10 20
        some gfile can have a different mesh size for fpol, q and
        others. in this case, the first line of file has the third
        mesh size number

'''

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
from ifigure.utils.edit_list import DialogEditList
from ifigure.mto.py_contents import Efitgfile
import numpy as np
######################################################
#         Setting for module file for py_module
#   name of module/class
module_name = 'EFIT_Gfile'
class_name = 'EFIT_Gfile'
#   module_evt_handler
#   functions which can be called from project tree
#
#    (menu name, function name, a flat to call skip()
#     after running function)
#

menu = [("Import File...", "onLoadFile", True),
        ("Export File...", "onWriteFile", True),
        ("Update File...", "onUpdateFile", True),
        ("Update Tree...", "onUpdateTree", True),
        ("Plot Equilibrium", "onPlotEq", True),
        ("Plot MidPlane", "onPlotMid", True),
        ("+Modify...", None,  False),
        ("Scale Bt...", "onScaleBt",  False),
        ("Scale Ip...", "onScaleIp",  False),
        ("!", None, False),
        ("+TextEditor...", None,  False),
        ("View Original File", "onOpenOrg", False),
        ("Edit File", "onOpenCurrent", False),
        ("!", None, False)]
method = ['scale_b', 'scale_i', 'scale_p', 'init',
          'txt2tree', 'tree2txt',
          'onLoadFile', 'onWriteFile', 'onPlotEq',
          'onOpenOrg', 'onOpenCurrent', 'onScaleBt', 'onScaleIp',
          'onPlotMid', 'onUpdateFile', 'onUpdateTree']

icon = 'data.png'
can_have_child = False
has_private_owndir = False
######################################################
modename = 'gfile_pathmode'
pathname = 'gfile_path'
extname = 'gfile_ext'


def string_split_ig(s, sep):
    return [x for x in re.split(sep, s) if x != '']

    '''
    print("here", s, sep, t)
    for i in reversed(range(len(t))):
        if t[i] == '':
            del t[i]
    return t
    '''
def eval_form2020(s):
    #form2020= '(5e16.9)'
    d = 16
    ret = []
    for i in range(5):
        #     print s[d*i:d*(i+1)],s[d*i:d*(i+1)].strip().__repr__()
        if s[d*i:d*(i+1)].strip() != '':
            ret.append(float(s[d*i:d*(i+1)]))
    return ret


def readandstrip(f):
    line = ''
    count = 0
    while line == '':
        line = f.readline()
        line = line.rstrip("\r\n")
        count = count + 1
        if count > 5:
            return ''

    return line


def make_form2020(array):
    line0 = []
    line = ''
    i = 0
    while i < len(array):
        line = line+'{: 13.9e}'.format(array[i])
        i = i+1
        if (i % 5) == 0:
            line0.append(line)
            line = ''

    if len(line) != 0:
        line0.append(line)

    return line0


def load_array_form2020(f, size):
    k = 0
    arr = []
    while (k < size):
        arr = arr+eval_form2020(readandstrip(f))
        k = k+5
    return np.array(arr)


def load_matrix_form2020(f, size1, size2):
    k = 0
    arr = []
    while k < size1*size2:
        arr = arr+eval_form2020(readandstrip(f))
        k = k+5
    return np.array(arr).reshape(size1, size2)


def add_extra_data(val):
    fpol = val['fpol']
    isPlasma = val['isPlasma']
    psirz = val['psirz']
    ssimag = val['ssimag']
    ssibdry = val['ssibdry']
    ssibry = val['ssibry']

    xpsi = (val['psirz']-val['ssimag'])/(val['ssibdry']-val['ssimag'])
    for m, xv in enumerate(val['rgrid']):
        for n, yv in enumerate(val['zgrid']):
            if not isPlasma[n, m]:
                xpsi[n, m] = 1.0
    rgrid = val['rgrid']
    zgrid = val['zgrid']
    xx, yy = np.meshgrid(rgrid, zgrid)

    xxx = np.linspace(0, 1, fpol.shape[0])
    fp = np.interp(xpsi.flatten(), xxx, val['fpol'])
    fp = fp.reshape(xx.shape)
    fc = np.interp(xpsi.flatten(), xxx, val['ffprim'])
    fc = fc.reshape(xx.shape)
    pr = np.interp(xpsi.flatten(), xxx, val['pres'])
    pr = pr.reshape(xx.shape)
    pc = np.interp(xpsi.flatten(), xxx, val['pprime'])
#   this is to check if pprime is computed correctly in ACCOME
#   psimesh = np.linspace(ssimag, ssibry, len(val['pres']))
#   pc = np.interp(xpsi.flatten(), xxx,
#                 np.gradient(val['pres'])/np.gradient(psimesh))
    pc = pc.reshape(xx.shape)
    qr = np.interp(xpsi.flatten(), xxx, val['qpsi'])
    qr = qr.reshape(xx.shape)

    pr[isPlasma != True] = 0.0
    pc[isPlasma != True] = 0.0
    fc[isPlasma != True] = 0.0
    val["pressrz"] = pr
    val["qrz"] = qr
    val["btrz"] = fp/xx

    dpsidz, dpsidr = np.gradient(psirz)
    brrz = -dpsidz/(zgrid[1]-zgrid[0])/xx
    bzrz = dpsidr/(rgrid[1]-rgrid[0])/xx
    val["brrz"] = brrz
    val["bzrz"] = bzrz

    mu0 = 4e-7*3.1415926535
    val["jtrz"] = (xx*pc+fc/xx/mu0)/1e6  # 1e6=(MA/m2)

    k = (val["zmaxis"] - rgrid[0])/(rgrid[1] - rgrid[0])
    from scipy.interpolate import interp2d

    f = interp2d(rgrid, zgrid, psirz, kind='cubic')
    val['npsimid'] = np.array([(f(r, val["zmaxis"]) - ssimag)/(ssibry - ssimag)
                               for r in rgrid]).flatten()
    f1 = interp2d(rgrid, zgrid, val["btrz"], kind='cubic')
    f2 = interp2d(rgrid, zgrid, val["bzrz"], kind='cubic')
    val['gammamid'] = np.array([np.arctan(f2(r, val["zmaxis"])
                                          / f1(r, val["zmaxis"]))*180/3.1415926
                                for r in rgrid]).flatten()
    val['bzmid'] = np.array([f2(r, val["zmaxis"])
                             for r in rgrid]).flatten()
    val['btmid'] = np.array([f1(r, val["zmaxis"])
                             for r in rgrid]).flatten()
    f = interp2d(rgrid, zgrid, val["jtrz"], kind='cubic')
    val['jtmid'] = np.array([f(r, val["zmaxis"])
                             for r in rgrid]).flatten()
    f = interp2d(rgrid, zgrid, val["pressrz"], kind='cubic')
    val['pressmid'] = np.array([f(r, val["zmaxis"])
                                for r in rgrid]).flatten()
    f = interp2d(rgrid, zgrid, val["qrz"], kind='cubic')
    val['qmid'] = np.array([f(r, val["zmaxis"])
                            for r in rgrid]).flatten()


def load_file(file=None):
    def is_ascii(s):
        return all([ord(c) < 128 for c in s])
        '''
        try:
            s.decode('ascii')
        except:
            return False
        return True
        '''
#   file='/home/shiraiwa/g1101019014.01340'
    f = open(file, 'r')

    line = f.readline()
    line = line.rstrip("\r\n")
    tmp = string_split_ig(line[49:], ' |,')

    header = line[:48]
    idum = int(tmp[0])
    mw = int(tmp[1])
    mh = int(tmp[2])
    mw2 = mw
    if len(tmp) == 4:
        try:
            mw2 = int(tmp[3])
            if mw2 == 0:
                mw2 = mw
        except:
            pass

    xdim, zdim, rzero, rgrid1, zmid = eval_form2020(readandstrip(f))
    rmaxis, zmaxis, ssimag, ssibdry, bcentr = eval_form2020(readandstrip(f))
    cpasma, ssimag, xdum, rmaxis, xdum = eval_form2020(readandstrip(f))
    zmaxis, xdum, ssibry, xdum, xdum = eval_form2020(readandstrip(f))

    fpol = load_array_form2020(f, mw2)
    pres = load_array_form2020(f, mw2)
    ffprim = load_array_form2020(f, mw2)
    pprime = load_array_form2020(f, mw2)

    psirz = load_matrix_form2020(f, mh, mw)
    qpsi = load_array_form2020(f, mw2)

    try:
        nbbbs, limitr = string_split_ig(readandstrip(f), ' |,')
    # print nbbbs, limitr
        nbbbs = int(nbbbs)
        limitr = int(limitr)
        if nbbbs != 0:
            rzbbbs = load_matrix_form2020(f, nbbbs, 2)

        xylim = load_matrix_form2020(f, limitr, 2)
    except:
        limitr = 0
        nbbbs = 0
        rzbbbs = np.zeros((2, 1))
        xylim = np.zeros((2, 1))

    rgrid = rgrid1 + xdim*np.arange(mw)/(mw-1.)
    zgrid = zmid-0.5*zdim + zdim*np.arange(mh)/(mh-1.)

    nm = Efitgfile()

    psirzraw = psirz.copy()
    if cpasma > 0:
        sss = -1
        ssimag = ssimag*sss
        ssibdry = ssibdry*sss
        ssibry = ssibry*sss
        psirz = psirz*sss
        ffprim = ffprim*sss
        pprime = pprime*sss

    nm["table"] = {}
    val = nm["table"]
    val["header"] = header
    val["idum"] = idum
    val["mw"] = mw
    val["mh"] = mh
    val["xdim"] = xdim
    val["zdim"] = zdim
    val["rzero"] = rzero
    val["rgrid1"] = rgrid1
    val["zmid"] = zmid
    val["rmaxis"] = rmaxis
    val["zmaxis"] = zmaxis
    val["ssimag"] = ssimag
    val["ssibdry"] = ssibdry
    val["bcentr"] = bcentr
    val["cpasma"] = cpasma
    val["ssibry"] = ssibry

    val["rgrid"] = rgrid
    val["zgrid"] = zgrid
    val["psirz"] = psirz
    val["psirzraw"] = psirzraw
    val["fpol"] = fpol
    val["pres"] = pres
    val["ffprim"] = ffprim
    val["pprime"] = pprime
    val["qpsi"] = qpsi
    val["nbbbs"] = nbbbs
    if nbbbs > 0:
        val["rbbbs"] = rzbbbs[:, 0]
        val["zbbbs"] = rzbbbs[:, 1]
    else:
        from python_lib.analysis.efit_tools import find_psi_contour
        rzbbbs = find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis,
                                  ssibry, return_all=False)

        nbbbs = rzbbbs.shape[0]
        val["nbbbs"] = nbbbs
        val["rbbbs"] = rzbbbs[:, 0]
        val["zbbbs"] = rzbbbs[:, 1]
    val["nlim"] = limitr
    if limitr > 0:
        val["xlim"] = xylim[:, 0]
        val["ylim"] = xylim[:, 1]
    else:
        val["xlim"] = []
        val["ylim"] = []
    # else:
    #   return nm
    # namelist section
    sec = None
    end_flag = False

    while 1:
        line0 = f.readline()
        if not is_ascii(line0):
            continue
        if not line0:
            break
        line0 = line0.rstrip("\r\n")
        line0 = ' '.join(line0.split())
        if line0.endswith('/'):
            line = line0[:-1]
        else:
            line = line0

        if line == '':
            continue
        if line.startswith('&'):
            s = string_split_ig(line, ' |,')
            sec = s[0][1:]
            print('making new sec ', sec, line.__repr__(), s)
            nm[sec] = OrderedDict()
            if len(s) > 1:
                line = ' '.join(s[1:])
            else:
                continue
        if sec is None:
            continue  # skip unitl first &*** starts
        sall = string_split_ig(line, ' |,')

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
                    i = i+1
                    continue  # 'name='
                k = sall[i].split('=')
                sall[i] = k[0]+'='
                sall.insert(i+1, k[1])
            i = i+1

        for s in sall:
            if s.find('=') != -1:
                k = s.split('=')
                varname = k[0]
#          s[0]=k[1]
#          print s
#          if s[0] is '': del s[0]
                if debug != 0:
                    print(('create dict key', sec, varname))
                # print 'create dict key', sec, varname
                nm[sec][varname] = []
                if s.endswith('/'):
                    sec = None
                continue
        # for lines without 'xxxx = '
            # print s, sec, varname
            nm[sec][varname] = nm[sec][varname]+parseStr(s)
        if line0.endswith('/'):
            sec = None
    xx, yy = np.meshgrid(rgrid, zgrid)
#   isPlasma = xx.copy()
    sss = len(rgrid)*len(zgrid)
    isPlasma = np.array([False]*sss).reshape(len(zgrid), len(rgrid))
    for m, xv in enumerate(rgrid):
        for n, yv in enumerate(zgrid):
            dx = rzbbbs[:, 0] - xv
            dy = rzbbbs[:, 1] - yv
            d1 = np.sqrt(dx[:-1]**2 + dy[:-1]**2)
            d2 = np.sqrt(dx[1:]**2 + dy[1:]**2)

            d = (dx[:-1]*dy[1:] - dx[1:]*dy[:-1])/d1/d2
            d = d[np.abs(d) < 1.0]
            xxxx = sum(np.arcsin(d))
            isPlasma[n, m] = (np.abs(xxxx) > 3)
#              print isPlasma[n, m] > 3
#   val['isPlasma0'] = isPlasma
#   print 'here'
#   isPlasma =  np.abs(isPlasma) > 3
    val["isPlasma"] = isPlasma

    try:
        add_extra_data(val)
    except:
        print("can't evaulate extra info")

    return nm
#   return val, nm,  header

# def add_gfile_2_tree(self_obj):


def scale_p(self, factor=None):

    td = self.td
    if factor is None:
        list = [["", "Enter P Scale Factor", 2],
                ["P sclae", str(1), 0]]

        flag, value = DialogEditList(list)
        if flag:
            factor = float(value[1])
        else:
            return

    print(('Pres scale by', str(factor)))
    td[:]["table"]["pres"] *= factor
    td[:]["table"]["pressmid"] *= np.abs(factor)
    td[:]["table"]["pressrz"] *= factor
    td[:]["table"]["pprime"] *= factor
    add_extra_data(td[:]["table"])
    print('Updating g-file')
    self.onUpdateFile()


def scale_b(self, factor=None):

    td = self.td
    if factor is None:
        list = [["", "Enter Bt Scale Factor", 2],
                ["Bt sclae", str(1), 0]]

        flag, value = DialogEditList(list)
        if flag:
            factor = float(value[1])
        else:
            return

    print(('Bt scale by', str(factor)))

    td[:]["table"]["ffprim"] *= factor*factor
    td[:]["table"]["fpol"] *= factor
    td[:]["table"]["qpsi"] *= np.abs(factor)
    td[:]["table"]["bcentr"] *= factor
    add_extra_data(td[:]["table"])
    print('Updating g-file')
    self.onUpdateFile()


def scale_i(self, factor=None):

    td = self.td
    if factor is None:
        list = [["", "Enter Ip Scale Factor", 2],
                ["Ip sclae", str(1), 0]]

        flag, value = DialogEditList(list)
        if flag:
            factor = float(value[1])
        else:
            return

    print(('Ip scale by', str(factor)))

    td[:]["table"]["psirz"] *= factor
    td[:]["table"]["qpsi"] *= np.abs(1./factor)
    td[:]["table"]["cpasma"] *= factor
    td[:]["table"]["ssibry"] *= factor
    td[:]["table"]["ssibdry"] *= factor
    td[:]["table"]["ssimag"] *= factor
    add_extra_data(td[:]["table"])
    print('Updating g-file')
    self.onUpdateFile()


def onScaleIp(self, evt):
    self.scale_i()


def onScaleBt(self, evt):
    self.scale_b()


def init(self, *args, **kargs):
    if "src" not in kargs:
        self.onLoadFile(file='')


def load_gfile(obj):
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
    if not self.td.has_owndir():
        self.td.mk_owndir()

    if os.path.basename(filename) == filename:
        path = os.path.join(self.td.owndir(), filename)
    else:
        path = filename

    fid = open(path, 'w')
    fid.write(txt)
    fid.close()

    self.td.set_path_pathmode(path, modename, pathname, extname)
    load_gfile(self.td)


def tree2txt(self, filename=''):
    '''
    make tree to txt and update owndir file
    '''

    self_obj = self.td

    txt = ['']

    table = self_obj[:]["table"]

    header = table["header"]
    idum = table["idum"]
    mh = table["mh"]
    mw = table["mw"]

    l0 = table["header"] + \
        '{: 4d}'.format(idum)+'{: 4d}'.format(mw)+'{: 4d}'.format(mh)

    xdum = 0
    if table["cpasma"] > 0:
        sss = -1
    else:
        sss = 1

    l1 = make_form2020([table["xdim"],
                        table["zdim"],
                        table["rzero"],
                        table["rgrid1"],
                        table["zmid"]])

    l2 = make_form2020([table["rmaxis"],
                        table["zmaxis"],
                        table["ssimag"]*sss,
                        table["ssibdry"]*sss,
                        table["bcentr"]])

    l3 = make_form2020([table["cpasma"],
                        table["ssimag"]*sss,
                        xdum,
                        table["rmaxis"],
                        xdum])

    l4 = make_form2020([table["zmaxis"],
                        xdum,
                        table["ssibry"]*sss,
                        xdum,
                        xdum])

    txt.append(l0+"\n")
    txt.append(l1[0]+"\n")
    txt.append(l2[0]+"\n")
    txt.append(l3[0]+"\n")
    txt.append(l4[0]+"\n")

    for field in ["fpol", "pres", "ffprim", "pprime", "psirz", "qpsi"]:
        value = table[field]
        if field in ['psirz', 'ffprim', 'pprime']:
            value = value*sss
        for line in make_form2020(value.flatten()):
            txt.append(line+"\n")

    nbbbs = table["nbbbs"]
    nlim = table["nlim"]
    l5 = '{: 5d}'.format(nbbbs)+'{: 5d}'.format(nlim)

    txt.append(l5+"\n")

    r = table["rbbbs"]
    z = table["zbbbs"]
    c = concatenate((r, z))
    rzbbbs = c.reshape(2, len(r)).transpose().flatten()
    for line in make_form2020(rzbbbs):
        txt.append(line+"\n")
    r = table["xlim"]
    z = table["ylim"]
    c = concatenate((r, z))
    xylim = c.reshape(2, len(r)).transpose().flatten()
    for line in make_form2020(xylim):
        txt.append(line+"\n")

    txt2 = ''.join(txt)
    return txt2


def onUpdateTree(self, event=None):
    load_gfile(self.td)


def onLoadFile(self, e=None, file=''):
    from ifigure.utils.addon_utils import onLoadFile

    if file != '':
        self.td.set_path_pathmode(file, modename, pathname, extname)
        ret = True
    else:
        cwd = os.getcwd()
        if self.td.has_owndir():
            os.chdir(self.td.owndir())
        try:
            ret = onLoadFile(self.td, message="Select G-File",
                             modename=modename,
                             pathname=pathname,
                             extname=extname)
        except:
            import traceback
            traceback.print_exc()
            pass
        os.chdir(cwd)

    if not ret:
        return False

    load_gfile(self.td)


def onWriteFile(self, e=None, filename=''):
    from ifigure.utils.addon_utils import onWriteFile

    txt = self.tree2txt()
    onWriteFile(self.td, filename=filename,
                txt=txt,
                message='Enter G-file Name',
                wildcard='G-file(g*.*)|g*.*|Any|*')


def onUpdateFile(self, event=None):
    file = self.td.path2fullpath(modename=modename,
                                 pathname=pathname)
    self.onWriteFile(filename=file)


def onOpenOrg(self, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenOrg
    onOpenOrg(self.td)


def onOpenCurrent(self, *args, **kargs):
    from ifigure.utils.addon_utils import onOpenCurrent
    onOpenCurrent(self.td, modename=modename,
                  pathname=pathname)


def onPlotMid(self, e=None):
    self_obj = self.td

    if self_obj.getvar0() is None:
        return
    proj = self_obj.get_root_parent()
    from ifigure.interactive import figure

    v = figure()
    v.nsec(1, 5)

    path = self_obj.get_full_path()
    x = self_obj[:]["table"]["rgrid"]
    y = self_obj[:]["table"]["zgrid"]
    psi = self_obj[:]["table"]["psirz"]
    ssimag = self_obj[:]["table"]["ssimag"]
    ssibdry = self_obj[:]["table"]["ssibdry"]

    fpol = self_obj[:]["table"]["fpol"]
    pprime = self_obj[:]["table"]["pprime"]
    ffprim = self_obj[:]["table"]["ffprim"]
    pres = self_obj[:]["table"]["pres"]
    qpsi = self_obj[:]["table"]["qpsi"]

    zmaxis = self_obj[:]["table"]["zmaxis"]

    btmid = self_obj[:]["table"]["btmid"]
    #brmid = self_obj[:]["table"]["brmid"]
    bzmid = self_obj[:]["table"]["bzmid"]
    jtmid = self_obj[:]["table"]["jtmid"]
    pressmid = self_obj[:]["table"]["pressmid"]
    qmid = self_obj[:]["table"]["qmid"]

    nr = psi.shape[1]
    dr = x[1]-x[0]
    dz = y[1]-y[0]
#    br = psi[:][j+1]
    j = psi.shape[0]//2
    psi_mid = psi[:][j]
    psi_mid = array([interp(zmaxis, y, psi[:, i]) for i in range(nr)])

    v.update(False)
    v.isec(0)
    obj = v.plot(x, bzmid)
    v.title("$B_{\mathrm{tor, z}}\/\mathrm{(T)}$")
    obj._name = 'bz'
    # obj=FigPlot(x,bzmid)
    #axes.add_child('bz', obj)
    obj = v.plot(x, btmid)
    obj._name = 'bt'
#    obj=FigPlot(x,sqrt(bt_mid*bt_mid+br_mid*br_mid+bz_mid*bz_mid))
#    axes.add_child('ball', obj)

    v.isec(1)
    v.title("$J_{\mathrm{tor}}\/\mathrm{(MA/m^2)}$")
    obj = v.plot(x, jtmid)
    obj._name = 'jtor'

    v.isec(2)
    v.title("$P\/\mathrm{(MPa)}$")
    obj = v.plot(x, pressmid/1e6)
    obj._name = 'pres'

    v.isec(3)
    v.title("$\mathrm{safety\,factor}$")
    obj = v.plot(x, qmid)
    obj._name = 'qpsi'

    v.isec(4)
    v.title("pitch angle")
    obj = v.plot(x, -np.arctan2(bzmid, btmid)*180/np.pi)
    obj._name = 'gamma'

    v.update(True)
#    app=self_obj.get_root_parent().app

#    app.show_page(0)


def onPlotEq(self, e=None, viewer=None):
    self_obj = self.td
    if self_obj.getvar0() is None:
        return

    path = self_obj.get_full_path()
    x = self_obj.get_contents("table", "rgrid")
    y = self_obj.get_contents("table", "zgrid")
    z = self_obj.get_contents("table", "psirz")
    try:
        xlim = self_obj.get_contents("table", "xlim")
        ylim = self_obj.get_contents("table", "ylim")
        rb = self_obj.get_contents("table", "rbbbs")
        zb = self_obj.get_contents("table", "zbbbs")
        fpol = self_obj.get_contents("table", "fpol")
        ssimag = self_obj.get_contents("table", "ssimag")
        ssibdry = self_obj.get_contents("table", "ssibdry")
        btrz = self_obj.get_contents("table", "btrz")
        brrz = self_obj.get_contents("table", "brrz")
        bzrz = self_obj.get_contents("table", "bzrz")
        jtrz = self_obj.get_contents("table", "jtrz")
        bnorm = sqrt(btrz**2+brrz**2+bzrz**2)
        bp = sqrt(brrz**2+bzrz**2)
        bangle = np.arctan2(bp, bnorm)
#       isPlasma = self_obj.get_contents("table", "isPlasma")
        no_lim_b = False
    except:
        no_lim_b = True

    rmaxis = self_obj.get_contents("table", "rmaxis")
    zmaxis = self_obj.get_contents("table", "zmaxis")

    if viewer is None:
        from ifigure.interactive import figure
        plt = figure()
    else:
        plt = viewer
        plt.cls()
    plt.update(False)

    plt.subplot(4, 3, [0, 1, 2, 3], [4, 5, 6, 7])
    plt.isec(4)
    plt.image(x, y, z, alpha=0.5)
    plt.contour(x, y, z, 30)
    if eval('self_obj[:]["table"]["nlim"]') != 0:
        plt.plot(xlim, ylim)
    if eval('self_obj[:]["table"]["nbbbs"]') != 0:
        plt.plot(rb, zb)
    plt.xlabel('R')
    plt.ylabel('Z')
    plt.title('PSI')

    if not no_lim_b:
        plt.isec(5)
        plt.title('B-norm')
        plt.image(x, y, bnorm, alpha=0.5)
        plt.contour(x, y, bnorm, 30)
        if self_obj[:]["table"]["nlim"] > 0:
            plt.plot(xlim, ylim)
        if self_obj[:]["table"]["nbbbs"] > 0:
            plt.plot(rb, zb)
        plt.xlabel('R')
        plt.ylabel('Z')

    plt.isec(0)
    pres = self_obj.get_contents("table", "pres")

    plt.plot(pres)
    plt.title('pressure')
    plt.xlabel('flux index')

    plt.isec(1)
    qpsi = self_obj.get_contents("table", "qpsi")
    plt.plot(qpsi)
    plt.title('qpsi')
    plt.xlabel('flux index')

    plt.isec(2)
    fpol = self_obj.get_contents("table", "fpol")
    plt.plot(fpol)
    plt.title('f_pol')
    plt.xlabel('flux index')
    plt.update(True)

    if no_lim_b:
        return
    from python_lib.analysis.efit_tools import flux_average, npsi2psi, npsi2npsit

    npsis = np.linspace(0.02, 0.99, 20)
    psis = [npsi2psi(self_obj, npsi) for npsi in npsis]
    sqrt_npsit = [np.sqrt(npsi2npsit(self_obj, npsi)) for npsi in npsis]
    jtor = [flux_average(x, y, z, rmaxis, zmaxis, jtrz, psi)
            for psi in psis]
    plt.isec(3)
    plt.plot(sqrt_npsit, jtor)
    plt.title('j_tor')
    plt.xlabel('sqrt_toroidal_flux')
    plt.update(True)
