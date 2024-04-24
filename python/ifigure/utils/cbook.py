from __future__ import print_function


#  load image file
#   this could be widget toolkit dependent
import sys
import six
import os
import matplotlib.colors
from ifigure.utils.wx3to4 import menu_Append, wxBitmapFromImage, wxCursorFromImage, menu_AppendItem
from ifigure.utils.wx3to4 import image_GetAlpha, image_SetAlpha, image_SetOptionInt, wxEmptyImage
import wx
import os
import string
import weakref
import matplotlib
import threading
import traceback
import ifigure
import numpy as np
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('cbook')


try:
    import Image
except ImportError:
    from PIL import Image


def is_safename(txt):
    try:
        exec(txt + '= 3', {}, {})
    except:
        return False
    return True


def text_repr(val):
    if isinstance(val, list):
        if (len(val) > 10):
            text = (val[:10].__repr__())[:-1]+'...'
        else:
            text = val.__repr__()
    elif isinstance(val, tuple):
        if (len(val) > 10):
            text = (val[:10].__repr__())[:-1]+'...'
        else:
            text = val.__repr__()
    elif isinstance(val, dict):
        if len(val) > 5:
            text = ({key: val[key]
                     for key in list(val.keys())[0:5]}.__repr__())[:-1]+'...'
        else:
            text = val.__repr__()
    elif isinstance(val, np.ndarray):
        text = '**data**'
    elif hasattr(val, '__len__'):
        try:
            if six.PY2:
                if (len(val) > 10 and not isinstance(val, str) and not isinstance(val, unicode)):
                    text = '**data**'
                else:
                    text = val.__repr__()
            else:
                if (len(val) > 10 and not isinstance(val, str)):
                    text = '**data**'
                else:
                    text = val.__repr__()
        except:
            try:
                text = val.__repr__()
            except:
                text = ''
    else:
        try:
            text = val.__repr__()
        except:
            text = ''
    if len(text) > 40:
        text = text[0:39]+'...'
    return text


def message(*args):
    msg = ','.join([str(x) for x in args])
    print(msg)
    import ifigure.server
    s = ifigure.server.Server()
    if s.info()[0]:
        ifigure.server.Server().export_message(msg)


def get_screen_font_size(size=10, text='ABCDEF'):
    font = wx.Font(pointSize=size, family=wx.DEFAULT,
                   style=wx.NORMAL,  weight=wx.NORMAL,
                   faceName='Consolas')
    dc = wx.ScreenDC()
    dc.SetFont(font)
    return dc.GetTextExtent(text)


def get_current_display_size(window):
    '''
    get display size of current window
    support multi-screen
    '''
    scx, scy = window.ClientToScreen((0, 0))
    for i in range(wx.Display.GetCount()):
        x0, y0, xd, yd = wx.Display(i).GetGeometry()
        if (x0 < scx < x0+xd and
                scy > y0 and scy < y0+yd):
            break
    return x0, y0, xd, yd


def show_pop_up(window, menu, xy, *args, **kwargs):
    x0, y0, xd, yd = get_current_display_size(window)
    if xy[1] > yd-100:
        xy = [xy[0], yd-100]
    return window.PopupMenu(menu,  # ifigure_popup(self),
                            xy)


def isInMainThread():
    return threading.current_thread().name == 'MainThread'


def pick_unused_port():
    '''
    a routeint to le a system to pick an unused port.
    this recipe was found in active state web site
    '''
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port

#
#  conversion from PIL to WX image
#


def pil_to_image(pil, alpha=True):
    #from PIL import Image
    #import Image
    """ Method will convert PIL Image to wx.Image """
    if alpha:
        image = wxEmptyImage(*pil.size)
        image.SetData(pil.convert("RGB").tobytes())
        image.SetAlphaData(pil.convert("RGBA").tobytes()[3::4])
    else:
        image = wxEmptyImage(pil.size[0], pil.size[1])
        new_image = pil.convert('RGB')
        data = new_image.tostring()
        image.SetData(data)
    return image

#
#  conversion from WX image to PIL image
#


