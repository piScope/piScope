import wx
import numpy as np
from weakref import ProxyType

isWX3 = (wx.__version__[0] == '3')

if isWX3:
    from wx._core import PyDeadObjectError
else:
    # wx4
    PyDeadObjectError = RuntimeError

if isWX3:
    from wx.aui import EVT__AUINOTEBOOK_TAB_MIDDLE_DOWN as EVT_AUINOTEBOOK_TAB_MIDDLE_DOWN
    from wx.aui import EVT__AUINOTEBOOK_TAB_RIGHT_DOWN as EVT_AUINOTEBOOK_TAB_RIGHT_DOWN
    from wx.aui import EVT__AUINOTEBOOK_TAB_RIGHT_UP as EVT_AUINOTEBOOK_TAB_RIGHT_UP
    from wx.aui import EVT__AUINOTEBOOK_TAB_MIDDLE_UP as EVT_AUINOTEBOOK_TAB_MIDDLE_UP
else:
    from wx.aui import EVT_AUINOTEBOOK_TAB_MIDDLE_DOWN
    from wx.aui import EVT_AUINOTEBOOK_TAB_RIGHT_DOWN
    from wx.aui import EVT_AUINOTEBOOK_TAB_RIGHT_UP
    from wx.aui import EVT_AUINOTEBOOK_TAB_MIDDLE_UP

if isWX3:
    from wx import TaskBarIcon as wxTaskBarIcon
    from wx import TBI_DOCK, TBI_CUSTOM_STATUSITEM, TBI_DEFAULT_TYPE
    from wx import EVT_TASKBAR_MOVE, EVT_TASKBAR_LEFT_DOWN, EVT_TASKBAR_LEFT_UP
    from wx import EVT_TASKBAR_RIGHT_DOWN, EVT_TASKBAR_RIGHT_UP, EVT_TASKBAR_LEFT_DCLICK
    from wx import EVT_TASKBAR_RIGHT_DCLICK, EVT_TASKBAR_CLICK
    from wx.combo import BitmapComboBox as wxBitmapComboBox
    from wx import IconFromBitmap
    from wx import EmptyImage as wxEmptyImage
    from wx import StockCursor as wxStockCursor
    from wx import CursorFromImage as wxCursorFromImage
    from wx import BitmapFromImage as wxBitmapFromImage
    from wx import NamedColour as wxNamedColour
    from wx import EmptyBitmapRGBA as wxEmptyBitmapRGBA
    from wx.grid import PyGridTableBase as GridTableBase

else:
    from wx.adv import TaskBarIcon as wxTaskBarIcon
    from wx.adv import TBI_DOCK, TBI_CUSTOM_STATUSITEM, TBI_DEFAULT_TYPE
    from wx.adv import EVT_TASKBAR_MOVE, EVT_TASKBAR_LEFT_DOWN, EVT_TASKBAR_LEFT_UP
    from wx.adv import EVT_TASKBAR_RIGHT_DOWN, EVT_TASKBAR_RIGHT_UP, EVT_TASKBAR_LEFT_DCLICK
    from wx.adv import EVT_TASKBAR_RIGHT_DCLICK, EVT_TASKBAR_CLICK
    from wx.adv import BitmapComboBox as wxBitmapComboBox
    from wx import Icon as IconFromBitmap
    from wx import Image as wxEmptyImage
    from wx import Cursor as wxStockCursor
    from wx import Cursor as wxCursorFromImage
    from wx import Bitmap as wxBitmapFromImage
    from wx import Colour as wxNamedColour
    wxEmptyBitmapRGBA = wx.Bitmap.FromRGBA
    from wx.grid import GridTableBase


def deref_proxy(w):
    if isWX3:
        return w
    if isinstance(w, ProxyType):
        w = w.__repr__.__self__
    return w


def wrap_method(m_wx3, m_wx4):
    def real_decorator(func):
        def wrap(obj, *args, **kwargs):
            if isWX3:
                m = getattr(obj, m_wx3)
            else:
                m = getattr(obj, m_wx4)
            args, kwargs = func(obj, *args, **kwargs)
            return m(*args, **kwargs)
        return wrap
    return real_decorator


def image2array(image):
    if isWX3:
        return np.fromstring(image.GetData(), dtype=np.uint8)
    else:
        return np.fromstring(bytes(image.GetData()), dtype=np.uint8)


