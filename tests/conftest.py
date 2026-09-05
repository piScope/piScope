from pathlib import Path
import sys

import pytest


# Ensure tests exercise local workspace code instead of an installed package.
PROJECT_PYTHON = Path(__file__).resolve().parent.parent / 'python'
PROJECT_PYTHON_STR = str(PROJECT_PYTHON)
if PROJECT_PYTHON_STR not in sys.path:
    sys.path.insert(0, PROJECT_PYTHON_STR)


def pytest_addoption(parser):
    parser.addoption(
        '--quick',
        action='store_true',
        default=False,
        help='run only the quick plotting regression suite',
    )


def pytest_collection_modifyitems(config, items):
    items.sort(
        key=lambda item: (
            1 if item.fspath.basename.startswith('test_zz') else 0,
            item.fspath.basename,
            item.nodeid,
        )
    )

    if not config.getoption('--quick'):
        return

    skip_non_quick = pytest.mark.skip(
        reason='non-quick test skipped by --quick selection'
    )
    for item in items:
        if 'quick' not in item.keywords:
            item.add_marker(skip_non_quick)