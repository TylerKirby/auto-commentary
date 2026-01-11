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
pytest tests/core/test_lexical.py  # Run specific test file
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

### Generating Sample Output
**Convention**: Always output to `output/<descriptive_name>/` (gitignored).

```bash
# Latin sample
python -m autocom.cli.main commentary examples/sample_latin_short.txt --pdf --output output/latin_sample

# Greek sample
python -m autocom.cli.main commentary examples/sample_greek.txt --pdf --output output/greek_sample

# Testing a specific fix
python -m autocom.cli.main commentary examples/sample_latin_short.txt --pdf --output output/headword_test
```

**Directory structure**:
- `examples/` - Source texts (tracked in git)
- `output/` - Generated artifacts (gitignored)
  - `output/<name>/commentary.pdf` - Rendered PDF
  - `output/<name>/commentary.tex` - LaTeX source
  - `output/<name>/missing_definitions.json` - Words without definitions

**Sample texts available**:
- `examples/sample_latin_short.txt` - Aeneid I.1-4 (Latin)
- `examples/sample_greek.txt` - Iliad I.1-3 (Greek)
- `examples/sample_greek_longer.txt` - Extended Greek passage
- `examples/sample_latin_text.txt` - Longer Latin passage

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

### Lexical Normalization Layer
The normalization layer (`autocom/core/lexical.py`) provides a canonical internal representation for dictionary entries, decoupling raw extraction from rendering.

**Core Types** (`autocom/core/lexical.py`):
- `NormalizedLexicalEntry`: Canonical dictionary entry with headword, lemma, POS, senses, and morphological metadata
- `PartOfSpeech`: Standardized POS enum (NOUN, VERB, ADJECTIVE, etc.)
- `Gender`: Grammatical gender (MASCULINE, FEMININE, NEUTER, COMMON)
- `VerbVoice`: Voice categories including DEPONENT and SEMI_DEPONENT
- `LatinPrincipalParts`: Structured verb forms (present, infinitive, perfect, supine)
- `GreekPrincipalParts`: Six Greek principal parts with tense stems
- `GreekVerbClass`: Verb classifications (OMEGA, MI, CONTRACT_ALPHA, etc.)
- `LatinStemType` / `GreekStemType`: Morpheus-compatible stem classifications

**Normalizers** (`autocom/core/normalizers/`):
- `WhitakersNormalizer`: Transforms Whitaker's Words output to `NormalizedLexicalEntry`
  - Reconstructs headwords from stems for all word types
  - Maps POS and gender codes to standard enums
  - Extracts and structures principal parts for verbs
  - Cleans senses (removes brackets, citations, normalizes whitespace)
  - Detects deponent/semi-deponent verbs and pluralia tantum nouns

**Architecture Flow**:
```
Raw Extraction (source-specific) → Normalizer → NormalizedLexicalEntry → Gloss → Rendering
```

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

## Development Practices

### Test-Driven Development (TDD)

This project follows TDD. When implementing new features or fixing bugs:

1. **Write tests first** - Before writing implementation code, write failing tests that define the expected behavior
2. **Run tests to confirm failure** - Verify the tests fail for the right reasons
3. **Implement the minimum code** - Write just enough code to make tests pass
4. **Refactor** - Clean up while keeping tests green
5. **Repeat** - Add more tests for edge cases and additional requirements

```bash
# Run tests frequently during development
pytest tests/path/to/test_file.py -v  # Run specific test file
pytest -x                              # Stop on first failure
pytest --lf                            # Run last failed tests
```

### Beads Acceptance Criteria

When creating beads issues, include detailed acceptance criteria that define "done":

```bash
bd create --title="Add Greek article display" --type=task --priority=2 --body="
## Description
Display the appropriate Greek article (ὁ, ἡ, τό) before noun headwords.

## Acceptance Criteria
- [ ] Masculine nouns display ὁ (e.g., ὁ λόγος)
- [ ] Feminine nouns display ἡ (e.g., ἡ θεά)
- [ ] Neuter nouns display τό (e.g., τό ἔργον)
- [ ] Verbs and other POS do not display articles
- [ ] Article appears in rendered PDF glossary

## Test Cases
- Test masculine 2nd declension noun
- Test feminine 1st declension noun
- Test neuter 3rd declension noun
- Test verb (no article)

## Out of Scope
- Dual/plural article forms
- Article agreement with adjectives
"
```

Good acceptance criteria are:
- **Specific** - Clear pass/fail conditions
- **Testable** - Can be verified with automated tests
- **Scoped** - Explicitly states what's NOT included

## Beads Usage

When working on an issue, use `bd update` liberally to record:
- What you discovered about the codebase
- Design decisions and why you made them
- What you tried that didn't work
- Dependencies or blockers you found
- Test cases you identified

This is your persistent memory. Future sessions (including after compaction)
will have this context. Write notes as if explaining to yourself tomorrow.

**IMPORTANT**: Before closing any beads issue, always point the user to relevant output for review:
- Generated PDFs: `output/<name>/commentary.pdf`
- Error/missing definitions: `output/<name>/missing_definitions.json`
- LaTeX source: `output/<name>/commentary.tex`
- Test results: Run and show pytest output

Never close an issue until the user has had a chance to review the output.
