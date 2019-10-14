''''
   this example shows how to add extra menu to mdsscope
   and add call-back routines when the menu item is 
   selected
'''

from ifigure.interactive import figure
from ifigure.mdsplus.mdsscope import MDSScope
import wx

exp = 'xtomo'
node = '.BRIGHTNESSES.ARRAY_3:CHORD_23'


class MDSScopeExtraMenuGUI(MDSScope):
    def __init__(self, *args, **kargs):
        MDSScope.__init__(self, *args, **kargs)
        extra_menu = wx.Menu()
        self.menuBar.Insert(self.menuBar.GetMenuCount()-1,
                            extra_menu, "ExtraMenu")
        self.add_menu(extra_menu, wx.ID_ANY,
                      "Plot Spectra...",
                      "plot spectra of panel #1",
                      self.onPlotSpectra)
        self.nsec(2)
        self.cls()

        self.data = self.AddSignalScript(experiment=exp,
                                         signals={'y': node},
                                         kind='plot')

    def onPlotSpectra(self, evt):
        try:
            p = self.data.get_child(0)
            x = p.getvar('x')
            y = p.getvar('y')
            self.isec(1)
            self.spec(x, y)
        except:
            import traceback
            traceback.print_exc()
        evt.Skip()


if not obj.get_parent().has_child('mdsscope_extramenu_book'):
    v = figure()
    v.book.rename('mdsscope_extramenu_book')
    v.book.set_keep_data_in_tree(True)
    v.book.Close()

obj.get_parent().mdsscope_extramenu_book.Open(MDSScopeExtraMenuGUI)
