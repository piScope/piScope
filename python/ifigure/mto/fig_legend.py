from __future__ import print_function

__author__ = "Syun'ichi Shiraiwa"
__copyright__ = "Copyright, S. Shiraiwa, PiScope Project"
__credits__ = ["Syun'ichi Shiraiwa"]
__version__ = "0.5"
__maintainer__ = "S. Shiraiwa"
__email__ = "shiraiwa@psfc.mit.edu"
__status__ = "beta"


from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_grp import FigGrp
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
from matplotlib.legend import Legend
import matplotlib.path as mpath
import matplotlib.cbook as mplcbook
import matplotlib.transforms as mpltransforms

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder
from ifigure.mto.figobj_gpholder import FigObjGPHolder


class FigLegend(FigObjGPHolder):
    def __init__(self, *args, **kywds):
        '''
        Curve object:
           figaxe1, figaxes2: None or full_path string
        '''

        self._objs = []  # for debug....
        if "draggable" in kywds:
            self.setvar("draggable", kywds["draggable"])
            del kywds["draggable"]
        else:
            self.setvar("draggable", False)
        if "container_idx" in kywds:
            self._container_idx = kywds["container_idx"]
            del kywds["container_idx"]
        else:
            self._container_idx = 0

        kywds = self._process_kywd(kywds, "xy", [0, 0])
        kywds = self._process_kywd(kywds, "trans1", ['figure']*2)
        kywds = self._process_kywd(kywds, "figaxes1", None)
        kywds = self._process_kywd(kywds, "fbedgecolor", 'k')
        kywds = self._process_kywd(kywds, "fbfacecolor", 'w')
        kywds = self._process_kywd(kywds, "fblinewidth", 1.0)
        kywds = self._process_kywd(kywds, "fblinestyle", "solid")
        kywds = self._process_kywd(kywds, "fbalpha", 1.0)
        kywds = self._process_kywd(kywds, "title", None)
        kywds = self._process_kywd(kywds, "shadow", False)

        GenericPointsHolder.__init__(self, num=1)

        if len(args) == 1:
            self.setvar('legendlabel', args[0])
        elif len(args) == 2:
            if (mplcbook.is_string_like(args[1]) or
                    isinstance(args[1], int)):
                self.setvar('legendlabel', args[0])
                self.setvar('legendloc', args[1])
            else:
                self.setvar('legendhandle', args[0])
                self.setvar('legendlabel', args[1])
        args = ()

        super(FigLegend, self).__init__(*args, **kywds)

        if self.getvar('figaxes1') is not None:
            self.setvar("figaxes1", figaxes1.get_full_path())

        self.setp('use_var', True)
        self.setp('legendpos', (None, None))
        self.setp('zorder', 2.5)
        self.setp('legendlabelprop', ['default']*4)

        self._cb_added = False
        self._drag_mode = 0
        self._drag_artist = None
        self._legend_hitlevel = -1
        self._hit_a = None
        self._floating = True

    @classmethod
    def isFigLegend(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'legend'

    @classmethod
    def allow_outside(self):
        ### if fig_obj can be dragged outside of axes ###
        return True

    @classmethod
    def property_in_file(self):
        return []

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return (["legendlabelcolor", "legendcolor", "legendlabel",
                 "legendlabelprop",
                 "legendpos", "legendloc", "draggable"] +
                super(FigLegend, self).attr_in_file())

    @classmethod
    def property_in_palette(self):
        return ["position", "labels", "box"], [
            ["legendloc",  "legendlabelprop"],
            ["legendtitle", "legendentry"],
            ["facecolor_2", "edgecolor_2", "linewidthz",
             "plinestyle_2", "alpha_2", "legendshadow"],
        ]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'legend.png')
        return [idx1]

    def set_parent(self, parent):
        FigObj.set_parent(self, parent)
        GenericPointsHolder.set_parent(self, parent)

    def canvas_menu(self):
        return []

    def get_artists_for_pick(self):
        return self._artists

    def isDraggable(self):
        if self.getp("draggable") is not None:
            return self.getp("draggable")
        else:
            return self.getvar("draggable")

    def generate_artist(self):
        if self.isempty() is False:
            return
        if self.getp('use_var'):
            if self.getvar('legendhandle') is not None:
                a = [weakref.ref(figobj._artists[0])
                     for figobj in self.getvar('legendhandle')]
                self.setp('legendhandle', a)
            if self.getvar('legendlabel') is not None:
                self.setp('legendlabel', self.getvar('legendlabel'))
            if self.getvar('legendloc') is not None:
                self.setp('legendloc', self.getvar('legendloc'))
            else:
                self.setp('legendloc', 'best')
            if self.getvar('draggable') is not None:
                self.setp('draggable', self.getvar('draggable'))
            else:
                self.setp('draggable', False)

            trans1 = self.getvar("trans1")
            figaxes1 = self.getvar("figaxes1")
            if figaxes1 is not None:
                figaxes1 = self.find_by_full_path(str(figaxes1))

            xy = self.getvar("xy")
            self.set_gp_point(0, xy[0], xy[1],
                              trans=trans1)
            self.set_gp_figpage()
            self.set_gp_figaxes(0, figaxes1)
            self.setp('use_var', False)

        a = self.make_newartist()
        if self.hasp("loaded_property"):
            self.set_artist_property(a, lp[0])
            self.delp("loaded_property")
        if not self._cb_added:
            fig_page = self.get_figpage()
            fig_page.add_resize_cb(self)
            self._cb_added = True

        self.setp('legendlabel', [t.get_text() for t in a.texts])
        return

    def onResize(self, evt):
        self.refresh_artist()

    def do_update_artist(self):
        self.refresh_artist()

    def apply_fbprop(self, patch):
        props = ['alpha', 'linestyle', 'linewidth',
                 'facecolor', 'edgecolor']
        for p in props:
            value = self.getvar('fb'+p)
            m = getattr(patch, 'set_'+p)
            m(value)

    def make_newartist(self):
        self.check_loaded_gp_data()
        c = self.get_container()
        args = []
        kwargs = self.getvar('kywds').copy()
        # clean legendhandle first
        if self.getp('legendhandle') is not None:
            v = [h for h in self.getp('legendhandle')
                 if (hasattr(h(), 'figobj') and
                     h().figobj is not None)]
            if len(v) == 0:
                self.delp('legendhandle')
            else:
                self.setp('legendhandle', v)

        if self.getp('legendhandle') is not None:
            v = [v() for v in self.getp('legendhandle')
                 if v() is not None]
            args.append(v)
        else:
            if hasattr(self.get_container(), "_get_legend_handles"):
                h = self.get_container()._get_legend_handles()
                args.append([x for x in h if hasattr(x, 'figobj')])
                self.setp('legendhandle', [weakref.ref(x)
                                           for x in h if hasattr(x, 'figobj')])

        if self.getp('legendlabel') is not None:
            args.append(self.getp('legendlabel'))
        if self.getp('legendloc') is not None:
            kwargs['loc'] = self.getp('legendloc')

        kwargs['title'] = self.getvar('title')
        kwargs['shadow'] = self.getvar('shadow')

        a = c.legend(*args, **kwargs)
        self.apply_fbprop(a.legendPatch)
        if self.getp('draggable'):
            pos = self.getp('legendpos')
            if pos[0] is not None:
                a._loc = tuple(self.getp('legendpos'))
        # store labelcolor, labelfamily, labelweight, labelstyle, labelsize
        labelcolor = self.getp('legendlabelcolor')
        if labelcolor is not None:
            i = 0
            while i < len(labelcolor) and i < len(a.texts):
                a.texts[i].set_color(labelcolor[i])
                i = i + 1
        labelcolor = [t.get_color() for t in a.texts]
        self.setp('legendlabelcolor', labelcolor)

        if self.get_figaxes() is not None:
            c.legend_ = None
            c.add_artist(a)

        if self.getp('legendhandle') is not None:
            for h in self.getp('legendhandle'):
                if (hasattr(h(), 'figobj') and
                        h().figobj is not None):
                    h().figobj.add_update_client(self)
                else:
                    print('h() does not have figobj')
