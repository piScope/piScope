import os
import ifigure


def base_dir():
    path = os.path.dirname(ifigure.__path__[0])
    base = os.path.dirname(path)
    return base


def bin_dir():
    return os.path.join(base_dir(), 'bin')
