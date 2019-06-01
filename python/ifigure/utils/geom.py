from __future__ import print_function
import numpy as np
import sys


def XY2pts(X, Y):
    if not isinstance(X, np.ndarray):
        X = np.array(X)
    if not isinstance(Y, np.ndarray):
        Y = np.array(Y)

    pts = np.hstack((X.flatten()[:, np.newaxis],
                     Y.flatten()[:, np.newaxis]))
    return pts


def ensure_cyclic(pts):
    if pts[0, 0] != pts[-1, 0] or pts[0, 1] != pts[-1, 1]:
        return np.vstack((pts, pts[0]))
    return pts


def norm_path(x):
    return np.sqrt(np.sum(x**2, 1))


def dot_path(x, y):
    return np.sum(x*y, 1)


def cross_path(x, y):
    d = x*np.fliplr(y)
    return d[:, 0] - d[:, 1]


def path_len(path):
    d = path[1:]-path[:-1]
    dd = np.sqrt(np.sum(d**2, 1))
    return np.sum(dd)


def check_inside(rec, x, y):
    ret = True

    if rec[0] > x:
        ret = False
    if rec[0]+rec[2] < x:
        ret = False
    if rec[1] > y:
        ret = False
    if rec[1]+rec[3] < y:
        ret = False
    return ret


def check_boxoverwrap(box1, box2):
    xo = False
    yo = False

    if ((box1[0] < box2[0] and
         box1[1] > box2[0]) or
        (box1[0] < box2[1] and
         box1[1] > box2[1])):
        xo = True
    if ((box1[2] < box2[2] and
         box1[3] > box2[2]) or
        (box1[2] < box2[3] and
         box1[3] > box2[3])):
        yo = True

    return xo and yo


def calc_scale_r(rec, old_rect):
    scale = [(rec[1]-rec[0])/(old_rect[1]-old_rect[0]),
             0.,
             0.,
             (rec[3]-rec[2])/(old_rect[3]-old_rect[2]),
             rec[0]-old_rect[0],
             rec[2]-old_rect[2]]
    return scale


def calc_scale(rec, old_rect):

    scale = [(rec[1]-rec[0])/(old_rect[1]-old_rect[0]),
             0.,
             0.,
             (rec[3]-rec[2])/(old_rect[3]-old_rect[2])]

    if old_rect[1] == old_rect[0]:
        scale[0] = 1
    if old_rect[3] == old_rect[2]:
        scale[3] = 1
    scale = scale + [rec[0] - scale[0]*old_rect[0],
                     rec[2] - scale[3]*old_rect[2]]
    return scale


def scale_rect(rec, scale):
    # this should be called scale area
    # rect is [x0, x1, y0, y1]
    #  [scale[0], scale[1]] x + scale[4]
    #  [scale[2], scale[3]] y + scale[5]
    return [scale[0]*rec[0] + scale[1]*rec[2] + scale[4],
            scale[0]*rec[1] + scale[1]*rec[3] + scale[4],
            scale[2]*rec[0] + scale[3]*rec[2] + scale[5],
            scale[2]*rec[1] + scale[3]*rec[3] + scale[5], ]


def scale_rect_r(rec, scale):
    # this should be called scale area
    # rect is [x0, x1, y0, y1]
    dx = rec[1]-rec[0]
    dy = rec[3]-rec[2]
    return [rec[0]+scale[4],
            rec[0]+dx*scale[0]+scale[4],
            rec[2]+scale[5],
            rec[2]+dy*scale[3]+scale[5]]


def transform_point(t, x, y):
    v = t.transform(np.array([[x, y]]))
    return v[0, 0], v[0, 1]


def area_intersection(p1, p2, area, internal_only=False,
                      closed=True, once=False, return_idx=False):
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
    q0 = q2 - q1
    for k in range(len(area[0])-1):
        #      q1 = np.array([x_a[k], y_a[k]])
        #      q2 = np.array([x_a[k+1], y_a[k+1]])
        #      q  = q2 - q1
        q = q0[k]
        m = np.matrix((-p, q))
        if np.linalg.cond(m) < 1./sys.float_info.epsilon:
            #          ans =  np.array((p1 - q1)*(np.matrix((-p, q))**-1)).flatten()
            ans = np.array((p1 - q1[k])*(np.matrix((-p, q))**-1)).flatten()
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
                if once:
                    break

    if return_idx:
        return x, y, idx
    else:
        return x, y


