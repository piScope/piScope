import multiprocessing as mp
import time


class MPWorker(mp.Process):
    def __init__(self, task_queue, result_queue, *args, **kargs):
        #   def __init__(self,  *args, **kargs):
        super(MPWorker, self).__init__(*args, **kargs)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self, *args, **kargs):
        while True:
            jobs = self.task_queue.get(True)
            if jobs == '1':
                self.result_queue.put('2')
                break
            time.sleep(1)
