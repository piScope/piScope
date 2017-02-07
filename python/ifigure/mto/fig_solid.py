from ifigure.mto.fig_obj import FigObj, mask_negative
from ifigure.mto.axis_user import XUser, YUser, ZUser, CUser
from ifigure.widgets.canvas.file_structure import *
import ifigure, os
import ifigure.widgets.canvas.custom_picker as cpicker
import numpy as np
import weakref, logging
from ifigure.utils.cbook import ProcessKeywords, LoadImageFile, isdynamic
from matplotlib.tri import Triangulation
from ifigure.matplotlib_mod.triplot_mod  import triplot
from ifigure.utils.args_parser import ArgsParser
from matplotlib import cm
from matplotlib.colors import Normalize, colorConverter, LightSource
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ColorConverter
cc = ColorConverter()
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('FigSolid')

#from mpl_toolkits.axes_grid1.inset_locator import inset_axes

class FigSolid(FigObj, XUser, YUser, ZUser, CUser):
    def __new__(cls, *args, **kywds):
        def set_hidden_vars(obj):
            obj._objs=[]  ## for debug....     
            obj._data_extent=None
            return obj

        if kywds.has_key('src'):
            obj = FigObj.__new__(cls, *args, **kywds)
            obj = set_hidden_vars(obj)
            return obj

        p = ArgsParser()
        p.add_var('v', ['iter|nonstr', 'dynamic']) 


        #p.add_key('cmap', None)
        #p.add_key('shade', False)
        if 'cz' in kywds and kywds['cz']:
            def_alpha = None
            def_ec = None
            def_fc = None
            def_lw = 0.0
        else:
            def_alpha = 1.0
            def_ec = (0, 0, 0, 1)
            def_fc = (0, 0, 1, 1)
            def_lw = 1.0

        # this prevent from passing linewidth to aritist
        def_lw = kywds.pop('linewidth', def_lw)
        p.add_key('linewidths', def_lw)

        p.add_key('alpha', def_alpha)
        p.add_key('facecolor', def_fc)
        p.add_key('edgecolor', def_ec)
        p.add_key('normals', None)
        p.add_key('cz', False, 'bool')
        p.add_key('cdata', None)
       # p.add_key('edgecolor', None)

        v, kywds,d, flag = p.process(*args, **kywds)
        if not flag: 
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)

        for name in v.keys(): obj.setvar(name, v[name])
        obj.setvar("kywds", kywds)
        return obj

    def __init__(self, *args,  **kywds):
        XUser.__init__(self)
        YUser.__init__(self)
        ZUser.__init__(self)
        CUser.__init__(self)

        args = []
        if not kywds.has_key('src'):
            kywds = self.getvar("kywds")
        super(FigSolid,self).__init__(*args, **kywds)

    @classmethod
    def get_namebase(self):
        return 'solid'
    @classmethod  
    def property_in_palette(self):
        return ["facecolor_2", "edgecolor_2", "linewidthz","alpha_2"]
    @classmethod
    def attr_in_file(self):
        return ([ "alpha", "facecolor", 
                 "edgecolor", "linewidth"] +
                super(FigSolid, self).attr_in_file())
    @classmethod  
    def load_classimage(self):
       from ifigure.ifigure_config import icondir as path
       idx1=LoadImageFile(path, 'surf.png')
       return [idx1]

    def set_parent(self, parent):
        XUser.unset_ax(self)
        YUser.unset_ay(self)
        ZUser.unset_az(self)
        CUser.unset_ac(self)
        super(FigSolid, self).set_parent(parent)
        XUser.get_xaxisparam(self)
        YUser.get_yaxisparam(self)
        ZUser.get_zaxisparam(self)
        CUser.get_caxisparam(self)
    def args2var(self):
        ret = self._args2var()
        return ret

    def _args2var(self):
        
        names0 = self.attr_in_file()
        names  = ["v"]
        use_np = [True]
        names  = names + names0
        use_np = use_np + [False]*len(names0)

        values = self.put_args2var(names, use_np)
        v = values[0]
        # need to do it manually since name is slightly different
        self.setp('linewidth', self.getvar('linewidths'))
        if v is None: return False
        self.setp('v', v)

        return True
    def generate_artist(self, coarse=False):
        if (self.isempty() is False
            and not coarse): return

        axes = self.get_figaxes()
        if not axes.get_3d(): return

        container=self.get_container()

        v = self._eval_v()
        ### use_var should be false if evaluation is
        ### okey.
        if self.getp('use_var'): return

        lp = self.getp("loaded_property")
        if lp is not None: self.delp("loaded_property")

        norms = self.getvar('normals')
        if norms is None:
            norms = []
            for xyz in v:
                if xyz.shape[0] > 2:
                    p0, p1, p2 = [xyz[k,:3] for k in range(3)]
                    n1 = np.cross(p0-p1, p1-p2)
                    d = np.sqrt(np.sum(n1**2))
                else:
                    d = 0
                if d == 0:
                    norms.append([0,0,1]*xyz.shape[0])
                else:
                    norms.extend([-n1/d]*xyz.shape[0])
            norms = np.hstack(norms).astype(np.float32).reshape(-1,3)
            
        kywds = self._var["kywds"].copy()
        kywds['alpha'] = self.getp('alpha') if self.getp('alpha') is not None else 1
        
        fc = self.getp('facecolor')
        if isinstance(fc, str): fc = cc.to_rgba(fc)
        if fc is None: fc = [0,0,0,0]        
        else:
            fc = list(fc)
            if self.getp('alpha') is not None: fc[3]=self.getp('alpha')
        ec = self.getp('edgecolor')
        if isinstance(ec, str): ec = cc.to_rgba(ec)
        if ec is None: ec = [0,0,0,0]
        else:
            ec = list(ec)
            if self.getp('alpha') is not None: ec[3]=self.getp('alpha')
        
        nv = len(v[:, :, 2].flatten())
        kywds['gl_3dpath'] = [v[:, :, 0].flatten(),
                              v[:, :, 1].flatten(),
                              v[:, :, 2].flatten(),
                              norms, np.arange(nv).reshape(v.shape[0], v.shape[1])]
        if self.getvar('cz'):
            kywds['cz'] = self.getvar('cz')
            if self.getvar('cdata') is not None:
                cdata = self.getvar('cdata')            
                kywds['facecolordata'] = np.mean(cdata, -1).real
        else:
            kywds['facecolor'] = (fc,)
        kywds['edgecolor'] = (ec,)
        kywds['linewidths'] =  0.0 if self.getp('linewidth') is None else self.getp('linewidth')
        self._artists = [container.plot_solid(v[:,:,:3], **kywds)]

        for artist in self._artists:
            artist.do_stencil_test = False
            artist.figobj=self
            artist.figobj_hl=[]
            artist.set_zorder(self.getp('zorder'))
            self._objs.append(weakref.ref(artist))
            if self.getvar('cz'):
                cax = self.get_caxisparam()
                if cax is None: dprint1('Error: cax is None')
                cax.set_crangeparam_to_artist(artist)            
            
    def switch_scale(self, level='fine'):
        return

    def del_artist(self, artist=None, delall=False):
        #if (len(self._artists) == 1 and
        #    self._artists[0] != self._fine_artist):
        #   self.switch_scale(level='fine')

        artistlist = self._artists
        self.store_loaded_property()

        if len(artistlist) != 0:
          self.highlight_artist(False, artistlist)
          container=self.get_container()
          for a in artistlist:
             try:           
                 a.remove()
             except:
                 dprint1("remove failed")

        #self._fine_artist = None
        super(FigSolid, self).del_artist(artistlist)

    def get_mappable(self):
        if self.getvar('cz'):
            return [a for a in self._artists if isinstance(a, ScalarMappable)]
        else:
            return []
        
    def highlight_artist(self, val, artist=None):
        from ifigure.matplotlib_mod.art3d_gl import Poly3DCollectionGL
        figure=self.get_figpage()._artists[0]
        ax = self.get_figaxes()
        if artist is None:
           alist=self._artists
        else:
           alist=artist

        if val == True:
           if self._parent is None: return
           container = self.get_container()
           if container is None: return

           de = self.get_data_extent()
           x=(de[0], de[1],de[1],de[0],de[0])
           y=(de[2], de[2],de[3],de[3],de[2])

           facecolor='k'
           if isinstance(alist[0], Poly3DCollectionGL):
               hl = alist[0].add_hl_mask()
           else:
               hl = []

           for item in hl:
              alist[0].figobj_hl.append(item)

        else:
            for a in alist:
              if len(a.figobj_hl) == 0: continue
              for hl in a.figobj_hl:
                 hl.remove()
              a.figobj_hl = []
        
    def set_cmap(self, value, a):
        a.set_cmap(cm.get_cmap(value))
        self.setp('cmap', value)
        ca = self.get_caxisparam()
        ca.set_cmap(value)
        if self.has_cbar():
            ca.update_cb()           

    def get_cmap(self, a=None):
        ca = self.get_caxisparam()
        return ca.cmap
    def set_alpha(self, value, a):
        a.set_alpha(value)
        self.setp('alpha', value)
