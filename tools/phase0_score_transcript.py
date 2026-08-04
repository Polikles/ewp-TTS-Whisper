#!/usr/bin/env python3
"""Score a hypothesis transcript against a manually verified reference.

This Phase 0 utility deliberately evaluates lexical content rather than
formatting. It never prints transcript text.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ewp_transcripts.quality import (
    NORMALIZATION_VERSION,
    error_counts,
    extract_json_text,
    normalize_transcript,
    read_hypothesis,
    score,
)


def extract_segment_text(serialized: str) -> str:
    """Extract ordered segment text from WhisperX-style result JSON."""

    return extract_json_text(serialized, "whisperx-json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate normalized lexical WER and CER without printing text."
    )
    parser.add_argument("reference", type=Path, help="manually verified UTF-8 text")
    parser.add_argument(
        "hypothesis",
        type=Path,
        help="candidate UTF-8 text or WhisperX-style JSON",
    )
    parser.add_argument(
        "--hypothesis-format",
        choices=("auto", "text", "whisperx-json"),
        default="auto",
        help="input format; auto treats a .json hypothesis as WhisperX JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON report path; the report is always printed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hypothesis_text, hypothesis_format = read_hypothesis(
        args.hypothesis, args.hypothesis_format
    )
    report = {
        "reference_file": args.reference.name,
        "hypothesis_file": args.hypothesis.name,
        "hypothesis_format": hypothesis_format,
        **score(
            args.reference.read_text(encoding="utf-8"),
            hypothesis_text,
        ),
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
