#
#  these routines recovers old scipy interp1d and interp2d 
#
from scipy.interpolate import RectBivariateSpline, make_interp_spline

def interp1d(x, y, kind='linear'):
    if kind=='linear':
        return make_interp_spline(x, y, k=1)
    elif kind=='cubic':
        return make_interp_spline(x, y, k=3)    


def interp2d(x, y, z, kind='linear'):
    if kind == 'cubic':
        kx = 3
        ky = 3
    elif kind == 'linear':
        kx = 1
        ky = 1
        
    return RectBivariateSpline(x, y, z.transpose(), kx=kx, ky=ky)
