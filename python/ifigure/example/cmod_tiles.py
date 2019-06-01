
import piscope
import os
from scipy.io.idl import readsav
from ifigure.utils.vctr_array import expand_vctr3d
from ifigure.interactive import figure, threed, plot, hold


def read_tile_data(list=False):
    dir = os.path.dirname(piscope.__file__)
    dir = os.path.dirname(dir)
    file = os.path.join(dir, 'example', 'cmod_tile_data.sav')
    data = readsav(file)
    return expand_vctr3d(data['xyzseg'], data['nseg'], data['lseg'], list=list)


def plot_tiles():
    '''
    line plot of tile data
    '''
    x, y, z = read_tile_data()
    figure()
    threed('on')
    plot(x, y, z)


def plot_tiles2():
    x, y, z = read_tile_data()
    figure()
    threed('on')
    plot(x, y, z, facecolor=[1, 0, 0, 1])


def plot_tiles3():
    x, y, z = read_tile_data(list=True)
    figure()
    threed('on')
    hold('on')
    for k in range(100):
        m = k+100
        plot(x[m], y[m], z[m], facecolor=[1, 0, 0, 1])
