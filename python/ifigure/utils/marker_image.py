from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.transforms import Bbox
import matplotlib.patches as patches

import numpy as np


def marker_image(path, size, trans,
                 edgecolor='k', facecolor='b',
                 edgewidth=1.0):

    fig = Figure(figsize=((size*2+1)/72., (size*2+1)/72.), dpi=72)

    # fig.set_edgecolor([1,1,1,0])
    # fig.set_facecolor([1,1,1,0])
    fig.set_edgecolor([0, 0, 0, 0])
    fig.set_facecolor([0, 0, 0, 0])
    fig.patch.set_alpha(0.0)
    fig.clf()
    fig.frameon = False
    ax = fig.add_subplot(111)
    ax.set_position((0, 0, 1, 1))
    ed = ax.transAxes.transform([(0, 0), (1, 1)])

    path = trans.transform_path(path)
    patch = patches.PathPatch(path, facecolor=facecolor, edgecolor=edgecolor,
                              lw=edgewidth)
    ax.patch.set_facecolor([0, 0, 0, 0])
    ax.patch.set_edgecolor([0, 0, 0, 0])
    ax.patch.set_alpha(0.0)
    ax.add_patch(patch)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.tick_params(length=0)

    ax.set_axis_off()
    canvas = FigureCanvasAgg(fig)
    buff, size = canvas.print_to_buffer()

    im = np.frombuffer(buff, np.uint8).reshape(size[1], size[0], -1)
    #idx = np.where(im[:,:,-1] == 0)
    #im[:,:,0][idx] = 0
    #im[:,:,1][idx] = 0
    #im[:,:,2][idx] = 0
    return im
