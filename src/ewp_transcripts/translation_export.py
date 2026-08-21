"""Deterministic derived exports from immutable translation snapshots."""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from ewp_transcripts.domain.errors import OutputReservationError
from ewp_transcripts.domain.translation import TranscriptTranslation, load_transcript_translation
from ewp_transcripts.output_lock import output_directory_lock


@dataclass(frozen=True, slots=True)
class TranslationExportOutcome:
    translation_path: Path
    written: tuple[Path, ...]
    skipped: tuple[Path, ...]


def render_translation_text(translation: TranscriptTranslation) -> str:
    """Render stable speaker blocks without inventing display-name metadata."""

    blocks: list[str] = []
    current_speaker: str | None = None
    current_lines: list[str] = []
    multiple_speakers = len({unit.speaker_id for unit in translation.units}) > 1
    for unit in translation.units:
        if unit.speaker_id != current_speaker:
            if current_lines:
                blocks.append("\n".join(current_lines))
            current_speaker = unit.speaker_id
            current_lines = [f"{unit.speaker_id}:"] if multiple_speakers else []
        current_lines.append(unit.target_text)
    if current_lines:
        blocks.append("\n".join(current_lines))
    return "\n\n".join(blocks) + "\n"


def _publish_or_skip(path: Path, payload: bytes) -> bool:
    if path.is_file():
        if path.read_bytes() == payload:
            return False
        raise OutputReservationError(
            f"Translation export already exists with other content: {path}"
        )
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        created = True
        try:
            remaining = memoryview(payload)
            while remaining:
                remaining = remaining[os.write(descriptor, remaining) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
        directory_flags = os.O_RDONLY | (os.O_DIRECTORY if hasattr(os, "O_DIRECTORY") else 0)
        directory_descriptor = os.open(path.parent, directory_flags)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return True
    except FileExistsError as error:
        raise OutputReservationError(
            f"Translation export was concurrently reserved: {path}"
        ) from error
    finally:
        if created:
            with suppress(FileNotFoundError):
                temporary.unlink()


def export_translation_text(
    translation_path: str | Path,
    *,
    output_directory: Path | None = None,
    lock_timeout_seconds: float = 0,
) -> TranslationExportOutcome:
    """Write or safely skip the deterministic TXT representation."""

    normalized = Path(translation_path).expanduser().absolute()
    translation = load_transcript_translation(normalized)
    destination = output_directory or normalized.parent
    name = (
        f"{translation.job_id}_{translation.direction.target_language}_translation_"
        f"{translation.translation_number:03d}.txt"
    )
    path = destination / name
    payload = render_translation_text(translation).encode("utf-8")
    with output_directory_lock(destination, timeout_seconds=lock_timeout_seconds):
        written = _publish_or_skip(path, payload)
    return TranslationExportOutcome(
        translation_path=normalized,
        written=(path,) if written else (),
        skipped=() if written else (path,),
    )
