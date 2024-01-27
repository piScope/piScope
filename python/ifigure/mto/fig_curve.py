
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
from matplotlib.patches import PathPatch
import matplotlib.path as mpath

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder
from ifigure.mto.figobj_gpholder import FigObjGPHolder


class FigCurve(FigObjGPHolder):
    def __init__(self, path=None, width=1.0, trans1=['figure']*2,
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
        GenericPointsHolder.__init__(self, num=1)
        super(FigCurve, self).__init__(*args, **kywds)
        self.setvar("curve_path", path)
        self.setvar("trans1", trans1)
        arrow1 = kywds.pop('arrow1', [False, 'simple'])
        arrow2 = kywds.pop('arrow2', [False, 'simple'])
        self.setvar("arrow1", arrow1)
        self.setvar("arrow2", arrow2)

        if figaxes1 is not None:
            self.setvar("figaxes1", figaxes1.get_full_path())
        else:
            self.setvar("figaxes1", None)
        self.setvar("width", width)
        self.setp('use_var', True)

        self._cb_added = False
        self._drag_mode = 0
        self._drag_artist = None
        self._hit_seg_i = -1

    @classmethod
    def isFigCurve(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'curve'

    @classmethod
    def property_in_file(self):
        return ["facecolor", "edgecolor", "zorder", "alpha", "linewidth",
                "linestyle", "fill"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return (["curve_path"] +
                super(FigCurve, self).attr_in_file())

    @classmethod
    def property_in_palette(self):
        return ["path", "patch", "arrow"], [["edgecolor", "linewidth",
                                             "plinestyle", "alpha", "closepoly"],
                                            ["fill", "facecolor"],
                                            ["curvearrow1", "curvearrow2"]]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'curve.png')
        return [idx1]

    def get_containter(self):
        return self.get_figpage()._artists[0]

#    def set_parent(self, parent):
#        FigObj.set_parent(self, parent)
#        GenericPointsHolder.set_gp_figpage(self)

    def canvas_menu(self):
        if self._drag_mode == 2:
            p = self.get_path()
            if self._drag_hit == -1:
                m = [("Add node",  self.onAddNode, None), ]
                if self._hit_seg_i != -1:
                    segpath = cbook.BezierSplit(self.get_path())
                    if len(segpath[self._hit_seg_i]) == 2:
                        m = m + \
                            [("Convert to curve",  self.onConvCurve, None), ]
                    else:
                        m = m + [("Convert to Line",  self.onConvLine, None), ]
                return m
            else:
                if cbook.BezierNodeType(p, self._drag_hit) == 1:
                    return [("Remove Node", self.onRmNode, None),
                            ("Convert to symmetric node", self.onMakeSym, None)]
                if cbook.BezierNodeType(p, self._drag_hit) == 2:
                    if p[self._drag_hit][2] == 1:  # smooth node
                        return [("Remove node", self.onRmNode, None),
                                ("Convert to coner node", self.onMakeCorner, None),
                                ("Convert to asymmetric node", self.onMakeAsym, None)]
                    elif p[self._drag_hit][2] == 2:  # coner node
                        return [("Remove Node", self.onRmNode, None),
                                ("Convert to symmetric node", self.onMakeSym, None)]
                    elif p[self._drag_hit][2] == 3:  # asymmetricr node
                        return [("Remove Node", self.onRmNode, None),
                                ("Convert to symmetric node", self.onMakeSym, None)]

        return []

    def onConvLine(self, evt):
        segpath = cbook.BezierSplit(self.get_path())
        p = segpath[self._hit_seg_i]
        segpath[self._hit_seg_i] = [p[0],
                                    (mpath.Path.LINETO, p[-1][1], 0)]
        path = cbook.BezierJoin(segpath)

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
#        hist = self.get_root_parent().app.history
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', path))
        hist.stop_record()

    def onConvCurve(self, evt):
        segpath = cbook.BezierSplit(self.get_path())
        p = segpath[self._hit_seg_i]
        x0, y0 = p[0][1]
        x1, y1 = p[-1][1]
        segpath[self._hit_seg_i] = [p[0],
                                    (mpath.Path.CURVE4,
                                     (x0*0.7+x1*0.3, y0*0.7+y1*0.3), p[0][2]),
                                    (mpath.Path.CURVE4,
                                     (x0*0.3+x1*0.7, y0*0.3+y1*0.7), 2),
                                    (mpath.Path.CURVE4, p[-1][1], 2)]
        path = cbook.BezierJoin(segpath)

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', path))
        hist.stop_record()

    def onAddNode(self, evt):
        fig_page = self.get_figpage()
        xy = self._artists[0].get_verts()
        path = self.get_path()
        hit, idx = cbook.BezierHitTest(path, self._st_p[0], self._st_p[1])
        if hit:
            path = cbook.BezierInsert(path, idx, self._st_p[0], self._st_p[1])
            window = evt.GetEventObject().GetTopLevelParent()
            hist = GlobalHistory().get_history(window)
#            hist = self.get_root_parent().app.history
            hist.start_record()
            hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                                  'pathdata', path))
            hist.stop_record()

    def onRmNode(self, evt):
        p = self.get_path()
        p = cbook.BezierRmnode(p, self._drag_hit)
        if p is None:
            pass

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
 #       hist = self.get_root_parent().app.history
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', p))
        hist.stop_record()

    def onMakeCorner(self, evt):
        p = self.get_path()
        p = [p[i] for i in range(len(p))]
        p[self._drag_hit] = (p[self._drag_hit][0], p[self._drag_hit][1], 2)
        p[self._drag_hit-1] = (p[self._drag_hit-1][0],
                               p[self._drag_hit-1][1], 2)
        p[self._drag_hit+1] = (p[self._drag_hit+1][0],
                               p[self._drag_hit+1][1], 2)

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
#        hist = self.get_root_parent().app.history
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', p))
        hist.stop_record()

    def onMakeSym(self, evt):
        p = self.get_path()
        p = [p[i] for i in range(len(p))]
        p[self._drag_hit] = (p[self._drag_hit][0], p[self._drag_hit][1], 1)

        d1 = np.sqrt((p[self._drag_hit][1][0]-p[self._drag_hit-1][1][0])**2 +
                     (p[self._drag_hit][1][1]-p[self._drag_hit-1][1][1])**2)
        d2 = np.sqrt((p[self._drag_hit][1][0]-p[self._drag_hit+1][1][0])**2 +
                     (p[self._drag_hit][1][1]-p[self._drag_hit+1][1][1])**2)
        dx = p[self._drag_hit+1][1][0]-p[self._drag_hit-1][1][0]
        dy = p[self._drag_hit+1][1][1]-p[self._drag_hit-1][1][1]
        dx1 = 1/np.sqrt(dx*dx+dy*dy)*dx*(d1+d2)/2
        dy1 = 1/np.sqrt(dx*dx+dy*dy)*dy*(d1+d2)/2
        p[self._drag_hit-1] = (p[self._drag_hit-1][0],
                               (p[self._drag_hit][1][0]-dx1,
                                p[self._drag_hit][1][1]-dy1),
                               1)
        p[self._drag_hit+1] = (p[self._drag_hit+1][0],
                               (p[self._drag_hit][1][0]+dx1,
                                p[self._drag_hit][1][1]+dy1),
                               1)
        hist = self.get_root_parent().app.history
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', p))
        hist.stop_record()

    def onMakeAsym(self, evt):
        p = self.get_path()
        p = [p[i] for i in range(len(p))]
        p[self._drag_hit] = (p[self._drag_hit][0], p[self._drag_hit][1], 3)
        p[self._drag_hit-1] = (p[self._drag_hit-1][0],
                               p[self._drag_hit-1][1], 3)
        p[self._drag_hit+1] = (p[self._drag_hit+1][0],
                               p[self._drag_hit+1][1], 3)

        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
