import numpy as np
class GLCompound(object):
    def isCompound(self):
        return self.hasvar('array_idx')

    @property
    def hidden_component(self):
        if not hasattr(self, '_hidden_component'):
            self._hidden_component = []
        return self._hidden_component
    
    def hide_component(self, idx):
        '''
        idx = list
        '''
        if not self.isCompound(): return
        self._hidden_component = idx  
        if len(self._artists) == 0: return

        a = self._artists[0]
        array_idx = self.getvar('array_idx')
        
        if self.hasvar('idxset'):
            idxset = self.getvar('idxset')
            
            mask  = np.array([ii in self._hidden_component for ii in array_idx],
                             copy=False)
            mask2 = np.array([not any(mask[iv]) for iv in idxset], copy = False)
            a.update_idxset(idxset[mask2])
            self.setSelectedIndex([])
        else:
            assert False, "hide_component is not supported for non-indexed artist"

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
        
    
