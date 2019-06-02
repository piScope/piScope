import six

if six.PY2:
    import cPickle as pickle
else:
    import pickle

from ifigure.ifigure_config import pickle_protocol

def dump(data, fid, **kwargs):
    kwargs['protocol'] = pickle_protocol
    pickle.dump(data, fid, **kwargs)


load = pickle.load
dumps = pickle.dumps
loads = pickle.loads
