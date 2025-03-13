# AutoCom: Automatic Commentary Generator

A Python package for generating automatic commentaries for Latin and Greek texts, making classical texts more accessible for students and teachers.

## Features

- Support for both Latin and Greek texts
- Automatic language detection
- Word definitions with grammatical analysis from various APIs and dictionaries
- Text formatting with line numbers and pagination
- LaTeX output for professional-looking commentaries
- Modular design for easy extension to other languages

## Installation

### Basic Installation

```bash
pip install autocom
```

### With Advanced Features

For enhanced NLP processing (lemmatization, morphological analysis), install with the "advanced" extras:

```bash
pip install autocom[advanced]
```

This will install additional dependencies like CLTK for advanced language processing.

## Project Structure

The package is organized in a modular way to clearly separate language-specific functionality from core components:

```
autocom/
├── core/
│   ├── __init__.py
│   ├── constants.py
│   ├── layout.py
│   ├── text.py
│   └── utils.py
├── languages/
│   ├── __init__.py
│   ├── latin/
│   │   ├── __init__.py
│   │   ├── definitions.py
│   │   └── parsers.py
│   └── greek/
│       ├── __init__.py
│       ├── definitions.py
│       └── parsers.py
├── __init__.py
└── cli.py
```

## Usage

### Basic Usage

```python
from autocom import generate_commentary

# Generate a Latin commentary
latin_text = "Gallia est omnis divisa in partes tres"
latin_commentary = generate_commentary(latin_text)  # Language auto-detected

# Generate a Greek commentary
greek_text = "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει"
greek_commentary = generate_commentary(greek_text)  # Language auto-detected
```

### Command Line Interface

```bash
# Generate commentary from a text file
autocom my_latin_text.txt --output commentary.tex

# Specify language explicitly
autocom my_greek_text.txt --language greek --output commentary.tex

# Customize output format
autocom my_text.txt --format markdown --output commentary.md
```

## API Reference

### Core Functions

- `detect_language(text)` - Detect whether text is Latin or Greek
- `clean_text(text, language)` - Clean and normalize text for the specified language
- `generate_commentary(text, language, output_format)` - Generate a full commentary

### Language-Specific Modules

#### Latin

- `autocom.languages.latin.get_definition(word)` - Get definition for a Latin word
- `autocom.languages.latin.extract_latin_words(text)` - Extract Latin words from text

#### Greek

- `autocom.languages.greek.get_definition(word)` - Get definition for a Greek word
- `autocom.languages.greek.extract_greek_words(text)` - Extract Greek words from text

## Examples

See the `examples/` directory for complete examples:

- `latin_definitions_example.py` - Demonstrates Latin word definitions
- `greek_text_example.py` - Demonstrates Greek text processing
- `multiple_languages_example.py` - Shows how to work with both languages

## Dependencies

- `requests` - For API interactions
- `unicodedata2` - For Unicode normalization of text
- `cltk` (optional) - For advanced language processing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
