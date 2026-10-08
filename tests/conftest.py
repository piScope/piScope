from pathlib import Path
import shutil
import sys
import webbrowser

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
    parser.addoption(
        '--compare-png',
        action='store_true',
        default=False,
        help='generate side-by-side PNG comparison HTML at the end of the run and open it in a browser',
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


def pytest_sessionstart(session):
    if not session.config.getoption('--compare-png'):
        return

    generated_root = Path(__file__).resolve().parent / 'generated_images'
    shutil.rmtree(generated_root, ignore_errors=True)
    generated_root.mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption('--compare-png'):
        return

    reporter = session.config.pluginmanager.get_plugin('terminalreporter')
    cwd = Path.cwd()

    try:
        from tests.generate_comparison_html import generate_html

        output_path = generate_html().resolve()
        try:
            display_path = output_path.relative_to(cwd)
        except ValueError:
            display_path = output_path

        opened = False
        try:
            opened = webbrowser.open(output_path.as_uri(), new=2)
        except Exception:
            opened = False

        msg = f'PNG comparison report: {display_path}'
        if opened:
            msg += ' (opened in browser)'
        else:
            msg += ' (browser open unavailable; open the HTML file manually)'

        if reporter is not None:
            reporter.write_line(msg)
        else:
            print(msg)
    except Exception as exc:
        err = f'Failed to generate PNG comparison report: {exc}'
        if reporter is not None:
            reporter.write_line(err, red=True)
        else:
            print(err)