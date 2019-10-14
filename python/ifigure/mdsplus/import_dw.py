import sys
import wx
import time
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('import_dw')

replace_shot = True


def interpret_globals(com, var, globals):
    globals[com] = var.strip()
    return globals


def interpret_globals_int(com, var, globals):
    globals[com] = int(var)
    return globals


def interpret_plots(com1, com2, var, plots, use_int=False):
    a = com1.split('_')
    c = int(a[2])-1
    r = int(a[1])-1
    if len(plots) <= c:
        return plots
    if len(plots[c]) <= r:
        return plots
    if use_int:
        plots[c][r][com2] = int(var)
    else:
        plots[c][r][com2] = var.strip()
#    print c, r, com2, var
    return plots


def import_dw(file=''):
    if file == '':
        open_dlg = wx.FileDialog(None, message="Select DWscope to open",
                                 wildcard='*.dat', style=wx.FD_OPEN)
        if open_dlg.ShowModal() == wx.ID_OK:
            file = open_dlg.GetPath()
            open_dlg.Destroy()
        else:
            return [None, None, None, None, None]

    f = open(file, 'r')
    lines = f.readlines()
    k = 0
    setting = {}
#    txxx = time.time()
    globals = {}
    geom = [300, 300]
    for line in lines:
        line = line.strip('\r\n')
        a = line.split(':')
        if len(a) < 2:
            continue
        com = a[0]
        var = ':'.join(a[1:])
        vararr = var.split('|||')
        vararr = [s.strip() for s in vararr]
        vararr = [s for s in vararr if s != '']
        var = '\n'.join(vararr)
        coms = com.split('.')

        if (coms[1][0:4] == 'plot' and len(coms) == 3):
            plots = interpret_plots(coms[1], coms[2], var, plots)
        elif (coms[1][0:4] == 'plot' and len(coms) == 4):
            if '.'.join(coms[2:]) == 'x.grid_lines':
                plots = interpret_plots(coms[1], '.'.join(coms[2:]), var,
                                        plots, use_int=True)
            elif '.'.join(coms[2:]) == 'y.grid_lines':
                plots = interpret_plots(coms[1], '.'.join(coms[2:]), var,
                                        plots, use_int=True)
            else:
                pass
        elif (coms[1][0:6] == 'global' and len(coms) == 3):
            globals = interpret_globals(coms[2], var, globals)
        elif (coms[1][0:6] == 'global' and len(coms) == 4):
            if '.'.join(coms[2:]) == 'x.grid_lines':
                globals = interpret_globals_int(
                    '.'.join(coms[2:]), var, globals)
            elif '.'.join(coms[2:]) == 'y.grid_lines':
                globals = interpret_globals_int(
                    '.'.join(coms[2:]), var, globals)
            else:
                pass
        elif coms[1][0:14] == 'rows_in_column':
            c = int(coms[1][15:])-1
            r = int(var)
            plots[c] = [{} for k in range(r)]
        elif coms[1] == 'columns':
            plots = [[] for k in range(int(var))]
        elif coms[1][:8] == 'geometry':
            geom = [int(x) for x in var.split('+')[0].split('x')]
        else:
            setting[coms[-1]] = var
        wx.GetApp().Yield(True)
#       wx.Yield()
        k = k+1
    f.close()

    if replace_shot:
        for x in plots:
            for y in x:
                if 'title' in y:
                    y['title'] = y['title'].replace('$shot', '_shots')
                    y['title'] = y['title'].replace('$SHOT', '_shots')
#    dprint1(time.time() - txxx)
    return setting, globals, plots, file, geom
