from __future__ import print_function

'''
   connections is a board game from 80's

   usage:
      from ifigure.extra.connections import new_game
      new_game()

   DOTO:
      develop an algorithm to decide next move in 
      order to implement one player mode.
'''

from ifigure.widgets.book_viewer import BookViewer
from matplotlib.patches import Rectangle
import wx
import numpy as np
from matplotlib.patches import PathPatch

# size of elements
a = 1./(2**(0.5))
b = 1.0
d = 1./(11*b + 10 * a)
params = None


class Params(object):
    def __init__(self):
        self.cur_dir = 'h'
        self.cur_color = 'black'
        self.cur_pos = [0, 0]
        self.b_pos = []
        self.r_pos = []
        self.mode_mode = 1
        self._last_move = None
        self._last_obj = None


def draw_field():
    page = params.page
    figure = page._artists[0]
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
    viewer = wx.GetApp().TopWindow.find_bookviewer(page.get_figbook())
    viewer.draw()


def draw_octagon(loc, color='black', direction='v', alpha=1):
    ## loc (0,0) - (8,8)
    # loc[1] - loc[0] shoud be even
    import matplotlib.path as mpath
    from numpy import cos, sin, sqrt
    Path = mpath.Path
    page = params.page

    xy = [(a + 1.5*b)*d + l*(a+b)*d for l in loc]
    r = sqrt((d*b)**2 + ((a+a+b)*d)**2)/2
    figure = page._artists[0]
    theta = np.array([(22.5 + 45.*x)*np.pi/180 for x in range(8)])

    theta2 = theta[[7, 0, 1, 2, 3, 4, 5, 6, 7]]
    verts = [(xy[0]+r*cos(t), xy[1]+r*sin(t)) for t in theta2]
    codes = [Path.MOVETO] + [Path.LINETO]*(len(verts)-1)
    path = mpath.Path(verts, codes)
    obj1 = PathPatch(path, facecolor='white', edgecolor='black', alpha=alpha,
                     figure=figure, transform=figure.transFigure)

    if direction == 'v':
        theta2 = theta[[6, 1, 2, 5, 6]]
    else:
        theta2 = theta[[7, 0, 3, 4, 7]]
    verts = [(xy[0]+r*cos(t), xy[1]+r*sin(t)) for t in theta2]
    codes = [Path.MOVETO] + [Path.LINETO]*(len(verts)-1)
    path = mpath.Path(verts, codes)
    obj2 = PathPatch(path, edgecolor='black', alpha=alpha,
                     facecolor=color, figure=figure, transform=figure.transFigure)
    figure.patches.extend([obj1, obj2])
    viewer = wx.GetApp().TopWindow.find_bookviewer(page.get_figbook())
    viewer.draw()
    return obj1, obj2


def draw_hl_octagon(loc, color='cyan', alpha=1):
    ## loc (0,0) - (8,8)
    # loc[1] - loc[0] shoud be even
    import matplotlib.path as mpath
    from numpy import cos, sin, sqrt
    Path = mpath.Path
    page = params.page

    xy = [(a + 1.5*b)*d + l*(a+b)*d for l in loc]
    r = sqrt((d*b)**2 + ((a+a+b)*d)**2)/2
    figure = page._artists[0]
    theta = np.array([(22.5 + 45.*x)*np.pi/180 for x in range(8)])

    theta2 = theta[[7, 0, 1, 2, 3, 4, 5, 6, 7]]
    verts = [(xy[0]+r*cos(t), xy[1]+r*sin(t)) for t in theta2]
    codes = [Path.MOVETO] + [Path.LINETO]*(len(verts)-1)
    path = mpath.Path(verts, codes)
    obj1 = PathPatch(path, facecolor=color, edgecolor=color, alpha=alpha,
                     figure=figure, transform=figure.transFigure,)
    figure.patches.extend([obj1])
    return obj1


class Connections(BookViewer):
    pass


def draw_cursor():
    p = globals()['params']
    for obj in p.cursors:
        p.page._artists[0].patches.remove(obj)
    obj1, obj2 = draw_octagon(p.cur_pos, color=p.cur_color,
                              direction=p.cur_dir, alpha=0.4)
    p.cursors = [obj1, obj2]


