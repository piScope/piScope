from __future__ import print_function

'''
   ifigure.interactive

   these are commands which can be used in piScope
   interactive shell (command input)

   many function calls are actually redicted to
   methods of bookviewer with additional keywords
   from _hold and _update. In that case, redirect_
   to_aviewer (decorator) is used to avoid repeating
   the same code. However, methods in bookviewer are
   programmed to use __doc__ in this file.

'''

import matplotlib.mlab as mlab
from functools import wraps
import logging
import ifigure
import wx
import weakref
import os
import numpy as np
from ifigure.utils.triangulation_wrapper import delaunay
#from ifigure.utils.cbook import isiterable, isndarray, message

_hold = False
_update = True
_lastisec = 0

aviewer = None


def get_topwindow():
    return wx.GetApp().GetTopWindow()


def set_aviewer(viewer):
    # called from ifigure_app.aviewer
    from ifigure.widgets.book_viewer import BookViewer
    if (viewer == wx.GetApp().TopWindow or
            isinstance(viewer, BookViewer)):
        globals()['aviewer'] = viewer
    elif (globals()['aviewer'] is not None):
        try:
            if (globals()['aviewer'].book is None):
                globals()['aviewer'] = None
        except:
            globals()['aviewer'] = None
    if viewer is None:
        if globals()['aviewer'] in wx.GetApp().TopWindow.viewers:
            return
        globals()['aviewer'] = None


def check_aviewer(func):
    @wraps(func)
    def checker(*args, **kargs):
        def func2(*args, **kargs):
            #              return figure()
            from ifigure.utils.cbook import message
            message("*** No current viewer (no plot) ***")
            return None

        # check if aviewer in still right object
        try:
            book = aviewer.book
        except:
            return func2(*args, **kargs)

        if aviewer.book is None:
            globals()['aviewer'] = None
            return func2(*args, **kargs)
        else:
            return func(*args, **kargs)

    return checker


def redirect_to_aviewer(func):
    @wraps(func)
    def checker(*args, **kargs):
        if aviewer is None:
            figure()
            wx.GetApp().Yield()  # yield let wx to process event including
            # project_tree_widget update
        m = getattr(aviewer, func.__name__)
        kargs['hold'] = _hold
        kargs['update'] = _update
        ret = m(*args, **kargs)
        aviewer.Raise()
        return ret
    return checker


def redirect_to_aviewer_3D(func):
    @wraps(func)
    def checker(*args, **kargs):
        if aviewer is None:
            figure()
            wx.GetApp().Yield()  # yield let wx to process event including
            # project_tree_widget update
        m = getattr(aviewer, func.__name__)
        kargs['hold'] = _hold
        kargs['update'] = _update
        aviewer.threed('on')
        ret = m(*args, **kargs)
        aviewer.Raise()
        return ret
    return checker


def redirect_to_aviewer_hold(func):
    @wraps(func)
    def checker(*args, **kargs):
        def func2(*args, **kargs):
            #              from ifigure.utils.cbook import message
            return figure()
#              message("*** No current viewer (no plot) ***")
#              return None
        if aviewer is None:
            figure()
#           return func2(*args, **kargs)
#        else:

        m = getattr(aviewer, func.__name__)
        kargs['hold'] = True
        kargs['update'] = _update
        ret = m(*args, **kargs)
        aviewer.Raise()
        return ret
    return checker


@redirect_to_aviewer
def showpage(ipage):
    '''
    show ipage
    '''
    pass


@redirect_to_aviewer
def cla(reset_color_cycle=True):
    '''
    clear current axis
    '''
    pass


@redirect_to_aviewer
def cls():
    '''
    cls() is the same as clf()
    isec is moved to 0
    '''
    pass


@redirect_to_aviewer
def clf():
    '''
    clear current page. page annotations are not
    deleted
    isec is moved to 0
    '''
    pass


@redirect_to_aviewer
def nsec(*args, **kargs):
    '''
    nsec is the same as subplot
    see subplot help (type 'subplot(' to show help)
    '''
    pass


@redirect_to_aviewer
def nsection(*args, **kargs):
    '''
    nsection is the same as subplot
    see subplot help (type 'subplot(' to show help)
    '''
    pass


@redirect_to_aviewer
def subplot(*args, **kargs):
    '''
    set page section format.
       subplot(3)     3 rows
       subplot(1, 3)     3 columns
       subplot(2, 3)  2x3
       subplot(2, 3, (0,1)) 2x3 and (0,1) merged
       subplot(2, 3, (0,1), (2, 3)) 2x3 and (0,1), (2, 3) merged

       'sort' = 'col' or 'column' or 'c' : sort result in column
       'sort' = 'row' or 'r' :             sort result in row

       dx and dy are optional arguments to determine the
       width and height of each column and row
       if these are used, the number of dx and dy should be
       ncol-1, nrow-1, respectively

       example: subplot(2,2, (0,1), dx=0.4)

    '''
    pass


@redirect_to_aviewer
def isec(i=None):
    '''
    isce/isection control current axes.
    if i is give, it sets current axes and returns ax
    otherwize it returns current ax
    '''
    pass


@redirect_to_aviewer
def isection(i=None):
    '''
    isce/isection control current axes.
    if i is give, it sets current axes and returns ax
    otherwize it returns rrent ax
    '''
    pass


@redirect_to_aviewer
def addpage(num=1, before=False):
    '''
    add a page to current book
    '''
    pass


@redirect_to_aviewer
def delpage():
    '''
    delete current page
    '''


@redirect_to_aviewer
def suptitle(txt, size=None, color=None):
    '''
    set page  title
    '''
    pass