#        xy = self.get_gp(0).get_device_point()

        lp = self.getp("loaded_property")
        if lp is not None:
            self.set_artist_property(a, lp[0])
            self.delp("loaded_property")
        a.figobj = self
        a.figobj_hl = []
        a.set_zorder(self.getp('zorder'))

        self._artists = [a]
        return a

    def refresh_artist(self):
        if len(self._artists) != 1:
            return
        a1 = self._artists[0]
        z = a1.zorder
        hl = len(self._artists[0].figobj_hl) != 0
        self.del_artist(delall=True)
        a = self.make_newartist()
        a.set_zorder(z)
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
#        val = []
#        for a in self._artists:
#           val.append(self.get_artist_property(a))
#        if len(val) != 0:
#           self.setp("loaded_property", val)

        if len(artistlist) != 0:
            c = self.get_container()
            self.highlight_artist(False, artistlist)
            for a in artistlist:
                if self.get_figaxes() is None:
                    if a in c.legends:
                        c.legends.remove(a)
                else:
                    if a in c.artists:
                        a.remove()#c.artists.remove(a)

        super(FigLegend, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        figure = self.get_figpage()._artists[0]
        if val == True:
            a = alist[0]
            if self._hit_a is None:
                box = a.get_window_extent().get_points()
            else:
                box = self._hit_a.get_window_extent().get_points()
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
        #        return FigGrp.get_artist_extent(self, a)
        box = a.get_window_extent().get_points()
        #x0, x1, y0, y1
        return [box[0][0], box[1][0], box[0][1], box[1][1]]

    def get_artist_extent_all(self):
        return self.get_artist_extent(self._artists[0])

    def picker(self, a, evt):
        return self.picker_a(a, evt)

    def picker_a0(self, a, evt):
        member_hit = False
        self._picker_a_mode = 0
        self._hit_a = None
        hit, extra, type, loc = super(FigLegend, self).picker_a0(a, evt)

        for t in a.get_texts() + [self._artists[0].get_title()]:
            if t is None:
                continue
            try:
                box = self.get_artist_extent(t)
            except:
                continue
            if (evt.x > box[0] and
                evt.x < box[1] and
                evt.y > box[2] and
                    evt.y < box[3]):
                member_hit = True
                self._hit_a = t
                self.highlight_artist(False)
                break
        if hit:
            type = 'area'
            loc = 3
        return hit, extra, type, loc

    def drag_a(self, a, evt, shift=None, scale=None):
        redraw, scale = super(FigLegend, self).drag_a(
            a, evt, shift=shift, scale=scale)
        return redraw, scale

    def dragdone_a(self, a, evt, shift=None, scale=None):
        shift = evt.guiEvent_memory.ShiftDown()
        redraw, scale0 = super(FigLegend, self).dragdone_a(a, evt,
                                                           shift=shift, scale=scale)
        x = min(self._drag_rec[:2])
        y = min(self._drag_rec[2:])

        bbx = a.get_bbox_to_anchor()
        pos = mpltransforms.BboxTransformFrom(bbx).transform_point((x, y))

        h = [UndoRedoFigobjMethod(a, 'legendloc',
                                  (True, self.getp('legendloc'), pos))]

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        self._hit_a = None
        self._picker_a_mode = 0
#        h = h + self.scale_artist(scale0, action = True)

        if len(h) != 0:
            hist.start_record()
            for item in h:
                hist.add_history(item)
            hist.stop_record()
        return 0, scale0

    def get_legendlabel(self, a, tab):
        idx = self._tab_2_idx(tab)
        if len(self._get_texts()) > idx:
            return self._get_texts()[idx].get_text()
        else:
            return ''

    def set_legendlabel(self, param, a):
        tab = param[0]
        value = param[1]
        idx = self._tab_2_idx(tab)
        if len(self._get_texts()) > idx:
            self._get_texts()[idx].set_text(value)
            h = self._artists[0].legendHandles[idx]
            h.set_label(value)
            self.getp('legendlabel')[idx] = value

    def get_legendlabel_prop(self, a):
        return self.getp('legendlabelprop')

    def set_legendlabel_prop(self, v, a):
        #        text = self._get_texts()[0]
        for text in a.texts + [self._get_title()]:
            page = a.figure.figobj
            if v[0] != 'default':
                text.set_family(v[0])
            else:
                text.set_family(page.getp('tick_font'))
            if v[1] != 'default':
                text.set_weight(v[1])
            else:
                text.set_weight(page.getp('tick_weight'))
            if v[2] != 'default':
                text.set_style(v[2])
            else:
                text.set_style(page.getp('tick_style'))
            if v[3] != 'default':
                text.set_size(v[3])
            else:
                text.set_size(page.getp('ticklabel_size'))

        self.setp('legendlabelprop', v)

    def get_legendentry(self, a):
        labels = [t.get_text() for t in self._get_texts()]
        colors = [self.getp('legendlabelcolor')[idx]
                  for idx, t in enumerate(self._get_texts())]

        idxlabel = ['#'+str(x+1) for x in range(len(labels))]
        if self._hit_a is not None and self._hit_a in self._artists[0].get_texts():
            idx = self._artists[0].get_texts().index(self._hit_a)
        else:
            idx = -1
        return idx, idxlabel, list(zip(labels, colors))

    def set_legendentry(self, value, a):
        idx = value[0]
        v = value[2][idx]

        self.getp('legendlabelcolor')[idx] = v[1]

        text = self._get_texts()[idx]
        text.set_text(v[0])
        text.set_color(v[1])
        h = self._artists[0].legendHandles[idx]
        h.set_label(v[0])
        self.getp('legendlabel')[idx] = v[0]

    def get_legendloc(self, a):
        return (self.getp('draggable'),
                self.getp('legendloc'),
                self.getp('legendpos'), )

    def set_legendloc(self, value, a):
        '''
        value = [draggable, loc, pos]
        '''

        self.setp('draggable', value[0])
        if len(value) == 2:
            self.setp('legendloc', value[1])
            if not value[0]:
                self.setp('legendpos', (None, None))
        if len(value) == 3:
            self.setp('legendpos', value[2])
            self.setp('legendloc', value[1])
        self.set_update_artist_request()

    def get_facecolor(self, a):
        return self._artists[0].legendPatch.get_facecolor()

    def set_facecolor(self, value, a):
        self._artists[0].legendPatch.set_facecolor(value)
        self.setvar('fbfacecolor', value)

    def get_edgecolor(self, a):
        return self._artists[0].legendPatch.get_edgecolor()

    def set_edgecolor(self, value, a):
        self._artists[0].legendPatch.set_edgecolor(value)
        self.setvar('fbedgecolor', value)

    def get_alpha(self, a):
        return self._artists[0].legendPatch.get_alpha()

    def set_alpha(self, value, a):
        self._artists[0].legendPatch.set_alpha(value)
        self.setvar('fbalpha', value)

    def get_linewidth(self, a):
        return self._artists[0].legendPatch.get_linewidth()

    def set_linewidth(self, value, a):
        self._artists[0].legendPatch.set_linewidth(value)
        self.setvar('fblinewidth', value)

    def get_linestyle(self, a):
        return self._artists[0].legendPatch.get_linestyle()

    def set_linestyle(self, value, a):
        self._artists[0].legendPatch.set_linestyle(value)
        self.setvar('fblinestyle', value)

    def get_title(self, a):
        if self._artists[0].get_title() is None:
            return ''
        else:
            return self._artists[0].get_title().get_text()

    def set_title(self, value, a):
        self.setvar('title', value)
        self.set_update_artist_request()

    def get_shadow(self, a):
        return self.getvar('shadow')

    def set_shadow(self, value, a):
        self.setvar('shadow', value)
        self.set_update_artist_request()

    def double_click_on_canvas(self, event, canvas):
        import matplotlib
        if not isinstance(self._hit_a, matplotlib.text.Text):
            return
        target_artist = self._hit_a
        if self._hit_a in self._get_texts():
            idx = self._get_texts().index(self._hit_a)
        elif self._hit_a is self._get_title():
            idx = -1
        else:
            return
#            idx = self._get_texts().index(self._hit_a)
#        if idx == -1: return
#        print idx
        tab = 'label1' if idx == 0 else str(idx+1)
        current_txt = target_artist.get_text()
        y = abs(event.y - canvas.GetClientSize()[1])

        def finish_text_edit(x, y, txt, target_artist=self._artists[0],
                             obj=canvas, tab=str(idx+1)):
            self = obj
            if tab != '0':
                a1 = UndoRedoFigobjMethod(target_artist,
                                          'legendlabel', txt)
                a1.set_extrainfo(tab)
            else:
                a1 = UndoRedoFigobjMethod(target_artist,
                                          'title', txt)
            window = self.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry([a1])
        canvas.ask_text_input(event.x, y,
                              value=current_txt, callback=finish_text_edit)

    def _tab_2_idx(self, tab):
        if tab == 'label1':
            idx = 0
        else:
            idx = int(tab)-1
        return idx

    def _get_texts(self):
        if len(self._artists) == 0:
            return []
        return self._artists[0].get_texts()

    def _get_title(self):
        return self._artists[0].get_title()

    def onRefreshLegend(self, evt):
        self.set_update_artist_request()
        canvas = evt.GetEventObject()
        ax = self.get_figaxes()
        if ax is not None:
            ax.set_bmp_update(False)
        canvas.draw()

    def canvas_menu(self):
        if self.get_rasterized():
            return [("Refresh Legend",   self.onRefreshLegend, None),
                    ("^Rasterized",  self.onUnsetRasterize, None)]
        else:
            return [("Refresh Legend",   self.onRefreshLegend, None),
                    ("*Rasterized",  self.onSetRasterize, None)]
