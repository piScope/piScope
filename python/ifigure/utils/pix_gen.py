from __future__ import print_function
#
#  a script to produce icon images
#
from ifigure.ifigure_config import plinestyle_list
from ifigure.ifigure_config import linewidth_list
from ifigure.ifigure_config import linestyle_list, linestylenames
from ifigure.ifigure_config import marker_list, markernames
from ifigure.ifigure_config import color_list
from ifigure.ifigure_config import arrowstyle_list
from ifigure.utils.cbook import register_idl_colormaps
from ifigure.ifigure_config import colormap_list
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import base64
from ifigure.ifigure_config import isMPL2
import wx

b64encode = base64.urlsafe_b64encode

def encode(txt):
    return (b64encode(txt.encode())).decode()

##################################################
def generate_colormap():
    dpi = 72
    dpi2 = dpi

    F = plt.figure(num=None, figsize=(2.4, 0.3), dpi=dpi, facecolor='w')
    x = [0, 1, 1, 0, 0]
    y = [1, 1, 0, 0, 1]


    print('### generating colormap palette button ###')
    idl_names = register_idl_colormaps()

    a = np.linspace(0, 1, 256).reshape(1, -1)
    a = np.vstack([a]*20)

    maps = [colormap_list()[0]] + colormap_list() + idl_names
    for map in maps:
        ax = plt.subplot(111)
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.imshow(a, cmap=plt.get_cmap(map), origin='lower')
        filename = 'colormap_'+encode(map)+'.png'
        ed = ax.transAxes.transform([(0, 0), (1, 1)])
        bbox = Bbox.from_extents(
            ed[0, 0]/dpi, ed[0, 1]/dpi, ed[1, 0]/dpi, ed[1, 1]/dpi)
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)
    ##################################################

def generate_arrow():    
    dpi = 72
    dpi2 = dpi/3

    F = plt.figure(num=None, figsize=(0.6, 0.325), dpi=dpi, facecolor='w')
    ax = plt.subplot(111)
    x = [0, 1, 1, 0, 0]
    y = [1, 1, 0, 0, 1]

    ed = ax.transAxes.transform([(0, 0), (1, 1)])
    bbox = Bbox.from_extents(
        (ed[0, 0]+1)/dpi, (ed[0, 1]+1)/dpi, ed[1, 0]/dpi, (ed[1, 1]-2)/dpi)

    print('### generating arrow palette button ###')

    a = np.linspace(0, 1, 256).reshape(1, -1)
    a = np.vstack((a, a))

    for name, style in arrowstyle_list():
        ax.cla()
        ax.tick_params(length=0)
        ax.annotate('', [1, 0.5], xytext=[0, 0.5],
                    arrowprops=dict(arrowstyle=style))
        filename = 'arrow_'+encode(name.encode())+'.png'
        ed = ax.transAxes.transform([(0, 0), (1, 1)])
        bbox = Bbox.from_extents(
            ed[0, 0]/dpi, ed[0, 1]/dpi, ed[1, 0]/dpi, ed[1, 1]/dpi)
        plt.savefig(filename, dpi=dpi, format='png', bbox_inches=bbox)

    ##################################################
def generate_color():
    dpi = 72
    dpi2 = dpi/3

    F = plt.figure(num=None, figsize=(1.2, 0.75), dpi=dpi, facecolor='w')
    ax = plt.subplot(111)
    x = [0, 1, 1, 0, 0]
    y = [1, 1, 0, 0, 1]

    ed = ax.transAxes.transform([(0, 0), (1, 1)])
    bbox = Bbox.from_extents(ed[0, 0]/dpi, ed[0, 1]/dpi,
                             ed[1, 0]/dpi, ed[1, 1]/dpi)

    print('### generating color palette button ###')

    collist = color_list()
    for color in collist:
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.fill(x, y, color=color)
        if color == 'none':
            plt.plot([0, 1], [1, 0], color='red')
        filename = 'color_'+encode(color)+'.png'
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)

    ax.cla()
    ax.tick_params(length=0)
    ax.set_axis_off()
    ax.text(0.5, 0.2, '?', ha='center', fontsize=30)
    filename = 'color_'+encode('other')+'.png'
    plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)

def generate_symbol():
    dpi = 72
    dpi2 = dpi/3
    
    print('### generating symbol palette button ###')
    x = [0, 0.5, 1]
    y = [0.5, 0.5, 0.5]
    for marker, mname in zip(marker_list(), markernames):
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.plot(x, y, marker=marker, linestyle='None',
                 markevery=(1, 2), color='black', markersize=30)
        filename = 'marker_'+encode(str(mname))+'.png'
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)


def generat_linestyle():
    dpi = 72
    dpi2 = dpi/3
    
    print('### generating linestyle palette button ###')
    linestylelist = linestyle_list()

    x = [0, 0.5, 1]
    y = [0.5, 0.5, 0.5]
    for linestyle, lname in zip(linestylelist, linestylenames):
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.plot(x, y, linestyle=linestyle, color='black', linewidth=5)
        filename = 'linestyle_'+encode(str(lname))+'.png'
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)


def generat_linewidth():
    dpi = 72
    dpi2 = dpi

    F = plt.figure(num=None, figsize=(0.4, 0.25), dpi=dpi, facecolor='w')
    ax = plt.subplot(111)

    print('### generating linewidth palette button ###')
    linewidthlist = linewidth_list()
    linewidthlist = ['0.0'] + linewidth_list()


    x = [0, 0.5, 1]
    y = [0.5, 0.5, 0.5]
    ed = ax.transAxes.transform([(0, 0), (1, 1)])
    bbox = Bbox.from_extents(ed[0, 0]/dpi, ed[0, 1]/dpi,
                             ed[1, 0]/dpi, ed[1, 1]/dpi)
    for linewidth in linewidthlist:
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.plot(x, y, linewidth=linewidth, color='black')
        filename = 'linewidth_'+encode(str(linewidth))+'.png'
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)


##################################################
def generate_plinestyle():
    dpi = 72
    dpi2 = dpi*5 if isMPL2 else dpi

    F = plt.figure(num=None, figsize=(0.4, 0.25), dpi=dpi, facecolor='w')
    ax = plt.subplot(111)
    x = [0, 1, 1, 0, 0]
    y = [1, 1, 0, 0, 1]
    ed = ax.transAxes.transform([(0, 0), (1, 1)])
    bbox = Bbox.from_extents(ed[0, 0]/dpi, ed[0, 1]/dpi,
                             ed[1, 0]/dpi, ed[1, 1]/dpi)

    print('### generating patch linestyle palette button ###')
    plinestylelist = plinestyle_list()

    x = [0, 0.5, 1]
    y = [0.5, 0.5, 0.5]
    for plinestyle in plinestylelist:
        ax.cla()
        ax.tick_params(length=0)
        ax.set_axis_off()
        plt.axhspan(0.5, 0.5,
                    linestyle=plinestyle, edgecolor='black',
                    facecolor='white', linewidth=2)
        filename = 'plinestyle_'+encode(str(plinestyle))+'.png'
        plt.savefig(filename, dpi=dpi2, format='png', bbox_inches=bbox)

        # plt produces blured image on MPL2.0
        if isMPL2:
            im = wx.Image(filename)
            w, h = im.GetSize()
            im.Rescale(w/5, h/5).SaveFile(filename, wx.BITMAP_TYPE_PNG)

