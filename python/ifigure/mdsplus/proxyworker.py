from ifigure.mdsplus.baseworker import MDSBaseWorker


class MDSProxyWorker(MDSBaseWorker):
    connection = None

    def __init__(self, *args, **kargs):
        super(MDSProxyWorker, self).__init__(*args, **kargs)
        pass

    def run(self, *args, **kargs):
        proc_name = self.name
        while True:
            job = self.task_queue.get(True)
            if job is None:
                self.task_queue.task_done()
                return
        return
