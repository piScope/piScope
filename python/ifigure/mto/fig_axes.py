from __future__ import print_function
#  Name   :fig_axes
#
#          this class to manage matplotlib.axes
#          the role of this class is similar to
#          fig_section in iScope
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#         2012. 04 first version
#         2013. 01 completing cbar....
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
import os
import matplotlib
import weakref
import six
import wx
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.colors import Colormap
import matplotlib.transforms as transforms
from scipy.interpolate import griddata
import matplotlib.ticker as mticker


import ifigure

from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_plot import FigPlot
from ifigure.mto.fig_contour import FigContour
from ifigure.mto.fig_image import FigImage
from ifigure.mto.axis_param import AxisXParam, AxisYParam, AxisZParam, AxisCParam
from ifigure.widgets.axes_range_subs import (AdjustableRangeHolderCbar,
                                             AdjustableRangeHolder)

from ifigure.widgets.canvas.file_structure import *
import ifigure.widgets.canvas.custom_picker as cpicker

import ifigure.events
from ifigure.utils.geom import scale_rect

import ifigure.utils.pickle_wrapper as pickle
import ifigure.utils.cbook as cbook

from ifigure.ifigure_config import isMPL33

from ifigure.widgets.undo_redo_history import (GlobalHistory,
                                               UndoRedoArtistProperty,
                                               UndoRedoFigobjProperty,
                                               UndoRedoFigobjMethod,
                                               UndoRedoAddRemoveArtists)

from ifigure.utils.edit_list import DialogEditListTab, DialogEditList

from ifigure.utils.args_parser import ArgsParser
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigAxes')

#color_cycle = matplotlib.rcParams['axes.color_cycle']

#from mpl_toolkits.axes_grid1.inset_locator import inset_axes

unique_label = 0


