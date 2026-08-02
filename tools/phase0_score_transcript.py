#!/usr/bin/env python3
"""Score a hypothesis transcript against a manually verified reference.

This Phase 0 utility deliberately evaluates lexical content rather than
formatting. It never prints transcript text.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence, TypeVar
import unicodedata


NORMALIZATION_VERSION = "ewp-phase0-lexical-v1"
Item = TypeVar("Item")


@dataclass(frozen=True)
class ErrorCounts:
    substitutions: int
    deletions: int
    insertions: int
    reference_units: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float:
        if self.reference_units == 0:
            raise ValueError("Cannot score an empty normalized reference")
        return self.errors / self.reference_units


def normalize_transcript(text: str) -> str:
    """Normalize lexical content while preserving letters, digits, and symbols."""

    normalized = unicodedata.normalize("NFC", text).casefold()
    characters = [
        " " if character.isspace() or unicodedata.category(character).startswith("P")
        else character
        for character in normalized
    ]
    return " ".join("".join(characters).split())


def error_counts(reference: Sequence[Item], hypothesis: Sequence[Item]) -> ErrorCounts:
    """Return deterministic Levenshtein substitution/deletion/insertion counts."""

    # Each cell is (total errors, substitutions, deletions, insertions).
    previous = [(index, 0, index, 0) for index in range(len(reference) + 1)]
    for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
        current = [(hypothesis_index, 0, 0, hypothesis_index)]
        for reference_index, reference_item in enumerate(reference, start=1):
            if reference_item == hypothesis_item:
                current.append(previous[reference_index - 1])
                continue

            diagonal = previous[reference_index - 1]
            substitution = (
                diagonal[0] + 1,
                diagonal[1] + 1,
                diagonal[2],
                diagonal[3],
            )
            left = current[reference_index - 1]
            deletion = (left[0] + 1, left[1], left[2] + 1, left[3])
            above = previous[reference_index]
            insertion = (above[0] + 1, above[1], above[2], above[3] + 1)

            # Prefer substitutions, then deletions, then insertions when several
            # optimal paths have the same total error count.
            current.append(
                min(
                    (substitution, deletion, insertion),
                    key=lambda value: (value[0], value[2] + value[3], value[3]),
                )
            )
        previous = current

    _, substitutions, deletions, insertions = previous[-1]
    return ErrorCounts(
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
        reference_units=len(reference),
    )


def score(reference_text: str, hypothesis_text: str) -> dict[str, object]:
    reference = normalize_transcript(reference_text)
    hypothesis = normalize_transcript(hypothesis_text)
    if not reference:
        raise ValueError("Normalized reference transcript is empty")

    word_counts = error_counts(reference.split(), hypothesis.split())
    character_counts = error_counts(list(reference), list(hypothesis))

    return {
        "normalization": NORMALIZATION_VERSION,
        "wer": round(word_counts.rate, 8),
        "cer": round(character_counts.rate, 8),
        "word_errors": asdict(word_counts) | {"errors": word_counts.errors},
        "character_errors": asdict(character_counts)
        | {"errors": character_counts.errors},
        "hypothesis_words": len(hypothesis.split()),
        "hypothesis_characters": len(hypothesis),
    }


def extract_segment_text(serialized: str) -> str:
    """Extract ordered segment text from WhisperX-style result JSON."""

    document = json.loads(serialized)
    if not isinstance(document, dict) or not isinstance(document.get("segments"), list):
        raise ValueError("Hypothesis JSON must contain a 'segments' list")

    text_parts: list[str] = []
    for index, segment in enumerate(document["segments"]):
        if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
            raise ValueError(f"Hypothesis segment {index} must contain string 'text'")
        text_parts.append(segment["text"])
    return " ".join(text_parts)


def read_hypothesis(path: Path, hypothesis_format: str) -> tuple[str, str]:
    selected_format = hypothesis_format
    if selected_format == "auto":
        selected_format = "whisperx-json" if path.suffix.casefold() == ".json" else "text"

    serialized = path.read_text(encoding="utf-8")
    if selected_format == "whisperx-json":
        return extract_segment_text(serialized), selected_format
    return serialized, selected_format


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
