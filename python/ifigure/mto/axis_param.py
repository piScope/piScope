import weakref
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LogNorm, Normalize, Colormap, SymLogNorm
import ifigure
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
import matplotlib.ticker as mticker
from ifigure.utils.cbook import isiterable
from ifigure.ifigure_config import isMPL33
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('AxisParam')

def _to_float(value):
    if hasattr(value, 'real'):
        return value.real
    return float(value)


def get_cmap(name, param=256):
    from matplotlib import colormaps
    return colormaps[name].resampled(param)

class Memberholder(object):
    def __init__(self):
        self._member = []
        self._ax_idx = []

    def add_ax_idx(self, v):
        if not v in self._ax_idx:
            self._ax_idx.append(v)

    def rm_ax_idx(self, v):
        self._ax_idx = [x for x in self._ax_idx if x != v]

    def get_member(self):
        return self._member

    def walk_member(self):
        for m in self._member:
            if m() is not None:
                yield(m())

    def add_member(self, obj):
        for r in self._member:
            if r() is obj:
                return
        self._member.append(weakref.ref(obj, self._memberdead))

    def num_member(self):
        return len(self._member)

    def rm_member(self, obj):
        for r in self._member:
            if r() is obj:
                self._member.remove(r)
                return

    def _memberdead(self, ref):
        self._member = [a for a in self._member
                        if a() is not None]


class AxisRangeParam(Memberholder):
    def __init__(self):
        Memberholder.__init__(self)
        self.name = ''
        self.base = 10
        self.auto = True
        self.range = [0, 1]
        self.symloglin = 1.0
        self.symloglinscale = 1.0
        self.scale = 'linear'
        self.cmap = 'jet'
        self.ticks = None     # None: auto, number, or exact value
        self.mode = (False, False, False)  # int, #symmetric, #margin

    def make_rangeparam_action(self, artist, value):
        action = UndoRedoFigobjMethod(artist,
                                      'axrangeparam', value)
        action.set_extrainfo(self.name)
        return action

    def make_rangeparam_action0(self, artist, value):
        '''
        this one does call handle_axes_change
        '''
        dprint1('make_rangeparam_action0 is obsolete and should not be used')

        def f(obj=artist.figobj, name=value[0]):
            obj.call_handle_axes_change(name)
        action = UndoRedoFigobjMethod(artist,
                                      'axrangeparam', value,
                                      finish_action=f)
        action.set_extrainfo(self.name)
        return action

    def get_rangeparam(self):
        v = [str(self.base),
             self.auto,
             self.range[:],
             self.scale,
             self.symloglin,
             self.symloglinscale,
             self.mode[0], self.mode[1], self.mode[2]]
        return v

    def set_rangeparam(self, value):
        if len(value) <= 7:
            value = [x for x in value]
            value.append(False)
        self.base = float(value[0])
        self.auto = value[1]
        self.mode = (value[6], value[7], value[8])
        self.symloglin = value[4]
        self.symloglinscale = value[5]
        self.scale = value[3]

        self.range = [_to_float(value[2][0]), _to_float(value[2][1])]

    def set_artist_rangeparam(self,
                              set_scale=None,
                              set_auto=None,
                              set_lim=None,
                              set_ticks=None):

        set_auto(False)
        suffix = self.name
        if self.scale == 'log':
            if isMPL33:
                kargs = {'base': self.base}
            else:
                kargs = {'base' + suffix: self.base}
        elif self.scale == 'symlog':
            if isMPL33:
                kargs = {'base': self.base,
                         'linthresh': self.symloglin,
                         'linscale': self.symloglinscale}
            else:
                kargs = {'base' + suffix: self.base,
                         'linthresh' + suffix: self.symloglin,
                         'linscale' + suffix: self.symloglinscale}
        else:
            kargs = {}

        set_scale(self.scale, **kargs)

        r = (_to_float(self.range[0]), _to_float(self.range[1]))
        set_lim(r)

    def make_save_data(self, ax):
        names = ("name", "base", "auto", "range", "scale", "cmap",
                 "mode", "ticks", "symloglin", "symloglinscale")
        d = {name: getattr(self, name) for name in names}
        m = []
        for plot in self._member:
            #           m.append(ax.get_relative_path(plot()))
            m.append(ax.get_td_path(plot())[1:])
        d["member"] = m
        d["_ax_idx"] = self._ax_idx
        return d

    def import_data(self, ax, data):
        names = ("name", "base", "auto", "range", "scale", "cmap",
                 "mode", "_ax_idx", "ticks", "symloglin",
                 "symloglinscale")
        for name in names:
            if name in data:
                setattr(self, name, data[name])
        self._loaded_member = data["member"]


