from __future__ import print_function
#  Name   :fig_page
#
#          this class to manage matplotlib.figure
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

from ifigure.matplotlib_mod.figure_mod import FigureMod as Figure
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_axes import FigAxes
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import wx
import weakref
import ifigure.utils.cbook as cbook
import ifigure.events

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigPage')

frameart_zbase = -100000  # a big number so that it is draw first.


class FigPage(FigObj):
    def __init__(self, figsize=(0.15, 0.1), dpi=72, src=None,
                 *args, **kywds):
        # list of page obj
        # this is for text, suptitle, and legend
        ###  placed in figure
        self.figobj = []
        super(FigPage, self).__init__()
        # left, righ, top, bottom (fraction of rect)
        self.setp("def_margin", [0.15, 0.1, 0.15, 0.15])
        self.setp("figsize", figsize)
        self.setp("dpi", dpi)
        self.setp("args", args)
        self.setp("kywds", kywds)
        self.setp("suptitle_labelinfo",  ['', 'black', 'default',
                                          'default', 'default', 'default'])

        self.setp("suptitle", '')
        self.setp("suptitle_size", 14)
        self.setp("title_size", 12)
        self.setp("ticklabel_size", 12)
        self.setp("axeslabel_size", 12)
        self.setp("axesbox_width",  1.0)
        self.setp("axestick_width",  1.0)
        self.setp("tick_font", 'sans-serif')
        self.setp("tick_weight", 'roman')
        self.setp("tick_style", 'normal')
        self.setp("title_font", 'sans-serif')
        self.setp("title_weight", 'roman')
        self.setp("title_style", 'normal')
        self.setp("nticks", [7, 7, 7])

        self._title_artist = None
        self._resize_cb = weakref.WeakSet()
        self._pan_cb = []
        self._zoom_cb = []
        self._nomargin = False
        self._page_margin = [0., 0., 0., 0.]  # left right bottom top?
        self._last_draw_size = (-1, -1)

    @classmethod
    def isFigPage(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'page'

    @classmethod
    def property_for_shell(self):
        return ["bgcolor", "page_title_size", "page_ticklabel_size", "page_axeslabel_size",
                "page_axesbox_width", "page_axestick_width", ]

    def can_have_child(self, child=None):
        from ifigure.mto.fig_book import FigBook
        if child is None:
            return True
        if isinstance(child, FigPage):
            return False
        if isinstance(child, FigBook):
            return False
        return True

    @classmethod  # define _attr values to be saved
    def property_in_file(self):
        return (['facecolor', 'figwidth', 'figheight'] +
                super(FigPage, self).property_in_file())

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ["tick_font", "tick_weight", "tick_style", "nticks",
                "title_font", "title_weight", "title_style",
                "ticklabel_size", "axeslabel_size",
                "def_margin", "axestick_width", "axesbox_width",
                "axestick_width", "suptitle_labelinfo", "figsize"]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'page.png')
        return [idx1]

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if key == wx.WXK_RETURN:
            return self.onShow
        return None

    def realize(self):
        if not self._suppress:
            from ifigure.mto.fig_axes import FigAxes
            from ifigure.mto.figobj_gpholder import FigObjGPHolder
            self.generate_artist()
            axes = [o for o in self.walk_tree() if isinstance(o, FigAxes)]
            o1 = [o for o in self.walk_tree() if (not isinstance(o, FigAxes) and
                                                  not isinstance(o, FigObjGPHolder))]
            o2 = [o for o in self.walk_tree() if isinstance(o, FigObjGPHolder)]
            oo = [o for o in axes + o1 + o2 if o is not self]

            for o in oo:
                o.generate_artist()
        else:
            if not self.isempty():
                self.del_artist(delall=True)
            for objname, figobj in self.get_children():
                figobj.realize()

    def realize_children(self):
        for objname, figobj in self.get_children():
            figobj.realize(realize_gpholder='non_gp')

        for objname, figobj in self.get_children():
            figobj.realize(realize_gpholder='gp')

        #from ifigure.mto.figobj_gpholder import FigObjGPHolder

        # not_gp_holder = [figobj for objname, figobj in self.get_children()
        #                 if not isinstance(figobj, FigObjGPHolder)]

        # gp_holder = [figobj for objname, figobj in self.get_children()
        #             if isinstance(figobj, FigObjGPHolder)]

        # for figobj in not_gp_holder:
        #    figobj.realize()

        # for figobj in gp_holder:
        #    figobj.realize()

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        if self.isempty():
            dprint2("generatieng figure")
            artist = Figure(figsize=self.getp("figsize"),
                            dpi=self.getp("dpi"),
                            *(self.getp("args")),
                            **(self.getvar("kywds")))
            self._artists.append(artist)
            self._title_artist = artist.suptitle('')
            artist.figobj = self
            artist.figobj_hl = []
            if self.hasp("loaded_property"):
                lp = self.getp("loaded_property")
                if len(lp) > 0:
                    self.set_artist_property(self._artists[0], lp[0])
                self.delp("loaded_property")

            # set suptitle
            info = self.getp('suptitle_labelinfo')
            self.set_suptitle(info[0],
                              size=info[-1],
                              color=info[1])

    def del_artist(self, artist=None, delall=False):

        if delall:
            alist = self._artists
        else:
            alist = artist

        if self._title_artist is not None:
            self._artists[0].texts.remove(self._title_artist)
            self._title_artist.figure = None
            self._title_artist = None

        self.store_loaded_property()

        if len(alist) == len(self._artists):
            for name, child in self.get_children():
                child.del_artist(delall=True)

        super(FigPage, self).del_artist(alist, delall=delall)

    def add_axes(self, name=None, *args, **kywds):
        fig_axes = FigAxes(*args, **kywds)
        if name is None:
            name = self.get_next_name("axes")

        fig_axes.setp("margin", self.getp("def_margin"))
        self.add_child(name, fig_axes)
        return self.get_iaxes(fig_axes)

    def del_axes(self, fig_axes):
        fig_axes.destroy()

    def get_iaxes(self, ax):
        c = 0
        for name, child in self.get_children():
            if isinstance(child, FigAxes):
                if ax is child:
                    return c
                c = c + 1
        for child in self.walk_tree():
            if isinstance(child, FigAxes):
                if child._floating and child._generic_axes:
                    if ax is child:
                        return c
                    c = c + 1

    def get_axes(self, iax=None):
        # if iax is None: return all axes
        # in this case, returned list is
        # the same as get_children: (name, obj)
        c = 0
        if iax is None:
            return [x for x in self.get_children()
                    if isinstance(x[1], FigAxes)]

        for name, child in self.get_children():
            if isinstance(child, FigAxes):
                if c == iax:
                    return child
                c = c + 1
        for child in self.walk_tree():
            if isinstance(child, FigAxes):
                if child._floating and child._generic_axes:
                    if c == iax:
                        return child
                    c = c + 1
        return None

    def i_axes(self, ax):
        return self.get_iaxes(ax)

    def num_axes(self, include_floating=False):
        c = 0
        for name, child in self.get_children():
            if isinstance(child, FigAxes):
                c = c + 1
        if not include_floating:
            return c
        for child in self.walk_tree():
            if isinstance(child, FigAxes):
                if child._floating and child._generic_axes:
                    c = c + 1
        return c

    def walk_axes(self):
        c = 0
        for name, child in self.get_children():
            if isinstance(child, FigAxes):
                yield child

    def reset_axesbmp_update(self):
        figure = self._artists[0]
        for a in figure.axes:
            if (hasattr(a, 'figobj') and
                    a.figobj is not None):
                a.figobj.set_bmp_update(False)

    def set_bmp_update(self, value):
        # all axes will be updated
        # currently it is called when page default size are chagned.
        if len(self._artists) == 0:
            return
        if not value:
            self.reset_axesbmp_update()

    def set_area(self, areas):
        naxes = self.num_axes()
        fa = self.get_axes()
        narea = len(areas)
        if naxes > narea:
            for k in range(narea, naxes):
                dprint1('deleting '+str(fa[k][1]))
                self.del_axes(fa[k][1])

        i_r = 0
        for area in areas:
            if i_r < naxes:
                ax = fa[i_r][1]
                ax.set_area(area)
            else:
                iax = self.add_axes(area=area)
                ax = self.get_axes(iax)
                if self.isempty():
                    self.realize()
                ax.realize()
            i_r = i_r+1

    def get_area(self):
        return [o.getp("area") for o in self.walk_axes()]

    def set_def_margin(self, value, a=None):
        self.setp("def_margin", value[:])
        for f_axes in self.walk_axes():
            f_axes.set_area(f_axes.get_area())

    def get_def_margin(self, a=None):
        return self.getp("def_margin")[:]

    def set_page_margin(self, value, a=None):
        self._page_margin = value[:]
        for f_axes in self.walk_axes():
            f_axes.set_area(f_axes.get_area())

    def get_page_margin(self, a=None):
        return self._page_margin[:]

    def set_section(self, *args, **kargs):
        # utility to split a page
        def merge(a, b):
            def feq(a, b):
                th = 1e-5
                return abs(a-b) < th
            if (feq(a[3], b[3]) and feq(a[1], b[1])):  # horizontal merge
                if feq(a[0]+a[2], b[0]):
                    return [a[0], a[1], a[2]+b[2], a[3]]
                if feq(b[0]+b[2], a[0]):
                    return [b[0], a[1], a[2]+b[2], a[3]]
            if (feq(a[2], b[2]) and feq(a[0], b[0])):  # vertical merge
                if feq(a[1]+a[3], b[1]):
                    return [a[0], a[1], a[2], a[3]+b[3]]
                if feq(b[1]+b[3], a[1]):
                    return [a[0], b[1], a[2], a[3]+b[3]]
            return None

        def check_d(a, lim):
            if (not isinstance(a, list) and
                    not isinstance(a, tuple)):
                a = [a]
            if len(a) != lim-1:
                print("number of dx (or dy) should be nrow-1 (or nnoc-1)")
                return None
            if sum(a) > 1 or sum(a) < 0:
                print("dx (or dy) is too large or too small")
                return None
            a.append(1.-sum(a))
            return a
        nrow = 1
        ncol = 1
        asym = []
        if (isinstance(args[0], list) or
                isinstance(args[0], tuple)):
            ncol = len(args[0])
            nrow = args[0]
        else:
            if len(args) > 0:
                nrow = args[0]
            if len(args) > 1:
                ncol = args[1]
            if len(args) > 2:
                asym = args[2:]
            nrow = [nrow]*ncol

        if nrow[0] == 0:
            self.set_area([])
            return

        dx = [1./ncol]*ncol
        dy = [[1./nrow[k]]*nrow[k] for k in range(ncol)]

        if 'dx' in kargs:
            dx = check_d(kargs["dx"], ncol)
            if dx is None:
                return
        if 'dy' in kargs:
            dy = check_d(kargs["dy"], nrow[0])

        areas0 = []
        for i in range(ncol):
            for j in range(nrow[i]):
                if i == 0:
                    x0 = 0
                else:
                    x0 = sum(dx[:i])
                if j == 0:
                    y0 = 1. - dy[i][0]
                else:
                    y0 = 1. - sum(dy[i][:j+1])
                areas0.append([x0, y0, dx[i], dy[i][j]])

        flag = [1]*len(areas0)
        mareas0 = []

        for a in asym:
            if max(a) > len(flag)-1:
                print('incorrect index for merge')
                return
            if min(a) < 0:
                print('incorrect index for merge')
                return
            if flag[a[0]] == 0:
                print('area is already merged')
                return
            marea = areas0[a[0]]
            flag[a[0]] = 0
            for b in a[1:]:
                if flag[b] == 0:
                    print('area is already merged')
                    return
                flag[b] = 0
                marea = merge(marea, areas0[b])
                if marea is None:
                    print('failed to merge area')
                    return
            mareas0.append(marea)

        areas = [areas0[i] for i in range(len(areas0)) if flag[i] == 1]
        for m in mareas0:
            areas.append(m)

        self.set_area(areas)
        if 'sort' in kargs:
            if (kargs['sort'] == 'col' or
                kargs['sort'] == 'column' or
                    kargs['sort'] == 'c'):
                #                print(('self.sort_axes_col',self.sort_axes_col))
                self.sort_axes_col()
            elif (kargs['sort'] == 'row' or
                  kargs['sort'] == 'r'):
                self.sort_axes_row()

