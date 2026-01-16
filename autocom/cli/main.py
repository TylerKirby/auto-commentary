"""
Command-line interface: parse, annotate, render, commentary (end-to-end).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from autocom.processing import analyze as analyze_mod
from autocom.processing import enrich as enrich_mod
from autocom.processing import ingest as ingest_mod
from autocom.processing import layout as layout_mod
from autocom.processing.analyze import get_analyzer_for_language
from autocom.processing.lexicon import get_lexicon_for_language
from autocom.rendering.latex import collect_missing_definitions, render_latex
from autocom.rendering.pdf import render_pdf

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _setup_logging(verbose: bool) -> None:
    """Configure a simple logging sink for CLI progress reporting."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging")) -> None:
    """Shared CLI configuration executed before subcommands."""
    _setup_logging(verbose)


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
    logger = logging.getLogger("autocom.cli.parse")
    logger.info("Detected language: %s", detected)
    logger.info("Lines: %s | Tokens: %s", num_lines, num_tokens)


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
    logger = logging.getLogger("autocom.cli.annotate")
    logger.info("Reading input: %s", input_path)
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)
    logger.info("Detected language: %s", detected_language)

    # Get appropriate analyzer
    if detected_language == "greek":
        logger.info("Initializing Greek analyzer (prefer_cltk=%s)", prefer_cltk)
        analyzer = get_analyzer_for_language("greek", prefer_cltk=prefer_cltk)
        enrichment = None  # Greek enrichment not implemented yet
    else:
        logger.info("Initializing Latin analyzer (prefer_spacy=%s)", prefer_spacy)
        analyzer = get_analyzer_for_language("latin", prefer_spacy=prefer_spacy)
        enrichment = enrich_mod.LatinEnrichment()

    logger.info("Running morphological analysis on %d lines", len(lines))
    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Get appropriate lexicon
    lexicon = get_lexicon_for_language(detected_language)
    logger.info("Applying lexicon enrichment")
    lines = lexicon.enrich(lines)

    # Apply language-specific enrichment
    if enrichment:
        logger.info("Running Latin enrichment layer")
        lines = enrichment.enrich(lines)

    freq = enrich_mod.compute_frequency(lines)
    lines = enrich_mod.mark_first_occurrences(lines)
    doc = layout_mod.build_document(norm, language=detected_language, lines=lines)
    annotated_tokens = sum(len(line.tokens) for line in doc.pages[0].lines)
    logger.info(
        "Completed annotation | Annotated tokens: %s | Unique lemmas: %s",
        annotated_tokens,
        len(freq),
    )


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
    logger = logging.getLogger("autocom.cli.render")
    logger.info("Reading input: %s", input_path)
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)
    logger.info("Detected language: %s", detected_language)

    # Get appropriate analyzer
    analyzer = get_analyzer_for_language(detected_language)
    logger.info("Running morphological analysis on %d lines", len(lines))
    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Compute frequency for Steadman-style annotations
    logger.info("Computing word frequencies")
    freq = enrich_mod.compute_frequency(lines)

    # Compute first occurrence line numbers
    logger.info("Computing first occurrence line numbers")
    first_occurrence_lines = enrich_mod.compute_first_occurrence_lines(lines)

    # Get appropriate lexicon and enrich with frequency data and first occurrence lines
    lexicon = get_lexicon_for_language(detected_language)
    logger.info("Applying lexicon enrichment with frequency data")
    lines = lexicon.enrich(lines, frequency_map=dict(freq), first_occurrence_line_map=first_occurrence_lines)

    # Apply language-specific enrichment (if available)
    if detected_language == "latin":
        logger.info("Running Latin enrichment layer")
        enr = enrich_mod.LatinEnrichment()
        lines = enr.enrich(lines)

    doc = layout_mod.build_document(norm, language=detected_language, lines=lines)
    latex_src = render_latex(doc)
    logger.info("Writing LaTeX output to %s", output_dir / "commentary.tex")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "commentary.tex").write_text(latex_src, encoding="utf-8")

    # Collect and write missing definitions for review
    missing_defs = collect_missing_definitions(doc)
    if missing_defs:
        import json

        errors_path = output_dir / "missing_definitions.json"
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(missing_defs, f, indent=2, ensure_ascii=False)
        logger.warning(
            "Found %d words without definitions - see %s for details",
            len(missing_defs),
            errors_path,
        )

    if pdf:
        logger.info("Rendering PDF via xelatex")
        pdf_path = render_pdf(latex_src, str(output_dir))
        logger.info("PDF generated at %s", pdf_path)


