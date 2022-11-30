from __future__ import print_function
#
#   fig_image
#
#  History:
#          12.06.10  Added Highlight
#          12.06.11  Added custom picker
#          12.09.04  Added image interpolation
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************

from ifigure.ifigure_config import isMPL2
from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, CUser, ZUser
from ifigure.widgets.canvas.file_structure import *
import ifigure
import os
import sys
import numpy as np
import ifigure.utils.cbook as cbook
import ifigure.widgets.canvas.custom_picker as cpicker
from scipy.interpolate import griddata, bisplrep, bisplev, interp2d
from ifigure.utils.cbook import ProcessKeywords
from ifigure.utils.triangulation_wrapper import tri_args
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox
from ifigure.utils.args_parser import ArgsParser
from matplotlib.colors import Colormap

#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigImage')

default_kargs = {'use_tri': False,
                 #                 'interp' : 'linear',
                 'interp': 'nearest',
                 'shading': 'flat',
                 'alpha':  None}
#                 'cmap'   :  'jet'}


class FigImage(FigObj, XUser, YUser, ZUser, CUser):
    """
    image : show image 

    image(z)
    image(x, y, z)
    """
    default_rasterized = True

    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            if not hasattr(obj, '_tri'):
                obj._tri = None  # this can go away!?
            for key in default_kargs:
                if not obj.hasp(key):
                    obj.setp(key, default_kargs[key])
                if not obj.hasvar(key):
                    obj.setvar(key, default_kargs[key])
            return obj

        if 'src' in kywds:
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_opt('x', None, ['numbers|nonstr', 'dynamic'])
        p.add_opt('y', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('z', ['numbers|nonstr', 'dynamic'])
        p.set_pair("x", "y")  # x and y should be given
        # together
        p.set_ndconvert("x", "y", "z")
        p.set_squeeze_minimum_1D("x", "y", "z")
        p.set_default_list(default_kargs)
        p.add_key2(('use_tri', 'interp', 'shading', 'alpha'))
        p.add_key('cmap', 'jet')

        v, kywds, d, flag = p.process(*args, **kywds)

        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in ('x', 'y', 'z', 'use_tri', 'interp', 'shading', 'alpha'):
            obj.setvar(name, v[name])
        if v['cmap'] is not None:
            if isinstance(v['cmap'], Colormap):
                v['cmap'] = v['cmap'].name
            kywds['cmap'] = v['cmap']
            del v['cmap']
        obj.setvar("kywds", kywds)

        return obj

    def __init__(self, *args, **kywds):
        self._data_extent = None
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)
        CUser.__init__(self)

        self._pick_pos = None
        self._cb_added = False
        args = []
        if 'src' not in kywds:
            kywds = self.getvar("kywds")
        super(FigImage, self).__init__(**kywds)

    @classmethod
    def isFigImage(self):
        return True

    @classmethod
    def can_have_child(self, child=None):
        return False

    @classmethod
    def get_namebase(self):
        return 'image'

    @classmethod
    def property_in_file(self):
        return (["array", "extent"] +
                super(FigImage, self).property_in_file())

    @classmethod
    def property_in_palette(self):
        return (['image'], [["image_interp", "alpha_2", "caxis", "noclip3d"], ])

    @classmethod  # define _attr values to be saved
    def attr_in_file(self):
        return (["interp", "shading", "alpha"] +
                super(FigImage, self).attr_in_file())

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'image.png')
        return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)
        super(FigImage, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)
        CUser.get_caxisparam(self)

    def args2var(self):
        ret = self._args2var()
        if ret:
            if 'cmap' in self.getvar("kywds"):
                cax = self.get_caxisparam()
                cax.set_cmap(self.getvar('kywds')['cmap'])
        return ret

    def _args2var(self):
        names0 = self.attr_in_file()
        names = ["x", "y", "z"] + names0
        use_np = [True]*3 + [False]*len(names0)
        values = self.put_args2var(names,
                                   use_np)
        x = values[0]
        y = values[1]
        z = values[2]
        if y is None and x is None and z.ndim == 2:
            y = np.arange((z.shape)[-2]).astype(z.dtype)
            self.setp("y", y)
            x = np.arange((z.shape)[-1]).astype(z.dtype)
            self.setp("x", x)
        if x is None:
            return False
        if y is None:
            return False
        if self._tri is not None:
            if self._tri.shape[0] == z.size:
                self.setp("x", x)
                self.setp("y", y)
                self.setp("z", z)
                return True
        if (x.size*y.size != z.size and
                not (x.size == z.size and y.size == z.size)):
            self.setp("x", None)
            self.setp("y", None)
            self.setp("z", None)
            return False
        return True

    def generate_artist(self):
        # this method generate artist
        # if artist does exist, update artist
        # based on the information specifically
        # managed by fig_obj tree. Any property
        # internally managed by matplotlib
        # does not change
        container = self.get_container()
        if container is None:
            return
