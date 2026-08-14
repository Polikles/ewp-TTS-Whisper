"""Tests for safe external revision-editor command handling."""

import subprocess
from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import RevisionEditorError
from ewp_transcripts.revision_editor import (
    editor_command,
    open_review_in_editor,
    require_review_change,
)


def test_editor_resolution_prefers_config_then_visual_then_editor() -> None:
    environment = {"VISUAL": "code --wait", "EDITOR": "vim"}

    assert editor_command("nano -w", environment=environment) == ("nano", "-w")
    assert editor_command("", environment=environment) == ("code", "--wait")
    assert editor_command("", environment={"EDITOR": "vim"}) == ("vim",)


def test_editor_launch_uses_argument_vector_without_shell(monkeypatch, tmp_path: Path) -> None:
    review = tmp_path / "episode.review.txt"
    review.write_text("review", encoding="utf-8")
    observed = None

    def fake_run(command, *, check):
        nonlocal observed
        observed = (command, check)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    open_review_in_editor(review, configured='code --wait "--reuse-window"')

    assert observed == (("code", "--wait", "--reuse-window", str(review)), False)


def test_missing_or_failed_editor_is_controlled(monkeypatch, tmp_path: Path) -> None:
    with pytest.raises(RevisionEditorError, match="--editor 'nano'.*environment variable"):
        editor_command("", environment={})

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, *, check: subprocess.CompletedProcess(command, 9),
    )
    with pytest.raises(RevisionEditorError, match="status 9"):
        open_review_in_editor(tmp_path / "review.txt", configured="false")


def test_unchanged_review_cannot_be_automatically_applied(tmp_path: Path) -> None:
    review = tmp_path / "episode.review.txt"
    review.write_text("unchanged", encoding="utf-8")

    with pytest.raises(RevisionEditorError, match="without changing.*no revision"):
        require_review_change(review, original_content=b"unchanged")

    review.write_text("corrected", encoding="utf-8")
    require_review_change(review, original_content=b"unchanged")
