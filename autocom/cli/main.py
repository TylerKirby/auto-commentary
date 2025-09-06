"""
Command-line interface: parse, annotate, render, commentary (end-to-end).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from autocom.processing import analyze as analyze_mod
from autocom.processing import enrich as enrich_mod
from autocom.processing import ingest as ingest_mod
from autocom.processing import layout as layout_mod
from autocom.processing.analyze import get_analyzer_for_language
from autocom.processing.lexicon import get_lexicon_for_language
from autocom.rendering.latex import render_latex
from autocom.rendering.pdf import render_pdf

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def parse(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    language: Optional[str] = typer.Option(None, "--language", "-l"),
) -> None:
    text = input_path.read_text(encoding="utf-8")
    norm = ingest_mod.normalize_text(text)
    detected = ingest_mod.detect_language(norm) if language is None else language
    lines = ingest_mod.segment_lines(norm)
    num_lines = len(lines)
    num_tokens = sum(len(line.tokens) for line in lines)
    msg = f"Language: {detected}; Lines: {num_lines}; Tokens: {num_tokens}"
    typer.echo(msg)


@app.command()
def annotate(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Force language (latin/greek)"),
    prefer_spacy: bool = typer.Option(
        True,
        "--prefer-spacy/--no-prefer-spacy",
        help="Prefer spaCy for Latin analysis",
    ),
    prefer_cltk: bool = typer.Option(
        True,
        "--prefer-cltk/--no-prefer-cltk",
        help="Prefer CLTK for Greek analysis",
    ),
) -> None:
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)

    # Get appropriate analyzer
    if detected_language == "greek":
        analyzer = get_analyzer_for_language("greek", prefer_cltk=prefer_cltk)
        enrichment = None  # Greek enrichment not implemented yet
    else:
        analyzer = get_analyzer_for_language("latin", prefer_spacy=prefer_spacy)
        enrichment = enrich_mod.LatinEnrichment()

    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Get appropriate lexicon
    lexicon = get_lexicon_for_language(detected_language)
    lines = lexicon.enrich(lines)

    # Apply language-specific enrichment
    if enrichment:
        lines = enrichment.enrich(lines)

    freq = enrich_mod.compute_frequency(lines)
    lines = enrich_mod.mark_first_occurrences(lines)
    doc = layout_mod.build_document(norm, language=detected_language, lines=lines)
    annotated_tokens = sum(len(line.tokens) for line in doc.pages[0].lines)
    summary = f"Language: {detected_language}; Annotated tokens: {annotated_tokens}; Unique lemmas: {len(freq)}"
    typer.echo(summary)


@app.command()
def render(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output",
        "-o",
    ),
    pdf: bool = typer.Option(False, "--pdf/--no-pdf"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Force language (latin/greek)"),
) -> None:
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)

    # Get appropriate analyzer
    analyzer = get_analyzer_for_language(detected_language)
    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Get appropriate lexicon
    lexicon = get_lexicon_for_language(detected_language)
    lines = lexicon.enrich(lines)

    # Apply language-specific enrichment (if available)
    if detected_language == "latin":
        enr = enrich_mod.LatinEnrichment()
        lines = enr.enrich(lines)

    doc = layout_mod.build_document(norm, language=detected_language, lines=lines)
    latex_src = render_latex(doc)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "commentary.tex").write_text(latex_src, encoding="utf-8")
    if pdf:
        pdf_path = render_pdf(latex_src, str(output_dir))
        typer.echo(str(pdf_path))


@app.command()
def commentary(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o"),
    pdf: bool = typer.Option(False, "--pdf/--no-pdf"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Force language (latin/greek)"),
    title: Optional[str] = typer.Option(None, "--title", help="Commentary title"),
    prefer_spacy: bool = typer.Option(
        True,
        "--prefer-spacy/--no-prefer-spacy",
        help="Prefer spaCy for Latin analysis",
    ),
    prefer_cltk: bool = typer.Option(
        True,
        "--prefer-cltk/--no-prefer-cltk",
        help="Prefer CLTK for Greek analysis",
    ),
) -> None:
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)

    # Get appropriate analyzer
    if detected_language == "greek":
        analyzer = get_analyzer_for_language("greek", prefer_cltk=prefer_cltk)
    else:
        analyzer = get_analyzer_for_language("latin", prefer_spacy=prefer_spacy)

    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Get appropriate lexicon
    lexicon = get_lexicon_for_language(detected_language)
    lines = lexicon.enrich(lines)

    # Apply language-specific enrichment (if available)
    if detected_language == "latin":
        enr = enrich_mod.LatinEnrichment()
        lines = enr.enrich(lines)

    lines = enrich_mod.mark_first_occurrences(lines)
    doc = layout_mod.build_document(norm, language=detected_language, lines=lines)

    # Add title to document metadata if provided
    if title:
        doc.metadata["title"] = title

    latex_src = render_latex(doc)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "commentary.tex").write_text(latex_src, encoding="utf-8")
    if pdf:
        pdf_path = render_pdf(latex_src, str(output_dir))
        typer.echo(str(pdf_path))


def run() -> None:  # entry point for module execution
    app()


if __name__ == "__main__":
    run()