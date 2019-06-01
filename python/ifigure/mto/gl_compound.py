import numpy as np
import ifigure

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('GL_COMPOUND')


class GLCompound(object):
    def isCompound(self):
        return self.hasvar('array_idx')

    @property
    def hidden_component(self):
        if not hasattr(self, '_hidden_component'):
            self._hidden_component = []
        return self._hidden_component

    @property
    def shown_component(self):
        h = self._hidden_component
        array_idx = list(np.unique(self.getvar('array_idx')))
        for x in h:
            if x in array_idx:
                array_idx.remove(x)
        return array_idx

    def hide_component(self, idx, inverse=False):
        '''
        idx = list
        '''
        if not self.isCompound():
            return

        if inverse:
            array_idx = list(np.unique(self.getvar('array_idx')))
            for x in idx:
                if x in array_idx:
                    array_idx.remove(x)
            idx = array_idx

        self._hidden_component = idx
        if len(self._artists) == 0:
            return

        a = self._artists[0]
        array_idx = self.getvar('array_idx')

        if self.hasvar('idxset'):
            idxset = self.getvar('idxset')

            mask = np.in1d(array_idx, self._hidden_component)
            mask2 = np.logical_not(np.any(mask[idxset], axis=1))
            a.update_idxset(idxset[mask2])
            self.setSelectedIndex([])
        else:
            assert False, "hide_component is not supported for non-indexed artist"

    def get_subset(self, component=None):
        '''
        v, idx, cdata = gl_compound::get_subset(component = None)

        return the vertex information of components
        if component is None, it returns visible components
        '''
        if not self.hasvar('idxset'):
            return
        if component is None:
            component = self.shown_component
        array_idx = self.getvar('array_idx')
        idxset = self.getvar('idxset')

        mask = np.array([ii in component for ii in array_idx],
                        copy=False)
        mask2 = np.array([all(mask[iv]) for iv in idxset], copy=False)

        s = idxset[mask2]
        ii, arr = np.unique(s.flatten(), return_inverse=True)
        idx = arr.reshape(s.shape)
        v = self.getvar('v')[ii]
        if not self.hasvar('cdata'):
            cdata = self.hasvar('cdata')[idx]
        else:
            cdata = None
        return v, idx, cdata

    def isSelected(self):
        return (len(self._artists[0]._gl_hit_array_id) > 0)

    def getSelectedIndex(self):
        return self._artists[0]._gl_hit_array_id

    def setSelectedIndex(self, ll):
        array_idx = self.getvar('array_idx')
        if array_idx is None:
            return
        array_idx = array_idx.copy()
        mask = np.isin(array_idx, np.array(ll, copy=False))
        array_idx[mask] *= -1
        for a in self._artists:
            a._gl_hit_array_id = ll
            a._gl_array_idx = array_idx
            a._update_a = True

    def set_pickmask(self, value):
        '''
        mask = True :: not pickable 
        '''
        self._pickmask = value
        for a in self._artists:
            a._gl_pickable = not value

    def set_gl_hl_use_array_idx(self, value):
        self.setp('_hl_use_array_idx', value)
        for a in self._artists:
            a.set_gl_hl_use_array_idx(value)

    def get_gl_hl_use_array_idx(self):
        return self.getp('_hl_use_array_idx') == True

    def onPickComponent(self, evt):
        self.set_gl_hl_use_array_idx(True)

    def onUnpickComponent(self, evt):
        self.set_gl_hl_use_array_idx(False)

    def onHidePickedComponent(self, evt):
        idx = self.getSelectedIndex()
        hidx = self.hidden_component
        self.hide_component(idx+hidx)
        self.set_bmp_update(False)
        evt.GetEventObject().unselect_all()
        ifigure.events.SendPVDrawRequest(self, w=evt.GetEventObject(),
                                         wait_idle=True, refresh_hl=False)

    def onShowPickedOnly(self, evt):
        idx = self.getSelectedIndex()
        self.hide_component(idx, inverse=True)
        self.set_bmp_update(False)
        ifigure.events.SendPVDrawRequest(self, w=evt.GetEventObject(),
                                         wait_idle=True, refresh_hl=False)

    def onShowAllComponent(self, evt):
        self.hide_component([])
        self.setSelectedIndex([])
        self.set_bmp_update(False)
        self.set_bmp_update(False)
        ifigure.events.SendPVDrawRequest(self, w=evt.GetEventObject(),
                                         wait_idle=True, refresh_hl=False)

    def canvas_menu(self):
        if not self.isCompound:
            return []
        m = []
        if not self.get_gl_hl_use_array_idx():
            m.append(("Pick by component", self.onPickComponent, None))
        else:
            m.append(("Hide selected", self.onHidePickedComponent, None))
            m.append(("Show selected only", self.onShowPickedOnly, None))
            if len(self.hidden_component) > 0:
                m.append(("Show all",  self.onShowAllComponent, None))
            m.append(("Pick as object", self.onUnpickComponent, None))

        return m

    def canvas_unselected(self):
        self._artists[0]._gl_hit_array_id = []