def image_to_pil(image):
    #
    #import Image
    """ Method will convert wx.Image to PIL Image """
    #pil = Image.new('RGB', (image.GetWidth(), image.GetHeight()))
    # pil.fromstring(image.GetData())

    data = image.GetData()

    import sys
    if isinstance(image.GetData(), bytearray):
        if sys.version_info > (3, 0):
            data = bytes(data)
        else:
            data = str(data)
    pil = Image.frombytes('RGB', (image.GetWidth(), image.GetHeight()),
                          data)
    print(pil)
    return pil


def make_crs_list(paths, hx, hy):
    crs = []
    for path in paths:
        im = wx.Image(path, wx.BITMAP_TYPE_PNG)
        # image = im.ConvertToBitmap()
        if im.HasAlpha():
            im.ConvertAlphaToMask()
        image_SetOptionInt(im, wx.IMAGE_OPTION_CUR_HOTSPOT_X, hx)
        image_SetOptionInt(im, wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hy)
        crs.append(wxCursorFromImage(im))
    return crs


def make_bitmap_list(paths):
    bitmaps = []
    for path in paths:
        im = wx.Image(path, wx.BITMAP_TYPE_PNG)
        bitmaps.append(im.ConvertToBitmap())
    return bitmaps


def on_off_args(v):
    ans = False
    if isinstance(v, str):
        if v.upper() == 'ON':
            ans = True
        if v.upper() == 'OFF':
            ans = True
        if v.upper() == '1':
            ans = True
        if v.upper() == '0':
            ans = False
    elif isinstance(v, bool):
        ans = v
    elif isinstance(v, int):
        if v == 1:
            ans = True
        if v == 0:
            ans = False
    elif isinstance(v, float):
        if v == 1.0:
            ans = True
        if v == 0.0:
            ans = False
    return ans


class ImageFiles(object):
    _list = None
    _size = 16

    def __init__(self):
        if ImageFiles._list is None:
            ImageFiles._list = wx.ImageList(ImageFiles._size,
                                            ImageFiles._size)

    def add(self, fpath):
        def bmp2array(bm):
            h, w = bm.GetSize()
            im = bm.ConvertToImage()
            array = np.frombuffer(bytes(im.GetData()), dtype=np.uint8).copy()
            array = array.reshape(w, h, -1)
            alpha = image_GetAlpha(im)
            if alpha is not None:
                alpha = np.frombuffer(bytes(image_GetAlpha(im)),
                                      dtype=np.uint8).reshape(w, h, -1).copy()
            else:
                alpha = np.zeros((w, h, 1), dtype=np.uint8)+255
            return array, alpha,

        def array2bmp(array, alpha):
            w = array.shape[0]
            h = array.shape[1]
            im = wxEmptyImage(h, w)
            im.SetData(array.tobytes())
            image_SetAlpha(im, alpha)
            return im.ConvertToBitmap()

        def alpha_composite(ca, cb, aa, ab):
            resc = ca.copy().astype(float)
            resa = aa.copy().astype(float)
            ca = ca.astype(float)
            cb = cb.astype(float)
            aa = aa.astype(float)/255.
            ab = ab.astype(float)/255.
            for k in range(3):
                resc[:, :, k] = (np.multiply(ca[:, :, k], aa[:, :, 0])
                                 + np.multiply(np.multiply(cb[:, :, k], ab[:, :, 0]), 1.-aa[:, :, 0]))
            resa[:, :, 0] = aa[:, :, 0] + \
                np.multiply(ab[:, :, 0], (1.-aa[:, :, 0]))
            resa = (resa*255).astype(np.uint8)
            resc = resc.astype(np.uint8)
            return resc, resa

        if fpath[-4:] == '.png':
            bm = wxBitmapFromImage(wx.Image(fpath, wx.BITMAP_TYPE_PNG))
        if fpath[-4:] == '.bmp':
            bm = wxBitmapFromImage(wx.Image(fpath, wx.BITMAP_TYPE_BMP))

        fpath2 = os.path.join(os.path.dirname(fpath), 'suppress.png')
        bm2 = wxBitmapFromImage(wx.Image(fpath2, wx.BITMAP_TYPE_PNG))

        array, alpha = bmp2array(bm)
        array2, alpha2 = bmp2array(bm2)
        array3, alpha3 = alpha_composite(array2, array,
                                         alpha2, alpha)
        bm3 = array2bmp(array3, alpha3)
        idx = ImageFiles._list.Add(bm)
        idx2 = ImageFiles._list.Add(bm3)
        if self.IsOk(idx) is False:
            print("can not read "+fpath)
            idx = -1
            idx2 = -1
        return idx, idx2

    def get_imagelist(self):
        return ImageFiles._list

    def IsOk(self, idx):
        bm = ImageFiles._list.GetBitmap(idx)
        return bm.IsOk()

    def FilePath(self, path, file):
        if ImageFiles._size == 32:
            fpath = os.path.join(path, '32x32', file)
        if ImageFiles._size == 24:
            fpath = os.path.join(path, '24x24', file)
        if ImageFiles._size == 16:
            fpath = os.path.join(path, '16x16', file)
        return fpath