class AxisVisualParam(object):
    def __init__(self):
        self.minortickmode = 'off'
        self.grid = 'off'
        self.lcolor = 'black'  # label color
        self.lsize = 'default'     # label size
        self.tcolor = 'black'      # tick color
        self.otcolor = 'black'     # offset text color
        self.otsize = 'default'    # offset text size
        # text, color, font-family, weight, style, size
        self.labelinfo = ['', 'black', 'default',
                          'default', 'default', 'default']
        self.tick_position = 'left'
        self.tick_both = True
        self.box = True
        self.format = 'default'

    def set_tickparam(self, a, adir, figaxes):
        figpage = figaxes.get_figpage()
        if self.lsize == 'default':
            if figpage is not None:
                size = figpage.getp("ticklabel_size")
            else:
                size = 12
        else:
            size = self.lsize
        if self.otsize == 'default':
            if figpage is not None:
                otsize = figpage.getp("ticklabel_size")
            else:
                otsize = 12
        else:
            otsize = self.otsize
        a.tick_params(axis=adir, labelsize=size)
        a.tick_params(axis=adir, labelcolor=self.lcolor)
        a.tick_params(axis=adir, color=self.tcolor)
        # print self.otcolor
        if adir == 'x':
            a.xaxis.offsetText.set_color(self.otcolor)
            a.xaxis.offsetText.set_size(otsize)
        elif adir == 'y':
            a.yaxis.offsetText.set_color(self.otcolor)
            a.yaxis.offsetText.set_size(otsize)
        self.set_box(a)

    def set_box(self, a):
        name_pairs = {'right': 'left',
                      'top': 'bottom',
                      'left': 'right',
                      'bottom': 'top'}
        if isinstance(self.tick_position, dict):
            pass
            # custom spine setting does not use this
        else:
            if self.tick_position in name_pairs:
                if self.box:
                    name = name_pairs[self.tick_position]
                    a.spines[name].set_color('k')
                else:
                    name = name_pairs[self.tick_position]
                    a.spines[name].set_color('none')

    def _set_label(self, txt):
        txt.set_text(self.labelinfo[0])
        txt.set_color(self.labelinfo[1])
        if self.labelinfo[2] != 'default':
            txt.set_family(self.labelinfo[2])
        if self.labelinfo[3] != 'default':
            txt.set_weight(self.labelinfo[3])
        if self.labelinfo[4] != 'default':
            txt.set_style(self.labelinfo[4])
        if self.labelinfo[5] == 'default':
            # put a tentative number
            # this size will be overwritten when
            # before AxesMod::draw is called from
            # FigureMod
            txt.set_size(10)
        else:
            txt.set_size(float(self.labelinfo[5]))

    def _set_ticker(self, a):
        try:
            if not isiterable(self.ticks):
                if self.scale == 'linear':
                    a.set_major_locator(mticker.AutoLocator())
                elif self.scale == 'log':
                    a.set_major_locator(mticker.LogLocator(self.base))
                elif self.scale == 'symlog':
                    from matplotlib.scale import SymmetricalLogScale
                    if isMPL33:
                        scale = SymmetricalLogScale(a,
                                                    base=self.base,
                                                    linthresh=self.symloglin,
                                                    linscale=self.symloglinscale)
                    else:
                        scale = SymmetricalLogScale(a,
                                                    basex=self.base,
                                                    linthreshx=self.symloglin,
                                                    linscalex=self.symloglinscale)
                    a.set_major_locator(
                        mticker.SymmetricalLogLocator(scale.get_transform()))
