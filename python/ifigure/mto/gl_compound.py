class GLCompound(object):
    @classmethod 
    def isCompound(cls):
        return True

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
        
    
