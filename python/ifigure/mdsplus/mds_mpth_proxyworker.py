import multiprocessing as mp
import time
import numpy
import tempfile
import traceback
import threading

from ifigure.mdsplus.proxy_jobrunner import JobRunner
#from ifigure.mdsplus.fake_jobrunner import JobRunner
from numpy import ndarray, isnan, squeeze
from ifigure.mdsplus.filed_ndarray import FiledNDArray


class ProxyWorkerBase(object):
    use_compress = True

    def run_loop(self, *args, **kargs):
        runner = JobRunner(self.host, self.port)
        while True:
            try:
                task = self.task_queue.get(True)
            except EOFError:
                r = {'error message': ['message was received']}
                r['worker output'] = ''
                self.result_queue.put((-1, 0, r))
                self.task_queue.task_done()

            if task != -1:
                job_id, jobgroup, globaljob = task
                ret = [None]*len(jobgroup)
                for k, jobset in enumerate(jobgroup):
                    skip_init = False
                    jobs, names = jobset
                    for job in jobs:
                        for j in job:
                            if j.command == 'open':
                                shot = j.params[1]
                                if shot == runner._shot:
                                    skip_init = True
                                    break
                runner.set_globaljob(globaljob)
                for k, jobset in enumerate(jobgroup):
                    flag = False
                    try:
                        r = runner.run(jobset, skip_init)
                    except:
                        r = {'error message': [
                            'runner.run failed', traceback.format_exc()]}
                        flag = True
                    finally:
                        r['worker output'] = ' '  # tmp.read()
                        #r['error message'] = []
                    try:
                        jobs, names = jobset
                        can_compress = jobs.can_compress
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
                                if isinstance(r[n], ndarray) and can_compress:
                                    r[n] = squeeze(r[n])
                                if (isinstance(r[n], ndarray) and
                                    r[n].size > 5e4 and len(r[n].shape) == 1 and
                                    can_compress and not any(isnan(r[n])) and
                                        ProxyWorkerBase.use_compress):
                                    r2[n] = FiledNDArray(r[n])
                                else:
                                    #                                 r2[n] = FileNDArray(r[n])
                                    r2[n] = r[n]
                        ret[k] = r2
                        r = r2
                    except:
                        r['error message'].append(traceback.format_exc())
                        ret[k] = r
                    self.result_queue.put((job_id, k, r))
#                   if flag: break
#                print 'putting data in queue', time.time()
#                self.result_queue.put((job_id, ret))
                self.task_queue.task_done()
            else:
                break
        runner.terminate()
        self.task_queue.task_done()
#                self.result_queue.put('ok')


class MDSMPProxyWorker(mp.Process, ProxyWorkerBase):
    def __init__(self, task_queue, result_queue, host, port, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(MDSMPProxyWorker, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.port = int(port)
        self.host = host

    def run(self, *args, **kargs):
        return ProxyWorkerBase.run_loop(self, *args, **kargs)


class MDSTHProxyWorker(threading.Thread, ProxyWorkerBase):
    def __init__(self, task_queue, result_queue, host, port, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(MDSTHProxyWorker, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.port = int(port)
        self.host = host
        ProxyWorkerBase.use_compress = True

    def run(self, *args, **kargs):
        return ProxyWorkerBase.run_loop(self, *args, **kargs)