#                    scale.set_default_locators_and_formatters(a)

                else:
                    a.set_major_locator(mticker.AutoLocator())
                #a.get_axes().locator_params(self.name[0], nbins = 10)
                if self.ticks is not None:
                    value = self.ticks
                else:
                    #figpage = a.get_axes().figobj.get_figpage()
                    figpage = a.axes.figobj.get_figpage()
                    if self.name[0] == 'x':
                        value = figpage.getp('nticks')[0]
                    elif self.name[0] == 'y':
                        value = figpage.getp('nticks')[1]
                    elif self.name[0] == 'z':
                        value = figpage.getp('nticks')[2]
                    else:
                        pass
                try:
                    # this works onlyfor MaxNLocator
                    #a.get_axes().locator_params(self.name[0], nbins = value)
                    a.axes.locator_params(self.name[0], nbins=value)
                except BaseException:
                    # for Symlog and LogLocator
                    a.get_major_locator().numticks = value
            else:
                a.set_ticks(self.ticks)

            if self.format == 'default':
                if self.scale == 'linear':
                    a.set_major_formatter(mticker.ScalarFormatter())
                elif self.scale == 'log':
                    a.set_major_formatter(
                        mticker.LogFormatterMathtext(self.base))
                elif self.scale == 'symlog':
                    a.set_major_formatter(
                        mticker.LogFormatterMathtext(self.base))
                else:
                    a.set_major_formatter(mticker.ScalarFormatter())
            elif self.format == 'scalar':
                a.set_major_formatter(mticker.ScalarFormatter())
            elif self.format == 'scalar(mathtext)':
                a.set_major_formatter(mticker.ScalarFormatter(
                    useOffset=True, useMathText=True))
                a.get_major_formatter().get_offset()
            elif self.format == 'log':
                a.set_major_formatter(mticker.LogFormatter(self.base))
            elif self.format == 'log(mathtext)':
                a.set_major_formatter(mticker.LogFormatterMathtext(self.base))
            elif self.format == 'log(exp)':
                a.set_major_formatter(mticker.LogFormatterExponent(self.base))
            elif self.format == 'none':
                a.set_major_formatter(mticker.NullFormatter())
            else:
                a.set_major_formatter(mticker.FormatStrFormatter(self.format))
        except BaseException:
            import traceback
            traceback.print_exc()

    def make_save_data(self, ax):
        names = ("minortickmode", "grid", "lcolor", "lsize", "tcolor",
                 "labelinfo", "tick_position", "tick_both", "otcolor",
                 "format", "ticks", "box", "otsize")
        return {name: getattr(self, name) for name in names}

    def import_data(self, ax, data):
        names = ("minortickmode", "grid", "lcolor", "lsize", "tcolor",
                 "labelinfo", "tick_position", "tick_both", "otcolor",
                 "format", "ticks", "box", "otsize")
        for name in names:
            if name in data:
                setattr(self, name, data[name])

        # for backward compatibility
        if not "otcolor" in data:
            setattr(self, "otcolor", data["lcolor"])
        # for backward compatibility
        if not "otsize" in data:
            setattr(self, "otsize", data["lsize"])

    def _apply_custom_spine_setting(self, spine, value):
        spine.set_position((value['loc. ref'],
                            float(value['loc. value'])))
        spine.set_alpha(value['alpha'])
        spine.set_facecolor(value['face'])
        spine.set_edgecolor(value['edge'])
        spine.set_linewidth(value['width'])
        spine.set_linestyle(value['style'])

    def _get_custom_spine_setting(self, spine):
        value = {}
        if spine.get_position() == 'zero':
            value['loc. ref'] = 'data'
            value['loc. value'] = '0'
        elif spine.get_position() == 'center':
            value['loc. ref'] = 'axes'
            value['loc. value'] = '0.5'
        else:
            value['loc. ref'] = spine.get_position()[0]
            value['loc. value'] = str(spine.get_position()[1])
        value['alpha'] = spine.get_alpha()
        value['face'] = spine.get_facecolor()
        value['edge'] = spine.get_edgecolor()
        value['width'] = spine.get_linewidth()
        value['style'] = spine.get_linestyle()
        return value