#
#   mene in tree viewer
#
    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        if self.num_axes() == 0:
            m = ('Add Axes',   self.onAddAxes, None)
        else:
            m = ('-Add Axes',   self.onAddAxes, None)
        if self.get_figbook().isOpen:
            me = ('Show Page',      self.onShow,    None)
        else:
            me = ('-Show Page',      self.onShow,    None)
        return [m, me,
                ('---',   None, None),
                ('Realize',   self.onRealize, None),
                ('---',   None, None)] + \
            super(FigPage, self).tree_viewer_menu()

    def onRealize(self, e):
        self.realize()
        ifigure.events.SendPVDrawRequest(self)
 #      self.onForceUpdate(e)

    def onAddAxes(self, e):
        self.add_axes()
        self.realize()
        self.set_area([[0, 0, 1, 1]])
        ifigure.events.SendPVAddFigobj(self)
        e.Skip()
#       self.onForceUpdate(e)

    def onShow(self, e):
        id = e.GetEventObject()
        ifigure.events.SendShowPageEvent(self, id)

#    def onDelete(self, e):
#        super(FigPage, self).onDelete(e)
#       return

#       app=self.get_root_parent().app

#       pbook=(self.get_root_parent()).pbook
#       if pbook is not self.get_parent():
        # easy case...
