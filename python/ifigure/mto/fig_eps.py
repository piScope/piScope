from __future__ import print_function
#
#  fig_eps
#
#     This class is to place raster image generated fro
#     eps file
#     It will keep eps file and embed it as vector
#     data when exporting to eps/pdf format
#
#     it uses convert for raster image generation.
#     ps2pdf -dEPSCrop is used for pdf genration.
#     pdfrw is used to Form XObject generation.
#
#     It create a FigImageV object which is essentially
#     FigImage, but draw is overwritten so that when
#     renderer is RendererPS or RenderePDF, it bypass
#     the orignal routine and add eps/pdf to a picutre
#     file.
#
#     FigImageV is placed in figure.artists, not figure.images
#     in order to avoid image decomposition in figure::draw
#
#  History:
#         2013 12
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
from matplotlib.backends.backend_pdf import RendererPdf, PdfFile, Name, Op, pdfRepr
import matplotlib.backends.backend_ps
from matplotlib.backends.backend_ps import RendererPS
import six
import weakref
import traceback

from ifigure.mto.fig_obj import FigObj
from ifigure.mto.axis_user import XUser, YUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import sys
import shutil
from six import itervalues, iteritems
import subprocess as sp
import numpy as np
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
from scipy.interpolate import griddata
from ifigure.utils.cbook import ProcessKeywords
import matplotlib
from matplotlib.tri import Triangulation
from matplotlib.cm import ScalarMappable
import matplotlib.image as mpimage
from ifigure.utils.args_parser import ArgsParser
from ifigure.mto.fig_box import FigBox
from matplotlib.image import FigureImage
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigEPS')


def calc_newpos_from_anchor(p1, p2, dp, mode):
    if mode == 0:
        return (p1, p1+dp)
    elif mode == 1:
        m = (p1+p2)/2.
        return (m-dp/2., m+dp/2.)
    else:
        return (p2-dp, p2)


unicode_file = 'unicode_literals' in dir(matplotlib.backends.backend_ps)

eps_funcs = '\n'.join(['/BeginEPSF {',
                       '  /EPSFsave save def',
                       '  count /OpStackSize exch def',
                       '  /DictStackSize countdictstack def',
                       '  % turn off showpage',
                       '  /showpage {} def',
                       '  % set up default graphics state',
                       '  0 setgray 0 setlinecap',
                       '  1 setlinewidth 0 setlinejoin',
                       '  10 setmiterlimit [] 0 setdash newpath',
                       '  /languagelevel where',
                       '  {pop languagelevel 1 ne',
                       '    {false setstrokeadjust false setoverprint} if',
                       '  } if',
                       '} bind def',
                       '/EndEPSF {',
                       '  count OpStackSize sub',
                       '  dup 0 lt {neg {pop} repeat} {pop} ifelse',
                       '  countdictstack DictStackSize sub ',
                       '  dup 0 lt {neg {end} repeat} {pop} ifelse',
                       '  EPSFsave restore',
                       '} bind def\n'])


