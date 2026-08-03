"""Tests for application-level non-mutating dry-run composition."""

from pathlib import Path

from ewp_transcripts import application
from ewp_transcripts.application import dry_run
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain import (
    DiscoveryResult,
    EpisodeInspection,
    InspectionResult,
)
from ewp_transcripts.domain.enums import PlanDecision


def _inspection(input_path: Path) -> InspectionResult:
    episode = EpisodeInspection.model_construct(
        job_id="episode",
        episode_signature_sha256="a" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(),
        warnings=(),
    )
    return InspectionResult(
        discovery=DiscoveryResult(
            input_path=input_path,
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=(episode,),
    )


def test_dry_run_composes_inspection_and_output_planning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    destination = tmp_path / "planned"
    monkeypatch.setattr(application, "inspect_input", lambda *args, **kwargs: _inspection(source))

    result = dry_run(
        source,
        config=ApplicationConfig(),
        output_directory=destination,
    )

    assert result.output_directory == destination
    assert result.language.value == "pl"
    assert result.output_directory.exists() is False
    assert len(result.jobs) == 1
    assert result.jobs[0].decision is PlanDecision.PROCESS
    assert result.jobs[0].outputs
    assert result.jobs[0].outputs.results == destination / "episode_results.json"