#          self.destroy()
#          e.Skip()
#       else:
        # show correct page to canvas..
#          npage, ipage=self.get_nipage()
#          cpage=self.get_parent().get_page(app.ipage)
#          print cpage
#          if cpage is self:
#             new_ipage = min([app.ipage, npage-2])
#             app.show_page(new_ipage)
#             self.destroy()
#          else:
#             self.destroy()
#             npage, ipage=cpage.get_nipage()
#             app.show_page(ipage)
#       e.Skip()

    def get_nipage(self):
        # return i_page and num_page of self
        npage = 0
        ipage = 0
        for name, child in self.get_parent().get_children():
            try:
                if child is self:
                    ipage = npage
                if child.isFigPage():
                    npage = npage+1
            except Exception:
                pass
        return npage, ipage

    def onResize(self, evt):
        if not self.isempty():
            self.setp('figsize', (self._artists[0].get_figwidth(),
                                  self._artists[0].get_figheight()))
        for obj in self._resize_cb:
            obj.onResize(evt)

    def onZoom(self, evt, figaxes):
        for ref in self._zoom_cb:
            if ref() is not None:
                ref().onZoom(evt, figaxes)

    def onPan(self, evt, figaxes):
        for ref in self._pan_cb:
            if ref() is not None:
                ref().onPan(evt, figaxes)

    def add_resize_cb(self, figobj):
        #        if figobj in [cb() for cb in self._resize_cb]: return
        self._resize_cb.add(figobj)

    def rm_resize_cb(self, figobj):
        if figobj in self._resize_cb:
            self._resize_cb.remove(figobj)
