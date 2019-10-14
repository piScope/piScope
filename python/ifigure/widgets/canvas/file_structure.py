from __future__ import print_function
import struct


def idltype2unitsize(x):
    # x is type code in IDL
    # returns unitsize
    units = {"1": 1,
             "2": 2,
             "3": 4,
             "4": 4,
             "5": 8,
             "6": 8,
             "7": 1,
             "9": 16,
             "12": 2,
             "13": 4,
             "14": 8,
             "15": 8,
             }
    return units[str(x)]


def idltype2code(x):
    # x is type code in IDL
    # returns unitsize
    units = {'1': "b",
             '2': "h",
             '3': "l",
             '4': "f",
             '5': "d",
             '6': "f",
             '7': "s",
             '9': "d",
             '12': "H",
             '13': "L",
             '14': "q",
             '15': "Q",
             }
    return units[str(x)]


def idl2python_type(s):

    #   IDL definition of type code
    #   0:  undefined
    #   1:  byte
    #   2:  integer
    #   3:  long
    #   4:  float
    #   5:  double
    #   6:  complex
    #   7:  string
    #   8:  structure
    #   9:  double complex
    #  10:  pointer
    #  11:  obj ref
    #  12:  unsigned int
    #  13:  unsigned long
    #  14:  long64
    #  15:  unsigned long64

    #  size(a) in IDL returns
    #    [ndim, length of each dimension, type-code, total number of element]

    idltype = s[len(s)-2]

    unit = 0
    code = ""
    iscomplex = 0

    unitsize = idltype2unitsize(idltype)
    code = idltype2code(idltype)
    if idltype == 6:
        iscomplex = 1
    if idltype == 9:
        iscomplex = 1

    return [unitsize, code, iscomplex]


def read_structure(fin):

    val = {}
    x = struct.unpack('l', fin.read(4))
    n = x[0]
    if n == 0:
        return val

    k = 1

    while k <= n:
        btag = struct.unpack('l', fin.read(4))

        tag = struct.unpack(str(btag[0])+"s", fin.read(btag[0]))
        print(tag)
        ndim = struct.unpack('l', fin.read(4))

        sz = struct.unpack(str(ndim[0]+2)+'l', fin.read(4*(ndim[0]+2)))

        nele = sz[len(sz)-1]
        print(nele)
        [unit, code, iscomplex] = idl2python_type(sz)
        if iscomplex:
            array = struct.unpack(str(nele*2)+code,  fin.read(unit*2*nele))
        else:
            array = struct.unpack(str(nele)+code,  fin.read(unit*nele))

        print(array)
        # should modify the dim and complex here
        if nele == 1:
            val[tag[0].upper()] = array[0]
        else:
            val[tag[0].upper()] = array[0:]
        k = k+1

    return val
