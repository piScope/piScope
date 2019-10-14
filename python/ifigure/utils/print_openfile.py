from __future__ import print_function
import __builtin__
openfiles = set()
oldfile = __builtin__.file


class newfile(oldfile):
    def __init__(self, *args):
        self.x = args[0]
        print("### OPENING %s ###" % str(self.x))
        oldfile.__init__(self, *args)
        openfiles.add(self)

    def close(self):
        print("### CLOSING %s ###" % str(self.x))
        oldfile.close(self)
        openfiles.remove(self)


oldopen = __builtin__.open


def newopen(*args):
    return newfile(*args)


__builtin__.file = newfile
__builtin__.open = newopen


def printOpenFiles():
    print("### %d OPEN FILES: [%s]" % (
        len(openfiles), ", ".join(f.x for f in openfiles)))
