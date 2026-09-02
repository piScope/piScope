'''
Focused tests for the interactive plot command.
'''

import numpy as np

import ifigure.interactive as interactive
import pytest

from tests.test_utils import check_prop_read, piscope_session


pytestmark = [pytest.mark.full]


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