class PdfFile_plus(PdfFile):
    def close(self):
        print('PdfFile plus is closing file')
        self.endStream()
        # Write out the various deferred objects
        self.writeFonts()
        self.writeObject(self.alphaStateObject,
                         dict([(val[0], val[1])
                               for val in itervalues(self.alphaStates)]))
        self.writeHatches()
        self.writeGouraudTriangles()
        xobjects = dict(iter(itervalues(self.images)))
        for tup in itervalues(self.markers):
            xobjects[tup[0]] = tup[1]
        for name, value in iteritems(self.multi_byte_charprocs):
            xobjects[name] = value
        for name, path, trans, ob, join, cap, padding, filled, stroked in self.paths:
            xobjects[name] = ob
        for tup in itervalues(self.pdfs):
            xobjects[tup[0]] = tup[1]
        self.writeObject(self.XObjectObject, xobjects)
        self.writeImages()
        self.writeMarkers()
        self.writePathCollectionTemplates()
        self.writePdfs()
        self.writeObject(self.pagesObject,
                         {'Type': Name('Pages'),
                          'Kids': self.pageList,
                          'Count': len(self.pageList)})
        self.writeInfoDict()

        # Finalize the file
        self.writeXref()
        self.writeTrailer()
        if self.passed_in_file_object:
            self.fh.flush()
        elif self.original_file_like is not None:
            self.original_file_like.write(self.fh.getvalue())
            self.fh.close()
        else:
            self.fh.close()

    def pdfObject(self, pdf):
        """Return name of an pdf XObject representing the given pdf."""
        pair = self.pdfs.get(id(pdf), None)
        if pair is not None:
            return pair[1]

        name = Name('Pdf%d' % self.nextPdf)
        ob = self.reserveObject('pdf %d' % self.nextPdf)
        self.nextPdf += 1
        self.pdfs[id(pdf)] = (pdf, name, ob)

        return name

    def pdfResources(self, d, pairs=None):
        from pdfrw.objects import PdfName, PdfArray, PdfDict, IndirectPdfDict, PdfObject
        if pairs is None:
            pairs = []
        v = dict()
        for key in d:
            if not isinstance(d[key], PdfDict):
                #                if isinstance(d[key], str):
                #                    v[key[1:]] = d[key][1:]
                #                else:
                v[key[1:]] = self.pdfobj2value(d[key])
            else:
                id = self.reserveObject('pdf resource element')
                v[key[1:]] = id
                pairs.append((id, d[key]))
        return v, pairs

    def pdfobj2value(self, obj):
        from pdfrw.objects import PdfName, PdfArray, PdfDict, IndirectPdfDict, PdfObject

        def convert(m):
            if str(m).startswith('/'):
                return Name(str(m)[1:])
            elif str(m) in ['false', 'true']:
                if str(m) == 'false':
                    return False
                else:
                    return True
            else:
                return eval(m)
        if isinstance(obj, PdfArray):
            return [convert(x) for x in obj]
        else:
            return convert(obj)

    def writeObject_stream(self, object, contents, stream):
        self.recordXref(object.id)
        self.write(("%d 0 obj\n" % object.id).encode('ascii'))
        self.write(pdfRepr(contents))
        self.write(b"\nstream\n")
        self.write(np.fromstring(stream, np.uint8))
        self.write(b"\nendstream\nendobj\n")

    def writePdfResources(self, pairs):
        from pdfrw.objects import PdfName, PdfArray, PdfDict, IndirectPdfDict, PdfObject
        next_pairs = []
        for id, value in pairs:
            if isinstance(value, PdfDict):
                d = {}
                pairs = []
                for key in value:
                    if isinstance(value[key], PdfDict):
                        d[key[1:]] = self.reserveObject('pdf resource element')
                        pairs.append((d[key[1:]], value[key]))
                    else:
                        d[key[1:]] = self.pdfobj2value(value[key])
                if value.stream is not None:
                    self.writeObject_stream(id, d, value.stream)
                else:
                    self.writeObject(id, d)
                next_pairs.append(pairs)
            else:
                if value.stream is not None:
                    self.writeObject_stream(
                        id, self.pdfobj2value(value), value.stream)
                else:
                    self.writeObject(id, self.pdfobj2value(value))

        for pairs in next_pairs:
            self.writePdfResources(pairs)

    def writePdfs(self):
        for pdf, name, ob in six.itervalues(self.pdfs):
            xobj = pdf.get_xobj()
            dd = {'Type': Name('XObject'), 'Subtype': Name('Form'),
                  'BBox': xobj.BBox, 'FormType': xobj.FormType,
                  'Filter': xobj.Filter, }
            if '/Resources' in xobj:
                resources, id_pairs = self.pdfResources(xobj.Resources)
                dd['Resources'] = resources
            self.beginStream(
                ob.id,
                self.reserveObject('length of pdf stream'),
                dd)
            self.currentstream.compressobj = None
            self.currentstream.write(np.fromstring(xobj.stream, np.uint8))
            self.endStream()
            if '/Resources' in xobj:
                self.writePdfResources(id_pairs)


class PdfFile_plus2(PdfFile_plus):
    def close(self):
        print('PdfFile plus2 is closing file')
        self.endStream()
        # Write out the various deferred objects
        self.writeFonts()
        self.writeObject(self.alphaStateObject,
                         dict([(val[0], val[1])
                               for val in six.itervalues(self.alphaStates)]))
        self.writeHatches()
        self.writeGouraudTriangles()
        xobjects = dict(x[1:] for x in six.itervalues(self._images))
        for tup in six.itervalues(self.markers):
            xobjects[tup[0]] = tup[1]
        for name, value in six.iteritems(self.multi_byte_charprocs):
            xobjects[name] = value
        for name, path, trans, ob, join, cap, padding, filled, stroked \
                in self.paths:
            xobjects[name] = ob
        for pdf, name, ob in six.itervalues(self.pdfs):
            xobjects[name] = ob
        self.writeObject(self.XObjectObject, xobjects)
        self.writeImages()
        self.writeMarkers()
        self.writePathCollectionTemplates()
        self.writePdfs()
        self.writeObject(self.pagesObject,
                         {'Type': Name('Pages'),
                          'Kids': self.pageList,
                          'Count': len(self.pageList)})
        self.writeInfoDict()

        # Finalize the file
        self.writeXref()
        self.writeTrailer()
        if self.passed_in_file_object:
            self.fh.flush()
        elif self.original_file_like is not None:
            self.original_file_like.write(self.fh.getvalue())
            self.fh.close()
        else:
            self.fh.close()


