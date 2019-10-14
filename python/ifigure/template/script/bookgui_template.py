from ifigure.interactive import figure
from ifigure.widgets.book_viewer import BookViewer
import numpy as np
import wx


class BookViewerGui(BookViewer):
    def __init__(self, *args, **kargs):
        BookViewer.__init__(self, *args, **kargs)
        extra_menu = wx.Menu()
        self.menuBar.Insert(self.menuBar.GetMenuCount()-1,
                            extra_menu, "ExtraMenu")
        self.add_menu(extra_menu, wx.ID_ANY,
                      "Plot Something...",
                      "plot sine wave (this is string for status bar)",
                      self.onPlotSomething)

    def onPlotSomething(self, evt):
        t = np.arange(1000.)/999.
        f = 10.
        self.plot(t, np.sin(2*3.14*f*t))


if not obj.get_parent().has_child('bookgui_book'):
    v = figure()
    v.book.rename('bookgui_book')
    v.book.set_keep_data_in_tree(True)
    v.book.Close()

obj.get_parent().bookgui_book.Open(BookViewerGui)
