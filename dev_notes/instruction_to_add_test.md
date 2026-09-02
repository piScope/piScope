# Instructions For Adding Plot Command Tests

Use this document when adding or updating plotting tests in this repository.

## Test Modes

- Default `pytest` run executes the full plotting suite.
- `pytest --quick` runs only quick-marked tests.

## File Roles

- `tests/test_plot_commands.py`

  Aggregate plotting regression test (quick suite). It should remain shallow and check:

  - plotting command inventory
  - plotting command presence
  - one valid call per plotting command
  - a basic property read/write round-trip

- `tests/test_zNN_<command>.py`

  Dedicated per-command test modules (full suite). They should cover:

  - alternate argument forms
  - command-specific keyword options
  - command-specific property behavior

The `zNN` prefix keeps dedicated command tests ordered after `test_plot_commands.py`.

## Shared Test Support

Shared helpers live in `tests/test_utils.py`.

Current shared routines:

- `piscope_session`: launches and shuts down a piScope session for a test module
- `check_prop_read`: reads all editable properties for a plotted object
- `check_prop_write`: writes back a saved property set

## Procedure For New Command Tests

1. Create `tests/test_zNN_<command>.py`.
2. Mark the module with `pytest.mark.full`.
3. Reuse helpers from `tests/test_utils.py`.
4. Keep `tests/test_plot_commands.py` shallow.