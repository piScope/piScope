from __future__ import print_function
#  Name   :fig_obj
#
#          base class for fig_obj
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
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.ifigure_config import isMPL2
from ifigure.widgets.canvas.file_structure import *

from ifigure.mto.treedict import TreeDict
#from ifigure.mto.py_script import PyScript
from ifigure.mto.py_code import PyCode
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.mto.metadata import MetadataHolder
import ifigure.utils.geom as geom
import ifigure.events
import logging
import weakref
import traceback
import ifigure.utils.pickle_wrapper as pickle
from matplotlib.lines import Line2D
from ifigure.utils.cbook import isiterable
import numpy as np

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigObj')


def set_mpl_all(artists, prop, value):
    for a in artists:
        m = getattr(a, 'set_'+prop)
        m(value)


def get_mpl_first(artists, prop):
    a = artists[0]
    m = getattr(a, 'get_'+prop)
    return m()


def properties_in_file_0(obj):
    from ifigure.widgets.artist_widgets import listparam
    props = obj._property_in_file(obj)
    return [listparam[p][4] for p in prop if listparam[p][5] == 0]


def properties_in_file_1(obj):
    from ifigure.widgets.artist_widgets import listparam
    props = obj._property_in_file(obj)
    return [listparam[p][4] for p in prop if listparam[p][5] == 1]


def properties_in_file_2(obj):
    from ifigure.widgets.artist_widgets import listparam
    props = obj._property_in_file(obj)
    return [listparam[p][4] for p in prop if (listparam[p][5] == 12
                                              or listparam[p][5] == 2)]


def properties_in_file_3(obj):
    from ifigure.widgets.artist_widgets import listparam
    props = obj._property_in_file(obj)
    return [listparam[p][4] for p in prop if (listparam[p][5] == 13
                                              or listparam[p][5] == 3)]


def mask_negative(z):
    z_masked = np.ma.masked_array(z)
    z_masked[z <= 0] = np.ma.masked
    return z_masked

# class FigObj(PyScript):


class FigObj(TreeDict, MetadataHolder):
    '''
    FigObj:
       baseclass of all figure object

    '''
    default_rasterized = False

    def __new__(cls, *args, **kargs):
        obj = TreeDict.__new__(cls, *args, **kargs)

        # attr variable is used to control
        # matplotlib, and intended not to seen
        # by users

        obj._attr = {}
        obj._artists = []
        obj._mappable = None
        obj._a_update = False
        obj._update_client = []
        obj._isPageObj = False
        # _axes is a weak reference to fig_axes
        obj._fig_axes = []
        obj._picker_a_type = 'area'
        obj._picker_a_loc = 3
        obj._picker_a_mode = 0
        obj._pickmask = False
        obj._drag_hl = None
        obj._bmp = None
        obj._bmp_update = False
        obj._container_idx = 0
        obj._data_extent = None

        obj._floating = False
        # True if obj is floating on axes
        # used for inset_axes, colorbar, legend
        obj._cursor1 = []
        obj._cursor1_a = None
        obj._cursor2 = []
        obj._cursor2_a = None
        obj._cursor_range = (-np.inf, np.inf)
        obj._cursor_data = [tuple(), tuple(), tuple()]
        obj._eval_fifo_length = 100
        obj._eval_mode = 'replace'
        return obj

#    def __repr__(self):
#        return self.get_full_path()

    def __init__(self, *args, **kywds):
        #        self._container=None

        kywds, parent = self._process_kywd2(kywds, 'parent', None)
        kywds, src = self._process_kywd2(kywds, 'src', None)
        kywds, zorder = self._process_kywd2(kywds, 'zorder', 1)
        kywds, rasterized = self._process_kywd2(kywds, 'rasterized',
                                                self.default_rasterized)
        self._show_scriptmenu = False

        super(FigObj, self).__init__(parent=parent, src=src)
        self._has_private_owndir = True
        #   at this point all arguments should have
        #   been processed. Here, the left over is
        #   kept and will be simply passed to
        #   artist generator
        self.setp('use_var', True)
        self.setp('zorder', zorder)
        self.setp('rasterized', rasterized)
        self.setp('frameart', False)
        self.setp('noclip3d', False)
        self.setp("args", args)
        if len(args) != 0:
            logging.warning(
                "FigObj:len(args) != 0: Not all arguments may not have processed")
            print(self)
            print(args)
        #  Properties of figobj have different
        #  level of complexity
        #
        #  1) some mpl routins return an artist,
        #   editting those property makes sense.
        #   for such an property,
        #     1) palette edit artist property
        #        directly
        #     2) cut/paste, save/load read these
        #        property from artists
        #     3) keyword unsupported by figobj
        #        is stored in _var and used to
        #        generate artist first time.
        #
        #
        #  2) Other mpl routine need a special care.
        #   For example, contour returns patchs.
        #   it is not possible to edit these patch
        #   properteis to change number of levels.
        #   In such case, generate_artist needs
        #   to call mpl everytime when those properties
        #   are changed.

        #
        #     1) palette edit _attr in figobj. these
        #        are set when artist are generated.
        #
        #     2) cut/paste, save/load read these
        #        property from artists
        #

        #  3) and most complicated case is when an
        #      figobj needs to handle both. this case
        #      is not yet implemented.
        #      Switching from hotizontal to vertical
        #      line in axsplan/axline will be such a
        #      case

        #   keyword argments handled by figobj is
        #   split from the list.
        #   the rest are stored and will be passed
        #   artist generator
        #   extracted keywords are copyed to _attr
        #   when an atrist is generated, and can
        #   be edited from palette.

        self.setvar("kywds", kywds)

    @classmethod
    def isFigObj(self):
        return True

    def isPageObj(self):
        return self._isPageObj

    @classmethod
    def get_namebase(self):
        return 'figobj'

    @classmethod
    def allow_outside(self):
        ### if fig_obj can be dragged outside of axes ###
        return False

    @classmethod
    def property_in_file(self):
        # define artist property read by mpl.getp and saved in file
        return ['zorder', 'rasterized']
