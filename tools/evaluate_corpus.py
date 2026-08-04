#!/usr/bin/env python3
"""Evaluate manifest-listed hypotheses against manually verified references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ewp_transcripts.corpus_quality import evaluate_corpus, load_corpus_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produce lexical corpus metrics and an error-only word diff."
    )
    parser.add_argument("manifest", type=Path, help="strict external corpus TOML manifest")
    parser.add_argument(
        "--hypothesis-root",
        type=Path,
        required=True,
        help="root containing hypothesis paths listed by the manifest",
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report path")
    parser.add_argument("--diff-output", type=Path, required=True, help="word-diff report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, difference = evaluate_corpus(
        load_corpus_manifest(args.manifest),
        hypothesis_root=args.hypothesis_root,
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.diff_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    args.diff_output.write_text(difference, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
