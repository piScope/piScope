from __future__ import print_function

'''
MDSplus job runner

There is two modes:
  1) a mode which uses MDSplus.Connection 
     This mode is for threaded worker and default
  2) a mode which uses MDSplus.Tree and MDSplusData
     This mode is for multiprocessing worker
'''


import sys
import time
import tempfile
import traceback
import threading
from ifigure.utils.pickled_pipe import PickledPipe
from .utils import parse_server_string
debug_runner = False


class JobRunner(object):
    def __init__(self):
        self.use_mdsconnect = False
        self.connection_str = ''
        self.connection = None
        self.g = {}
        self._shot = -1
        self.gjob = None   # global tdi (executed when shot number changed)

    def __del__(self):
        del self.connection
#        self.connection = None
    def run(self, jobset, skip_init):

        import MDSplus
        from MDSplus import Connection

        self.error = []
        jobs, names = jobset
        self.r = {'error message': []}
        sig_names = []
        dim_names = []
        try:
            for k, job in enumerate(jobs):
                for j in job:
                    if j.command == 'connection_mode':
                        #                   print 'connection_mode param', self.connection_str, j.params, self.connection
                        #                   if self.connection is not None:
                        #                        del self.connection
                        #                        self.connection = None
                        if self.connection_str != j.params[0]:
                            #                   if True:
                            server, port, tree = parse_server_string(
                                j.params[0])
                            self.use_mdsconnect = (False if server.upper() ==
                                                   'DIRECT' else True)
                            if self.use_mdsconnect:
                                if self.connection is not None:
                                    del self.connection
                                    self.connection = None
                                try:
                                    if port != '':
                                        server = server + ':' + port
                                    self.connection = Connection(server)
                                    self.connection_str = j.params[0]
                                    res = 'ok'
                                except:
                                    self.r['error message'] = ['connection error' +
                                                               traceback.format_exc()]
                                    self.r[names[k]] = None
                                    return self.r
                            else:
                                if self.connection is not None:
                                    del self.connection
                                    self.connection = None
                                res = 'ok'
                            self._connection_flag = True
                        else:
                            res = 'ok'
                    else:
                        if j.command == 'init':
                            if skip_init:
                                continue
                            else:
                                j.command = 'value'
                        if self.use_mdsconnect:
                            #                       res = self._run_job_mdsconnect(j, sig_names, dim_names, names[k])
                            res = self._run_job_mdsconnect(j)
                            if len(self.error) != 0:
                                self.r['error message'] = self.error[:]
                                self.r[names[k]] = res
                                return self.r
#                           return _evaluate_sig(self.r, sig_names, dim_names)
                        else:
                            res = self._run_job(j)
                            if len(self.error) != 0:
                                self.r['error message'] = self.error[:]
                                self.r[names[k]] = res
                                return self.r
                        self._connection_flag = False
#                           return _evaluate_sig(self.r, sig_names, dim_names)

                self.r[names[k]] = res
        except:
            self.error = ['run error', traceback.format_exc()]

#        self.r =  _evaluate_sig(self.r, sig_names, dim_names)
        self.r['error message'] = self.error
        return self.r

    def set_globaljob(self, job):
        self.gjob = job

    def terminate(self):
        if self.connection is not None:
            del self.connection
        self.connection = None

    def _run_script_txt(self, job):
        expr = job.params[0]
        try:
            code = compile(expr, '<string>', 'exec')
            g = {}
            l = {}
            exec(code, self.g, self.r)
            return 'ok'
        except:
            self.error = ['Scrip Error', expr, sys.exc_info()[0]]
        return None

