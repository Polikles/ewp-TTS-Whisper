"""Lightweight timestamped segments derived from canonical results."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from ewp_transcripts.domain.canonical import CanonicalResult, CanonicalSegment


class SegmentExportItem(TypedDict):
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    speaker_id: str | None
    overlap: bool
    active_speaker_ids: list[str]
    word_ids: list[str]


def render_segments_json(
    result: CanonicalResult,
    *,
    results_file: str | Path,
    results_sha256: str,
    generated_at: datetime,
    include_words: bool = True,
    revision_file: str | Path | None = None,
    revision_number: int | None = None,
) -> str:
    """Render deterministic speaker-turn JSON without reading source media."""

    if re.fullmatch(r"[a-f0-9]{64}", results_sha256) is None:
        raise ValueError("results_sha256 must be a lowercase hexadecimal SHA-256")
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    turns = _speaker_turns(result.transcript.segments, include_words=include_words)
    derived_from: dict[str, object] = {
        "results_file": Path(results_file).name,
        "results_sha256": results_sha256,
        "results_schema_version": result.schema_version,
    }
    if revision_file is not None:
        derived_from["revision_file"] = Path(revision_file).name
        derived_from["revision_number"] = revision_number
    document = {
        "schema_version": "1.0",
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "job_id": result.job_id,
        "derived_from": derived_from,
        "segmentation": {
            "mode": "speaker_turn",
            "include_words": include_words,
        },
        "speakers": [
            {
                "speaker_id": speaker.speaker_id,
                "speaker_label": speaker.speaker_label,
            }
            for speaker in result.speakers
        ],
        "segments": turns,
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def _speaker_turns(
    segments: tuple[CanonicalSegment, ...], *, include_words: bool
) -> list[SegmentExportItem]:
    turns: list[SegmentExportItem] = []
    for segment in segments:
        word_ids = [word.word_id for word in segment.words] if include_words else []
        if turns and _same_turn(turns[-1], segment):
            turn = turns[-1]
            turn["end_ms"] = segment.end_ms
            turn["text"] = " ".join((turn["text"].rstrip(), segment.text.lstrip()))
            turn["word_ids"].extend(word_ids)
            continue
        turns.append(
            {
                "segment_id": f"turn_{len(turns) + 1:06d}",
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "text": segment.text.strip(),
                "speaker_id": segment.speaker_id,
                "overlap": segment.overlap,
                "active_speaker_ids": list(segment.active_speaker_ids),
                "word_ids": word_ids,
            }
        )
    return turns


def _same_turn(turn: SegmentExportItem, segment: CanonicalSegment) -> bool:
    return (
        turn["speaker_id"] == segment.speaker_id
        and turn["overlap"] == segment.overlap
        and turn["active_speaker_ids"] == list(segment.active_speaker_ids)
    )
