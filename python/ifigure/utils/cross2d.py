#
#  2d version of cross 
#
__all__ = ['cross2d']

def cross2d(x, y):
    return x[..., 0] * y[..., 1] - x[..., 1] * y[..., 0]