@redirect_to_aviewer
def title(txt, size=None, color=None):
    '''
    set section  title
    '''
    pass


@redirect_to_aviewer
def xlabel(txt, name='x', size=None, color=None):
    '''
    set xaxis label
       xlabel(txt)
       xlabel(txt, name = 'x2')
       xlabel(txt, size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def xtitle(txt, name='x', size=None, color=None):
    '''
    set xaxis label
       xtitle(txt)
       xtitle(txt, name = 'x2')
       xtitle(txt, size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def ylabel(txt, name='y', size=None, color=None):
    '''
    set yaxis label
       ylabel(txt)
       ylabel(txt, name = 'y2')
       ylabel(txt, size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def ytitle(txt, name='y', size=None, color=None):
    '''
    set yaxis label
       ytitle(txt)
       ytitle(txt, name = 'y2')
       ytitle(txt,  size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def zlabel(txt, name='z', size=None, color=None):
    '''
    set zaxis label
       zlabel(txt)
       zlabel(txt, size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def ztitle(*args):
    '''
    set zaxis label
       ztitle(txt)
       ztitle(txt, size=10, color='red')
    '''
    pass


@redirect_to_aviewer
def clabel(txt, name='c'):
    '''
    set caxis label
       clabel(txt)
       clabel(txt, 'c2')
    '''
    pass


@redirect_to_aviewer
def ctitle(*args):
    '''
    set caxis label
       ctitle(txt)
       ctitle(txt, 'c2')
    '''
    pass


@redirect_to_aviewer_hold
def xlog(value=True, base=None):
    '''
    set xlog
    xlog()
    xlog(False)
    '''
    pass


@redirect_to_aviewer_hold
def ylog(value=True, base=None):
    '''
    set ylog
    ylog()
    ylog(False)
    '''
    pass


@redirect_to_aviewer_hold
def clog(value=True, base=None):
    '''
    set ylog
    clog()
    clog(False)
    '''
    pass


@redirect_to_aviewer_hold
def zlog(value=True, base=None):
    '''
    set zlog
    zlog()
    zlog(False)
    '''
    pass


@redirect_to_aviewer_hold
def xsymlog(base=None, linthresh=None, linscale=None, name='x'):
    '''
    set symlog in x

    [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'x')
    '''
    pass


@redirect_to_aviewer_hold
def ysymlog(base=None, linthresh=None, linscale=None,  name='y'):
    '''
    set symlog in y
    [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'y')
    '''
    pass


@redirect_to_aviewer_hold
def zsymlog(base=None, linthresh=None, linscale=None, name='z'):
    '''
    set symlog in z
    [x,y, z, c]symlog(base = None, linthresh = None, linscale = None,  name  = 'z')
    '''
    pass


@redirect_to_aviewer_hold
def csymlog(base=None, linthresh=None, linscale=None, name='c'):
    '''
    set symlog in c
    [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'c')
    '''
    pass


@redirect_to_aviewer_hold
def xlinear(value=True):
    '''
    set xscale linear
    xlinear()
    xlinear(False) # makes log scale
    '''
    pass


@redirect_to_aviewer_hold
def ylinear(value=True):
    '''
    set yscale linear
    ylinear()
    ylinear(False) # makes log scale
    '''
    pass


@redirect_to_aviewer_hold
def clinear(value=True):
    '''
    set cscale linear
    clinear()
    clinear(False) # makes log scale
    '''
    pass


@redirect_to_aviewer_hold
def zlinear(value=True):
    '''
    set zscale linear
    zlinear()
    zlinear(False) # makes log scale
    '''
    pass


@redirect_to_aviewer
def xauto(name='x'):
    '''
    auto scale x
    '''
    pass


@redirect_to_aviewer
def yauto(name='y'):
    '''
    auto scale y
    '''
    pass


@redirect_to_aviewer
def zauto(name='z'):
    '''
    auto scale z
    '''
    pass


@redirect_to_aviewer
def cauto(name='c'):
    '''
    auto scale c
    '''
    pass


@redirect_to_aviewer
def xlim(*range, **kargs):
    '''
    xlim change range of xaxis

    kargs:
        tposition : tick position ('top', 'bottom')
        ticks : tick values
        tcolor : tick color
        color : text color
        size : text size
        ocolor : offset text color
        osize : offset text size

    example) 
        xlim(min, max) , xlim((min, max)), or xlim([min, max])
        xlim([0, 3], size=25, color='red', tcolor='red', ticks=[0,1, 3], tposition='top')
    '''
    pass


@redirect_to_aviewer
def ylim(*range, **kargs):
    '''
    ylim change range of yaxis
    kargs:
        tposition : tick position ('left', 'right')
        ticks : tick values
        tcolor : tick color
        color : text color
        size : text size
        ocolor : offset text color
        osize : offset text size

    example) 
        ylim(min, max) , ylim((min, max)), or ylim([min, max])
        ylim([0, 3], size=25, color='red', tcolor='red', ticks=[0,1, 3], tposition='left')
    '''
    pass


@redirect_to_aviewer
def zlim(*range, **kargs):
    '''
    zlim change range of zaxis

    kargs:
        tposition : tick position ('top', 'bottom')
        ticks : tick values
        tcolor : tick color
        color : text color
        size : text size
        ocolor : offset text color
        osize : offset text size

    example) zlim(min, max) , zlim((min, max)), or zlim([min, max])
    '''
    pass


@redirect_to_aviewer
def clim(*range, **kargs):
    '''
    clim change range of caxis
    example) clim(min, max) , clim((min, max)), or clim([min, max])
    '''
    pass


@redirect_to_aviewer
def twinx():
    '''
    twinx
    '''
    pass


@redirect_to_aviewer
def twiny():
    '''
    twinx
    '''
    pass


@redirect_to_aviewer_hold
def oplot(*args, **kargs):
    '''
    oplot :
        overplot
    see plot for all arguments
    '''
    pass


@redirect_to_aviewer_hold
def oerrorbar(*args, **kargs):
    '''
    oerrrobar:
        overplot errorbar
    see errorbar for all arguments
    '''
    pass


@redirect_to_aviewer
def loglog(*args, **kargs):
    '''
    make loglog plot
    loglog(x, y, s)
    '''
    pass


@redirect_to_aviewer
def semilogy(*args, **kargs):
    '''
    make semilog (yaxis is log scale) plot
    semilogy(x, y, s)
    '''
    pass


@redirect_to_aviewer
def semilogx(*args, **kargs):
    '''
    make semilog (xaxis is log scale) plot
    semilogx(x, y, s)
    '''
    pass


@redirect_to_aviewer
def timetrace(*args, **kargs):
    '''
    timetrace: special plot for time
               it supports decimation
    timetrace(y)
    timetrace(x, y)
    '''
    pass


@redirect_to_aviewer
def plotc(*args, **kargs):
    '''
    plotc creates a line plot similar to plot.
    however, it has extra menus to edit points
    '''
    pass


@redirect_to_aviewer
def errorbarc(*args, **kargs):
    '''
    errorbar creates a line plot similar to errorbar.
    however, it has extra menus to edit points
    '''
    pass


@redirect_to_aviewer
def plot(*args, **kargs):
    """
    plot : xy plot

    plot(y)
    plot(x, y)
    plot(y, s)
`   plot(x, y, s)
    plot(x, y, z)
    plot(x, y, z, cz=True)

    s is a format string. For example 'bo-' means to use blue solid line with
    circle marker. The format string is directly passed to matplotlib.
    See http://piscope.psfc.mit.edu/index.php/Interactive_commands#plot for
    detail

    cz is option to change the color along a line using z.

    When x and y are expression, it evaulate x and y and the answer
    should be 1D data.
    If x and y are given as numbers, following handling
    is done
          x.ndim == 2 and y.ndmi ==1
            x is sliced using the first row and multiple lines
            are generated
          x.ndim == 1 and y.ndmi ==2
            y is sliced using the first row and multiple lines
            are generated
          x.ndim == 2 and y.ndmi ==2
            both x and y are sliced using the first row and multiple lines
            are generated

    see also: errorbar
    """
    pass


@redirect_to_aviewer
def scatter(*args, **kargs):
    """
    scatter plot

    scatter(x, y, s = 20, c = 'b')

    s : scalar or array_like (same length as x, y)
        size in points^2.
    c : color or sequence of color
        if c is a 1D array, it is normalized using c-axis range
        c can also be RGBA values (in which rows are RGB or RGBA)
    """
    pass


@redirect_to_aviewer
def hist(*args, **kargs):
    """
    histgram


    """
    pass


@redirect_to_aviewer
def triplot(*args, **kargs):
    """
    triplot : plot triangles

    triplot(x, y)
    triplot(x, y, mask = mask, ...)
    triplot(tri, x, y)

    """
    pass


@redirect_to_aviewer
def errorbar(*args, **kargs):
    """
    errorbar : xy plot with errorbar

    errorbar(x, y, xerr=xerr, yerr=yerr)

    options for xerr and yerr
        ### assign 0.1 for all points)
        xerr = 0.1
        ### assign different value of error
        xerr = [0.1, 0.2, ....]
        ### assign upper and lower error separately
        xerr = [[0.1, 0.2, ...],[0.4, 0.7...]]

    identical to calling plot with mpl_command = 'errorbar'
    """
    pass


@redirect_to_aviewer
def annotate(*args, **kargs):
    '''
    annotate(s, xy, xytext=None, xycoords='data',
            textcoords='data', arrowprops=None,
            **kargs)
    xycoords, textcoords : 'data', 'figure', 'axes'
      'figure' and 'axes' is from 0 to 1 (fraction)
      other opstions are not supported
    '''
    pass


@redirect_to_aviewer
def ispline(*args, **kargs):
    """
    ispline : xy plot
    ispline(x, y)
    """
    pass


@redirect_to_aviewer
def contour(*args, **kargs):
    """
    contour : contour line plot  (see also contourf)
    contour(z, n)
    contour(x, y, z, n)
    contour(z, v)
    contour(x, y, z, v)

    n: number of levels
    v: a list of contour levels
    """
    pass


@redirect_to_aviewer
def contourf(*args, **kargs):
    """
    contourf : contour fill plot
    contourf(z, n)
    contourf(x, y, z, n)
    contourf(z, v)
    contourf(x, y, z, v)

    n: number of levels
    v: a list of contour levels
    """
    pass


@redirect_to_aviewer
def quiver(*args, **kargs):
    """
    quiver : quiver plot
    for 2D:
       quiver(u, v)
       quiver(u, v, c)
       quiver(x, y, u, v)
       quiver(x, y, u, v, c)

    for 3D:
       quiver(X, Y, Z, U, V, W, **kwargs)

       X, Y, Z:
           The x, y and z coordinates of the arrow locations (default is
           tip of arrow; see *pivot* kwarg)
       U, V, W:
           The x, y and z components of the arrow vectors

    """
    pass


@redirect_to_aviewer
def quiver3d(*args, **kargs):
    '''
    quiver3D is threed('on') + quiver
    quiver3D(x, y, z, u, v, w,  cz = False, cdata = None)

    if cz is True and cdata is None, z is used for color
    '''


@redirect_to_aviewer
def image(*args, **kargs):
    """
    image : show image

    image(z)
    image(x, y, z)
    """
    pass


@redirect_to_aviewer
def specgram(x, NFFT=256,
             Fs=2,
             Fc=0,
             detrend=mlab.detrend_none,
             window=mlab.window_hanning,
             noverlap=128,
             xextent=None,
             pad_to=None,
             sides='default',
             scale_by_freq=None,
             **kwargs):
    '''
    plot spectrogram. Run matplotlib.pyplot.specgram
    and call image using the returnd spectrum.
    keywords are the same as specgram.
    '''
    pass


@redirect_to_aviewer
def spec(*args, **kargs):
    """
    spectram
    spec(t, v)
    spec(v)
    """
    pass


@redirect_to_aviewer
def tripcolor(*args, **kargs):
    """
    tricolor : show image using triangulation

    tripcolor(z)
    tripcolor(x, y, z)
    tripcolor(tri, z)
    tripcolor(tri, x, y, z)

    tri can be evaluated by tri = delaunay(x, y) beforehand
    """
    pass


@redirect_to_aviewer
def tricontour(*args, **kargs):
    """
    tri-contour plot

    tricontour(x, y, z, n)
    tricontour(x, y, z, v)
    tricontour(tri, x, y, z, n)
    tricontour(tri, x, y, z, v)
    tri can be evaluated by tri = delaunay(x, y) beforehand
    """
    pass


@redirect_to_aviewer
def tricontourf(*args, **kargs):
    """
    tri-contour plot with fill mode

    tricontourf(x, y, z, n)
    tricontourf(x, y, z, v)
    tricontourf(tri, x, y, z, n)
    tricontourf(tri, x, y, z, v)
    tri can be evaluated by tri = delaunay(x, y) beforehand
    """
    pass


@redirect_to_aviewer
def axline(*args, **kargs):
    """
    axline : axhline or axvline


    axline(x) or axline([x1,x2,x3...])  : vline
    axline([], y) or axline([], [y1,y2,y3...]) : hline
    axline([x1, x2...],[y1, y2...]) : mixed vline and hline

    (note) lines created by one axline commads shares
           color, marker, alpha, and other attirbute.
    """
    pass


@redirect_to_aviewer
def axlinec(*args, **kargs):
    """
    axlinec: editable axline
    """
    pass


@redirect_to_aviewer
def axspan(*args, **kargs):
    """
    axspan : axhspan or axvspan

    axspan([x1,x2])     : v-span
    axspan([], [y1,y2]) : h-span
    axspan([x1, x2], [y1,y2]) : mixed v-span h-span

    multiple v-span and h-span can be created at once
    axspan([[x1, x2], [x3, x4]...], [[y1,y2], [y3, y4]...])

    (note) artists created by one axspan commands
          shares color, marker, alpha, and other attirbute.
          drag is also applied to all artists.
    """
    pass


@redirect_to_aviewer
def axspanc(*args, **kargs):
    """
    axspanc: a user control version of axspan
             see help(axspan) for the details of argments

             a user can add/drag/remove the patch object and edit
             values from GUI
    """
    pass


@redirect_to_aviewer_hold
def text(*args, **kargs):
    """
    text : add text to current axes

    text(x, y, s) : type string s to (x, y)
    """
    pass


@redirect_to_aviewer_hold
def figtext(*args, **kargs):
    """
    figtext : add text to current figure

    figtext(x, y, s) : type string s to (x, y)
    """
    pass


@redirect_to_aviewer_hold
def arrow(*args, **kargs):
    """
    arrow : add arrow to current axes

    arrow(x1, y1, x2, y2)
    """
    pass


@redirect_to_aviewer_hold
def figarrow(*args, **kargs):
    """
    figarrow : add arrow to current page

    figarrow(x1, y1, x2, y2)
    """
    pass


@redirect_to_aviewer_hold
def legend(*args, **kargs):
    """
    legend: add legend box to current figure

    legend('label1') : legend for a single artist
    legend(['label1', 'label2']) for multiple aritsts
    legend(['label1', 'label2'], axes2 = True) for multiple aritsts
    """
    pass


@redirect_to_aviewer
def fill(*args, **kargs):
    '''
    fill(x, y)
    '''
    pass


@redirect_to_aviewer
def fill_between(*args, **kargs):
    '''
    fill_between(x, y,  y2=[0]*len(x), where=None)
    '''
    pass


@redirect_to_aviewer
def fill_betweenx(*args, **kargs):
    '''
    fill_betweenx(y, x, x2=[0]*len(y), where=None)
    (note): order of x and y is different from MPL?
    '''
    pass


@redirect_to_aviewer
def fill_between_3d(*args, **kargs):
    '''
    fill_between_3d(x1, y1, z1, x2, y, z2, c='b')
    '''
    pass


@redirect_to_aviewer_3D
def surf(*args, **kargs):
    '''
    surf or surface : surface plot in 3D
                      using mplot3d
    surf(x, y, z, **kargs):
    '''
    pass


@redirect_to_aviewer_3D
def surface(x, y, z, **kargs):
    '''
    surf/surface : surface plot in 3D
                      using mplot3d
    surf(x, y, z, **kargs):
    '''
    pass


@redirect_to_aviewer_3D
def revolve(*args, **kargs):
    '''
    revolve r, z : revolve (r, z) data

      keywords to define revolve
         rcenter: [0,0]
         rtheta:  [0, 2*pi]
         raxis:   [0,  1]
         rmesh:   100.
    '''
    pass


@redirect_to_aviewer_3D
def solid(v, **kargs):
    '''
    solid: plot soild volume complsed by triangle/quad

    solid(v, cz=False, cdata=None, **kargs):
    solid(v, idxset, cz=False, cdata=None, **kargs):

    v : 3D array of verteics
        v[ielement, ivertex,  xyz]
    cz : define color data separately
        when cz =true, 3rd dim of v should be four
        v[ielement, ivertex,  xyzc]

    Using idxset, vertices and index set to define the element shape
    is given separately. v[:, xyz] and idxset[ielement, ivertex]
    will be expanded as if v is v[idexset,...]. This allows to reduce
    the number of vertices passed to GPU

    if third dim is 2:
        v[ielement, ivertex,  xy]
        and
        z needs to be given as zvalue keyword argument

    cdata: used with cz  cdata[ielement, ivertex]

    draw_last : draw this artists last on GL canvas, useful for getting
                cleanin line smoothing
    facecolor: use solid facecolor
    edgecolor: use solid edgecolor

    example:

       (indexed array)
       ptx = np.array([[0, 0], [0,1], [1,1], [1,0]])
       box = np.array([[0,1,2,3]])
       figure();solid(ptx, box)
    '''
    pass


@redirect_to_aviewer_3D
def trisurf(v, **kargs):
    '''
    triangle surface plot
    trisurf(z, **kargs):
    trisurf(x, y, z, **kargs):
    trisurf(tri, x, y, z, **kargs):
    trisurf(tri, z, **kargs):
    '''
    pass


@redirect_to_aviewer
def property(obj, name, *args):
    '''
    property set or get property of target object

      property(obj) : return a list of editable property
      property(obj, name) : get an object property
      property(obj, name, value : set an object property
    '''
    pass


@redirect_to_aviewer
def threed(*args):
    '''
    turn on/off three-D axis mode
    '''
    pass


@redirect_to_aviewer
def lighting(**kwargs):
    '''
    set lighting of 3D scene (it affects only artists drawn on OpenGL canvas)
      lighting(ambient = 0.4)  : amibient lighting intensity
      lighting(light   = 0.4)  : lighting source intensity
      lighting(light_direction = (1, 0., 1, 0)) : lighting source direction
      lighting(specular = 1.0) : specular reflection intensity
      lighting(light_color = (1.0, 1, 1)) : light source color
      lighting(wireframe = 0)  : #0 normal mode
                                 #1 wireframe + hidden line elimination
                                 #2 wireframe
    '''
    pass


@redirect_to_aviewer
def _view(*args, **kwargs):
    pass


def view(*args, **kwargs):
    '''
       set 3D view
          view() : return current setting
          view(elev, azim, upvec)
          view('xy')
          view('yx')
          view('xz')
          view('yz')
          view('default')
          view('frustum')
          view('ortho')
          view('updown')
          view('equal')   # equal aspect ratio
          view('auto')    # auto aspect ratio
          view('clip')
          view('noclip')
    '''
    if len(args) == 0 and len(kwargs) == 0:
        v = aviewer
        return v.view()
    else:
        return _view(*args, **kwargs)


@redirect_to_aviewer
def xnames(*args, **kwargs):
    '''
    return list of x axis name of current plot
    '''
    pass


@redirect_to_aviewer
def ynames(*args, **kwargs):
    '''
    return list of y axis name of current plot
    '''
    pass


@redirect_to_aviewer
def znames(*args, **kwargs):
    '''
    return list of z axis name of current plot
    '''
    pass


@redirect_to_aviewer
def cnames(*args, **kwargs):
    '''
    return list of c axis name of current plot
    '''
    pass


@redirect_to_aviewer
def cbar(*args, **kwargs):
    '''
    toggle cbar of current plot
        cbar()
        cbar('c2')  # to specify caxis name

    keywords:
        position : position of color bar (normalized to axis)
        size : size of color bar (normalized to axis)
        direction : h or v (horizontal, or vertical)
        lcolor : text color
        lsize : text size
        olcolor : offset text color
        olsize : offset text size

    example:
        cbar(position=(0.1, 0.1), size=(0.7, 0.05), lsize=16, 
             lcolor='red', olsize=19, olcolor='b',direction='h') 
    '''
    pass


@redirect_to_aviewer
def savefig(filename):
    '''
    save figure as image

       savefig(filename)

       filename must be one of following
          .eps
          .pdf  (support multipage pdf)
          .svg
          .jpeg
          .png
          .gif  (animation gif)
    '''


@redirect_to_aviewer
def savedata(filename):
    '''
    save dataset as hdf file

      savedate(filename) # filename must be *.hdf
    '''

#
#   functions which are actually implemented here
#


@check_aviewer
def aviewer():
    return aviewer


@check_aviewer
def draw():
    '''
    draw draws the window contents. this command
    is intended to use with update('off') in script

    ex) ou = update()
        update('off')
        .... do some mupltiple plotting
        draw()
        update(ou)

    '''
    aviewer.draw()


@check_aviewer
def hold(val=None):
    '''
    hold controls if existing plots are deleted bofore
    adding a new one
       hold("on"), hold(1), hold(True)  -> hold is on
       hold("off"),hold(0), hold(False) -> hold is off

    '''
    if val is None:
        return globals()["_hold"]

    if isinstance(val, bool):
        globals()["_hold"] = val
    if isinstance(val, int):
        if (val == 1):
            globals()["_hold"] = True
        if (val == 0):
            globals()["_hold"] = False
    if isinstance(val, str):
        if (val.upper() == 'ON'):
            globals()["_hold"] = True
        if (val.upper() == 'OFF'):
            globals()["_hold"] = False


@check_aviewer
def update(val=None):
    '''
    update controls if it draws screen after interactive
    command.
    update('on'), update(1), update(True) : automatic update on
    update('off'), update(0), update(False) : automatic update off
    '''
    if val is None:
        return globals()["_update"]
    if isinstance(val, bool):
        globals()["_update"] = val
    if isinstance(val, int):
        if (val == 1):
            globals()["_update"] = True
            if not globals()["_update"]:
                draw()
        if (val == 0):
            globals()["_update"] = False
    if isinstance(val, str):
        if (val.upper() == 'ON'):
            if not globals()["_update"]:
                draw()
            globals()["_update"] = True

        if (val.upper() == 'OFF'):
            globals()["_update"] = False


@check_aviewer
def ipage():
    '''
    get current page number
    '''
    return globals()['aviewer'].ipage


@check_aviewer
def close(*args):
    '''
    close()
    clsee(1)   : close all figure window
    clsee(all) : close all figure window
    '''
    if len(args) == 0:
        m = getattr(aviewer, 'close')
        m()
    else:
        # close all viewer whith has close method
        # having close method indicates it inherit
        # BookViewerInteractive
        ifig_app = get_topwindow()
        for v in ifig_app.viewers[:]:
            if hasattr(v, 'close'):
                v.close()


def clear():
    ifig_app = get_topwindow()
    ifig_app.shell.clear()


def newbook(name='', basename=None):
    '''
    add a new book
    '''
    ifig_app = get_topwindow()
    book = ifig_app.proj.onAddBook(basename=basename)
    i_page = book.add_page()
    page = book.get_page(i_page)
    page.realize()
    page.add_axes()
    page.realize_children()
    page.set_area([[0, 0, 1, 1]])
    return book
#    ifigure.events.SendShowPageEvent(page)


def _open_book(book, viewer, **kwargs):
    ifig_app = get_topwindow()
    if ifig_app.find_bookviewer(book) is not None:
        ifig_app.find_bookviewer(book).Raise()
        ifig_app.aviewer = ifig_app.find_bookviewer(book)
        return
    ifigure.events.SendOpenBookEvent(book, w=ifig_app,
                                     viewer=viewer, useProcessEvent=True, **kwargs)
    ifigure.events.SendChangedEvent(book, w=ifig_app, useProcessEvent=True)
    ifigure.events.SendCanvasSelected(book.get_child(0), w=None,
                                      useProcessEvent=True)


def _get_book_by_number(parent, num, basename='book'):
    from ifigure.mto.fig_book import FigBook
    name = basename+str(num)
    if parent.has_child(name):
        book = parent.get_child(name=name)
        if not isinstance(book, FigBook):
            return None
        return book
    else:
        book = FigBook()
        ipage = book.add_page()
        book.get_page(ipage).add_axes()
        book.get_page(ipage).realize()
        book.get_page(ipage).set_area([[0, 0, 1, 1]])
        parent.add_child(name, book)
        ifigure.events.SendChangedEvent(book, w=wx.GetApp().TopWindow)
        return book


def figure(file='', book=None, viewer=None, **kwargs):
    '''
    create a new book and open it in a new figure window
         figure()  : open empty figure
         figure('***.bfz') : open book file
         figure(proj.book) : open FigBook object
         figure(1)  : open (or make) book1 under proj
         figure(1, parent)  : open (or make) book1 under parent
    '''
    from ifigure.widgets.book_viewer import BookViewer
    from ifigure.mto.fig_book import FigBook

    if isinstance(file, FigBook):
        book = file
        file = ''
    elif isinstance(file, int):
        num = file
        parent = book if book is not None else wx.GetApp().TopWindow.proj
        book = _get_book_by_number(parent, num)
        file = ''
        if book is None:
            return
    if book is None:
        book = newbook()
    if book.num_page() == 0:
        book.add_page()
    if viewer is None:
        viewer = BookViewer
    _open_book(book, viewer, **kwargs)
    viewer = wx.GetApp().TopWindow.find_bookviewer(book)
    if file == '':
        return viewer

    import os
    file = os.path.expanduser(file)
    if file.endswith('.bfz'):
        evt = None
        wx.CallAfter(viewer.onLoadBook, evt, file=file)
    return viewer

# def scope(type='direct'):


def scope(file='',  book=None,  viewer=None, **kwargs):
    '''
    open mdsscope
       scope() : open empty scope
       scope('***.pbz') : open book file
       scope('***.dat') : import *.dat as dwscope file
       scope(proj.book) : open FigBook object
    '''

    from ifigure.mto.fig_book import FigBook
    if isinstance(file, FigBook):
        book = file
        file = ''
    elif isinstance(file, int):
        num = file
        parent = book if book is not None else wx.GetApp().TopWindow.proj
        book = _get_book_by_number(parent, num, basename='scope')
        file = ''
        if book is None:
            return
    from ifigure.mdsplus.mdsscope import MDSScope
    if viewer is None:
        viewer = MDSScope
    if book is None:
        book = newbook(basename='scope')
    if book.num_page() == 0:
        book.add_page()
    book.get_page(0).set_nomargin(True)
    _open_book(book, viewer, **kwargs)
    viewer = wx.GetApp().TopWindow.find_bookviewer(book)
    if file == '':
        return viewer

    import os
    file = os.path.expanduser(file)
    if file.endswith('.dat'):
        wx.CallAfter(viewer.onImportDW, None, file=file)
    elif file.endswith('.bfz'):
        evt = None
        wx.CallAfter(viewer.onLoadBook, evt, file=file)
    return viewer


def videoviewer(file='', book=None):

    from ifigure.widgets.video_viewer import VideoViewer
    viewer = figure(file=file, book=book, viewer=VideoViewer)
    return viewer


def waveviewer(file='', book=None, nframe=30, sign=-1):

    from ifigure.widgets.wave_viewer import WaveViewer
    viewer = figure(file=file, book=book, viewer=WaveViewer)
    viewer.sign = sign
    viewer.nframe = nframe
    return viewer


def video(*args, **kargs):
    '''
    video viewer is to look video image (3D array)
    vidoe(x, y, z) or video(z)
    '''
    if len(args) == 1:
        z = args[0]
        x = np.arange(z.shape[-1])
        y = np.arange(z.shape[-2])
    elif len(args) == 3:
        z = args[0]
        x = args[1]
        y = args[2]
    else:
        raise ValueError

    v = videoviewer()
    o = v.image(*args, **kargs)
    v.goto_frame(0)

    return v


def futurize(obj=None, dryrun=False, verbose=False, unicode=True, stage1=True, stage2=True, help=False):
    '''
    futurize : an interface to PY2->PY3 conversion utility.

       it uses futurizer in future module. Default actin is to perform
       both stage1 and stage2 conversion.

       See more detail in
       https://python-future.org/futurize.html#forwards-conversion

       obj : either None, Folder, Script
           None: convert all scripts in project
           Folder: convert all scripts in folder
           Script: convert one script

       dryrun: does not save the conveted script.
       stage1: perform stage 1 conversion
       stage2: perform stage 2 conversion
    '''

    from ifigure.utils.future import futurizer as ft
    futurizer = ft()
    if help == True:
        futurizer.process_proj(dryrun=False, verbose=False, unicode=True, stage1=True, stage2=True,
                               help=True)
        return
    if obj is None:
        futurizer.process_proj(dryrun=dryrun, verbose=verbose, unicode=unicode,
                               stage1=stage1, stage2=stage2, help=False)
    from ifigure.mto.py_script import PyScript
    from ifigure.mto.py_code import PyFolder
    if isinstance(obj, PyScript):
        futurizer.process_script(obj, dryrun=dryrun, verbose=verbose, unicode=unicode,
                                 stage1=stage1, stage2=stage2, help=False)
    elif isinstance(obj, PyFolder):
        futurizer.process_folder(obj, dryrun=dryrun, verbose=verbose, unicode=unicode,
                                 stage1=stage1, stage2=stage2, help=False)
    else:
        pass


def scopenw(book):
    from ifigure.mdsplus.mdsscope_nw import MDSScopeNW
    return MDSScopeNW(book=book)


def tscope(file='',  book=None):
    ifig_app = get_topwindow()
    proj = ifig_app.proj

    if proj.setting.has_child('ts_worker'):
        workers = proj.setting.ts_worker
    else:
        file = os.path.join(ifigure.__path__[0], 'add_on',
                            'setting', 'module', 'mdsplus_worker.py')

        workers = proj.setting.add_absmodule(file)
        workers.rename('ts_worker')
        workers.setvar('translater', 'ts')
    v = scope(file=file, book=book, worker=workers)
    v.book.setvar('mdsplus_server', 'mdsplus.partenaires.cea.fr:8000:')


try:
    from petram.pi.shell_commands import petram
    has_petra = True
except:
    has_petra = False


def edit(file=''):
    app = wx.GetApp().TopWindow
    app.open_editor_panel()
    if file == '':
        app.script_editor.NewFile()
    else:
        import os
        file = os.path.expanduser(file)
        app.script_editor.OpenFile(file)
    if not app.isEditorAttached():
        app.script_editor.Raise()


def debug(command, *args):
    '''
     set and list debug level
     debug('set', level_name, level)
       or  debug('s', level_name, level)
     debug('list')
       or  debug('l', level_name, level)
    '''
    import ifigure.utils.debug
    if command.startswith('l'):
        for key in ifigure.utils.debug.debug_modes:
            print((key, ifigure.utils.debug.debug_modes[key]))
    elif command.startswith('s'):
        ifigure.utils.debug.set_level(args[0], args[1])


def profile(txt, *args):
    '''
    profile(txt)
    profile(txt, filename)

    run cProfile with locals in Shell
    '''
    ifig_app = get_topwindow()
    import cProfile
    l = ifig_app.shell.lvar
    cProfile.runctx(txt, {}, l, *args)


def profile_start():
    '''
    profiling start
    usage:
       pr = profile_start()
       ... do something
       profile_stop(pr)
    '''
    import cProfile
    print('starting profiler')
    pr = cProfile.Profile()
    pr.enable()
    return pr


def profile_stop(pr, sortby='cumulative'):
    '''
    profile_stop(pr, sortby='cumulative'):

    end profile
    sortby = 'cumulative', 'calls', 'cumtime',
             'file', 'filename', 'module',
             'ncalls', pcalls', 'line', 'name',
             'nfl', stdname', 'time', 'tottime'
    '''
    from six import StringIO
    import pstats
    pr.disable()
    # print 'stopped profiler'
    lsortby = ['cumulative', 'calls', 'cumtime',
               'file', 'filename', 'module',
               'ncalls', 'pcalls', 'line', 'name',
               'nfl', 'stdname', 'time', 'tottime']
    if not sortby in lsortby:
        print('invalid sortby')
        print(lsortby)
        return

    s = StringIO()
    sortby = sortby
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print((s.getvalue()))


def server(param=None, extra=None):
    '''
    server : control server mode
        server('on') : start server
        server('on', hostname) : start server
             in this case, server process is binded
             to hostname, allowing connection over
             network.
        server('off'): stop server
        server()     : show server information
    '''
    import ifigure.server
    server = ifigure.server.Server()
    if param == 'on':
        server.start(host=extra)
    elif param == 'off':
        server.stop()
    elif param is None:
        return server.info()


def importv(dest=None, path=''):
    '''
    import variables which was saved as pickled file

    '''
    import ifigure.utils.pickle_wrapper as pickle
    from ifigure.mto.py_code import PyData
    if dest is None:
        ifig_app = get_topwindow()
        dest = PyData()
        ifig_app.proj.add_child('data', dest)

    if path == '':
        open_dlg = wx.FileDialog(None, message="Select Data File",
                                 style=wx.FD_OPEN)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            return
        path = open_dlg.GetPath()
        open_dlg.Destroy()
        if path == '':
            return
    fid = open(path, 'r')
    data = pickle.load(fid)
    fid.close()

    for key in data:
        dest.setvar(key, data[key])

    ifigure.events.SendChangedEvent(dest, w=ifig_app, useProcessEvent=True)
    return dest


def exportv(variables, names, path=''):
    '''
    export variables as pickled file

    example: export([x, y, z], ['x', 'y', 'z'])
    note: one can make data_tree object and save it as project
          or export subtree.

    '''
    import cPickle as pickle
    save_dlg = wx.FileDialog(None, message="Enter Data File Name",
                             defaultDir=os.getcwd(),
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
    if save_dlg.ShowModal() != wx.ID_OK:
        save_dlg.Destroy()
        return
    path = save_dlg.GetPath()
    save_dlg.Destroy()
    if path == '':
        return

    fid = open(path, 'w')
    d = {n: v for v, n in zip(variables, names)}
    pickle.dump(d, fid)
    fid.close()


def quit():
    '''
    quit piScope
    '''
    ifig_app = get_topwindow()
    ifig_app.onQuit()


def glinfo():
    '''
    show OpenGL information
    '''
    try:
        import OpenGL
        import OpenGL.GL
    except ImportError:
        print("OpenGL not avaiable")
        return
    print('OpenGL Ver. : ' + OpenGL.GL.glGetString(OpenGL.GL.GL_VERSION).decode())
    print('GS Lang Ver.: ' +
          OpenGL.GL.glGetString(OpenGL.GL.GL_SHADING_LANGUAGE_VERSION).decode())
    print('Vendor      : ' + OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR).decode())
    print('Renderer    : ' + OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER).decode())


def setupmodel(package='', root='', path='setup_scripts', model=None,
               del_scripts=True):
    '''
    Utility command to setup simulation model. It uses
    mercurial repositories to store skelton scripts (and
    other pieces).

    setupmodel()
    setupmodel(package = '', root = '', path = 'setup_scripts', model=None,
               del_scripts = True, ):
    input:
         package: package name
         root   : root hg repository
         path   : paht to setup_scripts in repo
         model  : destination
    return :
         model object

    example:
         setupmodel()  : open dialog to pick model package
         setupmodel('genray_cql3d', '~/hg_root/ppkgs')
                       : setup genray_cql3d model pakcage using data
                         in hg repo at ~/hg_root/ppkags
    '''
    from ifigure.utils.model_setup_tools import setup
    return setup(package=package, model=model, root=root, path=path,
                 del_scripts=del_scripts)


def autoplay(viewer=None, interval=0.2):
    #timer = wx.Timer()
    # self.viewer.Bind(

    if viewer is None:
        viewer = aviewer
    if viewer is None:
        return

    def step_viewer(player=viewer, interval=interval):
        ipage = viewer.ipage
        num_page = viewer.book.num_page()
        if ipage == num_page-1:
            ipage = 0
        else:
            ipage = ipage + 1
        viewer.show_page(ipage)
        if viewer.timer is not None:
            viewer.timer.Start(interval*1000., oneShot=True)

    viewer.timer = wx.Timer(viewer)
    viewer.Bind(wx.EVT_TIMER, step_viewer)
    if viewer.isPropShown():
        viewer.toggle_property()

    viewer.timer.Start(interval*1000., oneShot=True)

    ifig_app = get_topwindow()
    x = ifig_app.shell.raw_input('stop?')
    viewer.timer.Stop()
    viewer.timer = None


# get_shellvar/put_shellvar is to manipulate shell variable
# from client
def get_shellvar(name):
    var = wx.GetApp().TopWindow.shell.lvar
    if name in var:
        return var[name]


def put_shellvar(name, value):
    var = wx.GetApp().TopWindow.shell.lvar
    var[name] = value

#
#  TODO (following functions needs to be revised
#


def get_page(ipage=None):
    return aviewer.get_page(ipage=ipage)


def get_axes(ipage=None, iaxes=None):
    return aviewer.get_axes(ipage=ipage, iaxes=iaxes)


def twinc():
    if aviewer is None:
        return
    fig_p = get_page(ipage=None)
    if fig_p is None:
        print("no page exists. use addpage() to create a page")
        return
    axes = get_axes(ipage=None, iaxes=None)
    axes.add_axis_param(dir='c')
    axes.set_bmp_update(False)
    draw()
    ifigure.events.SendChangedEvent(axes, w=aviewer, useProcessEvent=True)
