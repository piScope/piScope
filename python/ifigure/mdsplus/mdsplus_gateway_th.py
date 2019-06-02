#!/usr/bin/python

from __future__ import print_function
import socket
import threading
import os
import signal
import sys
import time
from six.moves import socketserver
import paramiko
import binascii
import ifigure.utils.pickle_wrapper as pickle
from ifigure.utils.daemon import Daemon
import MDSplus


class ThreadingTCPRequestHandler(socketserver.BaseRequestHandler):
    #
    def __init__(self, *args, **kargs):
        socketserver.BaseRequestHandler.__init__(self, *args, **kargs)
        name = '/tmp/mdspluse_gateway_thread'+str(os.getpid()) + '.log'
#        self.fid = open(name, 'w')

    def handle(self):
        message = self.request.recv(1024)

        data = pickle.loads(binascii.a2b_hex(message))
        #cur_thread = threading.current_thread()
        print(("Request ", data))

        r = {}
        for name, commands in data:
            for command in commands:
                com = command[0]
                param = command[1:]
                r[name] = self._handle(com, param)

        print(('return variables', list(r.keys())))

        sr = pickle.dumps(r)
        response = binascii.b2a_hex(sr)
        print(("sending data (length)", len(response)))
        self.request.sendall(response+'\n')
#        self.fid.flush()

    def _handle(self, com, param):
        response = ''

        print((com, param))
        if com == 'c':  # connection request
            tree, shot, node = param.split(',')
            try:
                print(('opening tree', tree, shot))
                self.t = MDSplus.Tree(tree, int(shot))
                print(('opening tree', self.t))
                if node.strip() != '':
                    tn = self.t.getNode(node)
                    self.t.setDefault(tn)
                response = 'ok'
            except Exception:
                print(('Error', str(sys.exc_info()[
                      1])+','+str(sys.exc_info()[2])))
                response = ''
        if com == 'd':
            node = param
            print(('setting def node', node))
            try:
                if node.strip() != '':
                    tn = self.t.getNode(node)
                    self.t.setDefault(tn)
                response = 'ok'
            except Exception:
                print(('Error', str(sys.exc_info()[
                      1])+','+str(sys.exc_info()[2])))
                response = ''

        if com == 'f':  # connection request
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
#              print "sending data (length)", len(response)
            except Exception:
                print(('Error', str(sys.exc_info()[
                      1])+','+str(sys.exc_info()[2])))
                response = ''

        if com == 'v':  # mdsvalue
            print(('mdsvalue', param))
            try:
                response = MDSplus.Data.compile(param).evaluate().data()
            except Exception:
                print(('Error', str(sys.exc_info()[
                      1])+','+str(sys.exc_info()[2])))
                response = ''

#           print "sending data (length)", len(response), 'original :', type(sr)

        return response

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class MDSDaemon(Daemon):
    def __init__(self, HOST, PORT, pidfile, stdout='/dev/null',
                 stderr='/dev/null'):
        self.host = HOST
        self.port = PORT
        Daemon.__init__(self, pidfile, stdout=stdout, stderr=stderr)

    def run(self):
        self.server = ThreadingTCPServer((self.host, self.port),
                                         ThreadingTCPRequestHandler)

        print(('Starting MDSGateway', self.host, self.port))
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
    daemon = MDSDaemon(HOST, PORT, '/tmp/mdsgateway.pid',
                       stdout='/tmp/mdsgateway.log',
                       stderr='/tmp/mdsgateway.log')

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
            sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
