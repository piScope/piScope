from __future__ import print_function

'''
    client.py


    it provides server/client operation of piScope

    A user can launch piScope from any python console,
    and send/recieve various command/data.

    useage:

        from ifigure.client import *

        launch()        # this launch piScope as a separate process
        plot(range(30)) # send range(30) to piscope and make a plot

        ## here a user export plot data to piScope shell, and
        ## create xdata and ydata

        print xdata     # in server/client mode, the data is automatically 
                        # sent

        ## a user can also get any pickable variables in piScope shell
        get('varname')

'''

import socket
import subprocess
import sys
import shlex
import ifigure.utils.pickle_wrapper as cPickle
import binascii
import threading
import os
from six.moves import socketserver
from ifigure.utils.cbook import pick_unused_port


class ReceiverReqHandler(socketserver.BaseRequestHandler):
    def handle(self):
        rfile = self.request.makefile('r')
        response = rfile.readline().strip()
        rfile.close()
        data = cPickle.loads(binascii.a2b_hex(response))
        if data['type'] == 'data':
            import __main__
            text = '\n'
            for key in data['data'][0]:
                if key in dir(__main__):
                    text = text + key + ' is updated\n'
                else:
                    text = text + key + ' is created\n'
                setattr(__main__, key, data['data'][0][key])
            print(text)
        elif data['type'] == 'msg':
            print((data['data']))


class Receiver(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class Client(object):
    port = 0
    host = 'localhost'
    process = None
    receiver = None

    def launch(self, host='localhost', exe=None):
        if host == 'localhost':
            from ifigure.utils.get_ifigure_dir import bin_dir
            # command = os.path.join(bin_dir(), 'piscope.sh') + ' -s'
            if exe is None:
                exe = sys.executable
            # command = command + ' -e '+ exe + ' &'
            # import piscope
            # command = sys.executable + ' ' + piscope.__file__ + ' -s -d'
            command = 'piscope  -s -d'
            # print(command)
            if os.altsep is not None:
                command = command.replace(os.sep, os.altsep)
            p = subprocess.Popen(shlex.split(command),  # shell = True,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
            lhost = 'localhost'
        else:
            pass
        line = ''
        while line[0:5] != 'start':
            line = p.stdout.readline()
            print(line)
        arr = line.split(':')
        Client.host = arr[1].rstrip("\r\n").strip()
        Client.port = int(arr[2].rstrip("\r\n").strip())
        Client.process = p
        if Client.receiver is None:
            port = pick_unused_port()

            sys.stdout.flush()
            Client.receiver = Receiver((lhost, port), ReceiverReqHandler)

            server_thread = threading.Thread(
                target=Client.receiver.serve_forever)
            server_thread.daemon = True
            server_thread.start()
        ip, port = Client.receiver.server_address
        print(('receiver :', ip, ':', port))
        message = cPickle.dumps(('r', ip, port))
        self.send(message, noresponse=True)

    def shutdown(self):
        if Client.process is not None:
            Client.process.kill()
            Client.process = None
            Client.host = 'localhost'
            Client.port = 0
            Client.receiver.shutdown()
            Client.receiver = None

    def set_connection(self, host, port):
        Client.port = port
        Client.host = host

    def send(self, message, noresponse=False):
        host = Client.host
        port = Client.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        response = None
        try:
            hexmessage = binascii.b2a_hex(message)
            sock.sendall(hexmessage + b'\n')
            if not noresponse:
                rfile = sock.makefile('r')
                response = rfile.readline().strip()
                rfile.close()
#             response = sock.recv(1024)
#             print len(response)
                response = cPickle.loads(binascii.a2b_hex(response))
        finally:
            sock.close()
        return response


def launch(exe=None):
    server('launch', exe=exe)


def shutdown():
    server('shutdown')


def server(param, host='localhost', port=None, exe=None):
    '''
    launch/connect piscope 
    server('coonect', host, port)
    server('launch')
    server('shutdown')
    '''
    c = Client()
    if param == 'launch':
        c.launch(exe=exe)
    if param == 'connect':
        c.set_connection(host, port)
    if param == 'shutdown':
        if c.host is None:
            return
        if c.port == 0:
            return

        message = cPickle.dumps(('f', 'quit', tuple(), dict()))
        c = Client()
        c.send(message, noresponse=True)
        c.shutdown()
    print(('host: ', c.host, ', port: ', c.port))


def check_connection():
    c = Client()
    message = cPickle.dumps(('c',))
    print((c.send(message)))


def make_testplot():
    message = cPickle.dumps(('t', 'plot(range(10))'))
    c = Client()
    c.send(message)


def _get_random_name():
    # get random name
    from time import gmtime, strftime
    import hashlib
    import os
    import ifigure_config

    check = True
    while(check):
        strtime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        m = hashlib.md5()
        m.update(strtime)
        txt = m.hexdigest()
        fpath = os.path.join(ifigure_config.rcdir,
                             '###param_'+txt)
        check = os.path.exists(fpath)
    return fpath


def _save_parameter_file(*args, **kargs):
    try:
        return sr
    except IOError as error:
        return False


def _send_message(command, *args, **kargs):
    try:
        message = cPickle.dumps(('f', command, args, kargs))
    except error:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)


def _send_message_g(command, *args, **kargs):
    try:
        message = cPickle.dumps(('g', command, args, kargs))
    except error:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)


