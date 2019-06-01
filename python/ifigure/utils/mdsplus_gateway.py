#!/usr/bin/python

from __future__ import print_function
import socket
import threading
from six.moves import socketserver
import paramiko
import os
import MDSplus
import binascii
import sys
import cPickle as pickle


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    #

    def handle(self):
        data = self.request.recv(1024)
        #cur_thread = threading.current_thread()
        com = data[0]
        param = data[1:]

        response = ''
        print(("Request ", data))
        if com == 'c':  # connection request
            tree, shot, node = param.split(',')
            try:
                self.t = MDSplus.Tree(tree, int(shot))
                tn = self.t.getNode(node)
                self.t.setDefault(tn)
                response = 'ok'
            except Exception:
                response = str(sys.exc_info()[1])+','+str(sys.exc_info()[2])

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
                r = MDSplus.Data.compile(expr).evaluate().data()
                sr = pickle.dumps(r)
                response = binascii.b2a_hex(sr)
                print(("sending data (length)", len(
                    response), 'original :', type(sr)))
                print(type(binascii.a2b_hex(response)))

            except Exception:
                response = str(sys.exc_info()[1])+','+str(sys.exc_info()[2])

        if com == 'v':  # mdsvalue
            r = MDSplus.Data.compile(param).evaluate().data()
            sr = pickle.dumps(r)
            response = binascii.b2a_hex(sr)
            print(("sending data (length)", len(
                response), 'original :', type(sr)))
            print(type(binascii.a2b_hex(response)))
        #response = "{}: {}".format(cur_thread.name, data)

        self.request.sendall(response+'\n')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = os.getenv("HOSTNAME"), 10002

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    print((ip, port))
    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    # usr=os.getenv("USER")
    from ifigure.utils.get_username import get_username
    usr = get_username()
    print(("Server loop running in thread:", server_thread.name))

    raw_input()

    server.shutdown()
