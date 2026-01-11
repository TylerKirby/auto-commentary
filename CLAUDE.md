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
pytest tests/languages/latin/test_cache.py  # Run specific test file
pytest -m "not slow"  # Skip slow tests
pytest -m "not whitakers"  # Skip tests requiring whitakers_words
pytest -m "not cltk"  # Skip tests requiring CLTK
```

### Code Quality
Format and lint code:
```bash
ruff format --line-length=120 autocom/ tests/  # Format code
ruff check autocom/ tests/  # Lint code
isort --line-length=120 --profile=black autocom/ tests/  # Sort imports
mypy --ignore-missing-imports --follow-imports=skip autocom/  # Type checking (optional)
```

### Running the Application
The CLI provides four main commands:
```bash
python -m autocom.cli.main parse examples/sample_latin_excerpt.txt  # Parse and analyze text
python -m autocom.cli.main annotate examples/sample_latin_excerpt.txt  # Full annotation pipeline
python -m autocom.cli.main render examples/sample_latin_excerpt.txt --pdf  # Generate LaTeX/PDF
python -m autocom.cli.main commentary examples/sample_latin_excerpt.txt --pdf  # Full commentary generation
```

## Project Architecture

### Core Pipeline
The application follows a deterministic pipeline architecture:

1. **Ingestion** (`autocom/pipeline/ingest.py`): Text normalization, language detection, tokenization
2. **Analysis** (`autocom/pipeline/analyze.py`): Morphological analysis using CLTK, spaCy, or Morpheus
3. **Enrichment** (`autocom/pipeline/enrich.py`): Glossing and frequency analysis
4. **Layout** (`autocom/pipeline/layout.py`): Document structure and pagination
5. **Rendering** (`autocom/rendering/`): LaTeX and PDF generation via XeLaTeX

### Domain Models
Core data structures defined in `autocom/core/models.py`:
- `Token`: Text token with optional morphological analysis and gloss
- `Line`: Collection of tokens representing a line of text
- `Page`: Collection of lines for pagination
- `Document`: Full document with metadata and language info
- `Analysis`: Morphological analysis (lemma, POS tags)
- `Gloss`: Dictionary definitions for lemmas (headword, genitive, gender, pos_abbrev, principal_parts, senses)

### Latin Processing
The `LatinAnalyzer` in `autocom/pipeline/analyze.py` supports multiple backends:
- **spaCy-UDPipe**: Preferred when available (models: perseus, proiel, ittb)
- **CLTK**: Fallback lemmatizer and NLP tools
- **Morpheus**: Public API for morphological analysis at morph.perseids.org

### Lexicon and Enrichment
- `autocom/languages/latin/lexicon.py`: Dictionary lookup with Whitaker's Words (primary) and Lewis & Short (fallback)
- `autocom/languages/latin/cache.py`: SQLite-based persistent cache for dictionary lookups
- `autocom/pipeline/enrich.py`: Frequency tracking and first-occurrence marking

### Dictionary Cache
The `DictionaryCache` class provides persistent SQLite caching for dictionary lookups:
- **Location**: `.dictionary_cache/dictionary_cache.db`
- **Whitaker's Words**: Cached permanently (no TTL - dictionary is static)
- **API lookups**: Cached with 30-day TTL
- **Performance**: ~7.5x speedup for cached lookups, 90% hit rate on typical texts
- **Usage**: Enabled by default in `LatinLexicon`, disable with `enable_cache=False`
- **Stats**: Call `lexicon.get_cache_stats()` to see hit/miss rates

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
Requires XeLaTeX (for native Unicode/Greek character support) with packages:
- fontspec (font selection with Unicode)
- multicol, geometry, fancyhdr, xcolor

The rendering pipeline uses `xelatex` instead of `pdflatex` to handle Greek characters
that appear in Lewis & Short definitions.

## Development Notes

- The project generates automated commentaries for Latin/Greek texts
- Output format is PDF with original text and word definitions
- All analysis is deterministic and cacheable
- Supports enclitic stripping (que, ne, ve)
- Maintains capitalization in lemmas for proper nouns
- Extensible backend system for morphological analysis