#        hist = self.get_root_parent().app.history
        hist.start_record()
        hist.add_history(UndoRedoFigobjMethod(self._artists[0],
                                              'pathdata', p))
        hist.stop_record()

    def isDraggable(self):
        return self._var["draggable"]

    def generate_artist(self):

        if self.isempty() is False:
            return

        if self.getp('use_var'):
            path = self.getvar("curve_path")
            trans1 = self.getvar("trans1")
            figaxes1 = self.getvar("figaxes1")
            if figaxes1 is not None:
                figaxes1 = self.find_by_full_path(str(figaxes1))

            self.set_gp_point(0, path[0][1][0], path[0][1][1],
                              trans=trans1)
            self.set_gp_figpage()
            self.set_gp_figaxes(0, figaxes1)
            self.setp('use_var', False)
            self.set_path(path)

#        if self.hasp("loaded_property"):
#            lp = self.getp("loaded_property")
#            self.add_gp(GenericPoint(0,0,trans='figure'))
#            self.set_gp_figpage()
#            self.get_gp(0).dict_to_gp(lp[-1][0], self)

        a_arr = self.make_newartist()
        # if self.hasp("loaded_property"):
        #   self.set_artist_property(a_arr[0], lp[0])
        #   self.delp("loaded_property")
        self.add_artists(a_arr)

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
        path = self.get_path()
        aaa = self.make_newartist0(path)
        a = aaa[0]
        lp = self.getp("loaded_property")
        if lp is not None:
            self.set_artist_property(a, lp[0])
            ec = lp[0]['edgecolor']
            for arrow in aaa[1:]:
                arrow.set_edgecolor(ec)
                arrow.set_facecolor(ec)
            self.delp("loaded_property")
        a.figobj = self
        a.figobj_hl = []
        return aaa

    def make_newartist0(self,  pin, draw_arrow=True):
        p = [(item[0], item[1]) for item in pin]
        codes, verts = zip(*p)
        path = matplotlib.path.Path(verts, codes)
        a = PathPatch(path, facecolor='none', fill=False,
                      edgecolor='black', alpha=1)
        if not draw_arrow:
            return a

        aaa = [a]
        if self.getvar('arrow1')[0]:
            dx = np.array(verts[1])-np.array(verts[0])
            dx = dx*np.sqrt(np.sum(dx**2))/1000.
            b = matplotlib.patches.FancyArrowPatch(posA=verts[0]+dx,
                                                   posB=verts[0],
                                                   connectionstyle='arc3',
                                                   arrowstyle=self.getvar(
                                                       'arrow1')[1],
                                                   mutation_scale=1,)
            aaa.append(b)
        if self.getvar('arrow2')[0]:
            dx = np.array(verts[-2])-np.array(verts[-1])
            dx = dx*np.sqrt(np.sum(dx**2))/1000.
            c = matplotlib.patches.FancyArrowPatch(posA=verts[-1],
                                                   posB=verts[-1]-dx,
                                                   connectionstyle='arc3',
                                                   arrowstyle=self.getvar(
                                                       'arrow2')[1],
                                                   mutation_scale=1,)
            aaa.append(c)
        return aaa

    def add_artists(self, a):
        figure = self.get_containter()
        self._artists = a
        figure.patches.extend(a)
        for aa in a:
            aa.set_figure(figure)

    def refresh_artist(self):
        if len(self._artists) == 0:
            return
        a1 = self._artists[0]
        z = a1.zorder
        hl = len(self._artists[0].figobj_hl) != 0
        self.del_artist(delall=True)
        a_arr = self.make_newartist()
        for a in a_arr:
            a.set_zorder(z)
        self.add_artists(a_arr)
        self.highlight_artist(hl, a_arr[0])
        a2 = self._artists[0]
        if a1 != a2:
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def del_artist(self, artist=None, delall=False):
        #       if delall:
        artistlist = self._artists