#    @classmethod
#    def _property_in_file(self):
#        ###define artist property read by mpl.getp and saved in file
#        return ['zorder', 'use_var', 'rasterized']

    @classmethod
    def property_in_palette(self):
        # define artist property or _attr shown in palette
        # this function retuns list of key in listparam defined in
        # artist_widgets.py. the 4th field listparam is the name
        # of property read by either mpl.getp (from artist) or
        # figobj.getp (from figobj)
        return []

    @classmethod
    def property_in_palette_axes(self):
        # define artist property or _attr shown
        # in the second panel (axes panel) of property editor
        # the format of return value is the same
        # as property_in_palette(self)
        return []

    @classmethod
    def property_for_shell(self):
        # define artist property which can be edited from shell
        # by default, this returns the same thing as property_in_palette
        # fig_page and fig_axes needs to implement this differently
        # since section editor, axes editor is different from artist_editor
        return self.property_in_palette()

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return ['zorder', 'use_var', 'rasterized', 'frameart', 'noclip3d']

    @classmethod
    def can_have_child(self, child=None):
        return isinstance(child, FigObj)

    @classmethod
    def isCompound(cls):
        '''
        Compount FigObj is a type of FigObj which has a mulltiple
        pickable objects. This is introduced to support GL object
        using array_idx. See FigCompound
        '''
        return False

    def isSelected(self):
        '''
        Compound FigObj could return False
        '''
        return True

    def var2p(self, list):
        '''

        '''
        print('FigObj::var2p is obsolete, use put_args2var')
        a = {}
        for name in list:
            if not self.hasvar(name):
                continue
            v = self.eval(name)
            self.setp(name, v)
            a[name] = v
        return a

    def put_args2var(self, names, use_np):
        '''
        a utility to perform eval and put value
        to _attr (setp)
        '''
        ans = []
        k = 0
        for name in names:
            if not self.hasvar(name):
                ans.append(None)
                continue
            else:
                v = self.eval(name, np=use_np[k])
                self.setp(name, v)
                ans.append(v)
            k = k+1
        return tuple(ans)

    def handle_use_var(self):
        '''
        args2var should be implemented in subclass.
        used to gether with put_args2var, subclass
        needs to specify the name of values and
        to handle exceptional cases.
        '''
        if self.getp('use_var'):
            success = self.args2var()
            if success:
                self.setp("use_var", False)
                return True
            else:
                return False

    def process_kywd(self, kywds, name, d):
        '''
        process keyword given to __init__
        store them to var
        '''
        if name in kywds:
            self.setvar(name, kywds[name])
            del kywds[name]
        else:
            self.setvar(name, d)
        return kywds

    def get_container(self, *args, **kywds):
        '''
        this assumes that the parent object has
        only one artist and my artist is child of
        it. if it is not the case, this should
        be overwritten
        '''
        ax = self.get_figaxes()
        if ax is None or ax is self:
            page = self.get_figpage()
            if len(page._artists) == 0:
                return None
            return page._artists[0]
        else:
            if len(ax._artists) == 0:
                return None
            if len(ax._artists) > self._container_idx:
                return ax._artists[self._container_idx]
            else:
                return ax._artists[0]

    def set_parent(self, parent):
        from ifigure.mto.fig_page import FigPage
        from ifigure.mto.fig_axes import FigAxes
        super(FigObj, self).set_parent(parent)
        while parent != None:
            if isinstance(parent, FigPage):
                self._isPageObj = True
                return
            if isinstance(parent, FigAxes):
                self._isPageObj = False
                return
            parent = parent.get_parent()

    def get_mappable(self):
        '''
        return a list of scalar mappable artist
        '''
        return []

    def set_bmp(self, bmp, x, y):
        self._bmp = (bmp, x, y)
        self._bmp_update = True

    def get_bmp(self):
        return self._bmp

    def get_bmp_update(self):
        # true if bitmap is updated
        return self._bmp_update

    def set_bmp_update(self, value):
        # bmp_update should set figaxes's _bmp_update
        obj = self.get_figaxes()
        if obj is not None:
            #           if obj.get_full_path() == 'proj.shot_summary.page1.axes2':
            #               traceback.print_stack()
            obj._bmp_update = value

    def canvas_selected(self):
        pass

    def canvas_unselected(self):
        pass

    def isDraggable(self):
        return False

    def destroy(self, clean_owndir=True):
        # destory tree is more complicated than making it.
        ### idea is...
        # 1) walking through the tree is done in treedict
        # 2) fig_obj takes care of self._artists and
        # artists.figobj. this was done by calleing
        # del_artists()
        # 3) derived classes takes care of the relation
        # between an artists and its container.
        # this way,derived class does not need to impliment
        # its destory by default.(del_artist() could have been
        # mergined in destroy(), it is done for the symmetry
        # of having generate_artist() and del_artist()
        self.set_bmp_update(False)
        if self._drag_hl is not None:
            self._drag_hl.figure.lines.remove(self._drag_hl)
            self._drag_hl = None
        self.del_artist(delall=True)
        for key in self._attr:
            self._attr[key] = None
        # calles super class which kills children first
        super(FigObj, self).destroy(clean_owndir=clean_owndir)

    def generate_artist(self, *args, **kywds):
        dprint1("generate_artist should have be overwrittne", self)

        # self._container=container
    def set_artist(self, alist0):
        if isiterable(alist0):
            alist = alist0
        else:
            alist = [alist0]
        self._artists = alist
        for artist in self._artists:
            artist.figobj = self
            artist.figobj_hl = []
            artist.set_zorder(self.getp('zorder'))

    def generate_cursor(self, evt, idx):
        # called during mouse click in cursor mode
        return []

    def reset_cursor_range(self, evt, idx):
        # called for 2D data cursor
        pass

    def update_cursor(self, evt, idx):
        # called during mousedrag in cursor mode
        pass

    def valid_cursor(self):
        # called just before drawing cursor
        return []

    def refresh_artist_data(self):
        # default action when data is changed...
        # redo artist generation
        if not self.isempty():
            self.del_artist(delall=True)
        if self.isempty() and not self._suppress:
            self._data_extent = None  # do I need this???
            self.generate_artist()
        self.set_bmp_update(False)

    def del_artist(self, artist=None, delall=False):
        # this routine isolate figobj and artists
        # before calling this process, artist should be
        # removed from container. this task should be
        # implemented in derived classes

        # note: subclass delete all childrens' artists
        # therefore del_artists need to be paired with
        # realize

        if delall:
            artistlist = self._artists
        else:
            artistlist = artist
        if artistlist is None:
            return

        for a in artistlist:
            a.figobj = None
            a.figobj_hl = []
        b = [a for a in self._artists if artistlist.count(a) == 0]
        self._artists = b

    def reset_artist(self, load_data=None):
        self.del_artist(delall=True)
        self.delp('loaded_property')
        self.setp('use_var', True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        if load_data is not None:
            self.load_data2(load_data)
        self.generate_artist()

    def get_artist(self, idx=None):
        if idx is not None:
            return self._artists[idx]
        return self._artists

    def set_pickmask(self, value):
        self._pickmask = value

    def get_artists_for_pick(self):
        return self._artists

    def get_first_artist(self):
        if len(self._artists) == 0:
            return None
        return self._artists[0]

    def walk_artists(self):
        for td in self.walk_tree():
            for a in td._artists:
                yield a

    def walk_allartists(self):
        def walk_children(a):
            yield a
            for a2 in a.get_children():
                for a3 in walk_children(a2):
                    yield a3
        for a in self._artists:
            for x in walk_children(a):
                yield x

    def walk_figobj(self):
        for obj in self.walk_tree():
            if isinstance(obj, FigObj):
                yield obj

    def set_zorder(self, z1, a=None):
        self.setp('zorder', z1)
        for a in self._artists:
            a.set_zorder(z1)
        if len(self._artists) != 0:
            self.set_bmp_update(False)

    def get_zorder(self, a=None):
        return self.getp('zorder')

    def get_artists_for_frameart(self):
        return self._artists

    def set_frameart(self, v, a=None):
        if self.get_figaxes() is not None:
            dprint1("axes object cannot become Frame Artist")
            return
        if self.get_figpage() is None:
            dprint1("object is not placed in page")
            return
        self.setp('frameart', v)
        for a in self.get_artists_for_frameart():
            a._is_frameart = v

        page = self.get_figpage()
        if v:
            page.add_frameart(self)
        else:
            page.rm_frameart(self)

    def get_frameart(self, a=None):
        return self.getp('frameart')

    def swap_zorder(self, z1, z2, get_action=False):
        page = self.get_figpage()
        objs = [figobj for figobj in page.walk_figobj()
                if figobj.getp('zorder') == z2]

        h = [] if get_action else None
        for figobj in objs:
            if get_action:
                h.append(UndoRedoFigobjMethod(
                    figobj._artists[0], 'zorder', z1))
            else:
                figobj.set_zorder(z1)
        if get_action:
            h.append(UndoRedoFigobjMethod(self._artists[0], 'zorder', z2))
        else:
            self.set_zorder(z1)
        return h

    def move_zorder_forward(self, get_action=False):
        z1 = self.getp('zorder')
        z2 = z1+0.001
        return self.swap_zorder(z1, z2, get_action=get_action)

    def move_zorder_backward(self, get_action=False):
        z1 = self.getp('zorder')
        z2 = z1-0.001
        return self.swap_zorder(z1, z2, get_action=get_action)

    def set_zorder_front(self, get_action=False):
        page = self.get_figpage()
        if self.get_frameart():
            l1 = [figobj.getp('zorder') for figobj in page.walk_figobj()
                  if not figobj._floating and figobj.get_frameart()]
        else:
            l1 = [figobj.getp('zorder') for figobj in page.walk_figobj()
                  if not figobj._floating and not figobj.get_frameart()]
        l2 = [a.zorder for a in page.walk_allartists()]

        ret = [] if get_action else None
        if self.get_zorder() <= max(l1):
            # if i am only figobj at front, do nothing
            if l1.count(self.get_zorder()) == 1 and self.get_zorder() == max(l1):
                return ret
            if get_action:
                return [UndoRedoFigobjMethod(self._artists[0], 'zorder', max(l1) + 0.001)]
            else:
                self.set_zorder(max(l1) + 0.001)
        else:
            if get_action:
                return [UndoRedoFigobjMethod(self._artists[0], 'zorder', max(l1+l2) + 0.001)]
            else:
                self.set_zorder(max(l1+l2) + 0.001)

    def set_zorder_bottom(self, get_action=False):
        page = self.get_figpage()
        a = []
        if self.get_frameart():
            l1 = [figobj.getp('zorder') for figobj in page.walk_figobj()
                  if not figobj._floating and figobj.get_frameart()]
        else:
            l1 = [figobj.getp('zorder') for figobj in page.walk_figobj()
                  if not figobj._floating and not figobj.get_frameart()]
        l2 = [a.zorder for a in page.walk_allartists()]
        #print(l1, l2)
        if get_action:
            return [UndoRedoFigobjMethod(self._artists[0], 'zorder', min(l1+l2) - 0.001)]
        else:
            self.set_zorder(min(l1+l2) - 0.001)

    def set_rasterized(self, value=None, a=None):
        '''
        set_rasterized(True or False) : change rasterized and apply it to 
                                        artist
        set_rasterized(): set artist.rasterrized. this is used in 
                          generate_artist or make_artist
        '''

        if value is not None:
            self.setp('rasterized', value)
        value = self.getp('rasterized')
        for a in self._artists:
            a.set_rasterized(value)

    def get_rasterized(self, a=None):
        return self.getp('rasterized')

    def get_rasterized_action(self, value):
        if len(self._artists) == 0:
            return []
        return [UndoRedoFigobjMethod(self._artists[0], 'rasterized', value)]

    def realize(self, realize_gpholder='both'):
        from ifigure.mto.figobj_gpholder import FigObjGPHolder

        do_generate = True

        if realize_gpholder == 'gp' and not isinstance(self, FigObjGPHolder):
            do_generate = False
        if realize_gpholder == 'non_gp' and isinstance(self, FigObjGPHolder):
            do_generate = False

        if not self._suppress:
            if do_generate:
                self.generate_artist()
            for objname, figobj in self.get_children():
                figobj.realize(realize_gpholder=realize_gpholder)
        else:
            if not self.isempty():
                self.del_artist(delall=True)
            for objname, figobj in self.get_children():
                figobj.realize(realize_gpholder=realize_gpholder)

    '''
       artist update...
       it provides the last moment update (just before draw
       call) of artists. it can be useful if an object 
       property depends on other object.
       However, it does not follow the order of depencency,
       and does not guarantee that referred object is 
       already updated. Therefore, the artist update
       should be performed without relying on this whenever
       it is possible
    '''

    def update_artist(self):
        if self._a_update:
            self.do_update_artist()
            self._a_update = False
#        if self._suppress is False:
        for objname, figobj in self.get_children():
            figobj.update_artist()
#       else:
#            for objname, figobj in self.get_children():
#                figobj.update_artist()

    def do_update_artist(self):
        # this should be implemented in derived class
        pass

    def set_update_artist_request(self, *argv, **argk):
        self._a_update = True

    def _clean_update_client_list(self):
        for figobj in self._update_client:
            if figobj() is None:
                self._update_client.remove(figobj)

    def set_client_update_artist_request(self):
        for figobj in self._update_client:
            if figobj() is not None:
                figobj().set_update_artist_request()
            else:
                self._update_client.remove(figobj)

    def add_update_client(self, figobj):
        check = False
        self._clean_update_client_list()
        for figobj2 in self._update_client:
            if figobj2() is figobj:
                return
        self._update_client.append(weakref.ref(figobj))

    def remove_update_client(self, figobj):
        self._clean_update_client_list()
        for figobj2 in self._update_client:
            if figobj2() is figobj:
                self._update_client.remove(figobj2)

    def isempty(self):
        return len(self._artists) == 0

    def highlight_artist(self, val, artist=None):
        pass

    def has_highlight(self, artist):
        return len(artist.figobj_hl) != 0

    def canvas_menu(self):
        if self.get_rasterized():
            return [("Export",  self.onExport, None),
                    ("Copy object path",  self.onCopyPath, None),
                    ("^Rasterized",  self.onUnsetRasterize, None), ]
        else:
            return [("Export",  self.onExport, None),
                    ("Copy object path",  self.onCopyPath, None),
                    ("*Rasterized",  self.onSetRasterize, None), ]

    def onCopyPath(self, evt):
        import wx
        path = self.get_full_path()
        if wx.TheClipboard.Open():
            # This data objects are held by the clipboard,
            # so do not delete them in the app.
            wx.TheClipboard.SetData(wx.TextDataObject(path))
            wx.TheClipboard.Close()

    def onUnsetRasterize(self, evt):
        from ifigure.widgets.undo_redo_history import GlobalHistory
        a = self.get_rasterized_action(False)
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='unrasteraized')

