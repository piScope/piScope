'''
Focused tests for the interactive solid command.
'''

import numpy as np

import ifigure.interactive as interactive
import pytest

from tests.test_utils import check_prop_read, piscope_session


pytestmark = [pytest.mark.full]


@pytest.fixture
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