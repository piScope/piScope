'''
Focused tests for the interactive clim command.
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

PLOT_COMMAND = 'clim'
ENABLE_PNG_VISUAL = True
PNG_BASELINE_SUBDIR = 'clim'
PNG_MAE_TOL = 0.02
PNG_P99_TOL = 0.12


def _image_data(scale=1.0):
    x = np.linspace(-1.0, 1.0, 48)
    y = np.linspace(-1.0, 1.0, 40)
    X, Y = np.meshgrid(x, y)
    return scale * np.sin(np.pi * X) * np.cos(np.pi * Y)


def _clim_cases():
    z = _image_data(scale=2.0)

    def _run_default(viewer):
        obj = viewer.image(z, cmap='viridis')
        viewer.clim(-0.5, 0.5)
        return obj

    def _run_tighter(viewer):
        obj = viewer.image(z, cmap='viridis')
        viewer.clim(-0.3, 0.3)
        return obj

    return [
        ('default_clip', _run_default),
        ('tight_clip', _run_tighter),
    ]


def _png_case_default(viewer):
    viewer.image(_image_data(scale=2.0), cmap='viridis')
    viewer.clim(-0.5, 0.5)
    viewer.title('Clim Default')


PNG_CASES = [
    ('default', _png_case_default),
]


BASELINE_DIR = Path(__file__).parent / 'reference_images' / PNG_BASELINE_SUBDIR
GENERATED_DIR = Path(__file__).parent / 'generated_images' / PNG_BASELINE_SUBDIR


@pytest.mark.parametrize('case_name,run_case', _clim_cases(), ids=lambda value: value if isinstance(value, str) else None)
def test_clim_variants(piscope_session, case_name, run_case):
    del case_name
    viewer = interactive.figure()
    obj = run_case(viewer)
    assert obj is not None
    props = check_prop_read(obj)
    assert isinstance(props, dict)


@pytest.mark.parametrize('case_name,case_func', PNG_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_clim_png_regression_cases(piscope_session, case_name, case_func):
    baseline = BASELINE_DIR / '{}.png'.format(case_name)
    if not baseline.exists():
        pytest.skip('baseline image missing: {}'.format(baseline))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_png = GENERATED_DIR / '{}.png'.format(case_name)
    _render_png_case(case_func, out_png, threed=False)
    _assert_png_created(out_png)
    _assert_png_matches(baseline, out_png, mae_tol=PNG_MAE_TOL, p99_tol=PNG_P99_TOL)