#        self._resize_cb = [x for x in self._resize_cb if x() is not figobj]

    def set_nomargin(self, value):
        from ifigure.mto.fig_axes import FigInsetAxes
        self._nomargin = value
        for figaxes in self.walk_axes():
            if not isinstance(figaxes, FigInsetAxes):
                figaxes.apply_nomargin_mode()
                figaxes.set_bmp_update(False)

    def get_nomargin(self):
        return self._nomargin

    def set_suptitle(self, txt, a=None, size=None, color=None):
        info = self.getp('suptitle_labelinfo')
        info[0] = txt
        if size is not None:
            info[-1] = size
        if color is not None:
            info[1] = color
        if self._title_artist is not None:
            self._title_artist.set_text(txt)
            if info[-1] != 'default':
                self._title_artist.set_size(info[-1])
            if info[1] != 'default':
                self._title_artist.set_color(info[1])

    def get_suptitle(self, a=None):
        info = self.getp('suptitle_labelinfo')
#        if self._title_artist is not None:
#            info[0] = self._title_artist.get_text()
        return info[0]

    def set_suptitle_size(self, s, a=None):
        info = self.getp('suptitle_labelinfo')
        info[5] = s
        if self._title_artist is not None:
            self._title_artist.set_size(float(s))

    def get_suptitle_size(self, a=None):
        info = self.getp('suptitle_labelinfo')
        return info[5]

    def _set_textprop(self, value, a):
        a.set_text(value[0])
        a.set_color(value[1])
        a.set_family(value[2])
        a.set_weight(value[3])
        a.set_style(value[4])
        a.set_size(float(value[5]))

    def _get_textprop(self, a):
        return [a.get_text(),
                a.get_color(),
                a.get_family()[0],
                a.get_weight(),
                a.get_style(),
                str(a.get_size())]

    def set_suptitle_labelinfo(self, value, a=None):
        tinfo = self.getp('suptitle_labelinfo')

        tfont = self.getp('title_font')
        tweight = self.getp('title_weight')
        tstyle = self.getp('title_style')
        tsize = self.getp('title_size')

        v2 = [x for x in value]
        if str(value[2]) == 'default':
            v2[2] = tfont
        if str(value[3]) == 'default':
            v2[3] = tweight
        if str(value[4]) == 'default':
            v2[4] = tstyle
        if str(value[5]) == 'default':
            v2[5] = tsize

        if self._title_artist is not None:
            self._set_textprop(v2, self._title_artist)
        self.setp('suptitle_labelinfo', value)

    def get_suptitle_labelinfo(self, a=None):
        return [x for x in self.getp('suptitle_labelinfo')]

    def postprocess_mpltext_edit(self):
        '''
        called after text is edited interactively
        this allows to load mpl text data to figobj
        '''
        info = self.getp('suptitle_labelinfo')
        if self._title_artist is not None:
            info[0] = self._title_artist.get_text()

    def sort_axes_col(self):
        '''
        sort is done by using left top conner
        '''
        l = [(int((a.getp('area')[0])*30),
              int((a.getp('area')[1] + a.getp('area')[3])*30),
              a) for a in self.walk_axes()]
        cols = [int((a.getp('area')[0])*30)
                for a in self.walk_axes()]
        idx = 0
        for col, c in enumerate(sorted(set(cols))):
            el = [item[2] for item in l if item[0] == c]
            l2 = [(int((a.getp('area')[1] + a.getp('area')[3])*30),
                   a) for a in el]
            for row, item in enumerate(reversed(sorted(l2))):
                id1 = self.i_child(item[1])
                self.move_child(id1, idx)
                idx = idx+1

    def sort_axes_row(self):
        '''
        sort is done by using left top conner
        '''
        l = [(int((a.getp('area')[0])*30),
              int((a.getp('area')[1] + a.getp('area')[3])*30),
              a) for a in self.walk_axes()]
        rows = [int((a.getp('area')[1] + a.getp('area')[3])*30)
                for a in self.walk_axes()]
        idx = 0
        for row, c in enumerate(reversed(sorted(set(rows)))):
            el = [item[2] for item in l if item[1] == c]
            l2 = [(int((a.getp('area')[0])*30),
                   a) for a in el]
            for col, item in enumerate(sorted(l2)):
                id1 = self.i_child(item[1])
                self.move_child(id1, idx)
                idx = idx+1


