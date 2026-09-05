# Instructions For Adding Plot Command Tests

Use this document when adding or updating plotting tests in this repository.

## Test Modes

- Default `pytest` run executes the full plotting suite.
- `pytest --quick` runs only quick-marked tests.
- `pytest --compare-png` runs the full suite, cleans `tests/generated_images`,
  generates a side-by-side PNG comparison HTML report, and tries to open it in
  the system default browser.

## File Roles

- `tests/test_plot_commands.py`

  Aggregate plotting regression test (quick suite). It should remain shallow and check:

  - plotting command inventory
  - plotting command presence
  - one valid call per plotting command
  - a basic property read/write round-trip

- `tests/test_zNN_<command>.py`

  Dedicated per-command 2D test modules (full suite).

- `tests/test_zzNN_<command>.py`

  Dedicated per-command 3D test modules (full suite). 2D modules run before 3D
  modules during collection. Per-command modules should cover:

  - alternate argument forms
  - command-specific keyword options
  - command-specific property behavior
  - optional PNG visual regression coverage

The `zNN` and `zzNN` prefixes keep dedicated command tests ordered after
`test_plot_commands.py`.

## Shared Test Support

Shared helpers live in `tests/test_utils.py`.

Current shared routines:

- `piscope_session`: launches and shuts down a piScope session for a test module
- `check_prop_read`: reads all editable properties for a plotted object
- `check_prop_write`: writes back a saved property set
- `_render_png_case`: renders one PNG case using a case callback
- `_assert_png_created`: validates that an output PNG exists and is non-uniform
- `_assert_png_matches`: compares generated PNG vs reference PNG with tolerance
- `_iter_command_test_modules` and `_collect_png_case_specs`: module metadata
  discovery used by reference generation

## PNG Visual Metadata (Per Command Module)

Command modules can opt into PNG visual regression by defining:

- `PLOT_COMMAND`
- `ENABLE_PNG_VISUAL`
- `PNG_CASES`
- optional `PNG_BASELINE_SUBDIR`, `PNG_THREED`, `PNG_MAE_TOL`, `PNG_P99_TOL`

Reference PNGs are stored under `tests/reference_images/<subdir>/`.
Generated PNGs are stored under `tests/generated_images/<subdir>/`.

Regenerate references with:

- `python tests/generate_reference_png.py`

Generate side-by-side report manually with:

- `python tests/generate_comparison_html.py`

## Procedure For New Command Tests

1. Create `tests/test_zNN_<command>.py`.
2. For 3D commands, create `tests/test_zzNN_<command>.py`.
3. Mark the module with `pytest.mark.full`.
4. Import shared helpers from `tests/test_utils.py`.
5. Add command variants and property-read checks.
6. If visual regression is needed, define PNG metadata and `PNG_CASES`.
7. Keep `tests/test_plot_commands.py` shallow.

## Practical Checks

1. Run command module only while authoring.
2. Run `pytest --quick` for a fast guardrail pass.
3. Run full `pytest` before merging.
4. When PNG cases change intentionally, regenerate reference images and review
   the comparison HTML report.