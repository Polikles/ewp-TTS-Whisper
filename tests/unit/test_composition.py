"""Tests for deterministic independent-stream timeline composition."""

import pytest

from ewp_transcripts.composition import merge_speaker_transcripts
from ewp_transcripts.domain.canonical import CanonicalSegment, CanonicalTranscript, CanonicalWord
from ewp_transcripts.domain.errors import TranscriptNormalizationError


def test_merges_chronologically_marks_overlap_and_reassigns_global_ids() -> None:
    first = _transcript(
        "pl",
        _segment("old-a", "same words", 0, 1000, "speaker_001", "source_001"),
        _segment("old-b", "after", 1200, 1800, "speaker_001", "source_001"),
    )
    second = _transcript(
        "pl",
        _segment("old-a", "same words", 500, 1300, "speaker_002", "source_002"),
    )

    merged = merge_speaker_transcripts((first, second))

    assert [segment.text for segment in merged.segments] == ["same words", "same words", "after"]
    assert [segment.segment_id for segment in merged.segments] == [
        "seg_000001",
        "seg_000002",
        "seg_000003",
    ]
    assert [segment.overlap for segment in merged.segments] == [True, True, True]
    assert [segment.active_speaker_ids for segment in merged.segments] == [
        ("speaker_001", "speaker_002"),
        ("speaker_001", "speaker_002"),
        ("speaker_001", "speaker_002"),
    ]
    assert [word.word_id for segment in merged.segments for word in segment.words] == [
        "word_000001",
        "word_000002",
        "word_000003",
        "word_000004",
        "word_000005",
    ]
    assert [segment.source_ids for segment in merged.segments] == [
        ("source_001",),
        ("source_002",),
        ("source_001",),
    ]


def test_touching_boundaries_are_not_overlap() -> None:
    first = _transcript("pl", _segment("a", "first", 0, 1000, "speaker_001", "source_001"))
    second = _transcript("pl", _segment("b", "second", 1000, 2000, "speaker_002", "source_002"))

    merged = merge_speaker_transcripts((first, second))

    assert all(segment.overlap is False for segment in merged.segments)
    assert [segment.active_speaker_ids for segment in merged.segments] == [
        ("speaker_001",),
        ("speaker_002",),
    ]


def test_rejects_empty_or_mixed_language_composition() -> None:
    with pytest.raises(TranscriptNormalizationError, match="At least one"):
        merge_speaker_transcripts(())

    polish = _transcript("pl", _segment("a", "tekst", 0, 1000, "speaker_001", "source_001"))
    english = _transcript("en", _segment("b", "text", 0, 1000, "speaker_002", "source_002"))
    with pytest.raises(TranscriptNormalizationError, match="incompatible"):
        merge_speaker_transcripts((polish, english))


def _transcript(language: str, *segments: CanonicalSegment) -> CanonicalTranscript:
    return CanonicalTranscript(language=language, segments=segments)


def _segment(
    segment_id: str,
    text: str,
    start_ms: int,
    end_ms: int,
    speaker_id: str,
    source_id: str,
) -> CanonicalSegment:
    tokens = text.split()
    span = end_ms - start_ms
    words = tuple(
        CanonicalWord(
            word_id=f"word_{index:06d}",
            text=token,
            start_ms=start_ms + span * (index - 1) // len(tokens),
            end_ms=start_ms + span * index // len(tokens),
            timestamp_source="aligned",
            speaker_id=speaker_id,
        )
        for index, token in enumerate(tokens, start=1)
    )
    return CanonicalSegment(
        segment_id=segment_id,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        speaker_id=speaker_id,
        overlap=False,
        active_speaker_ids=(speaker_id,),
        source_ids=(source_id,),
        words=words,
    )
