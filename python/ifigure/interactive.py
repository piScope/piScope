from __future__ import print_function

"""
Public entry point to plotting routines.

Runtime dispatch:
- Inside a live piScope app process: route to ifigure._private.interactive_wxapp.
- Outside piScope app process: route to ifigure._private.interactive_noapp.

"""

import importlib
from ifigure._private.interactive_common import (
    WXAPP_API,
    COMMON_API,
    DOCS,
    NOAPP_API,
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


def _get_noapp_backend():
    return importlib.import_module('ifigure._private.interactive_noapp')


def _get_app_backend():
    return importlib.import_module('ifigure._private.interactive_wxapp')


def _get_backend():
    if _in_piscope_gui_process():
        return _get_app_backend()
    return _get_noapp_backend()


_ACTIVE_BACKEND = _get_backend()


def _bind_public_api():
    is_app_backend = _ACTIVE_BACKEND.__name__.endswith('interactive_wxapp')
    is_noapp_backend = _ACTIVE_BACKEND.__name__.endswith('interactive_noapp')

    for _name in PUBLIC_API:
        if _name in COMMON_API:
            target = getattr(_ACTIVE_BACKEND, _name)
        elif is_app_backend and _name in WXAPP_API:
            target = getattr(_ACTIVE_BACKEND, _name)
        elif is_noapp_backend and _name in NOAPP_API:
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
    if _ACTIVE_BACKEND.__name__.endswith('interactive_wxapp'):
        if name in WXAPP_API:
            return getattr(_ACTIVE_BACKEND, name)
        raise AttributeError(name)
    if _ACTIVE_BACKEND.__name__.endswith('interactive_noapp'):
        if name in NOAPP_API:
            return getattr(_ACTIVE_BACKEND, name)
        raise AttributeError(name)
    raise AttributeError(name)


__all__ = [n for n in globals() if not n.startswith('_')]
