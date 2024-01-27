
__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

from ifigure.utils.debug import dprint

from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_page import FigPage
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.utils.cbook as cbook
import ifigure.utils.geom as geom
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
import matplotlib
import matplotlib.path
from matplotlib.patches import PathPatch

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder
from ifigure.mto.figobj_gpholder import FigObjGPHolder
from ifigure.utils.args_parser import ArgsParser
import matplotlib.transforms as mpltransforms

num_gp = 2


class FigArrow(FigObjGPHolder):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._drag_backup = None
            obj._drag_mode = 0  # 1 transpose 2 expand 3 rotate
            obj._drag_start = None
            return obj

        if 'src' in kywds:
            obj = FigObjGPHolder.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            obj.setvar('clip', True)  # backword compatiblity should come here
            return obj

        p = ArgsParser()
        p.add_opt('x1', 0.0, ['number', 'dynamic'])
        p.add_opt('y1', 0.0, ['number', 'dynamic'])
        p.add_opt('x2', 1.0, ['number', 'dynamic'])
        p.add_opt('y2', 1.0, ['number', 'dynamic'])
        # special note
        # positions are first moved to _attr and then transferred
        # to gp point.
        # _attr['x1','y1'...] will not be saved.
        # Is it the best way? Also, are others such as done in
        # the same way?
        # Positions are managed by gp. So perhaps, this is not the
        # correct way....

        # attempting to clean this complexty (2014. 07/31)
        # [x1, x2,,] is not transferred to _attr
        # _eval_xy always return the value using getvar
        ###
        p.add_key('width', 1.0)
        p.add_key("arrowstyle", '-|>,head_length=10,head_width=5')
        p.add_key("clip", True)
        p.add_key("trans", ["figure", "figure"]*num_gp)
        p.add_key("transaxes", ["default"]*num_gp)
        p.add_key('draggable', True)

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        if isinstance(v['trans'], str):
            v['trans'] = [v['trans'], ]*num_gp*2

        obj = FigObjGPHolder.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in v:
            obj.setvar(name, v[name])

        if not 'facecolor' in kywds:
            kywds['facecolor'] = 'k'
        if not 'edgecolor' in kywds:
            kywds['edgecolor'] = 'k'
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args,  **kywds):
        '''
        Arrow object:
        '''
        self._cb_added = False

        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")

        GenericPointsHolder.__init__(self, num=2)
        super(FigArrow, self).__init__(*args, **kywds)

    @classmethod
    def isFigArrow(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'arrow'

    @classmethod
    def property_in_file(self):
        return ["facecolor", "edgecolor", "alpha", "zorder"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return (["arrowstyle", "clip"] +
                super(FigArrow, self).attr_in_file())

    @classmethod
    def property_in_palette(self):
        return ["arrow", "patch"], [["arrowstyle"],
                                    ["facecolor", "edgecolor", "alpha"]]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'arrow.png')
        return [idx1]

    def get_containter(self):
        return self.get_figpage()._artists[0]

#    def set_parent(self, parent):
#        FigObj.set_parent(self, parent)
#        GenericPointsHolder.set_gp_figpage(self)

    def canvas_menu(self):
        def onClipTextByAxes(evt, figobj=self):
            action1 = UndoRedoFigobjProperty(figobj._artists[0],
                                             'clip', not self.getp('clip'))
            window = evt.GetEventObject().GetTopLevelParent()
            hist = GlobalHistory().get_history(window)
            hist.make_entry([action1], menu_name='clipping')

        dprint('arrow_dragmode', self._drag_mode)
        if self._drag_mode == 1:
            m = self.gp_canvas_menu(self.get_gp(0))
        elif self._drag_mode == 2:
            m = self.gp_canvas_menu(self.get_gp(1))
        else:
            m = self.gp_holder_canvas_menu()

        if self.get_figaxes() is not None:
            if self.getp('clip'):
                txt = "^Clip by axes"
            else:
                txt = "*Clip by axes"
            m.extend([(txt, onClipTextByAxes, None), ])
        return m

    def isDraggable(self):
        return self._var["draggable"]

    def args2var(self):
        names0 = self.attr_in_file()
#        names  = ["x1","y1", "x2", "y2"]
#        use_np = [False]*4
        names = []
        use_np = []
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)

        self.set_gp_by_vars()

        x = values[0]
        y = values[1]
        if x is None:
            return False
        if y is None:
            return False
#        if (x.size != 1) or (y.size != 1):
#            self.setp("x", None)
#            self.setp("y", None)
#            return False
        return True

    def generate_artist(self):
        if self.isempty() is False:
            return

        lp = self.getp("loaded_property")

        # this will take care of use_var
        x1, y1, x2, y2 = self._eval_xy()
#        self._eval_xy()

        ###
        if lp is None:
            if x1 is not None:
                self.set_gp_point(0, x1, y1)
                self.set_gp_point(1, x2, y2)

