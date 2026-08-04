"""Tests for deterministic word/segment reconciliation with diarization turns."""

from ewp_transcripts.diarization import reconcile_diarization
from ewp_transcripts.domain.canonical import (
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWord,
)
from ewp_transcripts.engines import DiarizationResult, DiarizationTurn


def test_exclusive_turns_assign_words_while_regular_turns_preserve_overlap() -> None:
    transcript = _transcript(
        _segment("seg_1", 0, 1200, _word("word_1", 100, 500), _word("word_2", 900, 1100)),
        _segment("seg_2", 1200, 2000, _word("word_3", 1300, 1800)),
    )
    diarization = DiarizationResult(
        turns=(
            DiarizationTurn(start_ms=0, end_ms=1500, speaker_label="backend-z"),
            DiarizationTurn(start_ms=800, end_ms=2000, speaker_label="backend-a"),
        ),
        exclusive_turns=(
            DiarizationTurn(start_ms=0, end_ms=800, speaker_label="backend-z"),
            DiarizationTurn(start_ms=800, end_ms=2000, speaker_label="backend-a"),
        ),
    )

    result = reconcile_diarization(
        transcript,
        diarization,
        source_id="source_001",
        use_exclusive_for_words=True,
    )

    identities = [
        (speaker.backend_label, speaker.speaker_id, speaker.speaker_label)
        for speaker in result.speakers
    ]
    assert identities == [
        ("backend-z", "speaker_001", "Speaker1"),
        ("backend-a", "speaker_002", "Speaker2"),
    ]
    first, second = result.transcript.segments
    assert [word.speaker_id for word in first.words] == ["speaker_001", "speaker_002"]
    assert first.speaker_id == "speaker_001"
    assert first.overlap is True
    assert first.active_speaker_ids == ("speaker_001", "speaker_002")
    assert second.speaker_id == "speaker_002"
    assert result.warnings == ()


def test_regular_overlap_tie_is_left_unassigned_and_warned() -> None:
    transcript = _transcript(_segment("seg_1", 0, 1000, _word("word_1", 400, 600)))
    diarization = DiarizationResult(
        turns=(
            DiarizationTurn(start_ms=0, end_ms=1000, speaker_label="A"),
            DiarizationTurn(start_ms=0, end_ms=1000, speaker_label="B"),
        )
    )

    result = reconcile_diarization(
        transcript,
        diarization,
        source_id="source_001",
        use_exclusive_for_words=False,
    )

    segment = result.transcript.segments[0]
    assert segment.words[0].speaker_id is None
    assert segment.speaker_id is None
    assert segment.overlap is True
    assert [warning.code for warning in result.warnings] == ["SPEAKER_ASSIGNMENT_AMBIGUOUS"]
    assert result.warnings[0].context == {"affected_words": 1}


def test_uncovered_word_is_left_unassigned_and_warned() -> None:
    transcript = _transcript(_segment("seg_1", 1000, 2000, _word("word_1", 1200, 1500)))

    result = reconcile_diarization(
        transcript,
        DiarizationResult(turns=()),
        source_id="source_001",
        use_exclusive_for_words=True,
    )

    assert result.speakers == ()
    assert result.transcript.segments[0].words[0].speaker_id is None
    assert [warning.code for warning in result.warnings] == ["SPEAKER_ASSIGNMENT_MISSING"]


def _word(word_id: str, start_ms: int, end_ms: int) -> CanonicalWord:
    return CanonicalWord(
        word_id=word_id,
        text=word_id,
        start_ms=start_ms,
        end_ms=end_ms,
        timestamp_source="aligned",
        speaker_id="speaker_001",
    )


def _segment(
    segment_id: str,
    start_ms: int,
    end_ms: int,
    *words: CanonicalWord,
) -> CanonicalSegment:
    return CanonicalSegment(
        segment_id=segment_id,
        start_ms=start_ms,
        end_ms=end_ms,
        text=" ".join(word.text for word in words),
        speaker_id="speaker_001",
        overlap=False,
        active_speaker_ids=("speaker_001",),
        source_ids=("source_001",),
        words=words,
    )


def _transcript(*segments: CanonicalSegment) -> CanonicalTranscript:
    return CanonicalTranscript(language="pl", segments=segments)
