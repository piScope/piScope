from __future__ import print_function
__version__ = '1.0.0'
__author__ = 'shiraiwa'
'''
nameing convetin for files
'''
import numpy as np
def gname(shot, t):
    return 'g'+str(shot)+'.'+ '{:0>5d}'.format(int(t*1000))
def aname(shot, t):
    return 'a'+str(shot)+'.'+ '{:0>5d}'.format(int(t*1000))
def kname(shot, t):
    return 'k'+str(shot)+'.'+ '{:0>5d}'.format(int(t*1000))

kind = 'cubic'

from scipy.interpolate import interp2d, interp1d
from scipy.optimize import curve_fit
from scipy.interpolate import CubicSpline


def ensure_cyclic(pts):
  if pts[0, 0] != pts[-1, 0] or pts[0, 1] != pts[-1, 1]: 
      return np.vstack((pts, pts[0]))
  return pts

def XY2pts(X, Y):
    if not isinstance(X, np.ndarray):
         X = np.array(X)
    if not isinstance(Y, np.ndarray):
         Y = np.array(Y)

    pts = np.hstack((X.flatten()[:, np.newaxis],
                     Y.flatten()[:, np.newaxis]))
    return pts

def path_contain(path, xy, check = False, cyclic = True):
    '''
    check if path contains xy based on winding number
    algorithm.

    equivalent to 
      mod(angle(u)-angle(v) - 180, 360) - 180 ???

    if xy is on a point of path, it returns True

    the first point and the last point should be the same
    (ensure_cyclic forces it)a
    '''
    if cyclic:
        path = ensure_cyclic(path)
    import numpy as np
    dx = path[:,0] - xy[0]
    dy = path[:,1] - xy[1]
    d1 = np.sqrt(dx[:-1]**2 + dy[:-1]**2)
    d2 = np.sqrt(dx[1:]**2 +  dy[1:]**2)

    d = (dx[:-1]*dy[1:] - dx[1:]*dy[:-1])/d1/d2
    dotp = (dx[:-1]*dx[1:] + dy[1:]*dy[:-1])
    if any(np.isnan(d)):
        ### when d1, d2 = 0
        return True

    d = np.arcsin(d)
    d[np.logical_and(dotp<0, d>0)] = np.pi-d[np.logical_and(dotp<0, d>0)]
    d[np.logical_and(dotp<0, d<0)] = -np.pi-d[np.logical_and(dotp<0, d<0)]

    xxxx = sum(d)
#    print(np.abs(xxxx)/3.14159/2)
#    if check: return d
    if check: return np.abs(xxxx)/np.pi/2
    return -0.001 < np.abs(xxxx)-np.pi*2 < 0.001

def calc_area(path, xy = [0., 0.]):
    '''
    calc area inside path
    '''
    import numpy as np
    dx = path[:,0] - xy[0]
    dy = path[:,1] - xy[1]
    d1 = np.sqrt(dx[:-1]**2 + dy[:-1]**2)
    d2 = np.sqrt(dx[1:]**2 +  dy[1:]**2)

    d = (dx[:-1]*dy[1:] - dx[1:]*dy[:-1])
    return np.abs(np.sum(d)/2.)

def area_intersection(p1, p2, area, internal_only = False, 
                      closed = True, once = False, return_idx=False):
   '''
   search all possible crosspoint with area on the line connecting p1 and p2
   if internal_only, crosspoint should be between p1 and p2
   p1, p2 : 2D points (x, y)
   area   : [[x1, x2, x3, x4,,,,], [y1, y2, y3,,,,]]
   '''
   x_a = area[0]
   y_a = area[1]
   if closed:
      if x_a[0] != x_a[-1] or y_a[0] != y_a[-1]: 
          y_a.append(y_a[0])
          x_a.append(x_a[0])

   p1 = np.array(p1)
   p2 = np.array(p2)

   p = p2 - p1

   x = []
   y = []
   idx = []
   q1 = XY2pts(x_a[:-1], y_a[:-1])
   q2 = XY2pts(x_a[1:],  y_a[1:])
   q0  = q2 - q1
   for k in range(len(area[0])-1):
#      q1 = np.array([x_a[k], y_a[k]])
#      q2 = np.array([x_a[k+1], y_a[k+1]])
#      q  = q2 - q1
      q = q0[k]
      m = np.matrix((-p, q))
      if np.linalg.cond(m) < 1./sys.float_info.epsilon:
#          ans =  np.array((p1 - q1)*(np.matrix((-p, q))**-1)).flatten()
          ans =  np.array((p1 - q1[k])*(np.matrix((-p, q))**-1)).flatten()
      else:
          continue

      if 0. < ans[-1] <= 1.:
          if not internal_only or (internal_only and 
                                   (0. < ans[0] <= 1.)):
#              x.append((q1 + ans[1]*q)[0])
#              y.append((q1 + ans[1]*q)[1])
              x.append((q1[k] + ans[1]*q)[0])
              y.append((q1[k] + ans[1]*q)[1])
              idx.append(k+ans[1])
              if once: break

   if return_idx: 
       return x, y, idx
   else:
       return x, y

