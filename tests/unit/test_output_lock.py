"""Tests for Linux/WSL output-directory locking."""

import json
import os
from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import OutputLockUnavailableError
from ewp_transcripts.output_lock import LOCK_FILENAME, output_directory_lock


def test_lock_creates_directory_and_sanitized_metadata(tmp_path: Path) -> None:
    output_directory = tmp_path / "new-output"

    with output_directory_lock(output_directory) as lock_path:
        metadata = json.loads(lock_path.read_text(encoding="utf-8"))
        assert metadata["pid"] == os.getpid()
        assert set(metadata) == {"pid", "acquired_at"}

    assert output_directory.is_dir()
    assert (output_directory / LOCK_FILENAME).is_file()


def test_second_holder_fails_without_waiting(tmp_path: Path) -> None:
    with (
        output_directory_lock(tmp_path),
        pytest.raises(OutputLockUnavailableError, match="another process"),
        output_directory_lock(tmp_path),
    ):
        pytest.fail("the second lock must not be acquired")


def test_lock_can_be_reacquired_after_release(tmp_path: Path) -> None:
    with output_directory_lock(tmp_path):
        pass
    with output_directory_lock(tmp_path) as lock_path:
        assert lock_path.name == LOCK_FILENAME


def test_symlink_output_directory_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked-output"
    link.symlink_to(target, target_is_directory=True)

    with (
        pytest.raises(OutputLockUnavailableError, match="symbolic link"),
        output_directory_lock(link),
    ):
        pytest.fail("a symlink destination must not be locked")
