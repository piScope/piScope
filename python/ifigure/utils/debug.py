from __future__ import print_function
#####################################
#
# debug.py
#
#    provide a simple interface to make debug prints
#    allow for controling turn on and off of debug
#    print for each module
#
# Usage:
#    (in import section)
#    import ifigure.utils.debug as debug
#    dprint1, dprint2, dprint3 = debug.init_dprints('ArgsParser', level=0)
#
#    (then use it as follows)
#    debug.set_level('ArgsParser', 1)  # set level for ArsgParser 1
#    dprint1('hogehogehoge')           # print something
#
#    level 1 (dprint1) : usr feedback which will be turn on normally
#    level 2 (dprint2) : first level of debug print
#    level 3 (dprint3) : second level of debug print
#    setting debug_default_level to 0 will turn off all error print
#    (silent mode)


import sys
import traceback
from ifigure.widgets.redirect_output import RedirectOutput

debug_mode = 1
debug_modes = {}
debug_default_level = 1

debug_stdout = RedirectOutput(sys.stdout, sys.stderr)


def dprint(*args):
    s = ''
    for item in args:
        s = s + ' ' + str(item)
    if debug_mode != 0:
        import sys
        ostdout = sys.stdout
        sys.stdout = debug_stdout
        print('DEBUG('+str(debug_mode)+')::'+s)
        sys.stdout = ostdout


def find_by_id(_id_):
    '''
    find an object using id 
    '''
    import gc
    for obj in gc.get_objects():
        if id(obj) == _id_:
            return obj
    raise Exception("No found")


class DPrint(object):
    def __init__(self, name, level):
        self.name = name
        self.level = level

    def __call__(self, *args, **kargs):
        if 'stack' in kargs:
            traceback.print_stack()
        s = ''
        for item in args:
            s = s + str(item)
        if debug_modes[self.name] >= self.level:
            import sys
            ostdout = sys.stdout
            sys.stdout = debug_stdout
            print('DEBUG('+str(self.name)+')::'+s)
            sys.stdout = ostdout


def prints(n):
    return DPrint(n, 1), DPrint(n, 2), DPrint(n, 3)


def set_level(name, level):
    debug_modes[name] = level


def init_dprints(name, level=debug_default_level):
    set_level(name, level)
    return prints(name)