class RendererPdf_plus(RendererPdf):
    def draw_pdf(self, gc, x, y, scale, o):
        self.check_gc(gc)

        pdfob = self.file.pdfObject(o)
        self.file.output(Op.gsave, scale[0], 0, 0, scale[1], x, y,
                         Op.concat_matrix,
                         pdfob, Op.use_xobject, Op.grestore)


def pdffile_upgrade(pdffile):
    from ifigure.ifigure_config import isMPL2
    if isMPL2:
        cls = PdfFile_plus2
    else:
        cls = PdfFile_plus
    if pdffile.__class__ != cls:
        pdffile.__class__ = cls
        pdffile.pdfs = {}
        pdffile.nextPdf = 1


def mixedrenderer_upgrade(renderer):
    if renderer._vector_renderer.__class__ != RendererPdf_plus:
        renderer._vector_renderer.__class__ = RendererPdf_plus
        setattr(renderer, 'draw_pdf', getattr(
            renderer._vector_renderer, 'draw_pdf'))


class pdfobj(object):
    def __init__(self, xobj):
        self._xobj = xobj

    def get_xobj(self):
        return self._xobj


class FigureImageV(FigureImage):
    def draw(self, renderer, *args, **kwargs):
        #        return FigureImage.draw(self, renderer, *args, **kwargs)
        if (hasattr(renderer, '_vector_renderer') and
                isinstance(renderer._vector_renderer, RendererPdf)):
            pdffile_upgrade(renderer._vector_renderer.file)
            mixedrenderer_upgrade(renderer)
            gc = renderer.new_gc()
            import ifigure.utils.buildxobj as buildxobj
            o = buildxobj.CacheXObj()

            gc.set_alpha(self.get_alpha())

            ocwd = os.getcwd()
            _pdffile = os.path.join(self._figobj().owndir(), self._pdf_file)
            os.chdir(os.path.dirname(_pdffile))
            file = os.path.basename(_pdffile)
            obj = o.load(file)
            os.chdir(ocwd)
            self._obj = obj
            renderer.draw_pdf(gc, round(self.ox),
                              round(self.oy),
                              self._image_scale, pdfobj(obj))
            gc.restore()
        elif (hasattr(renderer, '_vector_renderer') and
              isinstance(renderer._vector_renderer, RendererPS)):
            gc = renderer.new_gc()
            ps_write0 = renderer._vector_renderer._pswriter.write
            _eps_file = os.path.join(self._figobj().owndir(), self._eps_file)

            def ps_write(txt):
                if unicode_file:
                    ps_write0(unicode(txt))
                else:
                    ps_write0(txt)

            if not hasattr(renderer._vector_renderer, '_eps_func_written'):
                ps_write(eps_funcs)
                renderer._vector_renderer._eps_func_written = True
            ps_write('BeginEPSF\n')
            ps_write(str(round(self.ox)) + ' ' +
                     str(round(self.oy)) + ' translate\n')
            ps_write(str(self._image_scale[0])+' ' +
                     str(self._image_scale[1]) + ' scale\n')
            ps_write(str(-self._eps_bbox[0]) + ' ' +
                     str(-self._eps_bbox[1]) + ' translate\n')
            ps_write('%%BeginDocument: "' +
                     os.path.basename(_eps_file) + '"\n')
            fid = open(_eps_file, 'r')
            for l in fid.readlines():
                ps_write(l)
            fid.close()
            ps_write('%%EndDocument\n')
            ps_write('EndEPSF\n')
            gc.restore()
        else:
            return FigureImage.draw(self, renderer, *args, **kwargs)


def create_figimagev(figure, X,
                     xo=0,
                     yo=0,
                     alpha=None,
                     norm=None,
                     cmap=None,
                     vmin=None,
                     vmax=None,
                     origin=None,
                     **kwargs):
    '''
    add figimagev object to figure. Made based on figure::figimage
    '''
    im = FigureImageV(figure, cmap, norm, xo, yo, origin, **kwargs)
    im.set_array(X)
    im.set_alpha(alpha)
    if norm is None:
        im.set_clim(vmin, vmax)
#   figure.images.append(im)
    figure.artists.append(im)
    return im