'''
find contour
'''
def find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis, psi, return_all = False):
    '''
    return_all : return all segments
    (default)  : return path containing magnetic axis
                 if 0<npsi2psi(psi)<1: this is sufficient to check if it is inside LCFS
    '''
    #from ifigure.utils.geom import path_contain, XY2pts

    try:
        from matplotlib import _cntr as cntr
    except ImportError:
        try:
            from legacycontour import _cntr as cntr
        except ImportError:
            import ifigure.utils.find_contours as cntr        

    from scipy.interpolate import interp2d
    from scipy.interpolate import interp2d, interp1d, RectBivariateSpline

    #if False:
    if True:
       rgrid3 = np.linspace(rgrid[3], rgrid[-3], len(rgrid)*2)
       zgrid3 = np.linspace(zgrid[3], zgrid[-3], len(zgrid)*2)
       f = RectBivariateSpline(rgrid, zgrid, psirz.transpose())
       X3, Y3 = np.meshgrid(rgrid3, zgrid3)
       #psirz3 = [f(X3.flatten(), Y3.flatten()).reshape(X3.shape)
       psirz3 = np.hstack([f(x, y) for x, y in zip(X3.flatten(), Y3.flatten())]).reshape(X3.shape)
       #psirz3 = np.transpose(psirz3)
       c = cntr.Cntr(X3, Y3, psirz3)
       rgrid = rgrid3
       zgrid = zgrid3

    else:
       X, Y = np.meshgrid(rgrid, zgrid)
       c = cntr.Cntr(X, Y, psirz)

    res = c.trace(psi)
    nseg = len(res)//2
    segments, codes = res[:nseg], res[nseg:]
    dr = rgrid[1]-rgrid[0]
    dz = zgrid[1]-zgrid[0]
    
    
    if return_all: return segments
    res = []
    for k, seg in enumerate(segments):
        if path_contain(seg, [rmaxis, zmaxis]):
            return seg

def flux_average(rgrid, zgrid, psirz, rmaxis, zmaxis, q, psi):
    '''
    compute flux surface averaged value of
    quantity q. 
    q: 2D array
    psi: psi on which average is taken
    '''
    from scipy.interpolate import interp2d, interp1d

    path = find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis, psi)

    R, Z = np.meshgrid(rgrid, zgrid) 
    dr = rgrid[1]-rgrid[0]
    dz = zgrid[1]-zgrid[0]
    dpsidz, dpsidr = np.gradient(psirz)
    br = interp2d(rgrid, zgrid, -dpsidz/dz/R)
    bz = interp2d(rgrid, zgrid, dpsidr/dr/R)
    bp = np.array([np.sqrt(br(x, y)**2+bz(x, y)**2)  for x, y in zip(path[:,0], path[:,1])]).flatten()

    q = interp2d(rgrid, zgrid, q)
    qq = np.array([q(x,y) for x, y in zip(path[:,0], path[:,1])]).flatten()

    # create half grid data
    dl = np.sqrt((path[1:,0] - path[:-1,0])**2 + (path[1:,1] - path[:-1,1])**2)
    qq = (qq[1:]+qq[:-1])/2
    bp = (bp[1:]+bp[:-1])/2
    r = (path[1:,0]+path[:-1,0])/2

    # integration
    l = np.sum(qq*dl/bp/r)/np.sum(dl/bp/r)
    return l


'''
file below accept gfile object
'''

def limiter_rho(gfile):
   '''
   the distance of limiter normalized minor radius by 
   minor radius as a function of poloidal angle
   '''
   #from ifigure.utils.geom import area_intersection
   ra = gfile.get_contents('table', 'rmaxis')
   za = gfile.get_contents('table', 'zmaxis')
   rb = gfile.get_contents('table', 'rbbbs')
   zb = gfile.get_contents('table', 'zbbbs')
   rl = gfile.get_contents('table', 'xlim')
   zl = gfile.get_contents('table', 'ylim')

   rg = gfile.get_contents('table', 'rgrid')
   zg = gfile.get_contents('table', 'zgrid')
   lll = np.sqrt((rg[-1]-rg[0])**2 + (zg[-1]-zg[0])**2)

   tharr = np.linspace(-np.pi, np.pi, 180)
   tharr = tharr[:-1]

   p1 = [ra, za]
   res = []
   res2 = []
   for th in tharr:
       p2 = [ra + lll*np.cos(th), za + lll*np.sin(th)]
       x, y = area_intersection(p1, p2, 
                          [rl, zl],
                          internal_only = True, closed = False)
       x2, y2 = area_intersection(p1, p2, 
                          [rb, zb],
                          internal_only = True, closed = False)
       res.append(np.min(np.sqrt((np.array(x)-ra)**2 + (np.array(y)-za)**2)))
       res2.append(np.min(np.sqrt((np.array(x2)-ra)**2 + (np.array(y2)-za)**2)))
   return tharr, np.array(res)/np.array(res2)

