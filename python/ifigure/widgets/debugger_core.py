import bdb
from bdb import Bdb
break_points = {}


class Debugger(Bdb):
    def __init__(self, panel, *args, **kargs):
        Bdb.__init__(self, *args, **kargs)
        self.panel = panel

    def user_call(self, frame, argument_list):
        #       print 'user_call', frame
        self.panel.handle_user_call(frame, argument_list)
#       Bdb.user_call(self, frame, argument_list)

    def user_line(self, frame):
        #       print 'user_line', frame
        self.panel.handle_user_line(frame)
#       return frame
#       Bdb.user_line(self, frame)

    def user_return(self, frame, return_value):
        #       print 'user_return', frame
        self.panel.handle_user_return(frame, return_value)
#       Bdb.user_return(self, frame, return_value)

    def user_exception(self, frame, exc_info):
        #       print 'user_exception', frame
        self.panel.handle_user_exception(frame, exc_info)
#       Bdb.user_exception(self, frame, exc_info)

    def do_clear(self, arg):
        pass
#       print 'do_clear'
#       Bdb.do_clear(self, arg)

    def run(self, *args, **kargs):
        Bdb.run(self, *args, **kargs)


def get_debugger(panel=None):
    d = Debugger(panel)
    for file in break_points:
        for line in break_points[file]:
            d.set_break(d.canonic(file), line)
    return d


def add_breakpoint(file, line):
    #    print file, line
    if file in break_points:
        if not line in break_points[file]:
            break_points[file].append(line)
    else:
        break_points[file] = [line]

#    d = get_debugger()
#    d.set_break(d.canonic(file), line)
#    print d.get_all_breaks()


def rm_breakpoint(file, line):
    if not file in break_points:
        return
    if not line in break_points[file]:
        return
    break_points[file].remove(line)


def has_breakpoint(file, line):
    if not file in break_points:
        return False
    return (line in break_points[file])


def get_breakpoint(file):
    if not file in break_points:
        return []
    return break_points[file]