def cla(*args, **kargs):
    _send_message('cla', *args, **kargs)


def cls(*args, **kargs):
    _send_message('cls', *args, **kargs)


def clf(*args, **kargs):
    _send_message('clf', *args, **kargs)


def nsec(*args, **kargs):
    _send_message('nsec', *args, **kargs)


def nsection(*args, **kargs):
    _send_message('nsection', *args, **kargs)


def isec(*args, **kargs):
    _send_message('isec', *args, **kargs)


def isection(*args, **kargs):
    _send_message('isection', *args, **kargs)


def scope(*args, **kargs):
    _send_message('scope', *args, **kargs)


def figure(*args, **kargs):
    _send_message('figure', *args, **kargs)


def addpage(*args, **kargs):
    _send_message('addpage', *args, **kargs)


def delpage(*args, **kargs):
    _send_message('delpage', *args, **kargs)


def hold(*args, **kargs):
    _send_message('hold', *args, **kargs)


def update(*args, **kargs):
    _send_message('update', *args, **kargs)


def title(*args, **kargs):
    _send_message('title', *args, **kargs)


def xlabel(*args, **kargs):
    _send_message('xlabel', *args, **kargs)


def ylabel(*args, **kargs):
    _send_message('ylabel', *args, **kargs)


def xlim(*args, **kargs):
    _send_message('xlim', *args, **kargs)


def ylim(*args, **kargs):
    _send_message('ylim', *args, **kargs)


def subplot(*args, **kargs):
    _send_message('subplot', *args, **kargs)


def plot(*args, **kargs):
    _send_message('plot', *args, **kargs)


def errorbar(*args, **kargs):
    _send_message('errorbar', *args, **kargs)


def contour(*args, **kargs):
    _send_message('contour', *args, **kargs)


def image(*args, **kargs):
    _send_message('image', *args, **kargs)


def ispline(*args, **kargs):
    _send_message('ispline', *args, **kargs)


def axline(*args, **kargs):
    _send_message('axline', *args, **kargs)


def axspan(*args, **kargs):
    _send_message('axspan', *args, **kargs)


def text(*args, **kargs):
    _send_message('text', *args, **kargs)


def legend(*args, **kargs):
    _send_message('legend', *args, **kargs)


def get(*args, **kargs):
    return _send_message_g('get_shellvar', *args, **kargs)


def put(*args, **kargs):
    return _send_message_g('pet_shellvar', *args, **kargs)
