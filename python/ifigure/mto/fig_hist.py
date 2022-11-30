#
#   fig_hist
#
#       object to support histgram
#
#       note that this object itself does not support
#       multiple dataset. Multiple dataset is handled
#       in book_viewer_interactive::hist
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, CUser, ZUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import sys
import weakref
import numpy as np
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
from scipy.interpolate import griddata, bisplrep, bisplev, interp2d
from ifigure.utils.cbook import ProcessKeywords
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox
from ifigure.utils.args_parser import ArgsParser
from matplotlib.colors import Colormap
from matplotlib.patches import Rectangle
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists, GlobalHistory

#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigHist')

default_kargs = {}


class FigHist(FigObj, XUser, YUser, ZUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._tri = None
            for key in default_kargs:
                if not obj.hasp(key):
                    obj.setp(key, default_kargs[key])
                if not obj.hasvar(key):
                    obj.setvar(key, default_kargs[key])
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_var('x', ['any'])
#        p.set_default_list(default_kargs)
        p.add_key('alpha', 1.0)
        p.add_key('color', 'b')

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('x', 'alpha', 'color'):
            obj.setvar(name, v[name])

        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args, **kywds):
        self._data_extent = None
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)

        self._pick_pos = None
        self._cb_added = False
        self._n = None
        self._bins = None
        self._hit_a = None
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigHist, self).__init__(**kywds)

    @classmethod
    def isFigHist(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'hist'

    @classmethod
    def property_in_file(self):
        return (['color', 'alpha', 'linestyle', 'linewidth'] +
                super(FigHist, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return ["color_2", "linewidth_2", "plinestyle_2",  "alpha_2"]

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ([] +
                super(FigHist, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'image.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        super(FigHist, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)

    '''    
    def _args2var(self):
        names0 = self.attr_in_file()
        names  = ["x","y", "z"] + names0
        use_np = [True]*3 + [False]*len(names0)
        values = self.put_args2var(names,
                                   use_np) 
        x, y, z, = values[:3]
        if x is None: return False
        if y is None: return False

        return True
    '''

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
#           if self.get_figaxes().get_3d(): return
        if self.isempty() is False:
            return
        lp = self.getp("loaded_property")
        x = args = self.getvar('x')
        if lp is None or len(lp) == 0:

            if self.get_figaxes().get_3d():
                args = (x,)
            else:
                args = (x,)

            kywds = self._var["kywds"].copy()
            kywds['alpha'] = self.getvar('alpha')
            kywds['color'] = self.getvar('color')
            n, bins, patches = container.hist(*args,
                                              **kywds)
            self.set_artist(patches)
        else:
            if self.get_figaxes().get_3d():
                args = (x,)
            else:
                args = (x,)
            kywds = lp[0]
            '''
               kywds['s'] = self.getvar('s')*self.getvar('sscale')               
               kywds['c'] = self.getvar('c')
               kywds['marker']  = self.getvar('marker')                              
               '''
            n, bins, patches = container.hist(*args,
                                              **kywds)
            self.set_artist(patches)
        self._n = n
        self._bins = bins
        self.delp("loaded_property")

    def call_adjust_range(self):
        parent = self.get_figaxes()
        if parent is not None:
            parent.adjust_axes_range()

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = self._artists

        self.store_loaded_property()
#        self.highlight_artist(False, artistlist)
        for a in artistlist:
            a.remove()

        super(FigHist, self).del_artist(artistlist)

    def highlight_artist(self, val, artist=None):
        if artist is None:
            alist = self._artists
        else:
            alist = artist

        container = self.get_container()
        figure = self.get_figpage()._artists[0]

        if val == True:
            x = self.getvar('x')
            if self.get_figaxes().get_3d():
                args = (x,)
            else:
                args = (x, )

            x0, y0 = container.transAxes.transform((0, 0))
            x1, y1 = container.transAxes.transform((1, 1))
            bbox = Bbox([[x0, y0], [x1, y1]])

            for a in alist:
                hl = [Rectangle(p.get_xy(),
                                p.get_width(),
                                p.get_height(),
                                facecolor='black',
                                fill=True,
                                alpha=0.5,
                                figure=figure,
                                transform=container.transData)
                      for p in self._artists]
                a.figobj_hl = hl
                for aa in hl:
                    aa.set_clip_box(bbox)
                    aa.set_clip_on(True)
                    figure.patches.append(aa)
        else:
            for a in self._artists:
                for hl in a.figobj_hl:
                    if hl in figure.patches:
                        figure.patches.remove(hl)
                a.figobj_hl = []

    def picker_a(self, artist, evt):
        hit, extra = artist.contains(evt)
        if hit:
            self._hit_a = artist
            return True,  {'child_artist': artist}
        else:
            self._hit_a = None
            return False, {}

    def canvas_menu(self):
        if self._hit_a is None:
            return super(FigHist, self).tree_viewer_menu()
        menus = ([("Generate patch",   self.onGeneratePatch, None), ] +
                 super(FigHist, self).canvas_menu())
        return menus

    def onGeneratePatch(self, event):
        from ifigure.mto.fig_fill import FigFill
        if self._hit_a is not None:
            canvas = event.GetEventObject()
            x, y = self._hit_a.get_xy()
            w = self._hit_a.get_width()
            h = self._hit_a.get_height()

            x = [x, x+w, x+w, x, x]
            y = [y, y, y+h, y+h, y]
            obj = FigFill(x, y, color=self.getvar('color'))
            ax = self.get_figaxes()
            name = ax.get_next_name('HistBin')
            ax.add_child(name, obj)
            obj.realize()
            ax.set_bmp_update(False)
            canvas.draw()

            artists = [weakref.ref(obj._artists[0])]
            h = [UndoRedoAddRemoveArtists(artists=artists,
                                          mode=0)]
            window = canvas.GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry(h, menu_name='add histbin')

    def set_linewidth(self, value, a=None):
        for a in self._artists:
            a.set_linewidth(value)

    def get_linewidth(self, a=None):
        v = self._artists[0].get_linewidth()
        return v

    def set_linestyle(self, value, a=None):
        for a in self._artists:
            a.set_linestyle(value)

    def get_linestyle(self, a):
        v = self._artists[0].get_linestyle()
        return v

    def set_alpha(self, value, a=None):
        self.setvar('alpha', value)
        fc = self._artists[0].get_facecolor()
        fc = (fc[0], fc[1], fc[2], value)
        for a in self._artists:
            a.set_alpha(value)
            a.set_facecolor(tuple(fc))

    def get_alpha(self, a):
        return self.getvar('alpha')

    def set_color(self, value, a=None):
        if self.getvar('color') == value:
            return
        for a in self._artists:
            a.set_facecolor(value)
        alpha = self.getvar('alpha')
        self.set_alpha(alpha)

    def get_color(self, a):
        return self.getvar('color')

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x = self.getvar('x')
        xrange = self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])
        return xrange
        x, y, z = self._eval_xyz()
        if x is None:
            return xrange
        if scale == 'log':
            x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        if self._n is not None:
            return self._update_range(yrange, (0, np.nanmax(self._n)))
        else:
            return yrange
#        de = self.get_data_extent()
        x, y, z = self._eval_xyz()
        if x is None:
            return yrange
        if y is None:
            return yrange
        if scale == 'log':
            y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if self.get_figaxes().get_3d():
            return zrange
        else:
            return zrange

    def _eval_xyz(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None
        return self.getp(("x", "y", "z"))

    def _saveload_names(self):
        return ['x', 'y', 'z']

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        names = self._saveload_names()
        var = {name: check(self, name) for name in names}
        for name in names:
            if not var[name]:
                var[name+'data'] = self.getp(name)
        data['FigHist'] = (1, var)
        data = super(FigHist, self).save_data2(data)

        return data

    def load_data2(self, data):
        d = data['FigHist']
        super(FigHist, self).load_data2(data)
        var = d[1]
        names = self._saveload_names()
        for name in names:
            if not name in var:
                var[name] = True
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def get_export_val(self, a):
        return {"n":    self._n,
                "bins": self._bins}
