'''
   decorator which make sure that call happens in 
   the main thread.
'''
from functools import wraps
import wx
from six.moves import queue as Queue
import threading


class CallError(object):
    pass


def at_wxthread(func):
    @wraps(func)
    def checker(*args, **kargs):
        def func2(callable, queue, *args, **kargs):
            try:
                v = callable(*args, **kargs)
                queue.put(v)
            except:
                queue.put(CallError())

        t = threading.current_thread()
        if t.name == 'MainThread':
            return func(*args, **kargs)
        else:
            q = Queue.Queue()
            wx.CallAfter(func2, func,  q, *args, **kargs)
            value = q.get()
            if isinstance(value, CallError):
                raise ValueError('Asyc call failed')
        return value
    return checker
