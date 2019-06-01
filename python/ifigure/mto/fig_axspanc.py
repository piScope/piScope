import wx
import numpy as np
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile
from ifigure.widgets.undo_redo_history import GlobalHistory, UndoRedoFigobjMethod
from ifigure.utils.edit_list import DialogEditList
from ifigure.mto.fig_control import FigControl
from ifigure.mto.fig_axspan import FigAxspan
from ifigure.mto.fig_obj import set_mpl_all, get_mpl_first


class FigAxspanC(FigAxspan, FigControl):
    def __new__(cls, *args, **kargs):
        draggable, kargs = ProcessKeywords(kargs, 'draggable', True)
        dragmode, kargs = ProcessKeywords(kargs, 'dragmodee', 'independent')
#        dragmode, kargs = ProcessKeywords(kargs, 'alpha', 1.0)
#        dragmode, kargs = ProcessKeywords(kargs, 'alpha_disabled', 0.5)
        enabled_point, kargs = ProcessKeywords(kargs, 'enabled_point', 'all')
        obj = FigAxspan.__new__(cls, *args, **kargs)
        if obj is not None:
            obj.setvar('draggable', draggable)
            obj.setvar('dragmode', dragmode)
#            obj.setvar('alpha', alpha)
#            obj.setvar('alpha_disabled', alpha_disabled)
            if not obj.hasvar('enabled_point'):
                obj.setvar('enabled_point', enabled_point)
        return obj

    def __init__(self, *args, **kargs):
        FigAxspan.__init__(self, *args, **kargs)
        FigControl.__init__(self)
        self._figc_hit = -1
        self._enable_a = None

    @classmethod
    def get_namebase(self):
        return 'axspanc'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plotc.png')
        return [idx1]

    @classmethod
    def attr_in_file(self):
        return ['enabled_point']+super(FigAxspanC, self).attr_in_file()

    def picker_a(self, a, evt):
        hit, extra = FigAxspan.picker_a(self, a, evt)
        if hit:
            self._figc_hit = self._artists.index(extra['child_artist'])
            self._drag_backup = a.get_xy()
        else:
            self._figc_hit = -1
        return hit, extra

    def drag(self, a, evt):
        if self.getvar('dragmode') == 'independent':
            FigAxspan.drag(self, a, evt, idx=self._figc_hit)
        else:
            FigAxspan.drag(self, a, evt)

    def dragdone(self, a, evt):
        if self.getvar('dragmode') == 'independent':
            FigAxspan.dragdone(self, a, evt, idx=self._figc_hit)
        else:
            FigAxspan.dragdone(self, a, evt)

    def canvas_menu(self):
        m = [('+Add...', None, None),
             ('X span', self.onAddXSpan, None),
             ('Y span', self.onAddYSpan, None),
             ('!', None, None), ]
        if self._figc_hit != -1:
            if len(self.getp('x'))+len(self.getp('y')) > 1:
                m = m + [('Delete Span', self.onDelSpan, None), ]
            if self.getp('enabled_point')[self._figc_hit]:
                m = m + [('Edit Data...', self.onEditSpan, None),
                         #('Disalbe Span...', self.onEnableSpan, None),
                         ]

            else:
                m = m + [
                    ('Edit Data...', self.onEditSpan, None),
                    #                        ('Enable Span', self.onEnablePoint, None),
                ]
        return m + FigAxspan.canvas_menu(self)

    def onEditSpan(self, evt):
        x, y = self._eval_xy()
        if self._figc_hit < x.size:
            l = [['x1', str(x[self._figc_hit, 0]), 0, None],
                 ['x2', str(x[self._figc_hit, 1]), 0, None], ]
        else:
            l = [['y1', str(y[self._figc_hit-x.size, 0]), 0, None],
                 ['y2', str(y[self._figc_hit-x.size, 1]), 0, None], ]
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
            x[self._figc_hit, 0] = float(v[0])
            x[self._figc_hit, 1] = float(v[1])
        else:
            y[self._figc_hit - x.size, 0] = v[0]
            y[self._figc_hit - x.size, 1] = v[1]
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (x, y))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1

    def onEnableSpan(self, evt):
        pass

    def onDisableSpan(self, evt):
        pass

    def onDelSpan(self, evt):
        x, y = self._eval_xy()
        x = x.copy()
        y = y.copy()
        if self._figc_hit < x.size:
            x = np.array([xx for i, xx in enumerate(x) if i != self._figc_hit])
        else:
            y = np.array([xx for i, xx in enumerate(
                y) if i != self._figc_hit-len(x)])
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (x, y))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1

    def onAddXSpan(self, evt):
        l = [['x1', 0, 400, None],
             ['x2', 1, 400, None], ]
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
        x = np.array([xx for xx in x] + [v])
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (x, y))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(
            [action], menu_name='add span')
        return 1

    def onAddYSpan(self, evt):
        l = [['y1', 0, 400, None],
             ['y2', 1, 400, None], ]
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
        y = np.array([xx for xx in y] + [v])
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data',
                                      (x, y))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(
            [action], menu_name='add span')
        return 1

    def set_alpha(self, value, a):
        set_mpl_all(self._artists, 'alpha', value)
#            if self.getp('enabled_point')[self._figc_hit]:

    def get_alpha(self, a):
        return get_mpl_first(self._artists, 'alpha')

    def set_enabled_point(self, value, a):
        self.setp('enabled_point', value)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

    def get_enabled_point(self, a):
        return self.getp('enabled_point')

    def set_data(self, value, a):
        FigAxspan.set_data(self, value, a)
        self._data_extent = None
        self.set_update_artist_request()
        self.call_control_changed_callback()

    def get_data(self, a=None):
        return (self.getp('x').copy(), self.getp('y').copy(), self.getp('enabled_point')[:])

    def save_data2(self, data=None):
        var = {'enabled_point': self.getp('enabled_point')}
        data['FigAxspanC'] = (1, var)
        data = super(FigAxspanC, self).save_data2(data)
        return data

    def load_data2(self, data):
        super(FigAxspanC, self).load_data2(data)
        if not 'FigAxspanC' in data:
            self.setp('enabled_point',
                      [True]*(self.getp('x').size + self.getp('y').size))
        else:
            d = data['FigAxspanC'][1]
            self.setp('enabled_point', d['enabled_point'])