def check_path_inside_LCFS(gfile, path):
    #from ifigure.utils.geom import path_contain, XY2pts, calc_area
    rbbbs = gfile.get_contents("table","rbbbs")
    zbbbs = gfile.get_contents("table","zbbbs")
    rmaxis = gfile.get_contents("table","rmaxis")
    zmaxis = gfile.get_contents("table","zmaxis")
    if (path_contain(path, [rmaxis, zmaxis]) and
        calc_area(XY2pts(rbbbs, zbbbs)) > calc_area(path)): return True

    return False

def npsi2path(gfile, npsi, **kargs):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")

    psi = npsi2psi(gfile, npsi)
    path = find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis, psi, **kargs)

    return path

def npsi2psi(gfile, npsi):
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")
    return ssimag + (ssibry-ssimag)*npsi

def psi2npsi(gfile, psi):
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")
    return (psi - ssimag)/(ssibry-ssimag)

def _get_hr_rmid(gfile, fac=4):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")
    npsimid = gfile.get_contents("table","npsimid")

    idx = np.where(rgrid < rmaxis)[0]
    npsimid2 = npsimid[idx]
    rgrid2 =   rgrid[idx]
    idx = np.where(np.logical_and(0 < npsimid2, npsimid2 <1.))[0]
    if idx[0] != 0: idx = [idx[0]-1]+list(idx)
    npsimid2 = npsimid2[idx]
    rgrid2 =   rgrid2[idx]

    idx = np.where(rgrid > rmaxis)[0]
    npsimid1 = npsimid[idx]
    rgrid1 =   rgrid[idx]
    idx = np.where(np.logical_and(0 < npsimid1, npsimid1 <1.))[0]
    if idx[-1] != len(rgrid)-1: idx = list(idx)+[idx[-1]+1]
    npsimid1 = npsimid1[idx]
    rgrid1 =   rgrid1[idx]

#    new_r = (list(np.linspace(rgrid2[0], maxis, len(rgrid2)*fac)[:-1])+
#            list(np.linspace(rmaxis, rgrid1[-1], len(rgrid1)*fac)))
    kkk = 4
    new_r = (list(rgrid2[:-kkk]) + 
             list(np.linspace(rgrid2[-kkk+1], rgrid1[kkk], 30))+
             list(rgrid1[(kkk+1):]))
    new_r = np.array(new_r)
    xxx = list(rgrid2)+[rmaxis]+list(rgrid1) 
    yyy = list(npsimid2)+[0.0]+list(npsimid1)
    fx = interp1d(xxx, yyy, kind =kind)
    return new_r, fx(new_r)

def _get_hr_r1(gfile, fac=4):
    rmaxis = gfile.get_contents("table","rmaxis")
    rgrid, npsi = _get_hr_rmid(gfile, fac=4)
    idx = np.where(rgrid > rmaxis)[0]    
#    print npsi[idx], rgrid[idx]
    return npsi[idx], rgrid[idx]

def _get_hr_r2(gfile, fac=4):
    rmaxis = gfile.get_contents("table","rmaxis")
    rgrid, npsi = _get_hr_rmid(gfile, fac=4)
    idx = np.where(rgrid <= rmaxis)[0]    
    return npsi[idx], rgrid[idx]

def _get_enhanced_r1_array(gfile, enhance_center):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")
    npsimid = gfile.get_contents("table","npsimid")

    idx = np.where(rgrid > rmaxis)[0]
    npsimid = npsimid[idx]
    rgrid =   rgrid[idx]
    print('11111')
    idx = np.where(np.logical_and(0 < npsimid, npsimid <1.))[0]
    if idx[-1] != len(rgrid)-1: idx = list(idx)+[idx[-1]+1]

    npsimid = npsimid[idx]
    rgrid =   rgrid[idx]
    npsimid = [0]+list(npsimid)
    rgrid   = [rmaxis] + list(rgrid)

    if enhance_center > 0:
       k = enhance_center
       x2 = rgrid[0:k]
       y2 = npsimid[0:k]
       fx2 = np.poly1d(np.polyfit(x2, y2, 2))
       xc = np.linspace(rgrid[0], rgrid[k], 15)
       npsic =  fx2(xc)
       rgrid = list(xc) + rgrid[(k+1):]
       npsimid = list(npsic) + npsimid[(k+1):]
    return npsimid, rgrid

def npsi2r1(gfile, npsi, enhance_center=4):
#    npsimid, rgrid = _get_enhanced_r1_array(gfile, enhance_center)
    npsimid, rgrid = _get_hr_r1(gfile, enhance_center)
    rmaxis = gfile.get_contents("table","rmaxis")
    if npsi < npsimid[0]: return rmaxis
    if npsi > np.max(npsimid): return np.max(rgrid)

    fx = interp1d(npsimid, rgrid, kind =kind)
    return fx(npsi)

