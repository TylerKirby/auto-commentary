# Auto-Commentary

A system for generating properly formatted PDF commentaries for Greek and Latin texts in the style of scholarly editions.

## Project Overview

The Auto-Commentary tool takes Greek or Latin source texts and generates properly formatted PDF commentaries that include:

1. **Main Text Section**:
   - Original text with line numbers
   - Proper diacritical marks and accents

2. **Vocabulary/Glossary Section**:
   - Two-column glossary format
   - Word entries with grammatical information and definitions
   - Frequency or reference indicators

3. **Commentary Section**:
   - Grammatical analysis
   - Idiomatic explanations
   - Translations
   - Syntax notes

## Current Progress

- [x] Generate LaTeX from txt file. LaTeX should split text into even pages.
- [x] Basic text preprocessing functionality
- [x] Vocabulary extraction framework

## Implementation Plan

### Phase 1: Text Processing (Core Functionality)

1. **Text Preprocessing**
   - [x] Clean and normalize input text
   - [ ] Tokenize text into words and sentences
   - [ ] Add line numbering functionality
   - [ ] Handle special characters and diacritical marks for both Greek and Latin

2. **Language Analysis**
   - [ ] Enhance lemmatization for both Latin and Greek
   - [ ] Add grammatical analysis (parts of speech, declensions, conjugations)
   - [ ] Extract vocabulary with frequency analysis
   - [ ] Generate basic glossary entries

### Phase 2: Commentary Generation

1. **Vocabulary Section**
   - [ ] Create two-column vocabulary format
   - [ ] Include grammatical information for each word
   - [ ] Add definitions and translations
   - [ ] Include frequency information

2. **Commentary Notes**
   - [ ] Generate basic grammatical notes
   - [ ] Create section for detailed commentary
   - [ ] Link commentary to line numbers
   - [ ] Format special cases (idioms, unusual constructions)

### Phase 3: PDF Generation

1. **LaTeX Template**
   - [ ] Create comprehensive LaTeX template matching example format
   - [ ] Design typography and layout
   - [ ] Implement proper formatting for different elements (bold, italic, etc.)

2. **Output Generation**
   - [ ] Extend existing LaTeX generation to include all commentary sections
   - [ ] Add PDF compilation functionality
   - [ ] Create configurable options for output formatting

## Technical Architecture

The system follows this pipeline:

1. **Input**: Greek or Latin text files
2. **Processing**: 
   - Text normalization and cleaning
   - Linguistic analysis (using CLTK and other libraries)
   - Vocabulary extraction and lemmatization
3. **Content Generation**:
   - Glossary creation
   - Commentary generation
4. **Output**:
   - LaTeX document assembly
   - PDF compilation

## Usage

*To be implemented*

## Dependencies

- CLTK (Classical Language Toolkit)
- LaTeX/PDF generation tools
- NLP libraries for linguistic analysis
- Greek and Latin dictionaries and datasets
- Whitaker's Words Python module (`pip install whitakers_words`)
- Requests library for API calls

## Installation

### Prerequisites

- Python 3.9 or higher
- Git
- Internet connection (for downloading dependencies)

### Standard Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/auto-commentary.git
   cd auto-commentary
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package and dependencies:
   ```bash
   pip install -e .
   ```

### Alternative Installation Methods for Whitaker's Words

If you encounter connection issues when installing the whitakers_words dependency, try one of these alternatives:

#### Option 1: Manual installation of whitakers_words

1. Clone the repository manually:
   ```bash
   git clone https://github.com/blagae/whitakers_words.git
   cd whitakers_words
   pip install -e .
   cd ..
   ```

2. Then install the rest of the dependencies:
   ```bash
   pip install -r requirements.txt --no-deps
   ```

#### Option 2: Using SSH for GitHub

Update the requirements.txt file to use SSH instead of HTTPS:
```
git+ssh://git@github.com/blagae/whitakers_words.git#egg=whitakers_words
```

#### Option 3: Using a mirror or fork

If the original repository is unavailable, you can try a fork or mirror of whitakers_words.

## Running Tests

To run the test suite:

```bash
# Install required CLTK Latin models (if not already installed)
python -c "from cltk.data.fetch import FetchCorpus; corpus_downloader = FetchCorpus(language='lat'); corpus_downloader.import_corpus('lat_models_cltk')"

# Run all tests (recommended way using virtual environment's Python)
python -m pytest

# Or use the convenience script
./runtests.sh
```

> **Important Note**: Always use `python -m pytest` instead of just `pytest` to ensure tests run with the correct Python interpreter that has access to all installed packages.

The test suite is organized following standard pytest conventions:
- Unit tests are located in the `tests/unit/autocom/` directory
- Each module has its corresponding test file (e.g., `test_definitions.py` for `definitions.py`)

If you need to run specific tests, you can use pytest's filtering capabilities:

```bash
# Run tests in a specific file
python -m pytest tests/unit/autocom/test_definitions.py

# Run tests that match a specific name pattern
python -m pytest -k "whitakers"

# Run tests with specific markers
python -m pytest -m "slow"
```

## Troubleshooting

### Network Issues with GitHub

If you see errors like:
```
Failed to connect to github.com port 443: Couldn't connect to server
```

- Check your internet connection
- Try using a VPN if GitHub is restricted in your region
- Try the SSH method if you have SSH keys set up with GitHub
- Clone the repository manually and install locally

## Contributing

Contributions to improve the project are welcome. Please feel free to submit a Pull Request.
