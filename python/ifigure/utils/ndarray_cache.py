from __future__ import print_function
import weakref


class NdArrayCache(object):
    cache = weakref.WeakKeyDictionary({})
    i = 0

    def __init__(self, *args, **kywds):
        pass

    def show(self):
        for key in NdArrayCache.cache.iterkeyrefs():
            print(NdArrayCache.cache[key()])

    def store(self, t):
        if self.get_id(t) is not None:
            return self.get_id(t)
        data = []
        if t.base is not None:
            # chick if t.base is stored
            if not self.check(t.base):
                tbase_id = self.store(t.base)
            else:
                tbase_id = self.get_id(t.base)
        else:
            tbase_id = None

        NdArrayCache.i = NdArrayCache.i + 1
        data.append((NdArrayCache.i, tbase_id,
                     t.shape, t.strides))

        return NdArrayCache.i

    def get_id(self, obj):
        try:
            return NdArrayCache.cache[obj][0]
        except ReferenceError:
            return None
