import sys
import socket
import shlex
import threading
import os
import binascii
import subprocess
import time
import tempfile
from six.moves import socketserver
import traceback
import ifigure.utils.pickle_wrapper as pickle
from ifigure.utils.pickled_pipe import PickledPipe


def pick_unused_port():
    '''
    a routeint to le a system to pick an unused port.
    this recipe was found in active state web site
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


class Client(object):
    def __init__(self, *args, **kargs):
        self.sock = None
        self.rfile = None
        object.__init__(self, *args, **kargs)

    def make_connection(self, ip, port):
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((ip, port))
                self.rfile = self.sock.makefile('r')
            except:
                self.sock = None
                self.rfile = None

    def process(self, ip, port, message):
        if len(message) == 0:
            return {}

        v = {}

        try:
            if self.sock is None:
                self.make_connection(ip, port)
            msr = pickle.dumps(message)
            msbin = binascii.b2a_hex(msr)
            self.sock.sendall(msbin+'\n')
#
            response = self.rfile.readline().strip()
#            self.rfile.close()
            try:
                v = pickle.loads(binascii.a2b_hex(response))
            except EOFError:
                v = {'client_status': 'error in loading data'}
        except:
            v = {'client_status': 'error in sending data'}
        finally:
            pass
#            self.sock.close()
#            self.sock = None
        v['message'] = [message]
        return v

    def finish_connection(self):
        if self.rfile is not None:
            self.rfile.close()
        if self.sock is not None:
            self.sock.close()
        self.sock = None
        self.rfile = None


class JobRunner(object):
    def __init__(self, host, port):
        self.p = None
        self.host = 'localhost'
        lport = self.make_ssh_connection(host, port)
        self.port = lport
        self.client = Client()
        self._shot = -1
        self._connection_param = ''
        self.gjob = None
        try:
            time.sleep(3)
            self.client.make_connection(self.host, self.port)
        except:
            pass
        self.g = {}

    def __del__(self):
        from signal import SIGTERM, SIGKILL
        if self.client is not None:
            self.client.finish_connection()
        self.client = None
        if self.p is not None:
            os.kill(self.p.pid, SIGKILL)

    def terminate(self):
        if self.client is not None:
            self.client.finish_connection()
        self.client = None
        if self.p is not None:
            self.p.kill()
        self.p == None

    def make_ssh_connection(self, host, port):
        lport = pick_unused_port()

        command = 'ssh -N  -L ' +  \
            str(lport)+':' + str(host)+':' + \
            str(port) + ' ' + str(host)

        self.p = subprocess.Popen(shlex.split(command))
        return lport

    def set_globaljob(self, job):
        self.gjob = job

    def run(self, jobset, skip_init):
        self.error = []
        jobs, names = jobset

        all_commands = []
        for k, job in enumerate(jobs):
            commands = []
            for j in job:
                if j.command != 'script_txt':
                    if j.command == 'init':
                        if skip_init:
                            continue
                        else:
                            j.command = 'value'
#                    command, command2 = self._job_command(j)
                    ccc = self._job_command(j)
                    commands.extend(ccc)
#                    if command != '':
#                       commands.append(command)
#                    if command2 != '':
#                       commands.append(command2)
            if len(commands) > 0:
                all_commands.append((names[k], commands))
#        print all_commands
        self.r = self.client.process(self.host, self.port, all_commands)
        for k, job in enumerate(jobs):
            for j in job:
                if j.command == 'script_txt':
                    self.r[names[k]] = self._run_script(j)
        self.r['error message'] = self.error
        return self.r

    def _job_command(self, job):
        com = job.command
#           command = ''
#           command2 = ''
        ccc = []
        if com == 'open':
            tree = job.params[0]
            shot = job.params[1]
#               command = "c"+str(tree)+","+ str(shot)
            ccc.append("c"+str(tree)+"," + str(shot))
            if shot != self._shot:
                expr = 'reset_private();reset_public();1'
#                   command2 = "v"+str(expr)
                ccc.append("v"+str(expr))
            if self._connection_flag:
                if self.gjob is not None:
                    expr = self.gjob.params[0]
                    ccc.append("v"+str(expr))
            self._connection_flag = True
            self._shot = shot
        elif com == 'defnode':
            node = job.params[0]
            if node.strip() != '':
                ccc.append("d"+str(node))
#               else:
#                   command = ''
        elif com == 'value':
            expr = job.params[0]
#               command = "v"+str(expr)
            ccc.append("v"+str(expr))
        elif com == 'valuesig':
            expr = job.params[0]
#               command = "v"+str(expr)
            ccc.append("u"+str(expr))
        elif com == 'dim_of':
            expr = job.params[0][2:]
            ccc.append("w"+str(expr))
        elif com == 'connection_mode':
            if self._connection_param != job.params[0]:
                #                  command = 's'+ job.params[0]
                ccc.append('s' + job.params[0])
                self._connection_param = job.params[0]
                self._connection_flag = True
        return ccc
#           return command, command2

    def _run_script(self, job):
        expr = job.params[0]
        try:
            code = compile(expr, '<string>', 'exec')
            g = globals()
            l = {}
            exec(code, self.g, self.r)
            return 'ok'
        except:
            self.error = ['Scrip Error', expr, sys.exc_info()[0]]
            return None
