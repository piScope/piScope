from __future__ import print_function
import warnings
import matplotlib.colors as mcolors
import six
import logging
import numpy as np
import ifigure
from ifigure.utils.cbook import ProcessKeywords
from collections import OrderedDict
from functools import wraps
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
import ifigure.utils.debug as debug
import traceback
'''
   BookViewrInteractive

    A class which implement interactive commands for
    bookviewer
      addpage, isec, hold

    doc_string of these methods are copied from
    ifigure.interactive, and therefore not written here.
'''

'''
   most of function uses one of these decorators

      1) allow_interactive_call
         this is for plot command
         returned object from method will be added
         process update and hold keyword
         copy doc_string from ifigure.interactive

      2) allow_interactive_call2
         this is for commands to edit properties, such as title
         process update
         copy doc_string from ifigure.interactive

      3) share_doc_string
         this one just copy doc_string from ifigure.interactive

   decorator to update, hold functionality to
   methods for interactive ploting,
   also it copies doc_string from functions
   in ifigure.interactive
'''


_type_numbers = ['int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32',
                 'uint64', 'float16', 'float32', 'float64', 'complex64', 'complex128', 'complex256', ]
_dtype_numbers = []
for x in _type_numbers:
    try:
        _dtype_numbers.append(np.dtype(x))
    except:
        print('numpy does not know type = '+x)


class NoPageError(Exception):
    pass


class InteractiveCommandError(Exception):
    pass


dprint1, dprint2, dprint3 = debug.init_dprints('BookViewerInteractive')


def has_plot(figaxes):
    from ifigure.mto.fig_axes import FigAxes
    from ifigure.mto.fig_text import FigText
    from ifigure.mto.fig_box import FigBox
    from ifigure.mto.fig_circle import FigCircle
    from ifigure.mto.fig_legend import FigLegend
    for obj in figaxes.walk_tree():
        if (not isinstance(obj, FigAxes) and
            not isinstance(obj, FigText) and
            not isinstance(obj, FigBox) and
                not isinstance(obj, FigCircle)):
            return True
    return False


def pop_metadata(kargs):
    '''
       metadata is either dictionary
       or
           longname,
           xlongname
           ylongname and so on

      example :
           plot(np.arange(30), metadata = {'longname':'plot name',
                                           'xdata':{'longname': 'xdata name', 'unit': '[s]'},
                                           'ydata':{'longname': 'ydata name', 'unit': '[V]'}})
           plot(np.arange(30), metadata = 'metadata', xmetadata='xdata')

           note: "name" in metadata is reseved, and piScope automatically
                 fills using axis lables.
    '''
    meta0 = kargs.pop('metadata', None)
    if isinstance(meta0, dict):
        meta = OrderedDict()
        for k in meta0:
            if k.endswith('data'):
                if not 'data' in meta:
                    meta['data'] = {}
                meta['data'][k] = OrderedDict(meta0[k])
            else:
                meta[k] = meta0[k]
    else:
        meta = OrderedDict()
        if meta0 is not None:
            meta['name'] = ''
            meta['long_description'] = meta0

        names = []
        for k in kargs:
            if k.endswith('metadata'):
                names.append(k)
                header = k[:-8]
                if header == '':
                    pass
                else:
                    if not 'data' in meta:
                        meta['data'] = {}
                    meta['data'][header+'data'] = OrderedDict()
                    meta['data'][header+'data']['name'] = ''
                    meta['data'][header+'data']['long_description'] = kargs[k]
        if len(names) == 0:
            return None
        for name in names:
            del kargs[name]
    return meta


def allow_interactive_call(method):
    @wraps(method)
    def method2(self, *args, **kargs):
        metadata = pop_metadata(kargs)
        update, kargs = ProcessKeywords(
            kargs, 'update', value=self._interactive_update)
        hold, kargs = ProcessKeywords(kargs, 'hold', value=True)
        autonext, kargs = ProcessKeywords(kargs, 'autonext', value=True)

        f_page = self.get_page()
        if f_page is None:
            self.addpage()
        f_axes = f_page.get_axes(self.isec())
        if not self.canvas.hold_once() and not hold and self.isec() != -1:
            if has_plot(f_axes) and autonext:
                self.increment_isec()
                f_axes = f_page.get_axes(self.isec())
            f_axes.cla()
        if self.canvas.hold_once() and not hold and self.isec() != -1:
            f_axes.cla()

        ret = method(self, *args, **kargs)

        if ret is None:
            return
        if isinstance(ret, tuple):
            obj = ret[-1]
        else:
            obj = ret
        self.canvas.hold_once(False)
        obj = self.add_interative(obj)
        if metadata is not None:
            obj.setvar('metadata', OrderedDict(metadata))

        if update:
            ifigure.events.SendChangedEvent(
                self.book, w=self, useProcessEvent=True)
            ifigure.events.SendPVDrawRequest(
                self.book, wait_idle=True, refresh_hl=False)
        return obj
    import ifigure.interactive
    if hasattr(ifigure.interactive, method.__name__):
        f = getattr(ifigure.interactive, method.__name__)
        method2.__doc__ = f.__doc__
    return method2


def allow_interactive_call_autonext_false(method):
    @wraps(method)
    def method2(self, *args, **kargs):

        update, kargs = ProcessKeywords(
            kargs, 'update', value=self._interactive_update)
        hold, kargs = ProcessKeywords(kargs, 'hold', value=True)
        autonext, kargs = ProcessKeywords(kargs, 'autonext', value=False)

        f_page = self.get_page()
        if f_page is None:
            self.addpage()
        f_page = self.get_page()
        f_axes = f_page.get_axes(self.isec())
        if not self.canvas.hold_once() and not hold and self.isec() != -1:
            if has_plot(f_axes) and autonext:
                self.increment_isec()
                f_axes = f_page.get_axes(self.isec())
            f_axes.cla()
        if self.canvas.hold_once() and not hold and self.isec() != -1:
            f_axes.cla()

        ret = method(self, *args, **kargs)
        if ret is None:
            return
        if isinstance(ret, tuple):
            obj = ret[-1]
        else:
            obj = ret

        self.canvas.hold_once(False)
        obj = self.add_interative(obj)

        if update:
            ifigure.events.SendChangedEvent(
                self.book, w=self, useProcessEvent=True)
            ifigure.events.SendPVDrawRequest(
                self.book, wait_idle=True, refresh_hl=False)
        return obj
    import ifigure.interactive
    if hasattr(ifigure.interactive, method.__name__):
        f = getattr(ifigure.interactive, method.__name__)
        method2.__doc__ = f.__doc__
    return method2


