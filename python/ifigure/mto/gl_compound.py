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
        
    