#        self.set_rasterized(False)

    def onSetRasterize(self, evt):
        from ifigure.widgets.undo_redo_history import GlobalHistory
        a = self.get_rasterized_action(True)
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(a, menu_name='rasteraized')

#        self.set_rasterized(True)
    def set_container_idx(self, value, a=None):

        def _set_ax_params(figaxes, param):
            for b in figaxes.get_axes_artist_by_name(param.name):
                param.set_artist_rangeparam(b)
                param.set_tickparam(b, figaxes)

        if isinstance(self, XUser):
            self.unset_ax()
        if isinstance(self, YUser):
            self.unset_ay()
        if isinstance(self, ZUser):
            self.unset_az()
        #if isinstance(self, CUser): self.unset_ac()
        if self.isempty():
            self._container_idx = value
        else:
            self.del_artist(delall=True)
            self._container_idx = value
            self.generate_artist()
        if not self.isPageObj():
            figaxes = self.get_figaxes()
            params = figaxes.get_axis_param_container_idx(value)
            if isinstance(self, XUser) and 'x' in params:
                self.set_ax(params['x'])
                _set_ax_params(figaxes, params['x'])
            if isinstance(self, YUser) and 'y' in params:
                self.set_ay(params['y'])
                _set_ax_params(figaxes, params['y'])
            if isinstance(self, ZUser) and 'z' in params:
                self.set_az(params['z'])
                _set_ax_params(figaxes, params['z'])
            # if isinstance(self, CUser) and 'c' in params:
            #   self.set_ac(params['c'])

    def get_container_idx(self, a=None):
        return self._container_idx

    def set_caxis_idx(self, value, a=None):
        figaxes = self.get_figaxes()
        if figaxes is None:
            return

        if isinstance(self, CUser):
            self.unset_ac()
            if value >= len(figaxes._caxis):
                dprint1('len(self._caxis) is shorter than request...')
                return
            param = figaxes._caxis[value]
            self.set_ac(param)
            for a2 in self.get_mappable():
                param.set_crangeparam_to_artist(a2)

    def get_caxis_idx(self, a=None):
        if self.get_figaxes() is None:
            return None
        return self.get_axis_param_idx()[-1]

    def get_axis_param_idx(self):
        if self.get_figaxes() is None:
            return [None]*4
        fa = self.get_figaxes()
        value = [-1, -1, -1, -1]
        for k, p in enumerate(fa._xaxis):
            if self in [r() for r in p._member]:
                value[0] = k
        for k, p in enumerate(fa._yaxis):
            if self in [r() for r in p._member]:
                value[1] = k
        for k, p in enumerate(fa._zaxis):
            if self in [r() for r in p._member]:
                value[2] = k
        for k, p in enumerate(fa._caxis):
            if self in [r() for r in p._member]:
                value[3] = k
        return value

    def canvas_axes_selection_menu(self, fig_axes):
        def append_axis_menu(m, ll, name, figobj, dir, idx):
            if len(ll) < 2:
                return m
            m.append((name, None, None))
            for i, x in enumerate(ll):
                def handler(evt, obj=figobj, name=x.name,
                            value=i, direction=dir):
                    canvas = evt.GetEventObject()
                    canvas.change_figobj_axes(figobj, value, direction)
                if i == idx:
                    m.append(('^'+x.name, handler, None))
                else:
                    m.append(('*'+x.name, handler, None))
            m.append(('!',  None, None))
            return m
        idx = self.get_axis_param_idx()
        m = []
        m = append_axis_menu(m, fig_axes._xaxis, '+X axis',
                             self, 'x', idx[0])
        m = append_axis_menu(m, fig_axes._yaxis, '+Y axis',
                             self, 'y', idx[1])
        m = append_axis_menu(m, fig_axes._caxis, '+C axis',
                             self, 'c', idx[3])

        return m

    def _export_shell(self, data, data_name, text):
        '''
        note: text is not used anymore
        '''
        import ifigure.server
        s = ifigure.server.Server()
        if s.info()[0]:
            print('Sending data to client()')
