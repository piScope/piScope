from __future__ import print_function
import numpy as np

import matplotlib.artist as artist
from matplotlib.artist import Artist, allow_rasterization
from matplotlib.figure import Figure

from operator import itemgetter
from ifigure.utils.cbook import EraseBitMap


class FigureMod(Figure):
    #    def __init__(self, *args, **kargs):
    #        self._frameDrown = False
    #        Figure.__init__(self,*args, **kargs)

    def _call_draw(self, aa, draw, renderer):
        bk = aa.get_rasterized()
        aa.set_rasterized(self.get_rasterized())
        draw(renderer)
        aa.set_rasterized(bk)

    def draw_others(self, renderer, dsu=None):

        #if self.frameon: self.patch.draw(renderer)
        # a list of (zorder, func_to_call, list_of_args)
        if dsu is None:
            dsu = []
        for a in self.patches + self.lines + self.artists:
            # skip if a is  frameart
            if hasattr(a, '_is_frameart') and a._is_frameart:
                continue
            dsu.append((a.get_zorder(), a, a.draw, renderer))

        # override the renderer default if self.suppressComposite
        # is not None
        not_composite = renderer.option_image_nocomposite()
        if self.suppressComposite is not None:
            not_composite = self.suppressComposite

        if len(self.images) <= 1 or not_composite or \
                not allequal([im.origin for im in self.images]):
            for a in self.images:
                dsu.append((a.get_zorder(), a, a.draw, renderer))
        else:
            # make a composite image blending alpha
            # list of (_image.Image, ox, oy)
            mag = renderer.get_image_magnification()
            ims = [(im.make_image(mag), im.ox, im.oy)
                   for im in self.images]

            im = _image.from_images(self.bbox.height * mag,
                                    self.bbox.width * mag,
                                    ims)

            im.is_grayscale = False
            l, b, w, h = self.bbox.bounds

            def draw_composite(_a):
                gc = renderer.new_gc()
                gc.set_clip_rectangle(self.bbox)
                gc.set_clip_path(self.get_clip_path())
                renderer.draw_image(gc, l, b, im)
                gc.restore()

            dsu.append((self.images[0].get_zorder(),
                        self, draw_composite, None))

        # render the figure text
        # first apply default to suptitle
        if self.figobj._title_artist is not None:
            tfont = self.figobj.getp('title_font')
            tweight = self.figobj.getp('title_weight')
            tstyle = self.figobj.getp('title_style')
            tsize = self.figobj.getp('title_size')
            tinfo = self.figobj.getp('suptitle_labelinfo')
            title = self.figobj._title_artist
            if tinfo[2] == 'default':
                title.set_family(tfont)
            if tinfo[3] == 'default':
                title.set_weight(tweight)
            if tinfo[4] == 'default':
                title.set_style(tstyle)
            if tinfo[5] == 'default':
                title.set_size(tsize)
        for a in self.texts:
            dsu.append((a.get_zorder(), a, a.draw, renderer))

        for a in self.legends:
            dsu.append((a.get_zorder(), a, a.draw, renderer))

        dsu.sort(key=itemgetter(0))
        for _zorder, a, draw_func, arg in dsu:
            self._call_draw(a, draw_func, arg)

    def draw_frame(self, renderer):
        # draw the figure bounding box, perhaps none for white figure
        #        self.patch.set_facecolor((0.75, 0.75, 0.75, 0.1))
        if self.frameon:
            self.patch.draw(renderer)
            dsu = []
            for a in self.patches + self.lines + self.artists:
                if hasattr(a, '_is_frameart') and a._is_frameart:
                    dsu.append((a.get_zorder(), a, a.draw, renderer))
            dsu.sort(key=itemgetter(0))
            for _zorder, a, draw_func, arg in dsu:
                self._call_draw(a, draw_func, arg)

    def draw_axes(self, renderer, axes, noframe=False):
        def walk_children(a):
            yield a
            for a2 in a.get_children():
                for a3 in walk_children(a2):
                    yield a3

        if self.frameon and not noframe:
            self._call_draw(self.patch, self.patch.draw, renderer)

        #
        #  this is show axis box front ....
        #
        alist = [a for a in walk_children(axes)
                 if hasattr(a, 'figobj') and a.figobj is not None]
        normalz = [a.get_zorder() for a in alist
                   if not a.figobj._floating]
        if len(normalz) != 0:
            z = max(normalz)
            for a in alist:
                if (hasattr(a, 'nozsort') and
                        a.get_zorder() < z):
                    a.set_zorder(z+0.001)

        dsize = self.figobj.getp('ticklabel_size')
        dsize2 = self.figobj.getp('axeslabel_size')
        tickfont = self.figobj.getp('tick_font')
        tickweight = self.figobj.getp('tick_weight')
        tickstyle = self.figobj.getp('tick_style')

        if not hasattr(axes, 'zaxis'):
            var = ((axes.figobj.get_axis_param('x'),
                    axes.get_xaxis(),
                    'x'),
                   (axes.figobj.get_axis_param('y'),
                    axes.get_yaxis(),
                    'y'))
        else:
            var = ((axes.figobj.get_axis_param('x'),
                    axes.get_xaxis(),
                    'x'),
                   (axes.figobj.get_axis_param('y'),
                    axes.get_yaxis(),
                    'y'),
                   (axes.figobj.get_axis_param('z'),
                    axes.zaxis,
                    'z'))

        xticks = axes.xaxis.get_major_ticks() + axes.xaxis.get_minor_ticks()
        yticks = axes.yaxis.get_major_ticks() + axes.yaxis.get_minor_ticks()
        for tick in xticks+yticks:
            tick.label1.set_family(tickfont)
            tick.label1.set_style(tickstyle)
            tick.label1.set_weight(tickweight)
            tick.label2.set_family(tickfont)
            tick.label2.set_style(tickstyle)
            tick.label2.set_weight(tickweight)

        for p, axis, name in var:
            if p.lsize == 'default':
                axes.tick_params(axis=name, labelsize=dsize)
            offsetText = axis.get_offset_text()

            if p.labelinfo[2] == 'default':
                #                 print dsize2
                axis.label.set_family(tickfont)
            if p.labelinfo[3] == 'default':
                axis.label.set_weight(tickweight)
