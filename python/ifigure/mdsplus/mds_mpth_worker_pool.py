from __future__ import print_function
#
#   MDS worker pool for threaded worker and multiprocessing worker.
#
from ifigure.mdsplus.mds_mpth_directworker import MDSMPDirectWorker, MDSTHDirectWorker
from ifigure.mdsplus.mds_mpth_proxyworker import MDSMPProxyWorker, MDSTHProxyWorker
import multiprocessing as mp
import time
import weakref
import threading
from six.moves import queue as Queue
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('MDSMPWorkerPool')
jllock = threading.Lock()


class MDSWorkerPoolBase(object):
    job_id = 0
    job_list = {}

    def submit_ana_group(self, ana_group):
        job_id = MDSWorkerPoolBase.job_id

#       if hasattr(ana_group[0],'fig_mds'):
#           print 'submit', ana_group[0].fig_mds()
        jllock.acquire()
        MDSWorkerPoolBase.job_list[job_id] = [len(ana_group),
                                              weakref.ref(ana_group)]
        self.tasks.put((job_id, [(a.jobs, a.jobnames)
                                 for a in ana_group], ana_group.global_tdi))
        jllock.release()
        MDSWorkerPoolBase.job_id = job_id + 1

    def check_ana_group_done(self):
        from ifigure.mdsplus.mdsscope import GlobalCounter

        try:
            #           print 'waiting result'
            v = self.results.get(True)
        except:
            import traceback
            print(traceback.format_exc())
            return None
        self.results.task_done()
        if not (isinstance(v, tuple) and len(v) == 3):
            return v
        job_id, idx, result = v
        jllock.acquire()
        if not job_id in MDSWorkerPoolBase.job_list:
            print(' should not come here,, but just in case it ')
            return None
        jllock.release()
        if job_id in MDSWorkerPoolBase.job_list:
            xxx = MDSWorkerPoolBase.job_list[job_id]
            try:
                #                for a, v in zip(ana_group, result):
                #                    a.set_result(v != None, v)
                ana_group = xxx[1]()
                if ana_group is None:
                    return None
                ana_group[idx].set_result(result != None, result)
            except:
                import traceback
                print(traceback.format_exc())
                return None
            xxx[0] = xxx[0]-1
            if xxx[0] == 0:
                del MDSWorkerPoolBase.job_list[job_id]
            return ana_group, idx
        #   should not come here,, but just in case it
        return None

    def abort_job(self):
        tasks = []
        while not self.tasks.empty():
            try:
                j = self.tasks.get(False)
                self.tasks.task_done()
                tasks.append(j)
            except:
                import traceback
                traceback.print_exc()
                break
        ana_groups = []
        for job_id, job, res in tasks:
            if job_id in MDSWorkerPoolBase.job_list:
                xxx = MDSWorkerPoolBase.job_list[job_id]
                ana_group = xxx[1]()
                ana_groups.append(ana_group)
                del MDSWorkerPoolBase.job_list[job_id]
        print(('cancelled jobs', ana_groups))
        return ana_groups

    def has_noresult(self):
        return self.results.empty()

    def is_alive(self, w_id):
        return self.workers[w_id].is_alive()

    def is_any_alive(self):
        return any([w.is_alive() for w in self.workers])

    def terminate_all(self):
        print('terminating all')
        num_alive = 0
        for w in self.workers:
            if w.is_alive():
                num_alive = num_alive + 1
        for x in range(num_alive):
            self.tasks.put(-1)
        self.tasks.join()
        print('joined')
        # stops the listening thread
        self.results.put('stop')

    def get_num_worker(self):
        return len(self.workers)


class MDSMPWorkerPool(MDSWorkerPoolBase):
    def __init__(self, num, *args, **kwargs):
        self.num = num
        MDSWorkerPoolBase.job_id = 0
        MDSWorkerPoolBase.job_list = {}

        type = args[0]
        if len(args) > 1:
            host = args[1]
            port = args[2]
        else:
            host = None
            port = None

        self.tasks = mp.JoinableQueue()
#       self.results= mp.Queue()
        self.results = mp.JoinableQueue()

        self.workers = [None]*num
        for i in range(num):
            if type == 'direct':
                w = MDSMPDirectWorker(
                    self.tasks, self.results, kwargs['translater'])
            else:
                w = MDSMPProxyWorker(
                    self.tasks, self.results, str(host), str(port))
            self.workers[i] = w
            time.sleep(0.1)
        for w in self.workers:
            w.start()


class MDSTHWorkerPool(MDSWorkerPoolBase):
    def __init__(self, num, *args, **kwargs):
        self.num = num
        MDSWorkerPoolBase.job_id = 0
        MDSWorkerPoolBase.job_list = {}

        type = args[0]
        if len(args) > 1:
            host = args[1]
            port = args[2]
        else:
            host = None
            port = None

        self.tasks = Queue.Queue()
        self.results = Queue.Queue()

        self.workers = [None]*num
        for i in range(num):
            if type == 'direct':
                w = MDSTHDirectWorker(
                    self.tasks, self.results, kwargs['translater'])
            else:
                w = MDSTHProxyWorker(
                    self.tasks, self.results, str(host), str(port))
            self.workers[i] = w
            time.sleep(0.1)
        for w in self.workers:
            w.start()
