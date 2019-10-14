from __future__ import print_function

'''
   Setting Parser

   multipurpse setting file parser, which support three types of
   text input file.
   As for the field value, tt tries to evaluate string.
   This convert '16' to a number. If it is necessary to have 
   string '"16"' should be used. If it can not convert, the
   field value is considered as string
       0)  before any field start, global field can be added.
           it can be used for "version" field for example.
       1)  random field file
               x=3
               y=4
       2)  list of data witten in the same format
               student
                 name = 'bob'
                 age = 10
               end
               student
                 name = 'jay'
                 age = 14
               end
       2)  fortran namelist type file
               network
                 remote_host = 'cmodws60'
                 port = 22
               end
               interface
                  default_width = 300
                  default_height = 400
               end
       3) field name will be all converted to lower case.


   useage:
       filename = 'some file name'
       sp = SettingParser(rule_mode=1)
       sp.set_rule('student', {'name':'', 'age':16})
       print sp.read_file(filename)
'''

import os
from ifigure.utils.cbook import isiterable


class SettingParser(object):
    def __init__(self, rule_mode=1):
        '''
        rule_mode = 1: read as many set of parameters based on rule
        rule_mode = 2: there should be only one set for one rule
                       newer data will overwrite the exising data
        '''
        object.__init__(self)
        self.rule = {}
        self.rule_mode = rule_mode
        self.rule_nocheck = {}
        self.rule_usedefault = {}

    def set_rule(self, name, rule, nocheck=False, usedefault=True):
        self.rule[name] = rule
        self.rule_nocheck[name] = nocheck
        self.rule_usedefault[name] = usedefault
        return self

    def omit_comment(self, line):
        if line.find('#') != -1:
            line = line[0:line.find('#')]
        if line.find('!') != -1:
            line = line[0:line.find('#')]
        return line

    def split_line(self, _line):
        _arr = _line.split('=')
        _name = _arr[0].strip()
        _value = '='.join(_arr[1:]).strip()
        try:
            value = eval(_value)
        except:
            value = _value
        return _name.lower(), value

    def read_set(self, lc, lines, name, nocheck=False, usedefault=True):
        if usedefault:
            rule = dict(self.rule[name])
        else:
            rule = {}
        while lc < len(lines):
            line = lines[lc]
            line = self.omit_comment(line)
            if line.upper().find('END') != -1:
                lc = lc+1
                break
            if line.find('=') == -1:
                lc = lc+1
                continue

            name2, value = self.split_line(line)
            if nocheck or (name2 in rule):
                rule[name2] = value
            else:
                print(('Undefined field :', name2, ' in rule ' + name))
            lc = lc+1
        return lc, rule

    def read_file(self, file='', data=None, lines=None):
        '''
        if lines is given, it analyze line, otherwise,
        it parses a file 
        '''
        if lines is None:
            try:
                fid = open(file, 'r')
                lines = fid.readlines()
                fid.close()
            except IOError:
                return False, {}
        lines = [line.strip('\n\r') for line in lines]
#        print lines
        if data is None:
            data = {}
            if self.rule_mode == 1:
                for key in self.rule:
                    data[key] = []
        lc = 0
        while lc < len(lines):  # lc = line counter
            line = lines[lc]
            line = self.omit_comment(line)
            if line.find('=') == -1:
                if line.strip() in self.rule:
                    rname = line.strip()
                    lc = lc+1
                    lc, value = self.read_set(lc, lines, rname,
                                              nocheck=self.rule_nocheck[rname],
                                              usedefault=self.rule_usedefault[rname])
                    if rname in data:
                        data[rname].append(value)
                    else:
                        data[rname] = value
                    continue
                else:
                    lc = lc+1
                    continue
            name, value = self.split_line(line)
            data[name] = value
            lc = lc+1
        return True, data

    def write_subsection(self, lines, name, data):
        lines.append(name)
        for key in data:
            if isinstance(data[key], str):
                lines.append(key + ' = "' + str(data[key])+'"')
            else:
                lines.append(key + ' = ' + str(data[key]))
        lines.append('end')
        return lines

    def write_file(self, data, file=None):
        lines = []
        for key in data:
            if isinstance(data[key], dict):
                lines = self.write_subsection(lines, key, data[key])
            elif isinstance(data[key], list):
                for item in data[key]:
                    lines = self.write_subsection(lines, key, item)
            elif isinstance(data[key], tuple):
                for item in data[key]:
                    lines = self.write_subsection(lines, key, item)
            elif isinstance(data[key], str):
                lines.append(key + ' = "' + str(data[key])+'"')
            else:
                lines.append(key + ' = ' + str(data[key]))

        if file is None:
            for l in lines:
                print(l)
            return
        fid = open(file, 'w')
        for l in lines:
            fid.write(l+'\n')
        fid.close()