def LoadImageFile(path, fname):
    im = ImageFiles()
    fpath1 = im.FilePath(path, fname)
    return im.add(fpath1)


def Write2Main(val, name):
    import __main__
    print("writing variable "+name+" to __main__")
    exec('__main__.'+name+'=val')


def ReadFromMain(name):
    import __main__
    print("writing variable "+name+" from __main__")
    return eval('__main__.'+name)


def FindFrame(w):
    if isinstance(w, wx.Frame):
        return w
    w = w.GetParent()
    if w is not None:
        return FindFrame(w)


def GetNextName(keys, header):
    num = []
    for key in keys:
        if key.startswith(header+'_'):
            a = key[len(header)+1:]
            if a.isdigit():
                num.append(int(a))
            continue
        if key.startswith(header):
            a = key[len(header):]
            if a.isdigit():
                num.append(int(a))
            continue
    if len(num) == 0:
        return header+'1'
    else:
        return header+str(max(num)+1)


def MoveItemInList(l, i1, i2):
    # move i1 to i2
    if i1 > i2:
        return l[0:i2] + [l[i1]] + l[i2:i1] + l[i1+1:len(l)]
    elif i1 < i2:
        return l[0:i1] + l[i1+1:i2+1] + [l[i1]] + l[i2+1:len(l)]
    else:
        raise ValueError(
            "cbook::MoveItemInList :i1 should be different from i2")


def ClassNameToFile(s):
    pos = [i for i, e in enumerate(s+'A') if e.isupper()]
    parts = [s[pos[j]:pos[j+1]] for j in range(len(pos)-1)]
    return '_'.join(parts).lower()


def FileNameToClass(path):
    txt = os.path.basename(path)
    if (txt.split('.')[-1] == 'py' or
            txt.split('.')[-1] == 'pyc'):
        s = '.'.join(txt.split('.')[:-1])
    else:
        s = txt
    return ''.join([b.capitalize() for b in s.split('_')])


def isBinary(filename):
    """
    Return true if the given filename appears to be binary.
    File is considered to be binary if it contains a NULL byte.
    (This approach incorrectly reports UTF-16 as binary.)
    """
    if six.PY2:
        with open(filename, 'rb') as f:
            for block in f:
                if '\0' in block:
                    return True
    else:
        with open(filename, 'rb') as f:
            for block in f:
                if b'\0' in block:
                    return True

    return False


def isDescendant(parent, kid):
    p = kid.GetParent()
    while p is not None:
        if parent == p:
            return True
        p = p.GetParent()
    return False


def LoadClass(path, name):
    # path='ifigure.fig_objects.'
    # ClassNameToFile(name))
    import sys
#    print path+ClassNameToFile(name)
    mod = __import__(path+ClassNameToFile(name))
    return sys.modules[path+ClassNameToFile(name)]
#    components = name.split('.')
#    for comp in components[1:]:
#        comp
#        mod = getattr(mod, comp)

    return mod


def EraseBitMap(bmp):
    import array
    w = bmp.GetWidth()
    h = bmp.GetHeight()
    # Make a bitmap using an array of RGBA bytes
    bpp = 4  # bytes per pixel
    bytes = array.array('B', [0] * w*h*bpp)
    bmp.CopyFromBufferRGBA(bytes)
    return bmp


