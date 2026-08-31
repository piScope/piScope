from __future__ import print_function

"""
Public entry point to plotting routines.

Runtime dispatch:
- Inside a live piScope GUI process: route to ifigure._private.interactive_gui.
- Outside piScope GUI: route to ifigure._private.interactive_nogui.

"""

import importlib
from ifigure._private.interactive_docs import DOCS


def _in_piscope_gui_process():
    try:
        wx = importlib.import_module('wx')
    except Exception:
        return False

    try:
        app = wx.GetApp()
    except Exception:
        return False

    if app is None:
        return False

    top = getattr(app, 'TopWindow', None)
    if top is None:
        try:
            top = app.GetTopWindow()
        except Exception:
            top = None

    return top is not None


def _get_nogui_backend():
    return importlib.import_module('ifigure._private.interactive_nogui')


def _get_gui_backend():
    return importlib.import_module('ifigure._private.interactive_gui')


def _get_backend():
    if _in_piscope_gui_process():
        return _get_gui_backend()
    return _get_nogui_backend()


def _resolve_target(name):
    backend = _get_backend()
    if hasattr(backend, name):
        return getattr(backend, name)

    # Fallback allows utility calls (for example launch/shutdown) that are
    # implemented only in one backend to remain accessible.
    if backend.__name__.endswith('interactive_gui'):
        other = _get_nogui_backend()
    else:
        try:
            other = _get_gui_backend()
        except Exception:
            other = None

    if other is not None and hasattr(other, name):
        return getattr(other, name)

    raise AttributeError(name)


def _dispatch_name(name):
    def _wrapped(*args, **kargs):
        target = _resolve_target(name)
        return target(*args, **kargs)

    _wrapped.__name__ = name
    _wrapped.__qualname__ = name
    _wrapped.__module__ = __name__
    doc = DOCS.get(name)
    if doc:
        _wrapped.__doc__ = doc

    return _wrapped


_PLOT_API_NAMES = [
    'figure', 'hold', 'update',
    'showpage', 'cla', 'cls', 'clf', 'nsec', 'nsection',
    'subplot', 'isec', 'isection', 'addpage', 'delpage',
    'suptitle', 'title',
    'xlabel', 'xtitle', 'ylabel', 'ytitle', 'zlabel', 'ztitle',
    'clabel', 'ctitle',
    'xlog', 'ylog', 'clog', 'zlog',
    'xsymlog', 'ysymlog', 'zsymlog', 'csymlog',
    'xlinear', 'ylinear', 'clinear', 'zlinear',
    'xauto', 'yauto', 'zauto', 'cauto',
    'xlim', 'ylim', 'zlim', 'clim',
    'twinx', 'twiny',
    'oplot', 'oerrorbar',
    'loglog', 'semilogy', 'semilogx',
    'timetrace', 'plotc', 'errorbarc',
    'plot', 'scatter', 'hist', 'triplot', 'errorbar', 'annotate',
    'ispline', 'contour', 'contourf', 'quiver', 'quiver3d',
    'image', 'specgram', 'spec', 'tripcolor', 'tricontour',
    'tricontourf', 'axline', 'axlinec', 'axspan', 'axspanc',
    'text', 'figtext', 'arrow', 'figarrow', 'legend', 'fill',
    'fill_between', 'fill_betweenx', 'fill_between_3d', 'surf',
    'surface', 'revolve', 'solid', 'trisurf', 'property', 'threed',
    'lighting', 'view',
    'xnames', 'ynames', 'znames', 'cnames',
    'cbar', 'savefig', 'savedata',
]

_CONTROL_API_NAMES = [
    'get', 'put', 'detach',
    'launch', 'shutdown', 'connect', 'server',
    'check_connection', 'make_testplot', 'execute',
]

for _name in _PLOT_API_NAMES + _CONTROL_API_NAMES:
    globals()[_name] = _dispatch_name(_name)

def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    return _resolve_target(name)


__all__ = [n for n in globals() if not n.startswith('_')]
