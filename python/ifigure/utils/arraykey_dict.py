def find_all_keys(d, key):
    return [x for x in list(d) if x.startswith(key+'(')]


def find_idx(keys):
    return [int((x.split('(')[1]).strip()[:-1]) for x in keys]


def key_exists(d, key):
    return key in d or len(find_all_keys(d, key)) > 0


def set_value(d, key, value, size, defv):
    v = [defv]*size
    if len(value) <= len(v):
        v[:len(value)] = value
    else:
        v = value[:len(v)]
    d[key] = v


def clean_key(d, key):
    keys = find_all_keys(d, key)
    for k in keys:
        d.pop(k)
    return d


def read_value(d, key, def_v=None, size=None):
    if key in d:
        return d[key]
    else:
        keys = find_all_keys(d, key)
        idx = find_idx(keys)
        if size is None:
            val = [def_v] * max(idx)
        else:
            val = [def_v] * size

        for i, k in zip(idx, keys):
            val[i-1] = d[k][0]
        return val