class AxisParam(AxisRangeParam, AxisVisualParam):
    def __init__(self, name):
        AxisRangeParam.__init__(self)
        AxisVisualParam.__init__(self)
        self.name = name

    def make_save_data(self, ax):
        return {"AxisRangeParam": AxisRangeParam.make_save_data(self, ax),
                "AxisVisualParam": AxisVisualParam.make_save_data(self, ax)}

    def import_data(self, ax, data):
        AxisRangeParam.import_data(self, ax, data["AxisRangeParam"])
        AxisVisualParam.import_data(self, ax, data["AxisVisualParam"])
        return self


class AxisXParam(AxisParam):
    def __init__(self, *args, **kargs):
        AxisParam.__init__(self, *args, **kargs)
        self.tick_position = 'bottom'

    def set_tickparam(self, a, fa):
        AxisVisualParam.set_tickparam(self, a, 'x', fa)
        self.set_artist_tickposition(a)
        if self.tick_both:
            a.xaxis.set_ticks_position('both')

    def get_artist_tickposition(self, a):
        if isinstance(self.tick_position, dict):
            return self.tick_position
        else:
            value = {}
            def_set = ['top', 'bottom']
            for x, name in zip(def_set, ['spine1', 'spine2']):
                value[name] = self._get_custom_spine_setting(a.spines[x])

            value['label'] = self.tick_position
            return value

    def set_artist_tickposition(self, a):
        value = self.tick_position
        def_set = ['top', 'bottom']
        if isinstance(self.tick_position, dict):
            a.xaxis.set_ticks_position(value['label'])
            for x, name in zip(def_set, ['spine1', 'spine2']):
                self._apply_custom_spine_setting(a.spines[x], value[name])
        else:
            if value in def_set:
                a.xaxis.set_ticks_position(value)
                for x in def_set:
                    a.spines[x].set_position(('outward', 0))
            elif value == 'zero':
                a.xaxis.set_ticks_position(def_set[0])
                for x in def_set:
                    a.spines[x].set_position('zero')
            elif value == 'center':
                a.xaxis.set_ticks_position(def_set[0])
                for x in def_set:
                    a.spines[x].set_position('center')
            else:
                pass

    def set_label(self, a):
        txt = a.get_xaxis().label
        self._set_label(txt)

    def get_label_from_mpl(self, a):
        return a.get_xaxis().label.get_text()

    def set_ticks(self, a):
        xaxis = a.get_xaxis()
        self._set_ticker(xaxis)

    def get_mpl_range(self, a):
        return a.get_xlim()

    def set_artist_rangeparam(self, a):

        set_scale = a.set_xscale
        set_auto = a.set_autoscalex_on
        set_lim = a.set_xlim
        AxisRangeParam.set_artist_rangeparam(self,
                                             set_scale=set_scale,
                                             set_auto=set_auto,
                                             set_lim=set_lim)
        self.set_ticks(a)


