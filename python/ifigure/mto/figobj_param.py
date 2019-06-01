from ifigure.mto.fig_obj import FigObj
from ifigure.mto.py_code import PyParam, PyData


class FigobjParam(PyParam, FigObj):
    def generate_artist(self, *args, **kargs):
        pass

    def del_artist(self, *args, **kargs):
        pass


class FigobjData(PyData, FigObj):
    def generate_artist(self, *args, **kargs):
        pass

    def del_artist(self, *args, **kargs):
        pass
