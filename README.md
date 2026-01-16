# Auto-Commentary

A tool to automatically generate commentaries for Latin and Greek texts. The tool produces nicely formatted PDF files with the original text and word definitions in the style of Geoffrey Steadman's Greek and Latin readers.

## Features

- Automatic language detection (Latin/Greek)
- Multiple dictionary sources for definitions:
  - **Latin**: Whitaker's Words (primary), Lewis & Short (fallback), Latin WordNet API
  - **Greek**: LSJ, Morpheus API, CLTK
- Morphological analysis with multiple backends (spaCy-UDPipe, CLTK, Morpheus API)
- Steadman-style glossary formatting (headword with endings, principal parts for verbs)
- Frequency tracking with first-occurrence marking
- SQLite-based caching for fast repeated lookups
- Beautifully formatted PDF output with XeLaTeX
- Customizable lines per page

## Requirements

- Python 3.11+
- XeLaTeX (for native Unicode/Greek character support)
- Required LaTeX packages: fontspec, multicol, geometry, fancyhdr, xcolor

### Optional Dependencies

- `whitakers_words`: Python wrapper for Whitaker's Words parser
- `cltk`: Classical Language Toolkit for additional NLP features
- `spacy` with UDPipe models for Latin/Greek

## Installation

```bash
# Clone the repository
git clone https://github.com/TylerKirby/auto-commentary.git
cd auto-commentary

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

The easiest way to generate a commentary:

```bash
./generate_commentary.sh examples/sample_latin_excerpt.txt
```

This will:
1. Process the text and detect the language
2. Perform morphological analysis
3. Look up definitions from dictionary sources
4. Generate a LaTeX file with Steadman-style formatting
5. Compile to PDF with XeLaTeX
6. Open the PDF (on macOS)

Specify lines per page as a second argument:

```bash
./generate_commentary.sh examples/sample_latin_excerpt.txt 8
```

## CLI Usage

The CLI provides several commands:

```bash
# Parse and analyze text (morphological analysis only)
python -m autocom.cli.main parse examples/sample_latin_excerpt.txt

# Full annotation pipeline (analysis + glossing)
python -m autocom.cli.main annotate examples/sample_latin_excerpt.txt

# Generate LaTeX/PDF output
python -m autocom.cli.main render examples/sample_latin_excerpt.txt --pdf

# Full commentary generation (recommended)
python -m autocom.cli.main commentary examples/sample_latin_excerpt.txt --pdf
```

### Options

- `--output`: Specify output file path
- `--lines-per-page`: Number of text lines per page (default: 10)
- `--pdf`: Compile LaTeX to PDF
- `--show-language-stats`: Display language detection statistics

## Output

Generated files are placed in `output/<basename>/`:
- `commentary.tex`: LaTeX source file
- `commentary.pdf`: Compiled PDF (if `--pdf` flag used)
- `missing_definitions.json`: Words without definitions found

## Project Structure

```
autocom/
├── cli/              # Command-line interface
├── core/             # Core data models
│   ├── models.py     # Token, Line, Page, Document, Gloss
│   ├── lexical.py    # Normalization layer (NormalizedLexicalEntry)
│   └── normalizers/  # Source-specific normalizers
├── languages/        # Language-specific processing
│   ├── latin/        # Latin lexicon, cache, analysis
│   └── greek/        # Greek lexicon, analysis
├── pipeline/         # Processing pipeline stages
│   ├── ingest.py     # Text ingestion and tokenization
│   ├── analyze.py    # Morphological analysis
│   ├── enrich.py     # Glossing and frequency tracking
│   └── layout.py     # Document layout
└── rendering/        # Output generation
    └── latex.py      # LaTeX/PDF rendering
```

## Architecture

The tool follows a deterministic pipeline:

1. **Ingestion**: Text normalization, language detection, tokenization
2. **Analysis**: Morphological analysis (lemmatization, POS tagging)
3. **Enrichment**: Dictionary lookup, glossing, frequency tracking
4. **Layout**: Document structure and pagination
5. **Rendering**: LaTeX generation and PDF compilation

### Normalization Layer

Dictionary lookups go through a normalization layer that transforms source-specific data into a canonical `NormalizedLexicalEntry` model. This ensures consistent handling across different dictionary sources (Whitaker's, Lewis & Short, LSJ, etc.).

## Development

```bash
# Run tests
pytest

# Format code
ruff format --line-length=120 autocom/ tests/

# Lint
ruff check autocom/ tests/
```

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.

## License

MIT License
