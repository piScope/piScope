import six

if six.PY2:
    import cPickle as pickle
else:
    import pickle

from ifigure.ifigure_config import pickle_protocol

def dump(data, fid, **kwargs):
    if six.PY2:
        pickle.dump(data, fid)
    else:
        kwargs['protocol'] = pickle_protocol
        if pickle_protocol == 2:
            kwargs['fix_imports'] = True
        pickle.dump(data, fid, **kwargs)

def load(fid):
    if six.PY2:
        return pickle.load(fid)
    else:
        return pickle.load(fid, fix_imports=True, encoding='latin1')

dumps = pickle.dumps
loads = pickle.loads
