"""Generate a side-by-side HTML comparison of reference and generated PNG files.

Usage:
    python tests/generate_comparison_html.py
"""

from __future__ import annotations

import os
from pathlib import Path
from html import escape


def collect_relative_png_paths(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {
        p.relative_to(root)
        for p in root.rglob("*.png")
        if p.is_file()
    }


def to_posix(path: Path) -> str:
    return path.as_posix()


def rel_url(from_dir: Path, to_path: Path) -> str:
    return to_posix(Path(os.path.relpath(to_path, from_dir)))


def image_cell(img_path: str | None, alt: str) -> str:
    if img_path is None:
        return '<div class="missing">(missing)</div>'
    return (
        '<a href="{src}" target="_blank" rel="noopener">'
        '<img src="{src}" alt="{alt}"></a>'
    ).format(src=escape(img_path), alt=escape(alt))


def build_row(rel_path: Path, output_dir: Path, ref_root: Path, gen_root: Path) -> str:
    ref_abs = ref_root / rel_path
    gen_abs = gen_root / rel_path

    ref_src = None
    gen_src = None
    status = []

    if ref_abs.exists():
        ref_src = rel_url(output_dir, ref_abs)
    else:
        status.append("missing reference")

    if gen_abs.exists():
        gen_src = rel_url(output_dir, gen_abs)
    else:
        status.append("missing generated")

    status_txt = ", ".join(status) if status else "ok"

    return "".join([
        "<tr>",
        "<td><code>{}</code></td>".format(escape(to_posix(rel_path))),
        "<td>{}</td>".format(image_cell(ref_src, f"reference {rel_path}")),
        "<td>{}</td>".format(image_cell(gen_src, f"generated {rel_path}")),
        "<td>{}</td>".format(escape(status_txt)),
        "</tr>",
    ])


def generate_html() -> Path:
    tests_dir = Path(__file__).resolve().parent
    ref_root = tests_dir / "reference_images"
    gen_root = tests_dir / "generated_images"

    output_dir = gen_root
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "reference_vs_generated.html"

    rel_paths = sorted(collect_relative_png_paths(ref_root) | collect_relative_png_paths(gen_root))

    rows = [build_row(rel_path, output_dir, ref_root, gen_root) for rel_path in rel_paths]

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reference vs Generated PNG Comparison</title>
  <style>
    body {{ font-family: sans-serif; margin: 16px; }}
    h1 {{ margin: 0 0 8px 0; }}
    p {{ margin: 0 0 16px 0; color: #444; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f4f4f4; text-align: left; }}
    td:nth-child(2), td:nth-child(3) {{ width: 36%; }}
    img {{ width: 100%; height: auto; display: block; background: #fff; }}
    .missing {{ color: #a00; font-style: italic; }}
    code {{ font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Reference vs Generated PNG Comparison</h1>
  <p>Rows: {row_count}. Click an image to open full size.</p>
  <table>
    <thead>
      <tr>
        <th>File</th>
        <th>Reference</th>
        <th>Generated</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
""".format(row_count=len(rel_paths), rows="\n".join(rows))

    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    output_path = generate_html()
    print("wrote", output_path)


if __name__ == "__main__":
    main()
