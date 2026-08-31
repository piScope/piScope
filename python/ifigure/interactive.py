from __future__ import print_function

"""
Public entry point to plotting routines.

Runtime dispatch:
- Inside a live piScope GUI process: route to ifigure._private.interactive_gui.
- Outside piScope GUI: route to ifigure._private.interactive_nogui.

"""

import importlib
from ifigure._private.interactive_common import (
    COMMON_API,
    DOCS,
    GUI_API,
    NOGUI_API,
    PUBLIC_API,
)


def _in_piscope_gui_process():
    """Prefer the GUI backend whenever a wx app is active.

    A GUI application can exist before its main window is assigned to
    ``TopWindow`` or before ``GetTopWindow()`` is available. In that case,
    treating the app as non-GUI is incorrect and causes the wrong backend to
    be imported at module import time.
    """
    try:
        wx = importlib.import_module('wx')
    except Exception:
        return False

    try:
        app = wx.GetApp()
    except Exception:
        return False

    return app is not None


def _get_nogui_backend():
    return importlib.import_module('ifigure._private.interactive_nogui')


def _get_gui_backend():
    return importlib.import_module('ifigure._private.interactive_gui')


def _get_backend():
    if _in_piscope_gui_process():
        return _get_gui_backend()
    return _get_nogui_backend()


_ACTIVE_BACKEND = _get_backend()


def _bind_public_api():
    is_gui_backend = _ACTIVE_BACKEND.__name__.endswith('interactive_gui')
    is_nogui_backend = _ACTIVE_BACKEND.__name__.endswith('interactive_nogui')

    for _name in PUBLIC_API:
        if _name in COMMON_API:
            target = getattr(_ACTIVE_BACKEND, _name)
        elif is_gui_backend and _name in GUI_API:
            target = getattr(_ACTIVE_BACKEND, _name)
        elif is_nogui_backend and _name in NOGUI_API:
            target = getattr(_ACTIVE_BACKEND, _name)
        else:
            continue
        globals()[_name] = target

    for _name in list(globals()):
        if _name.startswith('_'):
            continue
        doc = DOCS.get(_name)
        if doc:
            globals()[_name].__doc__ = doc


_bind_public_api()


def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    if name in COMMON_API:
        return getattr(_ACTIVE_BACKEND, name)
    if _ACTIVE_BACKEND.__name__.endswith('interactive_gui'):
        if name in GUI_API:
            return getattr(_ACTIVE_BACKEND, name)
        raise AttributeError(name)
    if _ACTIVE_BACKEND.__name__.endswith('interactive_nogui'):
        if name in NOGUI_API:
            return getattr(_ACTIVE_BACKEND, name)
        raise AttributeError(name)
    raise AttributeError(name)


__all__ = [n for n in globals() if not n.startswith('_')]
