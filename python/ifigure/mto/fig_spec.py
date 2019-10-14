import traceback
import numpy
import ifigure
from ifigure.mto.fig_image import FigImage
import matplotlib.mlab as mlab
from ifigure.utils.args_parser import ArgsParser
from ifigure.mto.fig_obj import FigObj
import numpy as np

default_kargs = {'interp': 'linear',
                 'shading': 'flat',
                 'alpha':  1.0,
                 'cmap':  'jet',
                 'NFFT':  256,
                 'noverlap': 128,
                 'sides': 'onesided',
                 'window': 'hanning',
                 'detrend': 'none',
                 'pad_to': 'none'}

windows = {'hanning': mlab.window_hanning,
           'none': mlab.window_none,
           'blackman': numpy.blackman,
           'hamming': numpy.hamming,
           'bartlett': numpy.bartlett}

detrends = {'none': mlab.detrend_none,
            'mean': mlab.detrend_mean,
            'linear': mlab.detrend_linear}


class FigSpec(FigImage):
    '''
    FigSpec(v)
    FigSpec(t, v)
    '''
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
        p.add_opt('t', None, ['numbers|nonstr', 'dynamic'])
        p.add_var('v', ['numbers|nonstr', 'dynamic'])

        p.set_ndconvert("v", "t")
        p.set_squeeze_minimum_1D("v", "t")
        p.set_default_list(default_kargs)
        p.add_key2(('interp', 'shading', 'alpha', 'window', 'NFFT',
                    'noverlap', 'sides', 'detrend', 'pad_to'))
        p.add_key2('cmap', 'str')
        v, kywds, d, flag = p.process(*args, **kywds)
        if not flag:
            raise ValueError('Failed when processing argument')

        obj = FigObj.__new__(cls, *args, **kywds)
        obj = set_hidden_vars(obj)
        for name in ('v', 't', 'interp', 'shading', 'alpha',):
            obj.setvar(name, v[name])
        obj.setp("use_tri", False)
        if v['cmap'] is not None:
            kywds['cmap'] = v['cmap']
        obj.setvar("kywds", kywds)
        return obj

    @classmethod
    def isFigSpec(self):
        return True

    @classmethod
    def get_namebase(self):
        return 'spec'

    @classmethod
    def property_in_palette(self):
        tab0, list0 = FigImage.property_in_palette()
        return (['fft']+tab0, [["spec_fftp",  "spec_noverlap",
                                "spec_window", "spec_detrend", "spec_sided"]]+list0)

    def _args2var(self):
        names0 = ['t', 'v']+self.attr_in_file()
        names = names0
        use_np = [True]*2 + [False]*len(names0)
        values = self.put_args2var(names,
                                   use_np)
        t = values[0]
        v = values[1]
        if t is None:
            t = np.arange((v.shape)[0]).astype(v.dtype)
            self.setp("t", t)
        return self._do_fft()

    def _do_fft(self):
        t = self.getp('t')
        v = self.getp('v')
        try:
            Fs = 1/(t[1] - t[0])
            NFFT = self.getp('NFFT')
            detrend = detrends[self.getp('detrend')]
            window = windows[self.getp('window')]
            noverlap = self.getp('noverlap')
            sides = self.getp('sides')

            pad_to = self.getp('pad_to')
            if pad_to == 'none':
                pad_to = None
            z, y, x = mlab.specgram(v, NFFT=NFFT,
                                    Fs=Fs,
                                    detrend=detrend,
                                    window=window,
                                    noverlap=noverlap,
                                    pad_to=pad_to,
                                    sides=sides,
                                    scale_by_freq=None)
            self.setp("x", x + t[0])
            self.setp("y", y)
            self.setp("z", z)
        except:
            traceback.print_exc()
            self.setp("x", None)
            self.setp("y", None)
            self.setp("z", None)
            return False
        return True

    def _rebuild_artist(self):
        self._do_fft()
        if (len(self._artists) != 0 and
                self.getp('z') is not None):
            a1 = self._artists[0]
            self.del_artist(delall=True)
            self.delp('loaded_property')
            self.generate_artist()
            self.get_figaxes().set_bmp_update(False)
            a2 = self._artists[0]
            ifigure.events.SendReplaceEvent(self, a1=a1, a2=a2)

    def refresh_artist_data(self):
        self._rebuild_artist()
#        super(FigSpec, self).refresh_artist_data()

    def set_spec_fftp(self, value, a):
        self.setp('NFFT', int(value[0]))
        if value[1] == 'none':
            self.setp('pad_to', None)
        else:
            self.setp('pad_to', int(value[1]))
        self._rebuild_artist()

    def get_spec_fftp(self, a):
        if self.getp("pad_to") is None:
            pad_to = 'none'
        else:
            pad_to = str(self.getp("pad_to"))
        return str(self.getp('NFFT')), pad_to

    def set_spec_noverlap(self, value, a):
        self.setp('noverlap', int(value))
        self._rebuild_artist()

    def get_spec_noverlap(self,  a):
        return self.getp('noverlap')

    def set_spec_window(self, value, a):
        self.setp('window', str(value))
        self._rebuild_artist()

    def get_spec_window(self, a):
        return self.getp('window')

    def set_spec_detrend(self, value, a):
        self.setp('detrend', str(value))

    def get_spec_detrend(self, a):
        return self.getp('detrend')

    def set_spec_sides(self, value, a):
        self.setp('sides', str(value))
        self._rebuild_artist()

    def get_spec_sides(self, a):
        return self.getp('sides')
