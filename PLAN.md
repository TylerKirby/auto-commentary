# PDF Presentation Improvement Plan

## Goals
- Upgrade the generated commentary PDF so it approaches professional scholarly layouts (clear typography, balanced white space, visually distinct glossary).
- Reduce repeated LaTeX failures by tightening template hygiene and escaping.
- Establish a feedback loop for rapid iteration (preview, diffable artifacts).

## Immediate Work (0–2 days)
- [ ] **Audit current LaTeX output**: annotate `output/sample_latin_short/commentary.pdf` with issues (fonts, spacing, glossary readability).
- [ ] **Stabilize LaTeX build**: ensure templates avoid `\LaTeX` errors for long texts (e.g., guard blank glossary entries, wrap line numbers in `\textbf{}` safely).
- [ ] **Introduce consistent fonts**: switch body to `Latin Modern Roman` or `Libertinus`; load `Gentium Plus` for Greek via `fontspec` (requires XeLaTeX/LuaLaTeX decision).
- [ ] **Add section headers / ornaments**: create macros for text header versus glossary header with rule weight and spacing controls.
- [ ] **Regenerate sample outputs** to baseline before styling changes.

## Short Term Enhancements (2–5 days)
- [ ] **Adopt XeLaTeX**: migrate renderer to call `xelatex` so we can reliably load Unicode fonts; gate behind feature flag with graceful fallback to pdfLaTeX.
- [ ] **Build reusable LaTeX components**: move repeated structures into `.sty` or dedicated template partials (`line-block`, `gloss-entry`).
- [ ] **Refine glossary layout**: consider single-column format for short texts, dynamic column count, and `tabularx` for alignment of lemma vs definitions.
- [ ] **Implement line-number gutter**: use `paracol` or `tcolorbox` to create left gutter with line numbers, mirroring classical commentaries.
- [ ] **Contrast & color**: add subdued color accents (line number gray, glossary header rule) with user-configurable options.

## Medium Term (1–2 weeks)
- [ ] **Pagination-aware design**: update `layout.paginate` to account for glossary height using finer granularity (e.g., measure lemma count + definition length).
- [ ] **Add front matter/back matter**: optional title page, bibliography stub, index placeholders.
- [ ] **Support bilingual headers**: display original language plus English translation in header/footer.
- [ ] **Automated visual regression**: script to compile representative texts and compare PDFs (e.g., Ghostscript to PNG + image diff) to catch layout regressions.
- [ ] **Configurable themes**: add CLI flags for fonts, column count, colors, enabling users to choose preset styles.

- [ ] **Greek/Latin NLP benchmarks**: build reproducible suites to measure analyzer accuracy (lemma, POS, morphology) against gold data before/after changes.
- [ ] **Concise lexicon definitions**: rank dictionary senses by frequency/context; add heuristics for short gloss selection (e.g., prioritise teaching-friendly options).
- [ ] **Dictionary caching strategy**: store Perseus/LatinWordNet responses locally; add CLI toggle for offline mode.
- [ ] **Analyzer ensemble improvements**: experiment with combining CLTK, spaCy-UDPipe, Morpheus (majority vote, confidence scoring) to reduce lemma/POS errors.
- [ ] **Greek dialect handling**: expand `detect_greek_dialect` heuristics and surface dialect metadata in the CLI/log output.
- [ ] **Error telemetry**: log unknown words / failed lookups with counts so we can prioritise lexicon gaps.


## Risks / Considerations
- XeLaTeX dependency increases install footprint; need documentation + detection.
- External fonts require licensing checks; prefer SIL OFL fonts (Gentium, Libertinus).
- Layout changes might break glossary tests; update fixtures accordingly.
- Large texts stress LaTeX; consider chunking glossary or generating per-page glossaries with stable ordering.

## Success Criteria
- No LaTeX build failures on large Latin and Greek samples.
- PDFs use consistent professional fonts with clear hierarchy.
- Glossary readable at arm’s length with minimal overfull boxes (<5 warnings per run).
- CLI offers at least one alternative layout preset and documents usage.