#           ifigure.server.Server().export_data(data)
            ifigure.server.Server().export_data((data, data_name,
                                                 text))
        text = '\n'
        for key in data:
            flag = self.write2shell(data[key], key)
            if flag is None:
                continue
            if flag:
                text = text + key + ' is updated\n'
            else:
                text = text + key + ' is created\n'
        dprint2(text)

        app = self.get_app()
        if app is not None:
            import ifigure.widgets.dialog as dialog
            ret = dialog.message(app, text, 'Export', 0)
            app.shell.SendShellEnterEvent()

    def onExport(self, event):
        canvas = event.GetEventObject()
        sel = [a() for a in canvas.selection]
        for a in self._artists:
            if a in sel:
                fig_val = self.get_export_val(a)
                self._export_shell(fig_val, 'fig_val', '')
        event.Skip()

    def export(self,  a=None):
        if a is None:
            sel = self._artists
        else:
            if not a in self._artists:
                return []
            sel = [a]

        return [self.get_export_val(a) for a in sel]

    def get_export_val(self, a):
        raise NotImplementedError(
            'get_export_val is missing in '+str(self.__class__))

    def damp_artists(self, fid, artists=None):
        name = self.name
        if artists is not None:
            pickle.dump({"num": len(artists),
                         "name": name}, fid)
        else:
            pickle.dump({"num": 0,
                         "name": name}, fid)

    def load_artists(self, fid, parent):
        # parent should be realized before....
        header = pickle.load(fid)
        self._artists = []
        # self._artists=[None]*header["num"]
        containers = parent.get_artist()
        self._container = containers[0]

        tmp = parent.get_childnames()
        if tmp.count(header["name"]) == 0:
            name = header["name"]
        else:
            name = self.get_next_name(self.get_namebase())

        parent.add_child(name, self)

