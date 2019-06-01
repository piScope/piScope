'''
   Utility class for triplot, tripcolor
'''
import ifigure.events
import numpy as np


class TrianglePlots(object):
    def __init__(self):
        if not hasattr(self, '_tri'):
            self._tri = None

    def get_tri(self):
        return self._tri

    def set_mask(self, mask, a=None):
        self.setp('mask', mask)
        self.set_bmp_update(False)

    def get_mask(self, a=None):
        return self.getp('mask')

    def get_masked_tri(self):
        mask = self.getp('mask')
        if mask is not None:
            tri = self._tri.compress(1 - mask, axis=0)
        else:
            tri = self._tri
        return tri

    def mask_array(self, mask, no_draw=False):
        self.set_mask(mask)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)

    def mask_outside(self, edge, op=np.logical_or, no_draw=False):
        import ifigure.utils.triangulation_wrapper
        x, y = self.getp(('x', 'y'))
        tri = self._tri
        mask = ifigure.utils.triangulation_wrapper.mask_outside(x, y, tri, edge,
                                                                mask=self.getp('mask'), op=op)
        self.set_mask(mask)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)

    def mask_inside(self, edge, op=np.logical_or, no_draw=False):
        import ifigure.utils.triangulation_wrapper
        x, y = self.getp(('x', 'y'))
        tri = self._tri
        mask = ifigure.utils.triangulation_wrapper.mask_inside(x, y, tri, edge,
                                                               mask=self.getp('mask'), op=op)
        self.set_mask(mask)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)

    def mask_none(self, no_draw=False):
        self.set_mask(None)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)

    def mask_skew(self, th, op=np.logical_or, no_draw=False):
        import ifigure.utils.triangulation_wrapper
        x, y = self.getp(('x', 'y'))
        tri = self._tri
        mask = ifigure.utils.triangulation_wrapper.mask_skew(x, y, tri, th,
                                                             mask=self.getp('mask'), op=op)
        self.set_mask(mask)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)

    def get_tri_area(self, th, op=np.logical_or, no_draw=False):
        import ifigure.utils.triangulation_wrapper
        x, y = self.getp(('x', 'y'))
        tri = self._tri
        area = ifigure.utils.triangulation_wrapper.get_area(x, y, tri)
        return area

    def mask_area(self, th, op=np.logical_or, no_draw=False):
        import ifigure.utils.triangulation_wrapper
        x, y = self.getp(('x', 'y'))
        tri = self._tri
        mask = ifigure.utils.triangulation_wrapper.mask_area(x, y, tri, th,
                                                             mask=self.getp('mask'), op=op)
        self.set_mask(mask)

        self.del_artist(delall=True)
        if hasattr(self, "_data_extent"):
            self._data_extent = None
        self.generate_artist()
        if not no_draw:
            ifigure.events.SendPVDrawRequest(self)
