#
#   custom picker for ifigure
#
#   purpose of using custom picker is
#
#     to handle picking on figobj level.
#
#     to share picking routine with DnD
#     handler.
#
#     to turn on/off the picking externally
#     using the variable "active".
#
#     to call picker to page objects.
#
#
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
# *******************************************
#     Copyright(c) 2012- PSFC, MIT
# *******************************************
import logging
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.text import Text
from matplotlib.image import AxesImage

from ifigure.utils.cbook import Write2Main
from ifigure.ifigure_config import pick_r

import numpy as np

active = True
figchecked = False
# def AxesPicker(aritst, evt):
#    return axes_picker(artist, evt)


def label_picker(axes, evt):
    alist = [axes.title,
             axes.get_xaxis().get_label(),
             axes.get_yaxis().get_label()]
    if hasattr(axes, 'get_zaxis'):
        alist.append(axes.get_zaxis().get_label())

    for a in alist:
        hit, extra = a.contains(evt)
        if hit:
            return a
    return None


def axes_picker(artist, evt, canvas=None):
    from ifigure.mto.fig_grp import FigGrp
    
    if canvas is None:
        canvas = evt.guiEvent.GetEventObject()  # backend_wxagg
    tb = canvas.GetParent().toolbar  # toolbar
    ifig_canvas = canvas.GetParent()  # ifigure_canvas

    check = label_picker(artist, evt)
    if check is not None:
        return True, {"mpl_artist": check, "linked_artist": artist}
#    print 'Axex Picker', artist.figobj
    aaa = artist.get_children()
    bbb = [a for a in aaa]
    for a in bbb:
        aaa = aaa + a.get_children()
#    for a in aaa:
#       if hasattr(a, 'figobj'):  print a, a.figobj
    alist = reversed(
        sorted(
            [(a.zorder, a) for a in aaa
                if (hasattr(a, "figobj") and a in a.figobj.get_artists_for_pick())],
             key = lambda x: x[0])
    )

    # print [x[1].figobj for x in alist]
    ifig_sel = [a() for a in ifig_canvas.selection]
    for z, a in alist:
        figobj = a.figobj
        if figobj._pickmask:
            continue
        if (evt.xdata is None and
                not figobj.allow_outside()):
            continue
#           print 'checking aritst..', z, a.figobj.get_full_path()
        hit, extra = figobj.picker_a(a, evt)
        if hit:
            if isinstance(a.figobj, FigGrp):
                #                  globals()["active"]=False
                return hit, extra
            else:
                rootgrp = a.figobj.get_root_figgrp()
                if (rootgrp is not None):  # if in group
                    p = a.figobj
                    if a in ifig_sel:
                        #                          globals()["active"]=False
                        return True, {"child_artist": a}  # result in unselect
                    # go up tree till rootgrp
                    p = p.get_parent()
                    while rootgrp is p.get_root_figgrp():
                        for a in p._artists:
                            if a in ifig_sel:
                                hit, extra = p.picker_a(a, evt)
                                return hit, extra
#                              if hit:
#                                  globals()["active"]=False
#                                  return True, {"child_artist":a}
                        p = p.get_parent()
                    a = rootgrp._artists[0]
#                  globals()["active"]=False
                return True, {"child_artist": a}

    # this checks picker to axes object in amode
    # base fig_axes does have ispickable_a False,
    # which prevent it from being picked.
    # inlet axes, and its derived class can be picked.
#    if tb.ptype == 'amode':
    if True:
        if artist.figobj.ispickable_a:
            hit, extra = artist.figobj.picker_a(artist, evt)
            if hit:
                return True, {"child_artist": artist}

        # return True, {"child_artist":None}
    return False, {"child_artist": None}

# def figure_picker(figure, evt):
#    canvas = evt.guiEvent.GetEventObject()  ### backend_wxagg
#    tb = canvas.GetParent().toolbar         ### toolbar

#    if not globals()["figchecked"]:
#       hit, extra = fig_picker(figure, evt)
#       if hit:

#          globals()["active"]=False
#          globals()["figchecked"] = True
#          return True, extra
#       globals()["figchecked"] = True
#    return False, {"child_artist":None}


def figlabel_picker(fig, evt):
    if fig.figobj._title_artist is not None:
        alist = [fig.figobj._title_artist]
    else:
        alist = []
    for a in alist:
        hit, extra = a.contains(evt)
        if hit:
            return a
    return None


def fig_picker(artist, evt):
    from ifigure.mto.fig_grp import FigGrp        
    from ifigure.mto.fig_axes import FigAxes

    canvas = evt.guiEvent.GetEventObject()  # backend_wxagg
    tb = canvas.GetParent().toolbar  # toolbar
    ifig_canvas = canvas.GetParent()  # ifigure_canvas

    check = figlabel_picker(artist, evt)
    if check is not None:
        return True, {"mpl_artist": check, "linked_artist": artist}

    ptype = tb.ptype
    ifig_sel = [a() for a in ifig_canvas.selection]
