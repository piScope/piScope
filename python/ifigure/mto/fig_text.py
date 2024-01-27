#  Name   :fig_text
#
#          text object.
#          surpport both text and figtext
#          command.
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
import matplotlib.lines
import matplotlib.transforms as mpltransforms
import numpy as np
import weakref
import os

from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_axes import FigAxes
from ifigure.mto.fig_page import FigPage
from ifigure.widgets.canvas.file_structure import *
import ifigure
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
import ifigure.utils.geom as geom

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder
from ifigure.mto.figobj_gpholder import FigObjGPHolder

from ifigure.utils.args_parser import ArgsParser
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigText')
num_gp = 1


class FigText(FigObjGPHolder):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs = []  # for debug....
            obj._drag_backup = None
            obj._drag_mode = 1  # 1 transpose 2 expand 3 rotate
            obj._drag_start = None
            return obj

        if 'src' in kywds:
            obj = FigObjGPHolder.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            obj.setvar('clip', True)  # backword compatiblity should come here
            return obj

        p = ArgsParser()
        p.add_opt('x', 0.5, ['number', 'dynamic'])
        p.add_opt('y', 0.5, ['number', 'dynamic'])
        p.add_opt('z', 0.0, ['number', 'dynamic'])
        p.add_var('s', ['str', 'dynamic'])
        p.set_pair("x", "y")
        p.add_key('draggable', True)
        p.add_key('bbox', dict())
        p.add_key("fancybox", False)
        p.add_key("fbcolor", 'red')
        p.add_key("fbecolor", 'red')
        p.add_key("fbstyle", 'square')
        p.add_key("fbpad", 0.3)
        p.add_key("fbalpha", 1)
        p.add_key("fontfamily", 'sans-serif')
        p.add_key("fontstyle",  'normal')
        p.add_key("fontweight", 'roman')
        p.add_key("multialignment", "left")
        p.add_key("clip", True)
        p.add_key("trans", ["figure", "figure"]*num_gp)
        p.add_key("transaxes", ["default"]*num_gp)

        v, kywds, d, flag = p.process(*args, **kywds)

        if not flag:
            raise ValueError('Failed when processing argument')

        if isinstance(v['trans'], str):
            v['trans'] = [v['trans'], ]*num_gp*2

        obj = FigObjGPHolder.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in v:
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args,  **kywds):
        self._data_extent = None
        self._cb_added = False
        self._2d_text = True
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        GenericPointsHolder.__init__(self, num=num_gp)
        super(FigText, self).__init__(*args, **kywds)

    @classmethod
    def isFigText(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def allow_outside(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'text'

    @classmethod
    def property_in_file(self):
        return ["size", ] + \
            ["text", "color", "rotation", "alpha", "zorder"]

    @classmethod
    def property_in_palette(self):
        return ["text", "box"], [["text", "size",
                                  "color", "fontfamily", "fontweight", "fontstyle",
                                  "rotation", "alpha", "multialignment"],
                                 ["fancybox", "fbcolor", "fbecolor", "fbstyle", "fbpad",
                                  "fbalpha"]]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ["use_var", "fancybox", "fbcolor", "fbecolor",
                "fbstyle", "fbpad", "fbalpha", "zorder",
                "fontstyle", "fontweight", "fontfamily",
                "multialignment", "clip"]

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'a.png')
        return [idx1]

    def set_parent(self, parent):
        super(FigText, self).set_parent(parent)
#        GenericPointsHolder.set_gp_figpage(self)
        if isinstance(parent, FigPage):
            self._isFigPage = True
        else:
            self._isFigPage = False

    def isDraggable(self):
        return self._var["draggable"]

    def args2var(self):
        names0 = self.attr_in_file()
#        names  = ["x","y", "z", "s"]
#        use_np = [False]*4
        names = ["s"]
        use_np = [False]
        names = names + names0
        use_np = use_np + [False]*len(names0)
        values = self.put_args2var(names, use_np)

        self.set_gp_by_vars()  # use trans, transaxes in vars

#        x = values[0];y = values[1]
#        if x is None: return False
#        if y is None: return False
#        if (x.size != 1) or (y.size != 1):
#            self.setp("x", None)
#            self.setp("y", None)
#            return False
        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change

        if self.isempty() is False:
            return
#              self.del_artist(delall=True)

        lp = self.getp("loaded_property")

        # this will take care of use_var
        # and intialize gp points from vars if use_var
        x, y, z, s = self._eval_s()
        kywds = self._var["kywds"]

        if self.getp("fancybox"):
            style = self.getp("fbstyle")
            pad = self.getp("fbpad")
            t = style+',pad='+str(pad)
            bbox_props = dict(boxstyle=t,
                              facecolor=self.getp("fbcolor"),
                              edgecolor=self.getp("fbecolor"),
                              alpha=self.getp("fbalpha"))
            self.setp("bbox", bbox_props)
            kywds['bbox'] = bbox_props
        else:
            if 'bbox' in kywds:
                del kywds['bbox']
        if lp is not None:
            s = ''
#              x, y, s = self.eval("x", "y", "s")
#              if (x is not None  and
#                  y is not None):
#                 self.set_gp_point(0, x, y)
#           else:
#              s = ''
#              if len(lp) > 1:
#                 self.get_gp(0).dict_to_gp(lp[-1][0], self)
#              else:
#                 self.set_gp_figpage()

        self.make_newartist(s, **kywds)

        if not self._cb_added:
            fig_page = self.get_figpage()
            fig_page.add_resize_cb(self)
            self._cb_added = True

    def onResize(self, evt):
        self.refresh_artist()

    def do_update_artist(self):
        #        print 'text::do_update_artists'
        self.refresh_artist()

    def make_newartist(self, s='', **kywds):
        self.check_loaded_gp_data()

        container = self.get_container()
        xd, yd = self.get_device_point(0)
        # print xd, yd, self.get_gp(0).x, self.get_gp(0).y

        kywds['family'] = str(self.getp('fontfamily'))
        kywds['style'] = str(self.getp('fontstyle'))
        kywds['weight'] = str(self.getp('fontweight'))

        # multialingment and horizontal alignment
        # should be the same, somehow...(2014 01 07)

        kywds['multialignment'] = str(self.getp('multialignment'))
        kywds['ha'] = str(self.getp('multialignment'))

        if self._2d_text:
            self._artists = [container.text(xd, yd, s, **kywds)]
            self._artists[0].set_transform(mpltransforms.IdentityTransform())
        else:
            x, y, z, s = self._eval_s()
            self._artists = [container.text(x, y, z, s, **kywds)]

        lp = self.getp("loaded_property")
        if lp is not None:
            self.set_artist_property(self._artists[0], lp[0])
#        self._artists[0].set_size(self.getp('size'))
        self._artists[0].figobj = self
        self._artists[0].figobj_hl = []
        self._artists[0].set_zorder(self.getp('zorder'))
        if self.get_figaxes() is not None and self.getp('clip'):
            bbox = mpltransforms.Bbox.from_extents(
                container.get_window_extent().extents)
            try:
                self._artists[0].set_clip_box(bbox)
                self._artists[0].set_clip_on(True)
                self._artists[0]._bbox_patch.set_clip_box(bbox)
                self._artists[0]._bbox_patch.set_clip_on(True)
            except:
                pass

        self.delp("loaded_property")

        return self._artists[0]

    def refresh_artist(self):
        if len(self._artists) != 1:
            return
        a1 = self._artists[0]
        z = a1.zorder
        hl = len(self._artists[0].figobj_hl) != 0
        self.del_artist(delall=True)
        self.generate_artist()
        a2 = self._artists[0]
        #a2 = self.make_newartist()
        a2.set_zorder(z)
        self.highlight_artist(hl, [a2])
        if a1 != a2:
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def refresh_artist_data(self):
        if self.isempty() and not self._suppress:
            self.generate_artist()
            return
        x, y, z, s = self._eval_s()  # this handles "use_var"
        self._artists[0].set_text(s)
        if x is not None and y is not None:
            #           self.set_gp_point(0, x, y)
            xd, yd = self.get_device_point(0)
            self._artists[0].set_x(xd)
            self._artists[0].set_y(yd)

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = artist

        # save_data2->load_data2 will set "loaded_property"
        self.store_loaded_property()

        if len(artistlist) != 0:
            self.highlight_artist(False, artistlist)
            container = self.get_container()
            is_figtext = self.get_figaxes() is None
            for a in artistlist:
                #             a.set_picker(None)
                #            this does not work for figtext
                #             a.remove()
                if is_figtext:
                    container.texts.remove(a)
                else:
                    a.remove()

        super(FigText, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        page = self.get_figpage()
        figure = page._artists[0]
        container = figure
        #container = self.get_container()

        if container is None:
            return

        if val == True:
            for a in alist:
                try:
                    box = a.get_window_extent().get_points()
                    x = [box[0][0], box[0][0], box[1][0], box[1][0], box[0][0]]
                    y = [box[0][1], box[1][1], box[1][1], box[0][1], box[0][1]]
                except:
                    # if get_window_extent fails, it drow somthing
                    xd, yd = self.get_device_point(0)
                    x = [xd, xd+3, xd+3, xd, xd]
                    y = [yd, yd, yd+3, yd+3, yd]

                hl = matplotlib.lines.Line2D(x, y, marker='s',
                                             color='k', linestyle='None',
                                             markerfacecolor='None',
                                             markeredgewidth=0.5,
                                             figure=container)
                container.lines.extend([hl])
                self._objs.append(weakref.ref(hl))
                a.figobj_hl.append(hl)
        else:
            for a in alist:
                for hl in a.figobj_hl:
                    container.lines.remove(hl)
                a.figobj_hl = []
#
#   def hit_test
#

    def get_artist_extent(self, a):
        try:
            box = a.get_window_extent().get_points()
            return [box[0][0], box[1][0], box[0][1], box[1][1]]
        except:
            # if get_window_extent fails, it drow somthing
            xd, yd = self.get_device_point(0)
            return [xd, yd, xd+3, yd+3]

    def dragstart_a(self, a, evt):
        redraw = super(FigText, self).dragstart_a(a, evt)
        self._drag_backup = (a.get_position(), a.get_size())
        if self._picker_a_type == 'edge':
            self._picker_a_type = 'area'
        return redraw

    def drag_update_textpos(self, a):
        sx = min([self._st_extent[0], self._st_extent[1]])
        sy = min([self._st_extent[2], self._st_extent[3]])
        px = min([self._drag_rec[0], self._drag_rec[1]])
        py = min([self._drag_rec[2], self._drag_rec[3]])

        sa = np.array([sx, sy]).reshape(1, 2)
        sd = a.get_transform().inverted().transform(sa)
        pa = np.array([px, py]).reshape(1, 2)
        pd = a.get_transform().inverted().transform(pa)
        x = pd.flat[0] - sd.flat[0] + self._drag_backup[0][0]
        y = pd.flat[1] - sd.flat[1] + self._drag_backup[0][1]

        r = (float(self._drag_rec[1]-self._drag_rec[0]) /
             float(self._st_extent[1]-self._st_extent[0]))

        return x, y, self._drag_backup[1]*abs(r)

    def drag_a(self, a, evt, shift=None, scale=None):
        #        print  self._picker_a_type
        if self._picker_a_type == 'area':
            shift = evt.guiEvent.ShiftDown()
        else:
            shift = True
        redraw, scale = super(FigText, self).drag_a(a, evt,
                                                    shift=shift, scale=scale)

        return redraw, scale

#    def dragdone_a_clean(self, a):
#        a=self._artists[0]
#        a.set_x(self._drag_backup[0][0])
#        a.set_y(self._drag_backup[0][1])
#        a.set_size(self._drag_backup[1])
#        super(FigText, self).dragdone_a_clean(a)

    def dragdone_a(self, a, evt, sfift=None, scale=None):
        if self._picker_a_type == 'area':
            shift = evt.guiEvent_memory.ShiftDown()
        else:
            shift = True
        redraw, scale0 = super(FigText, self).dragdone_a(a, evt,
                                                         shift=shift, scale=scale)

        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()

#        hist = self.get_root_parent().app.history
        h = self.scale_artist(scale0, action=True)
        GlobalHistory().get_history(window).make_entry(h)
        return 0, scale0

    def scale_artist(self, scale, action=True):
        st_extent = self.get_artist_extent(self._artists[0])
        rec = geom.scale_rect(st_extent,
                              scale)
        a1 = self.move_gp_points(0, rec[0]-st_extent[0],
                                 rec[2]-st_extent[2], action=True)
        a = self._artists[0]
        s = a.get_size()*(scale[0]+scale[3])/2
        a2 = UndoRedoArtistProperty(a, 'size', s)
        return [a2, a1]

    def canvas_menu(self):
        def onClipTextByAxes(evt, figobj=self):
            action1 = UndoRedoFigobjProperty(figobj._artists[0],
                                             'clip', not self.getp('clip'))
            window = evt.GetEventObject().GetTopLevelParent()
            hist = GlobalHistory().get_history(window)
            hist.make_entry([action1], menu_name='clipping')
        if not self._2d_text:
            return []
        m = self.gp_canvas_menu(self.get_gp(0))
        if self.get_figaxes() is not None:
            if self.getp('clip'):
                txt = "^Clip by axes"
            else:
                txt = "*Clip by axes"
            m.extend([(txt, onClipTextByAxes, None), ])
        return m
#        return self.gp_holder_canvas_menu()

    def load_data(self, fid=None):
        FigObj.load_data(self, fid)
#        GenericPointsHolder.load_data(self, fid)

    def set_multialignment(self, value, a):

        ovalue = self.getp('multialignment')
        self.setp('multialignment', str(value))

        # changing multialinment also need to
        # change horizontal alignment of artists
        # this is to keep the position the same
        # after making two changes
        #  I am commenting out this adjustment since
        #  it may be better to change the postion and
        #  let a user to adjust it.
#        box=a.get_window_extent().get_points()
#        dx = abs(box[0][0] - box[1][0])
#        xd, yd = self.get_device_point(0)
#        d = {'left': 0, 'center':0.5, 'right':1}
#        shift = dx*(d[value] - d[ovalue])
#        self.set_device_point(0, xd+shift, yd)
        self.refresh_artist()

    def get_multialignment(self, a):
        return self.getp('multialignment')

    def save_data2(self, data=None):
        def check(obj, name):
            return obj.getp(name) is obj.getvar(name)
        if data is None:
            data = {}
        var = {
            #               'x':check(self,'x'),
            #               'y':check(self,'y'),
            #               'z':check(self,'z'),
            's': check(self, 's')}

#        if var["x"] is not True: var["xdata"] = self.getp("x")
#        if var["y"] is not True: var["ydata"] = self.getp("y")
#        if var["z"] is not True: var["zdata"] = self.getp("z")
        if var["s"] is not True:
            var["sdata"] = self.getp("s")

        data['FigText'] = (1, var)
        data = super(FigText, self).save_data2(data)
        return data

    def load_data2(self, data):
        if not self.hasvar('fontfamily'):
            self.setvar("fontfamily", 'sans-serif')
            self.setvar("fontstyle",  'normal')
            self.setvar("fontweight", 'roman')
            self.setp("fontfamily", 'sans-serif')
            self.setp("fontstyle",  'normal')
            self.setp("fontweight", 'roman')
        if not self.hasvar('multialignment'):
            self.setvar("multialignment", 'left')
            self.setp("multialignment", 'left')

        d = data['FigText']
        super(FigText, self).load_data2(data)
        var = d[1]
#        names = ["x", "y", "z", "s"]
        names = ["s"]

        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def _eval_s(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            x, y, z = self.eval("x", "y", "z")
            if (x is not None and
                    y is not None):
                self.set_gp_point(0, x, y)
            if not success:
                return None, None, None, None
        if self.get_figaxes() is not None:
            '''
            in case of 3d, it does not use generic_point,
            since the position of artist changes depending
            on view. This means that it can not be dragged
            by mouse...
            perhaps, I need to add three d object dragging
            in a generic way....
            '''
            if self.get_figaxes().get_3d():
                x, y, z = self.eval("x", "y", "z")
                self._2d_text = False
                return x, y, z, self.getp('s')

        x, y = self.get_gp_point(0)
        return [x, y, None, self.getp('s')]
#        return  self.getp(("x", "y", "z", "s"))

    def convert_to_tex_style_text(self, mode=True):
        from ifigure.utils.cbook import tex_escape_equation
        if len(self._artists) == 0:
            return
        if mode:
            s = self._artists[0].get_text()
            self.setp('s', s)
            self._artists[0].set_text(tex_escape_equation(str(s)))
        else:
            s = self.getp('s')
            self._artists[0].set_text(s)
