# Coding Style Guide
This guide reflects the stable pre-2026-08-19 style in piScope and Petra-M.

## General Rules

- Match the surrounding file first. Preserve local conventions instead of normalizing the whole codebase.
- Prefer small, direct changes over broad refactors.
- Keep public APIs and behavior stable unless the task explicitly asks for a change.
- Reuse existing project helpers, especially for GUI, debug, and model code.

## File And Import Style

- Group imports as standard library, third-party, then local project imports.
- Keep imports explicit and readable; do not add new wildcard imports.
- Use short aliases for heavily used project modules when that is already the local convention, for example `import ifigure.utils.cbook as cbook` or `import petram.debug as debug`.
- Prefer local imports in optional code paths when a dependency is expensive or optional.

## Naming Conventions

- Use `snake_case` for functions, methods, variables, and module-level helpers.
- Use `CamelCase` for classes.
- Use `UPPER_CASE` for constants and GUI IDs.
- Keep helper names consistent with the existing pattern, such as `get_*`, `set_*`, `load_*`, `run_*`, `on*`, and `is*`.
- Use the project’s existing class identity helpers when relevant, such as `isFigObj`, `isPyCode`, or `load_classimage`.

## Classes And State

- Initialize object state in `__init__` and keep internal attributes on `self._...`.
- Prefer straightforward data containers and light helper classes over deep inheritance.
- Use properties for exposed state when the surrounding class already does so.
- Keep classmethod helpers simple and declarative when they describe the class rather than an instance.

## Functions And Methods

- Keep functions short, direct, and easy to scan.
- Preserve existing signatures, including legacy names such as `*args`, `**kargs`, or `**kywds` when they are already used in the file.
- Use early returns when that makes control flow simpler.
- Prefer local, readable logic over generalized utility wrappers.
- Keep one-off compatibility code close to the call site.

## Formatting

- Use 4-space indentation.
- Separate top-level definitions with blank lines.
- Keep wrapped arguments and lists aligned in the style already used by the file.
- Avoid large reformatting-only edits.
- Keep line comments short and practical.

## Documentation And Comments

- Module headers often include a short summary, history, and copyright note.
- Use short docstrings to explain purpose, inputs, or special behavior when needed.
- Prefer comments that explain why the code is shaped a certain way, not what each line does.
- Do not over-clean legacy spelling or wording unless you are already editing that area.

## GUI And Menu Code

- Follow the existing wx/menu builder style: list-of-tuples, separator sentinels such as `!` and `---`, and helpers like `BuildMenu` or `add_menu`.
- Keep event handlers and UI callbacks direct.
- Use the project’s existing debug-print helpers and UI helper modules instead of introducing new frameworks.

## Error Handling And Optional Dependencies

- Use simple `try`/`except` blocks where the code is guarding optional GUI features, optional dependencies, or fallback behavior.
- Keep exception handling local and explicit when possible.
- Do not broaden error handling unless it matches the existing surrounding pattern.

## Tests

- Follow the existing split between the shallow aggregate plotting test and the per-command `test_zNN_*.py` modules.
- Reuse shared helpers from `tests/test_utils.py`.
- Keep quick tests shallow and full tests command-specific.

## Do Not Introduce By Default

- New type hints across untouched legacy modules.
- Dataclasses, pathlib, or other modern abstractions unless the surrounding file already uses them.
- Large helper layers that replace straightforward local code.
- Mass formatting or unrelated cleanup.

## Practical Rule

- When in doubt, copy the style of the nearest older file in the same subsystem, not the newest edit.