#       else:
#           artistlist=artist

        # save_data2->load_data2 will set "loaded_property"
        self.load_data2(self.save_data2({}))
#        val = []
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

        super(FigCurve, self).del_artist(artistlist)
        # print artistlist

    def highlight_artist(self, val, artist=None, path=None):

        # if artist is None:
        alist = [self._artists[0]]
        # else:
        #   alist=artist
        figure = self.get_figpage()._artists[0]
        w = figure.get_figwidth()*figure.get_dpi()
        h = figure.get_figheight()*figure.get_dpi()
#        print val, self._drag_mode, 'highlight in fig_curve'
        if val == True:
            if self._drag_mode == 3:
                return
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

                if self._drag_mode == 2:
                    if path is None:
                        path = self.get_path()
                    i = 0
                    while i < len(path):
                        item = path[i]
                        if i < len(path)-3:
                            item20 = path[i+3][0]
                        else:
                            item20 = None
                        if (item[0] == mpath.Path.MOVETO or
                                item[0] == mpath.Path.LINETO):
                            hl = [matplotlib.lines.Line2D([item[1][0]], [item[1][1]],
                                                          marker='s', markersize=5,
                                                          color='k', linestyle='None',
                                                          markerfacecolor='r',
                                                          figure=figure)]
                        elif item[0] == mpath.Path.CURVE4:
                            h0 = matplotlib.lines.Line2D(
                                [path[i-1][1][0], path[i][1][0]],
                                [path[i-1][1][1], path[i][1][1]],
                                marker=None,
                                color='k', linestyle='-',
                                markerfacecolor='k',
                                figure=figure)
                            h1 = matplotlib.lines.Line2D(
                                [path[i][1][0]],
                                [path[i][1][1]],
                                marker='o', markersize=3,
                                color='k', linestyle='None',
                                markerfacecolor='k',
                                figure=figure)
                            i = i+1
                            h2 = matplotlib.lines.Line2D(
                                [path[i][1][0], path[i+1][1][0]],
                                [path[i][1][1], path[i+1][1][1]],
                                marker=None,
                                color='k', linestyle='-',
                                markerfacecolor='k',
                                markeredgecolor='k',
                                figure=figure)
                            h3 = matplotlib.lines.Line2D(
                                [path[i][1][0]],
                                [path[i][1][1]],
                                marker='o', markersize=3,
                                color='k', linestyle='None',
                                markerfacecolor='k',
                                markeredgecolor='k',
                                figure=figure)
                            i = i+1
                            if path[i][2] == 1:
                                m = 'o'
                            elif path[i][2] == 2:
                                m = 's'
                            elif path[i][2] == 3:
                                m = '^'
                            if item20 == mpath.Path.LINETO:
                                m = 's'
                            h4 = matplotlib.lines.Line2D(
                                [path[i][1][0]],
                                [path[i][1][1]],
                                marker=m, markersize=5,
                                color='k', linestyle='None',
                                markerfacecolor='r',
                                figure=figure)
                            hl = [h0, h1, h2, h3, h4]

                        i = i+1
                        figure.lines.extend(hl)
                        a.figobj_hl.extend(hl)

