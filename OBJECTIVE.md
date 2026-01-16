# OBJECTIVE: CLI Commentary Generator for Greek and Latin Texts

## Project Overview
Implement a command-line interface that accepts plain Greek or Latin text files and generates comprehensive PDF commentaries with original text, line numbers, and detailed word-by-word glossaries with grammatical analysis.

## Target Output Format
Based on the example images, the commentary should include:
- **Header**: Title and text reference (e.g., "ILIAD 6.1-10", "Ten Letters of Seneca")
- **Primary Text**: Original text with line numbers, proper formatting and spacing
- **Glossary Section**: Alphabetized word definitions with:
  - Lemma forms
  - Grammatical information (case, gender, number, tense, mood, voice)
  - English definitions and contextual meanings
  - Cross-references and etymological notes where relevant

## Technical Architecture

### 1. Core Pipeline Enhancement
Build upon the existing pipeline architecture in `src/pipeline/`:

#### Text Ingestion (`src/pipeline/ingest.py`)
- **Current State**: Basic normalization, language detection, tokenization
- **Enhancements Needed**:
  - Improved Greek Unicode handling (polytonic, monotonic)
  - Better line segmentation for poetry vs. prose
  - Preservation of original formatting and line breaks
  - Metadata extraction (title, author, work reference)

#### Morphological Analysis (`src/pipeline/analyze.py`)
- **Current State**: Latin analysis with CLTK, spaCy-UDPipe, Morpheus
- **Enhancements Needed**:
  - **Greek Support**: Integrate Greek morphological analyzers
    - CLTK Greek models
    - Morpheus Greek endpoint
    - spaCy Greek models if available
  - **Enhanced Analysis Output**:
    - Full morphological feature sets
    - Principal parts for verbs
    - Comparative/superlative forms for adjectives
    - Dialectal variations
  - **Disambiguation**: Context-aware POS tagging and lemmatization

#### Lexicon and Glossing (`src/pipeline/lexicon.py`, `src/pipeline/enrich.py`)
- **Current State**: Basic Latin lexicon lookup
- **Major Enhancements Required**:
  - **Greek Lexicon Integration**:
    - LSJ (Liddell-Scott-Jones) dictionary
    - Autenrieth (Homeric dictionary)
    - Middle Liddell for basic definitions
  - **Latin Lexicon Expansion**:
    - Lewis & Short integration
    - Elementary Lewis for basic definitions
    - Specialized dictionaries (medical, legal, ecclesiastical)
  - **Contextual Definition Selection**:
    - Rank definitions by frequency and context
    - Poetic vs. prose usage preferences
    - Historical period considerations
  - **Grammatical Information Enhancement**:
    - Principal parts for verbs
    - Genitive forms for nouns
    - Comparative forms for adjectives
    - Irregular forms and suppletive paradigms

### 2. New Components to Implement

#### Greek Language Support (`src/agents/greek/`)
```
src/agents/greek/
├── __init__.py
├── parsing.py          # Greek morphological analysis
├── lexicon.py          # Greek dictionary integration
└── text_processing.py  # Greek-specific text handling
```

**Key Features**:
- Ancient Greek morphological analysis
- Dialect recognition (Attic, Ionic, Doric, etc.)
- Accentuation and breathing mark handling
- Manuscript tradition considerations

#### Enhanced Rendering System (`src/renderers/`)
- **LaTeX Template System**:
  - Commentary-specific templates
  - Bilingual typesetting (Greek/Latin + English)
  - Professional academic formatting
  - Customizable layouts for different text types
- **Typography Enhancements**:
  - Proper Greek fonts (GFS Porson, Gentium Plus)
  - Latin ligatures and abbreviations
  - Line numbering systems
  - Cross-reference systems

#### Bibliography and Citation System (`src/pipeline/citations.py`)
- Source attribution
- Standard abbreviation systems (LSJ, L&S, OLD)
- Cross-references to standard editions
- Manuscript traditions

### 3. CLI Interface Design

#### Enhanced Command Structure
```bash
autocom generate [INPUT_FILE] [OPTIONS]
```

#### Core Options
- `--language {latin,greek,auto}`: Force language detection
- `--output-dir PATH`: Output directory (default: ./output)
- `--title TEXT`: Commentary title
- `--author TEXT`: Text author
- `--work TEXT`: Work title
- `--lines-per-page INT`: Layout control
- `--lexicon {full,intermediate,basic}`: Vocabulary level
- `--include-grammar/--no-grammar`: Grammatical analysis toggle
- `--pdf/--latex-only`: Output format control