class FigAxes(FigObj,  AdjustableRangeHolder):
    def __init__(self, area=[0., 0., 1., 1.],
                 margin=[0.15, 0.15, 0.15, 0.15],
                 src=None, *args, **kywds):
        #        self.child=[]
        super(FigAxes, self).__init__(*args, **kywds)
        self.setp("margin", margin)
        self.setp("use_def_margin", True)
        self.setp("area", area)  # left bottom w h
        self._generic_axes = True
        self._margin_bk = [margin, True]
        self._nomargin_mode = False
        self._xaxis = []
        self._yaxis = []
        self._zaxis = []
        self._caxis = []
        self._rect = None
        self._3D = False
        self._3d_pane_color = self._3d_pane_var(
            ('lightgrey', 'lightgrey', 'lightgrey'),
            (1, 1, 1))
        self._use_gl = True
        self._extra_margin = [0., 0., 0., 0.]  # for edge only axis
        # flag to suppress tick label except when
        # an axes is the edge-most axes
        # top, bottom, left, right
        self._edge_only = [False, False, False, False]
        self.add_axis_param(dir='x')
        self.add_axis_param(dir='y')
        self._hastwin = [False, False]

        self.setp("xminortickmode", ['off', 'off'])
        self.setp("yminortickmode", ['off', 'off'])
        self.setp("grid", [False, False, False])  # x, y, z
        self.setp("aspect", 'auto')
        self.setp("show_axis", True)
        self.setp("use_def_size", [True, True, True])  # default text size
        self.setp("title_labelinfo",  ['', 'black', 'default',
                                       'default', 'default', 'default'])
        self.setp('axis_bgalpha', 1.0)
        self.setp('axis_bglinewidth', 0.0)
        self.setp('axis_bglinestyle', 'solid')
        self.setp('axis_bgedgecolor', (0, 0, 0, 0))
        self.setp('axis_bgfacecolor', (1, 1, 1, 1))

    @classmethod
    def isFigAxes(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'axes'

    @classmethod
    def property_in_file(self):
        from ifigure.ifigure_config import isMPL2
        if isMPL2:
            return ["frame_on",
                    "lighting", "azim",
                    "elev", "dist", "_upvec", "_use_clip",
                    "_use_frustum", "_show_3d_axes"]
        else:
            if self._3D:
                return ["lighting", "azim",
                        "elev", "dist", "_upvec", "_use_clip",
                        "_use_frustum", "_show_3d_axes"]
            else:
                return ["frame_on",  # "axis_bgcolor",
                        "lighting", "azim",
                        "elev", "dist", "_upvec", "_use_clip",
                        "_use_frustum", "_show_3d_axes"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        #       fig_axes store all getp() without this modification
        return []

    @property
    def ispickable_a(self):
        return False

    def can_have_child(self, child=None):
        if child is None:
            return True
        from ifigure.mto.fig_book import FigBook
        from ifigure.mto.fig_page import FigPage
        if isinstance(child, FigPage):
            return False
        if isinstance(child, FigBook):
            return False
        if (isinstance(child, FigAxes) and
                not isinstance(child, FigInsetAxes)):
            return False
        return True

    def add_axis_param(self, dir='x'):
        attr = '_'+dir+'axis'

        g = getattr(self, attr)
        if len(g) == 0:
            name = dir
        else:
            name = dir+str(len(g)+1)
        if dir == 'x':
            p = AxisXParam(name)
            self._xaxis.append(p)
        elif dir == 'y':
            p = AxisYParam(name)
            self._yaxis.append(p)
        elif dir == 'z':
            p = AxisZParam(name)
            self._zaxis.append(p)
        elif dir == 'c':
            p = AxisCParam(name)
            self._caxis.append(p)
        return p

    def get_axis_param(self, name):
        for x in (self._xaxis + self._yaxis
                  + self._zaxis + self._caxis):
            if x.name == name:
                return x

    def get_axis_param_container_idx(self, idx):
        params = {}
        for x in self._xaxis:
            if idx in x._ax_idx:
                params['x'] = x
                break
        for x in self._yaxis:
            if idx in x._ax_idx:
                params['y'] = x
                break
        for x in self._zaxis:
            if idx in x._ax_idx:
                params['z'] = x
                break
        for x in self._caxis:
            if idx in x._ax_idx:
                params['c'] = x
                break
        return params

    def get_axes_artist_by_name(self, name):
        def _search(l, name):
            for p in l:
                if p.name == name:
                    return p._ax_idx
            return []
        if name[0] == 'x':
            idx = _search(self._xaxis, name)
        elif name[0] == 'y':
            idx = _search(self._yaxis, name)
        elif name[0] == 'z':
            idx = _search(self._zaxis, name)
        elif name[0] == 'c':
            idx = _search(self._caxis, name)
        a = [self._artists[k] for k in idx
             if k < len(self._artists)]
        if len(a) != 0:
            return a
        else:
            return [self._artists[0]]

    def property_in_palette_axes(self):
        #        names = [x.name for x in ( self._xaxis + self._yaxis
        #                                  +self._zaxis + self._caxis)]
        tab = ["common"]
        if self._3D:
            item = [["title", "aspect", "axis",  # frameon is not used in 3D
                     "axis_bgcolor", "axis_bgalpha",
                     "axis3d_bgcolor", "axis3d_bgalpha"], ]
        else:
            item = [["title", "aspect", "frame", "axis",
                     "axis_bgedgenone",
                     "axis_bgcolor",
                     "axis_bgedgecolor",
                     "axis_bglinewidth", "axis_bglinestyle", "axis_bgalpha", ]]
        for i in self._xaxis:
            tab.append(i.name)
            item.append(["axlabel", "axrangeparam13",
                         "axformat",
                         "axlotsize",
                         "axtlcolor", "axticks"])
            if not self._3D:
                item[-1].append("axxpos")
        for i in self._yaxis:
            tab.append(i.name)
            item.append(["axlabel", "axrangeparam13",
                         "axformat",
                         "axlotsize",
                         "axtlcolor", "axticks"])
            if not self._3D:
                item[-1].append("axypos")
        if self._3D:
            for i in self._zaxis:
                tab.append(i.name)
                item.append(["axlabel", "axrangeparam13",
                             "axformat",
                             #                            "axlsize",
                             "axlotsize",
                             "axtlcolor", "axticks"])
        for i in self._caxis:
            tab.append(i.name)
            item.append(["axlabel", "axrangeparam13o",
                         "cmap3", "cxclipunder", "cxclipover"])

        if self._3D:
            if self._use_gl:
                tab.append('gl')
                item.append(["gl_view", "gl_lighting", ])
            else:
                pass

        return tab, item

    def property_for_shell(self):
        tab, item = self.property_in_palette_axes()
        tags = [x for x in tab]
        tags[0] = ''
        if tags[-1] == 'gl':
            tags[-1] = ''
        return tab, item, tags

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'axes.png')
        return [idx1]

    def set_parent(self, parent):
        super(FigAxes, self).set_parent(parent)
        from ifigure.mto.fig_page import FigPage
        if isinstance(self._parent, FigPage):
            if self._parent.get_nomargin():
                self.apply_nomargin_mode()

    def get_container(self, *args, **kywds):
        return super(FigAxes, self).get_container()

    def generate_artist(self, *args, **kywds):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change

        container = self.get_container()
        rect, use_def, margin = self.calc_rect()
        if self.isempty():
            #           print "generating axes"
            from ifigure.matplotlib_mod.axes_mod import AxesMod
            from ifigure.matplotlib_mod.axes3d_mod import Axes3DMod

            if self._3D:
                kywds['use_gl'] = self._use_gl
                ax = Axes3DMod(container, rect, *(self._attr["args"]), **kywds)
                if not ax in container.axes:
                    a = container.add_axes(ax)
                ax.disable_mouse_rotation()
            else:
                ax = AxesMod(container, rect, *(self._attr["args"]),
                             **kywds)
                a = container.add_axes(ax)
#           self.backup_margin_param()

            if container.axes.count(ax) == 0:
                print('error in generating axes...')

            self._artists.append(ax)

            ppp = len(self._artists)-1
            params = self.get_axis_param_container_idx(ppp)
            if not "x" in params:
                self._xaxis[-1].add_ax_idx(ppp)
            if not "y" in params:
                self._yaxis[-1].add_ax_idx(ppp)
            if self._3D:
                if not "z" in params:
                    self._zaxis[-1].add_ax_idx(ppp)
                code = self.get_3d_pane_colorcode()
                self._set_3d_pane_color(code)

#           for name in ('x', 'y'):
#               p = self.get_axis_param(name)

            for artist in self._artists:
                artist.figobj = self
                artist.figobj_hl = []
                artist.set_zorder(self.getp('zorder'))
            lp = self.getp("loaded_property")

            if lp is not None:
                for k, artist in enumerate(self._artists):
                    self.set_artist_property(artist, lp[k])
                    # print lp[k]
                self.delp("loaded_property")

            self.set_title(self.getp('title_labelinfo'), self._artists[0])
            self.set_axis_bgedgecolor(self.getp('axis_bgedgecolor'), None)
            self.set_axis_bgfacecolor(self.getp('axis_bgfacecolor'))
            self.set_axis_bgalpha(self.getp('axis_bgalpha'), None)
            self.set_axis_bglinestyle(self.getp('axis_bglinestyle'), None)
            self.set_axis_bglinewidth(self.getp('axis_bglinewidth'), None)
            self.set_axis_onoff(self.getp('show_axis'), None)

            if self._hastwin[0]:
                self.twinx(new_axesparam=False)
            elif self._hastwin[1]:
                self.twiny(new_axesparam=False)

            for idx, a in enumerate(self._artists):
                params = self.get_axis_param_container_idx(idx)
                for key in params:
                    params[key].set_artist_rangeparam(a)
                    params[key].set_label(a)
                    params[key].set_ticks(a)
                    if not self._3D:
                        params[key].set_tickparam(a, self)

            self._mpl_cb = [a.callbacks.connect('xlim_changed',
                                                self.xylim_changed_cb),
                            a.callbacks.connect('ylim_changed',
                                                self.xylim_changed_cb)]

        else:
            for artist in self._artists:
                artist.set_position(rect)
#        print self._artists[0].get_window_extent().get_points()
        self.set_aspect(self.getp('aspect'))
        self.set_grid(self.getp('grid'))
        for a in self._artists:
            if hasattr(a, 'set_nomargin_mode'):
                a.set_nomargin_mode(self._nomargin_mode)

    def generate_cursor(self, evt, idx, target=None):
        '''
        this routine produce line cursor artists
        '''
        if self.get_3d():
            return
        f_page = self.get_figpage()
        if f_page is None:
            return super(FigAxes, self).generate_cursor(evt, idx)
        if evt.xdata is None:
            return
        if len(self._artists) == 0:
            return
        if target is None:
            kk = 0
        else:
            kk = (0 if not target.axes in self._artists
                  else self._artists.index(target.axes))
        ax = self._artists[kk]
        tx = transforms.blended_transform_factory(ax.transData,
                                                  ax.transAxes)
        ty = transforms.blended_transform_factory(ax.transAxes,
                                                  ax.transData)
        box = transforms.Bbox.from_extents(ax.get_window_extent().extents)

        alpha = ifigure._cursor_config["1dalpha"]
        c1 = ifigure._cursor_config["1dcolor1"]
        c2 = ifigure._cursor_config["1dcolor2"]
        w = ifigure._cursor_config["1dthick"]
        if idx == 0:
            self._cursor1 = [Line2D([evt.xdata, evt.xdata], [0, 1],
                                    figure=f_page._artists[0],
                                    transform=tx, linewidth=w,
                                    linestyle='-', color=c1, alpha=alpha,
                                    clip_box=box, clip_on=True,
                                    markerfacecolor='None'),
                             Line2D([0, 1], [evt.ydata, evt.ydata],
                                    figure=f_page._artists[0],
                                    transform=ty, linewidth=w,
                                    linestyle='-', color=c1,
                                    alpha=alpha, clip_box=box, clip_on=True,
                                    markerfacecolor='None')]
            self._cursor1_a = weakref.ref(ax)
        else:
            self._cursor2 = [Line2D([evt.xdata, evt.xdata], [0, 1],
                                    figure=f_page._artists[0],
                                    transform=tx, linewidth=w,
                                    linestyle='-', color=c2,
                                    alpha=alpha, clip_box=box, clip_on=True,
                                    markerfacecolor='None'),
                             Line2D([0, 1], [evt.ydata, evt.ydata],
                                    figure=f_page._artists[0],
                                    transform=ty, linewidth=w,
                                    linestyle='-', color=c2,
                                    alpha=alpha, clip_box=box, clip_on=True,
                                    markerfacecolor='None')]
            self._cursor2_a = weakref.ref(ax)
        self.get_figpage().add_resize_cb(self)

    def reset_cursor_range(self, evt, idx):
        return
        ### evt and idx is not used
        a = np.inf
        b = -np.inf
        for cx in self._caxis:
            a = np.min((a, cx.range[0], cx.range[1]))
            b = np.max((b, cx.range[0], cx.range[1]))
        self._cursor_range = (a, b)
#    def init_cursor_str(self):
#        self._cursor_str = ['','','']

    def erase_cursor(self):
        self._cursor1 = []
        self._cursor2 = []
        self._cursor1_a = None
        self._cursor2_a = None

    def update_cursor(self, evt, idx, mode=0, target=None):
        if evt.xdata is None:
            return
        x = evt.xdata
        y = evt.ydata
        if mode == 0:
            self._update_cursor_line(idx, x, y)
        if mode == 1 and isinstance(target, Line2D):
            k = np.argmin(abs(target.get_xdata() - evt.xdata))
            x = target.get_xdata()[k]
            y = target.get_ydata()[k]
            self._update_cursor_line(idx, x, y)
            return x, y
        if mode == 2 and isinstance(target, Line2D):
            k = np.argmin(abs(target.get_ydata() - evt.ydata))
            x = target.get_xdata()[k]
            y = target.get_ydata()[k]
            self._update_cursor_line(idx, x, y)
            return x, y
        if mode == 3:
            x, y, z = target.figobj.getp(('x', 'y', 'z'))
            if z.size == x.size*y.size:
                X, Y = np.meshgrid(x, y)
                p1 = np.transpose(np.vstack((X.flatten(), Y.flatten())))
                z0 = float(griddata(p1, z.flatten(),
                                    (evt.xdata, evt.ydata),
                                    method='linear'))
                self._cursor_data[idx] = (evt.xdata,
                                          evt.ydata,
                                          z0)
                if idx == 0:
                    self._cursor_range = (z0, self._cursor_range[1])
                else:
                    self._cursor_range = (self._cursor_range[0], z0)
                if self._cursor_range[0] > self._cursor_range[1]:
                    self.erase_cursor()
                    return

                # draw cursor

                z = target.get_array()
                extent = target.get_extent()
                zp = ((z > self._cursor_range[0]).astype(int) *
                      (z < self._cursor_range[1]).astype(int))

                alpha = ifigure._cursor_config["2dalpha"]
                z = np.empty((zp.shape[0], zp.shape[1], 4))
                z[:, :, 0] = 1 - zp
                z[:, :, 1] = 1 - zp
                z[:, :, 2] = 1 - zp
                z[:, :, 3] = zp*alpha
                self._cursor1 = [self._artists[0].imshow(z,
                                                         extent=extent, aspect='auto',
                                                         origin='lower')]
 #               self._cursor1[0].remove()
                self._cursor1_a = weakref.ref(self._artists[0])
            else:
                print('contour coursor for this mode is not implemented')
                print('make funcy obj here')

        if mode == 4:
            '''
            target.figobj should be either FigImage or FigContour
            '''
            x, y, z = target.figobj.getp(('x', 'y', 'z'))
            if z.size == x.size*y.size:
                X, Y = np.meshgrid(x, y)
                p1 = np.transpose(np.vstack((X.flatten(), Y.flatten())))
                z0 = float(griddata(p1, z.flatten(),
                                    (evt.xdata, evt.ydata),
                                    method='linear'))

                self._cursor_data[idx] = (evt.xdata,
                                          evt.ydata,
                                          z0)
                if idx == 0:
                    self._cursor_range = (z0, self._cursor_range[1])
                else:
                    self._cursor_range = (self._cursor_range[0], z0)
                if self._cursor_range[0] > self._cursor_range[1]:
                    self.erase_cursor()
                    return

                alpha = ifigure._cursor_config["2dalpha"]
#                for a in self._cursor1:
#                    a.remove()
                self._cursor1 = self._artists[0].contour(x, y, z,
                                                         self._cursor_range, alpha=alpha).collections[:]
                self._cursor1_a = weakref.ref(self._artists[0])
#                for a in self._cursor1:
#                    a.remove()
            else:
                print('contour coursor for this mode is not implemented')
                print('make funcy obj here')
        if mode == 5:
            from ifigure.widgets.slice_viewer import SliceViewer
            self._update_cursor_line(idx, x, y)
            app = self.get_root_parent().app

            if (ifigure._cursor_book is None or
                    ifigure._cursor_book() is None):
                #print('creating slice viewer')
                book, viewer = app.open_newbook_in_newviewer(
                    SliceViewer)

                ifigure._cursor_book = weakref.ref(book)
            book = ifigure._cursor_book()
            if not book.isOpen:
                if book.num_page() == 0:
                    book.add_page()
                viewer = app.open_book_in_newviewer(SliceViewer,
                                                    book)
            else:
                viewer = app.find_bookviewer(book)

#            data1, data2 = target.figobj.get_slice(x, y)
            data1, data2 = target.figobj.get_slice(evt.x, evt.y)
            if data1 is None:
                return
            if data1 is None:
                return

            viewer.update_curve(idx, x, y, data1, data2)

    def _update_cursor_line(self, idx, x, y):
        if idx == 0:
            if len(self._cursor1) < 2:
                return
            self._cursor1[0].set_xdata([x, x])
            self._cursor1[1].set_ydata([y, y])
        else:
            if len(self._cursor2) < 2:
                return
            self._cursor2[0].set_xdata([x, x])
            self._cursor2[1].set_ydata([y, y])
        self._cursor_data[idx] = (x, y)

    def valid_cursor(self):
        val = []
        if len(self._artists) == 0:
            return val
        if (self._cursor1_a is not None and
                self._cursor1_a() in self._artists):
            val += self._cursor1
        if (self._cursor2_a is not None and
                self._cursor2_a() in self._artists):
            val += self._cursor2
        return val

    '''
    xylim_changed_cb is used to update pageobj reling
    on axes. GenericPointHolder needs to be updated 
    through this message chain.
    '''

    def xylim_changed_cb(self, a):
        self.set_client_update_artist_request()
#    def ylim_changed_cb(self, a):
#        self.set_client_update_artist_request()

    def del_artist(self, artist=None, delall=False):

        if delall:
            alist = self._artists
        else:
            #           alist=[artist]
            alist = artist

        val = []
        for a in self._artists:
            val.append(self.get_artist_property(a))
        if len(val) != 0:
            self.setp("loaded_property", val)

        if len(alist) is len(self._artists):
            for name, child in self.get_children():
                child.del_artist(delall=True)

        if len(alist) != 0:
            self.highlight_artist(False, alist)
            container = self.get_container()
            for a in alist:
                a.clear()
                a.callbacks.disconnect(self._mpl_cb[0])
                a.callbacks.disconnect(self._mpl_cb[1])
                try:
                    container.delaxes(a)
                except:
                    print("can not do delaxes...?")
                a.axes = None
        super(FigAxes, self).del_artist(alist, delall=delall)

    def get_axesartist_extent(self, w, h, a=None, renderer=None, box=None):
        '''
        a is ignored
        '''
        from ifigure.utils.cbook import GetArtistExtent

        def merge_box(box, box2):
            return (min((box[0], box2[0])),
                    min((box[1], box2[1])),
                    max((box[2], box2[2])),
                    max((box[3], box2[3])),)
        if box is None:
            box = (np.inf, np.inf, -np.inf, -np.inf)

        for a in self._artists:
            xa = a.get_xaxis()
            ya = a.get_yaxis()

            alist = [a, a.title]
            alist += xa.get_ticklabels()
            alist.append(xa.get_label())
            alist.append(xa.get_offset_text())
            alist += ya.get_ticklabels()
            alist.append(ya.get_label())
            alist.append(ya.get_offset_text())
            alist.extend(a.artists)
            #renderer = a.figure._cachedRenderer
            renderer = a.figure.canvas.get_renderer()

            for item in alist:
                # skip this case since it fails
                if (isinstance(item, matplotlib.text.Text) and
                        renderer is None):
                    continue
                try:

                    box1 = item.get_window_extent(renderer).extents
                    box = merge_box(box, box1)
                except:
                    dprint1('skipping obj in axesartist_extent:' + str(item))

            for item in a.texts:
                box = GetArtistExtent(item, box=box,  renderer=renderer)

            box = (max((box[0]-2, 0)),
                   max((box[1]-2, 0)),
                   min((w, box[2]+2)),
                   min((h, box[3]+2)))

        return box

    def calc_rect(self, ignore_pagemargin=False):
        #        print self, 'calc_rect'
        #        import traceback
        #        traceback.print_stack()
        if self._attr["use_def_margin"]:
            margin = self._parent.getp("def_margin")
        else:
            margin = self.getp("margin")

        area = self._attr["area"]
        tm = [margin[i] + self._extra_margin[i]
              for i in range(4)]
        rect = [area[0]+tm[0]*area[2],
                area[1]+tm[3]*area[3],
                (1-tm[0]-tm[1])*area[2],
                (1-tm[2]-tm[3])*area[3]]
        if self._nomargin_mode:
            ignore_pagemargin = True
        if not ignore_pagemargin:
            pm = self.get_figpage()._page_margin
            rect = [(1-pm[0]-pm[1])*rect[0]+pm[0],
                    (1-pm[2]-pm[3])*rect[1]+pm[3],
                    rect[2]*(1-pm[0]-pm[1]),
                    rect[3]*(1-pm[2]-pm[3]), ]
            if self.getp('aspect') == 'equal' and not self._3D:
                params = self.get_axis_param_container_idx(0)
                dx = abs(params['x'].range[1] - params['x'].range[0])
                dy = abs(params['y'].range[1] - params['y'].range[0])
                w, h = self.get_figpage().getp('figsize')
                ratio = (w*rect[2])*dy/dx/(h*rect[3])
                if ratio > 1:
                    #                   v = rect[3] / ratio
                    v = rect[3]*h*dx/dy/w
                    rect[0] = rect[0]+(rect[2] - v)/2.
#                   rect[2] = v
                    rect[2] = rect[3]*h*dx/dy/w
                else:
                    #                   v = rect[2] * ratio
                    v = rect[2]*w*dy/dx/h
                    rect[1] = rect[1]+(rect[3] - v)/2.
#                   rect[3] = v
                    rect[3] = rect[2]*w*dy/dx/h
        self._rect = rect
        return rect, self.getp("use_def_margin"), margin

    def get_rect(self, asbbox=False):
        if self._rect is None:
            self.calc_rect()
        return self._rect

    def set_area(self, area, a=None):
        self.setp("area", area[:])
        rect, use_def, margin = self.calc_rect()
        for a in self._artists:
            a.set_position(rect)
        self.set_client_update_artist_request()
        self.set_bmp_update(False)

    def get_area(self, a=None):
        return self.getp("area")[:]

    def set_margin(self, m, a=None):
        self.setp("margin", m[:])
        rect, use_def, margin = self.calc_rect()
        for a in self._artists:
            a.set_position(rect)
        self.set_client_update_artist_request()
        self.set_bmp_update(False)

    def get_margin(self, m, a=None):
        return self.getp("margin")[:]

    def get_grid(self, a=None):
        return self.getp('grid')

    def set_grid(self, value, a=None):
        if len(self._artists) == 0:
            return
        if self._3D:
            return
        a = self._artists[0]

        a.grid(value[0], 'major', 'x')
        a.grid(value[1], 'major', 'y')
        self.setp('grid', list(value))
#        if self._3D:
#            a.grid(value[2], 'major', 'z')

    def set_aspect(self, value, a=None):
        #        for a in self._artists: a.set_aspect(value)
        if len(self._artists) > 0:
            self._artists[0].set_aspect('auto')
        if self._3D:
            self.setp('aspect', 'auto')
            rect, use_def, margin = self.calc_rect()
            self.setp('aspect', str(value))
            if len(self._artists) > 0:
                ax = self._artists[0]
                if value == 'equal':
                    ax._ignore_screen_aspect_ratio = False
                else:
                    ax._ignore_screen_aspect_ratio = True
        else:
            self.setp('aspect', str(value))
            rect, use_def, margin = self.calc_rect()
        for a in self._artists:
            a.set_position(rect)
        self.set_client_update_artist_request()
        self.set_bmp_update(False)
        if str(value) == 'equal' and not self._3D:
            self.get_figpage().add_resize_cb(self)
        else:
            self.get_figpage().rm_resize_cb(self)

    def get_aspect(self, a=None):
        return self.getp('aspect')

    def set_extra_margin(self, m, a=None):
        self._extra_margin = m[:]

    def get_extra_margin(self, a=None):
        return self._extra_margin[:]

    def set_edge_only(self, m, a=None):
        self._edge_only = m

    def get_edge_only(self, a=None):
        return self._edge_only[:]

    def add_plot(self, name=None, *args, **kywds):
        obj = FigPlot(*args, **kywds)
        if name is None:
            name = self.get_next_name(obj.get_namebase())
        return self.add_child(name, obj)

    def add_contour(self, name=None, *args, **kywds):
        obj = FigContour(*args, **kywds)
        if name is None:
            name = self.get_next_name(obj.get_namebase())
        return self.add_child(name, obj)

    def add_image(self, name=None, *args, **kywds):
        obj = FigImage(*args, **kywds)
        if name is None:
            name = self.get_next_name(obj.get_namebase())
        return self.add_child(name, obj)

    def add_insetaxes(self, name=None, *args, **kywds):
        obj = FigInsetAxes(*args, **kywds)
        if name is None:
            name = self.get_next_name(obj.get_namebase())
        return self.add_child(name, obj)

    def add_colorbar(self, name=None,  *args, **kywds):
        '''
        this routine shoud be accessed from caxis_param.show_cbar
        '''
        obj = FigColorBar(*args, **kywds)
        if name is None:
            name = self.get_next_name(obj.get_namebase())
        return self.add_child(name, obj)

    def del_plot(self, fig_plot):
        self.del_figobj(fig_plot)

#
# setter/getter
#
    def set_axis_onoff(self, value, a=None):
        self.setp("show_axis", value)
        for a in self._artists:
            if value:
                a.set_axis_on()
            else:
                a.set_axis_off()

    def get_axis_onoff(self, a):
        return self.getp("show_axis")

    # nomargin
    def apply_nomargin_mode(self):
        if self.get_figpage().get_nomargin():
            self.backup_margin_param()
            self.setp("margin", [0, 0, 0, 0])
            self.setp("use_def_margin", False)
            for a in self._artists:
                if hasattr(a, 'set_nomargin_mode'):
                    a.set_nomargin_mode(True)
            self._nomargin_mode = True
        else:
            self.setp("margin", self._margin_bk[0])
            self.setp("use_def_margin", self._margin_bk[1])
            for a in self._artists:
                if hasattr(a, 'set_nomargin_mode'):
                    a.set_nomargin_mode(False)
            self._nomargin_mode = False
        rect, use_def, margin = self.calc_rect()
        for a in self._artists:
            a.set_position(rect)
        self.set_client_update_artist_request()

    def backup_margin_param(self):
        if not self._nomargin_mode:
            self._margin_bk = (self.getp("margin"),
                               self.getp("use_def_margin"))
    ### range / autorange / linear-log

    def set_axrangeparam13(self, param, a=None):
        '''
        this is called from aritst widgets in bypass history
        mode. history entry needs to be made in this routine

        param is in the format of request  (name, value)
        '''
        book = self.get_figbook()

        app = wx.GetApp().TopWindow
        viewer = app.find_bookviewer(book)
        if viewer is None:
            return
        canvas = viewer.canvas
        requests = {self: [param]}
        if param[1][0]:
            requests[self] = self.compute_new_range(request=requests[self])
        requests = canvas.expand_requests(requests)

        canvas.send_range_action(requests, 'range')

    def set_axrangeparam(self, param, a=None):
        p = self.get_axis_param(param[0])
        param[1][3] == str(param[1][3])
        if param[1][3] == 'log':
            range = param[1][2]
            range0 = range[0] if range[0] > 0 else range[1]*1e-16
#           range0= max((1e-16, range[0]))
            range1 = range[1]
            if range[1] < range0:
                range1 = 2*range0
            param[1][2] = [range0, range1]
        p.set_rangeparam(param[1])

        # update aritst range param
        if self.isempty():
            return
        for a in self.get_axes_artist_by_name(param[0]):
            p.set_artist_rangeparam(a)
        if self.get_aspect() == 'equal':
            rect, use_def, margin = self.calc_rect()
            for a in self._artists:
                a.set_position(rect)
        self.set_bmp_update(False)
#        ifigure.events.SendRangeChangedEvent(self, name=param[0])
#        print 'send range change event'

    def get_axrangeparam13(self, a, name):
        return self.get_axrangeparam(a, name)

    def get_axrangeparam(self, a, name):
        p = self.get_axis_param(name)
        value = p.get_rangeparam()
        return value

    def set_adjustrange(self, *args):
        self.adjust_axes_range()

    def get_adjustrange(self, *args):
        pass

    def call_handle_axes_change(self, n):
        if self.isempty():
            return
        for child in self.walk_tree():
            if child is not self and not child._suppress:
                child.handle_axes_change({'td': self, 'name': n})

    def set_textprop(self, value, a):
        a.set_text(value[0])
        a.set_color(value[1])
        a.set_family(value[2])
        a.set_weight(value[3])
        a.set_style(value[4])
        a.set_size(float(value[5]))

    def get_textprop(self, a):
        return [a.get_text(),
                a.get_color(),
                a.get_family()[0],
                a.get_weight(),
                a.get_style(),
                str(a.get_size())]

    def set_title(self, value, a=None):
        '''
        set/get_title stores textprop
        to _attr

        calling this using string argment is not recommended.
        '''
        figpage = self.get_figpage()
        if figpage is None:
            return

        tinfo = self.getp('title_labelinfo')
        tfont = figpage.getp('title_font')
        tweight = figpage.getp('title_weight')
        tstyle = figpage.getp('title_style')
        tsize = figpage.getp('title_size')

        if isinstance(value, six.string_types):
            # Don't use this!
            # use viewer.title whenever possible.
            dprint1('set_title is called with string argument. not recommendad')
            if a is not None:
                v0 = self.get_textprop(a.title)
                v0[0] = value
                value = v0
                v2 = [x for x in value]
            else:
                value = [value, 'k', 'default', 'default',
                         'default', 'default']
                v2 = [value, 'k', 'default', 'default',
                      'default', 'default']
        else:
            v2 = [x for x in value]
        if str(value[2]) == 'default':
            v2[2] = tfont
        if str(value[3]) == 'default':
            v2[3] = tweight
        if str(value[4]) == 'default':
            v2[4] = tstyle
        if str(value[5]) == 'default':
            v2[5] = tsize

        if a is not None:
            self.set_textprop(v2, a.title)
        self.setp('title_labelinfo', value)

    def get_title(self, a):
        value = self.getp('title_labelinfo')
        return [x for x in value]

    def set_cxclipunder(self, param, a):
        p = self.get_axis_param(param[0])
        p.clip = (param[1], p.clip[1])
        for a in self._artists:
            p.set_artist_rangeparam(a)
        self.set_bmp_update(False)

    def get_cxclipunder(self, a, name):
        p = self.get_axis_param(name)
        return p.clip[0]

    def set_cxclipover(self, param, a):
        p = self.get_axis_param(param[0])
        p.clip = (p.clip[0], param[1])
        for a in self._artists:
            p.set_artist_rangeparam(a)
        self.set_bmp_update(False)

    def get_cxclipover(self, a, name):
        p = self.get_axis_param(name)
        return p.clip[1]

    def set_axticks(self, param, a=None):
        p = self.get_axis_param(param[0])
        p.ticks = param[1]
        ax = self.get_axes_artist_by_name(param[0])[0]
        p.set_ticks(ax)
        self.set_bmp_update(False)

    def get_axticks(self, a=None, name='x'):
        p = self.get_axis_param(name)
        return p.ticks

    def refresh_nticks(self):
        self.set_bmp_update(False)
        for x in self._xaxis:
            #            x.ticks = nxticks
            a = self.get_axes_artist_by_name(x.name)[0]
            x.set_ticks(a)
        for y in self._yaxis:
            #            y.ticks = nyticks
            a = self.get_axes_artist_by_name(y.name)[0]
            y.set_ticks(a)
        if not self.get_3d():
            return
        for z in self._zaxis:
            #            z.ticks = nzticks
            a = self.get_axes_artist_by_name(z.name)[0]
            z.set_ticks(a)

    def set_axlabel(self, param, a):
        p = self.get_axis_param(param[0])
        p.labelinfo = param[1]
        p.set_label(self.get_axes_artist_by_name(param[0])[0])
        self.set_bmp_update(False)

    def get_axlabel(self, a, name):
        p = self.get_axis_param(name)
        return [x for x in p.labelinfo]

    # axis label color
    def set_axlcolor(self, param, a):
        p = self.get_axis_param(param[0])
        p.lcolor = param[1][0]
        p.otcolor = param[1][1]
        p.set_tickparam(self.get_axes_artist_by_name(param[0])[0], self)
        self.set_bmp_update(False)

    def get_axlcolor(self, a, name):
        p = self.get_axis_param(name)
        return p.lcolor, p.otcolor

    # tick color
    def set_axtcolor(self, param, a):
        from ifigure.utils.cbook import isstringlike
        p = self.get_axis_param(param[0])
        if isstringlike(param[1]):
            p.tcolor = str(param[1])
        else:
            p.tcolor = param[1]
        for a in self.get_axes_artist_by_name(param[0]):
            p.set_tickparam(a, self)
        self.set_bmp_update(False)

    def get_axtcolor(self, a, name):
        p = self.get_axis_param(name)
        return p.tcolor

    # tick/label color
    def set_axtlcolor(self, param, a):
        from ifigure.utils.cbook import isstringlike
        p = self.get_axis_param(param[0])
        if isstringlike(param[1]):
            p.tcolor = str(param[1][0])
        else:
            p.tcolor = param[1][0]
        p.lcolor = param[1][1]
        p.otcolor = param[1][2]
        for a in self.get_axes_artist_by_name(param[0]):
            p.set_tickparam(a, self)
        self.set_bmp_update(False)

    def get_axtlcolor(self, a, name):
        p = self.get_axis_param(name)
        return p.tcolor, p.lcolor, p.otcolor

    # label size
    def set_axlsize(self, param, a):
        p = self.get_axis_param(param[0])
        p.lsize = param[1]
        p.set_tickparam(self.get_axes_artist_by_name(param[0])[0], self)
        self.set_bmp_update(False)

    def get_axlsize(self, a, name):
        p = self.get_axis_param(name)
        return p.lsize

    def set_axotsize(self, param, a):
        p = self.get_axis_param(param[0])
        p.otsize = param[1]
        p.set_tickparam(self.get_axes_artist_by_name(param[0])[0], self)
        self.set_bmp_update(False)

    def get_axotsize(self, a, name):
        p = self.get_axis_param(name)
        return p.otsize

    def set_axlotsize(self, param, a):
        p = self.get_axis_param(param[0])
        p.lsize = 'default' if param[1][0] == 'default' else int(param[1][0])
        p.otsize = 'default' if param[1][1] == 'default' else int(param[1][1])
        p.set_tickparam(self.get_axes_artist_by_name(param[0])[0], self)
        self.set_bmp_update(False)

    def get_axlotsize(self, a, name):
        p = self.get_axis_param(name)
        return p.lsize, p.otsize

    def postprocess_mpltext_edit(self):
        '''
        called after text is edited interactively
        this allows to load mpl text data to figobj
        '''
        a = self._artists[0]
        if self._3D:
            plist = (self._xaxis + self._yaxis
                     + self._zaxis + self._caxis)
        else:
            plist = self._xaxis + self._yaxis + self._caxis
        for p in plist:
            a = self.get_axes_artist_by_name(p.name)[0]
            label = p.get_label_from_mpl(a)
            p.labelinfo[0] = label

        # title
        a = self._artists[0]
        value = self.getp('title_labelinfo')
        value[0] = a.title.get_text()

    # format
    def set_axformat(self, param, a):
        p = self.get_axis_param(param[0])
        p.format = param[1]
        p.set_ticks(self.get_axes_artist_by_name(param[0])[0])
        self.set_bmp_update(False)

    def get_axformat(self, a, name):
        p = self.get_axis_param(name)
        return p.format

    def onResize(self, evt):
        self.erase_cursor()
        if self.getp('aspect') == 'equal':
            rect, use_def, margin = self.calc_rect()
            for a in self._artists:
                a.set_position(rect)
            self.set_client_update_artist_request()


#
#   menu in tree viewer
#


    def tree_viewer_menu(self):
        # return MenuString, Handler, MenuImage
        #  m=('Add Plot',     self.onAddPlot, None),
        #      ('Add Contour',  self.onAddContour, None),
        #     ('Add Image',    self.onAddImage, None),
        m = [('Add InsetAxes', self.onAddInsetAxes, None), ]
        if False in [p.has_cbar() for p in self._caxis]:
            m.append(('Add ColorBar', self.onAddColorBar, None),)
        m.append(('---',        None, None))
        if len(self._artists) == 0:
            m.append(('Realize',    self.onRealize, None))

        return m+super(FigAxes, self).tree_viewer_menu()

    def onRealize(self, e):
        self.realize()
        ifigure.events.SendPVDrawRequest(self)
#       self.onForceUpdate(e)

    def onAddPlot(self, e):
        self.add_plot(None, [0, 1], [0, 1])
        self.realize()
        ifigure.events.SendPVAddFigobj(self)
        e.Skip()

    def onAddInsetAxes(self, e=None):
        ichild = self.add_insetaxes()
        child = self.get_child(ichild)
        child.realize()
        ifigure.events.SendPVAddFigobj(self)
        if e is not None:
            e.Skip()

    def onAddInsetAxesCanvas(self, evt):
        '''
        when canvas menu is selected
        evt.GetEventObject() = canvas
        '''
        ichild = self.add_insetaxes()
        child = self.get_child(ichild)
        child.realize()
        ifigure.events.SendChangedEvent(
            self.get_figpage(), evt.GetEventObject())
        ifigure.events.SendCanvasDrawRequest(evt.GetEventObject(),)
        evt.Skip()

    def onAddColorBar(self, e=None):
        '''
        add color bar when called from project tree browser
        not undoable...
        '''
        if False in [p.has_cbar() for p in self._caxis]:
            for k, p in enumerate(self._caxis):
                if not p.has_cbar():
                    p.show_cbar(self, offset=-0.1*k)
        ifigure.events.SendPVAddFigobj(self)
        e.Skip()

    def onAddContour(self, e):
        self.add_contour(None, np.arange(4).reshape(2, 2))
        self.realize()
        ifigure.events.SendPVAddFigobj(self)
        e.Skip()

    def onAddImage(self, e):
        self.add_image(None, np.zeros([2, 2]))
        self.realize()
        ifigure.events.SendPVAddFigobj(self)
        e.Skip()

# save/load
    def save_data(self, fid=None):
        val = self.getp()
        # print "writing axes param", val
        pickle.dump(val, fid)
        super(FigAxes, self).save_data(fid)

    def save_data2(self, data):
        # the first element is version code
        param = {"_edge_only": self._edge_only,
                 "_margin_bk": self._margin_bk,
                 "_nomargin_mode": self._nomargin_mode,
                 "_3D": self._3D,
                 "_extra_margin": self._extra_margin,
                 "_3d_pane_color": self._3d_pane_color,
                 "_hastwin": self._hastwin}

        axisdata = {"xaxis": [x.make_save_data(self) for x in self._xaxis],
                    "yaxis": [x.make_save_data(self) for x in self._yaxis],
                    "zaxis": [x.make_save_data(self) for x in self._zaxis],
                    "caxis": [x.make_save_data(self) for x in self._caxis]}

        data['FigAxes'] = (1, self.getp(), param, axisdata)
        data = super(FigAxes, self).save_data2(data)
        return data

    def load_data(self, fid=None):
        #        print "loading  fig_axes data"
        val = pickle.load(fid)
        for key in val:
            self.setp(key, val[key])
        super(FigAxes, self).load_data(fid)

    def load_data2(self, data):
        if 'FigAxes' in data:
            val = data['FigAxes'][1]

            # this if statement is bug fix recovery
            # normally this if is not executed
            if 'title_labelinfo' in val:
                if isinstance(val['title_labelinfo'], str):
                    dprint1(
                        'stored title_lableinfo is string!!!!. Executing recovery section')
                    # print self.getp('title_labelinfo')
                    self.getp('title_labelinfo')[0] = val['title_labelinfo']
                    del val['title_labelinfo']
                    # print self.getp('title_labelinfo')
                    if 'title_labelinfo' in data['FigObj'][2]:
                        del data['FigObj'][2]['title_labelinfo']
            for key in val:
                self.setp(key, val[key])
            if len(data['FigAxes']) > 2:
                param = data['FigAxes'][2]
                for key in param:
                    if hasattr(self, key):
                        setattr(self, key, param[key])
            if len(data['FigAxes']) > 3:
                axisdata = data['FigAxes'][3]
                self._xaxis = []
                for x in axisdata["xaxis"]:
                    ax = AxisXParam('x').import_data(self, x)
                    self._xaxis.append(ax)
                self._yaxis = []
                for x in axisdata["yaxis"]:
                    ax = AxisYParam('y').import_data(self, x)
                    self._yaxis.append(ax)
                self._zaxis = []
                for x in axisdata["zaxis"]:
                    ax = AxisZParam('z').import_data(self, x)
                    self._zaxis.append(ax)
                self._caxis = []
                for x in axisdata["caxis"]:
                    ax = AxisCParam('c').import_data(self, x)
                    self._caxis.append(ax)
        if not isinstance(self.getp('grid'), list):
            self.setp('grid', [False]*3)
        super(FigAxes, self).load_data2(data)

        from ifigure.ifigure_config import isMPL2
        if isMPL2:
            lp = self.getp("loaded_property")
            for x in lp:
                if 'axis_bgcolor' in x:
                    x['facecolor'] = x['axis_bgcolor']
                    del x['axis_bgcolor']

    def cla(self):
        from ifigure.mto.fig_text import FigText
        for name, child in self.get_children():
            if isinstance(child, FigAxes):
                continue
            if isinstance(child, FigText):
                continue
            child.destroy()

    def canvas_menu(self):
        return []

    def twinx(self, new_axesparam=True):
        if self.get_3d():
            return

        from ifigure.matplotlib_mod.axes_mod import AxesMod
        from ifigure.matplotlib_mod.axes3d_mod import Axes3DMod

        self._artists.append(AxesMod(self._artists[0].twinx()))
        if new_axesparam:
            p = self.add_axis_param(dir='y')
            if self._yaxis[0].tick_position == 'left':
                p.tick_position = 'right'
            else:
                p.tick_position = 'left'
            for p in self._yaxis:
                p.tick_both = False
#           self._axis_name_table[p.name] = len(self._artists)-1
        self._xaxis[0].add_ax_idx(len(self._artists)-1)
        self._yaxis[-1].add_ax_idx(len(self._artists)-1)
        self._artists[-1].figobj = self
        self._artists[-1].figobj_hl = []
        self._artists[-1].isTwin = True
        self._artists[-1].set_frame_on(False)
        self._artists[-1].set_zorder(self.getp('zorder'))
        self._hastwin[0] = True

        for a, p in zip(self._artists, self._yaxis):
            v = (p.name, self.get_ax_pos(a, p.name))
            self.set_ax_pos(v, a)
        return len(self._artists)-1

    def del_twinx(self):
        container = self.get_container()
        for p in self._xaxis + self._yaxis + self._zaxis + self._caxis:
            p.rm_ax_idx(len(self._artists)-1)
        container.delaxes(self._artists[-1])
        super(FigAxes, self).del_artist(artist=[self._artists[-1]])
        self._hastwin[0] = False
        self._yaxis = self._yaxis[:-1]
        for a, p in zip(self._artists, self._yaxis):
            v = (p.name, self.get_ax_pos(a, p.name))
            self.set_ax_pos(v, a)

    def twiny(self, new_axesparam=True):
        if self.get_3d():
            return

        from ifigure.matplotlib_mod.axes_mod import AxesMod
        from ifigure.matplotlib_mod.axes3d_mod import Axes3DMod

        self._artists.append(AxesMod(self._artists[0].twiny()))
        self._artists[-1].__class__ = self._artists[0].__class__
        if new_axesparam:
            p = self.add_axis_param(dir='x')
            if self._xaxis[0].tick_position == 'bottom':
                p.tick_position = 'top'
            else:
                p.tick_position = 'bottom'
            for p in self._xaxis:
                p.tick_both = False
#           self._axis_name_table[p.name] = len(self._artists)-1
        self._yaxis[0].add_ax_idx(len(self._artists)-1)
        self._xaxis[-1].add_ax_idx(len(self._artists)-1)
        self._artists[-1].figobj = self
        self._artists[-1].figobj_hl = []
        self._artists[-1].isTwin = True
        self._artists[-1].set_frame_on(False)
        self._artists[-1].set_zorder(self.getp('zorder'))
        self._hastwin[1] = True
        for a, p in zip(self._artists, self._xaxis):
            v = (p.name, self.get_ax_pos(a, p.name))
            self.set_ax_pos(v, a)
        return len(self._artists)-1

    def del_twiny(self):
        container = self.get_container()
        for p in self._xaxis + self._yaxis + self._zaxis + self._caxis:
            p.rm_ax_idx(len(self._artists)-1)
        container.delaxes(self._artists[-1])
        super(FigAxes, self).del_artist(artist=[self._artists[-1]])
        self._hastwin[1] = False
        self._xaxis = self._xaxis[:-1]
        for a, p in zip(self._artists, self._xaxis):
            v = (p.name, self.get_ax_pos(a, p.name))
            self.set_ax_pos(v, a)

    def set_twinx(self, value, a):
        if value[0]:
            i = self.twinx()
            for p, v in zip(self._yaxis, value[1]):
                p.import_data(self, v)
            self._yaxis[-1].set_artist_rangeparam(self._artists[i])
            for p in self._xaxis:
                for k in p._ax_idx:
                    p.set_artist_rangeparam(self._artists[k])
            self.apply_nomargin_mode()
        else:
            for p, v in zip(self._yaxis, value[1]):
                p.import_data(self, v)
            self.del_twinx()
            for p in self._xaxis:
                for k in p._ax_idx:
                    p.set_artist_rangeparam(self._artists[k])

    def set_twiny(self, value, a):
        if value[0]:
            i = self.twiny()
            for p, v in zip(self._xaxis, value[1]):
                p.import_data(self, v)
            self._xaxis[-1].set_artist_rangeparam(self._artists[i])
            for p in self._yaxis:
                for k in p._ax_idx:
                    p.set_artist_rangeparam(self._artists[k])
            self.apply_nomargin_mode()
        else:
            for p, v in zip(self._xaxis, value[1]):
                p.import_data(self, v)
            self.del_twiny()
            for p in self._yaxis:
                for k in p._ax_idx:
                    p.set_artist_rangeparam(self._artists[k])

    def get_twinx(self, a):
        value = [p.make_save_data(self) for p in self._yaxis]
        if self._hastwin[0]:
            return (True, value)
        return (False, value)

    def get_twiny(self, a):
        value = [p.make_save_data(self) for p in self._xaxis]
        if self._hastwin[1]:
            return (True, value)
        return (False, value)

    def hastwin(self, dir='both'):
        if dir.upper() == 'X':
            return self._hastwin[0]
        if dir.upper() == 'Y':
            return self._hastwin[0]
        if dir.upper() == 'BOTH':
            return [a for a in self._hastwin]

    def onAddTwinX(self, evt):
        #cvalue = self.get_twinx(None)
        self.twinx()
        value = [p.make_save_data(self) for p in self._yaxis]
        value.append(self._yaxis[-1].make_save_data(self))
        value[-1]["_ax_idx"] = []
        value = (True, value)
        #self.set_twinx(cvalue, None)
        self.del_twinx()
        h = UndoRedoFigobjMethod(self._artists[0], 'twinx', value)
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([h])
        #ifigure.events.SendSelectionEvent(self.get_figpage(), canvas, canvas.selection)

    def onRemoveTwinX(self, evt):
        '''
        1) reorient clients to the remaining axes        
        2) remove ax artist
        '''
        value = [p.make_save_data(self) for p in self._yaxis]
        value = (False, value[:-1])
        h = []
        for child in self.walk_tree():
            if child.get_container_idx() == 1:
                h.append(UndoRedoFigobjMethod(child._artists[0],
                                              'container_idx', 0))
        h.append(UndoRedoFigobjMethod(self._artists[0], 'twinx', value))
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def onAddTwinY(self, evt):
        self.twiny()
        value = [p.make_save_data(self) for p in self._xaxis]
        value.append(self._xaxis[-1].make_save_data(self))
        value[-1]["_ax_idx"] = []
        value = (True, value)
        self.del_twiny()
        h = UndoRedoFigobjMethod(self._artists[0], 'twiny', value)
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([h])

    def onRemoveTwinY(self, evt):
        value = [p.make_save_data(self) for p in self._xaxis]
        value = (False, value[:-1])
        h = []
        for child in self.walk_tree():
            if child.get_container_idx() == 1:
                h.append(UndoRedoFigobjMethod(child._artists[0],
                                              'container_idx', 0))

        h.append(UndoRedoFigobjMethod(self._artists[0], 'twiny', value))
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def set_caxis_value(self, value, a):
        while len(value) < len(self._caxis):
            self._caxis = self._caxis[:-1]
        while len(value) > len(self._caxis):
            ca_param = self.add_axis_param(dir='c')
        for p, v in zip(self._caxis, value):
            p.import_data(self, v)

    def get_caxis_value(self, a):
        value = [p.make_save_data(self) for p in self._caxis]
        return value

    def onAddC(self, evt):
        ca_param = self.add_axis_param(dir='c')
        value = [p.make_save_data(self) for p in self._caxis]
        self._caxis = self._caxis[:-1]
        h = []
        h.append(UndoRedoFigobjMethod(self._artists[0], 'caxis_value',
                                      value))
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def onRemoveC(self, evt):
        value = [p.make_save_data(self) for p in self._caxis[:-1]]
        h = []
        h.append(UndoRedoFigobjMethod(self._artists[0], 'caxis_value',
                                      value))
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h)

    def canvas_axes_menu(self):
        m = []
        if not self.get_3d():
            if (not self._hastwin[0] and not self._hastwin[1]):
                m.append(('Add X2 axis', self.onAddTwinY, None))
                m.append(('Add Y2 axis', self.onAddTwinX, None))
            if self._hastwin[0]:
                m.append(('Remove Y2 axis', self.onRemoveTwinX, None))
            if self._hastwin[1]:
                m.append(('Remove X2 axis', self.onRemoveTwinY, None))
        if len(self._caxis) == 0:
            txt = 'Add C axis'
        else:
            txt = 'Add C'+str(len(self._caxis)+1)+' axis'
        m.append((txt, self.onAddC, None))

        if len(self._caxis) > 0 and len(self._caxis[-1]._member) == 0:
            if len(self._caxis) == 1:
                txt = 'Remove C axis'
            else:
                txt = 'Remove C'+str(len(self._caxis))+' axis'
            m.append((txt, self.onRemoveC, None))
        if not isinstance(self, FigInsetAxes):
            m.append(('Add Inset Axes', self.onAddInsetAxesCanvas, None))
        if self.get_3d():
            m.append(('Use 2D Axes', self.onToggle3D, None))
        else:
            m.append(('Use 3D Axes', self.onToggle3D, None))

        return m

    def onToggle3D(self, evt):
        if self.get_3d():
            if sum([len(x._member) for x in self._zaxis]) != 0:
                from ifigure.widgets.dialog import message
                message(self, 'panel has 3D plot', 'error')
                return
            self.set_3d(False)
        else:
            self.set_3d(True)
        evt.GetEventObject().set_axes_selection(self._artists[0])
        ifigure.events.SendCanvasDrawRequest(evt.GetEventObject(),)
        ifigure.events.SendSelectionEvent(self, evt.GetEventObject(),
                                          evt.GetEventObject().selection)
