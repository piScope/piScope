from __future__ import print_function

__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"


from ifigure.mto.fig_obj import FigObj
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref
import logging
import matplotlib
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty, UndoRedoFigobjProperty, UndoRedoFigobjMethod


class FigAnnotate(FigObj):
    def __init__(self, s, xy, xytext=None, xycoords='data',
                 textcoords='data', arrowprops=None, **kywds):

        if xytext == None:
            xytext = xy
        if arrowprops == None:
            arrowprops = dict(arrowstyle="->",
                              connectionstyle="arc3")
        self._objs = []  # for debug....
        if "draggable" in kywds:
            self.setvar("draggable", kywds["draggable"])
            del kywds["draggable"]
        else:
            self.setvar("draggable", True)
        args = ()
        super(FigAnnotate, self).__init__(*args, **kywds)

        self.setvar("xy", xy)
        self.setvar("s",  s)
        self.setvar("xytext", xytext)
        self.setvar("xycoords", xycoords)
        self.setvar("textcoords", textcoords)
        self.setvar("arrowprops", arrowprops)
        self.setp('use_var', True)

    @classmethod
    def isFigAnnotate(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'annotate'

    @classmethod
    def property_in_file(self):
        return []

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ["use_var", "xy", "xytext", "s"]

    @classmethod
    def property_in_palette(self):
        return ["tab1", "tab2"], [["color"], ["color"]]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'arrow.bmp')
        return [idx1]

    def isDraggable(self):
        return self._var["draggable"]

    def generate_artist(self):
        container = self.get_container()
        if self.isempty() is False:
            return

        lp = self.getp("loaded_property")

        if self.getp('use_var'):

            xy = self.eval("xy")
            s = self.eval("s")
            xytext = self.eval("xytext")
            xycoords = self.eval("xycoords")
            textcoords = self.eval("textcoords")
            arrowprops = self.eval("arrowprops")
            self.setp("s", s)
            self.setp("xy", xy)
            self.setp("xytext", xytext)
            self.setp("textcoords", xycoords)
            self.setp("xycoords", xycoords)
            self.setp("arrowprops", arrowprops)
            self.setp('use_var', False)
        else:
            s = self.getp("s")
            xy = self.getp("xy")
            xytext = self.getp("xytext")
            xycoords = self.getp("xycoords")
            textcoords = self.getp("textcoords")
            arrowprops = self.getp("arrowprops")

        self._artists = [container.annotate(s, xy,
                                            xytext=xytext,
                                            xycoords=xycoords,
                                            textcoords=textcoords,
                                            arrowprops=arrowprops)]
        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []

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
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            for a in artistlist:
                #            a is axes in this case
                a.remove()

        super(FigAnnotate, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        container = self._artists[0].get_figure()
        w = container.get_figwidth()*container.get_dpi()
        h = container.get_figheight()*container.get_dpi()
        if val == True:
            for a in alist:

                arr = a.arrow_patch.get_verts()
                hl = matplotlib.lines.Line2D(arr[:, 0]/w, arr[:, 1]/h,
                                             marker='s',
                                             color='k', linestyle='None',
                                             markerfacecolor='None',
                                             figure=container,
                                             transform=container.transFigure,)
                container.lines.extend([hl])
                a.figobj_hl.append(hl)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    hl.remove()
                    a.figobj_hl = []

    def get_artist_extent(self, a):
        arr = a.arrow_patch.get_verts()
        x = arr[:, 0]
        y = arr[:, 1]
        return [min(x), max(x), min(y), max(y)]

    def picker_a0(self, a, evt):
        from ifigure.widgets.canvas.custom_picker import linehit_test, abs_d
        hit, extra, type, loc = super(FigAnnotate, self).picker_a0(a, evt)

        arr = a.arrow_patch.get_verts()
        x = arr[:, 0]
        y = arr[:, 1]
        self._drag_mode = 0

        hit = False
        if abs_d(x[0], y[0], evt.x, evt.y) < 5:
            self._drag_mode = 1
            hit = True
        elif abs_d(x[-1], y[-1], evt.x, evt.y) < 5:
            self._drag_mode = 2
            hit = True
        for i in range(len(x)-1):
            if (linehit_test(evt.x, evt.y, x[i], y[i], x[i+1], y[i+1]) < 5 and
                evt.x > min([x[i], x[i+1]]) and
                evt.y > min([y[i], y[i+1]]) and
                evt.x < max([x[i], x[i+1]]) and
                    evt.y < max([y[i], y[i+1]])):
                hit = True
                self._drag_mode = 3
                break
        return hit, extra, type, loc

    def drag_a(self, a, evt, shift=None):
        print(self._picker_a_type)
        shift = evt.guiEvent.ShiftDown()
        redraw = super(FigAnnotate, self).drag_a(a, evt, shift=shift)
        return redraw

    def dragdone_a(self, a, evt, shift=None):
        shift = evt.guiEvent_memory.ShiftDown()
        redraw = super(FigAnnotate, self).dragdone_a(a, evt, shift=shift)
        dx = evt.x - self._st_p[0]
        dy = evt.y - self._st_p[1]

        xy = self.getp("xy")
        xytext = self.getp("xytext")
        xycoords = self.getp("xycoords")
        textcoords = self.getp("textcoords")

        hist = self.get_root_parent().app.history
        hist.start_record()

        if self._drag_mode & 2 != 0:
            t1 = self.coordsname2transform(self._parent._artists[0],
                                           xycoords)
            xyd = self.convert_transform_point(t1, None, xy)
            xyd = (xyd[0]+dx, xyd[1]+dy)
            xy = self.convert_transform_point(None, t1, xyd)
            action1 = UndoRedoFigobjProperty(self._artists[0],
                                             'xy', xy)
            hist.add_history(action1)
        if self._drag_mode & 1 != 0:
            t2 = self.coordsname2transform(self._parent._artists[0],
                                           textcoords)
            xytextd = self.convert_transform_point(t2, None, xytext)
            xytextd = (xytextd[0]+dx, xytextd[1]+dy)
            xytext = self.convert_transform_point(None, t2, xytextd)
            action2 = UndoRedoFigobjProperty(self._artists[0],
                                             'xytext', xytext)
            hist.add_history(action2)

        hist.stop_record()
