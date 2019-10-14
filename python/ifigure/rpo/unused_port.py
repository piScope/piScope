import socket
import os
import subprocess


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


if __name__ == '__main__':
    port = PickUnusedPort()
    hostname = os.getenv("HOSTNAME")
    command = 'python -m Pyro4.naming -p '+str(port) + ' -n '+hostname + ' &'
    subprocess.Popen(command, shell=True)