#              print 'if drag_mode is xxx highlight gp here', self._drag_mode
        else:
            self._picker_a_mode = 0
            for a in alist:
                for hl in a.figobj_hl:
                    figure.lines.remove(hl)
                    a.figobj_hl = []

    def get_artist_extent(self, a):
        box = a.get_window_extent().get_points()
        return [box[0][0], box[1][0], box[0][1], box[1][1]]

    def picker_a0(self, a, evt):
        from ifigure.widgets.canvas.custom_picker import linehit_test, abs_d

        self._picker_a_mode = 0
        hit, extra, type, loc = super(FigCurve, self).picker_a0(a, evt)
        self._drag_hit = -1
        hit2, hit_seg_i = cbook.BezierHitTest(self.get_path(), evt.x, evt.y)

        if self._drag_mode == 2:
            i = 0
            for item in self.get_path():
                if ((evt.x - item[1][0])**2 +
                        (evt.y - item[1][1])**2) < 25:
                    self._drag_hit = i
                    self._drag_opath = item
                    break
                i = i+1
            if self._drag_hit != -1:
                return True, {}, 'area', 3
            self._hit_seg_i = hit_seg_i

        if self._drag_mode != 0:
            if type == 'point':
                return hit, extra, type, loc

#        x = np.transpose(a.get_verts())[0]
#        y = np.transpose(a.get_verts())[1]
#        ans, idx  = cpicker.CheckLineHit(x, y,
#                            evt.x, evt.y)
        if hit2:
            type = 'area'
            if self._drag_mode == 1:
                self._drag_mode = 2
                self._picker_a_mode = 1
                self._hit_seg_i = hit_seg_i
            else:
                if evt.button == 1:
                    self._drag_mode = 1
            return True, {}, 'area', 3
        self._drag_mode = 0
        return False, {}, type, loc

    def drag_a(self, a, evt, shift=None, scale=None):
        redraw, scale = super(FigCurve, self).drag_a(
            a, evt, shift=shift, scale=scale)
        if self._drag_hit != -1:
            self._drag_hl.set_color('None')
            self._drag_hl.set_marker('None')
            figure = self.get_containter()
            if figure.patches.count(self._drag_artist) != 0:
                figure.patches.remove(self._drag_artist)
            p = [item for item in self.get_path()]
            dx = evt.x - self._st_p[0]
            dy = evt.y - self._st_p[1]
            p = self.move_path(p, self._drag_hit, dx, dy)
            width = self.getp("width")
            self._drag_artist = self.make_newartist0(p, draw_arrow=False)

            figure.patches.append(self._drag_artist)
            self._drag_artist.set_figure(figure)
            self._drag_mode = 2
            self.highlight_artist(False)
            self.highlight_artist(True, path=p)
            self._drag_mode = 3
        return 0, scale

    def drag_a_get_hl(self, a):
        if (self._drag_hit == -1):
            return super(FigCurve, self).drag_a_get_hl(a)
        v = []
        if self._drag_artist is not None:
            v.append(self._drag_artist)
        return v+a.figobj_hl

    def dragdone_a(self, a, evt, shift=None, scale=None):
        shift = evt.guiEvent_memory.ShiftDown()
        redraw, scale0 = super(FigCurve, self).dragdone_a(a, evt,
                                                          shift=shift, scale=scale)
        if self._drag_mode == 3:
            self._drag_mode = 2

        h = []

        if self._drag_hit != -1:
            figure = self.get_containter()
            if figure.patches.count(self._drag_artist) != 0:
                figure.patches.remove(self._drag_artist)
                self._drag_artist = None
            p = [item for item in self.get_path()]
            dx = evt.x - self._st_p[0]
            dy = evt.y - self._st_p[1]
            p = self.move_path(p, self._drag_hit, dx, dy)

            self._drag_hit = -1
            h = h + [UndoRedoFigobjMethod(self._artists[0],
                                          'pathdata', p)]
            scale0 = [1, 0, 0, 1, 0, 0]
        else:
            h = h + self.scale_artist(scale0, action=True)