def allow_interactive_call_page(method):
    @wraps(method)
    def method2(self, *args, **kargs):

        update, kargs = ProcessKeywords(
            kargs, 'update', value=self._interactive_update)
        hold, kargs = ProcessKeywords(kargs, 'hold', value=True)

        ret = method(self, *args, **kargs)

        if ret is None:
            return
        if isinstance(ret, tuple):
            obj = ret[-1]
        else:
            obj = ret

        f_page = self.get_page()
        if f_page is None:
            self.addpage()
        f_page = self.get_page()

        obj = self.add_interative(obj, parent=f_page)
        if update:
            ifigure.events.SendChangedEvent(
                self.book, w=self, useProcessEvent=True)
            ifigure.events.SendPVDrawRequest(
                self.book, wait_idle=True, refresh_hl=False)
        return ret
    import ifigure.interactive
    if hasattr(ifigure.interactive, method.__name__):
        f = getattr(ifigure.interactive, method.__name__)
        method2.__doc__ = f.__doc__
    return method2


def allow_interactive_call2(method):
    @wraps(method)
    def method2(self, *args, **kargs):
        from ifigure.utils.cbook import ProcessKeywords
        update, kargs = ProcessKeywords(
            kargs, 'update', value=self._interactive_update)
        hold, kargs = ProcessKeywords(kargs, 'hold', value=True)

        ret = method(self, *args, **kargs)
        if update:
            ifigure.events.SendChangedEvent(
                self.book, w=self, useProcessEvent=True)
            ifigure.events.SendPVDrawRequest(
                self.book, wait_idle=True, refresh_hl=False)
        return ret
    import ifigure.interactive
    if hasattr(ifigure.interactive, method.__name__):
        f = getattr(ifigure.interactive, method.__name__)
        method2.__doc__ = f.__doc__
    return method2


def share_doc_string_simple(method):
    @wraps(method)
    def method2(self, *args, **kargs):
        ret = method(self, *args, **kargs)
        return ret
    import ifigure.interactive
    f = getattr(ifigure.interactive, method.__name__)
    method2.__doc__ = f.__doc__
    return method2


def share_doc_string(method):
    @wraps(method)
    def method2(self, *args, **kargs):
        update, kargs = ProcessKeywords(kargs, 'update',
                                        value=self._interactive_update)
        hold, kargs = ProcessKeywords(kargs, 'hold', value=True)
        ret = method(self, *args, **kargs)
        return ret
    import ifigure.interactive
    f = getattr(ifigure.interactive, method.__name__)
    method2.__doc__ = f.__doc__
    return method2


