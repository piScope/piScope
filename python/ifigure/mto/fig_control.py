from __future__ import print_function
import weakref
import traceback
import wx


class FigControl(object):
    def __init__(self):
        self._cc_callback_name = None
        self._cc_callback_obj = None

    def set_control_changed_callback(self, obj, name):
        self._cc_callback_name = name
        self._cc_callback_obj = weakref.ref(obj)

    def call_control_changed_callback(self):
        if self._cc_callback_name is None:
            return
        try:
            m = getattr(self._cc_callback_obj(), self._cc_callback_name)
        except:
            print(('callback not found', self))
            traceback.print_exc()
            return
        try:
            wx.CallAfter(m, self)
        except:
            traceback.print_exc()