#### Advanced Options
- `--dialect {attic,ionic,doric,koine}`: Greek dialect specification
- `--period {archaic,classical,hellenistic,late}`: Historical period
- `--prose/--verse`: Text type optimization
- `--abbreviations/--no-abbreviations`: Standard abbreviations
- `--cross-references/--no-cross-refs`: Internal linking

### 4. Data Integration Strategy

#### Dictionary Sources
- **Greek**: 
  - LSJ XML/JSON API integration
  - Perseus Digital Library
  - TLG lexical data
- **Latin**:
  - Lewis & Short digitized
  - Perseus Latin dictionary
  - Whitaker's Words integration

#### Morphological Analyzers
- **Greek**: 
  - Morpheus (Perseus)
  - CLTK Greek models
  - Custom trained models for specific corpora
- **Latin**: 
  - Existing Morpheus integration
  - Enhanced CLTK support
  - Collatinus for medieval Latin

### 5. Quality Assurance Framework

#### Validation Pipeline
- **Morphological Accuracy**: Compare against known paradigms
- **Lexical Coverage**: Ensure comprehensive vocabulary coverage
- **Output Quality**: LaTeX compilation testing
- **Performance**: Benchmark processing times

#### Test Coverage
- Unit tests for each language module
- Integration tests with sample texts
- Regression tests for known challenging texts
- Performance benchmarks

### 6. Implementation Phases

#### Phase 1: Greek Language Foundation
1. Implement Greek text processing pipeline
2. Integrate Greek morphological analysis
3. Basic Greek lexicon integration
4. Update CLI to support Greek texts

#### Phase 2: Enhanced Lexicography
1. Integrate comprehensive dictionaries (LSJ, L&S)
2. Implement contextual definition ranking
3. Add grammatical information enhancement
4. Cross-reference system implementation

#### Phase 3: Advanced Features
1. Typography and layout optimization
2. Citation and bibliography system
3. Dialect and period-specific processing
4. Advanced CLI options

#### Phase 4: Polish and Performance
1. Performance optimization
2. Error handling and user feedback
3. Documentation and examples
4. Distribution and packaging

### 7. File Structure Extensions

```
src/
├── agents/
│   ├── greek/                    # Greek language processing
│   │   ├── parsing.py
│   │   ├── lexicon.py
│   │   └── text_processing.py
│   └── latin/                    # Enhanced Latin processing
│       ├── parsing.py
│       └── advanced_lexicon.py
├── data/                         # Dictionary and linguistic data
│   ├── dictionaries/
│   │   ├── greek/
│   │   └── latin/
│   └── morphology/
├── pipeline/
│   ├── citations.py              # Bibliography system
│   ├── typography.py             # Advanced formatting
│   └── validation.py             # Quality assurance
├── renderers/
│   ├── templates/                # LaTeX templates
│   │   ├── commentary.tex
│   │   ├── greek_fonts.sty
│   │   └── latin_fonts.sty
│   └── bibliography.py           # Citation rendering
└── resources/                    # Linguistic resources
    ├── abbreviations.json
    ├── manuscript_sigla.json
    └── standard_editions.json
```

### 8. Success Criteria

#### Functional Requirements
- Process both Greek and Latin texts with >95% morphological accuracy
- Generate professionally formatted PDF commentaries
- Support major text types (epic, lyric, prose, dramatic)
- Handle texts from archaic through late periods

#### Performance Requirements
- Process typical classroom text (50-100 lines) in <30 seconds
- Generate PDF output in <60 seconds total
- Memory usage <1GB for typical texts

#### Quality Requirements
- Lexical coverage >98% for classical texts
- Grammatical analysis accuracy >95%
- LaTeX compilation success rate >99%
- Professional typographic quality matching academic standards

### 9. Dependencies and Resources

#### New Dependencies
- `lxml`: XML parsing for dictionary data
- `requests`: API integration
- `beautifulsoup4`: HTML parsing for web resources
- `fonttools`: Advanced typography
- `polyglot` or similar: Enhanced language detection

#### External Resources
- Perseus Digital Library APIs
- TLG (Thesaurus Linguae Graecae) data access
- Unicode Greek font packages
- Academic citation style guides

### 10. Risk Assessment and Mitigation

#### Technical Risks
- **Dictionary API limitations**: Implement local fallbacks and caching
- **Morphological accuracy**: Multiple analyzer ensemble approach
- **Typography complexity**: Extensive testing with different LaTeX distributions
- **Performance with large texts**: Implement chunking and progress reporting

#### Resource Risks
- **Dictionary licensing**: Focus on open-source and public domain resources
- **Font licensing**: Use SIL OFL and similar open licenses
- **API dependencies**: Implement graceful degradation

This implementation plan builds upon the existing codebase architecture while adding comprehensive Greek support and enhanced commentary generation capabilities to match the quality and format of the example images.