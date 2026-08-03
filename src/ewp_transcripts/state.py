"""Atomic non-completed job-state reservation and persistence."""

from __future__ import annotations

import os
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from ewp_transcripts import __version__
from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import (
    EpisodeInspection,
    JobReservation,
    JobStateRecord,
)
from ewp_transcripts.domain.enums import JobStateStatus, PlanDecision
from ewp_transcripts.domain.errors import OutputReservationError
from ewp_transcripts.output_lock import output_directory_lock
from ewp_transcripts.storage import find_existing_results, plan_job_outputs


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        remaining = remaining[os.write(descriptor, remaining) :]


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_exclusive_json(path: Path, payload: str, *, run_id: UUID) -> None:
    temporary = path.parent / f".{path.name}.{run_id}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        created = True
        try:
            _write_all(descriptor, payload.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
        _fsync_directory(path.parent)
    except FileExistsError as error:
        raise OutputReservationError(f"Output state already exists: {path}") from error
    except OSError as error:
        raise OutputReservationError(f"Cannot reserve output state: {path}") from error
    finally:
        if created:
            with suppress(FileNotFoundError):
                temporary.unlink()


def reserve_job(
    inspection: EpisodeInspection,
    *,
    output_directory: Path,
    run_id: UUID,
    force: bool,
    config: OutputsConfig,
    lock_timeout_seconds: float = 0,
) -> JobReservation:
    """Re-plan under lock and atomically publish a running state for PROCESS."""

    with output_directory_lock(
        output_directory,
        timeout_seconds=lock_timeout_seconds,
    ):
        existing = find_existing_results(output_directory)
        plan = plan_job_outputs(
            inspection,
            output_directory=output_directory,
            existing_results=existing,
            force=force,
            config=config,
        )
        if plan.decision is PlanDecision.SKIP:
            return JobReservation(plan=plan)
        if plan.outputs is None:  # Defensive; JobOutputPlan also enforces this invariant.
            raise OutputReservationError("Process plan has no output paths")

        now = datetime.now(UTC)
        state = JobStateRecord(
            application_version=__version__,
            run_id=run_id,
            job_id=inspection.job_id,
            episode_signature_sha256=inspection.episode_signature_sha256,
            result_version=plan.outputs.result_version,
            status=JobStateStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        _publish_exclusive_json(
            plan.outputs.partial_results,
            state.model_dump_json(indent=2) + "\n",
            run_id=run_id,
        )
        return JobReservation(
            plan=plan,
            state=state,
            state_path=plan.outputs.partial_results,
        )
