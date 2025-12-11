"""
CLI evaluation for Latin parsing using `examples/sample_latin_text.txt`.

This script tokenizes the provided Latin text file and exercises the full
Latin analysis pipeline: `LatinAnalyzer` for lemmatization/POS and `LatinLexicon`
for definitions with alternative lemma lookup.

It writes per-token results to `evals/results/<timestamp>.jsonl` and prints a concise
summary to stdout. Network-dependent parts (POS via Morpheus) are optional and
fail-safe.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Ensure repository root is on sys.path so `autocom` package can be imported when
# running this file directly (python evals/run_parsing_eval.py)
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _import_tools():
    # Local import to satisfy environment path setup before import
    from autocom.processing.analyze import LatinAnalyzer
    from autocom.languages.latin.analyzer import LatinParsingTools  # For macronization
    from autocom.languages.latin.lexicon import LatinLexicon
    from autocom.core.models import Token, Analysis

    return LatinAnalyzer, LatinParsingTools, LatinLexicon, Token, Analysis


LATIN_WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F\u0100-\u017F\u0180-\u024F]+")


@dataclass
class TokenEvalResult:
    token: str
    lemma: str
    pos: List[str]
    definitions: List[str]
    macronized: str
    lemma_source: str
    pos_source: str
    defs_source: str
    macron_source: str
    elapsed_ms: float
    had_error: bool
    error_message: Optional[str]


def read_text_tokens(file_path: Path, max_tokens: Optional[int]) -> List[str]:
    """
    Read a text file and extract a de-duplicated, order-preserving list of tokens.

    :param file_path: Path to the input text file.
    :param max_tokens: Optional cap on the number of unique tokens to return.
    :return: List of token strings in encounter order.
    """
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    raw_tokens = LATIN_WORD_RE.findall(text)

    seen = set()
    unique_tokens: List[str] = []
    for tok in raw_tokens:
        if len(tok) < 2:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        unique_tokens.append(tok)
        if max_tokens is not None and len(unique_tokens) >= max_tokens:
            break
    return unique_tokens


def evaluate_tokens(
    tokens: Iterable[str],
    enable_pos: bool,
    max_defs: int,
) -> Tuple[List[TokenEvalResult], dict]:
    """
    Run the full Latin analysis pipeline on an iterable of tokens.

    Uses LatinAnalyzer (with EnhancedLatinLemmatizer) for lemmatization/POS,
    and LatinLexicon for definitions with alternative lemma lookup.

    :param tokens: Iterable of token strings.
    :param enable_pos: Whether to call the networked POS service.
    :param max_defs: Maximum number of definitions to request per token.
    :return: (results, metrics) where results is a list of TokenEvalResult and metrics a dict.
    """
    LatinAnalyzer, LatinParsingTools, LatinLexicon, Token, Analysis = _import_tools()

    # Initialize full pipeline components
    analyzer = LatinAnalyzer(prefer_spacy=True, use_enhanced_lemmatizer=True)
    lexicon = LatinLexicon(max_senses=max_defs)
    tools = LatinParsingTools()  # For macronization

    results: List[TokenEvalResult] = []
    lemma_changed = 0
    pos_nonempty = 0
    defs_nonempty = 0
    macron_changed = 0
    errors = 0

    # Source usage counters
    lemma_source_counts = {"enhanced": 0, "spacy": 0, "cltk": 0}
    pos_source_counts = {"spacy": 0, "morpheus": 0, "none": 0}
    defs_source_counts = {"lewis_short": 0, "whitaker": 0, "alternative": 0, "none": 0}
    macron_source_counts = {"collatinus": 0, "none": 0}

    for tok in tokens:
        start = time.perf_counter()
        error_message: Optional[str] = None
        lemma = tok
        pos: List[str] = []
        defs: List[str] = []
        macron = tok
        lemma_source = "cltk"
        pos_source = "none"
        defs_source = "none"
        macron_source = "none"
        had_error = False
        try:
            # Create token and run through full analysis pipeline
            token_obj = Token(
                text=tok,
                normalized=tok.lower(),
                start_char=0,
                end_char=len(tok),
                is_punct=False,
            )

            # Step 1: Analyze token (lemmatization + POS via EnhancedLatinLemmatizer)
            analyzer.analyze_token(token_obj)
            lemma = token_obj.analysis.lemma if token_obj.analysis else tok
            lemma_source = "enhanced"
            lemma_source_counts["enhanced"] = lemma_source_counts.get("enhanced", 0) + 1

            # Step 2: Get POS labels
            if enable_pos and token_obj.analysis:
                pos = token_obj.analysis.pos_labels or []
                if pos:
                    pos_source = "spacy"
                else:
                    pos_source = "none"
                pos_source_counts[pos_source] = pos_source_counts.get(pos_source, 0) + 1

            # Step 3: Enrich with definitions (uses alternative lemma lookup)
            original_lemma = lemma
            lexicon.enrich_token(token_obj)

            if token_obj.gloss and token_obj.gloss.senses:
                defs = token_obj.gloss.senses[:max_defs]
                final_lemma = token_obj.gloss.lemma

                # Determine definition source
                if final_lemma != original_lemma:
                    # Alternative lemma was used
                    defs_source = "alternative"
                else:
                    # Check if it came from Lewis & Short or Whitaker
                    try:
                        ls_probe = lexicon._get_lewis_short_entry(final_lemma)
                        if ls_probe:
                            defs_source = "lewis_short"
                        else:
                            defs_source = "whitaker"
                    except Exception:
                        defs_source = "whitaker"

                # Update lemma to the one that found definitions
                lemma = final_lemma
            else:
                defs_source = "none"

            defs_source_counts[defs_source] = defs_source_counts.get(defs_source, 0) + 1

            # Step 4: Get macronization
            macron = tools.get_macronization(lemma or tok)
            if macron and macron != tok:
                macron_source = "collatinus"
            else:
                macron_source = "none"
            macron_source_counts[macron_source] = macron_source_counts.get(macron_source, 0) + 1

        except Exception as exc:  # defensive: keep eval running
            had_error = True
            errors += 1
            error_message = f"{type(exc).__name__}: {exc}"
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0

        if lemma and lemma != tok:
            lemma_changed += 1
        if pos:
            pos_nonempty += 1
        if defs:
            defs_nonempty += 1
        if macron and macron != tok:
            macron_changed += 1

        results.append(
            TokenEvalResult(
                token=tok,
                lemma=lemma,
                pos=pos,
                definitions=defs,
                macronized=macron,
                lemma_source=lemma_source,
                pos_source=pos_source,
                defs_source=defs_source,
                macron_source=macron_source,
                elapsed_ms=elapsed_ms,
                had_error=had_error,
                error_message=error_message,
            )
        )

    total = len(results)
    metrics = {
        "total_tokens": total,
        "lemma_changed": lemma_changed,
        "lemma_changed_rate": (lemma_changed / total) if total else 0.0,
        "pos_nonempty": pos_nonempty,
        "pos_nonempty_rate": (pos_nonempty / total) if total else 0.0,
        "defs_nonempty": defs_nonempty,
        "defs_nonempty_rate": (defs_nonempty / total) if total else 0.0,
        "macron_changed": macron_changed,
        "macron_changed_rate": (macron_changed / total) if total else 0.0,
        "errors": errors,
        "error_rate": (errors / total) if total else 0.0,
        "lemma_source_counts": lemma_source_counts,
        "pos_source_counts": pos_source_counts,
        "defs_source_counts": defs_source_counts,
        "macron_source_counts": macron_source_counts,
    }
    return results, metrics


def ensure_results_dir(base_dir: Path) -> Path:
    """
    Ensure `evals/results` exists under the repository root.

    :param base_dir: Path to repository root.
    :return: Path to created/existing results directory.
    """
    results_dir = base_dir / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def write_jsonl(path: Path, rows: Iterable[TokenEvalResult]) -> None:
    """
    Write results to a JSON Lines file.

    :param path: Destination jsonl path.
    :param rows: Iterable of TokenEvalResult.
    """
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate LatinParsingTools on a Latin text file.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("examples/sample_latin_text.txt"),
        help="Path to input Latin text (default: examples/sample_latin_text.txt)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=200,
        help="Maximum number of unique tokens to evaluate (default: 200)",
    )
    parser.add_argument(
        "--disable-pos",
        action="store_true",
        help="Skip POS lookups (networked Morpheus service)",
    )
    parser.add_argument(
        "--max-defs",
        type=int,
        default=5,
        help="Maximum number of definitions per token (default: 5)",
    )

    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    input_path = (repo_root / args.file) if not args.file.is_absolute() else args.file
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    tokens = read_text_tokens(input_path, max_tokens=args.max_tokens)
    results, metrics = evaluate_tokens(tokens, enable_pos=(not args.disable_pos), max_defs=args.max_defs)

    results_dir = ensure_results_dir(repo_root)
    ts = int(time.time())
    jsonl_path = results_dir / f"parsing_eval_{ts}.jsonl"
    summary_path = results_dir / f"parsing_eval_{ts}_summary.json"
    write_jsonl(jsonl_path, results)
    summary_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # Console summary
    print("LatinParsingTools evaluation summary:")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Saved per-token results to: {jsonl_path}")
    print(f"Saved summary to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
