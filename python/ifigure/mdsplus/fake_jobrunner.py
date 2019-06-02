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
        return {'x': np.arange(l), 'y': np.arange(l), 'error message': ''}
