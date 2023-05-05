from __future__ import print_function
#
#
#  this is a start-up script loaded in
#  shell window.
#  This script defines functions available in shell and
#  help function
#
#
import six
import numpy as np
from ifigure.interactive import aviewer
from ifigure.interactive import plot, timetrace, oplot, plotc, loglog, semilogx, semilogy
from ifigure.interactive import errorbar, errorbarc, oerrorbar
from ifigure.interactive import triplot, delaunay
from ifigure.interactive import fill, fill_between, fill_betweenx, fill_between_3d
from ifigure.interactive import contour, contourf
from ifigure.interactive import image, spec, specgram
from ifigure.interactive import scatter, hist
from ifigure.interactive import tripcolor, tricontour, tricontourf
from ifigure.interactive import axline, axlinec
from ifigure.interactive import axspan, axspanc
from ifigure.interactive import surf, solid, trisurf, revolve
from ifigure.interactive import quiver, quiver3d
from ifigure.interactive import annotate
from ifigure.interactive import legend
from ifigure.interactive import text, figtext, arrow, figarrow
from ifigure.interactive import ispline
from ifigure.interactive import figure, close, edit
from ifigure.interactive import newbook
from ifigure.interactive import scope, scopenw, tscope
from ifigure.interactive import video, waveviewer, videoviewer
#from ifigure.interactive import sliceviewer
from ifigure.interactive import addpage
from ifigure.interactive import delpage
from ifigure.interactive import hold
from ifigure.interactive import cla
from ifigure.interactive import cls
from ifigure.interactive import clf
from ifigure.interactive import nsection
from ifigure.interactive import nsec
from ifigure.interactive import subplot
from ifigure.interactive import isection
from ifigure.interactive import isec
from ifigure.interactive import showpage
from ifigure.interactive import title, suptitle
from ifigure.interactive import xlabel, ylabel, zlabel, clabel
from ifigure.interactive import xtitle, ytitle, ztitle, ctitle
from ifigure.interactive import update
from ifigure.interactive import draw
from ifigure.interactive import server
from ifigure.interactive import clear
from ifigure.interactive import debug
from ifigure.interactive import profile, profile_start, profile_stop
from ifigure.interactive import threed, lighting
#from ifigure.interactive import newcz
from ifigure.interactive import ipage
from ifigure.interactive import twinx
from ifigure.interactive import twiny
from ifigure.interactive import twinc
from ifigure.interactive import exportv
from ifigure.interactive import importv
from ifigure.interactive import xlog, ylog, zlog, clog
from ifigure.interactive import xsymlog, ysymlog, zsymlog, csymlog
from ifigure.interactive import xlinear, ylinear, zlinear, clinear
from ifigure.interactive import xlim, ylim, zlim, clim
from ifigure.interactive import xauto, yauto, zauto, cauto
from ifigure.interactive import xnames, ynames, znames, cnames
from ifigure.interactive import autoplay, cbar
from ifigure.interactive import autoplay, setupmodel
from ifigure.interactive import property
from ifigure.interactive import view
from ifigure.interactive import glinfo, savefig, savedata

if six.PY3:
    from importlib import reload
    from ifigure.interactive import futurize
else:
    from builtins import reload

from ifigure.interactive import has_petra
if has_petra:
    from ifigure.interactive import petram


def help(*args):
    '''
    help : command-line access to __doc__
    help() : show all availabe functions
    help(object) : show __doc__ of object

    (example)
    help(plot) : show help for plot function    
    help(help) : show this help.
    '''

    if len(args) == 0:
        import types
        lvar = locals()
        gvar = globals()
        lnames = [key for key in lvar if type(lvar[key]) == types.FunctionType]
        gnames = [key for key in gvar if type(gvar[key]) == types.FunctionType]
        print('Availabe functions')
#       print lnames
#       print gnames
        txt = ['    ']
        gnames.append('quit')
        gnames.append('forcequit')
        gnames = sorted(gnames)
        #gnames = [name for name in gnames if not name in _internal_func]
        flen = max([len(name) for name in gnames])+3
        f = '{:'+str(flen)+'}'
        gnames = [f.format(name) for name in gnames]

        # this is not to show some functions in list
        for name in gnames:
            if name.startswith('_'):
                continue

            if len(txt[-1])+len(name) > 80:
                #              txt[-1] = txt[-1]
                txt.append('    ')
            txt[-1] = '\t'.join([txt[-1], name])
        txt.append(
            '! execute shell command (note: do not call interactive command such as python/bash from this)')
        print(('\n'.join(txt)))

    else:
        f = args[0]
        if hasattr(f, '__doc__'):
            if f.__doc__ is not None:
                print((f.__doc__))
            else:
                print('help is not available for ' + f.__repr__())
        else:
            print(('help is not available for ', f))
