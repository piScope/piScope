from __future__ import print_function

'''
test module
'''

from ifigure.interactive import figure, property
import numpy as np
import traceback


def check_prop_read(obj):
    print('read property test :' + str(obj))
    props = property(obj)
    ret = {}
    for prop in props:
        try:
            val = property(obj, prop)
            print(str(prop) + ' : ' + str(val))
        except:
            print('reading '+str(prop) + ' failed')
            traceback.print_exc()
            return ret
        ret[prop] = val
    return ret


def check_prop_write(obj, data):
    print('write property test :' + str(obj))
    for prop in data:
        try:
            print(str(prop) + ' : ' + str(data[prop]))
            property(obj, prop, data[prop])
        except:
            print('writinging '+str(key) + ' failed')


def test_ax():
    v = figure()
    ax = v.get_axes()
    pl = v.plot(np.arange(30))

    ret = check_prop_read(ax)
    check_prop_write(ax, ret)
