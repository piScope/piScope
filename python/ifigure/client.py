
"""Compatibility layer for the no-app interactive backend which
uses:
    from ifigure.client import *

Public imports should use:

    from ifigure.interactive import *

ifigure.interactive auto-selects app vs no-app backend at runtime.
No-app implementation now lives in ifigure._private.interactive_noapp.
"""
from ifigure._private.interactive_noapp import *
