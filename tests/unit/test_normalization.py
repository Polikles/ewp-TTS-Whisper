"""Tests for canonical single-speaker transcript normalization."""

import pytest

from ewp_transcripts.domain.errors import TranscriptNormalizationError
from ewp_transcripts.engines import AlignedSegment, AlignedTranscript, AlignedWord
from ewp_transcripts.normalization import normalize_single_speaker


def test_preserves_aligned_words_and_assigns_stable_ids() -> None:
    result = normalize_single_speaker(
        _transcript(
            AlignedWord(text="Dzień", start_ms=100, end_ms=300, confidence=0.9),
            AlignedWord(text="dobry.", start_ms=320, end_ms=700, confidence=0.8),
        ),
        speaker_id="speaker_001",
        source_id="source_001",
    )

    segment = result.transcript.segments[0]
    assert segment.segment_id == "seg_000001"
    assert [word.word_id for word in segment.words] == ["word_000001", "word_000002"]
    assert [word.timestamp_source for word in segment.words] == ["aligned", "aligned"]
    assert all(word.speaker_id == "speaker_001" for word in segment.words)
    assert result.warnings == ()


def test_interpolates_missing_word_between_aligned_neighbors() -> None:
    result = normalize_single_speaker(
        _transcript(
            AlignedWord(text="pierwsze", start_ms=100, end_ms=300),
            AlignedWord(text="brakujące"),
            AlignedWord(text="trzecie", start_ms=600, end_ms=800),
        ),
        speaker_id="speaker_001",
        source_id="source_001",
    )

    missing = result.transcript.segments[0].words[1]
    assert (missing.start_ms, missing.end_ms, missing.timestamp_source) == (
        300,
        600,
        "interpolated",
    )
    assert [warning.code for warning in result.warnings] == [
        "WORD_ALIGNMENT_MISSING",
        "WORD_TIMESTAMP_INTERPOLATED",
    ]


def test_distributes_fully_untimed_segment_by_word_length() -> None:
    result = normalize_single_speaker(
        _transcript(AlignedWord(text="a"), AlignedWord(text="bbb")),
        speaker_id="speaker_001",
        source_id="source_001",
    )

    words = result.transcript.segments[0].words
    assert [(word.start_ms, word.end_ms) for word in words] == [(100, 300), (300, 900)]
    assert all(word.timestamp_source == "segment_fallback" for word in words)
    assert result.warnings[0].context == {
        "affected_words": 2,
        "segment_fallback_words": 2,
    }


def test_rejects_impossible_interpolation_interval() -> None:
    transcript = AlignedTranscript(
        language="pl",
        segments=(
            AlignedSegment(
                text="bad timing",
                start_ms=0,
                end_ms=1000,
                words=(
                    AlignedWord(text="first", start_ms=400, end_ms=700),
                    AlignedWord(text="missing"),
                    AlignedWord(text="last", start_ms=600, end_ms=900),
                ),
            ),
        ),
    )

    with pytest.raises(TranscriptNormalizationError, match="no valid interval"):
        normalize_single_speaker(
            transcript,
            speaker_id="speaker_001",
            source_id="source_001",
        )


def _transcript(*words: AlignedWord) -> AlignedTranscript:
    return AlignedTranscript(
        language="pl",
        segments=(
            AlignedSegment(
                text=" ".join(word.text for word in words),
                start_ms=100,
                end_ms=900,
                words=words,
            ),
        ),
    )
