"""Tests for the non-mutating dry-run CLI adapter."""

from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.domain import (
    DiscoveryResult,
    DryRunResult,
    EpisodeInspection,
    InspectionResult,
    JobOutputPlan,
    PlannedOutputPaths,
)
from ewp_transcripts.domain.enums import LanguageMode, PlanDecision

runner = CliRunner()


def _result(tmp_path: Path) -> DryRunResult:
    episode = EpisodeInspection.model_construct(
        job_id="episode",
        episode_signature_sha256="a" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(),
        warnings=(),
    )
    inspection = InspectionResult(
        discovery=DiscoveryResult(
            input_path=tmp_path / "episode.wav",
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=(episode,),
    )
    outputs = PlannedOutputPaths(
        output_directory=tmp_path,
        result_version=1,
        results=tmp_path / "episode_results.json",
        partial_results=tmp_path / "episode_results.partial.json",
        failed_results=tmp_path / "episode_results.failed.json",
        transcript=tmp_path / "episode_transcript.txt",
        subtitles_srt=tmp_path / "episode_subtitles.srt",
        subtitles_vtt=tmp_path / "episode_subtitles.vtt",
    )
    job = JobOutputPlan(
        job_id="episode",
        episode_signature_sha256="a" * 64,
        decision=PlanDecision.PROCESS,
        outputs=outputs,
    )
    return DryRunResult.model_construct(
        inspection=inspection,
        output_directory=tmp_path,
        language=LanguageMode.POLISH,
        jobs=(job,),
    )


def test_dry_run_human_output_lists_decision_and_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("ewp_transcripts.cli.dry_run", lambda *args, **kwargs: _result(tmp_path))

    result = runner.invoke(app, ["dry-run", str(tmp_path / "episode.wav")])

    assert result.exit_code == 0
    assert "PROCESS episode" in result.stdout
    assert "language: pl" in result.stdout
    assert "result version: 1" in result.stdout
    assert "episode_results.json" in result.stdout


def test_dry_run_json_passes_storage_options(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def dry_run_stub(*args, **kwargs):
        captured.update(kwargs)
        return _result(tmp_path)

    monkeypatch.setattr("ewp_transcripts.cli.dry_run", dry_run_stub)
    destination = tmp_path / "outputs"

    result = runner.invoke(
        app,
        [
            "dry-run",
            str(tmp_path / "episode.wav"),
            "--output-dir",
            str(destination),
            "--force",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"decision": "process"' in result.stdout
    assert captured["output_directory"] == destination
    assert captured["force"] is True
