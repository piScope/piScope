from __future__ import print_function

"""Compatibility layer for the no-GUI interactive backend which
uses:
    from ifigure.client import *

Public imports should use:

    from ifigure.interactive import *

ifigure.interactive auto-selects GUI vs no-GUI backend at runtime.
No GUI implementation now lives in ifigure._private.interactive_nogui.
"""
from ifigure._private.interactive_nogui import *
