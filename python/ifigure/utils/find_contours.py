'''
   find_contours based on scikit-image (marching square alogrith)
'''
import numpy as np
try:
   from skimage import measure
except ImportError:
   assert False, "Can not import skimage. Consider pip install skimage."

def findthem(data, level, xgrid=None, ygrid=None, transpose=True):
    if transpose:
        data = np.transpose(data)
    
    segs = measure.find_contours(data, level)

    ret = []

    if xgrid is not None:
        xx = np.arange(len(xgrid))
    if ygrid is not None:
        yy = np.arange(len(ygrid))

    for s in segs:
        if xgrid is not None:
            s[:, 0] = np.interp(s[:, 0], xx, xgrid)
        if ygrid is not None:
            s[:, 1] = np.interp(s[:, 1], yy, ygrid)
        ret.append(s)

    return ret

class Cntr():
    '''
    this class mimic Cntr in LegacyContour which seems stop working
    with new version of Matplotlib
    '''
    def __init__(self, x, y, z):
        x = np.array(x, copy=False)
        if len(x.shape) == 2:
            x = x[0, :]
        y = np.array(y, copy=False)
        if len(y.shape) == 2:
            y = y[:, 0]
            
        self.x = x
        self.y = y
        self.z = np.transpose(z)
        
    def trace(self, level):
        ret = findthem(self.z,
                       level,
                       xgrid=self.x,
                       ygrid=self.y,
                       transpose=False)

        ret = ret + [None]*len(ret)
        return ret
    
def contour(*args, **kwargs):
    '''
    countour plot using findthem (above).
    mostly meant for testing
    '''
    if len(args) == 3:
        x, y, z = args
    elif len(args) == 1:
        z = args[0]
        x = None
        y = None

    data = np.transpose(z)
    nlevels = kwargs.pop('nlevels', 15)

    from ifigure.interactive import figure

    levels = np.linspace(np.min(z), np.max(z), nlevels)

    v = figure()
    v.update(False)
    for l in levels:
        segs = findthem(data, l, xgrid=x, ygrid=y, transpose=False)
        for s in segs:
            v.plot(s[:,0], s[:,1])
            
    v.update(True)
