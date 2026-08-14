"""Safe external-editor launching for manual transcript review."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path

from ewp_transcripts.domain.errors import RevisionEditorError


def editor_command(
    configured: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Resolve configured editor text, then VISUAL/EDITOR, into an argument vector."""

    values = os.environ if environment is None else environment
    selected = (
        configured.strip() or values.get("VISUAL", "").strip() or values.get("EDITOR", "").strip()
    )
    if not selected:
        raise RevisionEditorError(
            "No revision editor is configured; use --editor 'nano', set editor under "
            "the [revision] section of transcriber.toml, or set the VISUAL/EDITOR "
            "environment variable to an installed editor command"
        )
    try:
        command = tuple(shlex.split(selected))
    except ValueError as error:
        raise RevisionEditorError("Revision editor command has invalid quoting") from error
    if not command:
        raise RevisionEditorError("Revision editor command is empty")
    return command


def open_review_in_editor(
    review_path: Path,
    *,
    configured: str,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Open a review, wait, and accept only a successful editor exit status."""

    command = (*editor_command(configured, environment=environment), str(review_path))
    try:
        completed = subprocess.run(command, check=False)
    except OSError as error:
        raise RevisionEditorError(f"Cannot start revision editor: {command[0]}") from error
    if completed.returncode != 0:
        raise RevisionEditorError(
            f"Revision editor exited unsuccessfully with status {completed.returncode}"
        )


def require_review_change(review_path: Path, *, original_content: bytes) -> None:
    """Reject a successful editor exit that did not change the prepared review."""

    try:
        current_content = review_path.read_bytes()
    except OSError as error:
        raise RevisionEditorError(f"Cannot read edited review: {review_path}") from error
    if current_content == original_content:
        raise RevisionEditorError(
            "Revision editor closed without changing the review; no revision was created. "
            f"Review retained at: {review_path}"
        )
