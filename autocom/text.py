def create_latex_file(input_filename, output_filename, title, author, words_per_page=150):
    with open(input_filename, 'r') as f:
        text = f.read()

    latex_preamble = fr"""\documentclass[14pt]{{book}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{setspace}}
\usepackage[a5paper, margin=1in]{{geometry}}

\title{{{title}}}
\author{{{author}}}
\date{{\today}}

\begin{{document}}

\frontmatter
\maketitle
\mainmatter
\doublespacing
"""

    latex_postamble = r"""\end{document}"""

    with open(output_filename, 'w') as f:
        f.write(latex_preamble)

        words = text.split()
        word_count = 0
        for word in words:
            word_count += 1
            f.write(f"{word} ")

            if word_count % words_per_page == 0:
                f.write("\n\n\\newpage\n\\null\n\\newpage\n")

        f.write(latex_postamble)

if __name__ == "__main__":
    input_text = "sample_latin_text.txt"
    output_filename = "sample_output/output.tex"
    title = "Title"
    author = "Author"

    create_latex_file(input_text, output_filename, title, author)