def r12npsi(gfile, r1, enhance_center=4):
#    npsimid, rgrid = _get_enhanced_r1_array(gfile, enhance_center)
    npsimid, rgrid = _get_hr_r1(gfile, enhance_center)
    if rgrid[-1] < r1: return npsimid[-1]
    if rgrid[0]  > r1: return npsimid[0]
    fx = interp1d(rgrid, npsimid, kind =kind)
    return fx(r1)

def _get_enhanced_r2_array(gfile, enhance_center):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")
    npsimid = gfile.get_contents("table","npsimid")

    idx = np.where(rgrid < rmaxis)[0]
    npsimid = npsimid[idx]
    rgrid =   rgrid[idx]

    idx = np.where(np.logical_and(0 < npsimid, npsimid <1.))[0]
    if idx[0] != 0: idx = [idx[0]-1]+list(idx)
    npsimid = npsimid[idx]
    rgrid =   rgrid[idx]
    npsimid = list(npsimid)+[0]
    rgrid   = list(rgrid)+[rmaxis]

    if enhance_center > 0:
       k = enhance_center
       x2 = rgrid[-k-1:]
       y2 = npsimid[-k-1:]
       fx2 = np.poly1d(np.polyfit(x2, y2, 2))
       xc = np.linspace(x2[0], x2[-1], 15)
       npsic =  fx2(xc)
       rgrid = rgrid[:(-k-2)] + list(xc)
       npsimid =  npsimid[:(-k-2)] + list(npsic) 
    return npsimid, rgrid


def npsi2r2(gfile, npsi, enhance_center=4):
#    npsimid, rgrid = _get_enhanced_r2_array(gfile, enhance_center)
    npsimid, rgrid = _get_hr_r2(gfile, enhance_center)
    rmaxis = gfile.get_contents("table","rmaxis")
    if npsi < npsimid[-1]: return rmaxis
    fx = interp1d(np.array(npsimid), np.array(rgrid), kind =kind)
    return fx(npsi)

def r22npsi(gfile, r1, enhance_center=4):
#    npsimid, rgrid = _get_enhanced_r2_array(gfile, enhance_center)
    npsimid, rgrid = _get_hr_r2(gfile, enhance_center)
    #if npsi < npsimid[-1]: return 0
    if rgrid[-1] < r2: return npsimid[-1]
    if rgrid[0]  > r2: return npsimid[0]
    fx = interp1d(rgrid, npsimid, kind =kind)
    return fx(r1)

def check_rmid_fit(gfile, enhance_center=3):
   
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    npsimid = gfile.get_contents("table","npsimid")
 
    npsi = np.linspace(0, 1, 3000)
    r1 = [npsi2r1(gfile, xx, enhance_center=enhance_center) for xx in npsi]
    r2 = [npsi2r2(gfile, xx, enhance_center=enhance_center) for xx in npsi]

    from ifigure.interactive import figure
    v = figure();
    v.plot(rgrid, npsimid, 'bo')
    v.plot(r1,    npsi, 'r')
    v.plot(r2,    npsi, 'k')
  
#    psi = npsi2psi(gfile, npsi)
#    path = find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis, psi)
#    return np.min(path[:,0])

def npsi2rho(gfile, npsi):
    r1 = npsi2r1(gfile, npsi)
    rmid = np.max(gfile.get_contents("table","rbbbs"))
    r0 =   gfile.get_contents("table","rmaxis")
    return (r1-r0)/(rmid-r0)

def rho2npsi(gfile, rho):
    rmid = np.max(gfile.get_contents("table","rbbbs"))
    r0 =   gfile.get_contents("table","rmaxis")
    z0 =   gfile.get_contents("table","zmaxis")

    r = (rmid - r0)*rho+r0
    return r12npsi(gfile, r)

def rz2psi(gfile, r=None, z=None, func=False):    
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")

    from scipy.interpolate import interp2d, interp1d
    fpsi = interp2d(rgrid, zgrid, psirz, kind='cubic')
    if func: return fpsi
    return fpsi(r, z)

def rz2npsi(gfile, r=0, z=0, func = False):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")
    psirz = (psirz - ssimag)/(ssibry-ssimag)
    from scipy.interpolate import interp2d, interp1d
    fpsi = interp2d(rgrid, zgrid, psirz, kind='cubic')
    if func: return fpsi
    return fpsi(r, z)

def _compute_psit(gfile):
    qpsi = gfile.get_contents("table","qpsi")
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")

    from scipy.integrate import cumtrapz
    dpsi = (ssimag - ssibry)/len(qpsi)
    psit = cumtrapz(qpsi)*dpsi
    return np.array([0] + [x for x in psit])
#    return psit

def _compute_npsit(gfile):
    psit = _compute_psit(gfile)
    npsit = (psit-psit[0])/(psit[-1] - psit[0])
    return npsit

def psi2psit(gfile, x):
    '''
    convert poloidal to toroidal flux
    '''
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")

    psit = _compute_psit(gfile)
    psi = np.linspace(ssimag, ssibry, len(psit))
    from scipy.interpolate import interp1d
    fx = interp1d(psi, psit)
    return fx(x)

