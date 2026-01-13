# Auto-Commentary

A tool to automatically generate commentaries for Latin and Greek texts. The tool produces nicely formatted PDF files with the original text and word definitions.

## Features

- Automatically detects Latin or Greek text
- Generates definitions for each word
- Creates a beautifully formatted PDF with proper pagination
- Latin text at the top, definitions at the bottom
- Customizable lines per page

## Requirements

- Python 3.6+
- LaTeX (with pdflatex)
- Required LaTeX packages: inputenc, fontenc, multicol, geometry, fancyhdr, xcolor, graphicx

## Quick Start

The easiest way to use the tool is with the provided shell script:

```bash
./generate_commentary.sh examples/sample_latin_excerpt.txt
```

This will:
1. Process the Latin text in the file
2. Generate definitions for each word
3. Create a LaTeX file in the `output` directory
4. Compile the LaTeX file to PDF
5. Open the PDF file (on macOS)

You can specify the number of lines per page as a second argument:

```bash
./generate_commentary.sh examples/sample_latin_excerpt.txt 8
```

## Manual Usage

If you prefer to run the steps manually:

1. Generate the LaTeX file:
   ```bash
   python -m autocom.cli examples/sample_latin_excerpt.txt --output=output/my_commentary.tex --lines-per-page=10 --show-language-stats
   ```

2. Compile the LaTeX file:
   ```bash
   pdflatex -interaction=nonstopmode -output-directory=output output/my_commentary.tex
   ```

3. Open the PDF:
   ```bash
   open output/my_commentary.pdf
   ```

## Layout Customization

The layout can be customized by modifying the `autocom/core/layout.py` file. Current layout features:
- Large Latin text at the top
- Simple horizontal divider
- Compact definitions table at the bottom
- Nice margins (0.75 inches)
- Bold headwords with smaller italic definitions
