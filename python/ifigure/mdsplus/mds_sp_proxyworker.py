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

from ifigure.mdsplus.proxy_jobrunner import JobRunner

if __name__ == '__main__':
    host = sys.argv[1]
    port = sys.argv[2]
    ch = PickledPipe(sys.stdin, sys.stdout)
    runner = JobRunner(host, port)
    while True:
        time.sleep(0.01)
        try:
            jobset = ch.recv(nowait=False)
        except EOFError:
            r = {'error message': ['message was received']}
            r['worker output'] = ''
            ch.send(r)

        if jobset != -1:
            tmp = tempfile.TemporaryFile()
            sys.stdout = tmp
            try:
                r = runner.run(jobset)
            except:
                r = {'error message': [
                    'runner.run failed', traceback.format_exc()]}
            finally:
                tmp.flush()
                tmp.seek(0)
                r['worker output'] = tmp.read()
                tmp.close()
                jobs, names = jobset
                def_names = ['message',
                             'pickle error',
                             'network message',
                             'worker output',
                             'error message',
                             'x', 'y', 'z',
                             'xerr', 'yerr', 'zerr']
                for n in names:
                    if not n in def_names:
                        def_names.append(n)
                r2 = {}
                for n in def_names:
                    if n in r:
                        r2[n] = r[n]
                ch.send(r2)
        else:
            runner.terminate()
            ch.send('ok')
            break