# save/load
#    def _do_save_data(self, fid=None):
#        print "saving fig_page data"


    def save_data2(self, data):
        # the first element is version code
        param = {"_page_margin": self._page_margin,
                 "_nomargin": self._nomargin}
        data['FigPage'] = (1, self.getp(), param)
        data = super(FigPage, self).save_data2(data)
        return data

    def load_data2(self, data):
        self.handle_loaded_figobj_data(data, 'FigPage')
        super(FigPage, self).load_data2(data)

    def set_figure_dpi(self, value):
        if len(self._artists) == 0:
            self.realize()
        self._artists[0].set_dpi(value)

    def get_figure_dpi(self):
        return self._artists[0].get_dpi()

    def set_viewer_samerange_mode(self, value, a):
        viewer = self.get_root_parent().app.find_bookviewer(self.get_figbook())
        viewer.set_use_samerange(value)

    def get_viewer_samerange_mode(self, a):
        viewer = self.get_root_parent().app.find_bookviewer(self.get_figbook())
        return viewer.get_use_samerange()

    def set_nticks(self, *args):
        '''
        set page default nticks
        '''
        changed = False
        for k, value in enumerate(args):
            if self.getp('nticks')[k] != value:
                self.getp('nticks')[k] = value
                changed = True
        if not changed:
            return
        for ax in self.walk_axes():
            ax.refresh_nticks()

    def convert_to_tex_style_text(self, mode=True):
        from ifigure.utils.cbook import tex_escape_equation
        if self._title_artist is None:
            return
        if mode:
            s = self._title_artist.get_text()
            self.setp('suptitle', s)
            self._title_artist.set_text(tex_escape_equation(str(s)))
        else:
            s = self.getp('suptitle')
            self._title_artist.set_text(s)

    def add_frameart(self, figobj):
        z = figobj.get_zorder()
        figobj.set_zorder(z + frameart_zbase)

    def rm_frameart(self, figobj):
        z = figobj.get_zorder()
        figobj.set_zorder(z - frameart_zbase)
