#  Name   :fig_grp
#
#          group class for fig_obj
#
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#
# *******************************************
#     Copyright(c) 2012- S. Shiraiwa
# *******************************************
from ifigure.widgets.canvas.file_structure import *

import logging
import os
import ifigure.utils.cbook as cbook

from ifigure.mto.treedict import TreeDict
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.py_script import PyScript
from ifigure.mto.py_code import PyCode
import ifigure.utils.geom as geom
import ifigure.events

from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox
import numpy as np

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import UndoRedoGroupUngroupFigobj


class FigGrp(FigObj):
    def __new__(cls, *args, **kargs):
        obj = FigObj.__new__(cls, *args, **kargs)
        obj._artist_extent = [None]*4
        return obj

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'group.png')
        return [idx]

    @classmethod
    def isFigGrp(self):
        return True

    def isPageObj(self):
        return self._isPageObj

    @classmethod
    def get_namebase(self):
        return 'group'

    @classmethod
    def allow_outside(self):
        ### if fig_obj can be dragged outside of axes ###
        return True

    @classmethod
    def property_in_file(self):
        # define artist property read by mpl.getp and saved in file
        return []

    @classmethod
    def property_in_palette(self):
        # define artist property or _attr shown in palette
        # this function retuns list of key in listparam defined in
        # artist_widgets.py. the 4th field listparam is the name
        # of property read by either mpl.getp (from artist) or
        # figobj.getp (from figobj)
        return []

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return []

    def isDraggable(self):
        val = True
        for name, child in self.get_children():
            val = val & child.isDraggable()
        return val

    def generate_artist(self, *args, **kywds):
        #        print 'entering fig_grp:: generate_artist'
        for name, child in self.get_children():
            if child._suppress:
                child.del_artist(delall=True)
            else:
                child.generate_artist(*args, **kywds)

        ax = self.get_figaxes()
        c = self.get_container()
        is_figgrp = self.get_figaxes() is None

        if self.isempty():
            a = Rectangle((0, 0), 1, 1, facecolor='none', fill=False,
                          edgecolor='none', alpha=0)
            a.figobj = self
            a.figobj_hl = []
            self._artists = [a]
            if is_figgrp:
                c.patches.append(a)
            else:
                c.add_patch(a)
            if ax is not None and ax.get_3d():
                import mpl_toolkits.mplot3d.art3d as art3d
                art3d.patch_2d_to_3d(a)

            figure = self.get_figpage()._artists[0]
            a.set_figure(figure)
            if self.get_figaxes() is not None:
                if len(self.get_figaxes()._artists) != 0:
                    a.axes = self.get_figaxes()._artists[0]

    def del_artist(self, artist=None, delall=False):
        artistlist = self._artists

        for name, child in self.get_children():
            child.del_artist(delall=True)
        if len(artistlist) != 0:
            c = self.get_container()
            is_figgrp = self.get_figaxes() is None

            self.highlight_artist(False, artistlist)
            for a in artistlist:
                if a in c.patches:
                    if is_figgrp:
                        c.patches.remove(a)
                    else:
                        a.remove()

        return super(FigGrp, self).del_artist(artist=artistlist,
                                              delall=delall)

    def highlight_artist(self, val, artist=None):
        figure = self.get_figpage()._artists[0]
        ax = self.get_figaxes()
        if val:
            if len(self._artists[0].figobj_hl) != 0:
                return
            box = self.get_artist_extent_all()
            self._artist_extent = box
            if box[0] is None:
                return
            x = [box[0], box[0], box[1], box[1], box[0]]
            y = [box[3], box[2], box[2], box[3], box[3]]

            hl = Line2D(x, y, marker='s',
                        color='k', linestyle='None',
                        markerfacecolor='k',
                        markeredgewidth=0.5,
                        figure=figure, alpha=0.3)
            figure.lines.append(hl)
            xy = (box[0], box[2])
            w = box[1] - box[0]
            h = box[3] - box[2]
            hlp = Rectangle(xy, w, h, alpha=0.3, facecolor='k',
                            figure=figure)
            if ax is not None:
                x0, y0 = ax._artists[0].transAxes.transform((0, 0))
                x1, y1 = ax._artists[0].transAxes.transform((1, 1))
                bbox = Bbox([[x0, y0], [x1, y1]])
                hlp.set_clip_box(bbox)
                hlp.set_clip_on(True)
            figure.patches.append(hlp)