#           if self.get_figaxes().get_3d(): return
        if self.isempty() is False:
            return
        x, y, z = self._eval_xyz()
        if z is None:
            return

        lp = self.getp("loaded_property")
        aspect = container.get_aspect()
        cax = self.get_caxisparam()
        if cax is None:
            dprint1('Error: cax is None')
            return
        crange = cax.range

        if lp is None or len(lp) == 0:
            if (self._tri is not None and
                    self._tri.shape[0] == z.size):
                pass

            else:
                if (x.size*y.size != z.size and
                        not (x.size == z.size and y.size == z.size)):
                    print('FigImage: array size is wrong')
                    return

            if not self.getvar('use_tri'):
                if self.get_figaxes().get_3d():
                    xp, yp, zp = x, y, z
                    extent = (np.min(x), np.max(x),
                              np.min(y), np.max(y), )
                else:
                    xp, yp, zp = self.interp_image(x, y, z)
                    extent = (np.min(xp), np.max(xp),
                              np.min(yp), np.max(yp), )
                args = []
                kywds = self._var["kywds"].copy()
                kywds['alpha'] = self.getp('alpha')
    #              args.append(np.flipud(zp))

                if cax.scale == 'linear':
                    args.append(zp)
                    kywds["vmin"] = crange[0]
                    kywds["vmax"] = crange[1]
                else:
                    # args.append(np.log10(zp))
                    args.append(zp)
                    kywds["vmin"] = np.log10(max((crange[0], 1e-16)))
                    kywds["vmax"] = np.log10(max((crange[1], 1e-16)))

                kywds["aspect"] = aspect
                kywds["origin"] = 'lower'
                if self.getp("interp") == 'linear':
                    kywds["interpolation"] = 'bilinear'
                elif self.getp("interp") == 'cubic':
                    kywds["interpolation"] = 'bicubic'
                else:
                    kywds["interpolation"] = self.getp("interp")

                self.set_artist(container.imshow(*args,
                                                 # picker=cpicker.Picker,
                                                 extent=extent,  **kywds))
                cax.set_crangeparam_to_artist(self._artists[0])

                setattr(self._artists[0].get_array(), '_xyp', (xp, yp))
            else:
                #print('drawing tri image')
                if x.size*y.size == z.size:
                    x, y = np.meshgrid(x, y)

                args, self._tri = tri_args(x, y, self._tri)
                kywds = self._var["kywds"]
                kywds['alpha'] = self.getp('alpha')
                if cax.scale == 'linear':
                    # args.append(z.flatten().astype(float))
                    args.append(np.real(z.flatten()))
                    kywds["clim"] = (crange[0], crange[1])
                else:
                    # args.append(np.log10(z))
                    # args.append(z.flatten().astype(float))
                    args.append(np.real(z.flatten()))
                    kywds["clim"] = [np.log10(max((crange[0], 1e-16))),
                                     np.log10(max((crange[1], 1e-16)))]
                kywds['shading'] = self.getp('shading')
                kywds['mask'] = self.getp('mask')

                self.set_artist(container.tripcolor(*args,
                                                    **kywds))
                cax.set_crangeparam_to_artist(self._artists[0])
            self._data_extent = [np.min(x), np.max(x),
                                 np.min(y), np.max(y)]
        else:
            if self.getvar('use_tri'):
                #print('redrawing tri image')
                x, y, z = self.getp(('x', 'y', 'z'))
                args, self._tri = tri_args(x, y, self._tri)

                args.append(z.flatten().astype(float))
                # astype(float) is patch work to open past files..

                #kywds = self._var["kywds"]
                kywds = lp[0]
                kywds['shading'] = self.getp('shading')
                kywds['mask'] = self.getp('mask')
                kywds['alpha'] = self.getp('alpha')
                keys = ['alpha', 'cmap', 'zorder']
                for k in keys:
                    if k in lp[0]:
                        kywds[k] = lp[0][k]
