"""Tests for deterministic sequential Phase 6 batch orchestration."""

from pathlib import Path

import pytest

from ewp_transcripts import application
from ewp_transcripts.application import TranscriptionOutcome, transcribe_batch
from ewp_transcripts.config import ApplicationConfig, DiarizationConfig, RuntimeConfig
from ewp_transcripts.domain import DiscoveryResult, EpisodeInspection, InspectionResult
from ewp_transcripts.domain.enums import PlanDecision
from ewp_transcripts.domain.errors import SpeechEngineError


def test_batch_continues_in_order_and_summarizes_isolated_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspection = _inspection(tmp_path, "episode-2", "episode-10", "episode-11")
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: inspection)
    calls: list[str] = []

    def run(episode, **kwargs):
        calls.append(episode.job_id)
        if episode.job_id == "episode-10":
            raise SpeechEngineError("controlled batch failure")
        decision = PlanDecision.SKIP if episode.job_id == "episode-11" else PlanDecision.PROCESS
        return TranscriptionOutcome(
            decision=decision,
            job_id=episode.job_id,
            result_path=tmp_path / f"{episode.job_id}_results.json",
        )

    monkeypatch.setattr(application, "_transcribe_episode", run)

    outcome = transcribe_batch(
        inspection.discovery.input_path,
        config=_config(tmp_path, continue_after_error=True),
        output_directory=tmp_path / "output",
    )

    assert calls == ["episode-2", "episode-10", "episode-11"]
    assert [job.status for job in outcome.jobs] == ["completed", "failed", "skipped"]
    assert outcome.completed == 1
    assert outcome.failed == 1
    assert outcome.skipped == 1
    assert outcome.stopped_early is False
    assert outcome.jobs[1].failure_code == "SPEECH_ENGINE_ERROR"
    assert outcome.jobs[1].failure_message == "controlled batch failure"


def test_batch_stop_policy_leaves_later_jobs_unstarted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspection = _inspection(tmp_path, "first", "broken", "never-started")
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: inspection)
    calls: list[str] = []

    def run(episode, **kwargs):
        calls.append(episode.job_id)
        if episode.job_id == "broken":
            raise RuntimeError("private internal detail")
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id=episode.job_id,
            result_path=tmp_path / f"{episode.job_id}_results.json",
        )

    monkeypatch.setattr(application, "_transcribe_episode", run)

    outcome = transcribe_batch(
        inspection.discovery.input_path,
        config=_config(tmp_path, continue_after_error=False),
    )

    assert calls == ["first", "broken"]
    assert [job.job_id for job in outcome.jobs] == ["first", "broken"]
    assert outcome.jobs[1].failure_code == "TRANSCRIPTION_FAILED"
    assert outcome.jobs[1].failure_message == "Unexpected transcription failure"
    assert outcome.stopped_early is True


def test_batch_cancellation_stops_queue_and_reports_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspection = _inspection(tmp_path, "cancelled", "never-started")
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: inspection)

    def cancel(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(application, "_transcribe_episode", cancel)

    outcome = transcribe_batch(
        inspection.discovery.input_path,
        config=_config(tmp_path, continue_after_error=True),
    )

    assert [job.job_id for job in outcome.jobs] == ["cancelled"]
    assert outcome.jobs[0].status == "cancelled"
    assert outcome.jobs[0].failure_code == "USER_CANCELLED"
    assert outcome.cancelled == 1
    assert outcome.stopped_early is True


def _config(tmp_path: Path, *, continue_after_error: bool) -> ApplicationConfig:
    return ApplicationConfig(
        diarization=DiarizationConfig(speaker_count=1),
        runtime=RuntimeConfig(
            work_root=tmp_path / "work",
            continue_batch_after_error=continue_after_error,
        ),
    )


def _inspection(tmp_path: Path, *job_ids: str) -> InspectionResult:
    input_path = tmp_path / "input"
    input_path.mkdir()
    episodes = tuple(
        EpisodeInspection.model_construct(
            job_id=job_id,
            episode_signature_sha256=f"{index:x}" * 64,
            duration_ms=1000,
            sample_rate_hz=48000,
            sources=(),
            warnings=(),
        )
        for index, job_id in enumerate(job_ids, start=1)
    )
    return InspectionResult(
        discovery=DiscoveryResult(
            input_path=input_path,
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=episodes,
    )
