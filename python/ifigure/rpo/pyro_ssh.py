from __future__ import print_function
import Pyro4
import subprocess
import shlex
import weakref
import socket
import logging
import time


def PickUnusedPort():
    '''
    a routeint to le a system to pick an unused port.
    this recipe was found in active state web site
    '''

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def confirm_connection(host, port):
    retry = 0
    max_retry = 15
    retry = 0
    wait = 2

    if host == 'localhost':
        host1 = ''
    else:
        host1 = host
    arg = (host1, port)

    while retry < max_retry:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(arg)
        except Exception:
            #          logging.exception("connection failed")
            retry = retry+1
            time.sleep(wait)
            continue
        break
    s.close()
    if retry == max_retry:
        print("connection failed")
        return False
    print("connection established")
    return True


class PyroSSH(object):
    def __init__(self, *args, **kargs):
        self.process = []
        self.proxy = []
        return super(PyroSSH, self).__init__()

    def nslookup(self, host, name, port=9090):
        lport = PickUnusedPort()  # unused local port
        command = 'ssh -N '+str(host) + ' -L ' +  \
            str(lport)+':' + str(host)+':' + \
            str(port)  # + ' & echo $!'
#        p=subprocess.call(shlex.split(command), shell=True)
        print(command)
        p = subprocess.Popen(shlex.split(command),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        confirm_connection('localhost', lport)
        try:
            nameserver = Pyro4.locateNS(port=lport)
            uri = nameserver.lookup(name)
        except Exception:
            return None
#           logging.exception("nslookup failed")
#           p.terminate()
#           return None
        print(('killing process', p.pid))
        p.terminate()
        p.kill()
        return uri

    def open_proxy(self, uri):
        lport = PickUnusedPort()  # unused local port
        command = 'ssh -N  '+str(uri.host) + ' -L ' +  \
            str(lport)+':' + str(uri.host)+':' + \
            str(uri.port)
        print(command)
        p = subprocess.Popen(shlex.split(command))
        confirm_connection('localhost', lport)

        uri0 = Pyro4.URI("PYRO:"+uri.object+"@localhost:"+str(lport))
        proxy = Pyro4.Proxy(uri0)
        self.process.append(p)
        self.proxy.append(proxy)
        return proxy

    def close_proxy(self, proxy):
        if self.proxy.count(proxy) != 0:
            idx = self.proxy.index(proxy)
            p = self.process[idx]
            self.process.remove(p)
            self.proxy.remove(proxy)
            print(('terminating process', p.pid))
            p.terminate()
            p.kill()


if __name__ == '__main__':
    c = PyroSSH()
    uri = c.nslookup('cmodws30.psfc.mit.edu', 'proxy_efit')
    print(uri)
    print(uri.object)

    proxy = c.open_proxy(uri)
    print(proxy.filename(shot=1120809022, time=1.0, prefix='k'))
    print(proxy.run_minus_5(shot=1120809022, time=1.0))
    c.close_proxy(proxy)
