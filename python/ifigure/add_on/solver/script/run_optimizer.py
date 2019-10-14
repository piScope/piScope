from __future__ import print_function
#
#   this is a skelton for a optimizer
#
#   It optimize parameter variables in model.param
#   to minimize a cost function
#
#   The cost function should be provilded by a user.
#
import wx
import weakref
import threading
from six.moves import queue as Queue
import ifigure.events


def modifier(worker, names, values):
    print('Running modifier')
    print(('working on model directory ...', worker))
    for name, value in zip(names, values):
        print(('appling new parameter...', name, value))
        worker.parameters.setvar(name, value)


solver = obj.get_parent()
tmodel = solver._model
rpath = tmodel.get_root_model().get_td_path(tmodel)
rname = tmodel.get_root_model()._name


def locate_cost_script():
    if solver._cost.startswith('.'):
        txt = solver.get_full_path()+solver._cost
    else:
        txt = solver._cost
    root = solver.get_root_parent()
    exec(root._name + ' = root')
    return eval(txt)


use_def_merger = solver._use_def_merger
renew_model_each_time = False


def run_workers(worker, sol):
    def submit(worker, queue, values):
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

        names = solver._pname
        modifier(worker, names, values)

        threads = model.Run(return_queue=queue)
        worker._thread_name = threads[0]

    def finish_job(method, idx, w, sol, queue):
        method(idx, w, sol)
        queue.put(w)
        solver._queue = None

    q = Queue.Queue()
    solver._queue = q
    cost_script = locate_cost_script()

    func_failed = False

    def func(values, w=worker, queue=q, ):
        aborted = False

        wx.CallAfter(submit, *(w, queue, values))
        try:
            while True:
                t = queue.get(True)
                if t == w._thread_name:
                    break
                elif t == 'abort job':
                    aborted = True
            if aborted:
                raise ValueError
                func_failed = True
            rmodel = w.get_child(name=rname)
            model = rmodel.resolve_td_path(rpath)
            c = cost_script.RunA(model)
            return c
        except Queue.Empty:
            solver._queue = None
            print('Failed to get response')
            raise ValueError

    # call scipy optimizer here
    from scipy.optimize import minimize

    try:
        kargs = solver._opt_kargs
        values = solver._init_value
        ret = minimize(func, values, **kargs)
    except:
        import traceback
        traceback.print_exc()
        solver._queue = None
        return
    if func_failed:
        return
    rmodel = w.get_child(name=rname)
    model = rmodel.resolve_td_path(rpath)

    if (model._finish_script == ')' or
            use_def_merger):
        model._finish_script = solver.merge_sol.get_full_path()
    # print 'calling merge_sol', model.do_finish
    wx.CallAfter(finish_job, model.do_finish, 0, w, sol, q)
    t = q.get(True)
    if t == 'abort job':
        print('abort recieved during postprocessing...')
    solver._queue = None
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

t = threading.Thread(target=run_workers, args=(workers[0], sol_base))
wx.CallAfter(t.start)