#        if self.hasp("loaded_property"):
#            lp = self.getp("loaded_property")
#            while self.num_gp() < 2:
#            self.add_gp(GenericPoint(0,0,trans='figure'))
#            self.set_gp_figpage()
#            self.get_gp(0).dict_to_gp(lp[-1][0], self)
#            self.get_gp(1).dict_to_gp(lp[-1][1], self)

        a = self.make_newartist()
#        if self.hasp("loaded_property"):
#           self.set_artist_property(a, lp[0])
#           self.delp("loaded_property")
#
        if not self._cb_added:
            fig_page = self.get_figpage()
            fig_page.add_resize_cb(self)
            self._cb_added = True

    def onResize(self, evt):
        self.refresh_artist()

    def do_update_artist(self):
        self.refresh_artist()

    def make_newartist(self):
        self.check_loaded_gp_data()
        width = self.getp("width")
        arrowstyle = self.getp("arrowstyle")
        x1, y1 = self.get_gp(0).get_device_point()
        x2, y2 = self.get_gp(1).get_device_point()

        from matplotlib.transforms import IdentityTransform
        trans = IdentityTransform()
        styles = matplotlib.patches.ArrowStyle.get_styles()
        kywds = self.getvar('kywds')
        a = matplotlib.patches.FancyArrowPatch(posA=(x1, y1),
                                               posB=(x2, y2),
                                               connectionstyle='arc3',
                                               arrowstyle=arrowstyle, mutation_scale=1,
                                               transform=trans,
                                               **kywds)
        lp = self.getp("loaded_property")
        if lp is not None:
            self.set_artist_property(a, lp[0])
            self.delp("loaded_property")
        a.figobj = self
        a.figobj_hl = []
        a.set_zorder(self.getp('zorder'))
        self.add_artists(a)
        container = self.get_container()

        # this section works only when after artists are added
        if self.get_figaxes() is not None and self.getp('clip'):
            bbox = mpltransforms.Bbox.from_extents(
                container.get_window_extent().extents)
            try:
                self._artists[0].set_clip_box(bbox)
                # print self._artists[0].get_clip_box()
                self._artists[0].set_clip_on(True)
#                self._artists[0]._bbox_patch.set_clip_box(bbox)
#                self._artists[0]._bbox_patch.set_clip_on(True)
            except:
                pass
        self.delp("loaded_property")
        return a

    def add_artists(self, a):
        container = self.get_container()
        figure = self.get_figpage()._artists[0]
        self._artists = [a]
        if self.get_figaxes() is None:
            container.patches.append(a)
            a.set_figure(figure)
        else:
            container.add_patch(a)
            #a.set_figure(figure)
            #axes = self.get_figaxes()._artists[0]
            #a.set_axes(axes)

    def refresh_artist(self):
        a1 = self._artists[0]
        z = a1.zorder
        hl = len(self._artists[0].figobj_hl) != 0
        self.del_artist(delall=True)
        a = self.make_newartist()
        a.set_zorder(z)
