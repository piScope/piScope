# Test Suite Notes

This directory contains the plotting regression tests for piScope.

## Test Modes

By default, `pytest` runs the full plotting test set.

- Full run:

  ```bash
  python -m pytest -q
  ```

- Quick run:

  ```bash
  python -m pytest -q --quick
  ```

- Test specific plot command:

  ```bash
  python -m pytest -q tests/test_z01_plot.py
  ```  

## Developer/LLM Test Conventions

For plotting test authoring conventions, see:

- `dev_notes/instruction_to_add_test.md`