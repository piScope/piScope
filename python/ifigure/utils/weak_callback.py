import weakref


class WeakCallback (object):
    """A Weak Callback object that will keep a reference to
    the connecting object with weakref semantics.

    This allows object A to pass its callback method to object S,
    without object S keeping A alive.

    Based on StackOverflow "How to store callback methods?"

    Changes: added methode deref, so that it can be used as
             weakreference to object method
    """

    def __init__(self, mcallback):
        """Create a new Weak Callback calling the method @mcallback"""
        obj = mcallback.__self__
        attr = mcallback.__func__.__name__
        self.wref = weakref.ref(obj, self.object_deleted)
        self.callback_attr = attr
        self.token = None

    def __call__(self, *args, **kwargs):
        #        print 'WeakCallback is called'
        obj = self.wref()
        if obj:
            attr = getattr(obj, self.callback_attr)
            return attr(*args, **kwargs)
        else:
            return self.default_callback(*args, **kwargs)

    def deref(self):
        obj = self.wref()
        if obj:
            attr = getattr(obj, self.callback_attr)
            return attr
        else:
            raise TypeError('Method called on dead object')

    def default_callback(self, *args, **kwargs):
        """Called instead of callback when expired"""
        pass

    def object_deleted(self, wref):
        """Called when callback expires"""
        pass