class AxisYParam(AxisParam):
    def __init__(self, *args, **kargs):
        AxisParam.__init__(self, *args, **kargs)
        self.tick_position = 'left'

    def set_tickparam(self, a, fa):
        AxisVisualParam.set_tickparam(self, a, 'y', fa)
        self.set_artist_tickposition(a)
        if self.tick_both:
            a.yaxis.set_ticks_position('both')

    def get_artist_tickposition(self, a):
        if isinstance(self.tick_position, dict):
            return self.tick_position
        else:
            value = {}
            def_set = ['left', 'right']
            for x, name in zip(def_set, ['spine1', 'spine2']):
                value[name] = self._get_custom_spine_setting(a.spines[x])

            value['label'] = self.tick_position
            return value

    def set_artist_tickposition(self, a):
        value = self.tick_position
        def_set = ['left', 'right']
        if isinstance(self.tick_position, dict):
            a.yaxis.set_ticks_position(value['label'])
            for x, name in zip(def_set, ['spine1', 'spine2']):
                self._apply_custom_spine_setting(a.spines[x], value[name])
        else:
            if value in def_set:
                a.yaxis.set_ticks_position(value)
                for x in def_set:
                    a.spines[x].set_position(('outward', 0))
            elif value == 'zero':
                a.yaxis.set_ticks_position(def_set[0])
                for x in def_set:
                    a.spines[x].set_position('zero')
            elif value == 'center':
                a.yaxis.set_ticks_position(def_set[0])
                for x in def_set:
                    a.spines[x].set_position('center')
            else:
                pass

    def set_label(self, a):
        txt = a.get_yaxis().label
        self._set_label(txt)

    def get_label_from_mpl(self, a):
        return a.get_yaxis().label.get_text()

    def set_ticks(self, a):
        yaxis = a.get_yaxis()
        self._set_ticker(yaxis)

    def get_mpl_range(self, a):
        return a.get_ylim()

    def set_artist_rangeparam(self, a):
        set_scale = a.set_yscale
        set_auto = a.set_autoscaley_on
        set_lim = a.set_ylim
        AxisRangeParam.set_artist_rangeparam(self,
                                             set_scale=set_scale,
                                             set_auto=set_auto,
                                             set_lim=set_lim)
        self.set_ticks(a)


class AxisZParam(AxisParam):
    def __init__(self, *args, **kargs):
        AxisParam.__init__(self, *args, **kargs)
        self.tick_position = 'default'  # not used??

    def set_artist_axisparam(self, a):
        pass

    def set_tickparam(self, a, fa):
        AxisVisualParam.set_tickparam(self, a, 'z', fa)

    def set_label(self, a):
        txt = a.get_zaxis().label
        self._set_label(txt)

    def get_label_from_mpl(self, a):
        return a.get_zaxis().label.get_text()

    def set_ticks(self, a):
        zaxis = a.get_zaxis()
        self._set_ticker(zaxis)

    def get_mpl_range(self, a):
        return a.get_zlim()

    def set_artist_rangeparam(self, a):
        if not hasattr(a, 'set_zlim'):
            return

        set_scale = a.set_zscale

        def func(value, ax=a):
            ax.autoscale(value, axis='z')
        set_auto = func
        set_auto = a.set_autoscalez_on
        set_lim = a.set_zlim
        AxisRangeParam.set_artist_rangeparam(self,
                                             set_scale=set_scale,
                                             set_auto=set_auto,
                                             set_lim=set_lim)
        self.set_ticks(a)


