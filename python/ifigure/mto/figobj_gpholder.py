from ifigure.mto.fig_obj import FigObj
from ifigure.mto.generic_points import GenericPoint, GenericPointsHolder


class FigObjGPHolder(FigObj, GenericPointsHolder):
    def destroy(self, clean_owndir=True):
        if self._cb_added:
            fig_page = self.get_figpage()
            fig_page.rm_resize_cb(self)
        GenericPointsHolder.destroy(self)
        FigObj.destroy(self, clean_owndir=clean_owndir)

    def check_loaded_gp_data(self):
        figpage = self.get_figpage()
        figaxes = self.get_figaxes()

        for k, gp in enumerate(self._gp_points):
            gp.set_figpage(figpage)

        if hasattr(self, '_loaded_gp_data'):
            for k, gp in enumerate(self._gp_points):
                gp.set_figpage(figpage)
                gp.dict_to_gp(self._loaded_gp_data[k], self)
            del self._loaded_gp_data

        for k, gp in enumerate(self._gp_points):
            if figaxes is not None:
                gp.set_figaxes(figaxes)

    def set_parent(self, parent):
        FigObj.set_parent(self, parent)
        GenericPointsHolder.set_parent(self, parent)

    def save_data(self, fid=None):
        FigObj.save_data(self, fid)
        GenericPointsHolder.save_data(self, fid)

    def load_data(self, fid=None):
        FigObj.load_data(self, fid)
        GenericPointsHolder.load_data(self, fid)

    def save_data2(self, data):
        data = FigObj.save_data2(self, data)
        data = GenericPointsHolder.save_data2(self, data)
        return data

    def load_data2(self, data):
        FigObj.load_data2(self, data)
        GenericPointsHolder.load_data2(self, data)
