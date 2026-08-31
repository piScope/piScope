import pickle

from ifigure.ifigure_config import pickle_protocol

def dump(data, fid, **kwargs):
    kwargs['protocol'] = pickle_protocol
    if pickle_protocol == 2:
        kwargs['fix_imports'] = True
    pickle.dump(data, fid, **kwargs)

def load(fid):
    return pickle.load(fid, fix_imports=True, encoding='latin1')

dumps = pickle.dumps
loads = pickle.loads
