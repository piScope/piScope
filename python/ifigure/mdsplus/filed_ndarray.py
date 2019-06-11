'''

  filed_ndarray 
  
  to transfer a large  data between processes.
  instead of pushing the data into pipe, 
  it creates files with two resolutions.
  main process will open coarse resolution file
  first.

  FileNDArray : used in sub process
  FileNDArrayAutoDel : used in main process, allowing
                       automatic delete of file


'''
import traceback
import tempfile
import numpy
import numpy
import os
import time
import ifigure.utils.debug as debug
debug.debug_default_level = 1
dprint1, dprint2, dprint3 = debug.init_dprints('FigNDArray')


def random_tmp_name(seed='1'):
    # generate a random string for an initial work dir
    from datetime import datetime
    import hashlib
    strtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S. %f")
    # print strtime
    m = hashlib.md5()
    m.update(strtime+str(seed))
    txt = m.hexdigest()
    return txt


class FiledNDArray(object):
    def __init__(self, array):
        self._decimation = False
        dprint3('Called here')
#        fid = tempfile.NamedTemporaryFile(delete=False)
#        name = fid.name
#        name = '/home/shiraiwa/my_tmp/'+random_tmp_name()
#        fid = open(name, 'w')
        fid, name = tempfile.mkstemp()
        self.dtype = str(array.dtype)
        self._level = 0
        self._level_size = {0: array.size}
        self._level_name = {0: name}
#        print 'Storing to', name
        array.tofile(name)
        os.close(fid)  # to close tempfile here
#        fid.close()
        if array.size > 2e4 and len(array.shape) == 1:
            #           fid = tempfile.NamedTemporaryFile(delete=False)
            #           name = fid.name
            #           name = '/home/shiraiwa/my_tmp/'+random_tmp_name()
            #           fid = open(name, 'w')
            fid, name = tempfile.mkstemp()
            array2 = self._decimate(array)
            dprint3('Storing to', name)
            array2.tofile(name)
            os.close(fid)  # to close tempfile here
#           fid.close()
            self._level = 1
            self._level_size[1] = array2.size
            self._level_name[1] = name

    def restore(self, level=None):
        #        return range(1000)
        if level is None:
            level = self._level
        try:
            dprint2('Restoring' +
                    self._level_name[level].__repr__())
            val = numpy.fromfile(self._level_name[level],
                                 dtype=self.dtype)
            os.remove(self._level_name[level])
            del self._level_name[level]
        except:
            dprint2('Failed to restore the file' +
                    self._level_name[level].__repr__())
            raise
        return val

    def _filename(self, level=None):
        if level is None:
            level = 0
        return self.name+'_'+str(level)

    def _decimate(self, x):
        #        print x.shape
        chunksize = 4000
        numchunks = x.size//chunksize
        if x.size//numchunks > chunksize:
            chunksize = x.size//numchunks
#        if numchunks < 100:
#        numchunks = 2000
#        chunksize = x.size/numchunks

        xchunks = x[:chunksize*numchunks].reshape((-1, numchunks))
#        print numpy.nanmax(xchunks, axis=1)
#        print numpy.nanmax(xchunks, axis=1).shape
#        print numchunks, chunksize
        x3 = numpy.vstack((numpy.nanmin(xchunks, axis=1), numpy.nanmax(
            xchunks, axis=1))).transpose().reshape(chunksize*2)
#        print x3.shape
        # append left over..
        if chunksize*numchunks < x.size:
            x2 = numpy.hstack((x3, numpy.nanmin(
                x[chunksize*numchunks:]), numpy.nanmax(x[chunksize*numchunks:])))
            return x2
        else:
            return x3

##
# add auto delete to filed_ndarray
##
# used in main process, so that it will delete the fiel
# when it is done.


class FiledNDArrayAutoDel(FiledNDArray):
    def __del__(self):
        for level in self._level_name:
            if os.path.exists(self._level_name[level]):
                os.remove(self._level_name[level])
