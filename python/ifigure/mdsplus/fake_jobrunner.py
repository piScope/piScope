import sys, socket, shlex, threading, os, binascii, subprocess, time, tempfile
import SocketServer, traceback
import cPickle as pickle
from ifigure.utils.pickled_pipe import PickledPipe
l = 3000000

class JobRunner(object):
    def __init__(self, host, port):
        self.p = None
        self.host = 'localhost'
        self.port = port

    def __del__(self):
        from signal import SIGTERM, SIGKILL
        if self.p is not None:
            os.kill(self.p.pid, SIGKILL)
    def terminate(self):
        if self.p is not None:
            self.p.kill()
        self.p == None

    def run(self, jobset):
        import numpy as np
        return {'x': np.arange(l), 'y': np.arange(l), 'error message':''}