#        hist = self.get_root_parent().app.history
        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        hist.start_record()
        for item in h:
            hist.add_history(item)
        hist.stop_record()
        return 0, scale0

    def move_path(self, p, i, dx, dy):
        Path = mpath.Path
        if cbook.BezierNodeType(p, self._drag_hit) == 2:
            p[self._drag_hit] = (p[self._drag_hit][0],
                                 (p[self._drag_hit][1][0]+dx,
                                  p[self._drag_hit][1][1]+dy),
                                 p[self._drag_hit][2])
            p[self._drag_hit-1] = (p[self._drag_hit-1][0],
                                   (p[self._drag_hit-1][1][0]+dx,
                                    p[self._drag_hit-1][1][1]+dy),
                                   p[self._drag_hit-1][2])
            if self._drag_hit != len(p)-1:
                if p[self._drag_hit+1][0] == Path.CURVE4:
                    p[self._drag_hit+1] = (p[self._drag_hit+1][0],
                                           (p[self._drag_hit+1][1][0]+dx,
                                            p[self._drag_hit+1][1][1]+dy),
                                           p[self._drag_hit+1][2])
        elif cbook.BezierNodeType(p, self._drag_hit) == 3:
            p[self._drag_hit] = (p[self._drag_hit][0],
                                 (p[self._drag_hit][1][0]+dx,
                                  p[self._drag_hit][1][1]+dy),
                                 p[self._drag_hit][2])
            if self._drag_hit > 1:
                if (p[self._drag_hit-2][0] == Path.CURVE4 and
                    p[self._drag_hit-1][0] == Path.CURVE4 and
                        p[self._drag_hit-2][2] >= 1):
                    if p[self._drag_hit-1][2] == 1:
                        p[self._drag_hit-2] = (p[self._drag_hit-2][0],
                                               (p[self._drag_hit-2][1][0]-dx,
                                                p[self._drag_hit-2][1][1]-dy),
                                               p[self._drag_hit-2][2])
                    if p[self._drag_hit-1][2] == 3:
                        d = np.sqrt((p[self._drag_hit-2][1][0]-p[self._drag_hit-1][1][0])**2 +
                                    (p[self._drag_hit-2][1][1]-p[self._drag_hit-1][1][1])**2)
                        dx = p[self._drag_hit][1][0]-p[self._drag_hit-1][1][0]
                        dy = p[self._drag_hit][1][1]-p[self._drag_hit-1][1][1]
                        dx1 = 1/np.sqrt(dx*dx+dy*dy)*dx*d
                        dy1 = 1/np.sqrt(dx*dx+dy*dy)*dy*d
                        p[self._drag_hit-2] = (p[self._drag_hit-2][0],
                                               (p[self._drag_hit-1][1][0]-dx1,
                                                p[self._drag_hit-1][1][1]-dy1),
                                               p[self._drag_hit-2][2])
        elif cbook.BezierNodeType(p, self._drag_hit) == 4:
            p[self._drag_hit] = (p[self._drag_hit][0],
                                 (p[self._drag_hit][1][0]+dx,
                                  p[self._drag_hit][1][1]+dy),
                                 p[self._drag_hit][2])
            if self._drag_hit < len(p)-3:
                if (p[self._drag_hit+2][0] == Path.CURVE4 and
                    p[self._drag_hit+1][0] == Path.CURVE4 and
                        p[self._drag_hit+2][2] >= 1):
                    if p[self._drag_hit+1][2] == 1:
                        p[self._drag_hit+2] = (p[self._drag_hit+2][0],
                                               (p[self._drag_hit+2][1][0]-dx,
                                                p[self._drag_hit+2][1][1]-dy),
                                               p[self._drag_hit+2][2])
                    if p[self._drag_hit+1][2] == 3:
                        d = np.sqrt((p[self._drag_hit+2][1][0]-p[self._drag_hit+1][1][0])**2 +
                                    (p[self._drag_hit+2][1][1]-p[self._drag_hit+1][1][1])**2)
                        dx = p[self._drag_hit][1][0]-p[self._drag_hit+1][1][0]
                        dy = p[self._drag_hit][1][1]-p[self._drag_hit+1][1][1]
                        dx1 = 1/np.sqrt(dx*dx+dy*dy)*dx*d
                        dy1 = 1/np.sqrt(dx*dx+dy*dy)*dy*d
                        p[self._drag_hit+2] = (p[self._drag_hit+2][0],
                                               (p[self._drag_hit+1][1][0]-dx1,
                                                p[self._drag_hit+1][1][1]-dy1),
                                               p[self._drag_hit+2][2])
        elif cbook.BezierNodeType(p, self._drag_hit) == 1:
            p[self._drag_hit] = (p[self._drag_hit][0],
                                 (p[self._drag_hit][1][0]+dx,
                                  p[self._drag_hit][1][1]+dy),
                                 p[self._drag_hit][2])
            if (self._drag_hit == 0 and
                    self.get_closepoly()):
                p[-1] = (p[-1][0],
                         (p[0][1][0], p[0][1][1]),
                         p[-1][2])
            if (self._drag_hit == 0 and
                    p[1][0] == Path.CURVE4):
                p[1] = (p[1][0], (p[1][1][0]+dx, p[1][1][1]+dy), p[1][2])
        elif cbook.BezierNodeType(p, self._drag_hit) == 5:
            p[self._drag_hit] = (p[self._drag_hit][0],
                                 (p[self._drag_hit][1][0]+dx,
                                  p[self._drag_hit][1][1]+dy),
                                 p[self._drag_hit][2])
            if (self._drag_hit == len(p)-1 and
                    self.get_closepoly()):
                p[0] = (p[0][0],
                        (p[-1][1][0], p[-1][1][1]),
                        p[0][2])
            if (self._drag_hit == len(p)-1 and
                not self.get_closepoly() and
                    p[-2][0] == Path.CURVE4):
                p[-2] = (p[-2][0],
                         (p[-2][1][0]+dx, p[2][1][1]+dy),
                         p[-2][2])

        return p

    def scale_artist(self, scale, action=True):
        opath = self.get_path()
        minx = min([i[1][0] for i in opath])
        miny = min([i[1][1] for i in opath])
        maxx = max([i[1][0] for i in opath])
        maxy = max([i[1][1] for i in opath])
        path = []
        for item in opath:
            #           x = minx+(item[1][0]-minx)*scale[0]+(item[1][1]-miny)*scale[1]+scale[4]
            #           y = miny+(item[1][0]-minx)*scale[2]+(item[1][1]-miny)*scale[3]+scale[5]
            x = (item[1][0])*scale[0]+(item[1][1])*scale[1]+scale[4]
            y = (item[1][0])*scale[2]+(item[1][1])*scale[3]+scale[5]
            path.append((item[0], (x, y), item[2]))
        if action:
            h = []
            a1 = UndoRedoFigobjMethod(self._artists[0],
                                      'pathdata',
                                      path)
            h.append(a1)
            return h
        else:
            self.set_pathdata(path, self._artists[0])

    def set_pathdata(self, path, a):
        self.set_path(path)
        self.set_update_artist_request()

    def get_pathdata(self, a):
        return self.get_path()

    def set_closepoly(self, value, a):
        Path = mpath.Path
        if value:
            if not self.get_closepoly(a):
                p = self.get_path()
                p.append((mpath.Path.CLOSEPOLY,
                          p[0][1], 1))
                self.set_path(p)
        else:
            if self.get_closepoly(a):
                p = self.get_path()
                p = p[:-1]
                self.set_path(p)
        self.set_update_artist_request()

    def get_closepoly(self, a=None):
        Path = mpath.Path
        return self.get_path()[-1][0] == mpath.Path.CLOSEPOLY

    def get_path(self):
        gp = self.get_gp(0)
        t = gp.get_gp_transform(dir='both')
        p = self.getp("curve_path")
        return [(item[0], gp.convert_trans_p(item[1], t), item[2])
                for item in p]

    def set_path(self, path):
        gp = self.get_gp(0)
        t = gp.get_gp_transform(dir='both')
        self.setp("curve_path",
                  [(item[0], gp.convert_trans_p(item[1], None, t), item[2])
                   for item in path])

    def set_curvearrow1(self, value, a):
        self.setvar('arrow1', (value[0], value[1][0]))
        self.refresh_artist()

    def get_curvearrow1(self, a):
        return (self.getvar('arrow1')[0], (self.getvar('arrow1')[1],))

    def set_curvearrow2(self, value, a):
        self.setvar('arrow2', (value[0], value[1][0]))
        self.refresh_artist()

    def get_curvearrow2(self, a):

        return (self.getvar('arrow2')[0], (self.getvar('arrow2')[1],))
