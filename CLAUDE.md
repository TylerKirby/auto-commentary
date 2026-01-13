# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Virtual Environment
Always use the virtual environment in `venv/`:
```bash
source venv/bin/activate
```

### Testing
Run tests with pytest:
```bash
pytest  # Run all tests
pytest tests/agents/latin/test_parsing.py  # Run specific test file
pytest -m "not slow"  # Skip slow tests
pytest -m "not whitakers"  # Skip tests requiring whitakers_words
pytest -m "not cltk"  # Skip tests requiring CLTK
```

### Code Quality
Format and lint code:
```bash
ruff format --line-length=120 src/ tests/  # Format code
ruff check src/ tests/  # Lint code
isort --line-length=120 --profile=black src/ tests/  # Sort imports
mypy --ignore-missing-imports --follow-imports=skip src/  # Type checking (optional)
```

### Running the Application
The CLI provides four main commands:
```bash
python -m src.cli.main parse examples/sample_latin_excerpt.txt  # Parse and analyze text
python -m src.cli.main annotate examples/sample_latin_excerpt.txt  # Full annotation pipeline
python -m src.cli.main render examples/sample_latin_excerpt.txt --pdf  # Generate LaTeX/PDF
python -m src.cli.main commentary examples/sample_latin_excerpt.txt --pdf  # Full commentary generation
```

## Project Architecture

### Core Pipeline
The application follows a deterministic pipeline architecture:

1. **Ingestion** (`src/pipeline/ingest.py`): Text normalization, language detection, tokenization
2. **Analysis** (`src/pipeline/analyze.py`): Morphological analysis using CLTK, spaCy, or Morpheus
3. **Enrichment** (`src/pipeline/enrich.py`): Glossing and frequency analysis
4. **Layout** (`src/pipeline/layout.py`): Document structure and pagination
5. **Rendering** (`src/renderers/`): LaTeX and PDF generation

### Domain Models
Core data structures defined in `src/domain/models.py`:
- `Token`: Text token with optional morphological analysis and gloss
- `Line`: Collection of tokens representing a line of text
- `Page`: Collection of lines for pagination
- `Document`: Full document with metadata and language info
- `Analysis`: Morphological analysis (lemma, POS tags)
- `Gloss`: Dictionary definitions for lemmas

### Latin Processing
The `LatinAnalyzer` in `src/pipeline/analyze.py` supports multiple backends:
- **spaCy-UDPipe**: Preferred when available (models: perseus, proiel, ittb)
- **CLTK**: Fallback lemmatizer and NLP tools
- **Morpheus**: Public API for morphological analysis at morph.perseids.org

### Lexicon and Enrichment
- `src/pipeline/lexicon.py`: Dictionary lookup and glossing
- `src/pipeline/enrich.py`: Frequency tracking and first-occurrence marking

## Configuration

### Code Style
- Line length: 120 characters
- Use ruff formatter with black profile
- Import order: system libraries → third party → local imports
- Type hints required for all function parameters and returns

### Testing Markers
- `slow`: Long-running tests
- `integration`: Tests with external services
- `whitakers`: Tests requiring whitakers_words package
- `cltk`: Tests requiring CLTK package

### LaTeX Dependencies
Requires LaTeX with: inputenc, fontenc, multicol, geometry, fancyhdr, xcolor, graphicx

## Development Notes

- The project generates automated commentaries for Latin/Greek texts
- Output format is PDF with original text and word definitions
- All analysis is deterministic and cacheable
- Supports enclitic stripping (que, ne, ve)
- Maintains capitalization in lemmas for proper nouns
- Extensible backend system for morphological analysis