"""Backend-neutral transcript normalization into canonical domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ewp_transcripts.domain.canonical import (
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWarning,
    CanonicalWord,
)
from ewp_transcripts.domain.enums import WarningCode
from ewp_transcripts.domain.errors import TranscriptNormalizationError
from ewp_transcripts.engines import AlignedSegment, AlignedTranscript, AlignedWord


@dataclass(frozen=True, slots=True)
class NormalizedTranscript:
    transcript: CanonicalTranscript
    warnings: tuple[CanonicalWarning, ...]


@dataclass(frozen=True, slots=True)
class _WordTiming:
    start_ms: int
    end_ms: int
    source: Literal["aligned", "interpolated", "segment_fallback"]


def normalize_single_speaker(
    aligned: AlignedTranscript,
    *,
    speaker_id: str,
    source_id: str,
) -> NormalizedTranscript:
    """Assign one speaker and deterministic fallback timing to an aligned transcript."""

    canonical_segments: list[CanonicalSegment] = []
    word_number = 1
    missing_words = 0
    interpolated_words = 0
    fallback_words = 0

    for segment_number, segment in enumerate(aligned.segments, start=1):
        timings = _word_timings(segment)
        words: list[CanonicalWord] = []
        for word, timing in zip(segment.words, timings, strict=True):
            words.append(
                CanonicalWord(
                    word_id=f"word_{word_number:06d}",
                    text=word.text,
                    start_ms=timing.start_ms,
                    end_ms=timing.end_ms,
                    timestamp_source=timing.source,
                    speaker_id=speaker_id,
                    confidence=word.confidence,
                )
            )
            word_number += 1
            if timing.source != "aligned":
                missing_words += 1
            if timing.source == "interpolated":
                interpolated_words += 1
            elif timing.source == "segment_fallback":
                fallback_words += 1
        canonical_segments.append(
            CanonicalSegment(
                segment_id=f"seg_{segment_number:06d}",
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=segment.text,
                speaker_id=speaker_id,
                overlap=False,
                active_speaker_ids=(speaker_id,),
                source_ids=(source_id,),
                confidence=segment.confidence,
                words=tuple(words),
            )
        )

    warnings: list[CanonicalWarning] = []
    if missing_words:
        warnings.append(
            CanonicalWarning(
                code=WarningCode.WORD_ALIGNMENT_MISSING.value,
                severity="warning",
                message="Some words lacked complete alignment timestamps.",
                stage="align",
                source_id=source_id,
                context={
                    "affected_words": missing_words,
                    "segment_fallback_words": fallback_words,
                },
            )
        )
    if interpolated_words:
        warnings.append(
            CanonicalWarning(
                code=WarningCode.WORD_TIMESTAMP_INTERPOLATED.value,
                severity="warning",
                message="Missing word timestamps were interpolated from neighboring timing.",
                stage="normalize",
                source_id=source_id,
                context={"affected_words": interpolated_words},
            )
        )
    return NormalizedTranscript(
        transcript=CanonicalTranscript(
            language=aligned.language,
            segments=tuple(canonical_segments),
        ),
        warnings=tuple(warnings),
    )


def _word_timings(segment: AlignedSegment) -> tuple[_WordTiming, ...]:
    if not segment.words:
        return ()
    aligned_indices = [
        index
        for index, word in enumerate(segment.words)
        if word.start_ms is not None and word.end_ms is not None
    ]
    if not aligned_indices:
        return _allocate(
            segment.words,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            source="segment_fallback",
        )

    result: list[_WordTiming | None] = [None] * len(segment.words)
    for index in aligned_indices:
        word = segment.words[index]
        assert word.start_ms is not None and word.end_ms is not None
        result[index] = _WordTiming(word.start_ms, word.end_ms, "aligned")

    index = 0
    while index < len(segment.words):
        if result[index] is not None:
            index += 1
            continue
        run_start = index
        while index < len(segment.words) and result[index] is None:
            index += 1
        run_end = index
        left = (
            segment.start_ms if run_start == 0 else _required_timing(result[run_start - 1]).end_ms
        )
        right = (
            segment.end_ms
            if run_end == len(segment.words)
            else _required_timing(result[run_end]).start_ms
        )
        if right < left:
            raise TranscriptNormalizationError(
                "Aligned word timing leaves no valid interval for missing words"
            )
        result[run_start:run_end] = _allocate(
            segment.words[run_start:run_end],
            start_ms=left,
            end_ms=right,
            source="interpolated",
        )
    return tuple(_required_timing(item) for item in result)


def _allocate(
    words: tuple[AlignedWord, ...],
    *,
    start_ms: int,
    end_ms: int,
    source: Literal["aligned", "interpolated", "segment_fallback"],
) -> tuple[_WordTiming, ...]:
    weights = [max(1, len(word.text.strip())) for word in words]
    total_weight = sum(weights)
    span = end_ms - start_ms
    elapsed_weight = 0
    timings: list[_WordTiming] = []
    for weight in weights:
        word_start = start_ms + span * elapsed_weight // total_weight
        elapsed_weight += weight
        word_end = start_ms + span * elapsed_weight // total_weight
        timings.append(_WordTiming(word_start, word_end, source))
    return tuple(timings)


def _required_timing(timing: _WordTiming | None) -> _WordTiming:
    if timing is None:
        raise TranscriptNormalizationError("Internal timestamp interpolation failed")
    return timing
