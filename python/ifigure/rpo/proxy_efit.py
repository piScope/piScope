from __future__ import print_function
import subprocess as sp
import os
import Pyro4


class ProxyEfit(object):
    def filename(self, shot, time, prefix='k'):
        # time in [s]
        a = '0'*5
        b = str(int(time*1000))
        c = a[:-len(b)]+b
        return '.'.join([prefix+str(int(shot)), c])

    def run_minus_5(self, shot=1120710020,
                    time=1,
                    tree='ANALYSIS',
                    exe='/usr/local/cmod/codes/efit/bin/efitd6565d'):
        # time in [s]
        p = sp.Popen(exe, stdin=sp.PIPE)
        p.stdin.write('-5\n')
        p.stdin.write('0\n')
        p.stdin.write('0\n')
        p.stdin.write(str(shot)+', '+str(int(time*1000))+', ' +
                      str(int(time*1000))+', ' + '1\n')

        p.stdin.write(tree+'\n')
        p.stdin.write("\\" + tree + "::\n")
        print(p.wait())

        path = self.filename(shot, time)
        content = ''
        if os.path.exists(path):
            f = open(path, 'r')
            content = f.read()
            f.close()
            os.remove(path)
        return content

    def run_2(self, shot=1120710020, time=1, namelist='',
              prefix='m',
              exe='/usr/local/cmod/codes/efit/bin/efitd6565d'):
        # time in [s]
        # save content as file
        kpath = self.filename(shot, time, prefix='k')
        f = open(kpath, 'w')
        f.write(namelist)
        f.close()

        # run mode 2 of efit
        p = sp.Popen(exe, stdin=sp.PIPE)
        p.stdin.write('2\n')
        p.stdin.write('1\n')
        p.stdin.write(kpath+'\n')
        p.wait()
        # read g and a file
        apath = self.filename(shot, time, prefix='a')
        gpath = self.filename(shot, time, prefix='g')
        acontent = ''
        if os.path.exists(apath):
            f = open(apath, 'r')
            acontent = f.read()
            f.close()
            os.remove(apath)
        gcontent = ''
        if os.path.exists(gpath):
            f = open(gpath, 'r')
            gcontent = f.read()
            f.close()
            os.remove(gpath)

        os.remove(kpath)
        return acontent, gcontent


def main():
    p = ProxyEfit()
    nameserver = Pyro4.locateNS()
    Pyro4.Daemon.serveSimple(
        {
            p: "proxy_efit"
        },
        ns=True,
        host=os.getenv('HOSTNAME'))


if __name__ == '__main__':
    # check program
    main()
