"""Tests for strict work-directory allocation and cleanup."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from ewp_transcripts.domain.errors import UnsafeWorkDirectoryError
from ewp_transcripts.workdirs import allocate_work_directory, cleanup_work_directory

RUN_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def test_allocate_creates_isolated_marked_workspace(tmp_path: Path) -> None:
    workspace = allocate_work_directory(tmp_path / "work", run_id=RUN_ID, job_id="episode")

    assert workspace.path == tmp_path / "work" / str(RUN_ID) / "episode"
    marker = json.loads(workspace.marker_path.read_text(encoding="utf-8"))
    assert marker == {
        "marker_version": "1.0",
        "run_id": str(RUN_ID),
        "job_id": "episode",
    }


def test_existing_workspace_is_never_reused(tmp_path: Path) -> None:
    root = tmp_path / "work"
    allocate_work_directory(root, run_id=RUN_ID, job_id="episode")

    with pytest.raises(UnsafeWorkDirectoryError, match="already exists"):
        allocate_work_directory(root, run_id=RUN_ID, job_id="episode")


def test_cleanup_removes_only_verified_workspace(tmp_path: Path) -> None:
    root = tmp_path / "work"
    workspace = allocate_work_directory(root, run_id=RUN_ID, job_id="episode")
    sibling = root / "models-must-remain"
    sibling.mkdir()
    (sibling / "model.bin").write_bytes(b"model")
    (workspace.path / "temporary.wav").write_bytes(b"audio")

    cleanup_work_directory(workspace)

    assert not workspace.path.exists()
    assert (sibling / "model.bin").read_bytes() == b"model"


def test_tampered_marker_blocks_cleanup(tmp_path: Path) -> None:
    workspace = allocate_work_directory(tmp_path / "work", run_id=RUN_ID, job_id="episode")
    workspace.marker_path.write_text("{}", encoding="utf-8")

    with pytest.raises(UnsafeWorkDirectoryError, match="does not match"):
        cleanup_work_directory(workspace)

    assert workspace.path.is_dir()


@pytest.mark.parametrize("job_id", ["", ".", "..", "../escape", "dir/escape"])
def test_unsafe_job_id_is_rejected(tmp_path: Path, job_id: str) -> None:
    with pytest.raises(UnsafeWorkDirectoryError, match="Unsafe job ID"):
        allocate_work_directory(tmp_path / "work", run_id=RUN_ID, job_id=job_id)


def test_symlink_work_root_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "work"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(UnsafeWorkDirectoryError, match="symbolic link"):
        allocate_work_directory(link, run_id=RUN_ID, job_id="episode")
