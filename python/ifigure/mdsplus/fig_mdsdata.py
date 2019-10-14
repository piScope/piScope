from __future__ import print_function
import traceback
import os
import ifigure
import numpy as np
import ifigure.utils.cbook as cbook
from ifigure.mto.py_code import PyData
from ifigure.mdsplus.fig_mds import FigMds
from ifigure.mto.figobj_param import FigobjParam, FigobjData
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigMdsData')


class FigMdsData(FigMds):
    def __init__(self, *args, **kargs):
        FigMds.__init__(self, *args, **kargs)
        self._plot_type = 'noplot'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx = cbook.LoadImageFile(path, 'data.png')
        return [idx]

    @classmethod
    def property_in_palette(self):
        return ["mdssource"]

    def get_artist_extent(self, a=None):
        return [None]*4

    def generate_artist(self, *args, **kargs):
        pass

    def del_artist(self, *args, **kargs):
        pass

    def postprocess_data(self, ana, viewer,
                         color_order=['red', 'blue', 'yellow'],
                         ):
        ishot = ana.uishot
        if ishot < 0:
            return
        if ishot >= self.num_child():
            obj = FigobjData()
            self.add_child('data'+str(ishot+1), obj)
        else:
            obj = self.get_child(ishot)

        if self.get_script_local:
            txt = self.make_script(ana.shot)
            if txt is not None:
                try:
                    code = compile(txt, '<string>', 'exec')
                    g = {}
                    l = {}
                    exec(code, viewer.g, ana.result)
                except:
                    dprint1('error occured when processing data by script')
                    print('error occured when processing data by following script')
                    print('#####')
                    print(txt)
                    print('#####')
                    print(traceback.format_exc())
                    self.get_child(ishot).set_suppress(True)
                    ana.postprocess_done = True
                    return
        obj.setvar('shot', ana.shot)
        obj.setvar('global_data',
                   {key: ana.result[key] for key in ana.result
                    if (isinstance(ana.result[key], np.ndarray) or isinstance(ana.result[key], np.number))})
        ana.postprocess_done = True

    def process_title(self, ana):
        pass

    def call_refresh_artist(self, ishot):
        pass

    def active_plots(self, l):
        pass

    def set_mdsrange(self, value, a):
        self._default_xyrange = value

    def get_mdsrange(self, a):
        return self._default_xyrange

    def get_mdsfiguretype(self, a):
        return self._plot_type

    def get_script_local(self, a=None):
        v = self.get_figbook().getvar('mdsscript_main')
        if v is not None:
            return v
        return True

    def onDataSetting(self, evt, noapply=False):
        if self._session_editor is not None:
            try:
                self._session_editor.Raise()
                return
            except:
                pass
        from ifigure.mdsplus.dlg_mdssession_data import DlgMdsSessionData
        p = evt.GetEventObject().GetTopLevelParent()
        data = self.getvar('mdsvars')
        self._session_editor = DlgMdsSessionData(p, data=data,
                                                 figmds=self,
                                                 noapply=noapply)
        evt.Skip()

    def save_data2(self, data=None):
        if self._save_mode == 1:
            d = self.getvar('global_data')
            self.setvar('global_data', None)
            data = super(FigMdsData, self).save_data2(data)
            self.setvar('global_data', d)
        else:
            data = super(FigMdsData, self).save_data2(data)
        return data