#    this is import iscope....
#    def load(self, fin):
#        print  read_structure(fin)

    def add_figobj(self, name=None, obj=None):
        if obj is None:
            return
        if name is None:
            name = self.get_next_name("figobj")
        return self.add_child(name, obj)

    def del_figobj(self, figobj):
        figobj.destroy()
#        figobj.del_artist(delall=True)
#        self.del_child(figobj)

    def get_figobj(self, ifigobj):
        return self.get_child[ifigobj]

    def add_child(self, *args, **kargs):
        #
        #  figobj::add_child(name, obj, keep_zorder=bool)
        #  figobj::add_child(obj, keep_zorder=bool)
        #       1) set _zorder to the highest in page
        #       2) set axes bmp_update to false
        #
        if len(args) == 2:
            name = args[0]
            obj = args[1]
        elif len(args) == 1:
            obj = args[0]
            name = obj.name

        if 'keep_zorder' not in kargs:
            kargs['keep_zorder'] = False

        figpage = self.get_figpage()
        if not 'z_base' in kargs:
            if figpage is not None:
                z = max([obj2.getp('zorder')
                         for obj2 in figpage.walk_figobj()])
            else:
                z = 1
        else:
            z_base = kargs['z_base']
            z = z_base._z_base

        idx = super(FigObj, self).add_child(name, obj, **kargs)
#        self.get_child(idx=idx).set_bmp_update(False)
        obj.set_bmp_update(False)

        if kargs['keep_zorder']:
            return idx

#        for obj in self.get_child(idx).walk_figobj():
        for obj2 in obj.walk_figobj():
            obj2.setp('zorder', z+0.001)
            z = z+0.001

        if 'z_base' in kargs:
            z_base._z_base = z
        return idx
#
#   Attribute Setter and Getter
#     it "DOES NOT" copy data if all data
#     is taken at once

    def setp(self, *args):  # arg = name, var or var
        if len(args) == 2:
            self._attr[args[0]] = args[1]
        if len(args) == 1:
            self._attr = args[0]

    def getp(self, name=None):
        if name is None:
            return self._attr

        from ifigure.utils.cbook import isiterable_not_string

        if isiterable_not_string(name):
            try:
                return tuple([self._attr.get(n, None) for n in name])
            except:
                import sys
                import traceback
                print(("FigObj::getp error:", sys.exc_info()[0]))
                print(traceback.format_exc())
#              print "fig obj att not found "+name
                return [None]*len(name)
        else:
            try:
                return self._attr[name]
            except Exception:
                #          print "fig obj att not found "+name
                return None

    def delp(self, name=None):
        if name is None:
            return self._attr
        try:
            del self._attr[name]
        except Exception:
            #          print "fig obj att not found "+name
            return None

    def hasp(self, name):
        return name in self._attr


#
#  tree viewer menu
#


    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        #        if self._show_scriptmenu:
        base = super(FigObj, self).tree_viewer_menu()
#        else:
#           base=super(PyCode, self).tree_viewer_menu()
        return [('Show Attribute', self.onShowAtt, None),
                ('Reset Artist', self.onResetArtist, None),
                #                 ('+Evaluate',  None, None),
                #                 ('Replace',    self.onEvalReplace, None),
                #                 ('Append',     self.onEvalAppend, None),
                #                 ('Prepend',      self.onEvalFront, None),
                #                 ('FIFO',       self.onEvalFifo, None),
                #                 ('Config...',  self.onEvalConfig, None),
                #                 ('!',   None, None),
                ('---', None, None)]+base

    def eval_expressions(self, mode=''):
        if mode == '':
            mode = self._eval_mode
        names = self.dynamic_names()
        for name in names:
            v = self.eval(name, np=True)
            if mode == 'replace':
                self.setp(name, v)
            elif mode == 'append':
                v2 = np.concatenate((self.getp(name), v))
                self.setp(name, v2)
            elif mode == 'front':
                v2 = np.concatenate((v, self.getp(name)))
                self.setp(name, v2)
            elif mode == 'fifo':
                l = obj._eval_fifo_length
                print('do something')
                pass

    def onEvalReplace(self, evt=None):
        self.eval_expressions(mode='replace')
        self.del_artist(delall=True)
        self.generate_artist()
        ifigure.events.SendPVDrawRequest(self)

    def onEvalAppend(self, evt=None):
        self.eval_expressions(mode='append')
        self.del_artist(delall=True)
        self.generate_artist()
        ifigure.events.SendPVDrawRequest(self)

    def onEvalFront(self, evt=None):
        self.eval_expressions(mode='front')
        self.del_artist(delall=True)
        self.generate_artist()
        ifigure.events.SendPVDrawRequest(self)

    def onEvalFifo(self, evt=None):
        self.eval_expressions(mode='fifo')
        self.del_artist(delall=True)
        self.generate_artist()
        ifigure.events.SendPVDrawRequest(self)

    def onEvalConfig(self, evt=None):
        pass

    def get_root_figobj(self):
        '''
        find figobj which closest to root in the tree
        this obj is usually book (probably always?)
        '''
        def isFigObj(obj):
            from ifigure.mto.fig_obj import FigObj
            return isinstance(obj, FigObj)
        root = self.get_root_parent()
        for book in self.walk_tree_up(cond=isFigObj):
            pass
        return book

    def get_root_figgrp(self):
        '''
        return FigGrp close to p
        '''
        from ifigure.mto.fig_grp import FigGrp
        p = self
        in_group = False
        while p is not None:
            if isinstance(p, FigGrp):
                in_group = True
                break
            p = p.get_parent()

        if not in_group:
            return None
        while p is not None:
            if not isinstance(p.get_parent(), FigGrp):
                break
            p = p.get_parent()
        return p

    def onDelete(self, e=None):
        ifigure.events.SendPVDeleteFigobj(self)
        return

    def onResetArtist(self, e):
        root = self.get_root_parent()
        book = self.get_root_figobj()

        self.reset_artist()
        ifigure.events.SendPVDrawRequest(self)

    def onShowAtt(self, e):
        from matplotlib.artist import getp
        for key in self._attr:
            print((key, type(self._attr[key])))
        for a in self._artists:
            print(getp(a))

    def onForceUpdate(self, evt):
        print('calling forced update.... check if it is necessary')
        id = evt.GetEventObject()
        app = id.GetTopLevelParent()
        app.deffered_force_layout()

    def onSuppress(self, evt=None):
        self.set_suppress(True)
