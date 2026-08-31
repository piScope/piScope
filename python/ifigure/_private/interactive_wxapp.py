
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
    pass


@redirect_to_aviewer
def cla(reset_color_cycle=True):
    pass


@redirect_to_aviewer
def cls():
    pass


@redirect_to_aviewer
def clf():
    pass


@redirect_to_aviewer
def nsec(*args, **kargs):
    pass


@redirect_to_aviewer
def nsection(*args, **kargs):
    pass


@redirect_to_aviewer
def subplot(*args, **kargs):
    pass


@redirect_to_aviewer
def isec(i=None):
    pass


@redirect_to_aviewer
def isection(i=None):
    pass


@redirect_to_aviewer
def addpage(num=1, before=False):
    pass


@redirect_to_aviewer
def delpage():
    pass


@redirect_to_aviewer
def suptitle(txt, size=None, color=None):
    pass


@redirect_to_aviewer
def title(txt, size=None, color=None):
    pass


@redirect_to_aviewer
def xlabel(txt, name='x', size=None, color=None):
    pass


@redirect_to_aviewer
def xtitle(txt, name='x', size=None, color=None):
    pass


@redirect_to_aviewer
def ylabel(txt, name='y', size=None, color=None):
    pass


@redirect_to_aviewer
def ytitle(txt, name='y', size=None, color=None):
    pass


@redirect_to_aviewer
def zlabel(txt, name='z', size=None, color=None):
    pass


@redirect_to_aviewer
def ztitle(*args):
    pass


@redirect_to_aviewer
def clabel(txt, name='c'):
    pass


@redirect_to_aviewer
def ctitle(*args):
    pass


@redirect_to_aviewer_hold
def xlog(value=True, base=None):
    pass


@redirect_to_aviewer_hold
def ylog(value=True, base=None):
    pass


@redirect_to_aviewer_hold
def clog(value=True, base=None):
    pass


@redirect_to_aviewer_hold
def zlog(value=True, base=None):
    pass


@redirect_to_aviewer_hold
def xsymlog(base=None, linthresh=None, linscale=None, name='x'):
    pass


@redirect_to_aviewer_hold
def ysymlog(base=None, linthresh=None, linscale=None,  name='y'):
    pass


@redirect_to_aviewer_hold
def zsymlog(base=None, linthresh=None, linscale=None, name='z'):
    pass


@redirect_to_aviewer_hold
def csymlog(base=None, linthresh=None, linscale=None, name='c'):
    pass


@redirect_to_aviewer_hold
def xlinear(value=True):
    pass


@redirect_to_aviewer_hold
def ylinear(value=True):
    pass


@redirect_to_aviewer_hold
def clinear(value=True):
    pass


@redirect_to_aviewer_hold
def zlinear(value=True):
    pass


@redirect_to_aviewer
def xauto(name='x'):
    pass


@redirect_to_aviewer
def yauto(name='y'):
    pass


@redirect_to_aviewer
def zauto(name='z'):
    pass


@redirect_to_aviewer
def cauto(name='c'):
    pass


@redirect_to_aviewer
def xlim(*range, **kargs):
    pass


@redirect_to_aviewer
def ylim(*range, **kargs):
    pass


@redirect_to_aviewer
def zlim(*range, **kargs):
    pass


@redirect_to_aviewer
def clim(*range, **kargs):
    pass


@redirect_to_aviewer
def twinx():
    pass


@redirect_to_aviewer
def twiny():
    pass


@redirect_to_aviewer_hold
def oplot(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def oerrorbar(*args, **kargs):
    pass


@redirect_to_aviewer
def loglog(*args, **kargs):
    pass


@redirect_to_aviewer
def semilogy(*args, **kargs):
    pass


@redirect_to_aviewer
def semilogx(*args, **kargs):
    pass


@redirect_to_aviewer
def timetrace(*args, **kargs):
    pass


@redirect_to_aviewer
def plotc(*args, **kargs):
    pass


@redirect_to_aviewer
def errorbarc(*args, **kargs):
    pass


@redirect_to_aviewer
def plot(*args, **kargs):
    pass


@redirect_to_aviewer
def scatter(*args, **kargs):
    pass


@redirect_to_aviewer
def hist(*args, **kargs):
    pass


@redirect_to_aviewer
def triplot(*args, **kargs):
    pass


@redirect_to_aviewer
def errorbar(*args, **kargs):
    pass


@redirect_to_aviewer
def annotate(*args, **kargs):
    pass


@redirect_to_aviewer
def ispline(*args, **kargs):
    pass


@redirect_to_aviewer
def contour(*args, **kargs):
    pass


@redirect_to_aviewer
def contourf(*args, **kargs):
    pass


@redirect_to_aviewer
def quiver(*args, **kargs):
    pass


@redirect_to_aviewer
def quiver3d(*args, **kargs):
    pass


@redirect_to_aviewer
def image(*args, **kargs):
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
    pass


@redirect_to_aviewer
def spec(*args, **kargs):
    pass


@redirect_to_aviewer
def tripcolor(*args, **kargs):
    pass


@redirect_to_aviewer
def tricontour(*args, **kargs):
    pass


@redirect_to_aviewer
def tricontourf(*args, **kargs):
    pass


@redirect_to_aviewer
def axline(*args, **kargs):
    pass


@redirect_to_aviewer
def axlinec(*args, **kargs):
    pass


@redirect_to_aviewer
def axspan(*args, **kargs):
    pass


@redirect_to_aviewer
def axspanc(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def text(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def figtext(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def arrow(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def figarrow(*args, **kargs):
    pass


@redirect_to_aviewer_hold
def legend(*args, **kargs):
    pass


@redirect_to_aviewer
def fill(*args, **kargs):
    pass


@redirect_to_aviewer
def fill_between(*args, **kargs):
    pass


@redirect_to_aviewer
def fill_betweenx(*args, **kargs):
    pass


@redirect_to_aviewer
def fill_between_3d(*args, **kargs):
    pass


@redirect_to_aviewer_3D
def surf(*args, **kargs):
    pass


@redirect_to_aviewer_3D
def surface(x, y, z, **kargs):
    pass


@redirect_to_aviewer_3D
def revolve(*args, **kargs):
    pass


@redirect_to_aviewer_3D
def solid(v, **kargs):
    pass


@redirect_to_aviewer_3D
def trisurf(v, **kargs):
    pass


@redirect_to_aviewer
def property(obj, name, *args):
    pass


@redirect_to_aviewer
def threed(*args):
    pass


@redirect_to_aviewer
def lighting(**kwargs):
    pass


@redirect_to_aviewer
def _view(*args, **kwargs):
    pass


def view(*args, **kwargs):
    if len(args) == 0 and len(kwargs) == 0:
        v = aviewer
        return v.view()
    else:
        return _view(*args, **kwargs)


@redirect_to_aviewer
def xnames(*args, **kwargs):
    pass


@redirect_to_aviewer
def ynames(*args, **kwargs):
    pass


@redirect_to_aviewer
def znames(*args, **kwargs):
    pass


@redirect_to_aviewer
def cnames(*args, **kwargs):
    pass


@redirect_to_aviewer
def cbar(*args, **kwargs):
    pass


@redirect_to_aviewer
def savefig(filename):
    pass


@redirect_to_aviewer
def savedata(filename):
    pass

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

    ### if file is not path, return here
    if (not isinstance(file, (str, bytes)) and
        not hasattr(file, '__fspath__')):
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
