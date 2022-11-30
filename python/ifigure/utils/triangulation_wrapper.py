import numpy as np
from scipy.spatial import Delaunay
from matplotlib.tri import Triangulation

use_mpl_tri = False


def tri_args(x, y, _tri=None):
    #    use_mpl_tri = False
    if use_mpl_tri:
        if _tri is None:
            _tri = Triangulation(x, y)
        args = [x, y, _tri.triangles]
    else:
        if _tri is None:
            _tri = delaunay(x, y)

        args = [x.flatten(), y.flatten(), _tri]

    return args, _tri


def delaunay(x, y):
    '''
    tri = delaunay(x, y)
    '''
    if len(x.shape) == 1 and len(y.shape) == 1:
        _tri = Delaunay(np.hstack((x.reshape(-1, 1),
                                   y.reshape(-1, 1),))).simplices.copy()

    elif len(x.shape) == 2 and len(y.shape) == 2:
        xx = np.arange(x.shape[1])
        yy = np.arange(x.shape[0])
        XX, YY = np.meshgrid(xx, yy)
        _tri = Delaunay(np.hstack((XX.flatten().reshape(-1, 1),
                                  YY.flatten().reshape(-1, 1),))).simplices.copy()
    else:
        import warning
        warning.warn(
            "triangulation input data has ndim > 2 or x and y have differnt ndim. Data is flattened first")
        _tri = Delaunay(np.hstack((x.flatten().reshape(-1, 1),
                                   y.flatten().reshape(-1, 1),))).simplices.copy()

    return _tri


def mask_inside(x, y, tri, edge, mask=None, op=np.logical_or):
    '''
    omit tringles 
    edge = (:, 2)
    '''
    pmid = np.transpose(np.vstack((x[tri].mean(axis=1), y[tri].mean(axis=1))))

    from ifigure.utils.geom import path_contain

    mask2 = [path_contain(edge, xy, check=False) for xy in pmid]
    if mask is not None:
        mask2 = op(mask, mask2)
    return np.array(mask2)


def mask_outside(x, y, tri, edge, mask=None, op=np.logical_or):
    pmid = np.vstack((x[tri].mean(axis=1), y[tri].mean(axis=1)))

    mask2 = np.logical_not(mask_inside(x, y, tri, edge,
                                       mask=None, op=op))
    if mask is not None:
        mask2 = op(mask, mask2)
    return np.array(mask2)


def mask_skew(x, y, tri, th=5, mask=None, op=np.logical_or, inv=False):
    ddd = np.vstack((np.sqrt((x[tri][:, 0] - x[tri][:, 1])**2+(y[tri][:, 0]-y[tri][:, 1])**2), np.sqrt((x[tri][:, 0] - x[tri][:, 2])
                                                                                                       ** 2+(y[tri][:, 0]-y[tri][:, 2])**2), np.sqrt((x[tri][:, 1] - x[tri][:, 2])**2+(y[tri][:, 1]-y[tri][:, 2])**2)))

    sk = np.max(ddd, 0)/np.min(ddd, 0)
    if inv:
        mask2 = sk < th
    else:
        mask2 = sk > th
    if mask is not None:
        mask2 = op(mask, mask2)
    return np.array(mask2)


def get_area(x, y, tri):
    ddd = (x[tri][:, 0]-x[tri][:, 1])*(y[tri][:, 0]-y[tri][:, 2]) - \
        (x[tri][:, 0]-x[tri][:, 2])*(y[tri][:, 0]-y[tri][:, 1])
    return np.abs(ddd)


def mask_area(x, y, tri, th=5, mask=None, op=np.logical_or, inv=False):
    ddd = get_area(x, y, tri)
    if inv:
        mask2 = ddd < th
    else:
        mask2 = ddd > th
    if mask is not None:
        mask2 = op(mask, mask2)
    return np.array(mask2)