#        self.setp('cmap', value)
#        self.set_cmap(self.get_cmap(a), a)

    def get_alpha(self, a=None):
        return self.getp('alpha')

    def set_edgecolor(self, value, a):
        self.setp('edgecolor', value)
        a.set_edgecolor([value])

    def get_edgecolor(self, a=None):
        return self.getp('edgecolor')

    def set_facecolor(self, value, a):
        if self.getvar('cz'): return
        if value == 'disabled': return
        if isinstance(value, str): value = cc.to_rgba(value)
        alpha = self.getp('alpha')
        if alpha is None: alpha = 1.0
        value = (value[0], value[1], value[2], alpha)
        self.setp('facecolor', value)
        a.set_facecolor([value])

    def get_facecolor(self, a=None):
        if self.getvar('cz'):
            return 'disabled'
        return self.getp('facecolor')

    def set_linewidth(self, value, a = None):
        self.setp('linewidth', value)
        if len(self._artists) > 0 :
            if a is None:
                a = self._artists[0]
            a.set_linewidth(value)

    def get_linewidth(self, a=None):
        return self.getp('linewidth')

    def set_shade(self, value, a):
        self.setp('shade', value)

    def get_shade(self, a=None):
        return self.getp('shade')

#
#   def hit_test
#
    def picker_a(self, artist, evt):
        axes = artist.get_axes()
        if axes is None: return False, {} 
        hit, extra = artist.contains(evt)

        if hit:
            return True, {}
        else:
            return False, {}

    def get_data_extent(self):
        if self._data_extent is not None:
            return self._data_extent
        x, y, z = self._eval_xyz() 
        self._data_extent=[np.min(x), np.max(x),
                           np.min(y), np.max(y),
                           np.min(z), np.max(z)]
        return self._data_extent

    def get_xrange(self, xrange=[None,None], scale = 'linear'):
        x, y, z = self._eval_xyz()
        if x is None: return xrange
        if scale == 'log': x = mask_negative(x)
        return self._update_range(xrange, [np.nanmin(x), np.nanmax(x)])

    def get_yrange(self, yrange=[None,None], xrange=[None, None], scale = 'linear'):
        x, y, z = self._eval_xyz()
        if y is None: return yrange
        if scale == 'log': y = mask_negative(y)
        return self._update_range(yrange, (np.nanmin(y), np.nanmax(y)))

    def get_zrange(self, zrange=[None,None], 
                         xrange=[None,None], 
                         yrange=[None,None],
                         scale = 'linear'):
        x, y, z = self._eval_xyz()
        if z is None: return zrange
        zrange = self._update_range(zrange,
                                    (np.nanmin(z), np.nanmax(z)))

        return zrange
    
    def get_crange(self, crange=[None,None], 
                         xrange=[None,None], 
                         yrange=[None,None],
                         scale = 'linear'):
        cdata = self.getvar('cdata')
        cz = self.getvar('cz')
        if not cz: return crange
        if cdata is None:
            x, y, z = self._eval_xyz()
            crange = self._update_range(crange,
                             (np.nanmin(z), np.nanmax(z)))

        else:
            if np.iscomplexobj(cdata):
                tmp  = np.max(np.abs(cdata))
                crange = self._update_range(crange,
                                    (-tmp, tmp))

            else:
                crange = self._update_range(crange,
                                    (np.nanmin(cdata), np.nanmax(cdata)))

        return crange

    @classmethod  
    def _saveload_names(self):
        return {'v',}

    def save_data2(self, data=None):
        def check(obj, name):
            if not isinstance(obj.getp(name), np.ndarray): return False
            if not isinstance(obj.getvar(name), np.ndarray): return False
            return obj.getp(name) is obj.getvar(name)
    
        if data is None: data = {}
        names = self._saveload_names()
        var = {name:check(self, name) for name in names}
        for name in names:
            if not var[name]: var[name+'data'] = self.getp(name)

        data['FigSolid'] = (1, var)
        data = super(FigSolid, self).save_data2(data)
        return data

    def load_data2(self, data):
        d = data['FigSolid']
        super(FigSolid, self).load_data2(data)
        var = d[1]

        names = self._saveload_names()
        for name in names:
            if var[name]:
                 self.setp(name, 
                          self.getvar(name))
            else:
                 self.setp(name, var[name+'data'])
    def _eval_xyz(self):
        v = self._eval_v()
        if v is None: return None, None, None
        return v[:,:,0], v[:,:,1], v[:,:,2]

    def _eval_v(self):
        if self.getp('use_var'): 
            success = self.handle_use_var()
            if not success: 
                return None
        return self.getp("v")

    def get_export_val(self, a):
        val =  {"vertices":  self.getp("v"),}
        if self.getvar('cz'):
            val['cdata'] = self.getvar("cdata")
        return val

        