#                  print lp
#                  kywds["clim"]=lp[0]["clim"]
                del(kywds['array'])
                self.set_artist(container.tripcolor(*args,
                                                    **kywds))
                cax.set_crangeparam_to_artist(self._artists[0])

            else:
                x, y, z = self.getp(('x', 'y', 'z'))
                xp, yp, zp = self.interp_image(x, y, z)
                args = []
                kywds = {}
                if 'im_center' in self._var["kywds"]:
                    kywds['im_center'] = self._var["kywds"]['im_center']
                if 'im_axes' in self._var["kywds"]:
                    kywds['im_axes'] = self._var["kywds"]['im_axes']

                kywds['alpha'] = self.getp('alpha')
                if self.getp("interp") == 'linear':
                    kywds["interpolation"] = 'bilinear'
                elif self.getp("interp") == 'cubic':
                    kywds["interpolation"] = 'bicubic'
                else:
                    kywds["interpolation"] = self.getp("interp")

                if cax.scale == 'linear':
                    args.append(zp)
                    kywds["vmin"] = crange[0]
                    kywds["vmax"] = crange[1]
                else:
                    args.append(zp)
                    kywds["vmin"] = np.log10(max((crange[0], 1e-16)))
                    kywds["vmax"] = np.log10(max((crange[1], 1e-16)))
                keys = ['alpha', 'cmap', 'zorder']
                for k in keys:
                    if k in lp[0]:
                        kywds[k] = lp[0][k]
                self.set_artist(container.imshow(*args,
                                                 extent=lp[0]["extent"], aspect=aspect,
                                                 origin='lower', **kywds))
                cax.set_crangeparam_to_artist(self._artists[0])
                setattr(self._artists[0].get_array(), '_xyp', (xp, yp))
        self.delp("loaded_property")

        self.set_rasterized()
        # this is to resize image when window is resized...
        if not self._cb_added:
            fig_page = self.get_figpage()
            fig_page.add_resize_cb(self)
            self._cb_added = True

#           for artist in self._artists:
#               artist.figobj=self
#               artist.figobj_hl=[]
#               artist.set_zorder(self.getp('zorder'))
    def onResize(self, evt):
        self.set_interp(self.get_interp(self._artists[0]), self._artists[0])
        self.set_bmp_update(False)

    def del_artist(self, artist=None, delall=False):
        if delall:
            artistlist = self._artists
        else:
            artistlist = self._artists

        self.store_loaded_property()

#        self.highlight_artist(False, artistlist)
        for a in artistlist:
            a.remove()

        super(FigImage, self).del_artist(artistlist)

    def get_mappable(self):
        return [a for a in self._artists if isinstance(a, ScalarMappable)]

    def highlight_artist(self, val, artist=None):
        #        print val, artist
        figure = self.get_figpage()._artists[0]
        ax = self.get_figaxes()
        if artist is None:
            alist = self._artists
        else:
            alist = artist
        if val == True:
            container = self.get_container()
            if container is None:
                return

            de = self.get_data_extent()
            from ifigure.matplotlib_mod.art3d_gl import AxesImageGL
            if isinstance(alist[0], AxesImageGL):
                hl = alist[0].add_hl_mask()
                for item in hl:
                    alist[0].figobj_hl.append(item)

#               hl = alist[0].make_hl_artist(container)
#               rect_alpha = 0.0
            else:
                x = [de[0], de[1], de[1], de[0], de[0]]
                y = [de[2], de[2], de[3], de[3], de[2]]
                hl = container.plot(x, y, marker='s',
                                    color='k', linestyle='None',
                                    markerfacecolor='None',
                                    markeredgewidth=0.5,
                                    scalex=False, scaley=False)
                rect_alpha = 0.3

                hlp = Rectangle((de[0], de[2]),
                                de[1]-de[0],
                                de[3]-de[2],
                                alpha=rect_alpha, facecolor='k',
                                figure=figure,
                                transform=container.transData)
                if ax is not None:
                    x0, y0 = ax._artists[0].transAxes.transform((0, 0))
                    x1, y1 = ax._artists[0].transAxes.transform((1, 1))
                    bbox = Bbox([[x0, y0], [x1, y1]])
                    hlp.set_clip_box(bbox)
                    hlp.set_clip_on(True)

                figure.patches.append(hlp)
                for item in (hl[0], hlp):
                    alist[0].figobj_hl.append(item)
        else:
            for a in alist:
                if len(a.figobj_hl) != 0:
                    a.figobj_hl[0].remove()
                    figure.patches.remove(a.figobj_hl[1])
                a.figobj_hl = []
