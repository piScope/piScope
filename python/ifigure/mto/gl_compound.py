import numpy as np
import ifigure

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('GL_COMPOUND')


class GLCompound(object):
    def isCompound(self):
        if (self.hasvar('array_idx') and
                self._var['array_idx'] is not None):
            return True
        return False

    @property
    def hidden_component(self):
        if not hasattr(self, '_hidden_component'):
            self._hidden_component = []
        return self._hidden_component

    @property
    def shown_component(self):
        h = self._hidden_component
        array_idx = np.unique(self.getvar('array_idx'))
        idx = array_idx[np.in1d(array_idx, h, invert=True)]

        return list(idx)

    def hide_component(self, idx, inverse=False):
        '''
        idx = list
        '''
        if not self.isCompound():
            return

        if inverse:
            array_idx = np.unique(self.getvar('array_idx'))
            idx = array_idx[np.in1d(array_idx, idx, invert=True)]
            idx = list(idx)

        self._hidden_component = idx
        if len(self._artists) == 0:
            return

        a = self._artists[0]
        array_idx = self.getvar('array_idx')
        flat_mode = array_idx.shape != a._gl_array_idx.shape

        if self.hasvar('idxset'):
            idxset = self.getvar('idxset')

            if flat_mode:
                mask = np.logical_not(
                    np.in1d(
                        np.abs(
                            a._gl_array_idx),
                        self._hidden_component))
                new_idxset = np.arange(len(a._gl_array_idx), dtype=int)
                new_idxset = new_idxset[mask].reshape(-1, idxset.shape[1])

            else:
                mask = np.in1d(array_idx, self._hidden_component)
                mask2 = np.logical_not(np.any(mask[idxset], axis=1))
                new_idxset = idxset[mask2]

            a.update_idxset(new_idxset)
            self.setSelectedIndex([])

            if self.hasvar('edge_idx') and self.getvar('edge_idx') is not None:
                idxset = self.getvar('edge_idx')
                mask2 = np.logical_not(np.any(mask[idxset], axis=1))
                a.update_edge_idxset(idxset[mask2])
        else:
            assert False, "hide_component is not supported for non-indexed artist"

    def get_subset(self, component=None):
        '''
        v, idx, cdata = gl_compound::get_subset(component = None)
        v, idx, cdata, edge_idx = gl_compound::get_subset(component = None)

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

        if self.hasvar('edge_idx') and self.getvar('edge_idx') is not None:
            idxset = self.getvar('edge_idx')
            mask2 = np.array([all(mask[iv]) for iv in idxset], copy=False)
            s2 = idxset[mask2]
            mapper = {x: k for k, x in enumerate(ii)}
            ss2 = np.array([mapper[x] for x in s2.flatten()])
            s2 = ss2.reshape(s2.shape)
            return v, idx, cdata, s2

        return v, idx, cdata

    def isSelected(self):
        # this is called to check if click hit this object
        return (len(self._artists[0]._gl_hit_array_id_new) > 0)

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
            a._gl_hit_array_id = list(ll)
            if a._gl_array_idx.shape == array_idx.shape:
                a._gl_array_idx = array_idx
            else:
                array_idx = np.abs(a._gl_array_idx)
                mask = np.isin(array_idx, np.array(ll, copy=False))
                array_idx[mask] *= -1
                a._gl_array_idx = array_idx
            a._update_a = True

    def addSelectedIndex(self, ll):
        ll = list(ll) + self.getSelectedIndex()
        ll = list(np.unique(ll))
        self.setSelectedIndex(ll)

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
        self.hide_component(idx + hidx)
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
        if not self.isCompound():
            return []
        m = []
        if not self.get_gl_hl_use_array_idx():
            m.append(("Pick by component", self.onPickComponent, None))
        else:
            m.append(("Hide selected", self.onHidePickedComponent, None))
            m.append(("Show selected only", self.onShowPickedOnly, None))
            if len(self.hidden_component) > 0:
                m.append(("Show all", self.onShowAllComponent, None))
            m.append(("Pick as object", self.onUnpickComponent, None))

        return m

    def canvas_unselected(self):
        self._artists[0]._gl_hit_array_id = []

    def rect_contains(self, rect, check_selected_all_covered=False):
        ax = self.get_figaxes()._artists[0]
        a = self._artists[0]
        hit, all_covered, selected_idx = ax.gl_hit_test_rect(rect, a,
                                                             check_selected_all_covered=check_selected_all_covered)
        return hit, a, all_covered, selected_idx
