'''
   FigAxlineC

     A figplot which a user can edit value by mouse
'''
import numpy as np
import wx
import os
import ifigure
from ifigure.mto.fig_axline import FigAxline
from ifigure.utils.geom import transform_point
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile
from ifigure.widgets.undo_redo_history import GlobalHistory, UndoRedoFigobjMethod
from ifigure.utils.edit_list import DialogEditList
from ifigure.mto.fig_control import FigControl


def _copy(x):
    if x is None:
        return
    return x.copy()


class FigAxlineC(FigAxline, FigControl):
    def __new__(cls, *args, **kargs):
        draggable, kargs = ProcessKeywords(kargs, 'draggable', True)
        dragmode, kargs = ProcessKeywords(kargs, 'dragmodee', 'independent')
        enabled_point, kargs = ProcessKeywords(kargs, 'enabled_point', 'all')
        obj = FigAxline.__new__(cls, *args, **kargs)
        if obj is not None:
            obj.setvar('draggable', draggable)
            obj.setvar('dragmode', dragmode)
            if not obj.hasvar('enabled_point'):
                obj.setvar('enabled_point', enabled_point)
        return obj

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plotc.png')
        return [idx1]

    @classmethod
    def get_namebase(self):
        return 'axlinec'

    def __init__(self, *args, **kargs):
        FigAxline.__init__(self, *args, **kargs)
        FigControl.__init__(self)
        self._figc_hit = -1
        self._enable_a = None

    @classmethod
    def attr_in_file(self):
        return ['enabled_point']+super(FigAxlineC, self).attr_in_file()

    def args2var(self):
        val = FigAxline.args2var(self)
        if self.getvar('enabled_point') == 'all':
            self.setp('enabled_point',
                      [True]*(self.getp('x').size + self.getp('y').size))
        return val

    def generate_artist(self):
        FigAxline.generate_artist(self)
        idx = np.where([not x for x in self.getp('enabled_point')])[0]
        if self._enable_a is not None:
            self._enable_a.remove()
            self._enable_a = None
        if idx.size == 0:
            return
        self._enable_a = []  # it is actually for disabled points
        x, y = self._eval_xy()
        container = self.get_container()
        for k in idx:
            lw = self._artists[k].get_linewidth()
            if k < x.size:
                self._enable_a.append(container.axvline(x[k],
                                                        color='white',
                                                        linestyle='--',
                                                        linewidth=lw))
            else:
                self._enable_a.append(container.axhline(y[k-x.size],
                                                        color='white',
                                                        linestyle='--',
                                                        linewidth=lw))

    def del_artist(self, artist=None, delall=False):
        if self._enable_a is not None:
            for a in self._enable_a:
                a.remove()
            self._enable_a = None
        return FigAxline.del_artist(self, artist=artist, delall=delall)

    def canvas_menu(self):
        m = [('Add Point', self.onAddPoint, None), ]
        if self._figc_hit != -1:
            if self.getp('enabled_point')[self._figc_hit]:
                m = m + [('Delete Point', self.onDelPoint, None),
                         ('Edit Point', self.onEditPoint, None),
                         ('Disable Point', self.onDisablePoint, None), ]
            else:
                m = m + [('Delete Point', self.onDelPoint, None),
                         ('Edit Point', self.onEditPoint, None),
                         ('Enable Point', self.onEnablePoint, None), ]
        return m + FigAxline.canvas_menu(self)

    def picker_a(self, a, evt):
        hit, extra = FigAxline.picker_a(self, a, evt)
        if hit:
            self._figc_hit = self._artists.index(extra['child_artist'])
            self._drag_backup = (a.get_xdata(), a.get_ydata())
        else:
            self._figc_hit = -1
        return hit, extra

    def drag(self, a, evt):
        if self.getvar('dragmode') == 'independent':
            if evt.inaxes is None:
                return 0
            if evt.xdata is None:
                return

            axes = a.axes
            x, y = self._eval_xy()
            if self._figc_hit < x.size:
                #                self.setp('x')[self._figc_hit] = evt.xdata
                self._artists[self._figc_hit].set_xdata([evt.xdata, evt.xdata])
            else:
                #                self.setp('y')[self._figc_hit - x.size] = evt.ydata
                self._artists[self._figc_hit].set_ydata([evt.ydata, evt.ydata])
        else:
            return FigAxline.drag(self, a, evt)

    def dragdone(self, a, evt):
        if self.getvar('dragmode') == 'independent':
            axes = a.axes
            x, y = self._eval_xy()
            if self._figc_hit < x.size:
                x = self.getp('x').copy()
                x[self._figc_hit] = evt.xdata
                y = self.getp('y').copy()
            else:
                x = self.getp('x').copy()
                y = self.getp('y').copy()
                y[self._figc_hit - x.size] = evt.ydata

            action = UndoRedoFigobjMethod(self._artists[0],
                                          'data',
                                          (x, y))
            window = evt.guiEvent.GetEventObject().GetTopLevelParent()
            GlobalHistory().get_history(window).make_entry([action])
            return 1
        else:
            return FigAxline.dragdone(self, a, evt)

    def do_update_artist(self):
        if not self.isempty():
            try:
                a1 = self._artists[self._figc_hit]
            except:
                a1 = self._artists[0]
            self.del_artist(delall=True)
        if self.isempty() and not self._suppress:
            self.generate_artist()
            try:
                a2 = self._artists[self._figc_hit]
            except:
                a2 = self._artists[0]
            if a1 != a2:
                ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def onAddPoint(self, evt):
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        v = self.getp('enabled_point')[:]
        if self._figc_hit < x.size:
            x = np.insert(x, self._figc_hit + 1, self._drag_backup[0][0])
            v.insert(self._figc_hit + 1, True)
        else:
            y = np.insert(y, self._figc_hit + 1 - x.size,
                          self._drag_backup[1][0])
            v.insert(self._figc_hit + 1, True)
        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data',
                                        (x, y)),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v), ]
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions, menu_name='add point')
        return 1

    def onDelPoint(self, evt):
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        v = self.getp('enabled_point')[:]
        if self._figc_hit < x.size:
            x = np.delete(x, self._figc_hit)
            del v[self._figc_hit]
        else:
            y = np.delete(y, self._figc_hit - x.size)
            del v[self._figc_hit]

        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data',
                                        (x, y)),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v), ]
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions, menu_name='delete point')
        return 1

    def onEditPoint(self, evt):
        x, y = self._eval_xy()
        if self._figc_hit < x.size:
            l = [['x', str(x[self._figc_hit]), 0, None], ]
        else:
            l = [['y', str(y[self._figc_hit-x.size]), 0, None], ]
        window = evt.GetEventObject().GetTopLevelParent()
        value = DialogEditList(l, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=window)
        if value[0]:
            v = value[1]
        else:
            return
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        if self._figc_hit < x.size:
            x[self._figc_hit] = float(v[0])
        else:
            y[self._figc_hit - x.size] = v[0]
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (x, y))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1

    def onEnablePoint(self, evt):
        v = self.getp('enabled_point')[:]
        v[self._figc_hit] = True
        x = self.getp('x').copy()
        y = self.getp('y').copy()

        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'data',
                                        (x, y))]
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onDisablePoint(self, evt):
        v = self.getp('enabled_point')[:]
        v[self._figc_hit] = False
        x = self.getp('x').copy()
        y = self.getp('y').copy()

        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'data',
                                        (x, y))]

        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def set_enabled_point(self, value, a):
        self.setp('enabled_point', value)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

    def get_enabled_point(self, a):
        return self.getp('enabled_point')

    def set_data(self, value, a):
        self.setp('x', value[0])
        self.setp('y', value[1])
        self._data_extent = None
        self.set_update_artist_request()
        self.call_control_changed_callback()

    def get_data(self, a=None):
        return (self.getp('x').copy(), self.getp('y').copy(), self.getp('enabled_point')[:])

    def save_data2(self, data=None):
        var = {'enabled_point': self.getp('enabled_point')}
        data['FigAxlineC'] = (1, var)
        data = super(FigAxlineC, self).save_data2(data)
        return data

    def load_data2(self, data):
        super(FigAxlineC, self).load_data2(data)
        if not 'FigAxlineC' in data:
            self.setp('enabled_point',
                      [True]*(self.getp('x').size + self.getp('y').size))
        else:
            d = data['FigAxlineC'][1]
            self.setp('enabled_point', d['enabled_point'])
