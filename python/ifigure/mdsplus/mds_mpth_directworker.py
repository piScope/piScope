import multiprocessing as mp
import time
import tempfile
import traceback
import threading

from numpy import ndarray, isnan, squeeze
from ifigure.mdsplus.filed_ndarray import FiledNDArray


class DirectWorkerBase(object):
    use_compress = True

    def run_loop(self, translater, *args, **kargs):
        if translater == 'default':
            from ifigure.mdsplus.direct_jobrunner import JobRunner
        elif translater == 'ts':
            from ifigure.mdsplus.direct_jobrunner_ts import JobRunner
        runner = JobRunner()
        while True:
            time.sleep(0.01)
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
#                for k, jobset in enumerate(jobgroup):
#                   skip_init = False
#                   jobs, names = jobset
#                   for job in jobs:
#                     for j in job:
#                       if j.command == 'open':
#                           shot = j.params[1]
#                           if shot == runner._shot:
#                               skip_init = True
#                               break
                runner.set_globaljob(globaljob)
                for k, jobset in enumerate(jobgroup):
                    flag = False
                    try:
                        r = runner.run(jobset, False)
                    except:
                        r = {'error message': [
                            'runner.run failed', traceback.format_exc()]}
                        flag = True
                    finally:
                        r['worker output'] = ' '  # tmp.read()
       #                r['error message'] = []
                    try:
                        jobs, names = jobset
                        can_compress = jobs.can_compress
                        def_names = ['message',
                                     #                                 'pickle error',
                                     #                                 'network message',
                                     'worker output',
                                     'error message',
                                     'x', 'y', 'z',
                                     'xerr', 'yerr', 'zerr']
#                      if len(r['error message']) != 0:
#                          print r['error message']

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
                                        DirectWorkerBase.use_compress):
                                    r2[n] = FiledNDArray(r[n])
                                else:
                                    r2[n] = r[n]
                        ret[k] = r2
                        r = r2
                    except:
                        r['error message'].append(traceback.format_exc())
                        ret[k] = r
                        flag = True
                    self.result_queue.put((job_id, k, r))
                #   if flag: break
#                self.result_queue.put((job_id, ret))
                self.task_queue.task_done()
#                print 'put data in queue', time.time()
            else:
                #                runner.terminate()
                #                self.result_queue.put('ok')
                break
        runner.terminate()
        del runner
        self.task_queue.task_done()


class MDSMPDirectWorker(mp.Process, DirectWorkerBase):
    def __init__(self, task_queue, result_queue, translater, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(MDSMPDirectWorker, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.translater = translater

    def __repr__(self):
        return threading.Thread.__repr__(self) + ' translater=' + self.translater

    def run(self, *args, **kargs):
        DirectWorkerBase.run_loop(self, self.translater, *args, **kargs)


class MDSTHDirectWorker(threading.Thread, DirectWorkerBase):
    def __init__(self, task_queue, result_queue, translater, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(MDSTHDirectWorker, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.translater = translater
        DirectWorkerBase.use_compress = True

    def __repr__(self):
        return threading.Thread.__repr__(self) + ' translater=' + self.translater

    def run(self, *args, **kargs):
        DirectWorkerBase.run_loop(self, self.translater, *args, **kargs)
