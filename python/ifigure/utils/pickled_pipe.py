import ifigure.utils.pickle_wrapper as pickle
import select
import time


class PickledPipe(object):
    '''
       PickledPipe(a, b)
       a: buffer for reading
       b: buffer for writing
    '''

    def __init__(self, in_f, out_f):
        self.in_f = in_f
        self.out_f = out_f

    def send(self, data):
        pickle.dump(data, self.out_f)
        self.out_f.flush()

    def recv(self, nowait=True):
        #        print self._check_readbuf()
        if self._check_readbuf() or not nowait:
            try:
                return pickle.load(self.in_f)
            except:
                return {'error message': ['pickle communicaiton error']}
        else:
            return None

    def _check_readbuf(self):
        #        print select.select([self.in_f],[],[], 0)[0]
        return self.in_f in select.select([self.in_f], [], [], 0)[0]
