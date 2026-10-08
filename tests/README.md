# Test Suite Notes

This directory contains the plotting regression tests for piScope.

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

- Full run + generate/open PNG comparison report:

  ```bash
  python -m pytest --compare-png
  ```
  This runs the full test suite, cleans `tests/generated_images`, generates
  the side-by-side visual comparison HTML report, and tries to open it in the
  system default web browser.
  
- Test specific plot command:

  ```bash
  python -m pytest tests/test_z01_plot.py
  ```  

## PNG Reference Generation

```bash
python tests/generate_reference_png.py
```
This script generates or updates baseline PNGs for all command modules that
enable PNG visual metadata.

Notes:

- Current reference PNGs were generated using Matplotlib 3.10.9.
- The generator cleans `tests/reference_images` first, then rebuilds all
  reference PNGs and metadata.

## Side-By-Side Visual Report Generation

```bash
python tests/generate_comparison_html.py
```

The output file is:

- `tests/generated_images/reference_vs_generated.html`

## More information to Developer/LLM

For plotting test authoring conventions, see:

- `dev_notes/instruction_to_add_test.md`