#    alist =reversed(
#           sorted(
#           [(a.zorder, a) for a in artist.get_children()
#            if (hasattr(a, "figobj") and not isinstance(a.figobj, FigGrp))]
#           )
#          )
    alist = reversed(
        sorted(
            [(a.zorder, a) for a in artist.get_children()
             if (hasattr(a, "figobj") and a in a.figobj.get_artists_for_pick())],
             key = lambda x: x[0])
    )
    for z, a in alist:
        flag = True
        figobj = a.figobj
        if isinstance(figobj, FigAxes):
            continue
        if hasattr(a, '_is_frameart'):
            if ifig_canvas._frameart_mode:
                if not a._is_frameart:
                    continue
            else:
                if a._is_frameart:
                    continue

        if flag:
            #           if ptype == 'pmode':
            #              hit, extra=figobj.picker(a, evt)
            #          if ptype == 'amode':
            hit, extra = figobj.picker_a(a, evt)
            if hit:
                if isinstance(a.figobj, FigGrp):
                    return hit, extra
                else:
                    rootgrp = a.figobj.get_root_figgrp()
                    if (rootgrp is not None):  # if in group
                        p = a.figobj
                        if a in ifig_sel:
                            # result in unselect
                            return True, {"child_artist": a}
                        # go up tree till rootgrp
                        p = p.get_parent()
                        while rootgrp is p.get_root_figgrp():
                            for a in p._artists:
                                if a in ifig_sel:
                                    #                          if p._artists[0] in ifig_sel:
                                    #                              a = p._artists[0]
                                    return p.picker_a(a, evt)
                            p = p.get_parent()
                        a = rootgrp._artists[0]
#                      return True, {"child_artist":a}
                # print hit to object which is not in group
                # and which is not group
                return True, {"child_artist": a}
    return False, {"child_artist": None}

# def picker(artist, evt, ptype):
    # if evt.xdata is None: return False, {}
#    if active:
#       figobj=artist.figobj

#       try:
#           if ptype == 'pmode':
#              hit, extra=figobj.picker(artist, evt)
#           if ptype == 'amode':
#              hit, extra=figobj.picker_a(artist, evt)
#       except Exception:
#            logging.exception("custom_picker: figobj.picker() failed")
#            return False, {}
#       if hit:
#           globals()["active"]=False
#       return hit, {}
#    else:
#       return False, {}


def CheckLineHit(x, y, x0, y0, trans=None, itrans=None):
    '''
    hit check between curve and pont
    if x, y are data coords.
      trans  : axes.trasnData.transform,
      itrans : axes.trasnData.inverted().transform
    '''
    def non_trans(args):
        return args

    if trans is None:
        trans = non_trans
        itrans = non_trans
    if itrans is None:
        itrans = non_trans
    if not isinstance(x, np.ndarray):
        x = np.array(x)
    if not isinstance(y, np.ndarray):
        y = np.array(y)

    x0d, y0d = trans((x0, y0))

    x1dt, y1dt = itrans((x0d-pick_r, y0d-pick_r))
    x2dt, y2dt = itrans((x0d+pick_r, y0d+pick_r))

    x1d, x2d = sorted([x1dt, x2dt])
    y1d, y2d = sorted([y1dt, y2dt])

    try:
        ic = np.where((x > x1d) & (x < x2d) & (y > y1d) & (y < y2d))[0][0]
    except:
        ic = None
        if x.shape[0] > 100:
            return False, 0

    if ic is not None:
        return True, ic
    xys = np.vstack((x, y)).transpose()

    d = [np.linalg.norm(trans(xy)-[x0d, y0d]) for xy in xys]

    # print d
    try:
        ic = np.where(d == min(d))[0][0]
    except:
        return False, 0

    if len(x) == 1:
        return False, 0

    ans = True
    if ic != len(x)-1:
        x1d, y1d = trans((x[ic], y[ic]))
        x2d, y2d = trans((x[ic+1], y[ic+1]))
        ans = ans and linehit_test(x0d, y0d, x1d, y1d, x2d, y2d)
    if ic != 0:
        x1d, y1d = trans((x[ic], y[ic]))
        x2d, y2d = trans((x[ic-1], y[ic-1]))
        ans = ans and linehit_test(x0d, y0d, x1d, y1d, x2d, y2d)
    if ic == 0:
        x1d, y1d = trans((x[0], y[0]))
        x2d, y2d = trans((x[1], y[1]))
        ans = ans and check_inner(x0d, y0d, x1d, y1d, x2d, y2d)
    if ic == len(x)-1:
        x1d, y1d = trans((x[ic], y[ic]))
        x2d, y2d = trans((x[ic-1], y[ic-1]))
        ans = ans and check_inner(x0d, y0d, x1d, y1d, x2d, y2d)

    return ans, ic


def linehit_test(x0, y0, x1, y1, x2, y2):
    #    print x0, y0, x1, y1, x2, y2
    d, l = norm_d(x0, y0, x1, y1, x2, y2)
#    print d, l
    if d > pick_r:
        return False
    return True
    #check_inner(x0, y0, x1, y1, x2, y2)


def abs_d(x0, y0, x1, y1):
    v1 = (x0-x1, y0-y1)
    l1 = np.sqrt(abs(v1[0]*v1[0]+v1[1]*v1[1]))
    return l1


def norm_d(x0, y0, x1, y1, x2, y2):
    # distance between (x0, y0) to a line
    # from (x1, y1) to (x2, y2)

    # return (normal_distance, distance between 0 and 1)

    v1 = (x0-x1, y0-y1)
    v2 = (x2-x1, y2-y1)

    l1 = np.sqrt(v1[0]*v1[0]+v1[1]*v1[1])
    l2 = np.sqrt(v2[0]*v2[0]+v2[1]*v2[1])

    cos = (v1[0]*v2[0]+v1[1]*v2[1])/l1/l2

    d = l1*np.sqrt(1. - cos*cos)
    return d, l1


def check_inner(x0, y0, x1, y1, x2, y2):

    v1 = (x0-x1, y0-y1)
    v2 = (x2-x1, y2-y1)
    if (v1[0]*v2[0]+v1[1]*v2[1]) < 0:
        return False

    v1 = (x0-x2, y0-y2)
    v2 = (x1-x2, y1-y2)
    if (v1[0]*v2[0]+v1[1]*v2[1]) < 0:
        return False

    return True


def activate():
    globals()["active"] = True
    globals()["figchecked"] = False
