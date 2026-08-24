from __future__ import print_function

'''
    server thread for ifigure.
    accept connection from remote host and
    receive plotting command

    message for communication between clients

    the first charactor determines the command

     'c' : check connection
     't' : execute command in string
           ex.  'tplot(range(10))' : execute plot(range(10))
     'f' : execute command with args and kargs written in file
           ex.  'fplot:xxxxxxxx'  : read (args, kargs) using cPickle
                 from xxxxxxxx and execute plot(*args, **kargs)

    history
       2012.12.01  v 0.1
      
'''


import subprocess
import shlex
import time
import os
import sys
import threading
import socket
import threading
from six.moves import socketserver
import wx
import ifigure.events
import ifigure.interactive
import binascii
import logging
import time
import socket
import subprocess
import sys
import shlex
from ifigure.utils.cbook import pick_unused_port
import ifigure.utils.pickle_wrapper as pickle

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        import __main__
        while not __main__.process_server_request:
            time.sleep(0.3)
        rfile = self.request.makefile('r')
        response = rfile.readline().strip()
        rfile.close()
        data = pickle.loads(binascii.a2b_hex(response))
#        data = self.request.recv(1024)
#        data = cPickle.loads(binascii.a2b_hex(data))
        ifig_app = wx.GetApp().TopWindow
        ifig_app.remote_lock.acquire()

        wx.GetApp().TopWindow.remote_reply = ''
        ifigure.events.SendRemoteCommandEvent(ifig_app.proj,
                                              command=data)
        try:
            data = wx.GetApp().TopWindow.server_response_queue.get(True)
            data = binascii.b2a_hex(pickle.dumps(data))
            self.request.sendall(data)
        except:
            import traceback
            traceback.print_exc()

        ifig_app.remote_lock.release()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class Server(object):
    HOST = ''
    PORT = None
    server = None
    rport = 0
    rhost = ''

    records = []
    
    def start(self, host=None):
        on, server, HOST, PORT = self.info()
        if server is not None:
            print(('server has already started', HOST, PORT, server))
            return

        if host is None:
            HOST = 'localhost'
        else:
            HOST = host
        PORT = pick_unused_port()

        server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
        server.request_queue_size = 1
        ip, port = server.server_address

        print(''.join(('starting server:', HOST, ':', str(PORT))))
        sys.stdout.flush()
        
        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

        Server.server = server
        Server.HOST = HOST
        Server.PORT = PORT

    def stop(self):
        on, server, HOST, PORT = self.info()
        server = Server.server
        if server is not None:
            print('shutting donw server')
            server.shutdown()
            server = None
        else:
            print('no server is running')

        Server.server = None

    def info(self):
        server = Server.server
        HOST = Server.HOST
        PORT = Server.PORT
        return server is not None, server, HOST, PORT

    def process(self, command):
        Server.records.append(command)
        
        logging.basicConfig(level=logging.DEBUG)
        ctype = command[0]
        shell = wx.GetApp().TopWindow.shell

        if ctype == 'c':   # check connection
            ret = 'ok'

        elif ctype == 't':  # execute text
            shell.execute_text(command[1])
            ret = 'ok'

        elif ctype == 'f':  # execute command
            c = command[1]
            args = command[2]
            kargs = command[3]

            try:
                f = getattr(ifigure.interactive, c)
                f(*args, **kargs)
                ret = 'ok'
            except:
                logging.exception(
                    "error occured during processing remote commmand")
                print(c)
                print(args)
                print(kargs)
                ret = None

        elif ctype == 'g':  # execute command and return value
            c = command[1]
            args = command[2]
            kargs = command[3]

            try:
                f = getattr(ifigure.interactive, c)
                ret = f(*args, **kargs)
            except:
                logging.exception(
                    "error occured during processing remote commmand")
                print(c)
                print(args)
                print(kargs)
                ret = None

        elif ctype == 'h':  # execute text command and return value
            c = command[1]
            try:
                ret = eval(c, globals(), shell.lvar)
            except:
                logging.exception(
                    "error occured during processing remote commmand")
                print(c)
                print(args)
                print(kargs)
                ret = None

        elif ctype == 'd':  # detach stdin/stdout/stderr
            Server.records.append('d is here')
            self.detach_streams()
            ret = 'ok'

        elif ctype == 'r':  # set receiver port address
            Server.rhost = command[1]
            Server.rport = command[2]
            print(('client :  ' + self.rhost + ':' + str(self.rport)))
            ret = 'ok'
        return ret

    def export_data(self, data, data_type='data'):
        if Server.rport == 0:
            return
        if Server.rhost == '':
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.rhost, self.rport))
        data = binascii.b2a_hex(pickle.dumps(
            {'type': data_type, 'data': data}))
        sock.sendall(data+b'\n')
        sock.close()

    def export_message(self, data):
        self.export_data(data, data_type='msg')

    def detach_streams(self):
        Server.records.append("detatching !!!!!!!!!!!")
        # Open the null device
        devnull = os.open(os.devnull, os.O_RDWR)
        Server.records.append("detatching !!!!!!!!!!!")        

        # Duplicate devnull file descriptor onto 0 (stdin), 1 (stdout), 2 (stderr)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        Server.records.append("detatching !!!!!!!!!!!")                

        # Close the original descriptor copy
        if devnull > 2:
            os.close(devnull)
        Server.records.append("detatching !!!!!!!!!!!")                            


        # Update sys objects to match the new file descriptors\
        import sys
        sys.stdin = open(os.devnull, 'r')
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        Server.records.append("detatching !!!!!!!!!!! done")                                    
        return        
        print(sys.stdion)



        
