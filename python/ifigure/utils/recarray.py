from __future__ import print_function
import numpy as np
import collections


def rec2dict(arr, cls=collections.OrderedDict):
    if not hasattr(arr, 'flatten'):
        return arr
    if not hasattr(arr.flatten()[0], 'dtype'):
        return arr
    elif arr.dtype.names is not None:
        r = cls()
        for name in arr.dtype.names:
            print(name)
            print(isinstance(arr[name], np.recarray))
            if isinstance(arr[name], np.recarray):
                r[name] = rec2dict(arr[name])
            elif (isinstance(arr[name], np.ndarray) and
                  arr[name].ndim == 1
                  and arr[name].shape[0] == 1 and
                  isinstance(arr[name][0], np.recarray)):
                r[name] = rec2dict(arr[name][0], cls=cls)
            else:
                r._var0[name] = arr[name]
        return r
    elif arr.dtype.hasobject:
        if arr.ndim == 1 and arr.shape[0] == 1:
            return rec2dict(arr[0])
        else:
            arr2 = arr.flatten()
            v = np.array([None]*len(arr2))
            for k, x in enumerate(arr2):
                v[k] = rec2dict(arr2[k])
            return v.reshape(arr.shape)
    else:
        return arr