#           figobj.reset_artist()

    def set_3d(self, value):
        if self._3D == value:
            return
        self._3D = value
        if self._3D and len(self._zaxis) == 0:
            self.add_axis_param(dir='z')
        if self._3D:  # going to 3d
            self.get_axis_bgfacecolor()
            self.get_axis_bgedgecolor()
            self.set_axis_bgalpha(0.0, None)
        if not self._3D:
            self._zaxis = []
        self.del_artist(delall=True)
        self.realize()
        if not self._3D:
            self.set_axis_bgedgecolor(self.getp('axis_bgedgecolor'))
            self.set_axis_bgfacecolor(self.getp('axis_bgfacecolor'))
            self.set_axis_bgalpha(1.0, None)
        self.set_bmp_update(False)

    def get_3d(self):
        return self._3D

    def set_axis3d_bgcolor(self, value, artist):
        self.set_3d_pane_colorname(value)

    def get_axis3d_bgcolor(self, artist):
        return self.get_3d_pane_colorname()

    def set_axis3d_bgalpha(self, value, artist):
        if value is None:
            value = 1.0
        self.set_3d_pane_alpha([float(value)]*3)

    def get_axis3d_bgalpha(self, artist):
        return self.get_3d_pane_coloralpha()[0]

    def get_gl_lighting(self, a):
        loc = a._lighting['light_direction']
        phi = np.arctan2(loc[1], loc[0])
        theta = np.arctan2(np.sqrt(loc[1]**2 + loc[0]**2), loc[2])

        v = [None,
             a._lighting['ambient'],
             a._lighting['light'],
             a._lighting['specular'],
             None,
             phi*180/np.pi,
             theta*180/np.pi,
             a._lighting['shadowmap'],
             a._use_frustum]
        return v

    def set_gl_lighting(self, v, a):
        a._lighting['ambient'] = v[1]
        a._lighting['light'] = v[2]
        a._lighting['specular'] = v[3]
        a._lighting['shadowmap'] = v[7]
        phi, th = v[5]*np.pi/180., v[6]*np.pi/180.
        loc = np.array([np.sin(th)*np.cos(phi),
                        np.sin(th)*np.sin(phi),
                        np.cos(th)])
        a._lighting['light_direction'] = loc
        a._use_frustum = v[8]

    def set_axes3d_viewparam(self, value, a, no_proj=False):
        if len(value) == 2:
            elev, azim = value
        else:
            elev, azim, upvec = value
            a._upvec = upvec
        a.elev = elev
        a.azim = azim
        if not no_proj:
            a.get_proj()
        self.set_bmp_update(False)

    def get_axes3d_viewparam(self, ax):
        return ax.elev, ax.azim, ax._upvec

    def set_axis_bgalpha(self, value, artist=None):
        for a in self._artists:
            a.patch.set_alpha(0.0)
        self._artists[0].patch.set_alpha(value)
        self.setp('axis_bgalpha', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def get_axis_bgalpha(self, artist=None):
        return self._artists[0].patch.get_alpha()

    def set_axis_bgedgealpha(self, value, artist=None):
        for a in self._artists:
            a.patch.set_linewidth(0.0)
        self._artists[0].patch.set_linewidth(value)
        self.setp('axis_bgalpha', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def get_axis_bglinewidth(self, artist):
        return self._artists[0].patch.get_linewidth()

    def set_axis_bglinewidth(self, value, artist=None):
        for a in self._artists:
            a.patch.set_linewidth(value)
        self.setp('axis_bglinewidth', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def get_axis_bglinestyle(self, artist):
        return self._artists[0].patch.get_linestyle()

    def set_axis_bglinestyle(self, value, artist=None):
        for a in self._artists:
            a.patch.set_linestyle(value)
        self.setp('axis_bglinestyle', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def get_axis_bgedgecolor(self, artist=None):
        v1 = self._artists[0].patch.get_edgecolor()
        if v1 != self.getp('axis_bgedgecolor'):
            self.setp('axis_bgedgecolor', v1)
        return v1

    def set_axis_bgedgecolor(self, value, artist=None):
        for a in self._artists:
            a.patch.set_edgecolor((0, 0, 0, 0))
        self._artists[0].patch.set_edgecolor(value)
        self.setp('axis_bgedgecolor', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def get_axis_bgfacecolor(self, artist=None):
        v1 = self._artists[0].patch.get_facecolor()
        if v1 != self.getp('axis_bgfacecolor'):
            self.setp('axis_bgfacecolor', v1)
        return v1

    def set_axis_bgfacecolor(self, value, artist=None):
        alpha = self._artists[0].patch.get_alpha()
        for a in self._artists:
            #            a.set_axis_bgcolor((0,0,0,0))
            a.patch.set_facecolor((0, 0, 0, 0))
            a.patch.set_alpha(0)
        value = list(value)
        if not any(value):
            alpha = 0.0
        if alpha is None:
            alpha = 1.0
        value[3] = alpha
        self._artists[0].patch.set_facecolor(value)
        self._artists[0].patch.set_alpha(value[3])
#        self._artists[0].set_axis_bgcolor(value)
        self.setp('axis_bgfacecolor', value)
        # self.set_3d_pane_alpha([float(value)]*3)

    def set_3d_pane_colorname(self, value):
        a = self.get_3d_pane_coloralpha()
        self._3d_pane_color = self._3d_pane_var(value, a)
        self._set_3d_pane_color(self.get_3d_pane_colorcode())

    def set_3d_pane_alpha(self, a):
        value = self.get_3d_pane_colorname()
        self._3d_pane_color = self._3d_pane_var(value, a)
        self._set_3d_pane_color(self.get_3d_pane_colorcode())

    def get_3d_pane_colorname(self):
        return list(zip(*self._3d_pane_color))[0]

    def get_3d_pane_coloralpha(self):
        return list(zip(*self._3d_pane_color))[1]

    def get_3d_pane_colorcode(self):
        return list(zip(*self._3d_pane_color))[2]

    def _set_3d_pane_color(self, code):
        from ifigure.matplotlib_mod.axes_mod import AxesMod
        from ifigure.matplotlib_mod.axes3d_mod import Axes3DMod

        if len(self._artists) == 0:
            return
        if not isinstance(self._artists[0], Axes3DMod):
            return
        a = self._artists[0]
        a.xaxis.set_pane_color(code[0])
        a.yaxis.set_pane_color(code[1])
        a.zaxis.set_pane_color(code[2])

    def _3d_pane_var(self, value, a):
        from matplotlib.colors import ColorConverter as cc
        return [(value[0], a[0], cc().to_rgba(value[0], alpha=a[0])),
                (value[1], a[1], cc().to_rgba(value[1], alpha=a[1])),
                (value[2], a[2], cc().to_rgba(value[2], alpha=a[2]))]

    def set_ax_pos(self, value, a):
        p = self.get_axis_param(value[0])
        p.tick_position = value[1][0]
        p.tick_both = value[1][1]
        p.box = value[1][2]

        #        a = self.get_axes_artist_by_name(value[0])
        for a in self.get_axes_artist_by_name(value[0]):
            p.set_box(a)
            if value[0].startswith('x'):
                p.set_artist_tickposition(a)
                if p.tick_both:
                    a.xaxis.set_ticks_position('both')
            elif value[0].startswith('y'):
                p.set_artist_tickposition(a)
                if p.tick_both:
                    a.yaxis.set_ticks_position('both')

    def get_ax_pos(self, a, name):
        p = self.get_axis_param(name)
        value = (p.tick_position,
                 p.tick_both,
                 p.box,
                 p.get_artist_tickposition(a))
        return value

    def set_cmap3(self, value, a):
        p = self.get_axis_param(value[0])
        p.set_cmap(value[1])
        for a in self._artists:
            p.set_artist_rangeparam(a)
        self.set_bmp_update(False)
        p.update_cb()

    def get_cmap3(self, value, name):
        p = self.get_axis_param(name)
        value = p.get_cmap()
        return value

    def reset_color_cycle(self):
        from ifigure.matplotlib_mod.mpl_utils import reset_color_cycle
        for a in self._artists:
            reset_color_cycle(a)

    def get_auto_status_str(self):
        area = self.getp('area')
        f = '{:.2f}'
        txt = [f.format(a) for a in area]
        return 'L:' + txt[0] + ' B:'+txt[1]+' W:' + txt[2] + ' H:' + txt[3]

    def convert_to_tex_style_text(self, mode=True):
        from ifigure.utils.cbook import tex_escape_equation
        if len(self._artists) == 0:
            return
        labels = []
        for a in self._artists:
            labels.extend([a.title, a.xaxis.label, a.yaxis.label])
            if self._3D:
                labels.append(a.zaxis.label)
        if mode:
            s_bk = [l.get_text() for l in labels]
            self.setp('s_bk', s_bk)
            for s, l in zip(s_bk, labels):
                l.set_text(tex_escape_equation(str(s)))
        else:
            s_bk = self.getp('s_bk')
            for s, l in zip(s_bk, labels):
                l.set_text(s)


class FigInsetAxes(FigAxes):
    def __init__(self, *args, **kywds):
        #        self.child=[]
        if "draggable" in kywds:
            self.setvar("draggable", kywds["draggable"])
            del kywds["draggable"]
        else:
            self.setvar("draggable", True)

        super(FigInsetAxes, self).__init__(*args, **kywds)

        self.setp("inset_w", 0.45)
        self.setp("inset_h", 0.45)
        self.setp("inset_transform", 'axes')
        self.setp("inset_anchor", (0.05, 0.5))
        self._floating = True

    @property
    def ispickable_a(self):
        return True

    @classmethod
    def isFigInsetAxes(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'insetaxes'

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return super(FigInsetAxes, self).attr_in_file()+["inset_w", "inset_h", "inset_transform", "inset_anchor"]

    @classmethod
    def property_in_palette(self):
        return ["inset_switchtrans", "inset_size"]

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
     #  m=[('Add Plot',     self.onAddPlot, None),
     #     ('Add Contour',  self.onAddContour, None),
     #     ('Add Image',    self.onAddImage, None),
     #     ('---',        None, None),
     #     ('Realize',    self.onRealize, None)]
        return super(FigAxes, self).tree_viewer_menu()

    def isDraggable(self):
        return self._var["draggable"]

    def set_parent(self, parent):
        super(FigInsetAxes, self).set_parent(parent)
        if parent is None:
            return
        if hasattr(parent, 'add_update_client'):
            parent.add_update_client(self)

    def get_container(self):
        #        f_axes = self._parent
        #        return f_axes._parent._artists[0]
        figpage = self.get_figpage()
        return figpage._artists[0]

    def do_update_artist(self):
        #        print 'do-update inset_axes'
        rect, use_def, margin = self.calc_rect()
        for a in self._artists:
            a.set_position(rect)
        self.set_client_update_artist_request()
        if self.has_highlight(self._artists[0]):
            self.highlight_artist(False, artist=[self._artists[0]])
            self.highlight_artist(True, artist=[self._artists[0]])
        self.set_bmp_update(False)

    def get_inset_transform(self, name):
        fig_axes = self._parent
        fig_page = self.get_figpage()

        return self.coordsname2transform(fig_page, name,
                                         fig_axes=fig_axes)

    def convert_transform(self, name1, name2, rect):

        if name1 is not None:
            t1 = self.get_inset_transform(name1)
        else:
            t1 = None
        if name2 is not None:
            t2 = self.get_inset_transform(name2)
        else:
            t2 = None
#        print self._parent._artists[0].get_window_extent().get_points()
        v = self.convert_transform_rect(t1, t2, rect)
        return v

    def calc_rect(self, ignore_pagemargin=False):
        #ignore_pagemargin is not used
        ax_main = self._parent
        rect, use_def, margin = ax_main.calc_rect()
        w = self.getp("inset_w")
        h = self.getp("inset_h")
        anchor = self.getp("inset_anchor")

        rect = [anchor[0], anchor[1], w, h]
        rect = self.convert_transform(
            self.getp("inset_transform"), 'figure', rect)
#        print 'rect', rect
        self._rect = rect
        return rect, use_def, margin

    def set_area(self, area):
        print("inset_axes set_area is called. this might be due to a potential bug.")
        pass

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        if val == True:

            for a in alist:
                box = a.get_window_extent().get_points()
                x = [box[0][0], box[0][0], box[1][0], box[1][0], box[0][0]]
                y = [box[0][1], box[1][1], box[1][1], box[0][1], box[0][1]]
                hl = Line2D(x, y, marker='s',
                            color='k', linestyle='None',
                            markerfacecolor='None',
                            markeredgewidth=0.5,
                            figure=a.figure)
                a.figure.lines.extend([hl])
                a.figobj_hl.append(hl)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    a.figure.lines.remove(hl)
                a.figobj_hl = []
#
#  Hit Test
#

    def get_artist_extent(self, a):
        box = a.get_window_extent().get_points()
        return [box[0][0], box[1][0], box[0][1], box[1][1]]

    def picker(self, a, evt):
        return self.picker_a(a, evt)

    def dragstart_a(self, a, evt, shift=None):
        redraw = super(FigInsetAxes, self).dragstart_a(a, evt)
        if self._drag_hl is not None:
            self._drag_hl.set_linestyle('-')
            self._drag_hl.set_color('r')
            self._drag_hl.set_alpha(0.5)

    def dragdone_a(self, a, evt, shift=None, scale=None):
        redraw = super(FigInsetAxes, self).dragdone_a(a, evt)

        anchor = [min([self._drag_rec[0], self._drag_rec[1]]),
                  min([self._drag_rec[2], self._drag_rec[3]])]
        w = abs(self._drag_rec[0] - self._drag_rec[1])
        h = abs(self._drag_rec[2] - self._drag_rec[3])

        rect = [anchor[0], anchor[1], w, h]
        rect = self.convert_transform(None, self.getp("inset_transform"), rect)

        h = [UndoRedoFigobjMethod(a, 'inset_rect', rect)
             for a in self._artists]
        canvas = evt.guiEvent_memory.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h,
                                                       menu_name='move')
        return True, None

    def scale_artist(self, scale, action=True):
        rect = self.get_inset_rect()
        rect = self.convert_transform(self.getp("inset_transform"), None, rect)
        # this rect is in device coords.
        area = scale_rect([rect[0], rect[0]+rect[2],
                           rect[1], rect[1]+rect[3]], scale)
        rect2 = [min(area[:2]), min(area[2:]), abs(area[1] - area[0]),
                 abs(area[3] - area[2])]
        rect = self.convert_transform(None, self.getp("inset_transform"),
                                      rect2)
        action1 = []
        for a in self._artists:
            action1.append(UndoRedoFigobjMethod(a, 'inset_rect', rect))
        return action1

    def set_inset_rect(self, value, a):
        self.setp('inset_anchor', value[0:2])
        self.setp('inset_w', value[2])
        self.setp('inset_h', value[3])
        self.do_update_artist()

    def get_inset_rect(self, a=None):
        x, y = self.getp('inset_anchor')
        w = self.getp('inset_w')
        h = self.getp('inset_h')
        return [x, y, w, h]

    def set_insetsize(self, value, a):
        v = [float(x) for x in value.split(',')]
        self.set_inset_rect(v, a)

    def get_insetsize(self, a=None):
        return ', '.join([str(x) for x in self.get_inset_rect()])

    def get_switchtrans(self, a):
        return self.getp('inset_transform')

    def set_switchtrans(self, value, a):
        v = str(value)

        w = self.getp("inset_w")
        h = self.getp("inset_h")
        anchor = self.getp("inset_anchor")
        rect = [anchor[0], anchor[1], w, h]

#        print rect
        rect = self.convert_transform(self.getp("inset_transform"), v, rect)
#        print rect
        self.setp("inset_w",  rect[2])
        self.setp("inset_h",  rect[3])
        self.setp("inset_anchor",  rect[0:2])

        return self.setp('inset_transform', v)


class FigColorBar(FigInsetAxes, AdjustableRangeHolderCbar):
    def __init__(self, *args, **kywds):
        super(FigColorBar, self).__init__(*args, **kywds)
        self._generic_axes = False
        self._cbar_image = None
        self._cbclient = []
        self._caxis_param = None
        self.setp("cdir", "v")

        self.setp("inset_w", 0.05)
        self.setp("inset_h", 0.8)
        self.setp("inset_anchor", (0.9, 0.1))
    # ColorBar does not support cursor...

    def generate_cursor(self, evt, idx):
        # called during mouse click in cursor mode
        return []

    @classmethod
    def property_in_palette(self):
        return ["inset_size"]

    def update_cursor(self, evt, idx):
        # called during mousedrag in cursor mode
        pass

    def valid_cursor(self):
        # called just before drawing cursor
        return []

    def canvas_axes_menu(self):
        return []

    def set_caxis_param(self, param):
        self._caxis_param = weakref.ref(param)

    def property_in_palette_axes(self):
        names = [x.name for x in (self._xaxis + self._yaxis)]
        tab = ["common"]+[self._caxis_param().name] + names
        item = [["title", "frame", "axis", ], ]
        item.append(["axcrangeparam13", "axformat"])
        for i in self._xaxis:
            item.append(["axlabel",
                         "axlotsize",
                         "axtlcolor", "axticks",
                         "axxpos"])
        for i in self._yaxis:
            item.append(["axlabel",
                         "axlotsize",
                         "axtlcolor", "axticks", "axypos"])
        return tab, item

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'colorbar.png')
        return [idx1]

    @classmethod
    def get_namebase(self):
        return 'colorbar'

    def destroy(self, clean_owndir=True):
        if self._cbar_image is not None:
            self._cbar_image.remove()
            self._cbar_image = None
        self._caxis_param = None
        super(FigColorBar, self).destroy(clean_owndir=clean_owndir)

    def generate_artist(self, *args, **kywds):
        super(FigColorBar, self).generate_artist(*args, **kywds)
        if self._caxis_param is None:
            return
        self.update_cbar_image()

    def del_artist(self, *args, **kywds):
        if self._cbar_image is not None:
            self._cbar_image.remove()
            self._cbar_image = None
        self.remove_2nd_artist()
        super(FigColorBar, self).del_artist(*args, **kywds)

    def remove_2nd_artist(self):
        if len(self._artists) == 2:
            artist = self._artists[1]
            artist.figobj = None
            artist.figobj_hl = []
            artist.remove()
            self._artists = [self._artists[0]]

    def update_cbar_image(self):
        if self._caxis_param is None:
            return
        dprint2('update_cbar_image')
        array = np.vstack((np.arange(256), np.arange(256)))
        self.set_cbarscale()
        cmesh = self.cmesh()
        if self._cbar_image is not None:
            self._cbar_image.remove()
            self._cbar_image = None

        a = self._artists[0]

        scale = self._caxis_param().scale
        zp = np.vstack((cmesh, cmesh))

        if self.getp('cdir') == 'h':
            self._artists[0].set_ylim((0, 1))
            y = (0, 1)
            a.set_xlim((cmesh[0], cmesh[-1]))
            a.set_autoscalex_on(False)
            a.set_autoscaley_on(False)
            self.set_axtcolor(['y', [0, 0, 0, 0]], a)
            self.set_axlcolor(['y', ([0, 0, 0, 0], [0, 0, 0, 0])], a)
            lc = self._caxis_param().lcolor
            tc = self._caxis_param().tcolor
            self.set_axtcolor(['x', tc], a)
            self.set_axlcolor(['x', (lc, lc)], a)
            extent = [cmesh[0], cmesh[-1], min(y), max(y)]

        elif self.getp('cdir') == 'v':
            x = self._artists[0].set_xlim((0, 1))
            x = (0, 1)
            a.set_ylim((cmesh[0], cmesh[-1]))
            a.set_autoscalex_on(False)
            a.set_autoscaley_on(False)
            zp = np.transpose(zp)
            self.set_axtcolor(['x', [0, 0, 0, 0]], a)
            self.set_axlcolor(['x', ([0, 0, 0, 0], [0, 0, 0, 0])], a)
            lc = self._caxis_param().lcolor
            tc = self._caxis_param().tcolor
            self.set_axtcolor(['y', tc], a)
            self.set_axlcolor(['y', (lc, lc)], a)
            extent = [min(x), max(x), cmesh[0], cmesh[-1]]

        if len(self._artists) > 1:
            self._artists[1].remove()
            self._artists = [self._artists[0], ]
        self.generate_twin_artist()

        self._cbar_image = self._artists[1].imshow(zp,
                                                   extent=extent,
                                                   interpolation='bicubic',
                                                   resample=True,
                                                   aspect='auto',
                                                   origin='lower')
        self._cbar_image.nozsort = True
        self.call_set_crangeparam_to_artist(self._caxis_param())

        if self._caxis_param().cmap is not None:
            self._cbar_image.set_cmap(self._caxis_param().cmap)

    def generate_twin_artist(self):
        if self.getp('cdir') == 'v':
            artist = self._artists[0].twinx()
            artist.yaxis.set_major_locator(mticker.NullLocator())
            artist.yaxis.set_major_formatter(mticker.NullFormatter())
        else:
            artist = self._artists[0].twiny()
            artist.xaxis.set_major_locator(mticker.NullLocator())
            artist.xaxis.set_major_formatter(mticker.NullFormatter())
        artist.figobj = self
        artist.figobj_hl = []
        artist.set_zorder(self.getp('zorder'))
        self._artists.append(artist)

    def set_update_cbar_image(self, value, a):
        self.update_cbar_image()

    def get_update_cbar_image(self, a):
        pass

    def set_cbarscale(self):
        if self._caxis_param is None:
            return
        scale = self._caxis_param().scale
        a = self._artists[0]
        a.set_yscale('linear')
        a.set_xscale('linear')
        if scale == 'log':
            if self.getp('cdir') == 'v':
                a.set_yscale('log')
            else:
                a.set_xscale('log')
        elif scale == 'symlog':
            th = self._caxis_param().symloglin
            range = self._caxis_param().range

            if self.getp('cdir') == 'v':
                a.set_ylim(range)
                if isMPL33:
                    a.set_yscale('symlog', linthresh=th)
                else:
                    a.set_yscale('symlog', linthreshy=th)
            else:
                a.set_xlim(range)
                if isMPL33:
                    a.set_xscale('symlog', linthresh=th)
                else:
                    a.set_xscale('symlog', linthreshx=th)
        if self.getp('cdir') == 'v':
            p = self.get_axis_param('y')
        else:
            p = self.get_axis_param('x')
        p.scale = scale

    def cmesh(self):
        param = self._caxis_param()
        cmin, cmax = param.range
        scale = param.scale

        if scale == 'linear':
            cmesh = np.linspace(cmin, cmax, 256)
        elif scale == 'symlog':
            cmesh = np.linspace(cmin, cmax, 256)
        else:
            #
            cmin = cmin if cmin > 0.0 else cmax*1e-16
            cmesh = np.linspace(cmin, cmax, 256)

        return cmesh

    def canvas_menu(self):
        return [("Colormap...",  self.onColormap, None),
                ("Clipping...",  self.onClip, None),
                ("Auto Scale C",  self.onAutoC, None),
                ("Switch Direction",  self.onDir, None)]

    def onDir(self, evt=None):
        if self.getp('cdir') == 'v':
            value = 'h'
        else:
            value = 'v'

        h = [UndoRedoFigobjMethod(self._artists[0], 'cbardir',
                                  value)]
        canvas = evt.GetEventObject()
        window = canvas.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h,
                                                       menu_name='cbar direction')

    def set_cbardir(self, value, a):
        pvalue = self._caxis_param().get_rangeparam()
        lim = pvalue[2]
        if value == 'v':
            self.setp('cdir', value)
#           self._ycolor=(self.get_ytcolor(self._artists[0]),
#                         self.get_ylcolor(self._artists[0]))
            self._artists[0].set_ylim((0, 1))
            self._artists[0].set_xlim(lim)
        elif value == 'h':
            self.setp('cdir', value)
            self._artists[0].set_xlim((0, 1))
            self._artists[0].set_ylim(lim)
        self.remove_2nd_artist()
        self.update_cbar_image()
        ifigure.events.SendPVDrawRequest(self)

    def get_cbardir(self, a):
        return self.getp('cdir')

    def onAutoC(self, evt):
        canvas = evt.GetEventObject()
        canvas.set_axes_selection(self._parent._artists[0])
        self.hndl_dclick(canvas)

    def onClip(self, evt):
        if self._caxis_param is None:
            return

        ca = self._caxis_param()
        canvas = evt.GetEventObject()
        l = [["", "Clip Setting", 2],
             ["Under", ca.clip[0], 3006, ({"text": "Clip"}, {})],
             ["Over", ca.clip[1], 3006, ({"text": "Clip"}, {})]]
        tip = None
        value = DialogEditList(l, tip=tip, parent=canvas,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        if value[0]:
            artist = self._artists[0]
            actions = [UndoRedoFigobjMethod(artist,
                                            'clip', (value[1][1], value[1][2]))]
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(actions)

#            ca.clip = (value[1][1], value[1][2])
#            for a in self._parent._artists:
#                ca.set_artist_rangeparam(a)
#            self._parent.set_bmp_update(False)
#            canvas.draw()

    def set_clip(self, value, a0):
        ca = self._caxis_param()
        ca.clip = value
        for a in self._parent._artists:
            ca.set_artist_rangeparam(a)
        self._parent.set_bmp_update(False)

    def get_clip(self, a):
        ca = self._caxis_param()
        return ca.clip

    def set_axcrangeparam13(self, value, a0):
        return self._parent.set_axrangeparam13(value, a0)

    def get_axcrangeparam13(self, a, name):
        return self._parent.get_axrangeparam13(a, name)

    def onColormap(self, evt):
        ca = self._caxis_param()
        canvas = evt.GetEventObject()

        name = ca.cmap
        if name.endswith('_r'):
            s = {"reverse": True}
        else:
            s = {"reverse": False}
        l = [["", name, 11, s]]
        value = DialogEditList(l, tip=None, parent=canvas)
        if value[0]:
            artist = self._artists[0]
            actions = [UndoRedoFigobjMethod(artist,
                                            'cmap', value[1][0])]
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(actions)

    def set_cmap(self, value, a0):
        ca = self._caxis_param()
        ca.cmap = value
        self._cbar_image.set_cmap(ca.cmap)
        self.call_set_crangeparam_to_artist(ca)

        for a in self._parent._artists:
            ca.set_artist_rangeparam(a)
        self._parent.set_bmp_update(False)
        self.set_bmp_update(False)

    def get_cmap(self, a0):
        ca = self._caxis_param()
        return ca.cmap

    def call_set_crangeparam_to_artist(self, ca):
        scale = ca.scale
        ca.scale = 'linear'
        ca.set_crangeparam_to_artist(self._cbar_image, check=False)
        ca.scale = scale

    def handle_axes_change(self, data):
        #        print 'handle_axes_change'
        evtTD = data['td']
#        hist = self.get_root_parent().app.history
        dprint2('handle_axes_changed in cbar')
        if evtTD == self:
            return
        else:
            self.update_cbar_image()
            self.set_bmp_update(False)

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        m = []
        return m+super(FigAxes, self).tree_viewer_menu()

    def hndl_dclick(self, canvas):
        '''
        called when user double click the fig_axes
           1) make a dummy request to make axes
           3) make a new request similar to range zoom 
        '''
        canvas.set_axes_selection(self._parent._artists[0])
        x = self._caxis_param()
        value = x.get_rangeparam()
        value[1] = True
        request = [(x.name, value)]
        requests = {
            self._parent: self._parent.compute_new_range(request=request)}
        requests = canvas.expand_requests(requests)
        canvas.send_range_action(requests, 'color range')

    def save_data2(self, data):
        data = super(FigColorBar, self).save_data2(data)

        index = self._parent._caxis.index(self._caxis_param())
        cbdata = {"caxisparam_index": index}
        data['FigColorBar'] = (1, cbdata)

        return data

    def load_data2(self, data):
        if 'FigColorBar' in data:
            cbdata = data["FigColorBar"][1]
            self._loaded_cbdata = cbdata
        return super(FigColorBar, self).load_data2(data)

    def init_after_load(self, olist, nlist):
        if hasattr(self, '_loaded_cbdata'):
            cbdata = self._loaded_cbdata
            if "caxisparam_index" in cbdata:
                k = cbdata["caxisparam_index"]
                self.set_caxis_param(self._parent._caxis[k])
            del self._loaded_cbdata

    def _get_caxis(self):
        if self.getp("cdir") == 'v':
            axis = a.get_yaxis()
        else:
            axis = a.get_xaxis()
        return axis

    def set_adjustrange(self, *args):
        pass

    def get_adjustrange(self, *args):
        pass

    # format
    def set_axformat(self, param, a):
        ca = self._caxis_param()
        ca.format = param[1]
        cdir = self.getp('cdir')
        if cdir == 'v':
            name = 'y'
        else:
            name = 'x'
        p = self.get_axis_param(name)
        p.format = param[1]
        p.set_ticks(self.get_axes_artist_by_name(name)[0])
        # p.set_ticks(self.get_axes_artist_by_name(param[0])[0])
        self.set_bmp_update(False)

    def get_axformat(self, a, name):
        ca = self._caxis_param()
        return ca.format
