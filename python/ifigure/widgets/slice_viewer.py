import wx
from ifigure.widgets.book_viewer import BookViewer
from ifigure.mto.fig_plot import FigPlot


class SliceViewer(BookViewer):
    def __init__(self, *args, **kargs):
        kargs['style'] = (wx.FRAME_FLOAT_ON_PARENT | wx.MINIMIZE_BOX
                          | wx.MAXIMIZE_BOX | wx.RESIZE_BORDER
                          | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX
                          | wx.CLIP_CHILDREN)
#        print kargs
        BookViewer.__init__(self, *args, **kargs)
        f_page = self.get_page(0)
        f_page.set_section(2)
        f_axes = self.get_axes(0, 0)
        for name, child in f_axes.get_children():
            child.destroy()
        obj = FigPlot([0], [0])
        f_axes.add_child('xslice_plot1', obj)
        obj.set_suppress(True)
        obj = FigPlot([0], [0])
        f_axes.add_child('xslice_plot2', obj)
        obj.set_suppress(True)
        f_axes.realize()
        f_axes = self.get_axes(0, 1)
        for name, child in f_axes.get_children():
            child.destroy()
        obj = FigPlot([0], [0])
        f_axes.add_child('xslice_plot1', obj)
        obj.set_suppress(True)
        obj = FigPlot([0], [0])
        f_axes.add_child('xslice_plot2', obj)
        obj.set_suppress(True)
        f_axes.realize()

    def update_curve(self, idx, x, y, data1, data2):
        from ifigure.interactive import plot, nsec, isec, update, title, xlabel, ylabel
        from ifigure import _cursor_config as cconfig

        self.Raise()
        c1 = cconfig["1dcolor1"]
        c2 = cconfig["1dcolor2"]
        if idx == 0:
            c = c1
        else:
            c = c2

        f_axes = self.get_axes(0, 0)
        f_axes.set_bmp_update(False)
        title = 'x slice : x = '+str(x)
        self._update_curve(idx, f_axes, c, x, y, data1, title)
        f_axes = self.get_axes(0, 1)
        f_axes.set_bmp_update(False)
        title = 'y slice : y = '+str(y)
        self._update_curve(idx, f_axes, c, x, y, data2, title)
        self.draw()

    def _update_curve(self, idx, f_axes, c, x, y, data, title):

        if f_axes.num_child() == 0:
            obj = FigPlot([0], [0])
            f_axes.add_child('xslice_plot1', obj)
            obj = FigPlot([0], [0])
            f_axes.add_child('xslice_plot2', obj)
            f_axes.realize()
        j = 0
        for name, child in f_axes.get_children():
            if (isinstance(child, FigPlot)):
                if j == idx:
                    child.setvar('x', data[0])
                    child.setvar('y', data[1])
                    child.set_suppress(False)
                    child.reset_artist()
                    a = child._artists[0]
                    a.set_color(c)
                    break
                else:
                    j = j+1
        f_axes.adjust_axes_range()
        v = f_axes.get_title(f_axes._artists[0])
        v[0] = title
        v = f_axes.set_title(v, f_axes._artists[0])
        f_axes.set_bmp_update(False)
