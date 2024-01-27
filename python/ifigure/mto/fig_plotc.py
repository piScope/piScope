'''
   FigPlotC

     A figplot which a user can edit value by mouse
'''
import numpy as np
import wx
import os
import ifigure
from ifigure.mto.fig_plot import FigPlot
from ifigure.utils.geom import transform_point
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile
from ifigure.widgets.undo_redo_history import GlobalHistory, UndoRedoFigobjMethod
from ifigure.utils.edit_list import DialogEditList
from ifigure.mto.fig_control import FigControl


def _copy(x):
    if x is None:
        return
    return x.copy()


class FigPlotC(FigPlot, FigControl):
    def __new__(cls, *args, **kargs):
        draggable, kargs = ProcessKeywords(kargs, 'draggable', True)
        enabled_point, kargs = ProcessKeywords(kargs, 'enabled_point', 'all')
        obj = FigPlot.__new__(cls, *args, **kargs)
        if obj is not None:
            obj.setvar('draggable', draggable)
            if not obj.hasvar('enabled_point'):
                obj.setvar('enabled_point', enabled_point)
        return obj

    def __init__(self, *args, **kargs):
        FigPlot.__init__(self, *args, **kargs)
        FigControl.__init__(self)
        self._figc_hit = -1
        self._enable_a = None
        self._mark_a = None

    @classmethod
    def attr_in_file(self):
        return ['enabled_point'] + FigPlot.attr_in_file()

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = LoadImageFile(path, 'plotc.png')
        return [idx1]

    @classmethod
    def get_namebase(self):
        return 'plotc'

    def args2var(self):
        val = FigPlot.args2var(self)
        if self.getvar('enabled_point') == 'all':
            self.setp('enabled_point', [True]*(self.getp('x').size))
        return val

    def isDraggable(self):
        return self.getvar("draggable")

    def generate_artist(self):
        FigPlot.generate_artist(self)
        container = self.get_container()
        a = self._artists[0]
        x = a.get_xdata()
        y = a.get_ydata()

        vm = self.getp('marked_point')
        if vm is not None:
            if self._mark_a is not None:
                self._mark_a.remove()
                self._mark_a = None

            a3 = container.plot(x[vm].copy(), y[vm].copy(), marker='o',
                                color='k', linestyle='None',
                                markerfacecolor='k',
                                markeredgecolor='k',
                                markersize=6,
                                scalex=False, scaley=False)
            self._mark_a = a3[0]

        idx = np.where([not xx for xx in self.getp('enabled_point')])[0]
        if self._enable_a is not None:
            self._enable_a.remove()
            self._enable_a = None
        if idx.size == 0:
            return

        marker = a.get_marker()
        fc = 'white'
        ec = a.get_markeredgecolor()
        ms = a.get_markersize()
        a2 = container.plot(x[idx].copy(), y[idx].copy(), marker=marker,
                            color='k', linestyle='None',
                            markerfacecolor=fc,
                            markeredgecolor=ec,
                            markersize=ms,
                            scalex=False, scaley=False)

        self._enable_a = a2[0]

    def del_artist(self, artist=None, delall=False):
        if self._enable_a is not None:
            self._enable_a.remove()
            self._enable_a = None
        if self._mark_a is not None:
            self._mark_a.remove()
            self._mark_a = None

        return FigPlot.del_artist(self, artist=artist, delall=delall)

    def canvas_menu(self):
        m = [('Add Point', self.onAddPoint, None), ]
        if self._figc_hit != -1:
            if self.getp('enabled_point')[self._figc_hit]:
                m = m + [('Delete point', self.onDelPoint, None),
                         ('Edit point', self.onEditPoint, None),
                         ('Disable point', self.onDisablePoint, None), ]
            else:
                m = m + [('Delete point', self.onDelPoint, None),
                         ('Edit point', self.onEditPoint, None),
                         ('Enable point', self.onEnablePoint, None), ]
            vm = self.get_mark_data()
            if vm[self._figc_hit]:
                m = m + [('Unmark point', self.onUnmarkPoint, None),
                         ('Reset mark', self.onResetMark, None),
                         ('Export mark', self.onExportMark, None), ]
            else:
                m = m + [('Mark point', self.onMarkPoint, None),
                         ('Reset mark', self.onResetMark, None),
                         ('Export mark', self.onExportMark, None), ]

        return m + FigPlot.canvas_menu(self)

    def onEditPoint(self, evt):
        def add_list(l, name, self, idx):
            value = self.getp(name)
            l.append([name, str(value[idx]), 0, None])

        from ifigure.utils.edit_list import DialogEditList
        l = []
        names = ['x', 'y']
        if self.getp('xerr') is not None:
            names.append('xerr')
        if self.getp('yerr') is not None:
            names.append('yerr')
        for name in names:
            add_list(l, name, self, self._figc_hit)

        window = evt.GetEventObject().GetTopLevelParent()
        value = DialogEditList(l, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=window)
        if value[0]:
            v = value[1]
        else:
            return
        x = _copy(self.getp('x'))
        x[self._figc_hit] = v[names.index('x')]
        y = _copy(self.getp('y'))
        y[self._figc_hit] = v[names.index('y')]
        yerr = _copy(self.getp('yerr'))
        if yerr is not None:
            yerr[self._figc_hit] = v[names.index('yerr')]
        xerr = _copy(self.getp('xerr'))
        if xerr is not None:
            xerr[self._figc_hit] = v[names.index('xerr')]

        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data', (x, y)), ]
        if self._mpl_cmd != 'plot':
            actions.append(UndoRedoFigobjMethod(self._artists[0],
                                                'errdata', (xerr, yerr)))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onDelPoint(self, evt):
        v = self.getp('enabled_point')[:]
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        del v[self._figc_hit]
        vm = self.getp('marked_point')[:]
        del vm[self._figc_hit]
        x = np.delete(x, self._figc_hit)
        y = np.delete(y, self._figc_hit)
        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data', (x, y)), ]
        if self._mpl_cmd != 'plot':
            xerr = _copy(self.getp('xerr'))
            yerr = _copy(self.getp('yerr'))
            if xerr is not None:
                xerr = np.delete(xerr, self._figc_hit)
            if yerr is not None:
                yerr = np.delete(yerr, self._figc_hit)
            actions.append(UndoRedoFigobjMethod(self._artists[0],
                                                'errdata', (xerr, yerr)))
        actions.append(UndoRedoFigobjMethod(self._artists[0],
                                            'enabled_point', v))
        actions.append(UndoRedoFigobjMethod(self._artists[0],
                                            'marked_point', vm))
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onAddPoint(self, evt):
        axes = self._artists[0].axes
        if axes is None:
            return
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        xed, yed = axes.transData.transform(self._figc_hit_pos)

        for k in range(x.size-1):
            x0 = x[k]
            y0 = y[k]
            x1 = x[k+1]
            y1 = y[k+1]
            x0d, y0d = axes.transData.transform([x0, y0])
            x1d, y1d = axes.transData.transform([x1, y1])
            d = np.sqrt((x0d-x1d)**2 + (y0d-y1d)**2)
            m1 = ((x1d-xed)*(x1d-x0d) + (y1d-yed)*(y1d-y0d))/d/d
            if (m1 < 0 or m1 > 1):
                continue
            m2 = ((x1d-xed)*(y1d-y0d) - (y1d-yed)*(x1d-x0d))/d
            if (m2 > 5 or m2 < -5):
                continue
            break
        else:
            return 1

        v = self.getp('enabled_point')[:]
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        v.insert(k+1, True)
        vm = self.getp('marked_point')[:]
        vm.insert(k+1, True)

        x = np.insert(x, k+1, self._figc_hit_pos[0])
        y = np.insert(y, k+1, self._figc_hit_pos[1])
        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data', (x, y)), ]
        if self._mpl_cmd != 'plot':
            xerr = _copy(self.getp('xerr'))
            yerr = _copy(self.getp('yerr'))
            if xerr is not None:
                xerr = np.insert(xerr, k+1, xerr[k])
            if yerr is not None:
                yerr = np.insert(yerr, k+1, yerr[k])
            actions.append(UndoRedoFigobjMethod(self._artists[0],
                                                'errdata', (xerr, yerr)))
        actions.append(UndoRedoFigobjMethod(self._artists[0],
                                            'enabled_point', v))
        actions.append(UndoRedoFigobjMethod(self._artists[0],
                                            'marked_point', vm))

        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onEnablePoint(self, evt):
        v = self.getp('enabled_point')[:]
        v[self._figc_hit] = True
        # x, y is the same, this triggers control_changed_callback
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data', (x, y)),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v)]

        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onDisablePoint(self, evt):
        v = self.getp('enabled_point')[:]
        v[self._figc_hit] = False

        # x, y is the same, this triggers control_changed_callback
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        actions = [UndoRedoFigobjMethod(self._artists[0],
                                        'data', (x, y)),
                   UndoRedoFigobjMethod(self._artists[0],
                                        'enabled_point', v)]
        window = evt.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(actions)
        return 1

    def onMarkPoint(self, evt):
        vm = self.getp('marked_point')
        if vm is None:
            l = len(self.getp('enabled_point'))
            self.setp('marked_point', [False]*l)
            vm = self.getp('marked_point')
        vm[self._figc_hit] = True
        self.setp('marked_point', vm)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

        import ifigure.events
        w = evt.GetEventObject().GetTopLevelParent()
        w.draw()
        return 1

    def onUnmarkPoint(self, evt):
        vm = self.getp('marked_point')
        if vm is None:
            l = len(self.getp('enabled_point'))
            self.setp('marked_point', [False]*l)
            vm = self.getp('marked_point')
        vm[self._figc_hit] = False
        self.setp('marked_point', vm)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

        import ifigure.events
        w = evt.GetEventObject().GetTopLevelParent()
        w.draw()
        return 1

    def onResetMark(self, evt):
        vm = self.getp('marked_point')
        if vm is None:
            l = len(self.getp('enabled_point'))
            self.setp('marked_point', [False]*l)
            vm = self.getp('marked_point')
        for x in range(len(vm)):
            vm[x] = False
        self.setp('marked_point', vm)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)
        import ifigure.events
        w = evt.GetEventObject().GetTopLevelParent()
        w.draw()
        return 1

    def onExportMark(self, evt):
        vm = self.getp('marked_point')
        if vm is None:
            return
        a = self._artists[0]
        x = a.get_xdata()
        y = a.get_ydata()
        xx = x[vm]
        yy = y[vm]
        data = {'xdata': xx, 'ydata': yy}
        self._export_shell(data, 'data', '')

    def enable_point(self, idx, value):
        if len(self.getp('enabled_point')) > idx+1:
            return
        self.getp('enabled_point')[self._figc_hit] = value

    def do_update_artist(self):
        if not self.isempty():
            a1 = self._artists[0]
            self.del_artist(delall=True)
        if self.isempty() and not self._suppress:
            self.generate_artist()
            a2 = self._artists[0]
            if a1 != a2:
                ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def set_enabled_point(self, value, a):
        self.setp('enabled_point', value)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

    def get_enabled_point(self, a):
        return self.getp('enabled_point')

    def set_marked_point(self, value, a):
        self.setp('marked_point', value)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

    def get_marked_point(self, a):
        return self.getp('marked_point')

    def picker_a(self, artist, evt):
        hit = False
        self._figc_hit = -1
        self._figc_hit_pos = (evt.xdata, evt.ydata)
        axes = artist.axes
        if axes is None:
            return False, {}
        x = artist.get_xdata()
        y = artist.get_ydata()
        for k, pd in enumerate(axes.transData.transform(np.transpose(np.vstack((x, y))))):
            if (abs(evt.x - pd[0]) < 5 and
                    abs(evt.y - pd[1]) < 5):
                hit = True
                self._figc_hit = k
                break

        if hit:
            return True, {'child_artist': artist}
        return FigPlot.picker_a(self, artist, evt)

    def dragstart(self, a, evt):
        x = self._artists[0].get_xdata()
        y = self._artists[0].get_ydata()
        self._drag_backup = (x[self._figc_hit],
                             y[self._figc_hit],)
        return 0

    def dragstart_a(self, a, evt):
        return self.dragstart(a, evt)

    def drag_a(self, a, evt, shift=None, scale=None):
        return self.drag(a, evt), scale

    def drag(self, a, evt):
        if evt.inaxes is None:
            return 0
        if evt.xdata is None:
            return 0
        if evt.ydata is None:
            return 0

        x = self._artists[0].get_xdata()
        y = self._artists[0].get_ydata()
        x[self._figc_hit] = evt.xdata
        y[self._figc_hit] = evt.ydata
        self._artists[0].set_xdata(x)
        self._artists[0].set_ydata(y)

        return 1

    def drag_a_get_hl(self, a):
        return self.drag_get_hl(a)

    def drag_get_hl(self, a):
        self._alpha_backup = a.get_alpha()
        for a in self._artists:
            a.set_alpha(0.5)
        return self._artists

    def drag_a_rm_hl(self, a):
        self.drag_rm_hl(a)

    def drag_rm_hl(self, a):
        a.set_alpha(self._alpha_backup)
        for a in self._artists:
            a.set_alpha(self._alpha_backup)

    def dragdone_a(self, a, evt, shift=None, scale=None):
        return self.dragdone(a, evt), scale

    def dragdone(self, a, evt):
        if evt.xdata is None:
            return

        x = self._artists[0].get_xdata()
        y = self._artists[0].get_ydata()
        x[self._figc_hit] = self._drag_backup[0]
        y[self._figc_hit] = self._drag_backup[1]

        x = self._artists[0].get_xdata().copy()
        y = self._artists[0].get_ydata().copy()
        x[self._figc_hit] = evt.xdata
        y[self._figc_hit] = evt.ydata
        action = UndoRedoFigobjMethod(self._artists[0],
                                      'data', (x, y))
        window = evt.guiEvent_memory.GetEventObject().GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry([action])
        return 1

    def get_masked_data(self):
        x = self.getp('x')
        y = self.getp('y')
        flag = self.getp('enabled_point')
        x2 = [x[k] for k in range(len(x)) if flag[k]]
        y2 = [y[k] for k in range(len(x)) if flag[k]]

        ret = [x2, y2]
        if self.getp('xerr') is not None:
            xerr = self.getp('xerr')
            xerr = [xerr[k] for k in range(len(x)) if flag[k]]
            ret.append(xerr)
        if self.getp('yerr') is not None:
            yerr = self.getp('yerr')
            yerr = [yerr[k] for k in range(len(x)) if flag[k]]
            ret.append(yerr)
        return tuple(ret)

    def set_data(self, value, a):
        # this one uses update_artist_request since
        # error bar needs to be changed accordingly.
        #
        # this means that it also needs to overwrite do_artist_update
        # to generte replace_event
        x = value[0]
        y = value[1]
        self.setp('x', x)
        self.setp('y', y)
        self._artists[0].set_xdata(x)
        self._artists[0].set_ydata(y)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)
        self.call_control_changed_callback()

    def get_data(self, a):
        x = self.getp('x').copy()
        y = self.getp('y').copy()
        return (x, y)

    def set_errdata(self, value, a):
        x = value[0]
        y = value[1]
        self.setp('xerr', x)
        self.setp('yerr', y)
        self.set_update_artist_request()
        self.get_figaxes().set_bmp_update(False)

    def get_errdata(self, a):
        x = _copy(self.getp('xerr'))
        y = _copy(self.getp('yerr'))
        return (x, y)

    def prepare_compact_savemode(self):
        var_bk = self._var.copy()
        return var_bk

    def get_mark_data(self):
        vm = self.getp('marked_point')
        l = len(self.getp('enabled_point'))
        if vm is None or len(vm) != l:
            self.setp('marked_point', [False]*l)
            vm = self.getp('marked_point')
        return vm

    def get_export_val(self, a):
        data = super(FigPlotC, self).get_export_val(a)
        data["xdata"] = self.getp('x')
        data["ydata"] = self.getp('y')
        if self.getp('xerr') is not None:
            data["xerrdata"] = self.getp('xerr')
        if self.getp('yerr') is not None:
            data["yerrdata"] = self.getp('yerr')

        return data
