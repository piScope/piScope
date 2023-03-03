from __future__ import print_function
#  Name   :fig_book
#
#          this class to manage bundle of fig_pages
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History :
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
import wx
import sys
from wx import WXK_RETURN

from ifigure.mto.fig_obj import FigObj
from ifigure.mto.fig_page import FigPage
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import ifigure.utils.cbook as cbook
import ifigure.events

try:
    import ifigure.mdsplus
    has_mdsscope = True
except:
    has_mdsscope = False


class FigBook(FigObj):
    _image_id = [-1]
    _image_load_done = False

    def __init__(self, *args, **kywds):
        from ifigure.ifigure_config import iFigureConfig
        self._open = False
        self._screen_size = (0, 0)
        self._lock_scale = False
        self._viewer_class = 'BookViewer'
        self._viewer_module = 'ifigure.widgets.book_viewer.BookViewer'
        self._screen_ratio_lock = None
        # none locking, other size ratio of canvas size
        self._keep_data_in_tree = not iFigureConfig(
        ).setting['delbook_on_windowclose']
        super(FigBook, self).__init__(*args, **kywds)

    @classmethod
    def isFigBook(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'book'

    @classmethod
    def can_have_child(self, child=None):
        if isinstance(child, FigPage):
            return True
        if has_mdsscope:
            from ifigure.mdsplus.fig_mdsdata import FigMdsData
            if isinstance(child, FigMdsData):
                return True
        return False

    @property
    def isOpen(self):
        return self._open

    def onResize(self, evt):
        for page in self.walk_page():
            page.onResize(evt)

    def set_open(self, value):
        self._open = value
        self._image_update = False

    def classimage(self):
        if FigBook._image_load_done is False:
            FigBook._image_id = self.load_classimage()
            FigBook._image_load_done = True

        if self._open:
            return FigBook._image_id[1]
        else:
            return FigBook._image_id[0]

    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'book.png')
        idx2 = cbook.LoadImageFile(path, 'open_book.png')
        return [idx1, idx2]

    def pv_kshortcut(self, key):
        '''
        define keyborad short cut on project viewer
        must return a method responding key
        '''
        if not self.isOpen:
            return
        if key == WXK_RETURN:
            return self.onShow
        return None

    def generate_artist(self):
        pass
        # book does not have artist

    def del_artist(self, artist=None, delall=False):
        if delall:
            alist = self._artists
        else:
            alist = [artist]
        if len(alist) is len(self._artists):
            for name, child in self.get_children():
                child.del_artist(delall=True)
        else:
            print("deleting book artist partially...!?")

    def add_page(self, name=None, before=None, *args, **kywds):
        '''
        add a new page and return i_page
        '''
#        if 'before' in kywds:
#            before = kywds['before']
#            del  kywds['before']
#        else:
#            before = None
        fig_page = FigPage(*args, **kywds)
        if name is None:
            name = self.get_next_name(fig_page.get_namebase())

        ipage = self.add_child(name, fig_page, before=before)
        ipage = self.i_page(fig_page)
        return ipage

    def del_page(self, f_page):
        f_page.destroy()

    def num_page(self):
        '''
         return number of page
        '''
        i = 0
        for name, child in self.get_children():
            try:
                if child.isFigPage():
                    i = i+1
            except Exception:
                pass
        return i

    def get_page(self, ipage):
        '''
         return fig_page of ipage
         count only fig_page objects ignoring
         other children
        '''
        i = 0
        for name, child in self.get_children():
            try:
                if child.isFigPage():
                    if ipage == i:
                        return child
                    else:
                        i = i+1
            except Exception:
                pass
        return None

    def i_page(self, page):
        '''
        return ipage of page. ipage is an index
        of child without counting other than figpage 
        '''
        i = 0
        for name, child in self.get_children():
            if isinstance(child, FigPage):
                if child == page:
                    return i
                i = i+1
        return -1

    def walk_page(self):
        i = 0
        for name, child in self.get_children():
            if isinstance(child, FigPage):
                yield child

    def save_data2(self, data):
        app = self.get_root_parent().app
        viewer = app.find_bookviewer(self)
        if viewer is not None:
            s = viewer.canvas.get_canvas_screen_size()
            self._screen_size = (s[0], s[1])

        # the first element is version code
        param = {"_screen_size": self._screen_size,
                 "_keep_data_in_tree": self._keep_data_in_tree,
                 "_screen_ratio_lock": self._screen_ratio_lock,
                 "_viewer_class": self._viewer_class,
                 "_viewer_module": self._viewer_module}
        data['FigBook'] = (1, {}, param)
        data = super(FigBook, self).save_data2(data)
        return data

    def load_data2(self, data):
        self.handle_loaded_figobj_data(data, 'FigBook')
        param = data['FigBook'][2]
        for key in param:
            setattr(self, key, param[key])
        super(FigBook, self).load_data2(data)

    def toggle_keep_data(self):
        self._keep_data_in_tree = not (self._keep_data_in_tree)

    def get_keep_data(self):
        return self._keep_data_in_tree
