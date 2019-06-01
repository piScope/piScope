from __future__ import print_function
'''
   a routin to expand goemetry array

   equivalent to the following IDL

   xvctr=mdsvalue('\analysis::top.limiters.tiles:XTILE')
   yvctr=mdsvalue('\analysis::top.limiters.tiles:YTILE')
   nvctr=mdsvalue('\analysis::top.limiters.tiles:NSEG')
   lvctr=mdsvalue('\analysis::top.limiters.tiles:PTS_PER_SEG')

   for i=0,nvctr-1 do begin
     x = n_elements(x) eq 0 ? xvctr(0:lvctr(i)-1,i) $
       : [x, !values.f_nan, xvctr(0:lvctr(i)-1,i)]
     y = n_elements(y) eq 0 ? yvctr(0:lvctr(i)-1,i) $
       : [y, !values.f_nan, yvctr(0:lvctr(i)-1,i)]   
   end
'''
import numpy as np


def expand_vctr(x, y, n, l):
    print(x.shape, end=' ')
    res_x = [np.hstack((x[k, :l[k]], np.nan)) for k in range(n)]
    res_y = [np.hstack((y[k, :l[k]], np.nan)) for k in range(n)]

    return np.hstack(res_x)[:-2], np.hstack(res_y)[:-2]


def expand_vctr3d(xyz, n, l, list=False):
    if list:
        res_x = [np.hstack(xyz[k, :l[k], 0]) for k in range(n)]
        res_y = [np.hstack(xyz[k, :l[k], 1]) for k in range(n)]
        res_z = [np.hstack(xyz[k, :l[k], 2]) for k in range(n)]
        return res_x, res_y, res_z
    else:
        res_x = [np.hstack((xyz[k, :l[k], 0], np.nan)) for k in range(n)]
        res_y = [np.hstack((xyz[k, :l[k], 1], np.nan)) for k in range(n)]
        res_z = [np.hstack((xyz[k, :l[k], 2], np.nan)) for k in range(n)]
        return np.hstack(res_x)[:-2], np.hstack(res_y)[:-2], np.hstack(res_z)[:-2]


def read_vtcr(file):
    from scipy.io.idl import readsav
    nm0 = readsav(file)
    return expand_vctr(nm0['xvctr'], nm0['yvctr'],
                       nm0['nvctr'], nm0['lvctr'])
