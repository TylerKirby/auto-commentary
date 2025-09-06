"""
CLI evaluation for `src/agents/latin/parsing.py` using `examples/sample_latin_text.txt`.

This script tokenizes the provided Latin text file and exercises the
`LatinParsingTools` methods (`get_lemma`, `get_pos`, `get_definition`, `get_macronization`).

It writes per-token results to `evals/results/<timestamp>.jsonl` and prints a concise
summary to stdout. Network-dependent parts (POS via Morpheus) are optional and
fail-safe. Definitions require Whitaker's Words; if unavailable, results will be empty.
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

# Ensure repository root is on sys.path so `src` package can be imported when
# running this file directly (python evals/run_parsing_eval.py)
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _import_tools():
    # Local import to satisfy environment path setup before import
    from src.agents.latin.parsing import (
        LatinParsingTools as _LatinParsingTools,  # noqa: WPS433
    )

    return _LatinParsingTools


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
    Run `LatinParsingTools` on an iterable of tokens and collect results plus summary metrics.

    :param tokens: Iterable of token strings.
    :param enable_pos: Whether to call the networked POS service.
    :param max_defs: Maximum number of definitions to request per token.
    :return: (results, metrics) where results is a list of TokenEvalResult and metrics a dict.
    """
    LatinParsingTools = _import_tools()
    tools = LatinParsingTools()

    results: List[TokenEvalResult] = []
    lemma_changed = 0
    pos_nonempty = 0
    defs_nonempty = 0
    macron_changed = 0
    errors = 0

    # Source usage counters
    lemma_source_counts = {"spacy": 0, "cltk": 0}
    pos_source_counts = {"spacy": 0, "morpheus": 0, "none": 0}
    defs_source_counts = {"lewis_short": 0, "whitaker": 0, "none": 0}
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
            # Determine lemma and source
            if getattr(tools, "_prefer_spacy", False) and getattr(tools, "_spacy_nlp", None) is not None:
                try:
                    _doc = tools._spacy_nlp(tok)  # type: ignore[attr-defined]
                    _spacy_lemma = _doc[0].lemma_ if _doc and len(_doc) > 0 else ""
                    if isinstance(_spacy_lemma, str) and _spacy_lemma.strip():
                        lemma_source = "spacy"
                except Exception:
                    lemma_source = "cltk"
            lemma = tools.get_lemma(tok)
            lemma_source_counts[lemma_source] = lemma_source_counts.get(lemma_source, 0) + 1

            # Determine POS and source
            if enable_pos:
                if getattr(tools, "_prefer_spacy", False) and getattr(tools, "_spacy_nlp", None) is not None:
                    try:
                        _docp = tools._spacy_nlp(tok)  # type: ignore[attr-defined]
                        if _docp and len(_docp) > 0:
                            _upos = _docp[0].pos_ or ""
                            _feats = str(_docp[0].morph) if getattr(_docp[0], "morph", None) is not None else ""
                            _label = _upos if not _feats else (f"{_upos}: {_feats}" if _upos else _feats)
                            if _label:
                                pos_source = "spacy"
                    except Exception:
                        pass
                pos = tools.get_pos(tok)
                if pos and pos_source != "spacy":
                    pos_source = "morpheus"
                if not pos:
                    pos_source = "none"
                pos_source_counts[pos_source] = pos_source_counts.get(pos_source, 0) + 1

            # Determine definitions and source
            try:
                ls_defs_probe = tools._lookup_lewis_short(lemma or tok, max_defs)  # type: ignore[attr-defined]
            except Exception:
                ls_defs_probe = []
            defs = tools.get_definition(lemma or tok, max_senses=max_defs)
            if ls_defs_probe:
                defs_source = "lewis_short"
            elif defs:
                defs_source = "whitaker"
            else:
                defs_source = "none"
            defs_source_counts[defs_source] = defs_source_counts.get(defs_source, 0) + 1

            # Determine macronization and source
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