class FigEPS(FigBox):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._image_size = (-1, -1)
            obj._image_scale_str = ('100', '100')
            obj._eps_bbox = (-1, -1, -1, -1)
            obj._image = None
            obj._image_artists = []
            obj._image_alpha = 1.0
            obj._image_scale = (1, 1)
            obj._keep_aspect = True
            # 0 (left or bottom) 1 (center) 2 (right, top)
            obj._anchor_mode = (0, 0)
            obj._resize_mode = True  # True  use normalized coords.
            # False evaulate new size from the eps bbox
            return obj

        p = ArgsParser()
        p.add_opt('org_epsfile', None, 'str')
        p.add_opt('xy', [0.2, 0.2], 'numbers')

        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('xy', 'org_epsfile'):
            obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args, **kywds):
        if len(args) > 0:
            file = args[0]
        else:
            file = ''
#        file = '/Users/shiraiwa/piscope_src/example/images/cmod_logo_official_better_color.eps'

        self.setvar('org_epsfile', file)
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
            kywds['xy'] = self.getvar('xy')
        super(FigEPS, self).__init__(**kywds)

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'eps.png')
        return [idx1]

    @classmethod
    def property_in_file(self):
        return []

    @classmethod
    def get_namebase(self):
        return 'eps'

    @classmethod
    def property_in_palette(self):
        return ["eps"], [["epsscale", "anchor", "alpha_2"]]

#    def set_parent(self, parent):
#        super(FigEPS, self).set_parent(parent)

    def generate_artist(self):

        if self.getvar('epsfile') is None:
            self.import_file()

        container = self.get_figpage()._artists[0]