def area_intersection_x(x1, x2, y0, area, internal_only=False,
                        once=False, debug=False, return_idx=False):
    '''
    search all possible crosspoint with area on the line connecting p1 and p2
    if internal_only, crosspoint should be between p1 and p2
    p1, p2 : 2D points (x, y)
    area   : [[x1, x2, x3, x4,,,,], [y1, y2, y3,,,,]]
    '''
    x_a = area[0]
    y_a = area[1]

    p1 = np.array([x1, y0])
    p2 = np.array([x2, y0])

    p = p2 - p1

    x = []
    y = []
    idx = []
    for k in range(len(area[0])-1):
        if (y_a[k]-y0)*(y_a[k+1]-y0) > 0:
            continue
        q1 = np.array([x_a[k], y_a[k]])
        q2 = np.array([x_a[k+1], y_a[k+1]])
        q = q2 - q1
        m = np.matrix((-p, q))
        if np.linalg.cond(m) < 1./sys.float_info.epsilon:
            ans = np.array((p1 - q1)*(np.matrix((-p, q))**-1)).flatten()
        else:
            continue
        if debug:
            print(q1, q2, ans)
        if 0. < ans[-1] <= 1.:
            if not internal_only or (internal_only and
                                     (0. < ans[0] <= 1.)):
                x.append((q1 + ans[1]*q)[0])
                y.append((q1 + ans[1]*q)[1])
                idx.append(k + ans[1])
                if once:
                    break
    if return_idx:
        return x, y, idx
    else:
        return x, y


def area_intersection_y(x0, y1, y2, area, internal_only=False,
                        once=False, debug=False, return_idx=False):
    '''
    search all possible crosspoint with area on the line connecting p1 and p2
    if internal_only, crosspoint should be between p1 and p2
    p1, p2 : 2D points (x, y)
    area   : [[x1, x2, x3, x4,,,,], [y1, y2, y3,,,,]]
    '''
    x_a = area[0]
    y_a = area[1]
    p1 = np.array([x0, y1])
    p2 = np.array([x0, y2])

    p = p2 - p1

    x = []
    y = []
    idx = []
    for k in range(len(area[0])-1):
        if (x_a[k] - x0)*(x_a[k+1] - x0) > 0:
            continue
        q1 = np.array([x_a[k], y_a[k]])
        q2 = np.array([x_a[k+1], y_a[k+1]])
        q = q2 - q1
        m = np.matrix((-p, q))
        if np.linalg.cond(m) < 1./sys.float_info.epsilon:
            ans = np.array((p1 - q1)*(np.matrix((-p, q))**-1)).flatten()
        else:
            continue
        if debug:
            print(ans)
        if 0. < ans[-1] <= 1.:
            if not internal_only or (internal_only and
                                     (0. < ans[0] <= 1.)):
                x.append((q1 + ans[1]*q)[0])
                y.append((q1 + ans[1]*q)[1])
                idx.append(k + ans[1])
                if once:
                    break
    if return_idx:
        return x, y, idx
    else:
        return x, y


def path_cut(path, p1, p2):
    '''
    cut path by a line connecting p1 and p2
    '''
    p1 = np.array(p1)
    p2 = np.array(p2)
    p = p2 - p1

    x = []
    y = []
    for k in range(len(path)-1):
        q1 = path[k]
        q2 = path[k+1]
        q = q2 - q1
        m = np.matrix((-p, q))
        if np.linalg.cond(m) < 1./sys.float_info.epsilon:
            ans = np.array((p1 - q1)*(np.matrix((-p, q))**-1)).flatten()
        else:
            continue

        if (0 < ans[-1] <= 1) and (0 < ans[0] <= 1):
            xc, yc = q1 + ans[1]*q
            break
    else:
        return [path, ]
    return [np.vstack((path[:k, :], np.array((xc, yc)))),
            np.vstack((np.array((xc, yc)), path[k:, :]))]