#           if ax is not None and ax.get_3d():
#               import mpl_toolkits.mplot3d.art3d as art3d
#               art3d.patch_2d_to_3d(hl)
#               if len(ax._artists) != 0:
#                   a.axes = self.get_figaxes()._artists[0]
            self._artists[0].figobj_hl.extend([hl, hlp])
        else:
            if len(self._artists[0].figobj_hl) == 2:
                figure.lines.remove(self._artists[0].figobj_hl[0])
                figure.patches.remove(self._artists[0].figobj_hl[1])
            self._artists[0].figobj_hl = []

    def has_highlight(self, artist):
        return len(artist.figobj_hl) != 0

    def canvas_menu(self):
        m = [("Ungroup",  self.onUngroup, None),
             ("Rasterized All",  self.onSetRasterize, None),
             ("UnRasterized All",  self.onUnsetRasterize, None)]
        return m

    def get_rasterized_action(self, value):
        a = []
        for name, child in self.get_children():
            a.extend(child.get_rasterized_action(value))
        return a

    def onUngroup(self, evt):
        canvas = evt.GetEventObject()
        canvas.ungroup()
#
#  tree viewer menu
#

    def tree_viewer_menu(self):
        return super(FigGrp, self).tree_viewer_menu()

    def canvas_unselected(self):
        self._artist_extent = [None]*4
#
#  Hit test (annotation mode)
#
#   1) nothing is selected
#        no hit happenes on group.
#        if child hit...custom_picker shoud return
#        topgroup if it is not in the selection.
#        if it is in the selection, it should return
#        the second one.. and so on
#        when the hit happens, canvas will highlight the
#        group and therefore
#        it set self._artist_extent
#   2) when self._artist_extent is set
#        it perform FigGrp own picker
#        if it is not area FigGrp keeps is selection
#        otherwise check children..

    def picker_a(self, a, evt):
        if self._artist_extent[0] is None:
            return False, {}

        hit = False
        extra = {}
        hit, extra, type, loc = self.picker_a0(a, evt)
        if not hit:
            return False, {}
        else:
            self._picker_a_type = type
            self._picker_a_loc = loc
            extra = {"child_artist": self._artists[0]}
            # if edge or point was picked, it does not check
            # the children
            if type !=  'area':
                return hit, extra

        children = reversed(
            sorted(
                [(child.getp('zorder'), child)
                 for name, child in self.get_children()]
                , key=lambda x: x[0]
            ))

        for z, child in children:
            if isinstance(child, FigGrp):
                box = child.get_artist_extent_all()
                child._artist_extent = box
                hit2, extra2 = child.picker_a(child._artists[0],
                                              evt)
                child.canvas_unselected()
                if hit2:
                    self._picker_a_type = 'area'
                    self._picker_a_loc = 3
                    self._artist_extent = [None]*4
                    return hit2, {"child_artist": child._artists[0]}
            else:
                for a1 in child.walk_artists():
                    hit2, extra2, type, loc = child.picker_a0(a1, evt)
                    if hit2:
                        self._picker_a_type = 'area'
                        self._picker_a_loc = 3
                        self._artist_extent = [None]*4
                        return hit2, {"child_artist": a1}

        # if it comes here there is two possibility
        # 1) FigGrp was not selected and non of child did not hit
        # 2) FigGrp was hit and non of child did not hit
        return hit, extra

    def get_artist_extent_all(self):
        '''
        retrun the extent of artist in device
        coordinate
        '''
        def _merge(s, x0d, x1d, y0d, y1d):
            s = [min((x0d, s[0])),
                 max((x1d, s[1])),
                 min((y0d, s[2])),
                 max((y1d, s[3])), ]
            return s

        s = [10000, -1, 10000, -1]
        flag = False
        for name, child in self.get_children():
            if isinstance(child, FigGrp):
                x0d, x1d, y0d, y1d = child.get_artist_extent_all()
                if x0d is None:
                    continue
                s = _merge(s, x0d, x1d, y0d, y1d)
                flag = True
            else:
                for a in child._artists:
                    x0d, x1d, y0d, y1d = child.get_artist_extent(a)
                    if x0d is None:
                        continue
                    s = _merge(s, x0d, x1d, y0d, y1d)
                    flag = True
        if not flag:
            return [None]*4
        return s

    def get_artist_extent2(self, a):
        return self.get_artist_extent_all()

    def get_artist_extent(self, a):
        return self._artist_extent

    def picker_a0(self, a, evt):
        ret = super(FigGrp, self).picker_a0(a, evt)