#
#   Setter/Getter
#

    def set_cmap(self, value, a):
        ca = self.get_caxisparam()
        ca.set_cmap(value)
        ca.set_crangeparam_to_artist(a)
        if self.has_cbar():
            ca.update_cb()

    def get_cmap(self, a=None):
        ca = self.get_caxisparam()
        return ca.cmap
#
#   HitTest
#

    def get_artist_extent(self, a):
        '''
        retrun the extent of artist in device 
        coordinate

        AxesImage object does not have get_window_extent
        '''
        de = self.get_data_extent()
        x1, y1 = self._artists[0].axes.transData.transform((de[0], de[2]))
        x2, y2 = self._artists[0].axes.transData.transform((de[1], de[3]))
        return [x1, x2, y1, y2]

    def picker_a(self, artist, evt):
        from ifigure.matplotlib_mod.art3d_gl import AxesImageGL
        if (isinstance(artist, AxesImageGL) or
                self.getvar('use_tri')):
            hit, extra = artist.contains(evt)
            if hit:
                self._pick_pos = [evt.xdata, evt.ydata]
                return True,  {'child_artist': artist}
            else:
                return False, {}

        # (an old routine when somehow the above did not work)
        # for mpl1.5, normal image plot needs to do this.
        ax = self.get_figaxes()
        hit, extra = ax._artists[0].contains(evt)
        if not hit:
            return False, {}

        de = self.get_data_extent()
        if (evt.xdata > de[0] and
            evt.xdata < de[1] and
            evt.ydata > de[2] and
                evt.ydata < de[3]):
            self._pick_pos = [evt.xdata, evt.ydata]
            return True, {'child_artist': artist}
        self._pick_pos = None
        return False, {}

    def picker_a0(self, artist, evt):
        hit, extra = self.picker_a(artist, evt)
        if hit:
            return hit, extra, 'area', 3
        else:
            return False, {}, None, 0

#
#  Popup in ProjViewer
#
    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImag
        ac = self.get_caxisparam()
        if ac is None:
            return super(FigImage, self).tree_viewer_menu()
        if ac.cbar_shown():
            m = [('Hide ColorBar', self.onHideCB, None), ]
        else:
            m = [('Show ColorBar', self.onShowCB, None), ]
        return m+super(FigImage, self).tree_viewer_menu()

    def onShowCB(self, e):
        new_cb = False
        if self.has_cbar():
            new_cb = True
        self.show_cbar()
        if new_cb:
            ifigure.events.SendPVAddFigobj(self.get_figaxes())
        ifigure.events.SendPVDrawRequest(self, w=None)
        e.Skip()

    def onHideCB(self, e):
        self.hide_cbar()
        ifigure.events.SendPVDeleteFigobj(self.get_figaxes())
        ifigure.events.SendPVDrawRequest(self, w=None)
        e.Skip()
#
#  Popup in Canvas
#

    def canvas_menu(self):
        ac = self.get_caxisparam()
        if ac is None:
            return super(FigImage, self).tree_viewer_menu()
        if ac.cbar_shown():
            m = [('Hide ColorBar', self.onHideCB1, None), ]
        else:
            m = [('Show ColorBar', self.onShowCB1, None), ]
        menus = [("Show Slice",  self.onSlice, None)] + m + \
            super(FigImage, self).canvas_menu()
        return menus

    def get_slice(self, xin, yin, a=None):
        if a is None:
            a = self._artists[0]
        array = a.get_array()
        axes = a.axes

        x0, y0 = axes.transAxes.transform([0, 0])
        x1, y1 = axes.transAxes.transform([1, 1])

        ix = float(xin-x0)/float(x1-x0)*array.shape[1]
        iy = float(yin-y0)/float(y1-y0)*array.shape[0]

        try:
            zp1 = array[:, int(ix)]
            zp2 = array[int(iy), :]
        except:
            return None, None

