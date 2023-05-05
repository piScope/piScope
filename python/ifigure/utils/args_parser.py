from __future__ import print_function
#
#   ArgsParser
#
#   argument parser
#
#   usage :
#
#   def hogehoge(*args, **kywds):
#      '''
#      hogehoge(x,  w=None)
#      hogehoge(x, y, w=None, o=xxx...)
#      '''
#
#      p = ArgsParser()
#      p.add_var('x', check)   ### mandatory argument
#      p.add_opt('y', 1, check)  ### optional argument
#      p.add_key('w', None) ### keyword argment
#
#      p.set_pair('x', 'y') ### require x and y need to be given togehter
#      p.set_pair('n', 'w') ### require n and w are not given togehter
#
#      p.set_ndconvert("x") ### convert x to ndarray if possible
#                           ### x should be iterable for this conversion
#      check : type check
#         'ndarray': check if it is ndarray
#         'iter' : check if it is array
#         'str'  : check if it is string
#         'int'  : check if it is int
#         'float'  : check if it is float
#         'nonstr'  : check if it is not str
#         'real'  : check if it is either float or int
#         'bool'  : check if it is bool
#         'dynamic'  : check if it is dynamic expression
#         'sequence'  : check if it is sequence
#         'number':  numbers (int, long, float, complex)
#         'numbers': sequence of numbers
#         'empty' : check if it is []
#
#      check can be list and conncted by '|'
#         ['float', 'int'] :
#          True if it is number ( = same as ['real'])
#         ['iter|nonstr', 'dynamic'] :
#          True if it is either 'dynamic' or 'iterable and not string'
#
#      v, kywds, flag = p.process(*args, **kywds)
#
#      v is a dict v[name] = value
#      kywds is remaining keywords which is not processed
#      flag is True if rule is successfully applied
#
from ifigure.utils.cbook import isiterable, isndarray, isdynamic, issequence, isnumber
import six
import numpy as np
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('ArgsParser')


def bit(n, l):
    if n == 0:
        return [0]*l
    v = [0]*l
    k = 0
    while n >= 2**k:
        v[k] = int((n & 2**k) != 0)
        k = k+1
    return v


def convert_ndarray(v, name):
    if name not in v:
        return v
    if v[name] is None:
        return v
    if isdynamic(v[name]):
        return v
    if isiterable(v[name]) and not isndarray(v[name]):
        try:
            v[name] = np.array(v[name])
        except:
            return v
    if not isiterable(v[name]):
        try:
            v[name] = np.array([v[name]])
        except:
            return v
    if np.iscomplex(v[name]).any():
        return v
    if np.iscomplexobj(v[name]):
        v[name] = v[name].real
    else:
        v[name] = v[name].astype(np.float64)
    return v


def apply_squeeze(v, name, minimum_1D=False):
    if name not in v:
        return v
    if isdynamic(v[name]):
        return v
    try:
        if (v[name] is not None and not minimum_1D):
            v[name] = np.squeeze(v[name])
        if (v[name] is not None and minimum_1D and
                v[name].dim > 1):
            v[name] = np.squeeze(v[name])
    except:
        pass
    return v