#        print(ret)
        return ret

# dragstart : called when drag starts
    def dragstart_a(self, a, evt):
        self._st_extent = self.get_artist_extent_all()
        redraw = super(FigGrp, self).dragstart_a(a, evt, mode=2)
        for name, child in self.get_children():
            for a1 in child.walk_artists():
                redraw = child.dragstart_a(a1, evt)
            child._drag_hl.set_color('none')
            child._drag_hl.set_markeredgecolor('none')
            child._drag_hl.set_markerfacecolor('none')
        return redraw

# drag : to show transient usr feedback during drag
    def drag_a(self, a, evt, shift=None, scale=None):
        redraw, scale = super(FigGrp, self).drag_a(a, evt,
                                                   shift=shift, scale=scale)

        for name, child in self.get_children():
            for a1 in child.walk_artists():
                redraw, scale = child.drag_a(a1, evt,
                                             shift=shift, scale=scale)
        return redraw, scale

    def drag_a_rm_hl(self, a):
        for name, child in self.get_children():
            for a1 in child.walk_artists():
                child.drag_a_rm_hl(a1)
        super(FigGrp, self).drag_a_rm_hl(a)
# dragdone : finish-up dragging

    def dragdone_a(self, a, evt, shift=None, scale=None):
        shift = evt.guiEvent_memory.ShiftDown()
        redraw, scale0 = super(FigGrp, self).dragdone_a(a, evt,
                                                        shift=shift, scale=scale)

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
#        hist = self.get_root_parent().app.history
        h = self.scale_artist(scale0, action=True)
        if len(h) != 0:
            hist.start_record()
            for item in h:
                hist.add_history(item)
            hist.stop_record()
        for name, child in self.get_children():
            for a1 in child.walk_artists():
                child.dragdone_a_clean(a1)
                child.highlight_artist(False, artist=[a1])
        self.highlight_artist(False, artist=[a])
#        self.highlight_artist(True, artist=[a])
        return 0, scale0

    def scale_artist(self, scale, action=True):
        h = []
        for name, child in self.get_children():
            h = h + child.scale_artist(scale, action=action)
        return h

### group/ungroup (group is defined in FigObj)
    def ungroup(self):
        '''
        ungroup object
        if self does not have parent, it can not
        be ungrouped
        '''
        p = self.get_parent()
        if p is None:
            return
        ret = [child for name, child in self.get_children()]
        for child in ret:
            child.move(p, keep_zorder=True)
        self.destroy()
        return ret

    def set_parent(self, parent):
        super(FigGrp, self).set_parent(parent)
        for name, child in self.get_children():
            child.set_parent(self)

    def get_xrange(self, xrange=[None, None], scale='linear'):
        for name, child in self.get_children():
            xrange = child.get_xrange(xrange=xrange, scale=scale)
        return xrange

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        for name, child in self.get_children():
            yrange = child.get_yrange(xrange=xrange,
                                      yrange=yrange, scale=scale)
        return yrange

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        for name, child in self.get_children():
            crange = child.get_crange(crange=crange,
                                      xrange=xrange,
                                      yrange=yrange, scale=scale)
        return crange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        for name, child in self.get_children():
            zrange = child.get_zrange(zrange=zrange,
                                      xrange=xrange,
                                      yrange=yrange, scale=scale)
        return zrange

    def set_container_idx(self, value, a=None):
        FigObj.set_container_idx(self, value, a=a)
        for name, child in self.get_children():
            child.set_container_idx(value, a=a)

    def set_caxis_idx(self, value, a):
        for name, child in self.get_children():
            child.set_caxis_idx(value, a=None)

    def get_axis_param_idx(self):
        for name, child in self.get_children():
            idx = child.get_axis_param_idx()
            if idx[0] is not None:
                return idx
        return [None]*4

    def set_zorder(self, z1, a=None):
        self.setp('zorder', z1)
        for a in self._artists:
            a.set_zorder(z1)
        for name, child in self.get_children():
            child.set_zorder(z1, a=None)
        self.set_bmp_update(False)

    def get_zorder(self, a=None):
        return self.getp('zorder')
