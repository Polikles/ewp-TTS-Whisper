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
            "No revision editor is configured; set revision.editor, VISUAL, or EDITOR"
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