#        self.realize()
        ifigure.events.SendPVDrawRequest(self)
#        app.draw()
        if evt is not None:
            evt.Skip()

    def onUnSuppress(self, evt=None):
        #        id=evt.GetEventObject()
        #        app=id.GetTopLevelParent()
        self.set_suppress(False)
#        self.realize()
        ifigure.events.SendPVDrawRequest(self)
#        app.draw()
        if evt is not None:
            evt.Skip()

    def set_suppress(self, val):
        super(FigObj, self).set_suppress(val)
        self.realize()
        self.set_bmp_update(False)
###
# plot mode picking/dragging
# the behavior of this mode should be implemented
# in subclasses
###
# Hit test

    def picker(self, artist, evt):
        print('picker is obsolete and should not be called')
        return False, {}
# dragstart : called when drag starts

    def dragstart(self, a, evt):
        redraw = 0  # request to draw canvas 0|1|??
        return redraw
# drag : to show transient usr feedback during drag

    def drag(self, a, evt):
        redraw = 0  # request to draw canvas 0|1|??
        return redraw
# dragdone : finish-up dragging

    def dragdone(self, a, evt):
        redraw = 0  # request to draw canvas 0|1|??
        return redraw

# drag_get_hl (return hl artist)
    def drag_get_hl(self, a):
        return []

    def drag_rm_hl(self, a):
        pass


# Hit test (annotation mode)

    @property
    def ispickable_a(self):
        return True

    def picker_a(self, a, evt):
        hit, extra, type, loc = self.picker_a0(a, evt)
        if hit:
            self._picker_a_type = type
            self._picker_a_loc = loc
        return hit, extra

    def get_artist_extent2(self, a):
        return self.get_artist_extent(a)

    def get_artist_extent(self, a):
        '''
        retrun the extent of artist in device 
        coordinate
        '''
        try:
            #box = a.get_window_extent(a.figure._cachedRenderer)
            box = a.get_window_extent(a.figure.canvas.get_renderer())
            return box.xmin, box.xmax, box.ymin, box.ymax
        except:
            print(('error in get_artist_extent for ', a))
            print(traceback.format_exc())
            return [None]*4
        return [None]*4

    def picker_a0(self, a, evt):
        '''
        generic annotation picker. it check hit to
        rect returned by get_artist_extent

        return value : hit, {}, type, loc
           type : 'area'   aloc =  3: hit in both xy, 1: x hit , 2 y hit
                  'edge'   loc = {0,1,2,3} 
                  'point'  loc = {0,1,2,3} 

        '''
        def checker(a0, b0, b1):
            if (a0 > b0 and a0 < b1):
                return True
            return False
        self._st_p = evt.x, evt.y
        x0d, x1d, y0d, y1d = self.get_artist_extent(a)
        if x0d is None:
            return False, {}, -1, -1
        hit_d = 5

        aloc = 0
        if checker(evt.x, x0d+hit_d, x1d-hit_d):
            aloc = aloc + 1
        if checker(evt.y, y0d+hit_d, y1d-hit_d):
            aloc = aloc + 2
        eloc = 0
        if checker(evt.x, x0d-hit_d, x0d+hit_d):
            eloc = eloc + 1
        if checker(evt.x, x1d-hit_d, x1d+hit_d):
            eloc = eloc + 2
        if checker(evt.y, y0d-hit_d, y0d+hit_d):
            eloc = eloc + 4
        if checker(evt.y, y1d-hit_d, y1d+hit_d):
            eloc = eloc + 8

        if aloc == 0 and eloc == 0:
            type = None
            return False, {}, type, 0
#        print aloc, eloc
        if aloc == 3:
            type = 'area'
            return True, {}, type, aloc
        if ((eloc & 1 != 0 or eloc & 2 != 0) and
                aloc == 2):
            type = 'edge'
            return True, {}, type, eloc
        if ((eloc & 4 != 0 or eloc & 8 != 0) and
                aloc == 1):
            type = 'edge'
            return True, {}, type, eloc
        if (eloc != 1 and eloc != 2 and eloc != 4 and eloc != 8
                and aloc == 0):
            type = 'point'
            return True, {}, type, eloc

        return False, {}, None, 0

# dragstart : called when drag starts
    def dragstart_a(self, a, evt, mode=1):
        '''
        fig_obj::dragstart_a(self, a, evt)
        fig_obj::drag_a(self, a, evt, shift = None)
        fig_obj::dragdone_a(self, a, evt, shift = None)
        these three methods provide generic drag handling 
        in annnotation mode. it calculate new window_extent
        and save it in propoerty. derived classes
        can used it to provide "live-update" of object 
        while drag is happening.
        '''
        redraw = 0
        if mode == 1:
            self._st_extent = self.get_artist_extent(a)

#        self.highlight_artist(False, artist=[a])

        x = [self._st_extent[0],
             self._st_extent[0],
             self._st_extent[1],
             self._st_extent[1],
             self._st_extent[0]]
        y = [self._st_extent[2],
             self._st_extent[3],
             self._st_extent[3],
             self._st_extent[2],
             self._st_extent[2]]
        self.drag_a_add_hl(a, x, y)