def DrawBox(box, canvas, color='red'):
    from matplotlib.lines import Line2D
    x = (box[0], box[2], box[2], box[0], box[0])
    y = (box[1], box[1], box[3], box[3], box[1])
    rb = Line2D(x, y, figure=canvas._figure,
                linestyle='-', color=color, alpha=1,
                markerfacecolor='None')
    canvas._figure.lines.extend([rb])
    canvas.draw()
    canvas._figure.lines.remove(rb)


def SetText2Clipboard(text):
    if not wx.TheClipboard.IsOpened():
        wx.TheClipboard.Open()
        data = wx.TextDataObject()
        data.SetText(text)
        wx.TheClipboard.SetData(data)
        wx.TheClipboard.Close()
        return 0
    return -1


def GetArtistExtent(a, box=None, renderer=None, canvas=None, force=False):
    '''
    find window extent of artists contained
    in a
    '''
    def merge_box(box, box2):
        return (min((box[0], box2[0])),
                min((box[1], box2[1])),
                max((box[2], box2[2])),
                max((box[3], box2[3])),)

    if box is None:
        box = (np.inf, np.inf, -np.inf, -np.inf)

    if hasattr(a, 'get_window_extent'):
        try:
            if renderer is None:
                #renderer = a.figure._cachedRenderer
                renderer = a.figure.canvas.get_renderer()

            box1 = a.get_window_extent(renderer).extents
            box = merge_box(box, box1)
        except:
            dprint1('GetArtistExtent can not check ' + str(a))
            pass
    for a in a.get_children():
        box = GetArtistExtent(a, box=box, renderer=renderer, canvas=canvas)
    if hasattr(a, 'artists'):
        for a in a.artists():
            box = GetArtistExtent(
                a, box=box, renderer=renderer, canvas=canvas, force=True)
    if hasattr(a, 'legends'):
        for a in a.legends():
            box = GetArtistExtent(
                a, box=box, renderer=renderer, canvas=canvas, force=True)
    if hasattr(a, 'get_bbox_patch'):
        if a.get_bbox_patch() is not None:
            box = GetArtistExtent(a.get_bbox_patch(), box=box,
                                  renderer=renderer, canvas=canvas, force=True)
#    box[0] = max([box[0], 0])
#    box[1] = min([w, box[1]])
#    box[2] = max([box[2], 0])
#    box[3] = min([h, box[3]])
#    box = (max((box[0], 0)),
#           max((box[1], 0)),
#           min((w, box[2])),
#           min((h, box[3])))
    if canvas:
        DrawBox(box, canvas)
    return box


def BezierFit(x, y):
    import matplotlib.path as mpath
    Path = mpath.Path

    if len(x) == 2:
        pathdata = [(Path.MOVETO, (x[0], y[0]), 0),
                    (Path.LINETO, (x[1], y[1]), 0)]
        return pathdata

    x = np.array(x)
    y = np.array(y)
    mx = (x[1:]+x[:-1])/2
    my = (y[1:]+y[:-1])/2

    cx1 = [(mx[i]-mx[i+1])/2.+x[i+1] for i in range(len(mx)-1)]
    cy1 = [(my[i]-my[i+1])/2.+y[i+1] for i in range(len(my)-1)]
    cx2 = [(mx[i+1]-mx[i])/2.+x[i+1] for i in range(len(mx)-1)]
    cy2 = [(my[i+1]-my[i])/2.+y[i+1] for i in range(len(my)-1)]

    cx2 = [(cx1[0]-x[0])/2.+x[0]]+cx2
    cy2 = [(cy1[0]-y[0])/2.+y[0]]+cy2
    cx1 = cx1+[(cx2[-1]-x[-1])/2.+x[-1]]
    cy1 = cy1+[(cy2[-1]-y[-1])/2.+y[-1]]

    pathdata = [(Path.MOVETO, (x[0], y[0]), 0)]
    for i in range(len(x)-1):
        pathdata.append((Path.CURVE4, (cx2[i], cy2[i]), 1))
        pathdata.append((Path.CURVE4, (cx1[i], cy1[i]), 1))
        pathdata.append((Path.CURVE4, (x[i+1], y[i+1]), 1))
    return pathdata