def psit2psi(gfile, x):
    '''
    convert toroidal flux to poloidal flux
    '''
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")

    psit = _compute_psit(gfile)
    psi = np.linspace(ssimag, ssibry, len(psit))
    from scipy.interpolate import interp1d
    fx = interp1d(psit, psi)
    return fx(x)

def npsi2npsit(gfile, x, func = False):
    '''
    convert poloidal to toroidal flux
    '''
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")

    if x>=1.0: return 1.
    if x<=0.0: return 0.
    psit = _compute_npsit(gfile)
    psi = np.linspace(0., 1., len(psit))
    from scipy.interpolate import interp1d
    fx = interp1d(psi, psit)
    if func: return fx
    return fx(x)

def npsit2npsi(gfile, x, func = False):
    '''
    convert toroidal flux to poloidal flux
    '''
    ssimag = gfile.get_contents("table","ssimag")
    ssibry = gfile.get_contents("table","ssibry")

    psit = _compute_npsit(gfile)
    psi = np.linspace(0., 1., len(psit))
    from scipy.interpolate import interp1d
    fx = interp1d(psit, psi)
    if func: return fx
    return fx(x)


def find_flux_surface(gfile, npsi, force_ccw=False, force_cw=False):
    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")

    psi = npsi2psi(gfile, npsi)
    path = find_psi_contour(rgrid, zgrid, psirz, rmaxis, zmaxis, psi)

    if force_ccw:
         r = path[:, 0]- rmaxis
         z = path[:, 1]- zmaxis
         th = np.arctan2(z, r)
         dth = th[1:] - th[:-1]
         if np.sum(dth < 0) > np.sum(dth > 0):
             path = np.flip(path, 0)
    if force_cw:             
         r = path[:, 0]- rmaxis
         z = path[:, 1]- zmaxis
         th = np.arctan2(z, r)
         dth = th[1:] - th[:-1]
         if np.sum(dth < 0) > np.sum(dth > 0):
             path = np.flip(path, 0)

    return path, psi

def npsi2any(gfile, x, unit = None):
    if unit == 'rho':
        return npsi2rho(gfile, x)
    elif unit == 'r1':
        return float(npsi2r1(gfile, x))
    elif unit == 'npsit':
        return float(npsi2npsit(gfile, x))
    elif unit == 'npsit-sqrt':
        return np.sqrt(npsi2npsit(gfile, x))
    elif unit == 'npsi-sqrt':
        return np.sqrt(x)
    else:
        return x

'''
flux coordinate
'''
def compute_theta(gfile, npsi = 0, path = None, method = 'straight_field_line'):
    '''
    compute counter path of npsi and theta on the
    path.
       method = 'straight_field_line'
                'equal_arc_length'
    path starts from outer mid-plane and rotate magnetic
    axis anti-clockwise and has a dimension of [:,2]

    ! both path and theta is NOT cyclic (2016 01 20)
    '''
    def find_cut(path, rmaxis, zmaxis):
        xx = path[:, 0]-rmaxis
        yy = path[:, 1]-zmaxis
        angle = np.arctan2(yy, xx)
        for i in range(len(angle)):
            a2 = np.roll(angle, i)
            if a2[0] >= 0 and a2[-1] < 0:
                return i
            
        print(angle)
        zz = len(path[:,0])
        if path[-2,1] < zmaxis and path[0,1] >= zmaxis:
            return 0
        for k in range(zz-1):
            km = k-1
            if path[km,1] < zmaxis and path[k,1] >= zmaxis:
                return k+1

    import numpy as np
    from scipy.interpolate import interp2d, interp1d

    rgrid = gfile.get_contents("table","rgrid")
    zgrid = gfile.get_contents("table","zgrid")
    psirz = gfile.get_contents("table","psirz")
    fpol =  gfile.get_contents("table","fpol")
    zmaxis = gfile.get_contents("table","zmaxis")
    rmaxis = gfile.get_contents("table","rmaxis")

    if path is None:
        path, psi0 = find_flux_surface(gfile, npsi, force_ccw=True)
        #rotate array so that cut happesn at low field side
        if (path[0,0] == path[-1, 0] and
            path[0,1] == path[-1, 1]):
            path = path[:-1,:]            
        icut = find_cut(path, rmaxis, zmaxis)
        path = np.roll(path, icut, 0)

        '''
        if path[icut, 0] < rmaxis:
            path = np.flipud(path)
            icut = find_cut(path, rmaxis, zmaxis)

        path = path[:-1,:]
        path = np.roll(path, -icut, 0)
        '''
        # insert outer midplane 

        fpsi = interp2d(rgrid, zgrid, psirz)
        psimid = np.array([fpsi(r, zmaxis) for r in rgrid if r > rmaxis])
        rmid = np.array([r for r in rgrid if r > rmaxis])
        f = interp1d(psimid.flatten(), rmid.flatten())
        path = np.vstack(([f(psi0), zmaxis], path, [f(psi0), zmaxis]))

        # path circulate anti-clockwise around magnetic axis
        if path[1,1] < path[0,1]:   # z[1] < z[0]
            path = np.array([y for y in reversed(path)])

    # comput magnetic field on path
    f = interp1d(np.linspace(0., 1., len(fpol)), fpol)
    fpol = f(npsi) 
 
    R, Z = np.meshgrid(rgrid, zgrid) 
    dr = rgrid[1]-rgrid[0]
    dz = zgrid[1]-zgrid[0]
    dpsidz, dpsidr = np.gradient(psirz)
    br = interp2d(rgrid, zgrid, -dpsidz/dz/R)
    bz = interp2d(rgrid, zgrid, dpsidr/dr/R)

    br = np.array([br(x, y) for x, y in zip(path[:,0], path[:,1])]).flatten()
    bz = np.array([bz(x, y) for x, y in zip(path[:,0], path[:,1])]).flatten()