class BookViewerInteractive(object):
    def __init__(self):
        self._interactive_update = True
        self._interactive_update_request = ([], [])

    def add_interative(self, obj, parent=None, floating=False):
        # first check if any page does exist

        f_page = self.get_page()
        if parent is None:
            parent = self.get_axes(ipage=None, iaxes=self.isec())
        if parent is None:
            raise InteractiveCommandError('no axes exists')

        name = parent.get_next_name(obj.get_namebase())
        if self._interactive_update:
            parent.add_child(name, obj)
        else:
            parent.add_child(name, obj, z_base=self)
        if floating:
            obj._floating = True

        try:
            if self._interactive_update:
                from ifigure.mto.fig_axes import FigAxes
                if isinstance(parent, FigAxes):
                    parent.adjust_axes_range()
                obj.realize()
            else:
                self._interactive_update_request[0].append(obj)
                if not parent in self._interactive_update_request[1]:
                    self._interactive_update_request[1].append(parent)
        except Exception:
            logging.exception("ifigure_app: realize() failed")
            obj.destroy()
            return None
        return obj

    def increment_isec(self):
        '''
        increment_isec moves the current axes to the next
        position by incrementing isec. if isec+1=nsec,
        isec is set to zero
        '''
        f_page = self.get_page()
        f_axes = f_page.get_axes(self.isec()+1)
        if f_axes is None:
            self.canvas._isec = 0
        else:
            self.canvas._isec = self.isec()+1

    def decrement_isec(self):
        '''
        increment_isec moves the current axes to the next
        position by incrementing isec. if isec+1=nsec,
        isec is set to zero
        '''
        f_page = self.get_page()
        f_axes = f_page.get_axes(self.isec()-1)
        if f_axes is None:
            self.canvas._isec = f_page.num_axes(include_floating=True)-1
        else:
            self.canvas._isec = self.isec()-1

    def update(self, value):
        from ifigure.mto.fig_axes import FigAxes
        if value:
            if not self._interactive_update:
                for parent in self._interactive_update_request[1]:
                    if isinstance(parent, FigAxes):
                        parent.adjust_axes_range()
                for obj in self._interactive_update_request[0]:
                    try:
                        obj.realize()
                    except:
                        traceback.print_exc()
                        print("failed to realize (destroied)" + str(obj))
                        obj.destroy()
                self._interactive_update_request = ([], [])
                ifigure.events.SendChangedEvent(
                    self.book, w=self, useProcessEvent=True)
                ifigure.events.SendPVDrawRequest(
                    self.book, wait_idle=True, refresh_hl=False)
        else:
            f_page = self.get_page()
            if f_page is not None:
                self._z_base = max([obj2.getp('zorder')
                                    for obj2 in f_page.walk_figobj()])
            else:
                self._z_base = 1
        self._interactive_update = value

    @share_doc_string
    def addpage(self, num=1, before=False):
        for k in range(num):
            page = self.new_page()
            i = self.add_page(page, before=before)

        fig_p = self.get_page(ipage=i)
        fig_b = self.book
        ifigure.events.SendChangedEvent(fig_b, w=self, useProcessEvent=True)
        ifigure.events.SendShowPageEvent(fig_p, w=self)
        return fig_p

    @share_doc_string
    def showpage(self, ipage):
        self.show_page(ipage)

    @share_doc_string
    def delpage(self):
        ipage = self.ipage
        fig_b = self.get_page(ipage=ipage).get_figbook()
        if fig_b.num_page() == 1:
            raise InteractiveCommandError('can not delete the current page')
        self.del_page()
        ifigure.events.SendChangedEvent(fig_b, w=self, useProcessEvent=True)

    @allow_interactive_call2
    def cla(self, reset_color_cycle=True):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError()

        axes = self.get_axes(ipage=None, iaxes=self.isec())
        axes.cla()
        axes.reset_color_cycle()

    @allow_interactive_call2
    def cls(self, obj=None):
        self.clf(obj=obj)

    @allow_interactive_call2
    def clf(self, obj=None):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError('no page exists')
        for axes in fig_p.walk_axes():
            axes.reset_color_cycle()
            children = [child for child in axes.walk_tree()]
            if obj is not None:
                children = [obj] if obj in children else []
            for child in children:
                if (not hasattr(child, '_generic_axes') or
                        not child._generic_axes):
                    child.destroy()
                else:
                    child.reset_color_cycle()
        if self.nsec() > 0:
            self.isec(0)

    def _do_subplot(self, *args, **kargs):
        fig_p = self.get_page()
        if fig_p is None:
            raise NoPageError('no page exists')

        if len(args) == 0:
            return fig_p.num_axes()

        self.set_section(*args, **kargs)
        ax = self.get_axes(ipage=None, iaxes=self.isec())
        if ax is None:
            ax = self.get_axes(ipage=None, iaxes=0)
        return ax

    @allow_interactive_call2
    def nsec(self, *args, **kargs):
        return self._do_subplot(*args, **kargs)

    @allow_interactive_call2
    def subplot(self, *args, **kargs):
        return self._do_subplot(*args, **kargs)

    @share_doc_string
    def isec(self, i=None):
        '''
        isce/isection control current axes.
        '''
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError('no page exists')

        if i is not None:

            fig_p = self.get_page(ipage=None)
            if fig_p.get_axes(iax=i) is None:
                raise InteractiveCommandError('axes['+str(fig_p.num_axes()) +
                                              '] does not exist')
            self.canvas._isec = i
            return self.canvas._isec
        else:
            if self.canvas._isec == -1:
                fig_ax = self.get_axes(ipage=None, iaxes=0)
                if fig_ax is not None:
                    self.set_axes(fig_ax)
                    self.canvas._isec = 0
            return self.canvas._isec

    @allow_interactive_call2
    def suptitle(self, txt, size=None, color=None):
        fig_page = self.get_page(ipage=None)
        fig_page.set_suptitle(txt, a=None, size=size, color=color)

    @allow_interactive_call2
    def title(self, txt, size=None, color=None):
        '''
        set title of current section
        '''
        fig_ax = self.get_axes(ipage=None, iaxes=self.isec())
        if fig_ax is None:
            return
        if len(fig_ax._artists) == 0:
            fig_ax.getp('title_labelinfo')[0] = txt
        else:
            v = fig_ax.get_title(fig_ax._artists[0])
            v[0] = txt
            if size is not None:
                v[-1] = 'default' if size == 'default' else float(size)
            if color is not None:
                v[1] = color
            fig_ax.set_title(v, fig_ax._artists[0])
        fig_ax.set_bmp_update(False)

    def _set_label(self, txt, name, size, color):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError("no page exists")
        fig_ax = self.get_axes(ipage=None, iaxes=self.isec())
        if fig_ax.get_axis_param(name) is None:
            raise InteractiveCommandError('Axis ('+name + ') does not exist')

        v = fig_ax.get_axlabel(fig_ax._artists[0], name)
        if txt is None and size is None:
            return v
        if txt is not None:
            v[0] = txt
        if size is not None:
            v[-1] = 'default' if size == 'default' else float(size)
        if color is not None:
            v[1] = color
        fig_ax.set_axlabel((name, v), fig_ax._artists[0])
        fig_ax.set_bmp_update(False)
        return txt

    @allow_interactive_call2
    def xlabel(self, txt=None, name='x', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def xtitle(self, txt=None, name='x', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def ylabel(self, txt=None, name='y', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def ytitle(self, txt=None, name='y', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def zlabel(self, txt=None, name='z', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def ztitle(self, txt=None, name='z', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def clabel(self, txt=None, name='c', size=None, color=None):
        return self._set_label(txt, name, size, color)

    @allow_interactive_call2
    def ctitle(self, txt=None, name='c', size=None, color=None):
        return self._set_label(txt, name, size, color)

    def _set_log(self, v, name, base=None, linthresh=None, linscale=None):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError("no page exists")
        fig_ax = self.get_axes(ipage=None, iaxes=self.isec())
        if fig_ax.get_axis_param(name) is None:
            raise InteractiveCommandError('Axis ('+name + ') does not exist')

        val = fig_ax.get_axrangeparam(fig_ax._artists[0], name)
        if v == 'symlog':
            val[3] = 'symlog'
        elif v == False:
            val[3] = 'linear'
        elif v == True:
            val[3] = 'log'
        if base is not None:
            val[0] = str(base)
        if linthresh is not None:
            val[4] = linthresh
        if linscale is not None:
            val[5] = linscale
        request = [(name, val)]
        request = fig_ax.compute_new_range(request=[(name, val)])
        fig_ax.perform_range_request(request)

    @allow_interactive_call2
    def xlog(self, value=True, base=None):
        self._set_log(value, 'x', base=base)

    @allow_interactive_call2
    def ylog(self, value=True, base=None):
        self._set_log(value, 'y', base=base)

    @allow_interactive_call2
    def clog(self, value=True, base=None):
        self._set_log(value, 'c', base=base)

    @allow_interactive_call2
    def zlog(self, value=True, base=None):
        self._set_log(value, 'z', base=base)

    @allow_interactive_call2
    def xlinear(self, value=False):
        self._set_log(value, 'x')

    @allow_interactive_call2
    def ylinear(self, value=False):
        self._set_log(value, 'y')

    @allow_interactive_call2
    def clinear(self, value=False):
        self._set_log(value, 'c')

    @allow_interactive_call2
    def zlinear(self, value=False):
        self._set_log(value, 'z')

    @allow_interactive_call2
    def xsymlog(self, base=None, linthresh=None, linscale=None,
                name='x'):
        self._set_log('symlog', name, base=base, linthresh=linthresh,
                      linscale=linscale)

    @allow_interactive_call2
    def ysymlog(self, base=None, linthresh=None, linscale=None,
                name='y'):
        self._set_log('symlog', name, base=base, linthresh=linthresh,
                      linscale=linscale)

    @allow_interactive_call2
    def zsymlog(self, base=None, linthresh=None, linscale=None,
                name='z'):
        self._set_log('symlog', name, base=base, linthresh=linthresh,
                      linscale=linscale)

    @allow_interactive_call2
    def csymlog(self, base=None, linthresh=None, linscale=None,
                name='c'):
        self._set_log('symlog', name, base=base, linthresh=linthresh,
                      linscale=linscale)

    def _set_auto(self, name):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError("no page exists")
        axes = self.get_axes(ipage=None, iaxes=self.isec())
        if axes.get_axis_param(name) is None:
            raise InteractiveCommandError('Axis ('+name + ') does not exist')

        v = axes.get_axrangeparam(axes._artists[0], name)
        v[1] = True
        request = axes.compute_new_range(request=[(name, v)])
        for r in request:
            axes.set_axrangeparam(r, axes._artists[0])
        ifigure.events.SendPVDrawRequest(axes, w=self, wait_idle=False,
                                         refresh_hl=False)

    @allow_interactive_call2
    def xauto(self, name='x'):
        self._set_auto(name)

    @allow_interactive_call2
    def yauto(self, name='y'):
        self._set_auto(name)

    @allow_interactive_call2
    def zauto(self, name='z'):
        self._set_auto(name)

    @allow_interactive_call2
    def cauto(self, name='c'):
        self._set_auto(name)

    def _set_lim(self, *range, **kargs):
        if len(range) == 2:
            val = (range[0], range[1])
        elif len(range) == 0:
            val = None
        else:
            val = range[0]

        name = kargs['name']

        if (name.startswith('x') or name.startswith('y') or
                name.startswith('z')):
            axis_param_names0 = ('tick_position', 'ticks', 'tcolor',
                                 'lcolor', 'lsize', 'otcolor', 'otsize')
            axis_param_names = ('tposition', 'ticks', 'tcolor',
                                'color', 'size', 'ocolor', 'osize')
            axis_param = {x: kargs[x] for x in axis_param_names if x in kargs}

        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError("no page exists")
        axes = self.get_axes(ipage=None, iaxes=self.isec())
        if axes.get_axis_param(name) is None:
            raise InteractiveCommandError('Axis ('+name + ') does not exist')
        v = axes.get_axrangeparam(axes._artists[0], name)
        if val is None:
            return v[2]
        v[1] = False
        v[2] = val
        axes.set_axrangeparam((name, v), axes._artists[0])

        if (name.startswith('x') or name.startswith('y') or
                name.startswith('z')):

            ap = axes.get_axis_param(name)
            for x, y in zip(axis_param_names0, axis_param_names):
                if y in axis_param:
                    setattr(ap, x, axis_param[y])
            artist = axes.get_axes_artist_by_name(name)[0]
            ap.set_tickparam(artist, axes)
            ap.set_ticks(artist)

        axes.set_bmp_update(False)

    @allow_interactive_call2
    def xlim(self, *range, **kargs):
        name, kargs = ProcessKeywords(kargs, 'name', value='x')
        kargs['name'] = name
        return self._set_lim(*range, **kargs)

    @allow_interactive_call2
    def ylim(self, *range, **kargs):
        name, kargs = ProcessKeywords(kargs, 'name', value='y')
        kargs['name'] = name
        return self._set_lim(*range, **kargs)

    @allow_interactive_call2
    def zlim(self, *range, **kargs):
        name, kargs = ProcessKeywords(kargs, 'name', value='z')
        kargs['name'] = name
        return self._set_lim(*range, **kargs)

    @allow_interactive_call2
    def clim(self, *range, **kargs):
        name, kargs = ProcessKeywords(kargs, 'name', value='c')
        kargs['name'] = name
        return self._set_lim(*range, **kargs)

    @allow_interactive_call2
    def twinx(self):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError('no page exists')
        axes = self.get_axes(ipage=None, iaxes=self.isec())
        if axes.hastwin('x'):
            raise InteractiveCommandError('axes has twin already')
        #cvalue = axes.get_twinx(None)
        axes.twinx()
        value = [p.make_save_data(axes) for p in axes._yaxis]
        value.append(axes._yaxis[-1].make_save_data(axes))
        value[-1]["_ax_idx"] = []
        value = (True, value)
        axes.del_twinx()
        axes.set_twinx(value, None)
        axes.set_bmp_update(False)

    @allow_interactive_call2
    def twiny(self):
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError('no page exists')
        axes = self.get_axes(ipage=None, iaxes=self.isec())
        if axes.hastwin('y'):
            raise InteractiveCommandError('axes has twin already')
        #cvalue = axes.get_twiny(None)
        axes.twiny()
        value = [p.make_save_data(axes) for p in axes._xaxis]
        value.append(axes._xaxis[-1].make_save_data(axes))
        value[-1]["_ax_idx"] = []
        value = (True, value)
        axes.del_twiny()
        axes.set_twiny(value, None)
        axes.set_bmp_update(False)

    @allow_interactive_call2
    def threed(self, *args):
        import ifigure.utils.cbook as cbook
        ax = self.get_axes(ipage=None, iaxes=self.isec())
        if ax is None:
            return
        if len(args) == 0:
            return ax.get_3d()
        v = cbook.on_off_args(args[0])
        ax.set_3d(v)
        # ax.del_artist(delall=True)
        # ax.realize()
        self.draw()
        self.canvas.set_axes_selection(ax._artists[0])
        self.canvas.toolbar.Show3DMenu()

    def oplot(self, *args, **kargs):
        kargs['hold'] = True
        v = self.plot(*args, **kargs)
        return v

    def oerrorbar(self, *args, **kargs):
        kargs['hold'] = True
        v = self.errorbar(*args, **kargs)
        return v

    @allow_interactive_call
    def timetrace(self, *args, **kargs):
        from ifigure.mto.fig_plot import TimeTrace
        obj = self._plot(*args, **kargs)
        if obj is not None:
            obj.__class__ = TimeTrace
            obj._use_decimate = True
        return obj

    @allow_interactive_call
    def plot(self, *args, **kargs):
        return self._plot(*args, **kargs)

    @allow_interactive_call
    def loglog(self, *args, **kargs):
        ret = self._plot(*args, **kargs)
        self._set_log(True, 'x')
        self._set_log(True, 'y')
        return ret

    @allow_interactive_call
    def semilogy(self, *args, **kargs):
        ret = self._plot(*args, **kargs)
        self._set_log(True,  'y')
        self._set_log(False, 'x')
        return ret

    @allow_interactive_call
    def semilogx(self, *args, **kargs):
        ret = self._plot(*args, **kargs)
        self._set_log(True,   'x')
        self._set_log(False,  'y')
        return ret

    @allow_interactive_call
    def plotc(self, *args, **kargs):
        from ifigure.mto.fig_plotc import FigPlotC
        kargs['cls'] = FigPlotC
        return self._plot(*args, **kargs)

    @allow_interactive_call
    def errorbar(self, *args, **kargs):
        from ifigure.mto.fig_plot import FigPlot
        kargs['mpl_command'] = 'errorbar'
        return self._plot(*args, **kargs)

    @allow_interactive_call
    def errorbarc(self, *args, **kargs):
        from ifigure.mto.fig_plotc import FigPlotC
        kargs['cls'] = FigPlotC
        kargs['mpl_command'] = 'errorbar'
        return self._plot(*args, **kargs)

    def _plot(self, *args, **kargs):
        from ifigure.utils.cbook import isiterable, isndarray, isdynamic, issequence, isnumber

        def convert_2_real_array(a):
            '''
            it actually keep complex as complex (2015.09.29)
            '''
            if a is None:
                return None
            if not isiterable(a):
                return a
            if len(a) == 1:
                return a
            if np.array(a).dtype in _dtype_numbers:
                return a
            else:
                x = np.array(a).astype(float)
                return x

        from ifigure.mto.fig_plot import FigPlot
        from ifigure.mto.fig_grp import FigGrp

        cls, kargs = ProcessKeywords(kargs, 'cls', value=FigPlot)
        # this is to analyze arguments
        try:
            obj = cls(*args, **kargs)
        except ValueError as x:
            traceback.print_exc()
            if hasattr(x, 'message'):
                print(x.message)
            return

        x = convert_2_real_array(obj.getvar('x'))
        y = convert_2_real_array(obj.getvar('y'))
        z = convert_2_real_array(obj.getvar('z'))
        c = convert_2_real_array(obj.getvar('c'))
        xerr = convert_2_real_array(obj.getvar('xerr'))
        yerr = convert_2_real_array(obj.getvar('yerr'))

        if (isinstance(y, np.ndarray) and
                x.ndim == 1 and y.ndim == 2):
            s = obj.getvar('s')
            obj = FigGrp()
            for k in range(y.shape[0]):
                if 'xerr' in kargs:
                    if isiterable(xerr):
                        kargs['xerr'] = xerr[k]
                if 'yerr' in kargs:
                    if isiterable(yerr):
                        kargs['yerr'] = yerr[k]
                if c is not None:
                    kargs['c'] = c[k]
                if z is None:
                    obj2 = FigPlot(x, y[k], s, **kargs)
                else:
                    obj2 = FigPlot(x, y[k], z[k], s, **kargs)
                name = obj.get_next_name(obj2.get_namebase())
                obj.add_child(name, obj2)
        elif (isinstance(x, np.ndarray) and
              x.ndim == 2 and y.ndim == 1):
            s = obj.getvar('s')
            obj = FigGrp()
            for k in range(x.shape[0]):
                if 'xerr' in kargs:
                    if isiterable(xerr):
                        kargs['xerr'] = xerr[k]
                if 'yerr' in kargs:
                    if isiterable(yerr):
                        kargs['yerr'] = yerr[k]
                if c is not None:
                    kargs['c'] = c[k]
                if z is None:
                    obj2 = FigPlot(x[k], y, s, **kargs)
                else:
                    obj2 = FigPlot(x[k], y, z[k], s, **kargs)
                name = obj.get_next_name(obj2.get_namebase())
                obj.add_child(name, obj2)
        elif (isinstance(x, np.ndarray) and
              x.ndim == 2 and y.ndim == 2):
            s = obj.getvar('s')
            obj = FigGrp()
            for k in range(x.shape[0]):
                if 'xerr' in kargs:
                    if isiterable(xerr):
                        kargs['xerr'] = xerr[k]
                if 'yerr' in kargs:
                    if isiterable(yerr):
                        kargs['yerr'] = yerr[k]
                if c is not None:
                    kargs['c'] = c[k]
                if z is None:
                    obj2 = FigPlot(x[k], y[k], s, **kargs)
                else:
                    obj2 = FigPlot(x[k], y[k], z[k], s, **kargs)
                name = obj.get_next_name(obj2.get_namebase())
                obj.add_child(name, obj2)
        else:
            obj.setvar('x', x)
            obj.setvar('y', y)
            obj.setvar('z', z)
            obj.setvar('xerr', xerr)
            obj.setvar('yerr', yerr)

        return obj

    @allow_interactive_call
    def triplot(self, *args, **kargs):
        from ifigure.mto.fig_triplot import FigTriplot
        try:
            obj = FigTriplot(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call
    def annotate(self, *args, **kargs):
        from ifigure.mto.fig_annotate import FigAnnotate
        obj = FigAnnotate(*args, **kargs)
        return obj

    @allow_interactive_call
    def ispline(self, *args, **kargs):
        from ifigure.mto.fig_spline import FigSpline
        try:
            obj = FigSpline(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def contour(self, *args, **kargs):
        from ifigure.mto.fig_contour import FigContour
        if not "FillMode" in kargs:
            kargs["FillMode"] = False
        try:
            obj = FigContour(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def contourf(self, *args, **kargs):
        from ifigure.mto.fig_contour import FigContour
        kargs["FillMode"] = True
        try:
            obj = FigContour(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def scatter(self, *args, **kargs):
        from ifigure.mto.fig_scatter import FigScatter
        try:
            obj = FigScatter(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def hist(self, x, *args, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        axes = fig_axes._artists[0]

        color = kargs.pop('color', None)
        weights = kargs.pop('weights', None)

        # Process 'x'
        # This part is copied from matplotlib._axes.
        from matplotlib.cbook import iterable
        if isinstance(x, np.ndarray) or not iterable(x[0]):
            # TODO: support masked arrays;
            x = np.asarray(x)
            if x.ndim == 2:
                x = x.T  # 2-D input with columns as datasets; switch to rows
            elif x.ndim == 1:
                x = x.reshape(1, x.shape[0])  # new view, single row
            else:
                raise ValueError("x must be 1D or 2D")
            if x.shape[1] < x.shape[0]:
                warnings.warn(
                    '2D hist input should be nsamples x nvariables;\n '
                    'this looks transposed (shape is %d x %d)' % x.shape[::-1])
        else:
            # multiple hist with data of different length
            x = [np.asarray(xi) for xi in x]

        nx = len(x)  # number of dataset
        from ifigure.matplotlib_mod.mpl_utils import get_color_cycle_list
        if color is None:
            color = get_color_cycle_list(axes)
        else:
            color = mcolors.colorConverter.to_rgba_array(color)
            if len(color) != nx:
                raise ValueError("color kwarg must have one color per dataset")

        # We need to do to 'weights' what was done to 'x'
        if weights is not None:
            if isinstance(weights, np.ndarray) or not iterable(weights[0]):
                w = np.array(weights)
                if w.ndim == 2:
                    w = w.T
                elif w.ndim == 1:
                    w.shape = (1, w.shape[0])
                else:
                    raise ValueError("weights must be 1D or 2D")
            else:
                w = [np.asarray(wi) for wi in weights]

            if len(w) != nx:
                raise ValueError('weights should have the same shape as x')
            for i in range(nx):
                if len(w[i]) != len(x[i]):
                    raise ValueError(
                        'weights should have the same shape as x')
        else:
            w = [None]*nx

        #
        #  end of processing
        from ifigure.mto.fig_hist import FigHist
        from ifigure.mto.fig_grp import FigGrp
        import wx
        try:
            if nx == 1:
                kargs['weights'] = w[0]
                kargs['color'] = color[0]
                obj = FigHist(x[0], *args, **kargs)
                wx.CallAfter(obj.call_adjust_range)
            else:
                obj = FigGrp()
                for k, xx in enumerate(x):
                    kargs['weights'] = w[k]
                    kargs['color'] = color[k]
                    obj2 = FigHist(xx, *args, **kargs)
                    name = obj.get_next_name(obj2.get_namebase())
                    obj.add_child(name, obj2)
                wx.CallAfter(obj2.call_adjust_range)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call
    def tricontour(self, *args, **kargs):
        from ifigure.mto.fig_tricontour import FigTricontour
        if not "FillMode" in kargs:
            kargs["FillMode"] = False
        try:
            obj = FigTricontour(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def tricontourf(self, *args, **kargs):
        from ifigure.mto.fig_tricontour import FigTricontour
        kargs["FillMode"] = True
        try:
            obj = FigTricontour(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def image(self, *args, **kargs):
        if 'use_tri' in kargs and kargs['use_tri']:
            return tripcolor(*args, **kargs)

        from ifigure.mto.fig_image import FigImage
        try:
            obj = FigImage(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def quiver(self, *args, **kargs):
        from ifigure.mto.fig_quiver import FigQuiver, FigQuiver3D

        is3D = self.threed()
        try:
            if is3D:
                obj = FigQuiver3D(*args, **kargs)
            else:
                obj = FigQuiver(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def quiver3d(self, *args, **kargs):
        from ifigure.mto.fig_quiver import FigQuiver, FigQuiver3D

        self.threed('on')
        try:
            obj = FigQuiver3D(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    import matplotlib.mlab as mlab
#    @allow_interactive_call

    def specgram(self, x, NFFT=256,
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
        fig_p = self.get_page(ipage=None)
        if fig_p is None:
            raise NoPageError('no page exists')

#        axes = self.get_axes(ipage=None, iaxes=self.isec())
        Pxx, freqs, bins = mlab.specgram(x, NFFT=NFFT,
                                         Fs=Fs,
                                         detrend=detrend,
                                         window=window,
                                         noverlap=noverlap,
                                         pad_to=None,
                                         sides='default',
                                         scale_by_freq=None)
#        im.remove()
        freqs = freqs + Fc
        obj = self.image(bins, freqs, Pxx, **kwargs)
        return Pxx, freqs, bins, obj

    @allow_interactive_call
    def spec(self, *args, **kargs):
        from ifigure.mto.fig_spec import FigSpec
        try:
            obj = FigSpec(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def tripcolor(self, *args, **kargs):
        from ifigure.mto.fig_tripcolor import FigTripcolor
        try:
            obj = FigTripcolor(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def axline(self, *args, **kargs):
        from ifigure.mto.fig_axline import FigAxline
        try:
            obj = FigAxline(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call
    def axlinec(self, *args, **kargs):
        from ifigure.mto.fig_axlinec import FigAxlineC
        try:
            obj = FigAxlineC(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call
    def axspan(self, *args, **kargs):
        from ifigure.mto.fig_axspan import FigAxspan
        try:
            obj = FigAxspan(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call
    def axspanc(self, *args, **kargs):
        from ifigure.mto.fig_axspanc import FigAxspanC
        try:
            obj = FigAxspanC(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call_autonext_false
    def text(self, *args, **kargs):
        from ifigure.mto.fig_text import FigText

        try:
            if not 'trans' in kargs:
                kargs['trans'] = ['axes']*2
            else:
                if isinstance(kargs['trans'], str):
                    kargs['trans'] = [kargs['trans']]*2

            obj = FigText(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return

        return obj

    @allow_interactive_call_autonext_false
    def arrow(self, *args, **kargs):
        from ifigure.mto.fig_arrow import FigArrow

        try:
            if not 'trans' in kargs:
                kargs['trans'] = ['axes']*4
            else:
                if isinstance(kargs['trans'], str):
                    kargs['trans'] = [kargs['trans']]*4
            #kargs['autonext'] = False
            obj = FigArrow(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call_page
    def figarrow(self, *args, **kargs):
        from ifigure.mto.fig_arrow import FigArrow

        try:
            if not 'trans' in kargs:
                kargs['trans'] = ['figure']*4
            obj = FigArrow(*args, **kargs)
        except ValueError as x:
            print(x.message)
            return
        return obj

    @allow_interactive_call_page
    def figtext(self, *args, **kargs):
        from ifigure.mto.fig_text import FigText

        obj = FigText(*args, **kargs)
        if obj is None:
            return

        return obj

    @allow_interactive_call_autonext_false
    def legend(self, *args, **kargs):
        from ifigure.mto.fig_legend import FigLegend
        if len(args) == 0:
            return
        if len(args) == 1 and isinstance(args[0], str):
            args = ((args[0],),)
        if "axes2" in kargs:
            kargs["container_idx"] = 1 if kargs["axes2"] else 0
            del kargs["axes2"]

        f_page = self.get_page()
        if f_page is None:
            return None
        f_axes = f_page.get_axes(self.isec())
        for name, obj in f_axes.get_children():
            if isinstance(obj, FigLegend):
                labels = obj.getvar('legendlabel')
                for arg in args:
                    labels = sum((labels, arg), ())
                obj.setvar('legendlabel', labels)
                obj.setp('legendlabel', labels)
                obj.refresh_artist()
                ifigure.events.SendChangedEvent(
                    self.book, w=self, useProcessEvent=True)
                ifigure.events.SendPVDrawRequest(
                    self.book, wait_idle=True, refresh_hl=False)
                return
        #kargs['autonext'] = False
        obj = FigLegend(*args, **kargs)
        return obj

    @allow_interactive_call
    def fill(self, *args, **kargs):
        from ifigure.mto.fig_fill import FigFill
        kargs['mpl_command'] = 'fill'
        obj = FigFill(*args, **kargs)
        return obj

    @allow_interactive_call
    def fill_between(self, *args, **kargs):
        from ifigure.mto.fig_fill import FigFill
        kargs['mpl_command'] = 'fill_between'
        obj = FigFill(*args, **kargs)
        return obj

    @allow_interactive_call
    def fill_betweenx(self, *args, **kargs):
        from ifigure.mto.fig_fill import FigFill
        kargs['mpl_command'] = 'fill_betweenx'
        obj = FigFill(*args, **kargs)
        return obj

    @allow_interactive_call
    def fill_between_3d(self, x1, y1, z1, x2, y2, z2, c='b', w=0, **kargs):
        from ifigure.mto.fig_solid import FigSolid

        verts1 = np.vstack([np.array(x1, copy=False),
                            np.array(y1, copy=False),
                            np.array(z1, copy=False), ]).transpose()
        verts2 = np.vstack([np.array(x2, copy=False),
                            np.array(y2, copy=False),
                            np.array(z2, copy=False), ]).transpose()

        x = np.arange(len(verts1))
        y = np.arange(2)
        X, Y = np.meshgrid(x, y)

        from ifigure.utils.triangulation_wrapper import delaunay

        idxset = delaunay(X.flatten(), Y.flatten())
        verts = np.vstack([verts1, verts2])

        args = (verts, idxset)

        kargs['linewidth'] = w
        kargs['facecolor'] = c

        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            fig_axes.set_3d(True)

        obj = FigSolid(*args, **kargs)
        return obj

    @allow_interactive_call
    def surf(self, *args, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            return

        from ifigure.mto.fig_surface import FigSurface
        obj = FigSurface(*args, **kargs)
        return obj

    @allow_interactive_call
    def surface(self, x, y, z, **kargs):
        return self.surf(x, y, z, **kargs)

    @allow_interactive_call
    def revolve(self, *args, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            return

        from ifigure.mto.fig_surface import FigRevolve
        obj = FigRevolve(*args, **kargs)
        return obj

    @allow_interactive_call
    def trisurf(self, *args, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            return

        from ifigure.mto.fig_trisurface import FigTrisurface
        obj = FigTrisurface(*args, **kargs)
        return obj

    @allow_interactive_call
    def solid(self, *args, **kargs):
        from ifigure.mto.fig_solid import FigSolid
        if args[0].shape[-1] == 4:
            kargs['cz'] = True
            kargs['cdata'] = args[0][..., -1]
            args = (args[0][..., :-1],)

        def_width = 0.0
        if len(args) == 2:
            verts = args[0]
            idxset = args[1]
            if verts.shape[-1] == 4:
                kargs['cz'] = True
                kargs['cdata'] = verts[..., -1]
                verts = verts[..., :-1]
            elif verts.shape[-1] == 2:
                zvalue = kargs.pop('zvalue', 0.0)
                verts = np.hstack((args[0], np.zeros((args[0].shape[0], 1))
                                   + zvalue))
            args = (verts, idxset)
            if idxset.shape[1] == 2:
                def_width = 1.0
        elif len(args) == 1:
            verts = args[0]
            if verts.shape[-1] == 4:
                kargs['cz'] = True
                kargs['cdata'] = verts[..., -1]
                verts = verts[..., :-1]
            elif args[0].shape[-1] == 2:
                zvalue = kargs.pop('zvalue', 0.0)
                verts = np.dstack((args[0], np.zeros((args[0].shape[0], args[0].shape[1], 1))
                                   + zvalue))
            args = (verts,)
            if verts.shape[1] == 2:
                def_width = 1.0
        else:
            assert False, "wrong number of arguments, solid(v, idx) or solid(v)"

        linewidth = kargs.pop("linewidth", def_width)
        kargs['linewidth'] = linewidth
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            fig_axes.set_3d(True)

        obj = FigSolid(*args, **kargs)
        return obj

    @allow_interactive_call2
    def lighting(self, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if not fig_axes.get_3d():
            return
        ax = fig_axes._artists[0]
        l = ax.get_lighting()
        if len(kargs) == 0:
            return l
        for k in kargs:
            if not k in l:
                raise KeyError(str(k) + ' does not exists')
        for k in kargs:
            l[k] = kargs[k]
        fig_axes.set_bmp_update(False)
        self.draw()

    @allow_interactive_call2
    def _view(self, *args, **kargs):
        fig_axes = self.get_axes(ipage=None, iaxes=self.isec())
        if fig_axes is None:
            return
        if not fig_axes.get_3d():
            return
        ax = fig_axes._artists[0]
        if len(args) == 0 and len(kargs) == 0:
            return ax.elev, ax.azim, ax._upvec
        elif len(args) == 3:
            ax.elev = args[0]
            ax.azim = args[1]
            ax._upvec = args[2]
            fig_axes.set_bmp_update(False)
        elif len(args) == 1:
            if args[0] == 'xy':
                if ax.elev == 90 and ax.azim == 180:
                    ax.elev, ax.azim = -90, 180
                else:
                    ax.elev, ax.azim = 90, 180
                ax._upvec = np.array([0, 1, 0])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'xz':
                if ax.elev == 0 and ax.azim == -90:
                    ax.elev, ax.azim = 180, -90
                else:
                    ax.elev, ax.azim = 0, -90
                ax._upvec = np.array([0, 0, 1])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'yx':
                ax.elev, ax.azim = -90, 0
                ax._upvec = np.array([0, 0, 1])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'yz':
                if ax.elev == 0 and ax.azim == 0:
                    ax.elev, ax.azim = 180, 0
                else:
                    ax.elev, ax.azim = 0, 0
                ax._upvec = np.array([0, 0, 1])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'zx':
                ax.elev, ax.azim = 0, 90
                ax._upvec = np.array([1, 0, 0])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'zy':
                ax.elev, ax.azim = 0, -180
                ax._upvec = np.array([0, 1, 0])
                fig_axes.set_bmp_update(False)
            elif args[0] == 'default':
                ax.elev, ax.azim = 30, -60
                ax._upvec = np.array([0, 0, 1])
                fig_axes.set_bmp_update(False)
            elif args[0] == '90':
                ax.rotate_view_90deg(True)
                fig_axes.set_bmp_update(False)
            elif args[0] == '-90':
                ax.rotate_view_90deg(False)
                fig_axes.set_bmp_update(False)
            elif args[0] == 'updown':
                ax._upvec = -ax._upvec
                fig_axes.set_bmp_update(False)
            elif args[0] == 'ortho':
                ax._use_frustum = False
                fig_axes.set_bmp_update(False)
            elif args[0] == 'frustum':
                ax._use_frustum = True
                fig_axes.set_bmp_update(False)
            elif args[0] == 'noclip':
                ax._use_clip = ax._use_clip & 2
                fig_axes.set_bmp_update(False)
            elif args[0] == 'clip':
                ax._use_clip = ax._use_clip | 1
                fig_axes.set_bmp_update(False)
            elif args[0] == 'nocp':
                ax._use_clip = ax._use_clip & 1
                fig_axes.set_bmp_update(False)
            elif args[0] == 'cp':
                ax._use_clip = ax._use_clip | 2
                fig_axes.set_bmp_update(False)

            elif args[0] == 'auto':
                self.xauto()
                self.yauto()
                self.zauto()
                fig_axes.set_aspect('auto')
                fig_axes.set_bmp_update(False)

            elif args[0] == 'equal':
                xlim = self.xlim()
                ylim = self.ylim()
                zlim = self.zlim()
                dx = abs(xlim[1]-xlim[0])
                dy = abs(ylim[1]-ylim[0])
                dz = abs(zlim[1]-zlim[0])
                dd = max((dx, dy, dz))
                self.xlim((xlim[1]+xlim[0]-dd)/2,
                          (xlim[1]+xlim[0]+dd)/2)
                self.ylim((ylim[1]+ylim[0]-dd)/2,
                          (ylim[1]+ylim[0]+dd)/2)
                self.zlim((zlim[1]+zlim[0]-dd)/2,
                          (zlim[1]+zlim[0]+dd)/2)
                fig_axes.set_aspect('equal')
                fig_axes.set_bmp_update(False)
            elif args[0] == 'axesicon':
                ax._show_3d_axes = True
                fig_axes.set_bmp_update(False)
            elif args[0] == 'noaxesicon':
                ax._show_3d_axes = False
                fig_axes.set_bmp_update(False)
            else:
                print('Unkonw keyword: ' + args[0])

    def view(self, *args, **kargs):
        return self._view(*args, **kargs)

    def close(self, ):
        '''
        close window
        '''
        # simply close the window by calling Close of Frame
        import wx
        if self is not wx.GetApp().TopWindow:
            self.Close()
        else:
            self.close_figurebook()

    @share_doc_string_simple
    def cbar(self, name=None, *args,  **kargs):

        position = kargs.pop('position', (0.9, 0.1))
        size = kargs.pop('size', (0.05, 0.8))
        lsize = kargs.pop('lsize', 'default')
        lcolor = kargs.pop('lcolor', 'black')
        olsize = kargs.pop('olsize', 'default')
        olcolor = kargs.pop('olcolor', 'black')
        direction = kargs.pop('direction', 'v')

        update = kargs.pop('update', self._interactive_update)
        hold = kargs.pop('hold', True)
        f_page = self.get_page()
        if f_page is None:
            return
        ax = f_page.get_axes(self.isec())

        action = 'both'
        for k, p in enumerate(ax._caxis):
            if (not p.has_cbar() and (name is None or p.name == name) and
                    (action == 'on' or action == 'both')):
                p.show_cbar(ax,
                            offset=-0.1*k,
                            position=position,
                            size=size,
                            lsize=lsize,
                            lcolor=lcolor,
                            olsize=olsize,
                            olcolor=olcolor,
                            direction=direction[0])
                action = 'on'
            if (p.has_cbar() and (name is None or p.name == name) and
                    (action == 'off' or action == 'both')):
                action = 'off'
                p.hide_cbar()
        if update:
            ifigure.events.SendChangedEvent(
                self.book, w=self, useProcessEvent=True)
            ifigure.events.SendPVDrawRequest(
                self.book, wait_idle=True, refresh_hl=False)

    def _names(self, attr):
        f_page = self.get_page()
        if f_page is None:
            return
        try:
            ax = f_page.get_axes(self.isec())
            return [p.name for p in getattr(ax, attr)]
        except:
            return []

    @share_doc_string
    def xnames(self):
        return self._names('_xaxis')

    @share_doc_string
    def ynames(self):
        return self._names('_yaxis')

    @share_doc_string
    def znames(self):
        return self._names('_zaxis')

    @share_doc_string
    def cnames(self):
        return self._names('_caxis')

    @allow_interactive_call2
    def property(self, obj, *args, **kargs):
        from ifigure.widgets.artist_widgets import listparam, call_getter
        ret = obj.property_for_shell()
        tags = None
        if isinstance(ret, tuple):
            tab = ret[0]
            props = ret[1]
            if len(ret) == 3:
                tags = ret[2]
        else:
            tab = ['']
            props = [ret]
        if tags is None:
            tags = ['']*len(props)

        ll = []
        if 'list' in kargs or len(args) == 0:
            for tag, plist in zip(tags, props):
                for p in plist:
                    if tag == '':
                        ll.append(listparam[p][6])
                    else:
                        ll.append((tag, listparam[p][6]))
            return ll
#        if len(args) == 0: return

#        from matplotlib.cbook import is_string_like
        from ifigure.utils.cbook import isstringlike
        name = args[0]
        if not isstringlike(name):
            tag, name = name
        else:
            tag = ''
        args = args[1:]
        for tt, plist in zip(tags, props):
            for p in plist:
                if (listparam[p][6].upper() == name.upper() and
                        tt == tag):
                    ll.append(listparam[p])

        if len(ll) == 0:
            print('Property '+name + ' is not found')
            return
        if len(ll) > 1:
            print('More thant two properties are found by '+name)
            print('Please inform developer this problem')
            return
        # dprint1(ll)
        ll = ll[0]
        if len(args) == 0:
            ret = [call_getter(a, ll, tab=tag) for a in obj._artists]
            if len(ret) == 1:
                return ret[0]
            return ret
        else:
            actions = []
            vv = args[0]
            if len(obj._artists) == 1:
                vv = (vv,)
            from ifigure.utils.cbook import isiterable

            for a, v in zip(obj._artists, vv):
                name = ll[4]
                sw = ll[5]
                if sw > 9:
                    sw = sw-10
                if sw == 0:
                    action = UndoRedoArtistProperty(a, name, v)
                elif sw == 1:
                    action = UndoRedoFigobjProperty(a, name, v)
                elif sw == 8:
                    action = UndoRedoFigobjProperty(a, name, v, nodelete=True)
                elif sw == 2:
                    action = UndoRedoFigobjMethod(a, name, v)
                elif sw == 3:
                    action = UndoRedoFigobjMethod(a, name, v)
                    action.set_extrainfo(tag)
                actions.append(action)
            for rec in actions:
                rec.do()
            figobj = actions[-1].do2()
            figobj.set_bmp_update(False)
            self.draw()

    def size(self, *args):
        if len(args) == 0:
            return self.GetSize()
        try:
            value = (args[0], args[1])
        except:
            try:
                value = tuple(args[0])
            except:
                raise
        self.SetSize(value)
        return self

    @allow_interactive_call2
    def savefig(self, filename):
        import os
        filename = os.path.expanduser(filename)
        if self.num_page() == 0:
            return
        if filename[-4:] == '.eps':
            wc = 0
        elif filename[-4:] == '.pdf':
            if self.num_page() == 1:
                wc = 1
            else:
                wc = 7
        elif filename[-4:] == '.svg':
            wc = 2
        elif filename[-4:] == '.png':
            wc = 3
        elif filename[-5:] == '.jpeg':
            wc = 4
        elif filename[-4:] == '.gif':
            wc = 5
        else:
            assert False, "unknown file format"

        self.canvas.save_pic(ret=filename, wc=wc)

    @allow_interactive_call2
    def savedata(self, filename, **kargs):
        import os
        filename = os.path.expanduser(filename)
        if self.num_page() == 0:
            return
        if filename[-4:] != '.hdf':
            assert False, "filename must end with hdf"

        page = self.canvas._figure.figobj
        metadata = kargs.pop('metadata', OrderedDict())
        export_flag = kargs.pop('export_flag', {})
        verbose = kargs.pop('verbose', True)

        try:
            #  for standalone testing (when running python hdf_export_window.py)
            from ifigure.utils.hdf_data_export import (build_data,
                                                       hdf_data_export,
                                                       set_all_properties_all,
                                                       select_unique_properties_all)
        except:
            print("can not load hdf export tools")
            raise

        dataset, metadata, export_flag = build_data(page,
                                                    verbose=False,
                                                    metadata=metadata,
                                                    export_flag=export_flag)

        try:
            hdf_data_export(data=dataset,
                            metadata=metadata,
                            export_flag=export_flag,
                            filename=filename,
                            verbose=verbose)
            print('HDF export finished : '+filename)
        except:
            print("can not export  hdf dataset")
            raise