def BezierComputeCurve(pathdata, mesh=10):
    def numerical_cubic_bezier_fn(control_pts, t):
        # define the actual cubic bezier equation here
        def fn(c, t): return c[0]*(1 - t)**3 + c[1]*3 * \
            t*(1 - t)**2 + c[2]*3*t**2*(1 - t) + c[3]*t**3
        xs = [x for x, y in control_pts]
        ys = [y for x, y in control_pts]
        # now calculate the x,y position from the bezier equation
        xpt = fn(xs, t)
        ypt = fn(ys, t)
        return xpt, ypt
    import matplotlib.path as mpath
    Path = mpath.Path
    t = np.linspace(0, 1, mesh)[:-1]
    ii = iter(pathdata)
    x = []
    y = []
    lastitem = next(ii)
    while 1:
        try:
            item1 = next(ii)
        except StopIteration:
            break
        if item1[0] == Path.MOVETO:
            lastitem = item[1]
        elif item1[0] == Path.CURVE4:
            item2 = next(ii)
            item3 = next(ii)
            cps = [lastitem[1], item1[1], item2[1], item3[1]]
            a, b = numerical_cubic_bezier_fn(cps, t)
            x.extend(a)
            y.extend(b)
            lastitem = item3
    return x, y


def BezierNodeType(path, inode):
    import matplotlib.path as mpath
    Path = mpath.Path

    type = 1
    j = 0
    '''
    node on the line is
    type = 1, 2, 5
    '''
    for i in range(len(path)):
        if (path[i][0] == Path.MOVETO or
                path[i][0] == Path.LINETO):
            type = 1
            j = 0
        elif path[i][0] == Path.CURVE4:
            j = j+1
            if j % 3 == 0:
                type = 2
            elif j % 3 == 1:
                type = 3
            else:
                type = 4
        elif path[i][0] == Path.POLYCLOSE:
            type = 5
        if i == inode:
            return type
    return type


def BezierRmnode(path, hit):
    '''
    remove control hit-th node from path
    '''
    import matplotlib.path as mpath
    Path = mpath.Path
#   print 'removing node ', hit
    segpath = BezierSplit(path)
    if len(segpath) == 1:
        return None
    if hit == 0:
        segpath = segpath[1:]
    else:
        i = 0
        iseg = 0
        for seg in segpath:
            #          print 'checking', i+len(seg), hit
            if i+len(seg)-1 >= hit:
                break
            i = i+len(seg)-1
            iseg = iseg+1
        iseg = min([iseg, len(segpath)])
#      print 'merging segment', iseg
        if iseg == len(segpath)-1:
            segpath = segpath[:-1]
        else:
            #          print 'merging segment', iseg, iseg+1
            seg1 = segpath[iseg]
            seg2 = segpath[iseg+1]
            # iseg segment which hit
            if (len(seg1) == 4 and len(seg2) == 4):  # curve-curve
                newseg = [seg1[0], seg1[1], seg2[2], seg2[3]]
            elif (len(seg1) == 4 and len(seg2) == 2):  # curve-line
                newseg = [seg1[0], seg2[1]]
            elif (len(seg1) == 2 and len(seg2) == 4):  # line-curve
                seg2m = (Path.LINETO, seg2[3][1], seg2[3][2])
                newseg = [seg1[0], seg2[3]]
            elif (len(seg1) == 2 and len(seg2) == 2):  # line-line
                newseg = [seg1[0], seg2[1]]

            segpath = segpath[:iseg]+[newseg]+segpath[iseg+2:]
    p = BezierJoin(segpath)
    return p


def BezierSplit(path):
    import matplotlib.path as mpath
    Path = mpath.Path

    segs = []
    seg = []

    i = 0
    while i < len(path):
        if path[i][0] == Path.MOVETO:
            seg = [path[i]]
        elif path[i][0] == Path.LINETO:
            seg = seg + [path[i]]
            segs.append(seg)
            seg = [(Path.MOVETO, path[i][1], 0)]
        elif path[i][0] == Path.CURVE4:
            seg = seg + [path[i]]
            i = i+1
            seg = seg + [path[i]]
            i = i+1
            seg = seg + [path[i]]
            segs.append(seg)
            seg = [(Path.MOVETO, path[i][1], 0)]
        i = i+1

    return segs


def BezierInsert(path, i,  x, y):
    segpath = BezierSplit(path)
    segpath[i] = BezierInsert0(segpath[i],  x, y)
    path = BezierJoin(segpath)
    return path


