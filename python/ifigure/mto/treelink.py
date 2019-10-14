from __future__ import print_function
import weakref
from ifigure.mto.treedict import TreeDict


class TreeLink(TreeDict):
    def __init__(self, parent=None, src=None, obj=None):
        if obj is not None:
            self._linkobj = weakref.ref(obj)
            self._linkobj_name = obj.get_full_path()
        else:
            obj = TreeDict()
            self._linkobj = weakref.ref(obj)
            self._linkobj_name = ''
            del obj
        self._linkvarname = None
        self._parent = parent
        super(TreeLink, self).__init__(parent=parent, src=src)
        self._name = 'link'

    @classmethod
    def isTreeLink(self):
        return True

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'next.png')
        return [idx]

    def can_have_child(self, child=None):
        return self._can_have_child

    def set_can_have_child(self, value):
        pass

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'treelink'

    def destroy(self, clean_owndir=True):
        # desotroing link does not affect linked object
        self._linkobj = None
        self._linkvarname = None
        super(TreeLink, self).destroy(clean_owndir=clean_owndir)

    def set_linkobj(self, obj):
        if obj is not None:
            self._linkobj = weakref.ref(obj)
            self._linkobj_name = obj.get_full_path()
        else:
            obj = TreeDict()
            self._linkobj = weakref.ref(obj)
            self._linkobj_name = ''
            del obj

    def get_linkobj(self):
        return self._linkobj()

    @property
    def is_linkalive(self):
        return (self._linkobj() is not None)

    def __repr__(self):
        str1 = super(TreeLink, self).__repr__()
        if self.is_linkalive:
            str2 = 'link to ' + self._linkobj().get_full_path()
        else:
            str2 = 'link dead'
        return str1 + ' (' + str2 + ')'

    #
    #  setting suppress does not propagate to linked obj
    #
    def set_suppress(self, val):
        self._suppress = val

    def save_data2(self, data):
        h2 = {"_linkobj_name": self._linkobj_name}
        data['TreeLink'] = (1, h2)
        return data

    def load_data2(self, data):
        h2 = data['TreeLink'][1]
        self._linkobj_name = h2['_linkobj_name']

    def init_after_load(self, olist, nlist):
        target = self._linkobj_name
        if target != '':
            target = self.find_by_full_path(target)
            self.set_linkobj(target)


if __name__ == '__main__':
    print("Demonstration")
    from ifigure.utils.treedict import TopTreeDict
    from ifigure.utils.project_top import ProjectTop
    from ifigure.fig_objects.fig_book import FigBook
    from ifigure.fig_objects.fig_page import FigPage
    from ifigure.fig_objects.fig_axes import FigAxes
    from ifigure.fig_objects.fig_plot import FigPlot
    from ifigure.fig_objects.py_code import PyModel

    page = FigPage()
    axes = FigAxes()
    plot = FigPlot()
    link = TreeLink(axes)
    page.add_child("axes", axes)
    page.add_child("link", link)
    axes.add_child("plot", plot)

    print(page.list_all())
