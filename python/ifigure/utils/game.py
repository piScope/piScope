from matplotlib.patches import Rectangle
import wx
import numpy as np
from matplotlib.patches import PathPatch


def draw_field(fpage):
    figure = fpage._artists[0]

    a = 1./(2**(0.5))
    b = 1.0
    d = 1./(11*b + 10 * a)

    step = (2*a + 2*b)*d
    xy1 = [((a+b)*d+step*x, 0) for x in range(5)]
    xy2 = [(step*x, (a+b)*d) for x in range(6)]

    for m in range(6):
        for xy in xy1:
            hlp = Rectangle((xy[0], xy[1]+m*step), b*d, b*d, facecolor='r',
                            figure=figure, transform=figure.transFigure)
            figure.patches.append(hlp)
            hlp = Rectangle((xy[1]+m*step, xy[0]), b*d, b*d, facecolor='k',
                            figure=figure, transform=figure.transFigure)
            figure.patches.append(hlp)
    viewer = wx.GetApp().TopWindow.find_bookviewer(fpage.get_figbook())
    viewer.draw()


def draw_octagon(fpage, xy, d):
    import matplotlib.path as mpath
    Path = mpath.Path

    theta = [(22.5 + 45.*x)*np.pi/180 for x in range(8)]
    pathdata = [(Path.MOVETO, (xy[0]+d*cos(theta[-1]),
                               xy[1]+d*sin(theta[-1])), 0)]
    for t in theta:
        pathdata.append((Path.LINETO,  (xy[0]+d*cos(t),
                                        xy[1]+d*sin(t)), 0))