def BezierJoin(segpath):
    path = [segpath[0][0]]
    for seg in segpath:
        path.extend(seg[1:])
    return path


def BezierInsert0(segpath,  x, y):
    import matplotlib.path as mpath
    Path = mpath.Path

    st = segpath[0][1]
    if segpath[-1][0] == Path.LINETO:
        ans = [segpath[0],
               (Path.CURVE4, (int(st[0]*0.3+x*.7), int(st[1]*0.3+y*.7)), 2),
               (Path.CURVE4, (x, y), 2), ]
        st = ans[-1][1]
        x, y = segpath[-1][1]
        ans = ans + [
            (Path.CURVE4, (int(st[0]*0.7+x*.3), int(st[1]*0.7+y*.3)), 2),
            segpath[-1]]
    elif segpath[-1][0] == Path.CURVE4:
        ans = [segpath[0],
               segpath[1],
               (Path.CURVE4, (int(st[0]*0.3+x*.7), int(st[1]*0.3+y*.7)), 2),
               (Path.CURVE4, (x, y), 2)]
        st = ans[-1][1]
        x, y = segpath[-1][1]
        ans = ans + [
            (Path.CURVE4, (int(st[0]*0.7+x*.3), int(st[1]*0.7+y*.3)), 2),
            segpath[-2],
            segpath[-1]]
    return ans


def BezierHitTest(path, x0, y0):
    from matplotlib.patches import PathPatch
    import ifigure.widgets.canvas.custom_picker as cpicker

    segpath = BezierSplit(path)
    i = 0
    for seg in segpath:
        p = [(item[0], item[1]) for item in seg]
        codes, verts = zip(*p)
        obj = matplotlib.path.Path(verts, codes)
        a = PathPatch(obj)
        xy = a.get_verts()
        if len(xy) == 0:  # this case happens when verts has only two points in mpl1.5
            x = [v[0] for v in verts]
            y = [v[1] for v in verts]
        else:
            x = np.transpose(xy)[0]
            y = np.transpose(xy)[1]
        hit, idx = cpicker.CheckLineHit(x, y, x0, y0)
        if hit:
            return True, i
        i = i+1
    return False, -1


def ParseNameObj(*argc):
    name = None
    obj = None
    if len(argc) == 2:
        name = argc[0]
        obj = argc[1]
    elif len(argc) == 1:
        if type(argc[0]) is str:
            name = argc[0]
        else:
            obj = argc[0]
    return name, obj


def BuildPopUpMenu(base, menus, eventobj=None,
                   xy=None, xydata=None):
    '''    
     base = wx.Menu
     menus = [(menu_string, func, icon_image)]

     special menu_string
       --- : separator
       '+' and '!' control submenu generation
        +...:  goto deeper menu
        !...: end of current depth

     icon_image is not yet implemented...

     if eventobj is set to widget, events returned
     from the popup has the widget as eventobj
    '''
    isTop = True
    ret = {}
    for m in menus:
        s = m[0]
        h = m[1]
        i = m[2]
        bmp = None if len(m) < 4 else m[3]
        id = wx.ID_ANY if len(m) < 5 else m[4]
        if s == '---':
            if not isTop:
                base.AppendSeparator()
            continue
        elif s[0] == '+':
            new_base = wx.Menu()
            mmi = base.AppendSubMenu(new_base, s[1:])
            base = new_base
            isTop = True
            mmm = base
        elif s[0] == '!':
            base = base.GetParent()
            isTop = False
        else:
            isTop = False
            escape = False
            if s[0] == "\\":
                escape = True
                mmi = wx.MenuItem(base, id, s[1:])
            elif s[0] == '-':
                mmi = wx.MenuItem(base, id, s[1:])
            elif s[0] == '*':
                mmi = wx.MenuItem(base, id, s[1:], kind=wx.ITEM_CHECK)
            elif s[0] == '^':
                mmi = wx.MenuItem(base, id, s[1:], kind=wx.ITEM_CHECK)
            else:
                mmi = wx.MenuItem(base, id, s)
            if bmp is not None:
                mmi.SetBitmap(bmp)
            menu_AppendItem(base, mmi)
            if not escape:
                if s[0] == '^':
                    mmi.Check(True)
                if s[0] == '-':
                    mmi.Enable(False)

            def func(evt, handler=h, obj=eventobj, extra=i,
                     xy=xy, xydata=xydata):
                if obj is not None:
                    evt.SetEventObject(obj)
                if extra is not None:
                    evt.ExtraInfo = extra
                if xy is not None:
                    evt.mpl_xy = xy
                else:
                    evt.mpl_xy = (None, None)
                if xydata is not None:
                    evt.mpl_xydata = xydata
                else:
                    evt.mpl_xydata = (None, None)
                handler(evt)
            base.Bind(wx.EVT_MENU, func, mmi)
            mmm = mmi.GetMenu()
        if id != wx.ID_ANY:
            ret[id] = (mmm, mmi)
    return ret