class ArgsParser(object):
    def __init__(self):
        self.vars = []
        self.key = []
        self.exclusives = []
        self.pairs = []
        self.ndconvert = []
        self.squeeze = []
        self.squeeze1D = []
        self.defv_list = []

    def add_var(self, name, t=None):
        self.vars.append((name, t))

    def add_opt(self, name, defv, t=None):
        self.vars.append((name, defv, t))

    def add_key(self, key, defv, t=None):
        self.key.append((key, defv, t))

    def set_default_list(self, defv_list):
        self.defv_list = defv_list

    def add_key2(self, key, t=None):
        if isinstance(key, tuple):
            for k in key:
                self.key.append((k, self.defv_list[k], None))
        else:
            self.key.append((key, self.defv_list[key], t))

    def set_exclusive(self, name1, name2):
        self.exclusives.append((name1, name2))

    def set_pair(self, name1, name2):
        self.pairs.append((name1, name2))

    def set_ndconvert(self, *args):
        for n in args:
            self.ndconvert.append(n)

    def set_squeeze(self, *args):
        for n in args:
            self.squeeze.append(n)

    def set_squeeze_minimum_1D(self, *args):
        for n in args:
            self.squeeze1D.append(n)

    def check_pairs(self, value):
        flag = True
        for name1, name2 in self.pairs:
            if (name1 not in value and
                    name2 in value):
                flag = False
            if (name1 in value and
                    name2 not in value):
                flag = False
        return flag

    def check_exclusives(self, value):
        flag = True
        for name1, name2 in self.exclusives:
            if (name1 in value and
                    name2 in value):
                flag = False
            if (name1 in value and
                    name2 in value):
                flag = False
        return flag

    def has_exclusives(self, name, value):
        for name1, name2 in self.exclusives:
            if name1 == name:
                return name2 in value
            if name2 == name:
                return name1 in value
        return False

    def check(self, value, incond):
        def do_check(value, cond):
            if cond == 'ndarray':
                return isndarray(value)
            if cond == 'can_ndreal_array':
                try:
                    void = np.array(value).astype(np.float64)
                    return void.size > 0
                except:
                    pass
                return False
            elif cond == 'iter':
                return isiterable(value)
            elif cond == 'sequence':
                return issequence(value)
            elif cond == 'str':
                if six.PY2:
                    return isinstance(value, str) or isinstance(value, unicode)
                else:
                    return isinstance(value, str)
            elif cond == 'nonstr':
                if six.PY2:                
                    return not (isinstance(value, str) or isinstance(value, unicode))
                else:
                    return not isinstance(value, str)
            elif cond == 'int':
                return isinstance(value, int)
            elif cond == 'float':
                return isinstance(value, float)
            elif cond == 'real':
                return isinstance(value, float) or isinstance(value, int)
            elif cond == 'dynamic':
                return isdynamic(value)
            elif cond == 'bool':
                return isinstance(value, bool)
            elif cond == 'number':
                return isnumber(value)
            elif cond == 'empty':
                if (isinstance(value, list) and
                        len(value) == 0):
                    return True
                return False
            elif cond == 'numbers':
                if issequence(value):
                    if len(value) == 0:
                        return False
                    return isnumber(value[0])
                else:
                    return False
            elif cond == 'any':
                return True
            print(('ArgsParser::Unknown condition (ignored)', cond))
            return True

        def do_check2(value, conds):
            ret = True
            cond = conds.split('|')
            for c in cond:
                ret = ret and do_check(value, c)
            return ret

        if isiterable(incond) and not isinstance(incond, str):
            a = False
            for c in incond:
                a = a or do_check2(value, c)
            return a
        else:
            return do_check(value, incond)

    def process(self, *args, **kywds):
        success = True
        value = {}
        flag = True
        cases = [bit(i, len(self.vars)) for i in range(2**len(self.vars))]
        
        for case in cases:
            # check length of arguments
            if sum(case) != len(args):
                continue

            # check required field selection
            k = 0
            flag = True
            for v in self.vars:
                if len(v) == 2 and case[k] == 0:
                    flag = False
                k = k+1
            if not flag:
                continue

            k1 = 0
            k2 = 0
            flag = True
            value = {}
            for v in self.vars:
                if case[k1] == 1:
                    if not self.check(args[k2], v[-1]):
                        flag = False
                        break
                    value[v[0]] = args[k2]
                    k2 = k2 + 1
                k1 = k1+1
            # check pairs
            if not self.check_pairs(value):
                flag = False
            if not self.check_exclusives(value):
                flag = False
            if flag:
                break

        if not flag:
            return {}, kywds, [], False

        # add optional using default value
        # add only parameter which counterpart of exclusive
        ### pair is not set
        defv_names = []
        for v in self.vars:
            if (len(v) == 3 and v[0] not in value and
                    not self.has_exclusives(v[0], value)):
                value[v[0]] = v[1]
                defv_names.append(v[0])

        # handle keyword values
        for key, v, t in self.key:
            if key in kywds:
                #               value.append((key, kywds[key]))
                val = kywds[key]
                if t is not None:
                    if not self.check(val, t):
                        dprint1('keyword type error : ', key)
                        return {}, kywds, [], False
                value[key] = val
                del kywds[key]
            else:
                value[key] = v
                defv_names.append(key)
