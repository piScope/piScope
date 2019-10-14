from __future__ import print_function
######################################################
#     sample "run" script for parametric solver
######################################################
#
#  this script consist from
#
#    1) modifier function
#        this function defines how to modify the
#        model based on parameter. it should accept
#        three arguments.
#           model : a model directory for each case
#           name  : a list of variables to be modified
#           value : a list of values, to which variabls
#                   are set
#
#        hint:
#          1) setting->parameters is copyed
#             to model->parameters. global variables
#             to the model should be stored here
#          2) each cases should be indpependent run.
#             this allows multi-threading of parameter
#             scan
#          3) if you are running models mutually dependent
#             prepare different solver script
#
#
#    2) main script to run parametrci scan
#        In usual usage, it is not necessary
#        to change this part.
#        this part of script is exposed to user as
#        an sample.
#
import wx
import weakref
import threading
from six.moves import queue as Queue
import ifigure.events


def modifier(worker, name, param):

    print('Running modifier')
    print(('working on model directory ...', model))
    for i in range(len(name)):
        print(('appling new parameter...', name[i], param[i]))
        worker.parameters.setvar(name[i], param[i])


renew_model_each_time = True
solver = obj.get_parent()
tmodel = solver._model
use_def_merger = solver._use_def_merger
vname = solver._pname
value = solver._pvalue
run_cases = solver._run_cases
print(run_cases)


def run_workers(workers, sol):
    def submit(worker, k, queue):
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

        solver.apply_modifier(modifier, worker, k)
        threads = model.Run(return_queue=queue)
        # print 'running ', model.get_full_path(), threads[0]
        worker._thread_name = threads[0]

    def finish_job(method, idx, w, sol, queue):
        method(idx, w, sol)
        queue.put(w)

    q = Queue.Queue()
    solver._queue = q
    finished = 0
    current = 0
    status = weakref.WeakKeyDictionary()
    work_id = weakref.WeakKeyDictionary()
    for w in workers:
        status[w] = False

    model_name = solver._model.name
    threads = {}
    aborted = False
    run_index = [i for i in range(len(run_cases)) if run_cases[i]]
    while finished < len(run_index):
        if aborted and not any(status):
            break
        for w in workers:
            if (not status[w] and
                    current < len(run_index) and not aborted):
                wx.CallAfter(submit, *(w, run_index[current], q))
#                 t = submit(solver, w, current, q)[0]
                work_id[w] = run_index[current]
                status[w] = True
#                 else:
#                    finished = finished + 1
                current = current + 1

        try:
            t = q.get(True)
            # t = thread name  : thread done
            #     worker       : finish job done
            #     'abort job'  : abort parametric scan
            for o in workers:
                if o._thread_name == t:
                    w = o
                    break
        except Queue.Empty:
            print(('not respond', finished))
            continue
        if t == 'abort job':
            abroted = True
        if t in workers:
            status[t] = False
            finished = finished + 1
#             print finished, sum(run_index)):
            continue

        # print 'response from', w, threading.current_thread()
        rpath = tmodel.get_root_model().get_td_path(tmodel)
        rname = tmodel.get_root_model()._name
        rmodel = w.get_child(name=rname)
        model = rmodel.resolve_td_path(rpath)

        if model._finish_script == '':
            model._finish_script = solver.merge_sol.get_full_path()
        # print 'calling merge_sol', model.do_finish
        wx.CallAfter(finish_job, model.do_finish, work_id[w], w, sol, q)
#        status[w] = False
#        finished = finished + 1

    solver._queue = None


task = obj.getvar("task")

print('### starting parametric solver ###')
solver.print_cases()
if task < 1:
    stop()

print('### apply modifier             ###')

if task < 2:
    stop()

print('### run all models             ###')
sol_base = solver._sol
rpath = tmodel.get_root_model().get_td_path(tmodel)
rname = tmodel.get_root_model()._name

if solver._num_worker < 1:
    for k, xxx in enumerate(sol_base.get_children()):
        name, case_xxx = xxx
        rmodel = case_xxx.get_child(name=rname)
        model = rmodel.resolve_td_path(rpath)
        print((case_xxx, model))
        if model is not None:
            solver.apply_modifier(modifier, case_xxx, k)
            model.Run()
else:
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