def path_contain(path, xy, check=False, cyclic=True):
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
    dx = path[:, 0] - xy[0]
    dy = path[:, 1] - xy[1]
    d1 = np.sqrt(dx[:-1]**2 + dy[:-1]**2)
    d2 = np.sqrt(dx[1:]**2 + dy[1:]**2)

    d = (dx[:-1]*dy[1:] - dx[1:]*dy[:-1])/d1/d2
    dotp = (dx[:-1]*dx[1:] + dy[1:]*dy[:-1])
    if any(np.isnan(d)):
        # when d1, d2 = 0
        return True

    d = np.arcsin(d)
    d[np.logical_and(dotp < 0, d > 0)] = np.pi - \
        d[np.logical_and(dotp < 0, d > 0)]
    d[np.logical_and(dotp < 0, d < 0)] = -np.pi - \
        d[np.logical_and(dotp < 0, d < 0)]

    xxxx = sum(d)
#    print(np.abs(xxxx)/3.14159/2)
#    if check: return d
    if check:
        return np.abs(xxxx)/np.pi/2
    return -0.001 < np.abs(xxxx)-np.pi*2 < 0.001


def calc_area(path, xy=[0., 0.]):
    '''
    calc area inside path
    '''
    import numpy as np
    dx = path[:, 0] - xy[0]
    dy = path[:, 1] - xy[1]
    d1 = np.sqrt(dx[:-1]**2 + dy[:-1]**2)
    d2 = np.sqrt(dx[1:]**2 + dy[1:]**2)

    d = (dx[:-1]*dy[1:] - dx[1:]*dy[:-1])
    return np.abs(np.sum(d)/2.)


def dist_path2xy(path, xy, check=False, return_idx=False):
    '''
    find distance from path to xy and
    the closest point on the path
    '''
    dx = path[:, 0] - xy[0]
    dy = path[:, 1] - xy[1]

    dd = XY2pts(dx, dy)
    dpath = path[1:] - path[:-1]

    #  b cos() = vec(a)*vec(b)/norm(a)
    ddcos = dot_path(-dd[:-1], dpath)/norm_path(dpath)
    norm_dpath = norm_path(dpath)
    norm_dd = norm_path(dd)
    idx = ddcos/norm_dpath

    #  b sin() = vec(a)xvec(b)/norm(a) (this is distance)
    ddsin = np.abs(cross_path(-dd[:-1], dpath)/norm_dpath)
    for k in range(len(idx)):
        if idx[k] < 0.:
            idx[k] = 0
            ddsin[k] = norm_dd[k]
        if idx[k] > 1.:
            idx[k] = 1
            ddsin[k] = norm_dd[k+1]
#      if ddcos[k] < 0:
#           idx[k] = 0.
#           ddsin[k] = norm_dd[k]
#      elif ddcos[k] > norm_dpath[k]:
#           idx[k] = 1.
#           ddsin[k] = norm_dd[k+1]
    min_k = np.argmin(ddsin)
    x, y = path[min_k] + (path[min_k+1]-path[min_k])*idx[min_k]

    if return_idx:
        return ddsin[min_k], x, y, min_k + idx[min_k]
    else:
        return ddsin[min_k], x, y


def s_path(path, idx=None):
    '''
    return distance along the path
    if idx is give, it returns the s at idx. idx
    can be float.
    '''
    norm_dpath = norm_path(path[1:] - path[:-1])
    cumsum = np.cumsum(norm_dpath)
    if idx is None:
        return cumsum
    else:
        lidx = int(idx)
        didx = idx - lidx
        return cumsum[lidx] + norm_dpath[lidx] * didx


