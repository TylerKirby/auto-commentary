#!/bin/bash

# Usage: ./generate_commentary.sh input_file [lines_per_page]
# Example: ./generate_commentary.sh examples/sample_latin_excerpt.txt 8

if [ -z "$1" ]; then
  echo "Usage: ./generate_commentary.sh input_file [lines_per_page]"
  echo "Example: ./generate_commentary.sh examples/sample_latin_excerpt.txt 8"
  exit 1
fi

INPUT_FILE=$1
LINES_PER_PAGE=${2:-10}  # Default to 10 lines per page if not specified
BASENAME=$(basename "$INPUT_FILE" | sed 's/\.[^.]*$//')  # Remove extension
OUTPUT_FILE="output/${BASENAME}.tex"

# Ensure output directory exists
mkdir -p output

# Generate the LaTeX file
echo "Generating commentary for $INPUT_FILE with $LINES_PER_PAGE lines per page..."
python -m autocom.cli "$INPUT_FILE" --output="$OUTPUT_FILE" --lines-per-page="$LINES_PER_PAGE" --show-language-stats

# Compile the LaTeX file if it was generated successfully
if [ $? -eq 0 ]; then
  echo "Compiling LaTeX file to PDF..."
  pdflatex -interaction=nonstopmode -output-directory=output "$OUTPUT_FILE"
  
  if [ $? -eq 0 ]; then
    echo "PDF created successfully at output/${BASENAME}.pdf"
    
    # Open the PDF file (macOS specific)
    if [ "$(uname)" == "Darwin" ]; then
      open "output/${BASENAME}.pdf"
    else
      echo "You can view the PDF at output/${BASENAME}.pdf"
    fi
  else
    echo "Error compiling LaTeX file."
  fi
else
  echo "Error generating commentary."
fi
