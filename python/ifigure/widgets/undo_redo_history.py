from __future__ import print_function
#
#  Name   :undo_redo_history.py
#
#          this module implement undo/redo to
#          ifigure
#
#          the idea is when a program edit a
#          property of matplotlib/ifigure#
#          it makes an undoredo object and
#          register it to undo_redo_history
#          using add_history.
#
#          undo_redo object defines how to
#          manipulate objects and how to
#          put it back
#
#          app itself should not touch properties
#          by itself if it want to make an
#          action undoable.
#
#          2012.11 Added group/ungroup action
#
#  Example  :
#        ### import stuffs.
#        from ifigure.widgets.undo_redo_history import GlobalHistory
#        from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
#        from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
#        from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
#
#        ### get window object
#        (for wx event)
#        window = evt.GetEventObject().GetTopLevelParent()
#        (for matplotlib event)
#        window = evt.guiEvent.GetEventObject().GetTopLevelParent()
#        ### get history object
#        hist = GlobalHistory().get_history(window)
#        ### start recording
#        hist.start_record()
#        ### define action
#        action1 = UndoRedoFigobjMethod(a, 'splinenode', (x, y))
#        ### registor history
#        hist.add_history(action1)
#        ### stop recording, whidh triger the action
#        ### to be performed
#        hist.stop_record()
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
# *******************************************
#     Copyright(c) 2012- S.Shiraiwa
# *******************************************
import weakref
import os

from ifigure.utils.cbook import isiterable
from ifigure.utils.weak_callback import WeakCallback

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('UndoRedoHistory')


def weakref_method(meth, callback):
    weak_obj = weakref.ref(meth.__self__, callback)
    weak_func = weakref.ref(meth.__func__, callback)
    return weak_obj, weak_func


def weakref_deref(meth_ref):
    obj = meth_ref[0]()
    func = meth_ref[1]()
    meth = getattr(obj, func.__name__)
    return meth


class History(object):
    def __init__(self):
        self.old_value = None
        self.new_value = None

    @property
    def proj(self):
        return self._proj()

    def set_proj(self, figobj):
        pd = WeakCallback(self.proj_dead)
        self._proj = weakref.ref(figobj.get_root_parent(), pd)
#        self._proj = weakref.ref(figobj.get_root_parent(), self.proj_dead)

    def proj_dead(self, obj):
        #        print self, id(self)
        self.history.rm_history(self)

    def do(self):
        print("History::do need to be overwriten")

    def do2(self):
        print("History::do need to be overwriten")

    def undo(self):
        print("History::do need to be overwriten")

    def redo(self):
        print("History::do need to be overwriten")

    def replace_aritst(self, a1, a2):
        pass

    def clear(self):
        if self._proj is not None:
            del self._proj
        self._proj = None

    def __del__(self):
        if self._proj is not None:
            del self._proj
        self._proj = None


class Undobase(History):
    def __init__(self, a, figobj=None):
        super(Undobase, self).__init__()
        self.is_hlupdate = False

        if figobj is None:
            figobj = a.figobj
        #        self.artist = weakref.ref(a, self.callback2)

        self.set_proj(figobj)
        self.set_artist(a, figobj)
        self.set_artist_bk(a)
        self._path = figobj.get_full_path()

    @property
    def figobj(self):
        return self.proj.find_by_full_path(self._path)

    @property
    def artist(self):
        if self._ia >= 0:
            return self.figobj._artists[self._ia]
        else:
            return None

    def set_artist(self, a, figobj):
        self._path = figobj.get_full_path()
        if a is not None:
            self._ia = self.figobj._artists.index(a)
        else:
            self._ia = -1

    @property
    def artist_bk(self):
        return self._artist_bk()

    def set_artist_bk(self, a):
        if a is not None:
            self._artist_bk = weakref.ref(a)

    def do(self):
        print('###!!! Histroy::do is called why?!!!###')
        self.old_value = self.getter()
        self.setter(self.new_value)
        self.update_hl()

    def do2(self):
        return self.figobj

    def update_hl(self):
        if not self.is_hlupdate:
            return
        if self.figobj.has_highlight(self.artist):
            self.figobj.highlight_artist(False,  artist=[self.artist])
            self.figobj.highlight_artist(True,  artist=[self.artist])

    def set_hlupdate(self, value=True):
        self.is_hlupdate = value

    def replace_aritst(self, a1, a2):
        if self.artist_bk == a1:
            self.set_artist_bk(a2)
            self.set_proj(a2.figobj)
            self.set_artist(a2, a2.figobj)