#
#  tree viewer menu
#

    def tree_viewer_menu(self):
        app = self.get_root_parent().app
        if app in app.viewers:
            t = '-'
        else:
            t = ''

        m = [('Add Page', self.onAddPage, None), ]
        if self.isOpen:
            m = m + \
                [('Close Book', self.onCloseBook, None), ]

        elif (self.num_page() != 0 and not self.isOpen):
            m = m + \
                [(t+'Open in Main Window', self.onOpenMViwer, None),
                 ('Open in BookViewer', self.onOpenViwer, None), ]
            if (self._viewer_class != 'BookViewer' and
                    self._viewer_class != 'MDSScope'):
                m.append(('Open in '+self._viewer_class,
                          self.onOpenDefViewer, None))
            if has_mdsscope:
                m.append(('Open in MDSScope', self.onOpenMdsScope, None))
        else:
            m = m + \
                [('-Open in BookViwer', self.onOpenViwer, None), ]
            if self._viewer_class != 'BookViewer':
                m.append(('-Open in '+self._viewer_class,
                          self.onOpenDefViewer, None))
            if has_mdsscope:
                m.append(('-Open in MDSScope', self.onOpenMdsScope, None))
        if self._keep_data_in_tree:
            m = m + \
                [('^Keep book when window closed', self.onToggleKeepData, None), ]
        else:
            m = m + \
                [('*Keep book when window closed', self.onToggleKeepData, None), ]
        m = m + [('---', None, None)] + \
            super(FigBook, self).tree_viewer_menu()
        return m

    def onToggleKeepData(self, e):
        self.toggle_keep_data()
        e.Skip()

    def onAddPage(self, e):
        self.add_page()
        e.Skip()

    def onShow(self, e):
        id = e.GetEventObject()
        ifigure.events.SendShowPageEvent(self, id)

    def onOpenDefViewer(self, e):
        mod = __import__(self._viewer_module)
        md = sys.modules[self._viewer_module]
        the_class = getattr(md, self._viewer_class)
        ifigure.events.SendOpenBookEvent(self,
                                         w=e.GetEventObject(),
                                         viewer=the_class)
        e.Skip()

    def onOpenMViwer(self, e):
        app = self.get_root_parent().app
        app.open_book_in_appwindow(self)

    def onOpenViwer(self, e):
        from ifigure.widgets.book_viewer import BookViewer
        ifigure.events.SendOpenBookEvent(self,
                                         w=e.GetEventObject(),
                                         viewer=BookViewer)
        e.Skip()

    def onOpenMdsScope(self, e):
        from ifigure.mdsplus.mdsscope import MDSScope
        ifigure.events.SendOpenBookEvent(self,
                                         w=e.GetEventObject(),
                                         viewer=MDSScope)
        e.Skip()

    def onCloseBook(self, e):
        viewer = self.get_root_parent().app.find_bookviewer(self)
        ovalue = self._keep_data_in_tree
        self._keep_data_in_tree = True

        if viewer is not None:
            if viewer is not wx.GetApp().GetTopWindow():
                viewer.onClose(None)
            else:
                viewer.close_figurebook()
        self._keep_data_in_tree = ovalue
        e.Skip()

    def get_keep_data_in_tree(self):
        return self._keep_data_in_tree

    def set_keep_data_in_tree(self, value):
        self._keep_data_in_tree = value

    def find_bookviewer(self):
        app = self.get_root_parent().app
        return app.find_bookviewer(self)

    from ifigure.widgets.at_wxthread import at_wxthread
    @at_wxthread
    def Open(self, vc):
        app = wx.GetApp().TopWindow
        if self.isOpen:
            v = app.find_bookviewer(self)
            if isinstance(v, vc):
                return v
            v.onClose()
        viewer = app.open_book_in_newviewer(vc, self, ipage=0)
        return viewer

    @at_wxthread
    def Close(self):
        app = wx.GetApp().TopWindow
        if self.isOpen:
            v = app.find_bookviewer(self)
            v.onClose()
