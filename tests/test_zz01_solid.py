'''
Focused tests for the interactive solid command.
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

PLOT_COMMAND = 'solid'
ENABLE_PNG_VISUAL = True
PNG_BASELINE_SUBDIR = 'solid'
PNG_THREED = True
PNG_MAE_TOL = 0.02
PNG_P99_TOL = 0.12


def solid_data():
    indexed_vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    indexed_quads = np.array([[0, 1, 2, 3]])

    indexed_vertices_2d = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ])

    quad_xyzc = np.array([
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.3],
            [1.0, 1.0, 0.0, 0.6],
            [0.0, 1.0, 0.0, 1.0],
        ]
    ])

    cube_faces = np.array([
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]],
    ])

    return {
        'indexed_vertices': indexed_vertices,
        'indexed_quads': indexed_quads,
        'indexed_vertices_2d': indexed_vertices_2d,
        'quad_xyzc': quad_xyzc,
        'cube_faces': cube_faces,
    }


def _solid_cases(data):
    return [
        ('face_array_xyz', lambda viewer: viewer.solid(data['cube_faces'])),
        ('indexed_xyz', lambda viewer: viewer.solid(data['indexed_vertices'], data['indexed_quads'])),
        ('indexed_xy_with_zvalue', lambda viewer: viewer.solid(data['indexed_vertices_2d'], data['indexed_quads'], zvalue=0.25)),
        ('face_array_xyzc', lambda viewer: viewer.solid(data['quad_xyzc'])),
        ('indexed_with_edgecolor', lambda viewer: viewer.solid(data['indexed_vertices'], data['indexed_quads'], edgecolor='k', facecolor='cyan')),
    ]


def _png_case_cube(viewer):
    data = solid_data()
    viewer.solid(data['cube_faces'])


def _png_case_indexed(viewer):
    data = solid_data()
    viewer.solid(data['indexed_vertices'], data['indexed_quads'], edgecolor='k', facecolor='cyan')


PNG_CASES = [
    ('cube_faces', _png_case_cube),
    ('indexed_colored', _png_case_indexed),
]


BASELINE_DIR = Path(__file__).parent / 'reference_images' / PNG_BASELINE_SUBDIR
GENERATED_DIR = Path(__file__).parent / 'generated_images' / PNG_BASELINE_SUBDIR


@pytest.mark.parametrize('case_name,run_case', _solid_cases({
    'indexed_vertices': np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ]),
    'indexed_quads': np.array([[0, 1, 2, 3]]),
    'indexed_vertices_2d': np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ]),
    'quad_xyzc': np.array([
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.3],
            [1.0, 1.0, 0.0, 0.6],
            [0.0, 1.0, 0.0, 1.0],
        ]
    ]),
    'cube_faces': np.array([
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]],
    ]),
}), ids=lambda value: value if isinstance(value, str) else None)
def test_solid_variants(piscope_session, case_name, run_case):
    del case_name
    viewer = interactive.figure()
    viewer.threed('on')
    obj = run_case(viewer)
    assert obj is not None
    props = check_prop_read(obj)
    assert isinstance(props, dict)


@pytest.mark.parametrize('case_name,case_func', PNG_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_solid_png_regression_cases(piscope_session, case_name, case_func):
    baseline = BASELINE_DIR / '{}.png'.format(case_name)
    if not baseline.exists():
        pytest.skip('baseline image missing: {}'.format(baseline))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_png = GENERATED_DIR / '{}.png'.format(case_name)
    _render_png_case(case_func, out_png, threed=True)
    _assert_png_created(out_png)
    _assert_png_matches(baseline, out_png, mae_tol=PNG_MAE_TOL, p99_tol=PNG_P99_TOL)
