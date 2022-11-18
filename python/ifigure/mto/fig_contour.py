from __future__ import print_function
#
#   fig_contour
#
#  History:
#          12.06.10  Added Highlight
#          12.06.11  Added custom picker
#          09.xx.15  Added tricontour support (object should be generated
#                    using FigTricontour)
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#  Special note for fig_contour:
#          1) len(self._artists) can be more than 1
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
import weakref
import wx
import os
import sys
import logging
from scipy.interpolate import griddata
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox

from ifigure.utils.cbook import isiterable, isndarray, isdynamic, issequence, isnumber

import ifigure
import ifigure.events
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
from ifigure.utils.args_parser import ArgsParser
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists, GlobalHistory
from ifigure.utils.triangulation_wrapper import tri_args

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigContour')

def_clabel_param = {

    'use_clabel': False,
    'fontsize': 10,
    'fixed_color': False,
    'colors': 'k',
    'inline': True,
    'inline_spacing': 5,
    'fmt': '%1.3f',
    'skip': 0}

default_kargs = {'use_tri': False,
                 'FillMode': False,
                 'interp': 'nearest',
                 'alpha':  1.0,
                 'cmap':  None, }


class FigContour(FigObj, XUser, YUser, CUser, ZUser):
    def __new__(cls, *args, **kywds):
        """
        contour : contour plot 
        contour(z, n)  
        contour(x, y, z, n)  
        contour(z, v)  
        contour(x, y, z, v)  

        n: number of levels
        v: a list of contour levels
        """
        def set_hidden_vars(obj):
            if not hasattr(obj, '_tri'):
                obj._tri = None  # this can go away!?
            obj._clabels = []
            obj._clabel_param = def_clabel_param
            obj._nouse_expression = False
            obj._hit_path = None
            obj._expression = ''
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_opt('y', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('z', ['numbers|nonstr', 'dynamic'])
        p.add_opt('n', 7, 'int')  # n = number of levels
        # v = levels (array)
        p.add_opt('v', None, ['numbers|nonstr', 'dynamic'])

        p.set_default_list(default_kargs)
        p.add_key2(("FillMode", "alpha", "use_tri"))
        p.add_key2('interp', 'str')
        p.add_key2('cmap', 'str')
        p.add_key('offset', None)
        p.add_key('zdir', 'z')

        p.set_pair("x", "y")  # x and y should be given
        # together
        p.set_ndconvert("x", "y", "z")
        p.set_squeeze_minimum_1D("x", "y", "z")

        v, kywds, d, flag = p.process(*args, **kywds)
        dprint2(v)

        if not flag:
            raise ValueError('Failed when processing argument')
            return None

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        obj._set_expression_vars(v['v'])
        for name in ('x', 'y', 'z'):
            obj.setvar(name, v[name])
        for name in ('FillMode', 'alpha', 'n', 'v', "cmap", "offset", "zdir", "use_tri"):
            obj.setvar(name, v[name])

        if v['cmap'] is not None:
            kywds['cmap'] = v['cmap']

        obj.setvar("kywds", kywds)
        return obj

    def _set_expression_vars(self, v):
        if v is not None:
            self._expression = str(v) if not isdynamic(v) else v[1:]
            self._nouse_expression = False if self._expression != '' else True
        else:
            self._expression = ''
            self._nouse_expression = False

    def __init__(self, *args, **kywds):
        self._data_extent = None
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)
        CUser.__init__(self)

        self._pick_pos = None
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigContour, self).__init__(**kywds)

    @classmethod
    def isFigContour(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'contour'

    def property_in_file(self):
        if not self.getp('FillMode'):
            return (['linestyle', 'linewidth', 'alpha'] +
                    super(FigContour, self).property_in_file())
        else:
            return (['edgecolor', 'alpha'] +
                    super(FigContour, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return (['contour', 'labels', 'path', 'line'], [
                ["contour_fill", "contour_nlevel2", "alpha_2", "caxis"],
                ['clabel_param'],
                ['pedgecolor_2'],
                ['plinestyle_2', 'elinewidth']])

    @classmethod
    def attr_in_file(self):
        return (["v", "n", "FillMode", "alpha", "interp"] +
                super(FigContour, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'plot1.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)
        super(FigContour, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)
        CUser.get_caxisparam(self)

    def args2var(self):
        ret = self._args2var()
        if ret:
            if 'cmap' in self.getvar("kywds"):
                cax = self.get_caxisparam()
                cax.set_cmap(self.getvar('kywds')['cmap'])
        return ret

    def _args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y", "z"] + names0
        use_np = [True]*3 + [True, True] + [False]*(len(names0)-2)
        # n and v can be dynamic too.
        values = self.put_args2var(names,
                                   use_np)
        x = values[0]
        y = values[1]
        z = values[2]
        if y is None and x is None and z.ndim == 2:
            y = np.arange((z.shape)[-2])
            self.setp("y", y)
            x = np.arange((z.shape)[-1])
            self.setp("x", x)
        if x is None:
            return False
        if y is None:
            return False
        if (x.size*y.size != z.size and
                not (x.size == z.size and y.size == z.size)):
            self.setp("x", None)
            self.setp("y", None)
            self.setp("z", None)
            return False
        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        container = self.get_container()
        if container is None:
            return

        flag = 0
        if self.isempty() is False:
            return
        x, y, z = self._eval_xyz()  # this handles "use_var"
        if z is None:
            return

        lp = self.getp("loaded_property")

        v, n, FillMode = self.getp(('v', 'n', 'FillMode'))

        kywds = self.getvar('kywds')
        kywds['alpha'] = self.getp('alpha')

        if self.getvar('use_tri'):
            args, self._tri = tri_args(x, y, self._tri)
            args.append(np.real(z.flatten()))
        else:
            args = []
            if x is not None:
                args.append(x)
            if y is not None:
                args.append(y)
            if z is not None:
                args.append(z)
        if (not self._nouse_expression and
                v is not None):
            args.append(v)
        else:
            args.append(int(n))

        cax = self.get_caxisparam()

#           dprint2(args)
        if len(args) == 0:
            return

        self._data_extent = [np.min(x), np.max(x), np.min(y), np.max(y)]
#           self.setp("data_extent",[min(x), max(x), min(y), max(y)])
        try:
            if self.get_figaxes().get_3d():
                kywds['offset'] = self.getvar('offset')
                kywds['zdir'] = self.getvar('zdir')
        except:
            pass

        if self.getvar('use_tri'):
            if FillMode:
                method = container.tricontourf
            else:
                method = container.tricontour
        else:
            if FillMode:
                method = container.contourf
            else:
                method = container.contour
        try:
            self._mappable = method(*args, **kywds)
            self._artists = self._mappable.collections[:]
            self.set_rasterized()
            for a in self.get_mappable():
                cax.set_crangeparam_to_artist(a)
        except Exception:
            logging.exception(
                "FigContour:generate_artist : artist generation failed")

        if lp is not None:
            #              print lp
            for i, var in enumerate(lp):
                if len(self._artists) > i:
                    self.set_artist_property(self._artists[i], var)
            self.delp("loaded_property")

        for path in self._artists:
            #                 path.set_picker(cpicker.Picker)
            path.figobj = self
            path.figobj_hl = []
            path.set_zorder(self.getp('zorder'))

        if self._clabel_param['use_clabel'] and not FillMode:
            args, kargs = self._make_clabel_param()
            wx.CallLater(1, self.call_clabel, *args, **kargs)

#           self._artists[0].figobj=self
#           self._artists[0].figobj_hl=[]

#    def refresh_artist_data(self):
#        if not self.isempty():
#           self.del_artist()
#       if self.isempty() and not self._suppress:
#            self.generate_artist()

    def del_artist(self, artist=None, delall=False):
        #
        #  delete highlight and artist
        #  for fig_contour, all artists are treated
        #  as one set. it does not support to delete
        #  a part of path collections
        delall = True
        if delall:
            artistlist = self._artists
        else:
            artistlist = self._artists

        self.store_loaded_property()
#        if not self.hasp("loaded_property"):
#             self.load_data2(self.save_data2({}))
#        self.highlight_artist(False)
        for a in artistlist:
            a.remove()
            self._mappable.collections.remove(a)
        for t in self._clabels:
            t.remove()
        self._clabels = []
        if (self._mappable is not None and
                len(self._mappable.collections) == 0):
            self._mappable = None
        super(FigContour, self).del_artist(artistlist)

    def get_mappable(self):
        return [self._mappable]

    def reset_artist(self):
        print('resetting contour artist')
        self.del_artist(delall=True)
# (why not)  self.delp('loaded_property')
        self.setp('use_var', True)
        self.generate_artist()

    def highlight_artist(self, val, artist=None):
        from ifigure.matplotlib_mod.art3d_gl import Poly3DCollectionGL
        from ifigure.matplotlib_mod.art3d_gl import Line3DCollectionGL
        figure = self.get_figpage()._artists[0]
        ax = self.get_figaxes()
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        if val == True:
            if self._parent is None:
                return
            container = self.get_container()
            if container is None:
                return

            if isinstance(alist[0], Poly3DCollectionGL):
                hl = alist[0].add_hl_mask()
                for item in hl:
                    alist[0].figobj_hl.append(item)
            else:
                de = self.get_data_extent()
                x = (de[0], de[1], de[1], de[0], de[0])
                y = (de[2], de[2], de[3], de[3], de[2])

                facecolor = 'k'
                if isinstance(alist[0], Poly3DCollectionGL):
                    hl = alist[0].make_hl_artist(container)
                    facecolor = 'none'
                    self._hit_path = None
                elif isinstance(alist[0], Line3DCollectionGL):
                    hl = alist[0].make_hl_artist(container)
                    facecolor = 'none'
                    self._hit_path = None
                else:
                    hl = container.plot(x, y, marker='s',
                                        color='k', linestyle='None',
                                        markerfacecolor='None',
                                        markeredgewidth=0.5,
                                        scalex=False, scaley=False)
                for item in hl:
                    alist[0].figobj_hl.append(item)

                if self._hit_path is not None:
                    v = self._hit_path.vertices
                    hl = container.plot(v[:, 0], v[:, 1], marker='s',
                                        color='k', linestyle='None',
                                        markerfacecolor='None',
                                        markeredgewidth=0.5,
                                        scalex=False, scaley=False)
                    for item in hl:
                        alist[0].figobj_hl.append(item)

                hlp = Rectangle((de[0], de[2]),
                                de[1]-de[0],
                                de[3]-de[2],
                                alpha=0.3, facecolor=facecolor,
                                figure=figure,
                                transform=container.transData)
                if ax is not None:
                    x0, y0 = ax._artists[0].transAxes.transform((0, 0))
                    x1, y1 = ax._artists[0].transAxes.transform((1, 1))
                    bbox = Bbox([[x0, y0], [x1, y1]])
                    hlp.set_clip_box(bbox)
                    hlp.set_clip_on(True)
                figure.patches.append(hlp)
                alist[0].figobj_hl.append(hlp)
        else:
            for a in alist:
                if len(a.figobj_hl) == 0:
                    continue
                for hl in a.figobj_hl[:-1]:
                    hl.remove()
                if isinstance(alist[0], Poly3DCollectionGL):
                    a.figobj_hl[-1].remove()
                else:
                    figure.patches.remove(a.figobj_hl[-1])
                a.figobj_hl = []
#
#   Setter/Getter
#
#    def set_contour_nlevel(self, value, a):
#        self.setp('n', value)
#        self.del_artist(delall=True)
#        self.delp('loaded_property')
#        self.generate_artist()
#        sel = [weakref.ref(self._artists[0])]
#        import wx
#        app = wx.GetApp().TopWindow
#        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)
#    def get_contour_nlevel(self, a):
#        return self.getp('n')

    def set_contour_nlevel2(self, value, a=None):
        self._nouse_expression = not value[0]
#        print value
        self.setp('n', int(value[2][0]))
        self.setp('v', value[1][0][1])
        self._expression = value[1][0][0]
        self.highlight_artist(False)
        self.del_artist(delall=True)
        self.delp('loaded_property')
        self.generate_artist()

        sel = [weakref.ref(self._artists[0])]
        import wx
        app = wx.GetApp().TopWindow
        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)

    def get_contour_nlevel2(self, a):
        v = (not self._nouse_expression,
             [(self._expression, self.getp('v'))],
             [str(self.getp('n'))], )
#        print 'returning figobj value', v
        return v

    def set_contour_fillmode(self, value, a):
        self.setp('FillMode', value)
        self.del_artist(delall=True)
        self.delp('loaded_property')
        self.generate_artist()

        sel = [weakref.ref(self._artists[0])]
        import wx
        app = wx.GetApp().TopWindow
        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)

    def get_contour_fillmode(self, a):
        return self.getp('FillMode')

    def set_alpha(self, value, a):
        for a in self._artists:
            a.set_alpha(value)

    def get_alpha(self, a):
        return self._artists[0].get_alpha()

    def set_edgecolor(self, value, a):
        for a in self._artists:
            a.set_edgecolor(value)

    def get_edgecolor(self, a):
        v = a.get_edgecolor()
        return v

    def set_elinewidth(self, value, a):
        for a in self._artists:
            a.set_linewidth(value)

    def get_elinewidth(self, a):
        v = a.get_linewidth()
        if len(v) > 0:
            return v[0]
        return ['1.0']

    def set_linestyle(self, value, a):
        for a in self._artists:
            a.set_linestyle(value)

    def get_linestyle(self, a):
        v = a.get_linestyle()
        return v

#
#   HitTest
#
    def picker_a(self, artist, evt):
        from matplotlib.collections import PathCollection
        from matplotlib.collections import LineCollection
        from ifigure.matplotlib_mod.art3d_gl import Poly3DCollectionGL
        from ifigure.widgets.canvas.custom_picker import CheckLineHit
        axes = artist.axes
        if axes is None:
            return False, {}
        trans = axes.transData
        self._hit_path = None
        if isinstance(artist, Poly3DCollectionGL):
            hit, extra = artist.contains(evt)
            if hit:
                return True, {'child_artist': artist}
            else:
                return False, {}
        else:
            # if isinstance(artist, PathCollection):
            #
            #  For PathCollection, we do this test first
            #
            #    for path in artist.get_paths():
            #        if path.contains_point((evt.x, evt.y), transform=trans, radius=6):
            #            self._hit_path = path
            #            return True, {'child_artist': artist}

            for path in artist.get_paths():
                #               for line plot, hit test is done for each path vertices
                #               path.contains_points does not check if the point is "on the line"
                #               this does assume that line generated from path is simple line
                #               segment without discontinueity and cuvrves (IOW, paht.codes = None)
                xy = trans.transform(path.vertices)
                ans, hit = CheckLineHit(xy[:, 0], xy[:, 1], evt.x, evt.y)
                if ans:
                    self._hit_path = path
                    return True, {'child_artist': artist}
#                if path.contains_point((evt.x, evt.y), transform=trans, radius=6):
#                     self._hit_path = path
#                     return True, {'child_artist':artist}
            return False, {}
        # following is old version
        # should not come here..
        printd('contour has artist nither PathCollection nor LienCollection... Why??')
        if axes is None:
            return False, {}
        de = self.get_data_extent()
        if (evt.xdata > de[0] and
            evt.xdata < de[1] and
            evt.ydata > de[2] and
                evt.ydata < de[3]):
            return True,  {'child_artist': artist}
        return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0

#
#  Popup in Canvas
#
#    def canvas_menu(self):
#        return [("Export",  self.onExport, None)] + \
#                super(FigContour,self).canvas_menu()
    def canvas_menu(self):
        ac = self.get_caxisparam()
        if ac is None:
            return super(FigContour, self).tree_viewer_menu()
        if ac.cbar_shown():
            m = [('Hide color bar', self.onHideCB1, None), ]
        else:
            m = [('Show color bar', self.onShowCB1, None), ]
        menus = [("Show slice",  self.onSlice, None),
                 ("Generate path plot",   self.onCopyPath, None)] + m + \
            [("Export path",   self.onExportPath, None)] + \
            super(FigContour, self).canvas_menu()
        return menus

    def onExportPath(self, event):
        if self._hit_path is not None:
            v = self._hit_path.vertices
            fig_val = {"xdata": v[:, 0],
                       "ydata": v[:, 1]}
            text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\']'
            self._export_shell(fig_val, 'fig_val', text)

    def onCopyPath(self, event):
        from ifigure.mto.fig_plot import FigPlot
        from ifigure.mto.fig_fill import FigFill
        if self._hit_path is not None:
            canvas = event.GetEventObject()
            v = self._hit_path.vertices
            if self.getp('FillMode'):
                obj = FigFill(v[:, 0], v[:, 1])
            else:
                obj = FigPlot(v[:, 0], v[:, 1], 'k')
            ax = self.get_figaxes()
            name = ax.get_next_name('Contour_path')
            ax.add_child(name, obj)
            obj.realize()

            ax.set_bmp_update(False)
            canvas.draw()

            artists = [weakref.ref(obj._artists[0])]
            h = [UndoRedoAddRemoveArtists(artists=artists,
                                          mode=0)]
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(h, menu_name='add path plot')

    def onExport(self, event):
        from matplotlib.artist import getp

        shell = self.get_root_parent().app.shell
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        for a in self._artists:
            if a in sel:
                print("Exporting Data to Shell")
                x, y, z = self._eval_xyz()
                fig_val = {"zdata": z,
                           "xdata": x,
                           "ydata": y}
                text = '#Exporting data as fig_val[\'xdata\'], fig_val[\'ydata\'], fig_val[\'zdata\']'
                self._export_shell(fig_val, 'fig_val', text)
                break
        # print "exporting data to file"

    def get_slice(self, xin, yin):
        x, y, z = self._eval_xyz()
        if z.ndim != 2:
            return None, None
        X, Y = np.meshgrid(x, y)
        p1 = np.transpose(np.vstack((X.flatten(), Y.flatten())))

        x0 = xin+np.zeros(y.size)
        y0 = yin+np.zeros(x.size)

        interp = self.getp("interp")
        zp1 = griddata(p1, z.flatten(),
                       (x, y0),
                       method=interp)
        zp2 = griddata(p1, z.flatten(),
                       (x0, y),
                       method=interp)
        return (x, zp1), (y, zp2)

    def onSlice(self, event):
        from ifigure.interactive import figure, plot, nsec, isec, update, title, xlabel, ylabel
        if event.mpl_xydata[0] is None:
            return

        app = self.get_root_parent().app
        data1, data2 = self.get_slice(event.mpl_xydata[0],
                                      event.mpl_xydata[1])
        if data1 is None:
            return
        if data2 is None:
            return
        from ifigure.widgets.book_viewer import BookViewer
        book, viewer = app.open_newbook_in_newviewer(BookViewer)
        book.get_page(0).set_section(2)
        ou = update()
        isec(0)
        plot(data1[0], data1[1])
        title('x slice : y = '+str(event.mpl_xydata[1]))
        xlabel('x')
        isec(1)
        plot(data2[0], data2[1])
        title('y slice : x = '+str(event.mpl_xydata[0]))
        xlabel('y')
        update(ou)

#
#   extent
#
    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x = self.eval("x", np=True)
        y = self.eval("y", np=True)
        if (x is None or
                y is None):
            z = self.eval("z", np=True)
            if (z is not None):
                x = np.arange(z.shape[1])
                y = np.arange(z.shape[0])
                self._data_extent = [
                    np.min(x), np.max(x), np.min(y), np.max(y)]
        else:
            self._data_extent = [np.min(x), np.max(x), np.min(y), np.max(y)]
        return self._data_extent

#
#   range
#
    def get_xrange(self, xrange=[None, None], scale='linear'):
        if (self.getvar('offset') is not None and
                self.getvar('zdir') == 'x'):
            return self._update_range(xrange, (self.getvar('offset'),
                                               self.getvar('offset'),))
        x, y, z = self._eval_xyz()
        if x is None:
            return
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()
        if (self.getvar('offset') is not None and
                self.getvar('zdir') == 'y'):
            return self._update_range(yrange, (self.getvar('offset'),
                                               self.getvar('offset'),))
        x, y, z = self._eval_xyz()
        if x is None:
            return
        if y is None:
            return
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):

        x, y, z = self._eval_xyz()
        if (x is None or
                y is None):
            x = np.arange(z.shape[1])
            y = np.arange(z.shape[0])
        if (self.getvar('offset') is not None and
            (self.getvar('zdir') == 'x' or
             self.getvar('zdir') == 'y')):
            crange = self._update_range(crange, (np.amin(z), np.amax(z)))
        elif (xrange[0] is not None and
              xrange[1] is not None and
              yrange[0] is not None and
              yrange[1] is not None):
            zt = np.ma.masked_array(z)
            if zt.ndim == 2:
                if y.ndim == 1:
                    zt[(y < yrange[0]) | (y > yrange[1]), :] = np.ma.masked
                else:
                    zt[(y < yrange[0]) | (y > yrange[1])] = np.ma.masked
                if x.ndim == 1:
                    zt[:, (x < xrange[0]) | (x > xrange[1])] = np.ma.masked
                else:
                    zt[(x < xrange[0]) | (x > xrange[1])] = np.ma.masked
            else:
                zt[(y < yrange[0]) | (y > yrange[1])] = np.ma.masked
                zt[(x < xrange[0]) | (x > xrange[1])] = np.ma.masked

            if scale == 'log':
                zt[z <= 0] = np.ma.masked
            crange = self._update_range(crange, (np.amin(zt), np.amax(zt)))

        return crange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        if (self.getvar('offset') is not None and
                self.getvar('zdir') == 'z'):
            return self._update_range(zrange, (self.getvar('offset'),
                                               self.getvar('offset'),))
        else:
            zrange = self.get_crange(crange=zrange,
                                     xrange=xrange,
                                     yrange=yrange, scale='linear')

        return zrange

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        var = {'x': check(self, 'x'),
               'y': check(self, 'y'),
               'z': check(self, 'z')}

        if not var["x"]:
            if self._save_mode == 0:
                var["xdata"] = self.getp("x")
            else:
                var["xdata"] = np.array([0, 1])
        if not var["y"]:
            if self._save_mode == 0:
                var["ydata"] = self.getp("y")
            else:
                var["ydata"] = np.array([0, 1])
        if not var["z"]:
            if self._save_mode == 0:
                var["zdata"] = self.getp("z")
            else:
                var["zdata"] = np.arange(4).reshape(2, 2)

        var["n"] = self.getp("n")
        var["v"] = self.getp("v")
        var["nouse_expression"] = self._nouse_expression
        var["clabel_param"] = self._clabel_param
        dprint2('save_data2', var)
        data['FigContour'] = (1, var)
        data = super(FigContour, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigContour']
        super(FigContour, self).load_data2(data)
        dprint2('load_data2', d[1])
        var = d[1]
        names = ["x", "y", "z"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])
        self.setp('n', var["n"])
        self.setp('v', var["v"])
        if "nouse_expression" in var:
            self._nouse_expression = var["nouse_expression"]
        if "clabel_param" in var:
            self._clabel_param = var["clabel_param"]

    def prepare_compact_savemode(self):
        var_bk = self._var.copy()
        self._var['z'] = np.arange(4).reshape(2, 2)
        self._var['x'] = np.array([0, 1])
        self._var['y'] = np.array([0, 1])
        return var_bk

    def _eval_xyz(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None
            self._set_expression_vars(self.getvar('v'))
        return self.getp(("x", "y", "z"))
#
#   clabel
#

    def _clabal_gui2kwargs(self, gui_param):
        self._clabel_param['use_clabel'] = gui_param[0]
        self._clabel_param['fontsize'] = gui_param[1][0]
        self._clabel_param['fixed_color'] = gui_param[1][1][0]
        self._clabel_param['colors'] = gui_param[1][1][1]
        self._clabel_param['inline'] = gui_param[1][2]
        self._clabel_param['inline_spacing'] = float(gui_param[1][3])
        self._clabel_param['fmt'] = str(gui_param[1][4])
        self._clabel_param['skip'] = int(gui_param[1][5])

    def _make_clabel_param(self):
        keys = ['fontsize', 'colors', 'inline', 'inline_spacing', 'fmt']
        kargs = {key: self._clabel_param[key] for key in keys}
        if not self._clabel_param['fixed_color']:
            kargs['colors'] = None
        if self._clabel_param['skip'] == 0:
            args = tuple()
        else:
            k = int(self._clabel_param['skip'])
            args = (self._mappable.levels[:(
                self._mappable.levels.size/k)*k].reshape(-1, k)[:, 0],)
        kargs['use_clabeltext'] = True
        return args, kargs

    def set_clabel_param(self, value, a):
        self._clabal_gui2kwargs(value)
        self.del_artist(delall=True)
        self.delp('loaded_property')
        self.generate_artist()
        sel = [weakref.ref(self._artists[0])]
        import wx
        app = wx.GetApp().TopWindow
        ifigure.events.SendSelectionEvent(self, w=app, selections=sel)

    def get_clabel_param(self, a):
        v = (self._clabel_param['use_clabel'],
             [self._clabel_param['fontsize'],
                 (self._clabel_param['fixed_color'],
                  self._clabel_param['colors']),
                 self._clabel_param['inline'],
                 float(self._clabel_param['inline_spacing']),
                 str(self._clabel_param['fmt']),
                 str(self._clabel_param['skip']), ])

        return v
        # should return like  (False, [8.0, (False, [(1.0, 0.0, 0.0, 1.0)]),
        # True, 5.0, u'%1.3f', '0'])

    def call_clabel(self, *args,  **kargs):
        for t in self._clabels:
            t.remove()
        self._clabels = []
        container = self.get_container()
        self._clabels = container.clabel(self._mappable, *args, **kargs)

        self.set_bmp_update(False)
        ifigure.events.SendPVDrawRequest(self, w=None,
                                         wait_idle=True, refresh_hl=False)
        return self._clabels