#        if self._drag_hl is None:
        return redraw

    # drag : to show transient usr feedback during drag
    def drag_a(self, a, evt, shift=None, scale=None):
        '''
        fig_obj::dragstart_a(self, a, evt)
        fig_obj::drag_a(self, a, evt, shift = None)
        fig_obj::dragdone_a(self, a, evt, shift = None)
        these three methods provide generic drag handling 
        in annnotation mode. it calculate new window_extent
        and save it in propoerty. derived classes
        can used it to provide "live-update" of object 
        while drag is happening.
        '''
        if shift is None:
            shift = evt.guiEvent.ShiftDown()
        loc = self._picker_a_loc
        rec = [x for x in self._st_extent]

        if scale is None:
            if self._picker_a_type == 'area':
                dx = evt.x - self._st_p[0]
                dy = evt.y - self._st_p[1]
                if shift:
                    if abs(dx) < abs(dy):
                        dx = 0
                    else:
                        dy = 0
                rec[0] = rec[0]+dx
                rec[1] = rec[1]+dx
                rec[2] = rec[2]+dy
                rec[3] = rec[3]+dy

            else:
                if ((loc & 1) != 0):
                    rec[0] = evt.x
                if ((loc & 2) != 0):
                    rec[1] = evt.x
                if ((loc & 4) != 0):
                    rec[2] = evt.y
                if ((loc & 8) != 0):
                    rec[3] = evt.y

            if shift and self._picker_a_type != 'area':
                if self._st_extent[1]-self._st_extent[0] != 0:
                    d = (float(self._st_extent[3]-self._st_extent[2]) /
                         float(self._st_extent[1]-self._st_extent[0]))
                else:
                    d = 1
                dy = float(rec[1]-rec[0])*d
                if ((loc & 4) != 0):
                    rec[2] = int(rec[3]-dy)
                if ((loc & 8) != 0):
                    rec[3] = int(rec[2]+dy)

            self._drag_rec = rec
            scale = geom.calc_scale(rec, self._st_extent)
        else:
            rec = geom.scale_rect(rec, scale)
            self._drag_rec = rec

        x = [rec[0], rec[0], rec[1], rec[1], rec[0]]
        y = [rec[2], rec[3], rec[3], rec[2], rec[2]]
        self.drag_a_add_hl(a, x, y)
#        self._drag_hl.set_xdata(x)
#        self._drag_hl.set_ydata(y)

        redraw = 0  # request to draw canvas 0|1|??
        return redraw, scale

    def drag_a_get_hl(self, a):
        if self._drag_hl is None:
            return []
        return [self._drag_hl]

    def drag_a_add_hl(self, a, x, y):
        if self._drag_hl is not None:
            self.drag_a_rm_hl(a)
        self._drag_hl = Line2D(x, y, figure=a.figure,
                               marker='s',
                               linestyle='-',
                               markerfacecolor='None')
        a.figure.lines.extend([self._drag_hl])

    def drag_a_rm_hl(self, a):
        if self._drag_hl is not None:
            a.figure.lines.remove(self._drag_hl)
            self._drag_hl = None

    def dragdone_a_clean(self, a):
        pass

# dragdone : finish-up dragging
    def dragdone_a(self, a, evt, shift=None, scale=None):
        '''
        fig_obj::dragstart_a(self, a, evt)
        fig_obj::drag_a(self, a, evt, shift = None)
        fig_obj::dragdone_a(self, a, evt, shift = None)
        these three methods provide generic drag handling 
        in annnotation mode. it calculate new window_extent
        and save it in propoerty. derived classes
        can used it to provide "live-update" of object 
        while drag is happening.
        '''
#        if self._drag_hl is None: return
        redraw, scale = self.drag_a(a, evt, shift=shift, scale=scale)
        self.drag_a_rm_hl(a)
#        self.dragdone_a_clean(a)
#        self.highlight_artist(True, artist=[a])
        return 0, scale

# scale_artist : scale artist by using sclae...
    def scale_artist(self, scale, action=True):
        pass

###   group/ungroup (ungroup is defined in FigGrp)
    def group(self, member):
        '''
        group figgrp object
        member : list of treedict to be grouped
                 (self is automatically added to 
                  member)
        return a FigGrp containes member. 
        if self has a parent. FigGrp will be
        added to the parent
        '''
        from ifigure.mto.fig_grp import FigGrp
        gp = FigGrp()
        print(member)
        p = self.get_parent()
        if p is not None:
            p.add_child(p.get_next_name(gp.get_namebase()),
                        gp, keep_zorder=True)

        if not self in member:
            member = [self]+member
        for obj in member:
            obj.move(gp, keep_zorder=True)
        return gp

# save/load
#    def save_data(self, fid=None):
#        val={"num_artists":len(self._artists),
#             "format": 2}
#        pickle.dump(val, fid)
#        for a in self._artists:
#           val=self.get_artist_property(a)
#           pickle.dump(val, fid)

#        ps = self.attr_in_file()
#        val = {}
#        for name in ps:
#           val[name]=self.getp(name)

#        secret="loaded_property"
#        if self.hasp(secret):
#           val[secret]=self.getp(secret)
#        pickle.dump(val, fid)

    def store_loaded_property(self):
        if self.hasp("loaded_property"):
            return False
        if (not self.isempty() and
                not self.hasp("loaded_property")):
            ap = [self.get_artist_property(a) for a in self._artists]
            self.setp("loaded_property", ap)
        if (self.isempty() and
                not self.hasp("loaded_property")):
            self.setp("loaded_property", [])
        return True

    def save_data2(self, data=None):
        if data is None:
            data = {}
        #ap = [self.get_artist_property(a) for a in self._artists]
        # artist_property is stored always as "loaded_property"
        # ap is left for backword compatibility
        ap = []
        is_new_stored_prop = self.store_loaded_property()
        ###
#        ps = properties_in_file_1(self)
        ps = self.attr_in_file()
        val = {}
        for name in ps:
            val[name] = self.getp(name)

        # this section is always True
        if self.hasp("loaded_property"):
            val["loaded_property"] = self.getp("loaded_property")

        param = {"_container_idx": self._container_idx}
        data['FigObj'] = (1, ap, val, param)

        # this is skipped, since superclass is treedict
        data = super(FigObj, self).save_data2(data)
        if is_new_stored_prop:
            self.delp('loaded_property')
        return data

    def handle_loaded_figobj_data(self, data, clsname):
        if clsname in data:
            val = data[clsname][1]
            for key in val:
                self.setp(key, val[key])
            if len(data[clsname]) > 2:
                param = data[clsname][2]
                for key in param:
                    if hasattr(self, key):
                        setattr(self, key, param[key])

    def load_data(self, fid=None):
        val = pickle.load(fid)
        loaded_prop = []
        for i in range(0, val["num_artists"]):
            prop = pickle.load(fid)
            loaded_prop.append(prop)
        if len(loaded_prop) != 0:
            self.setp("loaded_property", loaded_prop)
        else:
            pass
