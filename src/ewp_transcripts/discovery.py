"""Deterministic input path normalization and file discovery."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

from ewp_transcripts.domain import (
    DiscoveredFile,
    DiscoveryResult,
    DiscoverySkipReason,
    SkippedPath,
)
from ewp_transcripts.domain.errors import (
    InputNotFoundError,
    SymlinkInputError,
    UnsupportedInputError,
)

_WINDOWS_DRIVE_PATH = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<tail>.*)$")
_NATURAL_PART = re.compile(r"(\d+)")


def normalize_input_path(
    supplied_path: str | Path,
    *,
    cwd: Path | None = None,
    wsl_mount_root: Path = Path("/mnt"),
) -> Path:
    """Normalize Windows drive, WSL, POSIX, and relative paths without resolving symlinks."""

    raw_path = str(supplied_path)
    windows_match = _WINDOWS_DRIVE_PATH.match(raw_path)
    if windows_match:
        drive = windows_match.group("drive").casefold()
        tail_parts = [part for part in re.split(r"[\\/]", windows_match.group("tail")) if part]
        return wsl_mount_root / drive / Path(*tail_parts)

    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return ((Path.cwd() if cwd is None else cwd) / path).absolute()


def natural_path_key(path: Path) -> tuple[tuple[int, int | str], ...]:
    """Return a Unicode-aware natural-sort key for a path name."""

    normalized = unicodedata.normalize("NFC", path.name).casefold()
    parts: list[tuple[int, int | str]] = []
    for part in _NATURAL_PART.split(normalized):
        if not part:
            continue
        parts.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(parts)


def _candidate(path: Path) -> DiscoveredFile:
    return DiscoveredFile(
        path=path.absolute(),
        filename=path.name,
        suffix=path.suffix.removeprefix(".").casefold(),
    )


def _directory_entries(root: Path, *, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from root.rglob("*")
    else:
        yield from root.iterdir()


def discover_input(
    supplied_path: str | Path,
    *,
    recursive: bool = False,
    supported_extensions: Iterable[str],
    cwd: Path | None = None,
) -> DiscoveryResult:
    """Discover candidate audio files without reading or modifying their contents."""

    input_path = normalize_input_path(supplied_path, cwd=cwd)
    if input_path.is_symlink():
        raise SymlinkInputError(f"Direct input must not be a symbolic link: {input_path}")
    if not input_path.exists():
        raise InputNotFoundError(f"Input path does not exist: {input_path}")
    if input_path.is_file():
        return DiscoveryResult(
            input_path=input_path,
            recursive=False,
            files=(_candidate(input_path),),
            skipped=(),
        )
    if not input_path.is_dir():
        raise UnsupportedInputError(f"Input must be a regular file or directory: {input_path}")

    supported = {extension.casefold().removeprefix(".") for extension in supported_extensions}
    files: list[DiscoveredFile] = []
    skipped: list[SkippedPath] = []
    for path in _directory_entries(input_path, recursive=recursive):
        if path.is_symlink():
            skipped.append(SkippedPath(path=path.absolute(), reason=DiscoverySkipReason.SYMLINK))
            continue
        if not path.is_file():
            continue
        suffix = path.suffix.removeprefix(".").casefold()
        if suffix not in supported:
            skipped.append(
                SkippedPath(
                    path=path.absolute(),
                    reason=DiscoverySkipReason.UNSUPPORTED_EXTENSION,
                )
            )
            continue
        files.append(_candidate(path))

    files.sort(key=lambda item: (natural_path_key(item.path), item.filename))
    skipped.sort(key=lambda item: (natural_path_key(item.path), item.path.name))
    return DiscoveryResult(
        input_path=input_path,
        recursive=recursive,
        files=tuple(files),
        skipped=tuple(skipped),
    )