class AxisCParam(AxisParam):
    def __init__(self, name):
        AxisParam.__init__(self, name)
        self.tick_position = 'default'  # not used??
        self._cb = None
        self._cm = None
        self.clip = ((False, 'white'), (False, 'white'))

    def set_tickparam(self, a, fa):
        pass

    def set_label(self, a):
        pass

    def get_label_from_mpl(self, a):
        return self.labelinfo[0]

    def set_ticks(self, a):
        pass

    def get_mpl_range(self, a):
        if isinstalce(a, ScalarMappable):
            return a.get_clim()
        else:
            return (0, 1)

    def set_artist_rangeparam(self, a):
        '''
        a is axes object
        need to find all Scalarmappable
        '''

        figobjs = [a2.figobj for a2 in a.get_children()
                   if hasattr(a2, 'figobj')]
        for figobj in set(figobjs):
            for a2 in figobj.get_mappable():
                self.set_crangeparam_to_artist(a2)

    def set_crangeparam_to_artist(self, a2, check=True):
        '''
        a2 is artist
        '''
        if check:
            for m in self._member:
                if a2 in m().get_mappable():
                    break
            else:
                return

        if self._cm is None:
            self._cm = get_cmap(self.cmap, 256)
        cm = self._cm

        if self.clip[0][0]:
            cm.set_under(self.clip[0][1])
        else:
            cm.set_under(cm(0))
        if self.clip[1][0]:
            cm.set_over(self.clip[1][1])
        else:
            cm.set_over(cm(cm.N - 1))
        a2.set_cmap(cm)

        if self.scale == 'linear':
            a2.set_norm(Normalize(self.range[0],
                                  self.range[1]))
            a2.set_clim(self.range)
        elif self.scale == 'symlog':
            a2.set_norm(SymLogNorm(self.symloglin,
                                   vmin=self.range[0],
                                   vmax=self.range[1],
                                   base=10)
                        )
            a2.set_clim(self.range)
        else:
            a2.set_norm(LogNorm(self.range[0],
                                self.range[1]))
            a2.set_clim(self.range)

    def show_cbar(self, figaxes,
                  offset=0.0,
                  position=(0.9, 0.1),
                  size=(0.05, 0.8),
                  lsize='default',
                        lcolor='black',
                  olsize='default',
                        olcolor='black',
                  direction='v'):

        if self._cb is None:
            ichild = figaxes.add_colorbar()
            cb = figaxes.get_child(ichild)
            anchor = cb.getp("inset_anchor")
            anchor = (position[0] + offset, position[1])
            cb.setp("inset_anchor", anchor)
            cb.setp("cdir", direction)
            cb.setp("inset_w", size[0])
            cb.setp("inset_h", size[1])
            cb.set_caxis_param(self)
            cb.realize()
            self._cb = weakref.ref(cb, self._cb_dead)

            if direction == 'v':
                name = 'y'
            else:
                name = 'x'

            ap = cb.get_axis_param(name)
            artist = cb.get_axes_artist_by_name(name)[0]
            ap.lsize = lsize
            ap.otsize = olsize
            ap.lcolor = lcolor
            ap.otcolor = olcolor
            ap.set_tickparam(artist, cb)
            # set cb params here...

    def hide_cbar(self):
        if self._cb is None:
            return
        if self._cb() is None:
            return
        cb = self._cb()
        figaxes = cb.get_parent()
        cb.destroy()
        self._cb = None
        ifigure.events.SendChangedEvent(figaxes, w=None)

    def has_cbar(self):
        if self._cb is None:
            return False
        if self._cb() is None:
            return False
        return True

    def cbar_shown(self):
        if self._cb is not None:
            if self._cb() is not None:
                return True
            else:
                self._cb = None
                return False
        return False

    def _cb_dead(self, v):
        self._cb = None

    def rm_member(self, obj):
        super(AxisCParam, self).rm_member(obj)
        if len(self._member) == 0:
            if self._cb is None:
                return
            if self._cb() is not None:
                figaxes = self._cb().get_parent()
                self._cb().destroy()
                ifigure.events.SendChangedEvent(figaxes, w=None)
            self._cb = None

    def set_cmap(self, cmap):
        self.cmap = cmap
        self._cm = get_cmap(self.cmap, 256)

    def get_cmap(self):
        return self.cmap

    def update_cb(self):
        if self._cb is None:
            return
        if self._cb() is None:
            return
        self._cb().update_cbar_image()
        self._cb().set_bmp_update(False)

    def make_save_data(self, ax):
        d = AxisParam.make_save_data(self, ax)
        d["clip"] = self.clip
        return d

    def import_data(self, ax, data):
        AxisParam.import_data(self, ax, data)
        self.clip = data["clip"]
        return self

#    def add_colorbar(self, name=None, *args, **kywds):