#                 print dsize2
            if p.labelinfo[4] == 'default':
                #                 print dsize2
                axis.label.set_style(tickstyle)
            if p.labelinfo[5] == 'default':
                #                 print dsize2
                axis.label.set_size(dsize2)
            if p.otsize == 'default':
                offsetText.set_size(dsize)
            offsetText.set_weight(tickweight)
            offsetText.set_family(tickfont)
            offsetText.set_style(tickstyle)

#                func().label.set_size(dsize2)
        tfont = self.figobj.getp('title_font')
        tweight = self.figobj.getp('title_weight')
        tstyle = self.figobj.getp('title_style')
        tsize = self.figobj.getp('title_size')
        tinfo = axes.figobj.getp('title_labelinfo')
        title = axes.title
#        if axes.figobj.getp('use_def_size')[0]:
#
#            title.set_size(dsize)
        if tinfo[2] == 'default':
            title.set_family(tfont)
        if tinfo[3] == 'default':
            title.set_weight(tweight)
        if tinfo[4] == 'default':
            title.set_style(tstyle)
        if tinfo[5] == 'default':
            title.set_size(tsize)

        w = self.figobj.getp('axesbox_width')
        for s in axes.spines:
            axes.spines[s].set_linewidth(w)
        w = self.figobj.getp('axestick_width')
        axes.tick_params(axis='both', width=float(w))

        self._call_draw(axes, axes.draw, renderer)

    def draw_from_bitmap(self, renderer):

        if not self.get_visible():
            return
        renderer.open_group('figure')
        # do nothing
        renderer.close_group('figure')
        #self._cachedRenderer = renderer
        renderer = self.canvas.get_renderer()
        #self.canvas.draw_event(renderer)

        from matplotlib.backend_bases import DrawEvent
        self.canvas.callbacks.process("draw_event",
                                      DrawEvent("draw_from_bitmap", self.canvas,
                                                renderer))

    def draw(self, renderer):
        """
        Render the figure using :class:`matplotlib.backend_bases.RendererBase` instance renderer
        """
#        print('calling figure::draw')
#        import traceback
#        traceback.print_stack()
        return super(FigureMod, self).draw(renderer)
