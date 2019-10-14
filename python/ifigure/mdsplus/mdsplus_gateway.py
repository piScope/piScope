#!/usr/bin/python

from __future__ import print_function
import socket
import threading
import os
import signal
import sys
import time
import logging
import traceback
from six.moves import socketserver
#import paramiko
import binascii
from six.move import cPickle as pickle
#import cPickle as pickle
from ifigure.utils.daemon import Daemon
import MDSplus
from MDSplus import Connection
#from .utils import parse_server_string

write_handler_log = False


def parse_server_string(txt):
    l = txt.split(':')
    p = l[-2]
    t = l[-1]
    s = ':'.join(l[:-2])
    return s, p, t


class ForkingTCPRequestHandler(socketserver.StreamRequestHandler):
    #
    def __init__(self, *args, **kargs):
        name = '/tmp/mdsplus_gateway_'+str(os.getpid()) + '.log'

        self.use_mdsconnect = False
        self.connection_str = ''
        self.connection = None
        if write_handler_log:
            self.fid = open(name, 'w')
        else:
            self.fid = None
        socketserver.StreamRequestHandler.__init__(self, *args, **kargs)

    def write_log(self, txt):
        if self.fid is not None:
            self.fid.write(txt + '\n')

    def handle(self):
        try:
            while True:
                self.loop_handler()
        except:
            pass

    def loop_handler(self):
        message = self.rfile.readline().strip()
        if self.fid is not None:
            self.fid.write('handling input \n' + message + '\n')
        asmessage = binascii.a2b_hex(message)
#        logging.basicConfig(level = logging.DEBUG)
        try:
            data = pickle.loads(asmessage)
        except ValueError as EOFError:
            if self.fid is not None:
                self.fid.write('picke error \n')
                self.fid.flush()
