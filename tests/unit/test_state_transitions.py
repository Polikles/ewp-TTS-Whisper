"""Tests for verified running-to-failed/cancelled transitions."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import EpisodeInspection
from ewp_transcripts.domain.enums import JobStateStatus
from ewp_transcripts.domain.errors import InvalidJobStateError
from ewp_transcripts.state import reserve_job, transition_job_state

RUN_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def _inspection() -> EpisodeInspection:
    return EpisodeInspection.model_construct(
        job_id="episode",
        episode_signature_sha256="a" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(),
        warnings=(),
    )


@pytest.mark.parametrize("status", [JobStateStatus.FAILED, JobStateStatus.CANCELLED])
def test_transition_publishes_terminal_state_and_removes_running(
    tmp_path: Path,
    status: JobStateStatus,
) -> None:
    reservation = reserve_job(
        _inspection(),
        output_directory=tmp_path,
        run_id=RUN_ID,
        force=False,
        config=OutputsConfig(),
    )

    transitioned = transition_job_state(
        reservation,
        status=status,
        failure_code="CONTROLLED_TEST",
        failure_message="Controlled failure without transcript content.",
    )

    assert transitioned.status is status
    assert reservation.state_path and not reservation.state_path.exists()
    payload = json.loads((tmp_path / "episode_results.failed.json").read_text(encoding="utf-8"))
    assert payload["status"] == status.value
    assert payload["failure_code"] == "CONTROLLED_TEST"


def test_tampered_running_identity_is_rejected_without_terminal_write(tmp_path: Path) -> None:
    reservation = reserve_job(
        _inspection(),
        output_directory=tmp_path,
        run_id=RUN_ID,
        force=False,
        config=OutputsConfig(),
    )
    assert reservation.state_path
    payload = json.loads(reservation.state_path.read_text(encoding="utf-8"))
    payload["episode_signature_sha256"] = "b" * 64
    reservation.state_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidJobStateError, match="does not match"):
        transition_job_state(
            reservation,
            status=JobStateStatus.FAILED,
            failure_code="CONTROLLED_TEST",
            failure_message="Controlled failure.",
        )

    assert not (tmp_path / "episode_results.failed.json").exists()


def test_corrupt_partial_result_is_rejected_without_terminal_write(tmp_path: Path) -> None:
    reservation = reserve_job(
        _inspection(),
        output_directory=tmp_path,
        run_id=RUN_ID,
        force=False,
        config=OutputsConfig(),
    )
    assert reservation.state_path
    reservation.state_path.write_text("{truncated", encoding="utf-8")

    with pytest.raises(InvalidJobStateError, match="Cannot read trusted job state"):
        transition_job_state(
            reservation,
            status=JobStateStatus.FAILED,
            failure_code="CONTROLLED_TEST",
            failure_message="Controlled failure.",
        )

    assert reservation.state_path.read_text(encoding="utf-8") == "{truncated"
    assert not (tmp_path / "episode_results.failed.json").exists()
    assert not (tmp_path / "episode_results.json").exists()


def test_non_processing_reservation_cannot_transition() -> None:
    from ewp_transcripts.domain import JobOutputPlan, JobReservation
    from ewp_transcripts.domain.enums import PlanDecision

    plan = JobOutputPlan.model_construct(
        job_id="episode",
        episode_signature_sha256="a" * 64,
        decision=PlanDecision.SKIP,
        outputs=None,
        existing_result=None,
        warnings=(),
    )
    reservation = JobReservation.model_construct(plan=plan, state=None, state_path=None)

    with pytest.raises(InvalidJobStateError, match="processing reservation"):
        transition_job_state(
            reservation,
            status=JobStateStatus.FAILED,
            failure_code="CONTROLLED_TEST",
            failure_message="Controlled failure.",
        )
