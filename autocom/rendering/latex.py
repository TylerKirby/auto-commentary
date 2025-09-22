"""
LaTeX rendering for Steadman-style layout using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from autocom.core.models import Document


def _latex_escape(value: str) -> str:
    """Escape LaTeX special characters in user-provided content."""
    if value is None:
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "%": r"\%",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = []
    for char in str(value):
        escaped.append(replacements.get(char, char))
    return "".join(escaped)


def _env(template_dir: Optional[str] = None) -> Environment:
    dir_path = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(dir_path)),
        autoescape=select_autoescape([]),
    )
    env.filters["latex_escape"] = _latex_escape
    return env


def render_latex(
    document: Document,
    template_name: str = "steadman.tex.j2",
    template_dir: Optional[str] = None,
) -> str:
    env = _env(template_dir)
    template = env.get_template(template_name)
    return template.render(doc=document)
