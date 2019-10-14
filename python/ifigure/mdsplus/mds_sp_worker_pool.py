from __future__ import print_function
import ifigure
import os
import sys
import time
import subprocess
import random
from ifigure.utils.pickled_pipe import PickledPipe


#
#  debug setting
#
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('MDSSPWokerPool')


class MDSSPWorkerPool(object):
    def __init__(self, num, *args):
        self.num = num
        self.pch = [None]*num
        dirname = os.path.dirname(ifigure.__file__)

        type = args[0]
        if len(args) > 1:
            host = args[1]
            port = args[2]
        else:
            host = None
            port = None

        file = 'mds_sp_'+type+'worker.py'
        args = []
        if type == 'proxy':
            args = [str(host), str(port)]
#        if type == 'direct': file = 'mds_sp_directworker.py'
#        if type == 'proxy':  file = 'mds_sp_proxyworker.py'
#        if type == 'echoback':  file = 'mds_sp_echobackworker.py'
        script = os.path.join(dirname, 'mdsplus', file)
        for i in range(num):
            #           print args
            p = subprocess.Popen(['python', script] + args,
                                 bufsize=-1,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
            ch = PickledPipe(p.stdout, p.stdin)
            self.pch[i] = (p, ch)
        self.analysis = [None]*num
        self.task_count = [0]*num

    def set_analysis(self, ana, w_id):
        self.analysis[w_id] = ana

    def submit_batchjob(self, w_id, batch, names):
        k = 0
        p, ch = self.pch[w_id]
        ch.send((batch, names))
        self.task_count[w_id] = 1
        return w_id

    def check_batchfinished(self, w_id):
        if self.task_count[w_id] == 0:
            return 1, None
        p, ch = self.pch[w_id]
        if p.poll() is not None:
            self.task_count[w_id] = 0
            print('process died?')
            return -1, None
        data = ch.recv()
        if data is not None:
            self.task_count[w_id] = 0
            if data == 'error':
                #               self.task_count[w_id] = 0
                return -1, data
#           if self.task_count[w_id] == 0:
            return 1, data
        return 0, None

    def is_alive(self, w_id):
        p, ch = self.pch[w_id]
        return p.poll() is None

    def is_any_alive(self):
        return any([p.poll() is None for p, ch in self.pch])

    def terminate_all(self):
        for p, ch in self.pch:
            try:
                ch.send(-1)
                data = ch.recv(nowait=False)
            except:
                pass
            p.kill()
            p.wait()

    def get_worker(self):
        #  return a worker which is free.
        ans_list = []
        for i,  pch in enumerate(self.pch):
            p, ch = pch
            if (self.analysis[i] is None and
                    p.poll() is None):
                ans_list.append((p, i))
        if len(ans_list) == 0:
            return None, -1
        ret = ans_list[int(random.random()*len(ans_list))]
        return ret[0], ret[1]

    def get_num_worker(self):
        return len(self.pch)

    def get_pool_ready(self):
        ans_list = []
        for i,  pch in enumerate(self.pch):
            p, ch = pch
            if (self.analysis[i] is None and
                    p.poll() is None):
                ans_list.append((p, i))
        return (len(ans_list) == len(self.pch))
