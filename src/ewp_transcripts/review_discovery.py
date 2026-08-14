"""Deterministic discovery of completed canonical results for review preparation."""

from __future__ import annotations

import re
from pathlib import Path

from ewp_transcripts.discovery import natural_path_key, normalize_input_path
from ewp_transcripts.domain.errors import (
    InputNotFoundError,
    SymlinkInputError,
    UnsupportedInputError,
)

_RESULT_NAME = re.compile(r"^.+_results(?:_v[0-9]{3,})?\.json$")
_REVIEW_NAME = re.compile(r"^.+\.review(?:_v[0-9]{3,})?\.txt$")


def discover_review_results(
    input_path: str | Path,
    *,
    recursive: bool = False,
) -> tuple[Path, ...]:
    """Select result candidates without reading them or treating unrelated JSON as input."""

    path = normalize_input_path(input_path)
    if path.is_symlink():
        raise SymlinkInputError(f"Review input must not be a symbolic link: {path}")
    if not path.exists():
        raise InputNotFoundError(f"Review input does not exist: {path}")
    if path.is_file():
        return (path,)
    if not path.is_dir():
        raise UnsupportedInputError(f"Review input must be a regular file or directory: {path}")

    entries = path.rglob("*") if recursive else path.iterdir()
    candidates = [
        candidate.absolute()
        for candidate in entries
        if candidate.is_file()
        and not candidate.is_symlink()
        and _RESULT_NAME.fullmatch(candidate.name) is not None
    ]
    candidates.sort(
        key=lambda candidate: (
            natural_path_key(candidate),
            candidate.name,
            candidate.as_posix(),
        )
    )
    return tuple(candidates)


def discover_review_files(
    input_path: str | Path,
    *,
    recursive: bool = False,
) -> tuple[Path, ...]:
    """Select editable review files in deterministic natural order."""

    path = normalize_input_path(input_path)
    if path.is_symlink():
        raise SymlinkInputError(f"Review input must not be a symbolic link: {path}")
    if not path.exists():
        raise InputNotFoundError(f"Review input does not exist: {path}")
    if path.is_file():
        return (path,)
    if not path.is_dir():
        raise UnsupportedInputError(f"Review input must be a regular file or directory: {path}")
    entries = path.rglob("*") if recursive else path.iterdir()
    candidates = [
        candidate.absolute()
        for candidate in entries
        if candidate.is_file()
        and not candidate.is_symlink()
        and _REVIEW_NAME.fullmatch(candidate.name) is not None
    ]
    candidates.sort(
        key=lambda candidate: (
            natural_path_key(candidate),
            candidate.name,
            candidate.as_posix(),
        )
    )
    return tuple(candidates)
