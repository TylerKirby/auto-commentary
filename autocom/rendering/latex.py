"""
LaTeX rendering for Steadman-style layout using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from autocom.core.models import Document


def _env(template_dir: Optional[str] = None) -> Environment:
    dir_path = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(dir_path)),
        autoescape=select_autoescape([]),
    )


def render_latex(
    document: Document,
    template_name: str = "steadman.tex.j2",
    template_dir: Optional[str] = None,
) -> str:
    env = _env(template_dir)
    template = env.get_template(template_name)
    return template.render(doc=document)