#        lp=self.getp("loaded_property")
        super(FigEPS, self).generate_artist()

        self.set_frameart(self.getp('frameart'))

    def make_newartist(self):
        self.check_loaded_gp_data()
        if self._image_size == (-1, -1):
            dx = self._eps_bbox[2] - self._eps_bbox[0]
            dy = self._eps_bbox[3] - self._eps_bbox[1]
            x1d, y1d = self.get_gp(0).get_device_point()
            self.get_gp(1).set_device_point(x1d+dx, y1d+dy)
            self._image_scale_str = ('100', '100')

        try:
            self.call_convert()
        except:
            traceback.print_exc()
            a = super(FigEPS, self).make_newartist()
            a.set_alpha(0)
            return a

        a = super(FigEPS, self).make_newartist()
        a.set_alpha(0)

        x1d, y1d = self.get_gp(0).get_device_point()
        if self._image is not None:
            container = self.get_figpage()._artists[0]
            b = create_figimagev(container, self._image, x1d,
                                 y1d, alpha=self._image_alpha)
            self._image_artists = [b]
            b._image_scale = self._image_scale
            b._figobj = weakref.ref(self)
            b._pdf_file = self.getvar('epsfile')[:-3]+'pdf'
            b._eps_file = self.getvar('epsfile')
            b._eps_bbox = self._eps_bbox
            b._is_frameart = self.getp('frameart')

        z = self.getp('zorder')
        for im in self._image_artists:
            im.set_zorder(z)
        return a

    def del_artist(self, artist=None, delall=None):
        for a in self._image_artists:
            #             a.figure.images.remove(a)
            a.figure.artists.remove(a)
        self._image_artists = []

        super(FigEPS, self).del_artist(artist=artist, delall=delall)

    def set_zorder(self, z1, a=None):
        super(FigEPS, self).set_zorder(z1, a)
        z = self.getp('zorder')
        for im in self._image_artists:
            im.set_zorder(z)

    def import_file(self):
        file = self.getvar('org_epsfile')
        self.mk_owndir()
        wdir = self.owndir()
        bname = os.path.basename(file)
        shutil.copyfile(file, os.path.join(wdir, bname))
        self.setvar('epsfile', bname)
        self._eps_bbox = self.get_eps_bbox()

        pname = bname[:-3]+'pdf'
        app = self.get_root_parent().app
        ps2pdf = app.helper.setting['ps2pdf']
        o = sp.Popen([ps2pdf, "-dEPSCrop",
                      os.path.join(wdir, bname),
                      os.path.join(wdir, pname)],
                     stdout=sp.PIPE, stderr=sp.STDOUT).communicate()[0]
        print(o)

    def scale_artist(self, scale, action=True):
        h = super(FigEPS, self).scale_artist(scale, action=action)
        if action:
            pass
        else:
            pass
        return h

    def set_alpha(self, value, a):
        self._image_alpha = value
        for a in self._image_artists:
            a.set_alpha(value)

    def get_alpha(self, a):
        return self._image_alpha

    def set_anchor(self, value, a):
        self._anchor_mode = value

    def get_anchor(self, value):
        return self._anchor_mode

    def set_epsscale(self, value, a):

        self._keep_aspect = value[0]
        self._resize_mode = value[1]
        self._image_scale_str = (value[2], value[3])

        ox = self._eps_bbox[2] - self._eps_bbox[0]
        oy = self._eps_bbox[3] - self._eps_bbox[1]

        dx = int(ox*float(value[2])/100.)
        dy = int(oy*float(value[3])/100.)
        x1d, y1d = self.get_gp(0).get_device_point()
        self.get_gp(1).set_device_point(x1d+dx, y1d+dy)
        self.refresh_artist()

    def get_epsscale(self, a):
        ox = self._eps_bbox[2] - self._eps_bbox[0]
        oy = self._eps_bbox[3] - self._eps_bbox[1]
        ix = self._image.shape[1]
        iy = self._image.shape[0]

        dx = int(ox*float(self._image_scale_str[0])/100.)
        dy = int(oy*float(self._image_scale_str[1])/100.)
        if (ix != dx or iy != dy):
            return (self._keep_aspect,
                    self._resize_mode,
                    float(ix)/ox*100.,
                    float(iy)/oy*100.,)
        else:
            return (self._keep_aspect, self._resize_mode,
                    self._image_scale_str[0],
                    self._image_scale_str[1])

    def call_convert(self):
        x1d, y1d = self.get_gp(0).get_device_point()
        x2d, y2d = self.get_gp(1).get_device_point()
        ox = self._eps_bbox[2] - self._eps_bbox[0]
        oy = self._eps_bbox[3] - self._eps_bbox[1]

        if not self._resize_mode:
            '''
            this mode use geometric mean 
            '''
            r = (float(self._image_scale_str[1]) /
                 float(self._image_scale_str[0]))

            new_size1 = (abs(x1d - x2d), abs(x1d - x2d)*r*oy/ox)
            new_size2 = (abs(y1d - y2d)*ox/oy/r, abs(y1d - y2d))
            new_size = ((new_size1[0]*new_size2[0])**0.5,
                        (new_size1[1]*new_size2[1])**0.5)
            x1d, x2d = calc_newpos_from_anchor(
                x1d, x2d, new_size[0], self._anchor_mode[0])
            y1d, y2d = calc_newpos_from_anchor(
                y1d, y2d, new_size[1], self._anchor_mode[1])
            self.get_gp(0).set_device_point(x1d, y1d)
            self.get_gp(1).set_device_point(x2d, y2d)
        else:
            new_size = (abs(x1d - x2d), abs(y1d-y2d))

        new_size = [int(x) for x in new_size]
        if (new_size[0] == self._image_size[0] and
            new_size[1] == self._image_size[1] and
                self._image is not None):
            return

        wdir = self.owndir()
        des = os.path.join(wdir, 'tmp.png')
        src = os.path.join(wdir, self.getvar('epsfile'))

        params = []
        params += ['-resize', str(int(new_size[0])) +
                   'x'+str(int(new_size[1]))+'!']
        # print 'calling convert',  params

        app = self.get_root_parent().app
        convert = app.helper.setting['convert']
        sp.check_call([convert] + params + [src, des])
        self._image = mpimage.imread(des)
        self._image_size = new_size
        self._image_scale = (new_size[0]/ox, new_size[1]/oy)

    def get_eps_bbox(self, src=None):
        if src is None:
            wdir = self.owndir()
            src = os.path.join(wdir, self.getvar('epsfile'))

        app = self.get_root_parent().app
        gs = app.helper.setting['gs']
        o = sp.Popen(["gs", "-dNOPAUSE", "-dBATCH",
                      "-q", "-sDEVICE=bbox", src], stdout=sp.PIPE, stderr=sp.STDOUT).communicate()[0]
        arr = o.split(' ')
        arr[4] = arr[4].split('\n')[0]
        return float(arr[1]), float(arr[2]), float(arr[3]), float(arr[4])

    def save_data2(self, data):
        names = ('_image_size',
                 '_eps_bbox',
                 '_image_alpha',
                 '_image_scale_str',
                 '_keep_aspect',
                 '_anchor_mode',
                 '_resize_mode')

        var = {name: getattr(self, name) for name in names}
        data['FigEPS'] = (1, var)
        data = super(FigEPS, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigEPS']

        super(FigEPS, self).load_data2(data)
        for key in d[1]:
            setattr(self, key, d[1][key])

    def get_artists_for_frameart(self):
        '''
        for FigEPS
          _artists is box for picker
          _image_aritsts is actual art

          both should be labeled as frameart
        '''
        return self._image_artists+self._artists