#    def callback_none(self, obj):
#        pass


class UndoRedoAxesArtistProperty(Undobase):
    #
    #   this one stores weakref to mplobject's method
    #
    def __init__(self, a, name, new_value, figobj):
        Undobase.__init__(self, a, figobj=figobj)
#        self._setter = weakref_method(getattr(a, 'set_'+name),
#                                             self.callback1)
#        self._getter = weakref_method(getattr(a, 'get_'+name),
#                                             self.callback1)
        setter = WeakCallback(getattr(a, 'set_'+name))
        getter = WeakCallback(getattr(a, 'get_'+name))
        callback = WeakCallback(self.callback1)

        self._setter = setter
        self._getter = getter
        self._aaaa = weakref.ref(a, callback)
#        self._setter = weakref.ref(setter, callback)
#        self._getter = weakref.ref(getter, callback)

        self.pname = name
        self.new_value = new_value

    def __repr__(self):
        return 'AxesArtistProperty('+self.pname+')'

    def __del__(self):
        #        print 'deleting undoredo axes aritist property'
        self._artist = None
        self._setter = None
        self._getter = None
        Undobase.__del__(self)

    @property
    def setter(self):
        return self._setter
#         return self._setter().deref()
#        return weakref_deref(self._setter)
    @property
    def getter(self):
        return self._getter
#         return self._getter().deref()
#        return weakref_deref(self._getter)
    @property
    def artist(self):
        return self._artists()

    def set_artist(self, a, figobj=None):
        self._artist = weakref.ref(a, self.callback1)

    def do(self):
        self.old_value = self.getter()
        self.setter(self.new_value)
        self.figobj.postprocess_mpltext_edit()

    def update_hl(self):
        pass

    def do2(self):
        return self.figobj

    def undo(self):
        self.setter(self.old_value)
        self.figobj.postprocess_mpltext_edit()

    def redo(self):
        self.setter(self.new_value)
        self.figobj.postprocess_mpltext_edit()

    def callback1(self, obj):
        self.history.rm_history(self)
    #    def replace_aritst(self, a1,a2):
    #    if self.artist() == a1:
    #        self.set_artist(a2)
    #        #self._artist= weakref.ref(a2, self.callback2)

    def clear(self):
        self._artist = None
        self._setter = None
        self._getter = None
        Undobase.clear(self)


class UndoRedoArtistProperty(Undobase):
    def __init__(self, a, name, new_value, all=False):
        super(UndoRedoArtistProperty, self).__init__(a)
        #self.setter = getattr(a, 'set_'+name)
        #self.getter = getattr(a, 'get_'+name)
        self.pname = name
        self.new_value = new_value
        self.all = all
        #        self.all_figobj = a.figobj
        self.all_figobj_path = a.figobj.get_full_path()
        self.all_name = name

    def __repr__(self):
        return 'ArtistProperty('+self.pname+')'

    @property
    def setter(self):
        return getattr(self.artist, 'set_'+self.pname)

    @property
    def getter(self):
        return getattr(self.artist, 'get_'+self.pname)

    @property
    def all_figobj(self):
        return self.proj.find_by_full_path(self.all_figobj_path)

    def do(self):
        self.old_value = self.getter()
        self.setter(self.new_value)
        if self.all:
            for a in self.all_figobj._artists:
                setter = getattr(a, 'set_'+self.all_name)
                setter(self.new_value)
        self.figobj.set_client_update_artist_request()
        self.update_hl()

    def undo(self):
        self.setter(self.old_value)
        if self.all:
            for a in self.all_figobj._artists:
                setter = getattr(a, 'set_'+self.all_name)
                setter(self.old_value)
        self.update_hl()

    def redo(self):
        self.setter(self.new_value)
        if self.all:
            for a in self.all_figobj._artists:
                setter = getattr(a, 'set_'+self.all_name)
                setter(self.new_value)
        self.update_hl()

