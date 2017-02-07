def parse_server_string(txt):
    l = txt.split(':')
    p = l[-2]
    t = l[-1]
    s = ':'.join(l[:-2])
    return s, p, t