#           print "no loaded property....artist was not realized when saved?"
#        print(loaded_prop)
        if "format" in val:
            if val["format"] == 2:
                attr = pickle.load(fid)
                for k in attr:
                    self.setp(k, attr[k])
        if not self.hasvar("kywds"):
            self.setvar("kywds", {})

    def load_data2(self, data):
        d = data['FigObj']
        loaded_prop = d[1]
        attr = d[2]
        if len(d) > 3:
            param = d[3]
            for key in param:
                if hasattr(self, key):
                    setattr(self, key, param[key])
        if len(loaded_prop) != 0:
            self.setp("loaded_property", loaded_prop)
        else:
            pass
#           print "no loaded property....artist was not realized when saved?"

        for k in attr:
            self.setp(k, attr[k])
        if not self.hasvar("kywds"):
            self.setvar("kywds", {})
        super(FigObj, self).load_data2(data)


#    def init_after_load(self, olist, nlist):
#        from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
#        if isinstance(self, XUser): self.get_xaxisparam()
#        if isinstance(self, YUser): self.get_yaxisparam()
#        if isinstance(self, ZUser): self.get_zaxisparam()
#        if isinstance(self, CUser): self.get_caxisparam()

    def get_artist_property(self, a):
        #       plist = properties_in_file_0(self)
        plist = self.property_in_file()
        vals = {}
        for p in plist:
            p0 = p
            if isMPL2 and p == 'axis_bgcolor':
                p = 'facecolor'
            if hasattr(a, 'get_'+p):
                if callable(getattr(a, 'get_'+p)):
                    vals[p0] = (getattr(a, 'get_'+p))()
                else:
                    vals[p0] = getattr(a, 'get_'+p)
            elif hasattr(a, p):
                vals[p0] = getattr(a, p)
        return vals

    def set_artist_property(self, a, vals):
        for key in vals:
            #          if isMPL2 and key == 'axis_bgcolor': key = 'facecolor'
            if hasattr(a, 'set_'+key):
                if callable(getattr(a, 'set_'+key)):
                    (getattr(a, 'set_'+key))(vals[key])
                else:
                    setattr(a, 'set_'+key, vals[key])
            elif hasattr(a,  key):
                setattr(a, key, vals[key])

    def switch_scale(self, level):
        pass

#
#   set artist property
#
    def mpl_set(self, name, *value, **kargs):
        if "ia" in kargs:
            ia = kargs["ia"]
        else:
            ia = 0
        ax = self.get_figaxes()
        if ax is not None:
            ax.set_bmp_update(False)
        self.set_client_update_artist_request()
        if len(value) == 1:
            return self._artists[ia].set(**{name: value[0]})
        else:
            return self._artists[ia].set(**{name: value})

    def mpl_get(self, name, ia=0):
        m = getattr(self._artists[ia], 'get_'+name)
        return m()


#
#   range setting
#

    def get_xrange(self, xrange=[None, None], scale='linear'):
        return xrange

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        return yrange

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], sclae='linear'):
        return crange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None], scale='linear'):
        return zrange

    def _update_range(self, range, de):
        masked = np.ma.core.MaskedConstant
        if not isinstance(de[0], masked):
            if range[0] is None:
                range[0] = de[0]
            else:
                if de[0] is not None:
                    range[0] = min([range[0], de[0]])
        if not isinstance(de[1], masked):
            if range[1] is None:
                range[1] = de[1]
            else:
                if de[1] is not None:
                    range[1] = max([range[1], de[1]])
        return range
#
#
#

    def convert_to_tex_style_text(self, mode=True):
        pass
#
#   axes change
#

    def handle_axes_change(self, evt):
        '''
        some objects requires to change artist 
        if scale/range changed
        '''
        pass
#
#  axes, transform...
#

    def set_axesref(self, figaxes_list):
        self._fig_axes = []
        for figaxes in figaxes_list:
            if figaxes is not None:
                self._fig_axes.append(weakref.ref(figaxes, self.lost_figaxes))
            else:
                self._fig_axes.append(cbook.WeakNone())

    def get_axesref(self):
        return self._fig_axes

    def lost_figaxes(self, ref):
        print('referred axes is deleted')

    def convert_transform_rect(self, t1, t2, rect):
        n1 = np.array([rect[0], rect[1]]).reshape(1, 2)
        n2 = np.array([rect[0]+rect[2], rect[1]+rect[3]]).reshape(1, 2)
        if t1 is not None:
            n1 = t1.transform(n1)
            n2 = t1.transform(n2)
        if t2 is not None:
            n1 = t2.inverted().transform(n1)
            n2 = t2.inverted().transform(n2)

        w = n2[0][0]-n1[0][0]
        h = n2[0][1]-n1[0][1]
        rect = [n1[0][0], n1[0][1], w, h]
        return rect

    def convert_transform_point(self, t1, t2, p):
        '''
        it dose 
        1) transfomr to device using t1
        2) transform to new coord by t2.inverted()
        '''
        n1 = np.array([p[0], p[1]]).reshape(1, 2)
        if t1 is not None:
            n1 = t1.transform(n1)
        if t2 is not None:
            n1 = t2.inverted().transform(n1)
        return n1[0][0], n1[0][1]

    def coordsname2transform(self, fig_page, name, fig_axes=None):
        #name = name0[0]
        if fig_axes is None:
            return fig_page._artists[0].transFigure
        if name == 'data':
            return fig_axes._artists[0].transData
        elif name == 'axes':
            return fig_axes._artists[0].transAxes
        elif name == 'figure':
            return fig_page._artists[0].transFigure

#
# change rotation center in 3D plot
#
    def onSetRotCenter(self, evt):
        canvas = evt.GetEventObject()

        xx = 0
        yy = 0
        zz = 0
        ll = 0
        for x in canvas.selection:
            glartist = x()
            x, y, z = glartist.get_glverts()
            l = len(x)
            ll += l
            xx += np.mean(x)*l
            yy += np.mean(y)*l
            zz += np.mean(z)*l
            axes = glartist.axes

        xx /= l
        yy /= l
        zz /= l

        cc = np.array((xx, yy, zz))
        axes._gl_rot_center = cc
        axes._gl_use_rot_center = True

        evt.Skip()
