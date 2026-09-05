import traceback
import importlib.util
from pathlib import Path

import pytest
import numpy as np

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


def _load_png(path):
    import matplotlib.image as mpimg

    arr = mpimg.imread(str(path))
    if np.issubdtype(arr.dtype, np.integer):
        arr = arr.astype(np.float32) / 255.0
    else:
        arr = arr.astype(np.float32)
    return arr


def _assert_png_created(path):
    assert path.exists(), 'PNG was not created: {}'.format(path)
    assert path.stat().st_size > 0, 'PNG is empty: {}'.format(path)

    arr = _load_png(path)
    assert arr.ndim in (2, 3), 'unexpected PNG dimensions: {}'.format(arr.shape)
    assert arr.shape[0] > 0 and arr.shape[1] > 0, 'invalid PNG shape: {}'.format(arr.shape)
    assert float(np.std(arr)) > 0.001, 'PNG appears blank or uniform: {}'.format(path)


def _assert_png_matches(baseline, current, mae_tol=0.02, p99_tol=0.12):
    ref = _load_png(baseline)
    cur = _load_png(current)

    assert ref.shape == cur.shape, (
        'PNG shape mismatch: baseline={} current={}'.format(ref.shape, cur.shape)
    )

    diff = np.abs(ref - cur)
    mae = float(np.mean(diff))
    p99 = float(np.quantile(diff, 0.99))
    assert mae <= mae_tol and p99 <= p99_tol, (
        'image regression exceeded tolerance: mae={:.6f}, p99={:.6f}'.format(mae, p99)
    )


def _render_png_case(case_func, out_path, threed=False):
    viewer = interactive.figure(size=(500, 400))
    if threed:
        viewer.threed('on')
    case_func(viewer)
    viewer.savefig(str(out_path))


def _iter_command_test_modules(tests_dir=None):
    if tests_dir is None:
        tests_dir = Path(__file__).parent

    paths = sorted(list(tests_dir.glob('test_z[0-9]*.py')) + list(tests_dir.glob('test_zz*.py')))
    for path in paths:
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


def _collect_png_case_specs(module):
    if not getattr(module, 'ENABLE_PNG_VISUAL', False):
        return []

    command = getattr(module, 'PLOT_COMMAND', None)
    cases = getattr(module, 'PNG_CASES', None)
    if command is None or cases is None:
        raise ValueError(
            '{} enables PNG generation but missing PLOT_COMMAND or PNG_CASES'.format(
                module.__name__
            )
        )

    subdir = getattr(module, 'PNG_BASELINE_SUBDIR', command)
    threed = bool(getattr(module, 'PNG_THREED', False))
    mae_tol = float(getattr(module, 'PNG_MAE_TOL', 0.02))
    p99_tol = float(getattr(module, 'PNG_P99_TOL', 0.12))

    specs = []
    for case_name, case_func in cases:
        specs.append({
            'module': module.__name__,
            'command': command,
            'subdir': subdir,
            'case_name': case_name,
            'case_func': case_func,
            'threed': threed,
            'mae_tol': mae_tol,
            'p99_tol': p99_tol,
        })
    return specs


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