#    def _run_job_mdsconnect(self, job, sig_names,dim_names, name):
    def _run_job_mdsconnect(self, job):
        com = job.command
        if com == 'novalue':
            return ''
        if debug_runner:
            print(job)
        # print job
        # print threading.current_thread().name, com, job.params
        if com == 'open':
            tree = job.params[0]
            shot = job.params[1]
            try:
                #                  print tree,
                #                  print long(shot)
                if tree != '':
                    self.connection.openTree(tree, int(shot))
            except:
                self.error = ['run error', traceback.format_exc()]
                return None
            try:
                t = tree.split(',')[0].strip()
                self.connection.setDefault('\\' + t + '::TOP')
            except:
                pass
            try:
                if shot != self._shot:
                    expr = 'reset_private();reset_public();1'
                    r = self.connection.get(expr).data()
                if self._connection_flag:
                    if self.gjob is not None:
                        expr = self.gjob.params[0]
                        # print 'performing global tdi', expr
                        r = self.connection.get(expr).data()
                self._connection_flag = False
                self._shot = shot
                return 'ok'
            except:
                self.error = ['run error', traceback.format_exc()]
                return None
        elif com == 'defnode':
            node = job.params[0]
            try:
                if node.strip() != '':
                    self.connection.setDefault(node)
                return 'ok'
            except:
                # print(node)
                self.error = ['run error', traceback.format_exc()]
                return None
        elif com == 'value':
            try:
                expr = job.params[0]

                r = self.connection.get(expr).data()
                return r
            except:
                self.error = ['run error', expr, traceback.format_exc()]
                return None
        elif com == 'valuesig':
            try:
                expr = job.params[0]
                expr = 'gettsbase(_shot,' + '"'+expr.upper()+'")'
                r = self.connection.get('_piscopevar=execute($)', expr).data()
                return r
            except:
                self.error = ['run error', expr, traceback.format_exc()]
                return None
#           elif com == 'dim_of':# this is not used anymore
#               expr = job.params[0]
#               dim_names.append(name)
#               return expr
        elif com == 'script_txt':
            return self._run_script_txt(job)

#    def _run_job(self, job, sig_names, dim_names, name):
    def _run_job(self, job):
        import MDSplus
        from MDSplus import Connection
        com = job.command
        if com == 'novalue':
            return ''
        if com == 'open':
            tree = job.params[0]
            shot = job.params[1]
            try:
                if tree != '':
                    self.t = MDSplus.Tree(tree, int(shot))
                if shot != self._shot:
                    expr = 'reset_private();reset_public();1'
#                      r =MDSplus.Data.compile(expr).evaluate().data()
                    r = MDSplus.Data.execute(expr).data()
                if self._connection_flag:
                    if self.gjob is not None:
                        expr = self.gjob.params[0]
                        r = MDSplus.Data.execute(expr).data()
                self._connection_flag = False
                self._shot = shot
                return 'ok'
            except:
                #                  print traceback.format_exc()
                self.error = ['run error', traceback.format_exc()]
                return None
        elif com == 'defnode':
            node = job.params[0]
            try:
                if node.strip() != '':
                    tn = self.t.getNode(node)
                    self.t.setDefault(tn)
                return 'ok'
            except:
                self.error = ['run error', traceback.format_exc()]
                return None
        elif com == 'value':
            try:
                expr = job.params[0]
                r = MDSplus.Data.execute(expr).data()
#                  r =MDSplus.Data.execute(expr).data()
#                 sig_names.append(name)
                return r
            except:
                self.error = ['run error', expr, traceback.format_exc()]
                return None
        elif com == 'valuesig':
            try:
                expr = job.params[0]
                expr = 'gettsbase(_shot, ' + '"'+expr.upper()+'")'
                r = MDSplus.Data.execute('_piscopevar=execute($)', expr).data()
#                  r =MDSplus.Data.execute(expr).data()
#                 sig_names.append(name)
                return r
            except:
                self.error = ['run error', expr, traceback.format_exc()]
                return None

#           elif com == 'dim_of':     # this is not used anymore
#               expr = job.params[0]  ### expr should be y, 0 (= dim_of(y, 0))
#               dim_names.append(name)
#               return expr
        elif com == 'script_txt':
            return self._run_script_txt(job)
