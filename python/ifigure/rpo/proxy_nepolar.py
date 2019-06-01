from __future__ import print_function
import subprocess as sp
import numpy as np
import os
import Pyro4


class ProxyNepolar(object):
    def fill_array(self, i, txt):
        ndim = int(txt[i])
        i = i+1
        dim = [0]*ndim
        nel = 1
        for j in range(ndim):
            dim[j] = int(txt[i])
            nel = nel*dim[j]
            i = i+1
        arr = np.zeros(nel)
        for j in range(nel):
            arr[j] = float(txt[i])
            i = i + 1
        dim = [x for x in reversed(dim)]
        arr2 = arr.reshape(dim)
        return i, arr2

    def run_idl(self, shot=1120612006):

        p = sp.Popen('idl', stdin=sp.PIPE, shell=True,
                     stdout=sp.PIPE)

        p.stdin.write(
            '.r /home/shiraiwa/PycharmProjects2M/ifigure/rpo/ne_polar.pro\n')
        p.stdin.write('ne_polar, '+str(shot)+'\n')
        p.stdin.write('exit\n')
        p.stdout.flush()

        txt = ''.join(p.stdout.read())
        txt = txt.replace('\n', ' ')
        txt = txt.replace('\r', ' ')
        txt = [x for x in txt.split(' ') if len(x) != 0]

        print(txt)
        val = {}
        i = 0
        i, val["r_p"] = self.fill_array(i, txt)
        i, val["z_p"] = self.fill_array(i, txt)
        i, val["den_p"] = self.fill_array(i, txt)
        i, val["t"] = self.fill_array(i, txt)
        i, val["FaradayR"] = self.fill_array(i, txt)

        print(val)
        return val


def main():
    p = ProxyNepolar()
    nameserver = Pyro4.locateNS()
    Pyro4.Daemon.serveSimple(
        {
            p: "proxy_nepolar"
        },
        ns=True,
        host=os.getenv('HOSTNAME'))


if __name__ == '__main__':
    # check program
    main()