BuildMenu = BuildPopUpMenu


def parseStr(x0):
    #
    # convert string to number
    #   3D3, 3d3, 3E3, 3e3 to float
    #   the bottom part wad downloaded from somewhere
    #

    num = 1
    if x0.find('*') != -1:
        x = x0.split('*')[1]
        num = int(x0.split('*')[0])
    else:
        x = x0

    sign = 1
    x1 = x
    if x.startswith('+'):
        x1 = x[1:]
        sign = 1
    if x.startswith('-'):
        x1 = x[1:]
        sign = -1
    try:
        if x1.isdigit():
            return [int(x1)*sign]*num
    except:
        pass

    try:
        return [float(x1)*sign]*num
    except:
        pass

    try:
        return [float(x1.replace('D', 'E'))*sign]*num
    except:
        pass

    try:
        return [float(x1.replace('d', 'E'))*sign]*num
    except:
        pass

    try:
        return [x.isalpha() and x or x.isalnum() and x or len(set(string.punctuation).intersection(x)) == 1 and x.count('.') == 1 and float(x) or x]*num
    except:
        pass

    return [None]


def isdynamic(t):
    if (isinstance(t, str) and
        t.startswith('=') and
            len(t) != 1):
        return True
    else:
        return False


def isiterable(obj):
    'return true if *obj* is iterable'
    try:
        iter(obj)
    except TypeError:
        return False
    return True


def isiterable_not_string(obj):
    return hasattr(obj, '__iter__') and not isinstance(obj, str)


def isstringlike(x):
    if six.PY2:
        return (isinstance(x, str) or isinstance(x, unicode))
    else:
        return isinstance(x, str)


def nd_iter(x):
    if x.size:
        return x
    return []


def issequence(obj):
    'return true if *obj* is iterable'
    try:
        obj[0:0]
    except (AttributeError, TypeError):
        return False
    return True


def isnumber(obj):
    '''
    this may not catch all of strange classes....
    this also does not work with bool
    '''
    attrs = ['__add__', '__sub__', '__mul__', '__truediv__', '__pow__']
    return all(hasattr(obj, attr) for attr in attrs) and not (isinstance(obj, np.ndarray) and obj.dtype.kind in 'OSU')


def isndarray(obj):
    return isinstance(obj, np.ndarray)


def GetModuleDir(mname):
    import sys
    namelist = mname.split('.')
    if (namelist[0] in sys.modules) is False:
        try:
            top = __import__(namelist[0], globals(), locals(), [], -1)
        except Exception:
            return ''
    p0 = sys.modules[namelist[0]].__path__[0]
    if len(namelist) == 1:
        return p0
    k = 1
    for name in namelist[1:]:
        p0 = os.path.join(p0, name)
    return p0


def LoadScriptFile(file):
    import os
    import time
    import logging
    logging.basicConfig(level=logging.DEBUG)

    mtime = os.path.getmtime(file)
    f = open(file, 'r')
    txt = ''
    while 1:
        line = f.readline()
        if not line:
            break
        txt = txt+line
    f.close()

    try:
        code = compile(txt, file, 'exec')
    except:
        print(traceback.format_exc())
        raise

    return txt, code, mtime


def WeakNone():
    class tmp(object):
        pass
    x = tmp()
    ref = weakref.ref(x)
    del x
    return ref


def ProxyAlive(wp):
    if wp is None:
        return False
    try:
        wp.ref()
        return True
    except Exception:
        return False


