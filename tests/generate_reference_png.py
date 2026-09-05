"""
Generate baseline PNGs for all command test modules that declare PNG metadata.

Usage:
    python tests/generate_reference_png.py

Behavior:
    This script deletes tests/reference_images before writing new reference files.
"""

from pathlib import Path
import shutil
import sys

# Prefer local workspace source over site-packages.
_TESTS_DIR = Path(__file__).resolve().parent
_PROJECT_PYTHON = _TESTS_DIR.parent / 'python'
_PROJECT_PYTHON_STR = str(_PROJECT_PYTHON)
if _PROJECT_PYTHON_STR not in sys.path:
    sys.path.insert(0, _PROJECT_PYTHON_STR)

import matplotlib
import ifigure.interactive as interactive

try:
    from tests.test_utils import _collect_png_case_specs, _iter_command_test_modules, _render_png_case
except ModuleNotFoundError:
    from test_utils import _collect_png_case_specs, _iter_command_test_modules, _render_png_case


def main():
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent
    baseline_root = tests_dir / 'reference_images'

    if baseline_root.exists():
        shutil.rmtree(baseline_root)
    baseline_root.mkdir(parents=True, exist_ok=True)

    log_path = baseline_root / 'generate_reference_png.log'

    def display_path(value):
        if value is None:
            return 'unknown'
        p = Path(str(value))
        if p.is_absolute():
            try:
                return str(p.relative_to(project_root))
            except ValueError:
                return p.name
        return str(p)

    def log(*parts):
        message = ' '.join(str(p) for p in parts)
        print(message)
        with log_path.open('a', encoding='utf-8') as f:
            f.write(message + '\n')

    # Start a fresh log for each generation run.
    log_path.write_text('', encoding='utf-8')

    log('matplotlib', matplotlib.__version__)
    log('tests_dir', display_path(tests_dir))
    log('project_root', display_path(project_root))
    log('project_python', display_path(_PROJECT_PYTHON))
    log('ifigure_module', display_path(getattr(sys.modules.get('ifigure'), '__file__', None)))

    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    log('project_root_in_syspath', project_root_str in sys.path)

    specs = []
    for module in _iter_command_test_modules(tests_dir):
        specs.extend(_collect_png_case_specs(module))

    log('png_case_count', len(specs))

    if not specs:
        log('No PNG metadata found in test_z*/test_zz* modules.')
        return

    interactive.launch()
    try:
        for spec in specs:
            out_dir = baseline_root / spec['subdir']
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / '{}.png'.format(spec['case_name'])
            _render_png_case(spec['case_func'], out_path, threed=spec['threed'])
            log('wrote', display_path(out_path))
    finally:
        interactive.shutdown()


if __name__ == '__main__':
    main()
