"""Tests for strict backend-neutral speech-engine contracts."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from ewp_transcripts.engines import (
    AlignedSegment,
    AlignedTranscript,
    AlignedWord,
    EngineModelInfo,
    TranscriptionDraft,
    TranscriptionSegment,
)


def test_backend_neutral_transcript_models_accept_missing_word_timestamps() -> None:
    draft = TranscriptionDraft(
        language="pl",
        segments=(TranscriptionSegment(text="Dzień dobry.", start_ms=100, end_ms=900),),
    )
    aligned = AlignedTranscript(
        language="pl",
        segments=(
            AlignedSegment(
                text="Dzień dobry.",
                start_ms=100,
                end_ms=900,
                words=(
                    AlignedWord(text="Dzień", start_ms=100, end_ms=400, confidence=0.98),
                    AlignedWord(text="dobry."),
                ),
            ),
        ),
    )

    assert draft.segments[0].text == aligned.segments[0].text
    assert aligned.segments[0].words[1].start_ms is None
    assert "torch" not in sys.modules
    assert "whisperx" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_model_metadata_preserves_exact_local_revision_and_versions() -> None:
    info = EngineModelInfo(
        role="asr",
        name="large-v2",
        revision="f0fe81560cb8b68660e564f55dd99207059c092e",
        local_path=Path("/models/large-v2"),
        library_versions={"whisperx": "3.8.6", "torch": "2.8.0+cu128"},
    )

    assert info.local_path == Path("/models/large-v2")
    assert info.library_versions["whisperx"] == "3.8.6"


@pytest.mark.parametrize(
    "segment",
    [
        TranscriptionSegment.model_construct(text="bad", start_ms=200, end_ms=100),
        AlignedSegment.model_construct(text="bad", start_ms=200, end_ms=100, words=()),
    ],
)
def test_transcripts_reject_invalid_or_unsorted_segments(segment: object) -> None:
    with pytest.raises(ValidationError):
        if isinstance(segment, TranscriptionSegment):
            TranscriptionDraft.model_validate(
                {
                    "language": "pl",
                    "segments": (
                        {"text": "later", "start_ms": 500, "end_ms": 600},
                        {"text": "earlier", "start_ms": 100, "end_ms": 200},
                    ),
                }
            )
        else:
            AlignedTranscript.model_validate(
                {
                    "language": "pl",
                    "segments": ({"text": "bad", "start_ms": 200, "end_ms": 100, "words": ()},),
                }
            )


def test_aligned_word_must_fit_inside_segment() -> None:
    with pytest.raises(ValidationError, match="starts before"):
        AlignedSegment(
            text="word",
            start_ms=100,
            end_ms=200,
            words=(AlignedWord(text="word", start_ms=50, end_ms=150),),
        )