#               value.append((key, v))

        for name in self.ndconvert:
            value = convert_ndarray(value, name)

        for name in self.squeeze:
            value = apply_squeeze(value, name)
        for name in self.squeeze1D:
            value = apply_squeeze(value, name, minimum_1D=True)
        return value, kywds, defv_names, success


if __name__ == '__main__':
    def hogehoge1(*args, **kywds):
        '''
        hogehoge(x,  w=None)
        hogehoge(x, y, w=None, o=xxx...)
        '''

        p = ArgsParser()
        p.add_var('x')  # mandatory argument
        p.add_opt('y', 'default y')  # optional argument
        p.add_key('w', 'default keyword')  # keyword argment

        v, kywds, defv_names,  flag = p.process(*args, **kywds)
        print((v, kywds, defv_names, flag))

    def hogehoge2(*args, **kywds):
        '''
        hogehoge(y, s  w=None)
        hogehoge(x, y, s, w=None, o=xxx...)

        same as plot
        '''
        p = ArgsParser()
        p.add_opt('x', None, ['iter|nonstr', 'dynamic'])  # optional argument
        p.add_var('y', ['iter|nonstr', 'dynamic'])  # mandatory argument
        p.add_opt('s', 'default s', 'str')  # optional argument
        p.add_key('w', 'default keyword')  # keyword argment
        p.set_ndconvert('x', 'y')
        p.set_squeeze_minimum_1D('x', 'y')
#      p.set_squeeze('x', 'y')

        v, kywds, d, flag = p.process(*args, **kywds)
        print((v, kywds, d, flag))

    def hogehoge3(*args, **kywds):
        '''
        hogehoge(z)
        hogehoge(x, y, z)
        hogehoge(z, n)
        hogehoge(z, v)
        hogehoge(x, y, z, n)
        hogehoge(x, y, z, v)

        same as contour
        '''
        p = ArgsParser()
        p.add_opt('x', None, ['iter'])  # optional argument
        p.add_opt('y', None, ['iter'])  # optional argument
        p.add_var('z', ['iter'])  # mandatory argument
        p.add_opt('n', None, ['int', 'float'])  # optional argument
        p.add_opt('v', None, ['iter'])  # optional argument
        p.set_pair('x', 'y')
        p.set_exclusive('n', 'v')

        v, kywds, d, flag = p.process(*args, **kywds)
        print((v, kywds, d, flag))

    print("hogehoge1(x, y(option), w='default keyword)")
    print('case 1')
    print("   hogehoge1([1,3,5], 'new y')")
    hogehoge1([1, 3, 5], 'new y')
    print('')
    print('case 2')
    print("   hogehoge1([1,3,5], w='new keyword', other='???')")
    hogehoge1([1, 3, 5], w='new keyword', other='???')
    print('')
    print('case 3 (shoud have flag = False)')
    print("   hogehoge( w='new keyword')")
    hogehoge1(w='new keyword')

    print("hogehoge2(x(option), y, s(option), w='default keyword)")
    hogehoge2([1, 4, 9])
    hogehoge2([1, 2, 3], [1, 4, 9])
    hogehoge2([1, 4, 9], '=s')
    hogehoge2([1, 4, 9], 's')
    hogehoge2([1, 2, 3], [1, 4, 9], 's')
    hogehoge2([1, 2, 3], [1, 4, 9], 1)
    hogehoge2([1], [1])

    print("hogehoge3(x(option), y(option), z, n(option), v(option))")
    import numpy as np
    z = np.arange(25).reshape(5, 5)
    x = np.arange(5)
    y = np.arange(5)
    n = 10
    v = np.arange(10)
    hogehoge3(z)
    hogehoge3(x, y, z)
    hogehoge3(z, n)
    hogehoge3(z, v)
