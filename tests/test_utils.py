import traceback

import pytest

import ifigure.interactive as interactive


def check_prop_read(obj):
    print('read property test :' + str(obj))
    props = interactive.property(obj)
    ret = {}
    for prop in props:
        try:
            val = interactive.property(obj, prop)
            print(str(prop) + ' : ' + str(val))
        except Exception:
            print('reading ' + str(prop) + ' failed')
            traceback.print_exc()
            return ret
        ret[prop] = val
    return ret


def check_prop_write(obj, data):
    print('write property test :' + str(obj))
    for prop in data:
        try:
            print(str(prop) + ' : ' + str(data[prop]))
            interactive.property(obj, prop, data[prop])
        except Exception:
            print('writinging ' + str(prop) + ' failed')


@pytest.fixture(scope='module')
def piscope_session():
    try:
        interactive.launch()
    except Exception as exc:
        pytest.skip('piScope session could not be launched: {}'.format(exc))

    yield

    try:
        interactive.shutdown()
    except Exception:
        pass