import os


def get_username():
    if 'USER' in os.environ:
        return os.environ['USER']
    if 'USERNAME' in os.environ:
        return os.environ['USERNAME']
    return 'UNKNOWN'
