__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"

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
from matplotlib.patches import Rectangle
import matplotlib.path as mpath

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder
from ifigure.mto.figobj_gpholder import FigObjGPHolder


class FigBox(FigObjGPHolder):
    def __init__(self, xy=[0, 0], width=0.1, height=0.1,
                 isotropic=False,
                 trans1=['figure']*2,
                 figaxes1=None,  **kywds):
        '''
        Curve object:
           figaxe1, figaxes2: None or full_path string
        '''

        self._objs = []  # for debug....
        if "draggable" in kywds:
            self.setvar("draggable", kywds["draggable"])
            del kywds["draggable"]
        else:
            self.setvar("draggable", True)
        args = ()

        GenericPointsHolder.__init__(self, num=2)
        super(FigBox, self).__init__(*args, **kywds)

        self.setvar("trans1", trans1)

        if figaxes1 is not None:
            self.setvar("figaxes1", figaxes1.get_full_path())
        else:
            self.setvar("figaxes1", None)
        self.setvar("width", width)
        self.setvar("height", height)
        self.setvar("xy", xy)
        self.setp('use_var', True)
        self.setp('isotropic', isotropic)

        self._cb_added = False
        self._drag_mode = 0
        self._drag_artist = None
        self._hit_seg_i = -1

    @classmethod
    def isFigBox(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'box'

    @classmethod
    def property_in_file(self):
        return ["facecolor", "edgecolor", "zorder", "alpha", "linewidth",
                "linestyle", "fill"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return super(FigBox, self).attr_in_file()

    @classmethod
    def property_in_palette(self):
        return ["path", "patch"], [["edgecolor", "linewidth",
                                    "plinestyle", "alpha", "box_type"],
                                   ["fill", "facecolor"]]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'box.png')
        return [idx1]

    def get_containter(self):
        return self.get_figpage()._artists[0]

#    def set_parent(self, parent):
#        FigObj.set_parent(self, parent)
#        GenericPointsHolder.set_gp_figpage(self)

    def isDraggable(self):
        return self._var["draggable"]

    def generate_artist(self):

        if self.isempty() is False:
            return
        if self.getp('use_var'):
            trans1 = self.getvar("trans1")
            figaxes1 = self.getvar("figaxes1")
            if figaxes1 is not None:
                figaxes1 = self.find_by_full_path(str(figaxes1))

            xy = self.getvar("xy")
            w = self.getvar("width")
            h = self.getvar("height")

            self.set_gp_point(0, xy[0], xy[1], trans=trans1)
            self.set_gp_point(1, xy[0]+w, xy[1]+h, trans=trans1)
            self.set_gp_figpage()
            self.set_gp_figaxes(0, figaxes1)
            self.set_gp_figaxes(1, figaxes1)
            self.setp('use_var', False)

#        if self.hasp("loaded_property"):
#            lp = self.getp("loaded_property")
#            self.set_gp_point(0, 0, 0, trans = 'figure')
#            self.set_gp_point(1, 0, 0, trans = 'figure')
#            self.set_gp_figpage()
#            self.get_gp(0).dict_to_gp(lp[-1][0], self)
#            self.get_gp(1).dict_to_gp(lp[-1][1], self)

        a = self.make_newartist()
        if self.hasp("loaded_property"):
            self.set_artist_property(a, lp[0])
            self.delp("loaded_property")
        self.add_artists(a)
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
        x1, y1 = self.get_gp(0).get_device_point()
        x2, y2 = self.get_gp(1).get_device_point()

        xy = (min([x1, x2]), min([y1, y2]))
        w = abs(x1-x2)
        h = abs(y1-y2)
        if self.getp('isotropic'):
            if w < h:
                h = w
            else:
                w = h

        a = Rectangle(xy, w, h, facecolor='none', fill=False,
                      edgecolor='black', alpha=1)

        lp = self.getp("loaded_property")
        if lp is not None:
            self.set_artist_property(a, lp[0])
            self.delp("loaded_property")
        a.figobj = self
        a.figobj_hl = []

        a.set_zorder(self.getp('zorder'))
        a._is_frameart = self.getp('frameart')
        return a

    def add_artists(self, a):
        figure = self.get_containter()
        self._artists = [a]
        figure.patches.append(a)
        a.set_figure(figure)

    def refresh_artist(self):
        if len(self._artists) != 1:
            return
        a1 = self._artists[0]
        z = a1.zorder
        hl = len(self._artists[0].figobj_hl) != 0
        self.del_artist(delall=True)
        a = self.make_newartist()
        a.set_zorder(z)
        self.add_artists(a)
        self.highlight_artist(hl, [a])
        a2 = self._artists[0]
        if a1 != a2:
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        # save_data2->load_data2 will set "loaded_property"

        self.load_data2(self.save_data2({}))

#        for a in self._artists:
#           val.append(self.get_artist_property(a))
#        if len(val) != 0:
#           self.setp("loaded_property", val)

        if len(artistlist) != 0:
            container = self.get_figpage()._artists[0]
            self.highlight_artist(False, artistlist)
            for a in artistlist:
                #            a is axes in this case
                #            a.remove()
                container.patches.remove(a)

        super(FigBox, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        figure = self.get_figpage()._artists[0]
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
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    figure.lines.remove(hl)
                    a.figobj_hl = []

    def get_artist_extent(self, a):
        box = a.get_window_extent().get_points()
        return [box[0][0], box[1][0], box[0][1], box[1][1]]

    def picker_a0(self, a, evt):

        self._picker_a_mode = 0
        hit, extra, type, loc = super(FigBox, self).picker_a0(a, evt)
        return hit, extra, type, loc

    def drag_a(self, a, evt, shift=None, scale=None):
        redraw, scale = super(FigBox, self).drag_a(
            a, evt, shift=shift, scale=scale)
        return redraw, scale

    def dragdone_a(self, a, evt, shift=None, scale=None):
        shift = evt.guiEvent_memory.ShiftDown()
        redraw, scale0 = super(FigBox, self).dragdone_a(a, evt,
                                                        shift=shift, scale=scale)

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)

        h = []
        h = h + self.scale_artist(scale0, action=True)

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

    def canvas_menu(self):
        return self.gp_holder_canvas_menu()

    def get_boxtype(self, a):
        if self.getp('isotropic'):
            return 'square'
        else:
            return 'rectangle'

    def set_boxtype(self, value, a):
        if value == 'square':
            self.setp('isotropic', True)
        else:
            self.setp('isotropic', False)
        self.refresh_artist()
