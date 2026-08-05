"""Tests for locked atomic running-state reservation."""

import errno
import json
from pathlib import Path
from uuid import UUID

import pytest

import ewp_transcripts.state as state_module
from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import EpisodeInspection
from ewp_transcripts.domain.enums import JobStateStatus, PlanDecision
from ewp_transcripts.domain.errors import OutputReservationError
from ewp_transcripts.state import reserve_job

RUN_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def _inspection(signature: str = "a" * 64) -> EpisodeInspection:
    return EpisodeInspection.model_construct(
        job_id="episode",
        episode_signature_sha256=signature,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(),
        warnings=(),
    )


def _completed(path: Path, signature: str = "a" * 64) -> None:
    path.write_text(
        json.dumps(
            {
                "job_id": "episode",
                "status": "completed",
                "result_version": 1,
                "episode": {"episode_signature_sha256": signature},
            }
        ),
        encoding="utf-8",
    )


def test_process_reservation_publishes_complete_running_json(tmp_path: Path) -> None:
    output_directory = tmp_path / "output"

    reservation = reserve_job(
        _inspection(),
        output_directory=output_directory,
        run_id=RUN_ID,
        force=False,
        config=OutputsConfig(),
    )

    assert reservation.plan.decision is PlanDecision.PROCESS
    assert reservation.state and reservation.state.status is JobStateStatus.RUNNING
    assert reservation.state_path == output_directory / "episode_results.partial.json"
    payload = json.loads(reservation.state_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == str(RUN_ID)
    assert payload["episode_signature_sha256"] == "a" * 64
    assert not list(output_directory.glob("*.tmp"))


def test_duplicate_skip_does_not_publish_running_state(tmp_path: Path) -> None:
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    _completed(output_directory / "episode_results.json")

    reservation = reserve_job(
        _inspection(),
        output_directory=output_directory,
        run_id=RUN_ID,
        force=False,
        config=OutputsConfig(),
    )

    assert reservation.plan.decision is PlanDecision.SKIP
    assert reservation.state is None
    assert reservation.state_path is None
    assert not (output_directory / "episode_results.partial.json").exists()


def test_repeated_forced_reservations_allocate_distinct_versions(tmp_path: Path) -> None:
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    _completed(output_directory / "episode_results.json")

    first = reserve_job(
        _inspection(),
        output_directory=output_directory,
        run_id=RUN_ID,
        force=True,
        config=OutputsConfig(),
    )
    second = reserve_job(
        _inspection(),
        output_directory=output_directory,
        run_id=UUID("223e4567-e89b-12d3-a456-426614174000"),
        force=True,
        config=OutputsConfig(),
    )

    assert first.state and first.state.result_version == 2
    assert second.state and second.state.result_version == 3
    assert first.state_path and first.state_path.name.endswith("_v002.partial.json")
    assert second.state_path and second.state_path.name.endswith("_v003.partial.json")


@pytest.mark.parametrize(
    ("error_number", "case_name"),
    [(errno.ENOSPC, "disk full"), (errno.EIO, "output write error")],
)
def test_running_state_write_failure_is_sanitized_and_leaves_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_number: int,
    case_name: str,
) -> None:
    def fail_write(descriptor: int, payload: bytes) -> None:
        del descriptor, payload
        raise OSError(error_number, case_name)

    monkeypatch.setattr(state_module, "_write_all", fail_write)
    output_directory = tmp_path / "output"

    with pytest.raises(OutputReservationError, match="Cannot reserve output state"):
        reserve_job(
            _inspection(),
            output_directory=output_directory,
            run_id=RUN_ID,
            force=False,
            config=OutputsConfig(),
        )

    assert not (output_directory / "episode_results.partial.json").exists()
    assert not (output_directory / "episode_results.json").exists()
    assert not list(output_directory.glob("*.tmp"))