class iFigureSettingParser(SettingParser):
    def mname2file(self, mname):
        from ifigure.ifigure_config import rcdir, ifiguredir, resourcedir
#        print mname, resourcedir
#        def_file = os.path.join(*([ifiguredir] + mname.split('.')))
        def_file = os.path.join(*([resourcedir] + mname.split('.')))
        user_file = os.path.join(*([rcdir] + mname.split('.')))
        return def_file, user_file

    def mk_filepath_dir(self, filename):
        t = filename
        if os.path.exists(t):
            return
        if not os.path.exists(os.path.dirname(t)):
            self.mk_filepath_dir(os.path.dirname(t))
        else:
            print(('making directory', t))
            os.mkdir(t)

    def read_setting(self, mname, fromDefault=False):
        def_file, user_file = self.mname2file(mname)
#        print def_file
#        print user_file

        flag, def_v = self.read_file(def_file)
        if (os.path.exists(user_file) and
                not fromDefault):
            flag, user_v = self.read_file(user_file)
            try:
                #                print user_v['version'] , def_v['version']
                if user_v['version'] < def_v['version']:
                    self.write_setting(mname, def_v)
                    return def_v
                else:
                    return user_v
            except:
                self.write_setting(mname, def_v)
                return def_v
        else:
            self.write_setting(mname, def_v)
            return def_v

    def write_setting(self, mname, data):
        user_file, user_file = self.mname2file(mname)
        self.mk_filepath_dir(os.path.dirname(user_file))
        self.write_file(data, user_file)


if __name__ == '__main__':

    lines = ['version = 1',
             'port = 22',
             'host = transport']
    sp = SettingParser()
    print(sp.read_file(lines=lines))

    lines = ['version = 1',
             'student',
             'name = "bob"',
             'age = 17',
             'end',
             'student',
             'name = "jones"',
             'age = 14',
             'end',
             'student',
             'name = "anne"',
             'age = 15',
             'end']

    sp = SettingParser(rule_mode=1)
    sp.set_rule('student', {'name': '', 'age': 16})
    print(sp.read_file(lines=lines))

    lines = ['version = 1',
             'type = "proxy"',
             'connection',
             "server = 'cmodws60.psfc.edu'",
             "port = 10002",
             "end",
             "connection",
             "server = 'cmodws59.psfc.mit.edu'",
             "port = 10002",
             "end"]

    sp = SettingParser(rule_mode=1)
    sp.set_rule('connection', {}, nocheck=True)
    flag, data = sp.read_file(lines=lines)
    print(data)
    sp.write_file(data)

    lines = ['house',
             'rooms = 5',
             'garage = 2',
             'end',
             'yard',
             'type  = "lawn"',
             'end',
             'toy',
             'name = "train"',
             'end']

    sp = SettingParser(rule_mode=2)
    sp.set_rule('house', {})
    sp.set_rule('yard', {})
    sp.set_rule('toy', {})
    print(sp.read_file(lines=lines))

    lines = ['version = 1',
             'house',
             'rooms = 5',
             'garage = 2',
             'end',
             'yard',
             'type  = "lawn"',
             'end',
             'toy',
             'NAME = "1,1,1,1"',
             'end']

    sp = SettingParser(rule_mode=2)
    sp.set_rule('house', {}, nocheck=True)
    sp.set_rule('yard', {}, nocheck=True)
    sp.set_rule('toy', {}, nocheck=True)
    flag, data = sp.read_file(lines=lines)
    print(data)
    sp.write_file(data)