#        atrans = axes.transData.transform
#        idtrans = axes.transAxes.inverted().transform
#        print xin, yin
#        print atrans((xin, yin))
#        print idtrans(atrans((xin, yin)))
#        xn, yn = idtrans(atrans((xin, yin)))
#        print array.shape

#        zp1 = array[:, long(xn*array.shape[1])]
#        zp2 = array[long(yn*array.shape[0]), :]

        xp, yp = getattr(array, '_xyp')
        return (yp, np.array(zp1)), (xp, np.array(zp2))

    def onSlice(self, event):
        from ifigure.interactive import figure, plot, nsec, isec, update, title, xlabel, ylabel
        if event.mpl_xydata[0] is None:
            return

        for a in self._artists:
            axes = a.axes
            if axes is None:
                return
            data1, data2 = self.get_slice(event.mpl_xy[0],
                                          event.mpl_xy[1], a)
            if data1 is None:
                continue
            if data2 is None:
                continue
            figure()
            nsec(2)
            ou = update()
            isec(0)
            plot(data1[0], data1[1])
            title('y slice : y = '+str(event.mpl_xydata[1]))
            xlabel('x')
            isec(1)
            plot(data2[0], data2[1])
            title('x slice : x = '+str(event.mpl_xydata[0]))
            xlabel('y')
            update(ou)

    def get_export_val(self, a):
        x, y, z = self._eval_xyz()
        # althouth internally it is called zdata, export will name it cdata,
        # which is more appropriate.
        return {"cdata": z,
                "xdata": x,
                "ydata": y}

    def interp_image(self, x, y, z):

        if isMPL2:
            return x, y, z
        else:
            axes = self.get_container()

            atrans = axes.transAxes.transform
            idtrans = axes.transData.inverted().transform
            p0, p1 = atrans([(0, 0), (1, 1)])
            dx = np.floor(p1[0]-p0[0])+2
            dy = np.floor(p1[1]-p0[1])+2
            xp = idtrans(
                np.transpose(
                    np.vstack((np.floor(p0[0])+np.arange(int(dx)),
                               np.linspace(p0[0], p1[0], dx)))))[:, 0]
            yp = idtrans(
                np.transpose(
                    np.vstack((np.floor(p0[1])-1+np.zeros(int(dy)),
                               np.linspace(p0[1], p1[1], dy)))))[:, 1]

            # eliminate points outside the data range
            #xp = np.array([tmp for tmp in xp if (tmp > np.min(x) and tmp < np.max(x))])
            #yp = np.array([tmp for tmp in yp if (tmp > np.min(y) and tmp < np.max(y))])

            interp = self.getp("interp")
            from scipy.interpolate import RegularGridInterpolator
            if ((x.size*y.size == z.size and interp == 'nearest') or
                    (x.size*y.size == z.size and interp == 'linear')):
                f = RegularGridInterpolator((y, x), z, method=interp,
                                            bounds_error=False, fill_value=np.nan)
                XP, YP = np.meshgrid(xp, yp)
                p1 = np.transpose(np.vstack((YP.flatten(), XP.flatten())))
                zp = f(p1)
                zp = zp.reshape((len(yp), len(xp))).astype(float)
            elif (x.size*y.size != z.size or interp == 'nearest' or
                  np.any(np.isnan(z))):
                if interp == 'quintic':
                    interp = 'cubic'
                X, Y = np.meshgrid(x, y)
                p1 = np.transpose(np.vstack((X.flatten(), Y.flatten())))
                XP, YP = np.meshgrid(xp, yp)
                interp = self.getp("interp")
                # print 'griddata', interp
                zp = griddata(p1, z.flatten(),
                              (XP.flatten(), YP.flatten()),
                              method=str(interp))
                zp = zp.reshape((len(yp), len(xp))).astype(float)

            else:
                f = interp2d(x, y, z, kind=interp)
                zp = f(xp, yp)
    #           print(zp)
    #        if interp == 'nearest':
            # this hide the outside of image when even 'nearest' is
            # used
            zp[:, xp < np.min(x)] = np.nan
            zp[:, xp > np.max(x)] = np.nan
            zp[yp < np.min(y), :] = np.nan
            zp[yp > np.max(y), :] = np.nan

            return xp, yp, zp

    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent

        x, y, z = self._eval_xyz()
        if z is None:
            return self._data_extent
        if x is None or y is None:
            #  x and y may be None if it failed to
            #  evaluable expression
            if z.ndim != 2:
                return self._data_extent
            if x is None:
                x = [0, z.shape[1]]
            if y is None:
                y = [0, z.shape[0]]
            self._data_extent = [min(x), max(x), min(y), max(y)]
        else:
            self._data_extent = [np.min(x), np.max(x),
                                 np.min(y), np.max(y)]

        return self._data_extent