#    def replace_aritst(self, a1,a2):
#        if self._artist() == a1:
#            self._artist = weakref.ref(a2, self.callback2)
        #self.setter = getattr(a2, 'set_'+self.pname)
        #self.getter = getattr(a2, 'get_'+self.pname)


class UndoRedoFigobjProperty(Undobase):
    def __init__(self, a, name, new_value, nodelete=False):
        super(UndoRedoFigobjProperty, self).__init__(a)
        self.new_value = new_value
        self.name = name
        self.nodelete = nodelete

    def __repr__(self):
        return 'FigObjProperty('+self.name+')'

    def setter(self, value):
        return self.figobj.setp(self.name, value)

    def getter(self):
        return self.figobj.getp(self.name)

    def do(self):
        self.old_value = self.getter()
        self.setter(self.new_value)
        self.set_artist(self.figobj._artists[0], self.figobj)
        self.set_artist_bk(self.figobj._artists[0])

        self.update_hl()

    def do2(self):
        import ifigure.events
        
        if not self.nodelete:
            a1 = self.figobj._artists[0]
            hl = self.figobj.has_highlight(a1)
            self.figobj.del_artist(delall=True)
            self.figobj.realize()
            a2 = self.figobj._artists[0]
            if a1 != a2:
                dprint2('sending replace event')
                ifigure.events.SendReplaceEvent(self.figobj,
                                                a1=a1, a2=a2)
        return self.figobj

    def undo(self):
        import ifigure.events
        
        self.setter(self.old_value)
        self._artist = None
        if not self.nodelete:
            a1 = self.figobj._artists[0]
            hl = self.figobj.has_highlight(a1)
            self.figobj.del_artist(delall=True)
            self.figobj.realize()
            a2 = self.figobj._artists[0]

            if a1 != a2:
                ifigure.events.SendReplaceEvent(self.figobj,
                                                a1=a1, a2=a2)
        self.set_artist_bk(self.figobj._artists[0])

    def redo(self):
        import ifigure.events
        
        self.setter(self.new_value)
        self._artist = None
        if not self.nodelete:
            a1 = self.figobj._artists[0]
            hl = self.figobj.has_highlight(a1)
            self.figobj.del_artist(delall=True)
            self.figobj.generate_artist()
            a2 = self.figobj._artists[0]
            if a1 != a2:
                ifigure.events.SendReplaceEvent(self.figobj,
                                                a1=a1, a2=a2)
        self.set_artist_bk(self.figobj._artists[0])


class UndoRedoFigobjMethod(Undobase):
    def __init__(self, a, name, new_value, finish_action=None,
                 figobj=None, old_value=None):
        if a is not None:
            figobj = a.figobj
        super(UndoRedoFigobjMethod, self).__init__(a, figobj=figobj)
        self.new_value = new_value
        #        self.getter_m = getattr(self.figobj(), 'get_'+name)
        #        self.setter_m = getattr(self.figobj(), 'set_'+name)
        self._extra = None
        self._use_do2 = finish_action
        self._mname = name
        if old_value is not None:
            self._old_value = old_value
        # print 'figobjmethd', id(self)

    def __repr__(self):
        return 'FigobjMethod('+self._mname+')'

    @property
    def getter_m(self):
        return getattr(self.figobj, 'get_'+self._mname)

    @property
    def setter_m(self):
        return getattr(self.figobj, 'set_'+self._mname)

    def set_extrainfo(self, info):
        self._extra = info

    def set_finish_action(self, f):
        self._use_do2 = f

    def do(self):
        if not hasattr(self, '_old_value'):
            self.old_value = self.getter()
        else:
            self.old_value = self._old_value
        self.setter(self.new_value)
        self.update_hl()

    def do2(self):
        if self._use_do2 is not None:
            if isiterable(self._use_do2):
                for f in self._use_do2:
                    f()
            else:
                self._use_do2()
            self.update_hl()
        return self.figobj

    def setter(self, value):
        if self._extra is None:
            self.setter_m(value, self.artist)
        else:
            self.setter_m((self._extra, value), self.artist)

    def getter(self):
        if self._extra is None:
            return self.getter_m(self.artist)
        else:
            return self.getter_m(self.artist, self._extra)

    def undo(self):
        self.setter(self.old_value)
        self.update_hl()

    def redo(self):
        self.setter(self.new_value)
        self.update_hl()


