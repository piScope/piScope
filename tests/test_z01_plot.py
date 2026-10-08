'''
Focused tests for the interactive plot command.
'''

from pathlib import Path

import numpy as np

import ifigure.interactive as interactive
import pytest

from tests.test_utils import (
    _assert_png_created,
    _assert_png_matches,
    _render_png_case,
    check_prop_read,
    piscope_session,
)


pytestmark = [pytest.mark.full]

PLOT_COMMAND = 'plot'
ENABLE_PNG_VISUAL = True
PNG_BASELINE_SUBDIR = 'plot'
PNG_MAE_TOL = 0.02
PNG_P99_TOL = 0.12


@pytest.fixture
def line_data():
    x = np.linspace(0.0, 1.0, 32)
    y = np.sin(2.0*np.pi*x)
    z = np.cos(2.0*np.pi*x)
    y2 = np.vstack([y, 0.5*y + 0.25])
    return x, y, z, y2


def _plot_cases(data):
    x, y, z, y2 = data
    return [
        ('y_only', lambda viewer: viewer.plot(y)),
        ('xy', lambda viewer: viewer.plot(x, y)),
        ('y_with_style', lambda viewer: viewer.plot(y, 'r--')),
        ('xy_with_style', lambda viewer: viewer.plot(x, y, 'ko-')),
        ('xy_multiline', lambda viewer: viewer.plot(x, y2)),
        ('xy_colored_line', lambda viewer: viewer.plot(x, y, z, cz=True)),
        ('xy_with_kwargs', lambda viewer: viewer.plot(x, y, linewidth=2.0, marker='o')),
    ]


def _png_case_sinewave(viewer):
    x = np.linspace(0.0, 10.0, 100)
    y = np.sin(x)
    viewer.plot(x, y)
    viewer.title('Sine Wave')
    viewer.xlabel('x-axis')
    viewer.ylabel('y-axis')
    viewer.legend('curve1')


def _png_case_multiline(viewer):
    x = np.linspace(0.0, 1.0, 64)
    y1 = np.sin(2.0 * np.pi * x)
    y2 = 0.5 * np.cos(2.0 * np.pi * x)
    viewer.plot(x, np.vstack([y1, y2]))
    viewer.title('Plot Multiline')
    viewer.xlabel('x')
    viewer.ylabel('y')
    viewer.legend(('sin', 'cos'))


PNG_CASES = [
    ('sinewave', _png_case_sinewave),
    ('multiline', _png_case_multiline),
]


BASELINE_DIR = Path(__file__).parent / 'reference_images' / PNG_BASELINE_SUBDIR
GENERATED_DIR = Path(__file__).parent / 'generated_images' / PNG_BASELINE_SUBDIR


@pytest.mark.parametrize('case_name,run_case', _plot_cases((
    np.linspace(0.0, 1.0, 32),
    np.sin(2.0*np.pi*np.linspace(0.0, 1.0, 32)),
    np.cos(2.0*np.pi*np.linspace(0.0, 1.0, 32)),
    np.vstack([
        np.sin(2.0*np.pi*np.linspace(0.0, 1.0, 32)),
        0.5*np.sin(2.0*np.pi*np.linspace(0.0, 1.0, 32)) + 0.25,
    ]),
)), ids=lambda value: value if isinstance(value, str) else None)
def test_plot_variants(piscope_session, case_name, run_case):
    del case_name
    viewer = interactive.figure()
    obj = run_case(viewer)
    assert obj is not None
    props = check_prop_read(obj)
    assert isinstance(props, dict)


@pytest.mark.parametrize('case_name,case_func', PNG_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_plot_png_regression_cases(piscope_session, case_name, case_func):
    baseline = BASELINE_DIR / '{}.png'.format(case_name)
    if not baseline.exists():
        pytest.skip('baseline image missing: {}'.format(baseline))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_png = GENERATED_DIR / '{}.png'.format(case_name)
    _render_png_case(case_func, out_png, threed=False)
    _assert_png_created(out_png)
    _assert_png_matches(baseline, out_png, mae_tol=PNG_MAE_TOL, p99_tol=PNG_P99_TOL)
