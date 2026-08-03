"""Tests for the complete Phase 5 application lifecycle without ML models."""

from pathlib import Path

import pytest

from ewp_transcripts import application
from ewp_transcripts.application import transcribe_one
from ewp_transcripts.config import ApplicationConfig, DiarizationConfig, RuntimeConfig
from ewp_transcripts.domain import (
    AudioStream,
    ChannelClassification,
    DiscoveryResult,
    EpisodeInspection,
    InspectedSource,
    InspectionResult,
    SourceFingerprint,
    load_canonical_result,
)
from ewp_transcripts.domain.enums import ChannelMode, PlanDecision
from ewp_transcripts.domain.errors import SpeechEngineError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"


def test_transcribe_publishes_exports_cleans_workspace_and_then_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspection = _inspection(tmp_path)
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: inspection)
    calls = 0

    def pipeline(episode, reservation, workspace, **kwargs):
        nonlocal calls
        calls += 1
        assert workspace.path.is_dir()
        return _matching_result(reservation)

    monkeypatch.setattr(application, "run_single_speaker_pipeline", pipeline)
    config = _config(tmp_path)
    destination = tmp_path / "output"

    first = transcribe_one(
        inspection.discovery.input_path,
        config=config,
        output_directory=destination,
    )
    assert first.exports is not None
    missing_export = next(path for path in first.exports.written if path.suffix == ".srt")
    missing_export.unlink()
    second = transcribe_one(
        inspection.discovery.input_path,
        config=config,
        output_directory=destination,
    )

    assert first.decision is PlanDecision.PROCESS
    assert first.result_path.is_file()
    assert {path.suffix for path in first.exports.written} == {".txt", ".srt", ".vtt"}
    assert second.decision is PlanDecision.SKIP
    assert second.result_path == first.result_path
    assert second.exports is not None
    assert second.exports.written == (missing_export,)
    assert len(second.exports.skipped) == 2
    assert calls == 1
    assert not list(config.runtime.work_root.glob("*/*"))
    assert not list(destination.glob("*.partial.json"))


def test_transcribe_failure_publishes_failed_state_and_retains_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspection = _inspection(tmp_path)
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: inspection)

    def fail(*args, **kwargs):
        raise SpeechEngineError("sanitized engine failure")

    monkeypatch.setattr(application, "run_single_speaker_pipeline", fail)
    config = _config(tmp_path)
    destination = tmp_path / "output"

    with pytest.raises(SpeechEngineError, match="sanitized engine failure"):
        transcribe_one(
            inspection.discovery.input_path,
            config=config,
            output_directory=destination,
        )

    failed_paths = list(destination.glob("*.failed.json"))
    assert len(failed_paths) == 1
    payload = failed_paths[0].read_text(encoding="utf-8")
    assert '"failure_code":"SPEECH_ENGINE_ERROR"' in payload.replace(" ", "")
    assert "sanitized engine failure" in payload
    assert not list(destination.glob("*.partial.json"))
    assert len(list(config.runtime.work_root.glob("*/*"))) == 1


def _config(tmp_path: Path) -> ApplicationConfig:
    return ApplicationConfig(
        diarization=DiarizationConfig(speaker_count=1),
        runtime=RuntimeConfig(work_root=tmp_path / "work"),
    )


def _inspection(tmp_path: Path) -> InspectionResult:
    source_path = tmp_path / "episode.wav"
    source_path.write_bytes(b"source")
    source = InspectedSource(
        fingerprint=SourceFingerprint(
            path=source_path,
            filename=source_path.name,
            size_bytes=6,
            sha256="a" * 64,
        ),
        stream=AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=48000,
            channels=1,
        ),
        duration_ms=1000,
        channel_mode=ChannelMode.MONO,
        channel_classification=ChannelClassification(
            original_channels=1,
            detected_mode=ChannelMode.MONO,
            processing_mode=ChannelMode.MONO,
            selected_channel_index=0,
        ),
        speaker_id="speaker_001",
    )
    episode = EpisodeInspection(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(source,),
    )
    return InspectionResult(
        discovery=DiscoveryResult(
            input_path=source_path,
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=(episode,),
    )


def _matching_result(reservation):
    assert reservation.state is not None
    base = load_canonical_result(EXAMPLE_PATH)
    episode = base.episode.model_copy(
        update={
            "episode_id": reservation.state.job_id,
            "episode_signature_sha256": reservation.state.episode_signature_sha256,
        }
    )
    return base.model_copy(
        update={
            "run_id": reservation.state.run_id,
            "job_id": reservation.state.job_id,
            "result_version": reservation.state.result_version,
            "episode": episode,
        }
    )