class UndoRedoGroupUngroupFigobj(History):
    def __init__(self, figobjs=None, mode=0):
        '''
        define group/ungroup history
        mode : 0: group  1: ungroup
        '''
        super(UndoRedoGroupUngroupFigobj, self).__init__()

        if figobjs is None:
            return
        self.set_objs(figobjs)
        self.set_proj(figobjs[0])
        self._root_path = figobjs[0].get_root_figobj().get_full_path()
        self.mode = mode

    def __repr__(self):
        return 'GroupUngroup'

    @property
    def figobj(self):
        return self.proj.find_by_full_path(self._root_path)

    @property
    def objs(self):
        ret = [self.proj.find_by_full_path(p) for p in self._objs_path]
        if None in ret:
            return []
        return ret

    def set_objs(self, objs):
        self._objs_path = [figobj.get_full_path() for figobj in objs]

    def do(self):
        import ifigure.events
        
        for obj in self.objs:
            obj.highlight_artist(False, artist=obj._artists)
        self.redo()
        #        print 'new obj', self.objs[0].get_full_path()
        ifigure.events.SendChangedEvent(self.objs[0],
                                        self.objs[0].get_app(),
                                        useProcessEvent=True)

    def do2(self):
        import ifigure.events
        
        alist = []
        for obj in self.objs:
            alist = alist + [weakref.ref(a) for a in obj._artists]
        self.objs[0].get_app().proj_tree_viewer.update_widget()
        ifigure.events.SendSelectionEvent(self.objs[0],
                                          self.objs[0].get_app(),
                                          alist)
        return self.objs[0]

    def undo(self):
        if self.mode == 0:
            self.ungroup()
        else:
            self.group()

    def redo(self):
        if self.mode == 1:
            self.ungroup()
        else:
            self.group()

    def group(self):
        print('grouping...')
        if len(self.objs) == 0:
            print('disaster handling here')
            return
        gp = self.objs[0].group(self.objs)
        gp.realize()
        self.set_objs([gp])

    def ungroup(self):
        print('ungrouping...')
        if len(self.objs) == 0:
            print('disaster handling here')
            return
        figobjs = self.objs[0].ungroup()
        self.set_objs(figobjs)


class UndoRedoAddRemoveArtists(History):
    def __init__(self, artists=None, mode=0):
        '''
        define add/remove history
        mode : 0: add  1: remove

        usage for addition and removal is a bit different.
        when removing artists, make a history record and registor
        it. then history does remove the artists.
        when adding artists add the artists and make a history record. 
        history does not do anything when the record is registored.
        '''
        super(UndoRedoAddRemoveArtists, self).__init__()
        self.figobj_paths = [a().figobj.get_full_path() for a in artists]
        self.artist_idx = [a().figobj._artists.index(a()) for a in artists]
        self.mode = mode
        self.set_proj(artists[0]().figobj)

        figpage = artists[0]().figobj.get_figpage()
        if figpage == artists[0]().figobj:
            figbook = figpage.get_parent()
            self._root_path = figbook.get_full_path()
        else:
            self._root_path = figpage.get_full_path()
        self.filenames = []
        self.child_idx = []
        self._ret_path = ''

    def __repr__(self):
        return 'AddRemove'

    @property
    def figobj(self):
        return self.proj.find_by_full_path(self._root_path)

    def do(self):
        for k in range(len(self.figobj_paths)):
            figobj = self.proj.find_by_full_path(self.figobj_paths[k])
            a = figobj._artists[self.artist_idx[k]]
            figobj.highlight_artist(False, artist=[a])
        self.redo()

    def do2(self):
        import ifigure.events
        
        if self._ret_path != '':
            root = self.proj.find_by_full_path(self._ret_path)
        else:
            root = self.proj.find_by_full_path(self._root_path)
