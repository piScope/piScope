import numpy as np 

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
            if x in array_idx: array_idx.remove(x)
        return array_idx

    def hide_component(self, idx, inverse = False):
        '''
        idx = list
        '''
        if inverse:
            array_idx = list(np.unique(self.getvar('array_idx')))
            for x in idx:
               if x in array_idx: array_idx.remove(x)
            idx = array_idx
        if not self.isCompound(): return
        self._hidden_component = idx  
        if len(self._artists) == 0: return

        a = self._artists[0]
        array_idx = self.getvar('array_idx')
        
        if self.hasvar('idxset'):
            idxset = self.getvar('idxset')
            
            mask  = np.in1d(array_idx, self._hidden_component)
            mask2 = np.logical_not(np.any(mask[idxset], axis=1))
            a.update_idxset(idxset[mask2])
            self.setSelectedIndex([])
        else:
            assert False, "hide_component is not supported for non-indexed artist"

    def get_subset(self, component = None):
        if not self.hasvar('idxset'): return
        if component is None:
            component = self.shown_component
        array_idx = self.getvar('array_idx')
        idxset = self.getvar('idxset')
            
        mask  = np.array([ii in component for ii in array_idx],
                             copy=False)
        mask2 = np.array([all(mask[iv]) for iv in idxset], copy = False)

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
        self._artists[0]._gl_hit_array_id = ll

    def set_pickmask(self, value):
        '''
        mask = True :: not pickable 
        '''
        self._pickmask = value
        for a in self._artists:
            a._gl_pickable = not value
        
    
