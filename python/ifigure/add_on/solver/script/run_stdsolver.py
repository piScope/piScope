from __future__ import print_function
#
#   run script for StandardSolver
#
#   make a thread to wait for the result,
#   and the thread submit a job, which is started
#   in a main thread.
#
from six.moves import queue as Queue
import threading
import weakref
import wx
renew_model_each_time = True
solver = obj.get_parent()
tmodel = solver._model
use_def_merger = solver._use_def_merger


def run_workers(workers, sol):
    def submit(worker, queue):
        rpath = tmodel.get_root_model().get_td_path(tmodel)
        rname = tmodel.get_root_model()._name
        rmodel = worker.get_child(name=rname)

        if (renew_model_each_time and
                rmodel is not None):
            # print "Desotry", rmodel
            rmodel.destroy()
        rmodel = worker.get_child(name=rname)
        if rmodel is None:
            tmodel.get_root_model().duplicate(worker, rname, save_script_link=True)
            rmodel = worker.get_child(name=rname)

        model = rmodel.resolve_td_path(rpath)
        threads = model.Run(return_queue=queue)
        # print 'running ', model.get_full_path(), threads[0]
        worker._thread_name = threads[0]

    def finish_job(method, idx, w, sol, queue):
        method(idx, w, sol)
        queue.put(w)
        solver._queue = None

    q = Queue.Queue()
    solver._queue = q
    wx.CallAfter(submit, *(w, q))
    while True:
        try:
            t = q.get(True)
            break
        except Queue.Empty:
            solver._queue = None
            print('Failed to get response')
            return
        # print 'response from', w, threading.current_thread()
        if t == 'abort job':
            # for a moment let's ignore this...
            continue

    rpath = tmodel.get_root_model().get_td_path(tmodel)
    rname = tmodel.get_root_model()._name
    rmodel = w.get_child(name=rname)
    model = rmodel.resolve_td_path(rpath)

    if (model._finish_script == ')' or
            use_def_merger):
        model._finish_script = solver.merge_sol.get_full_path()
    # print 'calling merge_sol', model.do_finish
    wx.CallAfter(finish_job, model.do_finish, 0, w, sol, q)
#    model.do_finish(0, w, sol)


sol_base = solver._sol
workers = solver.get_workers()
if len(workers) == 0:
    print('no workers')
    stop()
if solver._queue is not None:
    print('there is a waiting queue, exiting...')
    stop()
for w in workers:
    w._thread_name = ''
t = threading.Thread(target=run_workers, args=(workers, sol_base))
wx.CallAfter(t.start)