#        print root.get_full_path()
        ifigure.events.SendChangedEvent(root,
                                        self.proj.app)
        return root

    def undo(self):
        if self.mode == 0:
            self.remove()
        else:
            self.add()

    def redo(self):
        if self.mode == 1:
            self.remove()
        else:
            self.add()

    def add(self):
        o_list = []
        for k in reversed(range(len(self.filenames))):
            path = self.figobj_paths[k]
            parent = self.proj.find_by_full_path(
                '.'.join(path.split('.')[0:-1]))
            # print path, parent.get_full_path()
            a_idx = self.artist_idx[k]
            child = parent.load_subtree(self.filenames[k],
                                        keep_zorder=True)
            # print child, self.filenames[k]
            parent.move_child(child.get_ichild(), self.child_idx[k])
            child.realize()
            print(('removing', self.filenames[k]))
            os.remove(self.filenames[k])
            o_list.append(child)
        self.filenames = []
        self.child_idx = []
        if len(o_list) != 0:
            self._ret_path = o_list[0].find_common_parent(
                o_list).get_full_path()
        else:
            self._ret_path = ''

    def remove(self):
        self.filenames = []
        self.child_idx = []
        p_list = []
        for k in range(len(self.figobj_paths)):
            figobj = self.proj.find_by_full_path(self.figobj_paths[k])
            p_list.append(figobj.get_parent())
        if len(p_list) != 0:
            self._ret_path = p_list[0].find_common_parent(
                p_list).get_full_path()
        else:
            self._ret_path = ''
        for k in range(len(self.figobj_paths)):
            figobj = self.proj.find_by_full_path(self.figobj_paths[k])
            a = figobj._artists[self.artist_idx[k]]
            idx = figobj.get_ichild()
            filename = os.path.join(self.proj.getvar('wdir'), '.trash',
                                    self.proj.random_tmp_name(seed=k))
            print(('saving', filename))
            figobj.save_subtree(filename)
            self.filenames.append(filename)
            self.child_idx.append(idx)
            # now need to save figobj
            if figobj is not None:
                figobj.del_artist(artist=(a,))
            if figobj.isempty():
                figobj.destroy()


class HistoryEntry(list):
    def __init__(self, *args, **kargs):
        super(HistoryEntry, self).__init__(*args, **kargs)
        self.use_reverse = True
        self.finish_action = None
        self.menu_name = 'Edit'   # name appears on menu

    def __repr__(self):
        txt = 'HistoryEntry('
        txt2 = '.'.join([item.__repr__() for item in self])
        return txt + txt2 + ')'

    def redo(self):
        for rec in self:
            rec.redo()
        figobj = self[-1].do2()
        self.do_finish_action()
        figobj.set_bmp_update(False)
        return figobj

    def undo(self):
        if self.use_reverse:
            for rec in reversed(self):
                rec.undo()
            figobj = self[0].do2()
        else:
            for rec in self:
                rec.undo()
            figobj = self[-1].do2()
        self.do_finish_action()
        figobj.set_bmp_update(False)
        return figobj

    def do(self):
        for rec in self:
            rec.do()
        figobj = self[-1].do2()
        self.do_finish_action()
        figobj.set_bmp_update(False)
        return figobj

    def do_finish_action(self):
        if self.finish_action is not None:
            for ref, name, args in self.finish_action:
                if ref() is None:
                    continue
                m = getattr(ref(), name)
                m(*args)


class UndoRedoHistory(object):
    '''
    History object need to have
      0) figobj (member)
      1) undo   (method)
      2) redo   (method)
      3) do     (method)
      4) do2    (method)
    '''

    def __init__(self, window, *args, **kargs):
        super(UndoRedoHistory, self).__init__(*args, **kargs)
        self.undostack = []
        self.redostack = []
        self.new_entry = HistoryEntry()
        self.entrystack = []
        self.window = weakref.ref(window)

    def set_undo_redo_menu_item(self, undo_mi, redo_mi):
        self.undo_mi = undo_mi
        self.redo_mi = redo_mi

    def update_menu_item(self):
        if len(self.undostack) == 0:
            self.undo_mi.SetItemLabel("Can't Undo")
            self.undo_mi.Enable(False)
        else:
            name = self.undostack[-1].menu_name
            self.undo_mi.SetItemLabel('Undo '+name)
            self.undo_mi.Enable(True)
        if len(self.redostack) == 0:
            self.redo_mi.SetItemLabel("Can't Redo")
            self.redo_mi.Enable(False)
        else:
            name = self.redostack[-1].menu_name
            self.redo_mi.SetItemLabel('Redo '+name)
            self.redo_mi.Enable(True)

    def replace_artist(self, a1, a2):
        for item in self.undostack:
            for hist in item:
                hist.replace_aritst(a1, a2)
        for item in self.redostack:
            for hist in item:
                hist.replace_aritst(a1, a2)

    def start_record(self):
        if len(self.new_entry) != 0:
            self.stop_record()
        self.redostack = []

    def add_history(self, action):
        # obj : undoredo obj
        # action.do()
        self.new_entry.append(action)
        action.history = weakref.proxy(self)

    def clear(self):
        if len(self.new_entry) != 0:
            self.stop_record()
        for hist in self.undostack:
            for item in hist:
                item.clear()
        for hist in self.redostack:
            for item in hist:
                item.clear()
        self.undostack = []
        self.redostack = []
        self.update_menu_item()

    def make_entry(self, actions, use_reverse=True, menu_name='edit',
                   finish_action=None, draw_request='draw'):
        if len(actions) == 0:
            return
        self.start_record()
        self.new_entry.use_reverse = use_reverse
        for action in actions:
            self.add_history(action)
        self.new_entry.finish_action = finish_action
        self.stop_record(menu_name, draw_request=draw_request)
        self.update_menu_item()