#        self.add_artists(a)
        self.highlight_artist(hl, [a])
        a2 = self._artists[0]
        if a1 != a2:
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        val = []
        for a in self._artists:
            val.append(self.get_artist_property(a))
        if len(val) != 0:
            self.setp("loaded_property", val)

        if len(artistlist) != 0:
            #            container=self.get_figpage()._artists[0]
            container = self.get_container()
            is_figtext = self.get_figaxes() is None
            self.highlight_artist(False, artistlist)
            for a in artistlist:
                #            a is figure in this case
                if is_figtext:
                    container.patches.remove(a)
                else:
                    a.remove()

        super(FigArrow, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        figure = self.get_figpage()._artists[0]
        w = figure.get_figwidth()*figure.get_dpi()
        h = figure.get_figheight()*figure.get_dpi()
        if val == True:
            for a in alist:
                box = a.get_window_extent().get_points()
                x = [box[0][0], box[0][0], box[1][0], box[1][0], box[0][0]]
                y = [box[0][1], box[1][1], box[1][1], box[0][1], box[0][1]]
                hl = matplotlib.lines.Line2D(x, y, marker='s',
                                             color='k', linestyle='None',
                                             markerfacecolor='none',
                                             markeredgewidth=0.5,
                                             figure=figure)
                figure.lines.extend([hl])
                a.figobj_hl.append(hl)
                if self._drag_mode == 1:
                    x, y = self.get_gp(0).get_device_point()
                    x = [x]
                    y = [y]
                    hl = matplotlib.lines.Line2D(x, y, marker='s',
                                                 color='k', linestyle='None',
                                                 markerfacecolor='k',
                                                 markeredgewidth=0.5,
                                                 figure=figure)
                    figure.lines.extend([hl])
                    a.figobj_hl.append(hl)
                if self._drag_mode == 2:
                    x, y = self.get_gp(1).get_device_point()
                    x = [x]
                    y = [y]
                    hl = matplotlib.lines.Line2D(x, y, marker='s',
                                                 color='k', linestyle='None',
                                                 markerfacecolor='k',
                                                 markeredgewidth=0.5,
                                                 figure=figure)
                    figure.lines.extend([hl])
                    a.figobj_hl.append(hl)
#              print 'if drag_mode is xxx highlight gp here', self._drag_mode
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    figure.lines.remove(hl)
                    a.figobj_hl = []

    def get_artist_extent(self, a):
        box = a.get_window_extent().get_points()
        return [box[0][0], box[1][0], box[0][1], box[1][1]]

    def picker_a0(self, a, evt):
        from ifigure.widgets.canvas.custom_picker import linehit_test, abs_d
        hit, extra, type, loc = super(FigArrow, self).picker_a0(a, evt)
        type = 'area'
        loc = 3
#        hit2, extra =  a.contains(evt)
        hit2 = self.gp_hittest_line(evt, self.get_gp(0), self.get_gp(1))
        # print a, hit2, extra
        test = self.gp_hittest_rect(evt, self.get_gp(0), self.get_gp(1))
        # print hit2, test
        hit = False
        if test == 1:
            self._drag_mode = 1
            hit = True
            return hit, extra, type, loc
        elif test == 3:
            self._drag_mode = 2
            hit = True
            return hit, extra, type, loc
        elif test == 5 or hit2 == 1:
            hit = True
            self._drag_mode = 3
        if self.gp_hittest_p(evt, self.get_gp(0)):
            self._drag_mode = 1
            hit = True
        if self.gp_hittest_p(evt, self.get_gp(1)):
            self._drag_mode = 2
            hit = True
        return hit, {}, type, loc

    def drag_a(self, a, evt, shift=None, scale=None):
        redraw, scale0 = super(FigArrow, self).drag_a(a, evt,
                                                      shift=shift, scale=scale)
        if self._drag_mode == 1:
            x, y = self.get_device_point(1)
            self._drag_hl.set_xdata([evt.x, x])
            self._drag_hl.set_ydata([evt.y, y])
        if self._drag_mode == 2:
            x, y = self.get_device_point(0)
            self._drag_hl.set_xdata([evt.x, x])
            self._drag_hl.set_ydata([evt.y, y])
        return redraw, scale0

    def dragdone_a(self, a, evt, shift=None, scale=None):

        shift = evt.guiEvent_memory.ShiftDown()
        redraw, scale0 = super(FigArrow, self).dragdone_a(a, evt,
                                                          shift=shift, scale=scale)

        dx1 = 0
        dx2 = 0
        dy1 = 0
        dy2 = 0

        h = []
        if scale is None:
            dx = evt.x - self._st_p[0]
            dy = evt.y - self._st_p[1]
            if self._drag_mode & 1 != 0:
                dx1 = dx
                dy1 = dy
            if self._drag_mode & 2 != 0:
                dx2 = dx
                dy2 = dy
            a1 = self.move_gp_points(0, dx1, dy1, action=True)
            a2 = self.move_gp_points(1, dx2, dy2, action=True)
            h.append(a1)
            h.append(a2)
        else:
            h = h + self.scale_artist(scale, action=True)

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)

        hist.start_record()
        for item in h:
            hist.add_history(item)
        hist.stop_record()
        return 0, scale0

    def scale_artist(self, scale, action=True):
        st_extent = self.get_artist_extent(self._artists[0])
        rec = geom.scale_rect(st_extent,
                              scale)
        gp = self.get_gp(0)
        x1, y1 = gp.get_device_point()
        gp = self.get_gp(1)
        x2, y2 = gp.get_device_point()

        if x1 > x2 and y1 > y2:
            i = (1, 3, 0, 2)
        elif x1 <= x2 and y1 > y2:
            i = (0, 3, 1, 2)
        elif x1 > x2 and y1 <= y2:
            i = (1, 2, 0, 3)
        elif x1 <= x2 and y1 <= y2:
            i = (0, 2, 1, 3)
        dx1 = rec[i[0]] - st_extent[i[0]]
        dy1 = rec[i[1]] - st_extent[i[1]]
        dx2 = rec[i[2]] - st_extent[i[2]]
        dy2 = rec[i[3]] - st_extent[i[3]]

        if action:
            h = []
            a1 = self.move_gp_points(0, dx1, dy1, action=True)
            a2 = self.move_gp_points(1, dx2, dy2, action=True)
            h.append(a1)
            h.append(a2)
            return h
        else:
            self.move_gp_points(0, dx1, dy1, action=False)
            self.move_gp_points(1, dx2, dy2, action=False)

    def set_arrowstyle(self, value, a):
        #        print 'set_arrowystyle', a, value
        self.set_update_artist_request()
        self.setp("arrowstyle", value)

    def get_arrowstyle(self, a):
        return self.getp("arrowstyle")

    def _eval_xy(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None, None
        return self.getvar('x1', 'y1', 'x2', 'y2')
#        if self.getp(("x1", "y1", "x2", "y2")) is None:
#            return None, None, None, None
#        return  self.getp(("x1", "y1", "x2", "y2"))
