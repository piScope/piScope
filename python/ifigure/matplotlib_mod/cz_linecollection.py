from matplotlib.collections import LineCollection
from matplotlib.cm import ScalarMappable
import numpy as np
from matplotlib.artist import allow_rasterization
from matplotlib.path import Path
from matplotlib.transforms import Bbox, TransformedPath
from matplotlib.colors import Colormap


class CZLineCollection(LineCollection):
    def __init__(self,  x, y, cz,
                 cmap='jet', linestyle='solid',
                 pickradius=5,  alpha=None,  **kargs):
        if linestyle is None:
            kargs['linestyle'] = 'solid'
            self._nodraw = True
        else:
            kargs['linestyle'] = linestyle
            self._nodraw = False
        self.x = x
        self.y = y
        self.cz = cz
        self.set_xydata()
        self.pickradius = pickradius
        segments = self._calc_segments()
#        self.set_linewidth(1)
        LineCollection.__init__(self, segments, **kargs)
        self.set_array(cz)
        self._cz_linesytle_name = linestyle
#        self._cz_alpha = alpha
        self._transformed_path = None
        self.set_alpha(alpha)

    def get_xdata(self):
        return self.x

    def get_ydata(self):
        return self.y

    def get_czdata(self):
        return self.cz

    def set_xydata(self):
        self._xydata = np.transpose(np.array([self.x, self.y]))

    def set_xdata(self, x):
        self.x = x
        if (x.size != self.y.size or
                x.size != self.cz.size):
            return
        segments = self._calc_segments()
        self.set_segments(segments)
        self.set_xydata()
        self.set_array(self.cz)
        self.set_alpha(self._cz_alpha)

    def set_ydata(self, y):
        self.y = y
        if (y.size != self.x.size or
                y.size != self.cz.size):
            return
        segments = self._calc_segments()
        self.set_segments(segments)
        self.set_xydata()
        self.set_array(self.cz)
        self.set_alpha(self._cz_alpha)

    def set_czdata(self, cz):
        self.cz = cz
        if (cz.size != self.x.size or
                cz.size != self.y.size):
            return
        segments = self._calc_segments()
        self.set_segments(segments)
        self.set_xydata()
        self.set_array(self.cz)
        self.set_alpha(self._cz_alpha)

    def set_alpha(self, v):
        #        LineCollection.set_alpha(self, v)
        #        calling superclass set_alpha does make color along
        #        the line constant
        self._alpha = None
        self._cz_alpha = v
        ec = self.get_edgecolors()
        r = (ec[:, 0] != 0.)
        g = (ec[:, 1] != 0.)
        b = (ec[:, 2] != 0.)
        if self._cz_alpha is None:
            v = 1.0
        ec[np.logical_or(np.logical_or(r, g), b), 3] = v

#        self.get_edgecolors()[:,3] = v
    def update_scalarmappable(self):
        #
        #  update_scalamappable in super class will
        #  set proper size of edgecolors
        #  then I need to set alpha
        #
        LineCollection.update_scalarmappable(self)
        self.set_alpha(self._cz_alpha)

    def get_alpha(self):
        return self._cz_alpha

    def set_color(self, v):
        pass

    def get_color(self):
        pass

    def set_linewidth(self, v):
        LineCollection.set_linewidth(self, v)

    def get_linewidth(self):
        v = LineCollection.get_linewidth(self)[0]
        return v

    def set_linestyle(self, v):
        if v is None or v == 'None':
            self._nodraw = True
        else:
            self._nodraw = False
            LineCollection.set_linestyle(self, v)
        self._cz_linesytle_name = v

    def get_linestyle(self):
        if self._nodraw:
            return 'None'
        return self._cz_linesytle_name

    def set_marker(self, v):
        pass

    def get_marker(self):
        pass

    def set_markersize(self, v):
        pass

    def get_markersize(self):
        pass

    def set_markeredgecolor(self, v):
        pass

    def get_markeredgecolor(self):
        pass

    def set_markerfacecolor(self, v):
        pass

    def get_markerfacecolor(self):
        pass

    def set_markeredgewidth(self, v):
        pass

    def get_markeredgewidth(self):
        pass

    def contains(self, mouseevent):
        '''
        a hit test based on what is used in 
        line2D
        '''
        from matplotlib.lines import segment_hits
        if self.figure is None:
            pixels = self.pickradius
        else:
            pixels = self.figure.dpi / 72. * self.pickradius

        olderrflags = np.seterr(all='ignore')
        transformed_path = self._get_transformed_path()
        path, affine = transformed_path.get_transformed_path_and_affine()
        path = affine.transform_path(path)
        xy = path.vertices
        xt = xy[:, 0]
        yt = xy[:, 1]

        try:
            # If line, return the nearby segment(s)
            ind = segment_hits(mouseevent.x, mouseevent.y, xt, yt, pixels)
        finally:
            np.seterr(**olderrflags)
        return len(ind) > 0, dict(ind=ind)

    def get_window_extent(self, renderer):
        bbox = Bbox([[0, 0], [0, 0]])
        trans_data_to_xy = self.get_transform().transform
        bbox.update_from_data_xy(trans_data_to_xy(self._xydata),
                                 ignore=True)
        return bbox

    @allow_rasterization
    def draw(self, *argrs, **kargs):
        self._transform_path()
        if not self._nodraw:
            LineCollection.draw(self, *argrs, **kargs)

    def _calc_segments(self):
        points = np.array([self.x, self.y]).T.reshape(-1, 1, 2)
        return np.concatenate([points[:-1], points[1:]], axis=1)

    def _transform_path(self):
        _path = Path(self._xydata)
        self._transformed_path = TransformedPath(_path, self.get_transform())

    def _get_transformed_path(self):
        """
        Return the :class:`~matplotlib.transforms.TransformedPath` instance
        of this line.
        """
        if self._transformed_path is None:
            self._transform_path()
        return self._transformed_path
