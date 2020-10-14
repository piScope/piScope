import six

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.ticker import ScalarFormatter
from mpl_toolkits.mplot3d.axes3d import Axes3D
import mpl_toolkits.mplot3d.proj3d as proj3d
import mpl_toolkits.mplot3d.art3d as art3d
import matplotlib.transforms as trans
import ifigure.events as events
from matplotlib.artist import allow_rasterization
import numpy as np
import traceback
from matplotlib.collections import Collection, LineCollection, \
    PolyCollection, PatchCollection, PathCollection


class AxesMod(Axes):
    def __new__(cls, *args, **kargs):
        if isinstance(args[0], Axes):
            args[0].__class__ = AxesMod
            return args[0]
        else:
            return Axes.__new__(cls)

    def __init__(self, *args, **kargs):
        self._nomargin_mode = False
        self._offset_trans_changed = False
        self._ypad = None
        if isinstance(args[0], Axes):
            return
        super(AxesMod, self).__init__(*args, **kargs)

    def set_nomargin_mode(self, mode):
        self._nomargin_mode = mode
        if True:
            ay = self.get_yaxis()
            if len(ay.get_major_ticks()) > 0:
                yt = ay.get_major_ticks()[0]
                self._ypad = yt.get_pad()

    def get_nomargin_mode(self):
        return self._nomargin_mode

    def cz_plot(self, x, y, z, **kywds):
        from ifigure.matplotlib_mod.cz_linecollection import CZLineCollection
        a = CZLineCollection(x, y, z,  **kywds)
        self.add_collection(a)
        return a

    def _get_all_ax_artists(self, inframe=False):
        '''
        return all ax artists in the container
        '''
        artists = []

        artists.extend(self.collections)
        artists.extend(self.patches)
        artists.extend(self.lines)
        artists.extend(self.texts)
        artists.extend(self.artists)

        # the frame draws the edges around the axes patch -- we
        # decouple these so the patch can be in the background and the
        # frame in the foreground. Do this before drawing the axis
        # objects so that the spine has the opportunity to update them.
        if self.axison and self._frameon:
            artists.extend(six.itervalues(self.spines))

        if self.axison and not inframe:
            if self._axisbelow:
                self.xaxis.set_zorder(0.5)
                self.yaxis.set_zorder(0.5)
            else:
                self.xaxis.set_zorder(2.5)
                self.yaxis.set_zorder(2.5)
            artists.extend([self.xaxis, self.yaxis])
        if not inframe:
            artists.append(self.title)
            artists.append(self._left_title)
            artists.append(self._right_title)
        artists.extend(self.tables)
        if self.legend_ is not None:
            artists.append(self.legend_)

        return artists

    @allow_rasterization
    def draw(self, renderer):
        ax = self.get_xaxis()
        ay = self.get_yaxis()

        formatters = [self.get_xaxis().get_major_formatter(),
                      self.get_xaxis().get_minor_formatter(),
                      self.get_yaxis().get_major_formatter(),
                      self.get_yaxis().get_minor_formatter()]
        if hasattr(self, 'get_zaxis'):
            formatters.extend([self.get_zaxis().get_major_formatter(),
                               self.get_zaxis().get_minor_formatter()])

        #
        # 2015.10 ScalarFormatter stores usetex, useMathtext when the
        #         object is instantiated. To switch usetex to print
        #         text as text object in pdf, those interanal values
        #         needs to be manipulated.

        usetex = mpl.rcParams['text.usetex']
        org_useMathtext = []
        org_usetex = []
        for f in formatters:
            if isinstance(f, ScalarFormatter):
                org_useMathtext.append(f._useMathText)
                org_usetex.append(f._usetex)
                if usetex:
                    f._useMathText = False
                    f._usetex = True
            else:
                org_usetex.append(False)
                org_useMathtext.append(False)  # dummy data

        ### text size is not know here ###
        t = ay.get_offset_text()
        w, h, d = renderer.get_text_width_height_descent('lp',
                                                         t._fontproperties,
                                                         ismath=False)
        wx, hx, d = renderer.get_text_width_height_descent('lp',
                                                           ax.label._fontproperties,
                                                           ismath=False)
        wy, hy, d = renderer.get_text_width_height_descent('lp',
                                                           ay.label._fontproperties,
                                                           ismath=False)
        xticks = ax.get_major_ticks() + ax.get_minor_ticks()
        yticks = ay.get_major_ticks() + ay.get_minor_ticks()
        if self._nomargin_mode:
            for xtick in xticks:
                xtick.set_pad(-abs(xtick.get_pad()))
                xtick.label1.set_verticalalignment('bottom')
                xtick.label2.set_verticalalignment('top')
            for ytick in yticks:
                ytick.set_pad(- wy)
                ytick.label1.set_horizontalalignment('left')
                ytick.label2.set_horizontalalignment('right')
            self.title.set_position((0.5, 0.9))
            self.title.set_verticalalignment('top')

            if not self._offset_trans_changed:
                t2x = trans.ScaledTranslation(0, 3*w/72,
                                              self.figure.dpi_scale_trans)
                xtext = ax.get_offset_text()
                t0 = xtext.get_transform()
                xtext.set_transform(t0+t2x)
                px = xtext.get_position()
                xtext.set_position((0.9, px[1]))
                xtext = ax.label
                t0 = xtext.get_transform()
                xtext.set_transform(t0+t2x)

                t2y = trans.ScaledTranslation(0, -2*w/72,
                                              self.figure.dpi_scale_trans)
                ytext = ay.get_offset_text()
                t0 = ytext.get_transform()
                ytext.set_transform(t0+t2y)
                py = ytext.get_position()
                ytext.set_position((0.1, py[1]))
                self._offset_trans_changed = True

                t2y2 = trans.ScaledTranslation(3*h/72, 0,
                                               self.figure.dpi_scale_trans)
                ytext = ay.label
                t0 = ytext.get_transform()
                ytext.set_transform(t0+t2y2)
        else:
            for xtick in xticks:
                xtick.set_pad(abs(xtick.get_pad()))
                xtick.label1.set_verticalalignment('top')
                xtick.label2.set_verticalalignment('bottom')
            for ytick in yticks:
                if self._ypad is None:
                    self._ypad = 4
                ytick.set_pad(self._ypad)
                ytick.label1.set_horizontalalignment('right')
                ytick.label2.set_horizontalalignment('left')
            self.title.set_position((0.5, 1.0))
            self.title.set_verticalalignment('baseline')

            if self._offset_trans_changed:
                t2x = trans.ScaledTranslation(0, -3*w/72,
                                              self.figure.dpi_scale_trans)
                xtext = ax.get_offset_text()
                t0 = xtext.get_transform()
                xtext.set_transform(t0+t2x)
                px = xtext.get_position()
                xtext.set_position((1.0, px[1]))
                xtext = ax.label
                t0 = xtext.get_transform()
                xtext.set_transform(t0+t2x)

                t2y = trans.ScaledTranslation(0, 2*w/72,
                                              self.figure.dpi_scale_trans)
                ytext = ay.get_offset_text()
                t0 = ytext.get_transform()
                ytext.set_transform(t0+t2y)
                py = ytext.get_position()
                ytext.set_position((0.0, py[1]))
                self._offset_trans_changed = False

                t2y2 = trans.ScaledTranslation(-3*h/72, 0,
                                               self.figure.dpi_scale_trans)
                ytext = ay.label
                t0 = ytext.get_transform()
                ytext.set_transform(t0+t2y2)

        area = self.figobj.getp('area')
        edge_only = self.figobj._edge_only

        if edge_only[1]:
            hide_xbottom = True
            col1 = xticks[0].label1.get_color()
            for xtick in xticks:
                xtick.label1.set_color('None')
        else:
            hide_xbottom = False
        if edge_only[0]:
            hide_yleft = True
            col2 = yticks[0].label1.get_color()
            for ytick in yticks:
                ytick.label1.set_color('None')
        else:
            hide_yleft = False

        for a in self.artists:
            if not hasattr(a, 'figobj'):
                continue
            if a.figobj.get_namebase() == 'legend':
                l = a.figobj
                l.set_legendlabel_prop(l.getp('legendlabelprop'), a)

        #
        #  zorder of rasterized artsits is moved to negative
        #  before rendering
        #
        artists = self.get_children()
        artists.remove(self.patch)
        artists.remove(self.title)
        artists.remove(self._left_title)
        artists.remove(self._right_title)
        rastered_a = [a for a in artists if a.get_rasterized()]

        if len(rastered_a) > 0:
            delta_a = np.max([a.zorder for a in rastered_a])+1
            for a in rastered_a:
                a.zorder = a.zorder-delta_a

        try:
            super(AxesMod, self).draw(renderer)
        except:
            traceback.print_exc()
        finally:
            if len(rastered_a) > 0:
                for a in rastered_a:
                    a.zorder = a.zorder+delta_a

            if hide_xbottom:
                for xtick in xticks:
                    xtick.label1.set_color(col1)
            if hide_yleft:
                for ytick in yticks:
                    ytick.label1.set_color(col2)

            #
            # Restore orinal setting of usetex in scallar formatter
            #
            for org1, org2, f in zip(org_useMathtext, org_usetex, formatters):
                if isinstance(f, ScalarFormatter):
                    f._useMathText = org1
                    f._usetex = org2