#    def make_group_entry(self, actions, use_reverse=True, menu_name = 'edit'):
#        self.start_record()
#        self.new_entry.use_reverse = use_reverse
#        for action in actions: self.add_history(action)
#        self.stop_record(menu_name)
#        self.update_menu_item()

    def rm_history(self, obj):
        self.undostack = [
            item for item in self.undostack if item.count(obj) == 0]
        self.redostack = [
            item for item in self.redostack if item.count(obj) == 0]
        self.new_entry = HistoryEntry()
        self.update_menu_item()

    def stop_record(self, menu_name='Edit', draw_request='draw'):
        import ifigure.events
        
        self.new_entry.menu_name = menu_name
        self.new_entry.draw_request = draw_request
        self.undostack.append(self.new_entry)
        self.entrystack.append(self.new_entry)
        ifigure.events.SendNewHistoryEvent(self.new_entry[-1].figobj,
                                           w=self.window())
        self.new_entry = HistoryEntry()

    def flush_entry(self):
        for hist in self.entrystack:
            figobj = hist.do()
            self.send_draw_request(hist)
#           for rec in hist:
#               rec.do()
#           figobj=hist[-1].do2()
#           figobj.set_bmp_update(False)
        self.entrystack = []

    def undo(self):
        dprint2('undoing...')
        if len(self.new_entry) != 0:
            self.stop_record()
        if len(self.undostack) == 0:
            dprint1('nothing to undo...')
            return
        hist = self.undostack.pop()
        figobj = hist.undo()
        self.send_draw_request(hist)
#        if hist.use_reverse:
#            for rec in reversed(hist):
#                rec.undo()
#            figobj = hist[0].do2()
#        else:
#            for rec in hist:
#                rec.undo()
#            figobj = hist[-1].do2()
#        figobj.set_bmp_update(False)
        self.redostack.append(hist)
        self.update_menu_item()
        return figobj

    def redo(self):
        dprint2('redoing...')
        if len(self.new_entry) != 0:
            self.stop_record()
        if len(self.redostack) == 0:
            dprint1('nothing to redo...')
            return
        hist = self.redostack.pop()
        figobj = hist.redo()
        self.send_draw_request(hist)
#        for rec in hist:
#            rec.redo()
#        figobj=hist[-1].do2()
#        figobj.set_bmp_update(False)
        self.undostack.append(hist)
        self.update_menu_item()
        return figobj

    def send_draw_request(self, hist):
        import ifigure.events
        
        if hist.draw_request == 'draw':
            ifigure.events.SendCanvasDrawRequest(self.window().canvas)
        elif hist.draw_request == 'draw_all':
            ifigure.events.SendCanvasDrawRequest(
                self.window().canvas, all=True)


class GlobalHistory():
    history = None
    mode = 0

    def __init__(self):
        pass

    def set_mode(self, mode):
        GlobalHistory.mode = mode

    def get_history(self, window=None):
        if GlobalHistory.mode == 0:
            if GlobalHistory.history is None:
                GlobalHistory.history = UndoRedoHistory()
            return GlobalHistory.history
        else:
            if window is None:
                print('History w/o window is called')
                GlobalHistory.history = UndoRedoHistory()
                return GlobalHistory.history
            w = window.GetTopLevelParent()
            return w.history