#           logging.exception('picke load error', len(message))
#           response = None
#           return
        #cur_thread = threading.current_thread()
        if self.fid is not None:
            self.fid.write('handling request  \n' + str(data) + '\n')
            self.fid.flush()
        r = {}
        for name, commands in data:
            for command in commands:
                com = command[0]
                param = command[1:]
        #cur_thread = threading.current_thread()
                if self.fid is not None:
                    self.fid.write(com + ':' + param + '\n')
                    self.fid.flush()
                if com == 's':

                    server, port, tree = parse_server_string(param)
                    self.use_mdsconnect = (False if server.upper() ==
                                           'DIRECT' else True)

                    if self.use_mdsconnect:
                        try:
                            if self.connection_str != param:
                                del self.connection
                                if port != '':
                                    server = server + ':' + port
                                self.connection = Connection(server)
                                self.connection_str = param
                                r[name] = 'ok'
                        except:
                            r[name] = 'connection error'
                            self.error = ['connection error',
                                          self.connection_str]
                    else:
                        if self.connection is not None:
                            del self.connection
                            self.connection = None
                        self.connection_str = ''
                        r[name] = 'ok'
                else:
                    self.error = []
                    if self.use_mdsconnect:
                        r[name] = self._handle_mdsconnect(com, param)
                    else:
                        r[name] = self._handle(com, param)
                    if len(self.error) != 0:
                        if self.fid is not None:
                            self.fid.write(str(self.error))
                            self.fid.flush()
        if self.fid is not None:
            self.fid.write('return variables  \n' + str(list(r.keys())) + '\n')
            self.fid.flush()

        sr = pickle.dumps(r)
        response = binascii.b2a_hex(sr)
        if self.fid is not None:
            self.fid.write('sending data (length) \n' +
                           str(len(response)) + '\n')
            self.fid.flush()
        self.request.sendall(response+'\n')
        if self.fid is not None:
            self.fid.flush()

    def _handle_mdsconnect(self, com, param):
        response = ''

        self.write_log(str(com)+':'+str(param))
        if com == 'c':  # connection request
            arr = param.split(',')
            tree = ','.join(arr[:-1])
            shot = arr[-1]
            try:
                if tree != '':
                    self.write_log('opening tree :' +
                                   str(tree) + ':'+str(shot))
                    self.connection.openTree(tree, int(shot))
                response = 'ok'
            except Exception:
                self.error = ['run error', traceback.format_exc()]
                response = None
        elif com == 'd':
            node = param
            self.write_log('setting def node ' + str(node))
            try:
                if node.strip() != '':
                    self.connection.setDefault(node)
                response = 'ok'
            except Exception:
                self.error = ['run error', traceback.format_exc()]
                response = None
        elif com == 'v':  # mdsvalue
            self.write_log('mdsvalue '+str(param))
            try:
                response = self.connection.get(param).data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        elif com == 'u':  # mdsvalue
            self.write_log('mdsvalue '+str(param))
            try:
                response = self.connection.get(
                    '_piscopevar=execute($)', param).data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        elif com == 'w':  # dim_of (this is not used anymore)
            self.write_log('dim_of '+str(param))
            expr = param[1:]
            dim = int(param[0])
            try:
                #               response =MDSplus.Data.compile(param).evaluate().data()
                response = self.connection.get(expr).dim_of(dim).data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        # self.write_log(response.__repr__())
        return response

    def _handle(self, com, param):
        response = ''

        self.write_log(str(com)+' '+str(param))
        if com == 'c':  # connection request
            arr = param.split(',')
            tree = ','.join(arr[:-1])
            shot = arr[-1]
            try:
                if tree != '':
                    self.write_log('opening tree '+str(tree) + ' '+str(shot))
                    self.t = MDSplus.Tree(tree, int(shot))
                    self.write_log('opening tree '+str(self.t))
                response = 'ok'
            except Exception:
                self.error = ['run error', traceback.format_exc()]
                response = None
        elif com == 'd':
            node = param
            self.write_log('setting def node '+str(node))
            try:
                if node.strip() != '':
                    tn = self.t.getNode(node)
                    self.t.setDefault(tn)
                response = 'ok'
            except Exception:
                self.error = ['run error', traceback.format_exc()]
                response = None
        elif com == 'f':  # connection request
            a = param.split(',')
            tree = a[0]
            shot = a[1]
            node = a[2]
            expr = ','.join(a[3:])
            try:
                self.t = MDSplus.Tree(tree, int(shot))
                if node.strip() != '':
                    tn = self.t.getNode(node)
                    self.t.setDefault(tn)
                response = MDSplus.Data.compile(expr).evaluate().data()
            except Exception:
                self.error = ['run error', expr, traceback.format_exc()]
                response = None
        elif com == 'v':  # mdsvalue
            self.write_log('mdsvalue '+str(param))
            try:
                response = MDSplus.Data.compile(param).evaluate().data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        elif com == 'u':  # mdsvalue
            self.write_log('mdsvalue '+str(param))
            try:
                response = MDSplus.Data.execute(
                    '_piscopevar=execute($)', param).data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        elif com == 'w':  # dim_of (this is not used anymore)
            self.write_log('dim_of '+str(param))
            expr = param[1:]
            dim = int(param[0])
            try:
                #               response =MDSplus.Data.compile(param).evaluate().data()
                response = MDSplus.Data.execute(expr).dim_of(dim).data()
            except Exception:
                self.error = ['run error', param, traceback.format_exc()]
                response = None
        return response


class ForkingTCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
    pass


class MDSDaemon(Daemon):
    def __init__(self, HOST, PORT, pidfile, stdout='/dev/null',
                 stderr='/dev/null'):
        self.host = HOST
        self.port = PORT
        Daemon.__init__(self, pidfile, stdout=stdout, stderr=stderr)

    def run(self):
        self.server = ForkingTCPServer((self.host, self.port),
                                       ForkingTCPRequestHandler)

        print(('Starting MDSplus Gateway', self.host, self.port))
        print(sys.stdout)
        self.ip, self.port = self.server.server_address
        sys.stdout.flush()
        sys.stderr.flush()

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        # Exit the server thread when the main thread terminates
        self.server_thread.setDaemon(True)
        self.server_thread.start()
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        while True:
            # this loop is to keep thread on
            time.sleep(0.1)
            sys.stdout.flush()
            sys.stderr.flush()

    def signal_handler(self, signal, frame):
        print(('Received singal', signal))
        self.server.shutdown()
        sys.exit(0)

    def stop(self):
        print('Stopping server')
        Daemon.stop(self)


if __name__ == "__main__":
    HOST, PORT = socket.gethostname(), 10002
    pid_file = '/tmp/mdsplus_gateway.pid'
    log_file = '/tmp/mdsplus_gateway.log'

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            if os.path.exists(log_file):
                os.remove(log_file)
            daemon = MDSDaemon(HOST, PORT, pid_file,
                               stdout=log_file,
                               stderr=log_file)
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon = MDSDaemon(HOST, PORT, pid_file,
                               stdout=log_file,
                               stderr=log_file)
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon = MDSDaemon(HOST, PORT, pid_file,
                               stdout=log_file,
                               stderr=log_file)
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
            sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
