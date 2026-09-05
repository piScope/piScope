'''
Focused tests for the interactive semilogy command.
'''

from pathlib import Path

import numpy as np
import pytest

import ifigure.interactive as interactive

from tests.test_utils import (
    _assert_png_created,
    _assert_png_matches,
    _render_png_case,
    check_prop_read,
    piscope_session,
)


pytestmark = [pytest.mark.full]

PLOT_COMMAND = 'semilogy'
ENABLE_PNG_VISUAL = True
PNG_BASELINE_SUBDIR = 'semilogy'
PNG_MAE_TOL = 0.02
PNG_P99_TOL = 0.12


def _semilogy_cases():
    x = np.linspace(0.1, 10.0, 120)
    y = np.exp(x / 5.0)
    y2 = np.exp(x / 6.0)
    return [
        ('xy_default', lambda viewer: viewer.semilogy(x, y)),
        ('xy_style', lambda viewer: viewer.semilogy(x, y, 'r--')),
        ('xy_kwargs', lambda viewer: viewer.semilogy(x, y2, linewidth=2.0, marker='o')),
    ]


def _png_case_default(viewer):
    x = np.linspace(0.1, 10.0, 120)
    y = np.exp(x / 5.0)
    viewer.semilogy(x, y)
    viewer.title('Semilogy Default')
    viewer.xlabel('x')
    viewer.ylabel('exp(x/5)')


PNG_CASES = [
    ('default', _png_case_default),
]


BASELINE_DIR = Path(__file__).parent / 'reference_images' / PNG_BASELINE_SUBDIR
GENERATED_DIR = Path(__file__).parent / 'generated_images' / PNG_BASELINE_SUBDIR


@pytest.mark.parametrize('case_name,run_case', _semilogy_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_semilogy_variants(piscope_session, case_name, run_case):
    del case_name
    viewer = interactive.figure()
    obj = run_case(viewer)
    assert obj is not None
    props = check_prop_read(obj)
    assert isinstance(props, dict)


@pytest.mark.parametrize('case_name,case_func', PNG_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_semilogy_png_regression_cases(piscope_session, case_name, case_func):
    baseline = BASELINE_DIR / '{}.png'.format(case_name)
    if not baseline.exists():
        pytest.skip('baseline image missing: {}'.format(baseline))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_png = GENERATED_DIR / '{}.png'.format(case_name)
    _render_png_case(case_func, out_png, threed=False)
    _assert_png_created(out_png)
    _assert_png_matches(baseline, out_png, mae_tol=PNG_MAE_TOL, p99_tol=PNG_P99_TOL)
