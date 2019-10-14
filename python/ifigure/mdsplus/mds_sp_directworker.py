import sys
import time
import tempfile
import traceback
from ifigure.utils.pickled_pipe import PickledPipe
from .utils import parse_server_string


class JobRunner(object):
    def __init__(self):
        self.use_mdsconnect = False
        self.connection_str = ''
        self.connection = None
        self.g = {}
        self._shot = -1

    def run(self, jobset, skip_init):
        import MDSplus
        from MDSplus import Connection

        self.error = []
        jobs, names = jobset
        self.r = {}
        self.r['error message'] = ['']
        try:
            for k, job in enumerate(jobs):
                for j in job:
                    if j.command == 'connection_mode':
                        if self.connection_str != j.params[0]:
                            self.connection_str = j.params[0]
                            server, port, tree = parse_server_string(
                                self.connection_str)
                            self.use_mdsconnect = (False if server.upper() ==
                                                   'DIRECT' else True)
                            if self.use_mdsconnect:
                                if self.connection is not None:
                                    del self.connection
                                try:
                                    if port != '':
                                        server = server + ':' + port
                                    self.connection = Connection(server)
                                    res = 'ok'
                                except:
                                    res = ('connection error' +
                                           traceback.format_exc())
                            else:
                                if self.connection is not None:
                                    del self.connection
                                    self.connection = None
                                res = 'ok'
                        else:
                            res = 'ok'
                    else:
                        if j.command == 'init':
                            if skip_init:
                                continue
                            else:
                                j.command = 'value'
                        if self.use_mdsconnect:
                            res = self._run_job_mdsconnect(j)
                            if len(self.error) != 0:
                                self.r['error message'] = self.error
                                self.r[names[k]] = res
                                return self.r
                        else:
                            res = self._run_job(j)
                            if len(self.error) != 0:
                                self.r['error message'] = self.error
                                self.r[names[k]] = res
                                return self.r
                self.r[names[k]] = res
        except:
            self.error = ['run error', traceback.format_exc()]
        self.r['error message'] = self.error
        return self.r

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

    def _run_job_mdsconnect(self, job):
        com = job.command
        if com == 'open':
            tree = job.params[0]
            shot = job.params[1]
            try:
                self.connection.openTree(tree, int(shot))
                return 'ok'
            except:
                self.error = ['run error', traceback.format_exc()]
                return None
            self._shot = shot
        elif com == 'defnode':
            node = job.params[0]
            try:
                if node.strip() != '':
                    self.connection.setDefault(node)
                return 'ok'
            except:
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
        elif com == 'script_txt':
            return self._run_script_txt(job)

    def _run_job(self, job):
        import MDSplus
        from MDSplus import Connection

        com = job.command

        if com == 'open':
            tree = job.params[0]
            shot = job.params[1]
            try:
                self.t = MDSplus.Tree(tree, int(shot))
                return 'ok'
            except:
                self.error = ['run error', traceback.format_exc()]
                return None
            self._shot = shot
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
                r = MDSplus.Data.compile(expr).evaluate().data()
                return r
            except:
                self.error = ['run error', expr, traceback.format_exc()]
                return None
        elif com == 'script_txt':
            return self._run_script_txt(job)


if __name__ == '__main__':
    ch = PickledPipe(sys.stdin, sys.stdout)
    runner = JobRunner()
    while True:
        time.sleep(0.01)
        try:
            jobset = ch.recv(nowait=False)
        except EOFError:
            break
        if jobset != -1:
            tmp = tempfile.TemporaryFile()
            sys.stdout = tmp
            try:
                r = runner.run(jobset)
            except:
                r = {'error message': ['runner.run failed']}
#               r = {'error message':['message was received']}
                r['worker output'] = ''
                ch.send(r)
            finally:
                tmp.flush()
                tmp.seek(0)
                r['worker output'] = tmp.read()
                tmp.close()

                jobs, names = jobset
                def_names = ['worker output',
                             'error message',
                             'x', 'y', 'z',
                             'xerr', 'yerr', 'zerr']
                for n in names:
                    if not n in def_names:
                        def_names.append(n)
                r2 = {}
#               r = {n:r[n] for n in def_names if r.has_key(n)}
                for n in def_names:
                    if n in r:
                        r2[n] = r[n]

                ch.send(r2)
        else:
            break