#    bp = np.array([np.sqrt(br(x, y)**2+bz(x, y)**2)  for x, y in zip(path[:,0], path[:,1])]).flatten()
    bp = np.sqrt(br*br + bz*bz)
    bt = np.array([fpol/x  for x, y in zip(path[:,0], path[:,1])])

    # integrate theta on path    
    dlsq = (path[1:,0] - path[:-1,0])**2 + (path[1:,1] - path[:-1,1])**2
    dlsq2 = (path[-1,0] - path[0,0])**2 + (path[-1,1] - path[0,1])**2
    #dlsq = np.hstack((dlsq, [dlsq2]))

    if method == 'straight_field_line':
        x_half = (path[1:,0] + path[:-1,0])/2.
        bp_half = (bp[1:] + bp[:-1])/2.
        bt_half = (bt[1:] + bt[:-1])/2.
        print(dlsq.shape, bt_half.shape, bp_half.shape, x_half.shape)
        theta = np.hstack((0, np.cumsum(np.sqrt(dlsq)*bt_half/bp_half/x_half)))
        theta = theta/theta[-1]*2.*np.pi
        #theta  = theta[:-1]        
    elif method == 'equal_arc_length':
        theta = np.hstack((0, np.cumsum(np.sqrt(dlsq))))
        theta = theta/theta[-1]*2.*np.pi
        #theta  = theta[:-1]
    else:
        raise ValueError('unknown method option')


    return path, theta, bt, bz, br

def br_bz_bt2zeta_eta_xi(path, br, bz, bt):
    '''
    br, bz, bt is 1D array
    unit vector for zeta, eta, xi direction

    note : it does not return a covariant/contravariant basis
    '''
    brtz = np.transpose(np.vstack((br, bt, bz)))
    zeta = brtz/np.transpose(np.vstack([np.sqrt(np.sum(brtz**2, 1))]*3))

    bp = np.transpose(np.vstack((br, [0]*len(bz), bz)))
    bp = bp/np.transpose(np.vstack([np.sqrt(np.sum(bp**2, 1))]*3))
#    bp = bp/np.sqrt(np.sum(bp**2))  # unit vector in the poloidal field direction

    # unit vector in the poloidal field direction
    bp2D = bp[:, [0, 2]]
    # approximately this should work?
    if np.sum((path[1:] - path[:-1])*bp2D[1:])< 0:
       e_theta_hat = -bp ## unit vector in theta
    else:
        e_theta_hat = bp 
    # perpendicular to flux surface going outward
    xi = np.transpose(np.vstack([e_theta_hat[:,1], -e_theta_hat[:,0], [0]*len(bz)]))

    # unit vector in the toroidal field direction
    e_phi_hat =  np.transpose(np.vstack([[0]*len(bz), [1.]*len(bz), [0.]*len(bz)]))

    ### eta is third direction of (zeta, eta, xi) makes right hand 
    eta = np.cross(zeta, xi)     

    ### pitch angle is angle of zeta on e_phi, e_theta plane 
    cos = np.sum(zeta*e_phi_hat, 1)     # cos(pitch angle)
    sin = np.sum(zeta*e_theta_hat, 1)   # sins(pitch angle)

#    print np.sqrt(cos**2 + sin**2)
    mu = np.arctan2(sin, cos)
    return zeta, eta, xi, mu

from scipy.integrate import simps
class fit_func(object):
    def __init__(self, coeff):
        self.coeffs = np.array(coeff, copy=False)

    def __call__(self, new_angle):
       new_angle = np.atleast_1d(new_angle)
       for i, ab in enumerate(self.coeffs):
           if i == 0:
              new_r = np.sin(i*new_angle)*ab[0] 
              new_r = new_r + np.cos(i*new_angle)*ab[1] 
           else:
              new_r = new_r + np.sin(i*new_angle)*ab[0] 
              new_r = new_r + np.cos(i*new_angle)*ab[1] 
       return new_r
   
        