#
#   range
#
    def _get_3d_placement(self):
        if 'im_center' in self._var["kywds"]:
            im_center = np.array(self._var["kywds"]['im_center'])
        else:
            im_center = np.array([0, 0, 0])
        if 'im_axes' in self._var["kywds"]:
            ax1 = np.array(self._var["kywds"]['im_axes'][0])
            ax2 = np.array(self._var["kywds"]['im_axes'][1])
        else:
            ax1 = np.array([1, 0, 0])
            ax2 = np.array([1, 0, 0])

        return im_center, ax1, ax2

    def get_xrange(self, xrange=[None, None], scale='linear'):
        x, y, z = self._eval_xyz()
        if x is None:
            return xrange
        if not self.get_figaxes().get_3d():
            if scale == 'log':
                x = mask_negative(x)
            return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])
        else:
            im_center, ax1, ax2 = self._get_3d_placement()
            data = np.hstack(
                [im_center[0] + ax1[0]*x, im_center[0] + ax2[0]*y])
            xrange = self._update_range(xrange,
                                        (np.nanmin(data), np.nanmax(data)))
            return xrange

    def get_yrange(self, yrange=[None, None],
                   xrange=[None, None], scale='linear'):
        #        de = self.get_data_extent()
        x, y, z = self._eval_xyz()
        if x is None:
            return yrange
        if y is None:
            return yrange
        if not self.get_figaxes().get_3d():
            if scale == 'log':
                y = mask_negative(y)
            return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))
        else:
            im_center, ax1, ax2 = self._get_3d_placement()
            data = np.hstack(
                [im_center[1] + ax1[1]*x, im_center[1] + ax2[1]*y])
            yrange = self._update_range(yrange,
                                        (np.nanmin(data), np.nanmax(data)))
            return yrange

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if not self.get_figaxes().get_3d():
            return zrange

        x, y, z = self._eval_xyz()
        im_center, ax1, ax2 = self._get_3d_placement()

        data = np.hstack([im_center[2] + ax1[2]*x, im_center[2] + ax2[2]*y])
        zrange = self._update_range(zrange,
                                    (np.nanmin(data), np.nanmax(data)))

        return zrange

    def get_crange(self, crange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):

        x, y, z = self._eval_xyz()

        if np.iscomplexobj(z):
            z = z.real

        if self.get_figaxes().get_3d():
            crange = self._update_range(crange,
                                        (np.amin(z), np.amax(z)))
            return crange

        if (xrange[0] is not None and
            xrange[1] is not None and
            yrange[0] is not None and
                yrange[1] is not None):
            if x.size*y.size == z.size:
                idx1 = np.where((y >= yrange[0]) & (y <= yrange[1]))[0]
                idx2 = np.where((x >= xrange[0]) & (x <= xrange[1]))[0]
                if (len(idx1) == 0 or len(idx2) == 0):
                    if (crange[0] is None and
                            crange[1] is None):
                        # this is for safety maybe not necessary
                        if scale == 'log':
                            z = mask_negative(z)
                        crange = self._update_range(crange,
                                                    (np.min(z), np.max(z)))

                else:
                    zt = z[idx1, :]
                    zt = zt[:, idx2]
                    if scale == 'log':
                        zt = mask_negative(zt)
                    crange = self._update_range(crange,
                                                (np.nanmin(zt), np.nanmax(zt)))

            elif x.size == z.size and y.size == z.size:
                idx1 = np.where((y.flatten() >= yrange[0]) & (y.flatten() <= yrange[1]) &
                                (x.flatten() >= xrange[0]) & (x.flatten() <= xrange[1]))[0]
                if (len(idx1) == 0):
                    if scale == 'log':
                        zt = mask_negative(zt)
                    crange = self._update_range(crange,
                                                (min(zt), max(zt)))
                else:
                    zt = z.flatten()[idx1]
                    if scale == 'log':
                        zt = mask_negative(zt)
                    crange = self._update_range(crange,
                                                (np.amin(zt), np.amax(zt)))
            else:
                # if len(_tri) == len(z), it comes here
                crange = self._update_range(crange,
                                            (np.nanmin(z), np.nanmax(z)))

        return crange

    def set_alpha(self, value, a):
        a.set_alpha(value)
        a.set_array(a.get_array())
        self.setp('alpha', value)

    def get_alpha(self, a):
        return a.get_alpha()

    def set_interp(self, value, a):
        self.setp('interp', value)
        if value == 'cubic':
            avalue = 'bicubic'
        elif value == 'linear':
            avalue = 'bilinear'
        else:
            avalue = value

        x, y, z = self.getp(("x", "y", "z"))

        if (x.size*y.size != z.size and
                not (x.size == z.size and y.size == z.size)):
            print('FigImage: array size is wrong')
            return
        if self.get_figaxes().get_3d():
            xp, yp, zp = x, y, z
            a.set_gl_interp(value)
        else:
            xp, yp, zp = self.interp_image(x, y, z)
            a.set_array(zp)
            setattr(a.get_array(), '_xyp', (xp, yp))
        a.set_interpolation(avalue)

    def get_interp(self, a):
        return self.getp('interp')
    # needs to be implemented...

    def _update_range_gl(self, range, idx):
        for a in self._artists:
            if hasattr(a, 'get_gl_data_extent'):
                tmprange = a.get_gl_data_extent()[idx]
            range = self._update_range(range,
                                       tmprange)
        return range

    def get_zrange(self, zrange=[None, None],
                   xrange=[None, None],
                   yrange=[None, None],
                   scale='linear'):
        if self.get_figaxes().get_3d():
            zrange = self._update_range_gl(zrange, 2)
        return zrange

    def handle_axes_change(self, evt=None):
        if len(self._artists) != 0:
            a1 = self._artists[0]
            flag = True
            self.del_artist(delall=True)
            self.delp('loaded_property')
            self.generate_artist()
        else:
            flag = False
        if flag:
            a2 = self._artists[0]
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray):
                return False
            if not isinstance(obj.getvar(name), np.ndarray):
                return False
            return obj.getp(name) is obj.getvar(name)

        if data is None:
            data = {}
        var = {'x': check(self, 'x'),
               'y': check(self, 'y'),
               'z': check(self, 'z')}

        if not var["x"]:
            if self._save_mode == 0:
                var["xdata"] = self.getp("x")
            else:
                var["xdata"] = np.array([0, 1])
        if not var["y"]:
            if self._save_mode == 0:
                var["ydata"] = self.getp("y")
            else:
                var["ydata"] = np.array([0, 1])
        if not var["z"]:
            if self._save_mode == 0:
                var["zdata"] = self.getp("z")
            else:
                var["zdata"] = np.zeros([2, 2])

#        dprint2('save_data2', var)
        data['FigImage'] = (1, var)
        data = super(FigImage, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigImage']
        super(FigImage, self).load_data2(data)
        dprint2('load_data2', d[1])
        var = d[1]
        names = ["x", "y", "z"]
        for name in names:
            if var[name]:
                self.setp(name,
                          self.getvar(name))
            else:
                self.setp(name, var[name+'data'])

    def prepare_compact_savemode(self):
        var_bk = self._var.copy()
        self._var['z'] = np.zeros([2, 2])
        self._var['x'] = np.array([0, 1])
        self._var['y'] = np.array([0, 1])
        return var_bk

#    def refresh_artist_data(self):
#        print 'image refresh'
#        FigObj.refresh_artist_data(self)
#        print self._artists

    def _eval_xyz(self):
        if self.getp('use_var'):
            success = self.handle_use_var()
            if not success:
                return None, None, None
        return self.getp(("x", "y", "z"))