def handle_keyevent(evt):
    import wx
    p = globals()['params']
    if (evt.GetKeyCode() == wx.WXK_RIGHT and
            p.cur_pos[0] < 7):
        p.cur_pos = [p.cur_pos[0]+2, p.cur_pos[1]]
    elif (evt.GetKeyCode() == wx.WXK_LEFT and
          p.cur_pos[0] > 1):
        p.cur_pos = [p.cur_pos[0]-2, p.cur_pos[1]]
    elif (evt.GetKeyCode() == wx.WXK_UP and
          p.cur_pos[1] < 7):
        p.cur_pos = [p.cur_pos[0], p.cur_pos[1]+2]
    elif (evt.GetKeyCode() == wx.WXK_DOWN and
          p.cur_pos[1] > 1):
        p.cur_pos = [p.cur_pos[0], p.cur_pos[1]-2]
    elif evt.GetKeyCode() == wx.WXK_SHIFT:
        if p.cur_pos[0] % 2 == 0:
            p.cur_pos = [1, 1]
        else:
            p.cur_pos = [0, 0]
    elif evt.GetKeyCode() == wx.WXK_RETURN:
        for pos in p.b_pos + p.r_pos:
            if pos[0] == p.cur_pos[0] and pos[1] == p.cur_pos[1]:
                return
        obj1, obj2 = draw_octagon(p.cur_pos, color=p.cur_color,
                                  direction=p.cur_dir, alpha=1)
        p._last_obj = (obj1, obj2)
        ppp = tuple(p.cur_pos)
        p._last_move = ppp
        if p.cur_color == 'red':
            p.r_pos.append(ppp)
            p.cur_color = 'black'
        else:
            p.b_pos.append(ppp)
            p.cur_color = 'red'
        if check_finish():
            p.viewer.canvas.canvas.Unbind(wx.EVT_KEY_UP)
            return
    elif evt.GetKeyCode() == wx.WXK_TAB:
        if p._last_obj is not None:
            page = params.page
            figure = page._artists[0]
            figure.patches.remove(p._last_obj[0])
            figure.patches.remove(p._last_obj[1])
            if p._last_move in p.r_pos:
                p.r_pos.remove(p._last_move)
            if p._last_move in p.b_pos:
                p.b_pos.remove(p._last_move)
            if p.cur_color == 'red':
                p.cur_color = 'black'
            else:
                p.cur_color = 'red'

        p._last_obj = None
        p._last_move = None

    if p.cur_pos[0] % 2 == 0:
        if p.cur_color == 'black':
            p.cur_dir = 'h'
        else:
            p.cur_dir = 'v'
    else:
        if p.cur_color == 'black':
            p.cur_dir = 'v'
        else:
            p.cur_dir = 'h'
    draw_cursor()


def r_check_finish(st, pos, et, rt):
    v = False
    if st in pos:
        rt.append(st)
        if st in et:
            return True
        pos.remove(st)
        if st[1] % 2 == 1:
            if r_check_finish((st[0]+2, st[1]), pos[:], et, rt):
                v = True
            if r_check_finish((st[0]-2, st[1]), pos[:], et, rt):
                v = True
        else:
            if r_check_finish((st[0],   st[1]+2), pos[:], et, rt):
                v = True
            if r_check_finish((st[0],   st[1]-2), pos[:], et, rt):
                v = True
        if r_check_finish((st[0]+1,   st[1]+1), pos[:], et, rt):
            v = True
        if r_check_finish((st[0]-1,   st[1]+1), pos[:], et, rt):
            v = True
        if r_check_finish((st[0]+1,   st[1]-1), pos[:], et, rt):
            v = True
        if r_check_finish((st[0]-1,   st[1]-1), pos[:], et, rt):
            v = True
    return v


def b_check_finish(st, pos, et, rt):
    if st in pos:
        rt.append(st)
        if st in et:
            return True
        pos.remove(st)
        if st[1] % 2 == 0:
            if b_check_finish((st[0]+2, st[1]), pos[:], et, rt):
                return True
            if b_check_finish((st[0]-2, st[1]), pos[:], et, rt):
                return True
        else:
            if b_check_finish((st[0],   st[1]-2), pos[:], et, rt):
                return True
            if b_check_finish((st[0],   st[1]+2), pos[:], et, rt):
                return True
        if b_check_finish((st[0]+1,   st[1]+1), pos[:], et, rt):
            return True
        if b_check_finish((st[0]+1,   st[1]-1), pos[:], et, rt):
            return True
        if b_check_finish((st[0]-1,   st[1]+1), pos[:], et, rt):
            return True
        if b_check_finish((st[0]-1,   st[1]-1), pos[:], et, rt):
            return True

    return False


def highlight_route(rt):
    import time
    objs = [draw_hl_octagon(pos, color='cyan', alpha=0.5) for pos in rt]
    print(objs)
    page = params.page
    viewer = wx.GetApp().TopWindow.find_bookviewer(page.get_figbook())
    viewer.draw()
    for x in range(20):
        time.sleep(0.1)
        if x % 2 == 0:
            for o in objs:
                o.set_alpha(0.8)
            viewer.draw_all()
        else:
            for o in objs:
                o.set_alpha(0.5)
            viewer.draw_all()


def check_finish():
    p = globals()['params']
    for x in [(0, 0), (2, 0), (4, 0), (6, 0), (8, 0)]:
        rt = []
        if r_check_finish(x, p.r_pos[:], [(0, 8), (2, 8), (4, 8), (6, 8), (8, 8)], rt):
            print('red win')
            highlight_route(rt)
            return True
    for x in [(0, 0), (0, 2), (0, 4), (0, 6), (0, 8)]:
        rt = []
        if b_check_finish(x, p.b_pos[:], [(8, 0), (8, 2), (8, 4), (8, 6), (8, 8)], rt):
            print('black win')
            highlight_route(rt)
            return True


def new_game():
    from __main__ import ifig_app
    import ifigure.events
    book = ifig_app.proj.onAddBook()
    i_page = book.add_page()
    page = book.get_page(i_page)
    page.realize()
    page.get_artist(0).set_facecolor('yellow')
    ifigure.events.SendOpenBookEvent(book, w=ifig_app,
                                     viewer=Connections, useProcessEvent=True)

    p = Params()
    globals()['params'] = p
    p.page = page
    p.viewer = ifig_app.find_bookviewer(book)
    p.viewer.SetSize((300, 300))
    draw_field()
    obj1, obj2 = draw_octagon([0, 0], color='black', direction='v', alpha=0.4)
    p.cursors = [obj1, obj2]
    p.viewer.canvas.canvas.Bind(wx.EVT_KEY_UP, handle_keyevent)