@app.command()
def commentary(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o"),
    pdf: bool = typer.Option(False, "--pdf/--no-pdf"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Force language (latin/greek)"),
    title: Optional[str] = typer.Option(None, "--title", help="Commentary title"),
    paper_size: str = typer.Option(
        "letter",
        "--paper-size",
        "-p",
        help="Paper size for pagination (letter, a4, a5)",
    ),
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
    api_fallbacks: bool = typer.Option(
        True,
        "--api-fallbacks/--no-api-fallbacks",
        help="Enable API fallbacks for dictionary lookups (slower but more complete)",
    ),
) -> None:
    logger = logging.getLogger("autocom.cli.commentary")
    logger.info("Reading input: %s", input_path)
    text = input_path.read_text(encoding="utf-8")
    norm, lines = ingest_mod.normalize_and_segment(text)

    # Auto-detect language if not specified
    detected_language = language or ingest_mod.detect_language(norm)
    logger.info("Detected language: %s", detected_language)

    # Get appropriate analyzer
    if detected_language == "greek":
        logger.info("Initializing Greek analyzer (prefer_cltk=%s)", prefer_cltk)
        analyzer = get_analyzer_for_language("greek", prefer_cltk=prefer_cltk)
    else:
        logger.info("Initializing Latin analyzer (prefer_spacy=%s)", prefer_spacy)
        analyzer = get_analyzer_for_language("latin", prefer_spacy=prefer_spacy)

    logger.info("Running morphological analysis on %d lines", len(lines))
    lines = analyzer.analyze(lines)
    lines = analyze_mod.disambiguate_sequence(lines)

    # Compute frequency for Steadman-style annotations
    logger.info("Computing word frequencies")
    freq = enrich_mod.compute_frequency(lines)

    # Compute first occurrence line numbers
    logger.info("Computing first occurrence line numbers")
    first_occurrence_lines = enrich_mod.compute_first_occurrence_lines(lines)

    # Get appropriate lexicon and enrich with frequency data and first occurrence lines
    lexicon = get_lexicon_for_language(detected_language, enable_api_fallbacks=api_fallbacks)
    logger.info("Applying lexicon enrichment with frequency data (api_fallbacks=%s)", api_fallbacks)
    lines = lexicon.enrich(lines, frequency_map=dict(freq), first_occurrence_line_map=first_occurrence_lines)

    # Apply language-specific enrichment (if available)
    if detected_language == "latin":
        logger.info("Running Latin enrichment layer")
        enr = enrich_mod.LatinEnrichment()
        lines = enr.enrich(lines)

    logger.info("Marking first occurrences for frequency annotations")
    lines = enrich_mod.mark_first_occurrences(lines)

    # Extract core vocabulary (words appearing 15+ times) for Steadman-style front matter
    logger.info("Extracting core vocabulary (15+ occurrences)")
    core_vocab_tokens, core_vocab_lemmas = enrich_mod.extract_core_vocabulary_tokens(lines, frequency_threshold=15)
    logger.info("Found %d core vocabulary words", len(core_vocab_tokens))

    logger.info("Building document with paper size: %s", paper_size)
    doc = layout_mod.build_document(norm, language=detected_language, lines=lines, paper_size=paper_size)

    # Add core vocabulary to document
    doc.core_vocabulary = core_vocab_tokens
    doc.metadata["core_vocab_lemmas"] = core_vocab_lemmas

    # Add title to document metadata if provided
    if title:
        logger.info("Setting document title: %s", title)
        doc.metadata["title"] = title

    latex_src = render_latex(doc)
    logger.info("Writing LaTeX output to %s", output_dir / "commentary.tex")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "commentary.tex").write_text(latex_src, encoding="utf-8")

    # Collect and write missing definitions for review
    missing_defs = collect_missing_definitions(doc)
    if missing_defs:
        import json

        errors_path = output_dir / "missing_definitions.json"
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(missing_defs, f, indent=2, ensure_ascii=False)
        logger.warning(
            "Found %d words without definitions - see %s for details",
            len(missing_defs),
            errors_path,
        )

    if pdf:
        logger.info("Rendering PDF via xelatex")
        pdf_path = render_pdf(latex_src, str(output_dir))
        logger.info("PDF generated at %s", pdf_path)


def run() -> None:  # entry point for module execution
    app()


if __name__ == "__main__":
    run()
