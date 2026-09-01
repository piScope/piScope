import pytest


def pytest_addoption(parser):
    parser.addoption(
        '--quick',
        action='store_true',
        default=False,
        help='run only the quick plotting regression suite',
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--quick'):
        return

    skip_non_quick = pytest.mark.skip(
        reason='non-quick test skipped by --quick selection'
    )
    for item in items:
        if 'quick' not in item.keywords:
            item.add_marker(skip_non_quick)