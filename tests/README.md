# Test Suite Notes

This directory contains the plotting regression tests for piScope.

## Command Module Rule

Each command-focused test module follows this naming and ownership rule:

- `test_z*.py` tests one 2D command.
- `test_zz*.py` tests one 3D command.
- One module should focus on one command, while covering multiple argument/style variants.

Command modules can optionally define PNG visual regression metadata:

- `PLOT_COMMAND`
- `ENABLE_PNG_VISUAL`
- `PNG_CASES`
- optional `PNG_BASELINE_SUBDIR`, `PNG_THREED`, `PNG_MAE_TOL`, `PNG_P99_TOL`

## Test Modes

By default, `pytest` runs the full plotting test set.

- Full run:

  ```bash
  python -m pytest
  ```

- Quick run:

  ```bash
  python -m pytest --quick
  ```

- Test specific plot command:

  ```bash
  python -m pytest tests/test_z01_plot.py
  ```  

## Developer/LLM Test Conventions

For plotting test authoring conventions, see:

- `dev_notes/instruction_to_add_test.md`

## PNG Baseline Generation

Use one unified script to generate/update baseline PNGs for all command modules
that enable PNG visual metadata:

```bash
python tests/generate_reference_png.py
```

The generator cleans `tests/reference_images` first, then rebuilds all reference
PNGs from command-module metadata.