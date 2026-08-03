"""Tests for atomic completed-result publication."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from ewp_transcripts.domain import (
    JobOutputPlan,
    JobReservation,
    JobStateRecord,
    PlannedOutputPaths,
)
from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result
from ewp_transcripts.domain.enums import JobStateStatus, PlanDecision
from ewp_transcripts.domain.errors import InvalidJobStateError, OutputReservationError
from ewp_transcripts.state import finalize_job_result

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"
RUN_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
CREATED_AT = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


def test_finalization_publishes_result_and_removes_running_state(tmp_path: Path) -> None:
    reservation = _reservation(tmp_path)
    assert reservation.state_path is not None
    result = _matching_result(reservation)

    final_path = finalize_job_result(reservation, result)

    assert final_path.is_file()
    assert not reservation.state_path.exists()
    assert load_canonical_result(final_path) == result
    assert not list(final_path.parent.glob(".*.tmp"))


def test_identity_mismatch_leaves_running_state_unchanged(tmp_path: Path) -> None:
    reservation = _reservation(tmp_path)
    assert reservation.state_path is not None
    before = reservation.state_path.read_bytes()
    result = _matching_result(reservation).model_copy(update={"job_id": "other"})

    with pytest.raises(InvalidJobStateError, match="does not match"):
        finalize_job_result(reservation, result)

    assert reservation.state_path.read_bytes() == before
    assert reservation.plan.outputs is not None
    assert not reservation.plan.outputs.results.exists()


def test_occupied_final_path_is_not_overwritten(tmp_path: Path) -> None:
    reservation = _reservation(tmp_path)
    assert reservation.state_path is not None
    assert reservation.plan.outputs is not None
    reservation.plan.outputs.results.write_text("keep", encoding="utf-8")
    result = _matching_result(reservation)

    with pytest.raises(OutputReservationError, match="already exists"):
        finalize_job_result(reservation, result)

    assert reservation.plan.outputs.results.read_text(encoding="utf-8") == "keep"
    assert reservation.state_path.exists()


def _reservation(tmp_path: Path) -> JobReservation:
    output = tmp_path / "output"
    output.mkdir()
    outputs = PlannedOutputPaths(
        output_directory=output,
        result_version=1,
        results=output / "episode_results.json",
        partial_results=output / "episode_results.partial.json",
        failed_results=output / "episode_results.failed.json",
    )
    plan = JobOutputPlan(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        decision=PlanDecision.PROCESS,
        outputs=outputs,
    )
    state = JobStateRecord(
        application_version="0.1.0",
        run_id=RUN_ID,
        job_id="episode",
        episode_signature_sha256="b" * 64,
        result_version=1,
        status=JobStateStatus.RUNNING,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )
    outputs.partial_results.write_text(state.model_dump_json(), encoding="utf-8")
    return JobReservation(plan=plan, state=state, state_path=outputs.partial_results)


def _matching_result(reservation: JobReservation) -> CanonicalResult:
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
