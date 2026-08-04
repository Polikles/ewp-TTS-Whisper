"""Dependency-free lexical transcript quality metrics."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path

NORMALIZATION_VERSION = "ewp-phase0-lexical-v1"


@dataclass(frozen=True, slots=True)
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
    """Normalize formatting while preserving lexical distinctions."""

    normalized = unicodedata.normalize("NFC", text).casefold()
    characters = [
        " " if character.isspace() or unicodedata.category(character).startswith("P") else character
        for character in normalized
    ]
    return " ".join("".join(characters).split())


def error_counts[Item](reference: Sequence[Item], hypothesis: Sequence[Item]) -> ErrorCounts:
    """Return deterministic Levenshtein substitution/deletion/insertion counts."""

    previous = [(index, 0, index, 0) for index in range(len(reference) + 1)]
    for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
        current = [(hypothesis_index, 0, 0, hypothesis_index)]
        for reference_index, reference_item in enumerate(reference, start=1):
            if reference_item == hypothesis_item:
                current.append(previous[reference_index - 1])
                continue
            diagonal = previous[reference_index - 1]
            substitution = (diagonal[0] + 1, diagonal[1] + 1, diagonal[2], diagonal[3])
            left = current[reference_index - 1]
            deletion = (left[0] + 1, left[1], left[2] + 1, left[3])
            above = previous[reference_index]
            insertion = (above[0] + 1, above[1], above[2], above[3] + 1)
            current.append(
                min(
                    (substitution, deletion, insertion),
                    key=lambda value: (value[0], value[2] + value[3], value[3]),
                )
            )
        previous = current
    _, substitutions, deletions, insertions = previous[-1]
    return ErrorCounts(substitutions, deletions, insertions, len(reference))


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
        "character_errors": asdict(character_counts) | {"errors": character_counts.errors},
        "hypothesis_words": len(hypothesis.split()),
        "hypothesis_characters": len(hypothesis),
    }


def extract_json_text(serialized: str, hypothesis_format: str) -> str:
    """Extract ordered segment text from a supported JSON result."""

    document = json.loads(serialized)
    if not isinstance(document, dict):
        raise ValueError("Hypothesis JSON must contain an object")
    if hypothesis_format == "canonical-json":
        transcript = document.get("transcript")
        segments = transcript.get("segments") if isinstance(transcript, dict) else None
    else:
        segments = document.get("segments")
    if not isinstance(segments, list):
        raise ValueError("Hypothesis JSON must contain a 'segments' list")
    text_parts: list[str] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
            raise ValueError(f"Hypothesis segment {index} must contain string 'text'")
        text_parts.append(segment["text"])
    return " ".join(text_parts)


def read_hypothesis(path: Path, hypothesis_format: str) -> tuple[str, str]:
    """Read text or extract segment text without exposing metadata to the scorer."""

    serialized = path.read_text(encoding="utf-8")
    selected = hypothesis_format
    if selected == "auto":
        if path.suffix.casefold() != ".json":
            selected = "text"
        else:
            document = json.loads(serialized)
            selected = (
                "canonical-json"
                if isinstance(document, dict) and isinstance(document.get("transcript"), dict)
                else "whisperx-json"
            )
    if selected in {"whisperx-json", "canonical-json"}:
        return extract_json_text(serialized, selected), selected
    if selected != "text":
        raise ValueError(f"Unsupported hypothesis format: {selected}")
    return serialized, selected


def word_error_diff(reference_text: str, hypothesis_text: str) -> tuple[str, ...]:
    """Return error-only normalized word operations for human review."""

    reference = normalize_transcript(reference_text).split()
    hypothesis = normalize_transcript(hypothesis_text).split()
    operations: list[str] = []
    matcher = SequenceMatcher(a=reference, b=hypothesis, autojunk=False)
    for operation, ref_start, ref_end, hyp_start, hyp_end in matcher.get_opcodes():
        if operation == "equal":
            continue
        reference_block = reference[ref_start:ref_end]
        hypothesis_block = hypothesis[hyp_start:hyp_end]
        paired = min(len(reference_block), len(hypothesis_block))
        operations.extend(
            f"~ {reference_block[index]} -> {hypothesis_block[index]}" for index in range(paired)
        )
        operations.extend(f"- {word}" for word in reference_block[paired:])
        operations.extend(f"+ {word}" for word in hypothesis_block[paired:])
    return tuple(operations)