def image_GetAlpha(image):
    if isWX3:
        return image.GetAlphaData()
    else:
        return image.GetAlpha()


def image_SetAlpha(image, array):
    if isWX3:
        return image.SetAlphaData(array.tobytes())
    else:
        return image.SetAlpha(array.tobytes())


def tree_InsertItemBefore(tree, pitem, pos, label, image=-1, selImage=-1, data=None):
    if isWX3:
        return tree.InsertItemBefore(pitem, pos, label, image=image)
    else:
        return tree.InsertItem(pitem, pos, label, image=image, selImage=selImage, data=data)


def grid_ClientSizeTuple(grid, *args, **kwargs):
    if isWX3:
        return grid.ClientSizeTuple()
    else:
        return grid.ClientSize


@wrap_method('SetOptionInt', 'SetOption')
def image_SetOptionInt(image, *args, **kwargs):
    return args, kwargs


@wrap_method('SetPyData', 'SetItemData')
def tree_SetItemData(tree, *args, **kwargs):
    return args, kwargs


@wrap_method('GetPyData', 'GetItemData')
def tree_GetItemData(tree, *args, **kwargs):
    return args, kwargs


@wrap_method('SetToolTipString', 'SetToolTip')
def panel_SetToolTip(panel, *args, **kwargs):
    return args, kwargs


@wrap_method('GetPositionTuple', 'GetPosition')
def evt_GetPosition(evt, *args, **kwargs):
    return args, kwargs


@wrap_method('AppendMenu', 'Append')
def menu_Append(menu, *args, **kwargs):
    return args, kwargs

menuitems = {}
def menu_AppendSubMenu(menu, *args, **kwargs):
    if isWX3:
        return menu.Append(*args, **kwargs)
    else:
        # this one replaces the following....
        #   menu_Append(helpmenu, ID_WINDOWS, 'Viewers...', self._windowmenu)
        if isinstance(args[0], wx.WindowIDRef):# and not args[0] in menuitems:
            assert False, "This does not work anymore, change your code"
            '''
            if args[0] not in menuitems:
                item = wx.MenuItem(menu, id=args[0], text=args[1], subMenu=args[2])
                menuitems[args[0]] = (item, args[2])
            else:
                item = menuitems[args[0]][0]
            return menu.Append(item)
            '''
        else:
            return menu.AppendSubMenu(args[2], args[1])

@wrap_method('AppendItem', 'Append')
def menu_AppendItem(menu, *args, **kwargs):
    return args, kwargs

@wrap_method('RemoveItem', 'Remove')
def menu_RemoveItem(menu, *args, **kwargs):
    return args, kwargs


def GridSizer(*args, **kwargs):
    if not 'hgap' in kwargs:
        kwargs['hgap'] = 0
    if not 'vgap' in kwargs:
        kwargs['vgap'] = 0
    if len(args) == 2:
        kwargs['rows'] = args[0]
        kwargs['cols'] = args[1]
    elif len(args) == 1:
        kwargs['cols'] = args[0]
    elif len(args) == 0:
        kwargs['cols'] = 1
    return wx.GridSizer(**kwargs)


def FlexGridSizer(*args, **kwargs):
    if not 'hgap' in kwargs:
        kwargs['hgap'] = 0
    if not 'vgap' in kwargs:
        kwargs['vgap'] = 0
    if len(args) == 2:
        kwargs['rows'] = args[0]
        kwargs['cols'] = args[1]
    elif len(args) == 1:
        kwargs['cols'] = args[0]
    elif len(args) == 0:
        kwargs['cols'] = 1
    return wx.FlexGridSizer(**kwargs)


def TextEntryDialog(*args, **kwargs):
    parent = args[0]
    message = args[1]
    value = kwargs.pop('value', None)
    if value is None:
        value = kwargs.pop('defaultValue', None)
    if value is None:
        value = ''

    if len(args) > 2:
        kwargs['caption'] = args[2]
    if len(args) > 3:
        value = args[3]
    if isWX3:
        kwargs['defaultValue'] = value
    else:
        kwargs['value'] = value
        parent = deref_proxy(parent)
    return wx.TextEntryDialog(parent, message, **kwargs)