'''
def connect_pairs(ll):
    d = {}

    flags = [False,]*len(ll)
    count = 1
    d[ll[0][0]] = ll[0][1]
    flags[0] = True
    while count < len(ll):
       for k, f in enumerate(flags):
           if f: continue
           l = ll[k]
           if l[0] in d.keys():
               d[l[1]] = l[0]
               flags[k] = True
               count = count + 1
           elif l[1] in d.keys():
               d[l[0]] = l[1]
               flags[k] = True
               count = count + 1               
           else:
               pass
    key = d.keys()[0]
    pt = [key]
    lmax = len(d.keys())
    while d[key] != pt[0]:
        pt.append(d[key])
        key = d[key]
        if len(pt) > lmax: break
    if d[key] == pt[0]: pt.append(pt[0])

    return pt
'''


def connect_pairs(ll):
    '''
    connect paris of indices to make a loop

    (example)
    >>> idx = array([[1, 4],  [3, 4], [1,2], [2, 3],])
    >>> connect_pairs(idx)
    [[1, 2, 3, 4, 1]]
    '''
    if not isinstance(ll, np.ndarray):
        ll = np.array(ll)

    idx = np.where(ll[:, 0] > ll[:, 1])[0]
    t1 = ll[idx, 0]
    t2 = ll[idx, 1]
    ll[idx, 0] = t2
    ll[idx, 1] = t1

    ii = np.vstack([np.arange(ll.shape[0]), ]*2).transpose()
    d = np.ones(ll.shape[0]*ll.shape[1]).reshape(ll.shape)
    from scipy.sparse import csr_matrix, coo_matrix
    m = coo_matrix((d.flatten(), (ii.flatten(), ll.flatten())),
                   shape=(len(ll), np.max(ll+1)))
    mm = m.tocsc()
    ic = mm.indices
    icp = mm.indptr
    mm = m.tocsr()
    ir = mm.indices
    irp = mm.indptr

    def get_start(taken):
        idx = np.where(np.logical_and(np.diff(icp) == 1, taken == 0))[0]
        nz = np.where(np.logical_and(np.diff(icp) != 0, taken == 0))[0]
        if len(nz) == 0:
            return
        if len(idx) > 0:
            #print('Open end found')
            pt = (ic[icp[idx[0]]], idx[0])
        else:
            pt = (ic[icp[nz[0]]], nz[0])
        pts = [pt]
        return pts

    def hop_v(pt):
        ii = pt[1]
        ii = [icp[ii], icp[ii+1]-1]
        next = ic[ii[1]] if ic[ii[0]] == pt[0] else ic[ii[0]]
        return (next, pt[1])

    def hop_h(pt):
        ii = pt[0]
        ii = [irp[ii], irp[ii+1]-1]
        next = ir[ii[1]] if ir[ii[0]] == pt[1] else ir[ii[0]]
        return (pt[0], next)

    def trace(pts):
        loop = [pts[-1][1]]
        while True:
            pts.append(hop_v(pts[-1]))
            # rows.append(pts[-1][0])
            pts.append(hop_h(pts[-1]))
            if pts[-1][1] in loop:
                break  # open ended
            loop.append(pts[-1][1])
            if pts[-1] == pts[0]:
                break
        return loop

    taken = (icp*0)[:-1]
    loops = []
    while True:
        pts = get_start(taken)
        if pts is None:
            break
        loop = trace(pts)
        loops.append(loop)
        taken[loop] = 1

    return loops


def make_loop_idx(loop):
    ''' 
    make indexset array from loop

    (example)
    a = connect_pairs(idx)
    figure()
    solid(v,  make_loop_idx(a[0]))
    '''
    if loop[0] == loop[-1]:
        loop = loop[:-1]
    return np.vstack((loop, np.roll(loop, 1))).transpose()


def find_edges(idxset):
    '''
    find exterior edges of triangulation, but the algorith
    is not limited to triangles.

    idxset is an array defining patch.
    for example :idxset[:, 3] is idx of triangles
    this routine findds edges which appears once
    patch

    '''
    s = idxset.shape
    l = []  # loop
    for i in range(s[-1]-1):
        l.append(idx[:, [i, i+1]])
    l.append(idx[:, [s[-1]-1, 0]])
    c = np.vstack(l)
    from collections import defaultdict
    d = defaultdict(int)
    for i in c:
        d[tuple(np.sort(i))] += 1
    e = [k for k in d if d[k] == 1]

    return e
