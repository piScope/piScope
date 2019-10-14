from __future__ import print_function
import subprocess as sp
import os
import Pyro4


class ProxyNeTe(object):
    def fill_array(self, i, txt):
        ct = []
        print((i, txt[i]))
        for t in range(1+i, int(txt[i])+1+i):
            ct.append(txt[t])
        return t+1, ct

    def run_idl(self, shot=1120809022,
                time=1):

        p = sp.Popen('idl', stdin=sp.PIPE, shell=True,
                     stdout=sp.PIPE)

        p.stdin.write(
            '.r /home/shiraiwa/PycharmProjects2M/ifigure/rpo/nete_ispline.pro\n')
        p.stdin.write('v=nete_ispline('+str(shot)+','+str(time)+')\n')
        # ne(core)
        p.stdin.write('print, n_elements(v.cne)\n')
        p.stdin.write('print, reform(v.cne)\n')
        p.stdin.write('print, n_elements(v.cne_err)\n')
        p.stdin.write('print, reform(v.cne_err)\n')
        # te(core)
        p.stdin.write('print, n_elements(v.cte)\n')
        p.stdin.write('print, reform(v.cte)\n')
        p.stdin.write('print, n_elements(v.cte_err)\n')
        p.stdin.write('print, reform(v.cte_err)\n')
        # r(core)
        p.stdin.write('print, n_elements(v.c_rho)\n')
        p.stdin.write('print, reform(v.c_rho)\n')
        # ne(edge)
        p.stdin.write('print, n_elements(v.ene)\n')
        p.stdin.write('print, reform(v.ene)\n')
        p.stdin.write('print, n_elements(v.ene_err)\n')
        p.stdin.write('print, reform(v.ene_err)\n')
        # te(edge)
        p.stdin.write('print, n_elements(v.ete)\n')
        p.stdin.write('print, reform(v.ete)\n')
        p.stdin.write('print, n_elements(v.ete_err)\n')
        p.stdin.write('print, reform(v.ete_err)\n')
        # r(edge)
        p.stdin.write('print, n_elements(v.e_rho)\n')
        p.stdin.write('print, reform(v.e_rho)\n')

        p.stdin.write('exit\n')
        p.stdout.flush()

        txt = ''.join(p.stdout.read())
        txt = txt.replace('\n', ' ')
        txt = txt.replace('\r', ' ')
        txt = [float(x) for x in txt.split(' ') if len(x) != 0]
#        a = txt.split('\r')
#        txt=''.join(a)
#        a = txt.split('\n')
#        txt=''.join(a)
        print(txt)
        val = {}
        i = 0
        i, val["cn"] = self.fill_array(i, txt)
        i, val["cn_err"] = self.fill_array(i, txt)
        i, val["ct"] = self.fill_array(i, txt)
        i, val["ct_err"] = self.fill_array(i, txt)
        i, val["cr"] = self.fill_array(i, txt)
        i, val["en"] = self.fill_array(i, txt)
        i, val["en_err"] = self.fill_array(i, txt)
        i, tmp = self.fill_array(i, txt)
        val["et"] = [x/1000. for x in tmp]
        i, tmp = self.fill_array(i, txt)
        val["et_err"] = [x/1000. for x in tmp]
        i, val["er"] = self.fill_array(i, txt)

        print(val)
        return val


def main():
    p = ProxyNeTe()
    nameserver = Pyro4.locateNS()
    Pyro4.Daemon.serveSimple(
        {
            p: "proxy_nete"
        },
        ns=True,
        host=os.getenv('HOSTNAME'))


if __name__ == '__main__':
    # check program
    main()
