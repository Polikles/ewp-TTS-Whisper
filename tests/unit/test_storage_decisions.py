"""Tests for read-only process, skip, and version decisions."""

from pathlib import Path

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import EpisodeInspection, ExistingResult, WarningCode
from ewp_transcripts.domain.enums import PlanDecision
from ewp_transcripts.storage import plan_job_outputs


def _inspection(signature: str = "a" * 64) -> EpisodeInspection:
    return EpisodeInspection.model_construct(
        job_id="episode",
        episode_signature_sha256=signature,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(),
        warnings=(),
    )


def _existing(tmp_path: Path, *, signature: str, version: int = 1) -> ExistingResult:
    suffix = "" if version == 1 else f"_v{version:03d}"
    return ExistingResult(
        path=tmp_path / f"episode_results{suffix}.json",
        job_id="episode",
        episode_signature_sha256=signature,
        result_version=version,
    )


def test_same_signature_skips_without_force(tmp_path: Path) -> None:
    existing = _existing(tmp_path, signature="a" * 64)

    plan = plan_job_outputs(
        _inspection(),
        output_directory=tmp_path,
        existing_results=(existing,),
        force=False,
        config=OutputsConfig(),
    )

    assert plan.decision is PlanDecision.SKIP
    assert plan.outputs is None
    assert plan.existing_result == existing
    assert [warning.code for warning in plan.warnings] == [WarningCode.EXISTING_RESULT_SKIPPED]


def test_force_allocates_next_version_for_same_signature(tmp_path: Path) -> None:
    existing = _existing(tmp_path, signature="a" * 64)

    plan = plan_job_outputs(
        _inspection(),
        output_directory=tmp_path,
        existing_results=(existing,),
        force=True,
        config=OutputsConfig(),
    )

    assert plan.decision is PlanDecision.PROCESS
    assert plan.outputs and plan.outputs.result_version == 2
    assert plan.outputs.results.name == "episode_results_v002.json"


def test_existing_v002_and_occupied_v003_allocate_v004(tmp_path: Path) -> None:
    existing = _existing(tmp_path, signature="a" * 64, version=2)
    (tmp_path / "episode_results_v003.partial.json").write_text("active", encoding="utf-8")

    plan = plan_job_outputs(
        _inspection(),
        output_directory=tmp_path,
        existing_results=(existing,),
        force=True,
        config=OutputsConfig(),
    )

    assert plan.outputs and plan.outputs.result_version == 4


def test_same_job_with_changed_signature_processes_new_version(tmp_path: Path) -> None:
    existing = _existing(tmp_path, signature="a" * 64)

    plan = plan_job_outputs(
        _inspection("b" * 64),
        output_directory=tmp_path,
        existing_results=(existing,),
        force=False,
        config=OutputsConfig(generate_segments_json=True),
    )

    assert plan.decision is PlanDecision.PROCESS
    assert plan.outputs and plan.outputs.result_version == 2
    assert plan.outputs.transcript and plan.outputs.transcript.name.endswith("_v002.txt")
    assert plan.outputs.segments and plan.outputs.segments.name.endswith("_v002.json")
    assert [warning.code for warning in plan.warnings] == [WarningCode.SOURCE_NAME_COLLISION]


def test_new_job_uses_version_one(tmp_path: Path) -> None:
    plan = plan_job_outputs(
        _inspection(),
        output_directory=tmp_path,
        existing_results=(),
        force=False,
        config=OutputsConfig(),
    )

    assert plan.outputs and plan.outputs.result_version == 1
    assert plan.outputs.results.name == "episode_results.json"
