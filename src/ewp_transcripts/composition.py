"""Deterministic shared-timeline composition for independent speaker streams."""

from __future__ import annotations

from ewp_transcripts.domain.canonical import CanonicalSegment, CanonicalTranscript
from ewp_transcripts.domain.errors import TranscriptNormalizationError


def merge_speaker_transcripts(
    transcripts: tuple[CanonicalTranscript, ...],
) -> CanonicalTranscript:
    """Merge independent canonical streams without deduplicating spoken content."""

    if not transcripts:
        raise TranscriptNormalizationError("At least one transcript is required for composition")
    languages = {transcript.language for transcript in transcripts}
    if len(languages) != 1:
        raise TranscriptNormalizationError("Speaker transcripts use incompatible languages")

    indexed = [
        (stream_index, segment_index, segment)
        for stream_index, transcript in enumerate(transcripts)
        for segment_index, segment in enumerate(transcript.segments)
    ]
    indexed.sort(
        key=lambda item: (
            item[2].start_ms,
            item[2].end_ms,
            item[0],
            item[1],
        )
    )
    speaker_order = _speaker_order(transcripts)
    composed: list[CanonicalSegment] = []
    word_number = 1
    for segment_number, (_, _, segment) in enumerate(indexed, start=1):
        active = {
            other.speaker_id
            for _, _, other in indexed
            if other.speaker_id is not None and _intersects(segment, other)
        }
        if segment.speaker_id is not None:
            active.add(segment.speaker_id)
        active_speakers = tuple(
            sorted(
                active, key=lambda speaker_id: (speaker_order.get(speaker_id, 10**9), speaker_id)
            )
        )
        words = []
        for word in segment.words:
            words.append(word.model_copy(update={"word_id": f"word_{word_number:06d}"}))
            word_number += 1
        composed.append(
            segment.model_copy(
                update={
                    "segment_id": f"seg_{segment_number:06d}",
                    "overlap": len(active_speakers) > 1,
                    "active_speaker_ids": active_speakers,
                    "words": tuple(words),
                }
            )
        )
    return CanonicalTranscript(language=languages.pop(), segments=tuple(composed))


def _speaker_order(transcripts: tuple[CanonicalTranscript, ...]) -> dict[str, int]:
    order: dict[str, int] = {}
    for transcript in transcripts:
        for segment in transcript.segments:
            if segment.speaker_id is not None and segment.speaker_id not in order:
                order[segment.speaker_id] = len(order)
    return order


def _intersects(left: CanonicalSegment, right: CanonicalSegment) -> bool:
    if left is right:
        return True
    return left.start_ms < right.end_ms and right.start_ms < left.end_ms