def fit_boundary(gfile = None, path = None, plot = False, 
                 npsi = 0.995, method='straigh_field_line',
                 fit='spline', maxorder=-1, verbose=True):
    ''''
    fit boundary shape by fourier serious

    f : function to compute R for geometrical theta
    g : function to compute the geometrical theta from flux coordinate
        theta
    >>> f, g, theta0, r, R0, Z0 = fit_boundary(gfile, 
                                               plot=True, 
                                               npsi=0.7, 
                                               method='equal_arc_length')
    >>> tt = g(theta);R = f(tt)
    >>> figure();plot(R*np.cos(tt) + R0, R*np.sin(tt) + Z0)
    '''
    def ft(y, x, n):
       d = x[-1] - x[0]
       dx = np.gradient(x)

       return (simps(y*np.sin(n*x), x=x)/d, 
               simps(y*np.cos(n*x), x=x)/d)

    def cost_func(x, *params):
        '''
        params = sin_1, sin_2, sin_3, ...,  cos_0, cos_1, ....
        '''
        params = [0] + list(params)
        coeffs = np.array(params).reshape(-1,2)
        for i, ab in enumerate(coeffs):
           if i == 0:
              new_r = np.sin(i*x)*ab[0] 
              new_r = new_r + np.cos(i*x)*ab[1] 
           else:
              new_r = new_r + np.sin(i*x)*ab[0] 
              new_r = new_r + np.cos(i*x)*ab[1] 
        return new_r

    if path is None:
        path, theta, bt, bz, br = compute_theta(gfile, npsi, method=method)

    
    if (np.sqrt((path[0,0] - path[-1,0])**2 +
                (path[0,1] - path[-1,1])**2)) < 1e-6:
         ## un-cyclic if it is
         #print("DOING THIS")
         path = path[:-1, :]
         theta = theta[:-1]
    if (np.sqrt((path[0,0] - path[-1,0])**2 +
                (path[0,1] - path[-1,1])**2)) < 1e-6:
         #print("DOING THIS")        
         ## un-cyclic if it is
         path = path[:-1, :]
         theta = theta[:-1]

    #R0 = (np.max(path[:,0])+np.min(path[:,0]))/2
    #Z0 = (np.max(path[:,1])+np.min(path[:,1]))/2
    R0 = gfile.get_contents("table","rmaxis")    
    Z0 = gfile.get_contents("table","zmaxis")
    theta0 = np.unwrap(np.arctan2(path[:,1]-Z0, path[:,0]-R0))

    r = np.sqrt((path[:,0]-R0)**2 + (path[:,1]-Z0)**2)
    if theta0[1] < theta0[0]: 
        theta0 = np.flipud(theta0)
        r  = np.flipud(r)

    idx = np.where(theta0 < -np.pi)[0]
    if len(idx) > 0:
        k = idx[-1]+1
        theta0 = np.hstack((theta0[k:], theta0[:k]+2*np.pi)).flatten()
        r  = np.hstack((r[k:], r[:k])).flatten()

    ## make it cyclic again
    theta0 = np.hstack((theta0, [theta0[0]+2*np.pi])).flatten()
    theta = np.hstack((theta, [theta[0]+2*np.pi])).flatten()    
    r     = np.hstack((r, r[0])).flatten()

    if plot:
        from ifigure.interactive import figure
        v = figure(100)
        v.nsec(2)
        v.plot(theta0, r, 'ro')

        
    if fit == 'spline':
        f = CubicSpline(theta0, r, bc_type='periodic')
        if plot:    
            v.plot(theta0, f(theta0))
    elif fit == 'fourier':
        errors = []
        coeffs = []
        maxorder = min([len(theta0)//2, 15]) if maxorder ==-1 else maxorder
        orders = list(range(1, maxorder))
        
        delta_min = np.mean(np.abs(np.gradient(r)))
        if verbose:
            print('delta_min', delta_min)
        
        theta00 = np.linspace(0, 2*np.pi, 100)        
        for order in orders:
            p0 = np.zeros(2*order-1)
            p0[0] = 1
            ret = curve_fit(cost_func, theta0, r, p0=p0)
            coeff = np.array([0] + list(ret[0])).reshape(-1, 2)
            errors.append(np.sum((cost_func(theta0, *ret[0]) - r)**2))
            coeffs.append(coeff)
            max_error = np.max(np.sqrt((cost_func(theta0, *ret[0]) - r)**2))


            fitted = cost_func(theta00, *ret[0])
            dfitted = np.diff(fitted)
            n_local_minmax = np.sum(dfitted[:-1]*dfitted[1:] < 0)
            ddfitted = np.diff(dfitted)
            n_inflection_points = np.sum(ddfitted[:-1]*ddfitted[1:] < 0)
            if verbose:
                print(max_error, n_local_minmax, n_inflection_points)
            #if n_inflection_points > 4:
            #    errors = errors[:-1]
            #    coeffs = coeffs[:-1]
            #    break                
            #if n_local_minmax > 4:
            #    errors = errors[:-1]
            #    coeffs = coeffs[:-1]
            #    break

            if max_error < delta_min:
                break
        '''
        coeff = [ft(r, theta0, i) for i in range(40)]
        errors = [np.sum((fit_func(coeff[:i+1])(theta0) - r)**2) for i in range(30)]
        '''
        idx = np.argmin(errors)
        if verbose:        
            print('minimum error found when length = ', idx)
        #f = fit_func(coeff[:idx+1])
        f = fit_func(coeffs[idx])
        delta = np.abs(f(theta0) - r)
        if verbose:                
            print('maximum error and average error = ', np.max(delta), np.mean(delta))
        if plot: 
            theta00 = np.linspace(0, 2*np.pi, 100)
            v.plot(theta00, f(theta00))
        if plot:
            v.isec(1)
            v.plot(errors)
    else:
        assert False, "unknown fitting metod:"+ fit

    from scipy.interpolate import interp2d, interp1d
    g = interp1d(theta, theta0)
    
    return f, g, theta0, r, R0, Z0

def plot_theta(gfile, method = 'straight_field_line',rho = [0.1, 0.99], **kargs):
    from scipy.interpolate import interp1d
    import numpy as np
    npsis = np.linspace(rho[0], rho[1], 15)**2
    thetas = np.linspace(0, 2*np.pi, 60)

    resx = []
    resy = []
    for npsi in npsis:
        path, theta, bt, bz, br = compute_theta(gfile, npsi, method = method)
        fx = interp1d(theta, path[:, 0])
        fy = interp1d(theta, path[:, 1])
        x = np.array([fx(th) for th in thetas])
        y = np.array([fy(th) for th in thetas])
        resx.append(x)
        resy.append(y)

    x = np.vstack(resx)
    y = np.vstack(resy)

    from ifigure.interactive import figure
    v = figure();
    v.plot(x,y, **kargs)
    v.plot(np.transpose(x), np.transpose(y), **kargs)

    return x, y, v

def fit_flux_coords(gfile,
                    method = 'straight_field_line',
                    rho = [0.1, 0.99],
                    plot=True,
                    verbose=True,
                    rsegs=15,
                    psegs=128,
                    **kargs):
    '''
    plot result of fit_boundary
    '''
    from scipy.interpolate import interp1d
    import numpy as np
    npsis = np.linspace(rho[0], rho[1], rsegs)**2
    thetas = np.linspace(0, 2*np.pi, psegs+1)[:-1]

    resx = []
    resy = []

    for npsi in npsis:
        if npsi > 0.25:
           f, g, tetha0, r, R0, Z0 = fit_boundary(gfile, npsi=npsi,
                                                  method=method,
                                                  fit='spline',
                                                  verbose=verbose)
        else:
           f, g, tetha0, r, R0, Z0 = fit_boundary(gfile, npsi=npsi,
                                                  method=method,
                                                  fit='fourier',
                                                  maxorder=4,
                                                  verbose=verbose)           
           
        th = g(thetas)
        r =  f(th)
        x = r*np.cos(th) + R0
        y = r*np.sin(th) + Z0
        
        resx.append(x)
        resy.append(y)

    x = np.vstack(resx)
    y = np.vstack(resy)

    if plot:
        from ifigure.interactive import figure
        v = figure();
        v.plot(x,y, **kargs)
        v.plot(np.transpose(x), np.transpose(y), **kargs)

    npsis = np.hstack([0, npsis])
    return x, y, R0, Z0, npsis

def non_conforming_flux_coords(gfile,
                               method = 'straight_field_line',
                               rho = [0.1, 0.99],
                               plot=True,
                               verbose=True,
                               rsegs=16,
                               psegs=128,
                               refine = 4,
                               **kargs):
    
    x, y, R0, Z0, npsis = fit_flux_coords(gfile,
                                          method=method,
                                          rho=rho,
                                          rsegs=rsegs*refine+1,
                                          psegs=psegs*refine,
                                          verbose=False,
                                          plot=False)
    
    average_dist = np.mean(np.sqrt(np.diff(x, 1)**2 + np.diff(y, 1)**2), 1)
    
    max_exp = int(np.log(average_dist[-1]/average_dist[0])/np.log(2))

    if plot:
        from ifigure.interactive import figure
        v = figure();
        v.plot(x[0::refine,:],y[0::refine], "k-")
        v.plot(np.transpose(x[:, 0::refine]), np.transpose(y[:,0::refine]), "k-")

    seg = 8
    xy_pairs = [(np.array([R0,]),
                 np.array([Z0,]),)]
    for i in np.arange(rsegs*refine+1)[0::refine]:
        exponent = int(np.round(np.log(average_dist[i]/average_dist[0])/np.log(2)))

        n_pol = seg*2**exponent # number of element in poloidal dir.
        if n_pol > psegs:
            n_pol = psegs
        if n_pol > x.shape[1]:
            step = 1
        else:
            step = x.shape[1]//n_pol
        xx = x[i, 0::step]
        yy = y[i, 0::step]

        xy_pairs.append((xx, yy))
        
        v.plot(np.transpose(x), np.transpose(y), **kargs)
    for xx, yy in xy_pairs:
        v.plot(xx,yy, "o")
        
    return x, y, xy_pairs, npsis
    





