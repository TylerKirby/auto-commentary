"""
PDF rendering: run pdflatex on generated LaTeX and manage artifacts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def render_pdf(
    latex_source: str,
    output_dir: str,
    jobname: str = "commentary",
) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    tex_path = out_path / f"{jobname}.tex"
    pdf_path = out_path / f"{jobname}.pdf"
    tex_path.write_text(latex_source, encoding="utf-8")
    try:
        subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                tex_path.name,
            ],
            cwd=str(out_path),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(f"pdflatex failed: {exc}")
    if not pdf_path.exists():
        raise RuntimeError("pdflatex reported success but no PDF was produced")
    return pdf_path
