"""Deterministic input path normalization and file discovery."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
from typing import Literal

from ewp_transcripts.domain import (
    DiscoveredFile,
    DiscoveryResult,
    DiscoverySkipReason,
    EpisodeCandidate,
    GroupedSource,
    SkippedPath,
    SourceFingerprint,
)
from ewp_transcripts.domain.errors import (
    AmbiguousGroupError,
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


def fingerprint_file(path: Path, *, chunk_size: int = 1024 * 1024) -> SourceFingerprint:
    """Calculate a streaming SHA-256 identity for one regular, non-symlink file."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if path.is_symlink():
        raise SymlinkInputError(f"Source must not be a symbolic link: {path}")
    if not path.is_file():
        raise InputNotFoundError(f"Source file does not exist: {path}")

    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return SourceFingerprint(
        path=path.absolute(),
        filename=path.name,
        size_bytes=path.stat().st_size,
        sha256=digest.hexdigest(),
    )


def _speaker_suffix(stem: str, separator: str) -> tuple[str, str] | None:
    base, found, label = stem.rpartition(separator)
    if not found or not base or not label:
        return None
    return base, label


def _grouped_source(file: DiscoveredFile, speaker_label: str | None) -> GroupedSource:
    return GroupedSource(
        fingerprint=fingerprint_file(file.path),
        speaker_label=speaker_label,
        speaker_source="filename" if speaker_label else "default",
    )


def group_discovered_files(
    files: Iterable[DiscoveredFile],
    *,
    separator: str = "-",
    speaker_count: Literal["auto"] | int = "auto",
) -> tuple[EpisodeCandidate, ...]:
    """Group discovered files using the documented final-separator convention."""

    if not separator:
        raise ValueError("separator must not be empty")
    ordered = sorted(files, key=lambda item: (natural_path_key(item.path), item.filename))
    by_stem: dict[str, list[DiscoveredFile]] = {}
    suffixed: dict[str, list[tuple[DiscoveredFile, str]]] = {}
    for file in ordered:
        by_stem.setdefault(file.path.stem, []).append(file)
        parsed = _speaker_suffix(file.path.stem, separator)
        if parsed is not None:
            base, label = parsed
            suffixed.setdefault(base, []).append((file, label))

    group_bases = {
        base for base, candidates in suffixed.items() if len(candidates) >= 2 or base in by_stem
    }
    consumed: set[Path] = set()
    episodes: list[EpisodeCandidate] = []
    for base in sorted(group_bases, key=lambda value: natural_path_key(Path(value))):
        labelled = suffixed[base]
        normalized_labels = [
            unicodedata.normalize("NFC", label).casefold() for _, label in labelled
        ]
        if len(normalized_labels) != len(set(normalized_labels)):
            raise AmbiguousGroupError(f"Duplicate speaker label in group: {base}")

        sources: list[GroupedSource] = []
        for index, file in enumerate(by_stem.get(base, []), start=1):
            sources.append(_grouped_source(file, f"Speaker{index}"))
            consumed.add(file.path)
        for file, label in labelled:
            sources.append(_grouped_source(file, label))
            consumed.add(file.path)
        episodes.append(EpisodeCandidate(job_id=base, sources=tuple(sources)))

    for file in ordered:
        if file.path in consumed:
            continue
        parsed = _speaker_suffix(file.path.stem, separator)
        standalone_label = parsed[1] if parsed is not None and speaker_count == 1 else None
        episodes.append(
            EpisodeCandidate(
                job_id=file.path.stem,
                sources=(_grouped_source(file, standalone_label),),
            )
        )

    episodes.sort(key=lambda episode: natural_path_key(Path(episode.job_id)))
    return tuple(episodes)