def LaunchEmacs(file):
    import wx

    if wx.Platform == '__WXMAC__':
        txt = 'open -a /Applications/Emacs.app ' + file
    else:
        txt = 'emacs '+file + ' &'
    os.system(txt)


def ProcessKeywords(kywds, name, value=None):
    if name in kywds:
        value = kywds[name]
        del kywds[name]
    return value, kywds


def test(a=None, b=None, c=None):
    print(a)
    print(b)
    print(c)


try:
    from scipy import genfromtxt as genfromtxt
except ImportError:
    from numpy import genfromtxt as genfromtxt


def loadct(num, **kwargs):
    file = os.path.join(ifigure.__path__[0], 'resources', 'idl_colors.txt',)

    output = genfromtxt(file,
                        skip_header=256*num,
                        skip_footer=(39-num)*256)/255.
    return matplotlib.colors.LinearSegmentedColormap.from_list('idl'+str(num),
                                                               output, **kwargs)


def register_idl_colormaps():
    from matplotlib.cm import register_cmap
    names = []
    for x in range(40):
        cmap = loadct(x)
        name = 'idl'+str(x)
        register_cmap(name=name, cmap=cmap)
        names.append(name)
    return names


def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    import re
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless',
        '>': r'\textgreater',
    }
    if six.PY2:
        regex = re.compile('|'.join(re.escape(unicode(key))
                                    for key in sorted(list(conv.keys()), key=lambda item: - len(item))))
    else:
        regex = re.compile('|'.join(re.escape(key)
                                    for key in sorted(list(conv.keys()), key=lambda item: - len(item))))

    return regex.sub(lambda match: conv[match.group()], text)


def escape_split(s, delim):
    ret = []
    current = []
    itr = iter(s)
    for ch in itr:
        if ch == '\\':
            try:
                # skip the next character; it has been escaped!
                current.append('\\')
                current.append(next(itr))
            except StopIteration:
                pass
        elif ch == delim:
            # split! (add current to the list and reset it)
            ret.append(''.join(current))
            current = []
        else:
            current.append(ch)
    ret.append(''.join(current))
    return ret


def tex_escape_equation(text):
    arr = escape_split(text, '$')
#    print arr
#    if arr[0] != '':
#        arr2 = [x if i%2 else tex_escape(x) for i,x in enumerate(arr)]
#    else:
#        arr2 = [x if not i%2 else tex_escape(x) for i,x in enumerate(arr)]
    arr2 = [x if i % 2 else tex_escape(x) for i, x in enumerate(arr)]
    delim = ['$']*(len(arr)-1)
    if len(delim) % 2:
        delim[-1] = '\$'
    return ''.join([x+y for x, y in zip(arr2, delim+[''])])
#    if arr[0] != '':
#       return ''.join([x+y for x, y in zip(arr2, delim+[''])])
#    else:
#        return ''.join([y+x for x, y in zip(arr2, delim+[''])])
#    if arr[0] == '': arr[0] = '\\'
#    return '$'.join(arr)


def walk_OD_tree(od, basekey=''):
    '''
    walk OrdereDictionary tree
    '''
    import collections
    for key in list(od.keys()):
        if isinstance(od[key], collections.OrderedDict):
            if basekey == '':
                basekey2 = key
            else:
                basekey2 = basekey+'.'+key
            for key2 in walk_OD_tree(od[key], basekey=basekey2):
                #               yield key2, data
                yield key2
        else:
            if basekey == '':
                basekey2 = key
            else:
                basekey2 = basekey+'.'+key
#           yield basekey2, od[key]
            yield basekey2


def read_OD_tree(od, keys):
    arr = keys.split('.')
    ret = od
    for k in arr:
        ret = ret[k]
    return ret


class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(
            current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

        self.show_detail()

    def show_detail(self):
        print(("Added:", self.added()))
        for item in self.added():
            print((item, ':', self.current_dict[item]))

        print(("Removed:", self.removed()))
        for item in self.removed():
            print((item, ':', self.past_dict[item]))

        print(("Changed:", self.changed()))
        for item in self.changed():
            print((item, ':', self.current_dict[item], self.past_dict[item]))

        print(("Unchanged:", self.unchanged()))

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])
