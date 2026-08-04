"""Tests for backend-neutral Phase 8 diarization contracts."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from ewp_transcripts.engines import (
    DiarizationEngine,
    DiarizationResult,
    DiarizationTurn,
    EngineModelInfo,
)


class FakeDiarization:
    model_info = EngineModelInfo(
        role="diarization",
        name="community-1",
        revision="revision",
    )

    def diarize(self, audio_path: Path, *, speaker_count: int | None) -> DiarizationResult:
        assert audio_path.name == "episode.wav"
        assert speaker_count == 2
        return DiarizationResult(
            turns=(
                DiarizationTurn(start_ms=0, end_ms=1500, speaker_label="SPEAKER_00"),
                DiarizationTurn(start_ms=1000, end_ms=2000, speaker_label="SPEAKER_01"),
            ),
            exclusive_turns=(
                DiarizationTurn(start_ms=0, end_ms=1000, speaker_label="SPEAKER_00"),
                DiarizationTurn(start_ms=1000, end_ms=2000, speaker_label="SPEAKER_01"),
            ),
        )

    def close(self) -> None:
        return None


def test_protocol_supports_overlapping_and_exclusive_timelines() -> None:
    engine: DiarizationEngine = FakeDiarization()

    result = engine.diarize(Path("episode.wav"), speaker_count=2)

    assert result.turns[0].end_ms > result.turns[1].start_ms
    assert result.exclusive_turns is not None
    assert result.exclusive_turns[0].end_ms == result.exclusive_turns[1].start_ms


def test_contract_rejects_unsorted_regular_turns() -> None:
    with pytest.raises(ValidationError, match="sorted chronologically"):
        DiarizationResult(
            turns=(
                DiarizationTurn(start_ms=1000, end_ms=2000, speaker_label="SPEAKER_01"),
                DiarizationTurn(start_ms=0, end_ms=500, speaker_label="SPEAKER_00"),
            )
        )


def test_contract_rejects_overlapping_exclusive_turns() -> None:
    with pytest.raises(ValidationError, match="must not overlap"):
        DiarizationResult(
            turns=(),
            exclusive_turns=(
                DiarizationTurn(start_ms=0, end_ms=1100, speaker_label="SPEAKER_00"),
                DiarizationTurn(start_ms=1000, end_ms=2000, speaker_label="SPEAKER_01"),
            ),
        )


def test_importing_contracts_does_not_eagerly_import_ml_libraries() -> None:
    assert "pyannote.audio" not in sys.modules
    assert "torch" not in sys.modules
