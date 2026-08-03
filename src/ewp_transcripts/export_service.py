"""Application service for safe, model-free derived exports."""

from __future__ import annotations

import hashlib
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from ewp_transcripts.config import SubtitlesConfig
from ewp_transcripts.domain.canonical import CanonicalResult
from ewp_transcripts.domain.errors import InvalidCanonicalResultError, OutputReservationError
from ewp_transcripts.exporters import (
    build_subtitle_cues,
    render_segments_json,
    render_srt,
    render_transcript,
    render_vtt,
)
from ewp_transcripts.output_lock import output_directory_lock


class ExportFormat(StrEnum):
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
    SEGMENTS = "segments"


@dataclass(frozen=True, slots=True)
class ExportOutcome:
    result_version: int
    written: tuple[Path, ...]
    skipped: tuple[Path, ...]


def export_result(
    results_path: Path,
    *,
    formats: tuple[ExportFormat, ...],
    output_directory: Path | None = None,
    force: bool = False,
    subtitles_config: SubtitlesConfig | None = None,
    generated_at: datetime | None = None,
) -> ExportOutcome:
    """Generate requested exports atomically from one completed canonical result."""

    if not formats:
        raise InvalidCanonicalResultError("At least one export format is required")
    unique_formats = tuple(dict.fromkeys(formats))
    result, payload = _read_result(results_path)
    if result.status != "completed":
        raise InvalidCanonicalResultError("Only completed canonical results can be exported")
    destination = results_path.parent if output_directory is None else output_directory.expanduser()
    if not destination.is_absolute():
        destination = (Path.cwd() / destination).absolute()

    with output_directory_lock(destination):
        version = _select_version(
            destination,
            job_id=result.job_id,
            formats=unique_formats,
            base_version=result.result_version,
            force=force,
        )
        paths = {
            format_: _export_path(destination, result.job_id, format_, version)
            for format_ in unique_formats
        }
        skipped = tuple(path for path in paths.values() if path.exists()) if not force else ()
        pending = tuple((format_, path) for format_, path in paths.items() if path not in skipped)
        try:
            rendered = _render_exports(
                result,
                pending,
                results_path=results_path,
                results_sha256=hashlib.sha256(payload).hexdigest(),
                subtitles_config=subtitles_config or SubtitlesConfig(),
                generated_at=generated_at or datetime.now(UTC),
            )
        except ValueError as error:
            raise InvalidCanonicalResultError("Cannot render configured exports") from error
        for path, content in rendered:
            _publish_exclusive(path, content)
        return ExportOutcome(
            result_version=version,
            written=tuple(path for path, _ in rendered),
            skipped=skipped,
        )


def _read_result(path: Path) -> tuple[CanonicalResult, bytes]:
    try:
        payload = path.read_bytes()
        return CanonicalResult.model_validate_json(payload), payload
    except (OSError, ValidationError) as error:
        raise InvalidCanonicalResultError(f"Cannot read canonical result: {path}") from error


def _select_version(
    directory: Path,
    *,
    job_id: str,
    formats: tuple[ExportFormat, ...],
    base_version: int,
    force: bool,
) -> int:
    if not force:
        return base_version
    version = max(2, base_version + 1)
    while any(_export_path(directory, job_id, format_, version).exists() for format_ in formats):
        version += 1
    return version


def _export_path(directory: Path, job_id: str, format_: ExportFormat, version: int) -> Path:
    if (
        not job_id
        or job_id in {".", ".."}
        or Path(job_id).name != job_id
        or any(character in job_id for character in ("/", "\\", "\x00"))
    ):
        raise InvalidCanonicalResultError("Canonical job_id is unsafe for export filenames")
    suffix = "" if version == 1 else f"_v{version:03d}"
    role, extension = {
        ExportFormat.TXT: ("transcript", "txt"),
        ExportFormat.SRT: ("subtitles", "srt"),
        ExportFormat.VTT: ("subtitles", "vtt"),
        ExportFormat.SEGMENTS: ("segments", "json"),
    }[format_]
    return directory / f"{job_id}_{role}{suffix}.{extension}"


def _render_exports(
    result: CanonicalResult,
    pending: tuple[tuple[ExportFormat, Path], ...],
    *,
    results_path: Path,
    results_sha256: str,
    subtitles_config: SubtitlesConfig,
    generated_at: datetime,
) -> tuple[tuple[Path, str], ...]:
    cues = None
    rendered: list[tuple[Path, str]] = []
    for format_, path in pending:
        if format_ is ExportFormat.TXT:
            content = render_transcript(result)
        elif format_ is ExportFormat.SEGMENTS:
            content = render_segments_json(
                result,
                results_file=results_path,
                results_sha256=results_sha256,
                generated_at=generated_at,
            )
        else:
            if cues is None:
                cues = build_subtitle_cues(result, subtitles_config)
            content = render_srt(cues) if format_ is ExportFormat.SRT else render_vtt(cues)
        rendered.append((path, content))
    return tuple(rendered)


def _publish_exclusive(path: Path, content: str) -> None:
    temporary = path.parent / f".{path.name}.{uuid4()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        created = True
        try:
            payload = content.encode("utf-8")
            while payload:
                written = os.write(descriptor, payload)
                payload = payload[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except FileExistsError as error:
        raise OutputReservationError(f"Export already exists: {path}") from error
    except OSError as error:
        raise OutputReservationError(f"Cannot publish export: {path}") from error
    finally:
        if created:
            with suppress(FileNotFoundError):
                temporary.unlink()
