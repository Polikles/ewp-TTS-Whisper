"""Strict allocation and cleanup of isolated per-job work directories."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import UUID

from ewp_transcripts.domain import WorkDirectory
from ewp_transcripts.domain.errors import UnsafeWorkDirectoryError

MARKER_FILENAME = ".ewp-transcripts-work.json"


def _safe_component(value: str, *, label: str) -> str:
    if not value or value in {".", ".."} or Path(value).name != value or "\x00" in value:
        raise UnsafeWorkDirectoryError(f"Unsafe {label} for work directory: {value!r}")
    return value


def allocate_work_directory(
    work_root: Path,
    *,
    run_id: UUID,
    job_id: str,
) -> WorkDirectory:
    """Create a new owner-marked work directory without reusing an existing path."""

    if work_root.is_symlink():
        raise UnsafeWorkDirectoryError(f"Work root must not be a symbolic link: {work_root}")
    safe_job_id = _safe_component(job_id, label="job ID")
    run_component = str(run_id)
    run_directory = work_root / run_component
    if run_directory.is_symlink():
        raise UnsafeWorkDirectoryError(
            f"Run directory must not be a symbolic link: {run_directory}"
        )
    path = run_directory / safe_job_id
    marker_path = path / MARKER_FILENAME
    try:
        work_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        run_directory.mkdir(exist_ok=True, mode=0o700)
        path.mkdir(mode=0o700)
        marker = {
            "marker_version": "1.0",
            "run_id": run_component,
            "job_id": safe_job_id,
        }
        descriptor = os.open(
            marker_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            payload = (json.dumps(marker) + "\n").encode("utf-8")
            remaining = memoryview(payload)
            while remaining:
                remaining = remaining[os.write(descriptor, remaining) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except FileExistsError as error:
        raise UnsafeWorkDirectoryError(f"Work directory already exists: {path}") from error
    except OSError as error:
        raise UnsafeWorkDirectoryError(f"Cannot allocate work directory: {path}") from error
    return WorkDirectory(
        work_root=work_root,
        run_id=run_id,
        job_id=safe_job_id,
        path=path,
        marker_path=marker_path,
    )


def cleanup_work_directory(workspace: WorkDirectory) -> None:
    """Delete exactly one verified owned workspace, never its root or siblings."""

    expected_path = workspace.work_root / str(workspace.run_id) / workspace.job_id
    if workspace.path != expected_path or workspace.marker_path != expected_path / MARKER_FILENAME:
        raise UnsafeWorkDirectoryError("Work directory paths do not match ownership metadata")
    if (
        workspace.work_root.is_symlink()
        or workspace.path.is_symlink()
        or workspace.marker_path.is_symlink()
    ):
        raise UnsafeWorkDirectoryError("Symbolic-link work directories cannot be cleaned")
    try:
        marker = json.loads(workspace.marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise UnsafeWorkDirectoryError("Work directory marker is missing or invalid") from error
    expected_marker = {
        "marker_version": "1.0",
        "run_id": str(workspace.run_id),
        "job_id": workspace.job_id,
    }
    if marker != expected_marker:
        raise UnsafeWorkDirectoryError("Work directory marker does not match ownership")
    try:
        shutil.rmtree(workspace.path)
    except OSError as error:
        raise UnsafeWorkDirectoryError(f"Cannot clean work directory: {workspace.path}") from error
