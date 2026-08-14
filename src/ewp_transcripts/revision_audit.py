"""Reconstructable detailed diagnostics for immutable transcript revisions."""

from __future__ import annotations

import json
import os
import unicodedata
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ewp_transcripts.domain.canonical import CanonicalResult
from ewp_transcripts.domain.errors import OutputReservationError
from ewp_transcripts.domain.revision import (
    TranscriptRevision,
    sha256_file,
    validate_revision_base,
)
from ewp_transcripts.output_lock import output_directory_lock


def _lexical(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if character.isalnum())


def build_revision_audit(
    base: CanonicalResult,
    revision: TranscriptRevision,
    *,
    base_path: Path,
    revision_path: Path,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Reconstruct a base-relative edit list without relying on stored deltas."""

    validate_revision_base(revision, base, base_sha256=sha256_file(base_path))
    words = tuple(word for segment in base.transcript.segments for word in segment.words)
    by_id = {word.word_id: word for word in words}
    mapping_frequency: dict[str, int] = {}
    for token in revision.transcript.tokens:
        for word_id in token.source_word_ids:
            mapping_frequency[word_id] = mapping_frequency.get(word_id, 0) + 1
    changes: list[dict[str, object]] = []
    mapped_ids: set[str] = set()
    for token in revision.transcript.tokens:
        mapped_ids.update(token.source_word_ids)
        source = [by_id[word_id] for word_id in token.source_word_ids]
        if not source:
            classification = "insertion"
        elif len(source) > 1:
            classification = "merge"
        elif mapping_frequency[source[0].word_id] > 1:
            classification = "split"
        elif token.text == source[0].text:
            classification = (
                "speaker_change" if token.speaker_id != source[0].speaker_id else "unchanged"
            )
        elif _lexical(token.text) == _lexical(source[0].text):
            classification = "punctuation_only"
        else:
            classification = "substitution"
        if classification != "unchanged":
            changes.append(
                {
                    "classification": classification,
                    "token_id": token.token_id,
                    "before": " ".join(word.text for word in source) or None,
                    "after": token.text,
                    "source_word_ids": list(token.source_word_ids),
                    "speaker_before": source[0].speaker_id if source else None,
                    "speaker_after": token.speaker_id,
                    "insertion_anchor": (
                        token.insertion_anchor.model_dump(mode="json", exclude_none=True)
                        if token.insertion_anchor is not None
                        else None
                    ),
                }
            )
    for word in words:
        if word.word_id not in mapped_ids:
            changes.append(
                {
                    "classification": "deletion",
                    "token_id": None,
                    "before": word.text,
                    "after": None,
                    "source_word_ids": [word.word_id],
                    "speaker_before": word.speaker_id,
                    "speaker_after": None,
                    "insertion_anchor": None,
                }
            )
    created = generated_at or datetime.now(UTC)
    return {
        "schema_version": "1.0",
        "generated_at": created.isoformat().replace("+00:00", "Z"),
        "job_id": revision.job_id,
        "base_result": {
            "file": base_path.name,
            "sha256": revision.base_result.sha256,
        },
        "revision": {
            "file": revision_path.name,
            "revision_id": str(revision.revision_id),
            "revision_number": revision.revision_number,
        },
        "statistics": revision.statistics.model_dump(mode="json"),
        "changes": changes,
    }


def publish_revision_audit(
    audit: dict[str, object],
    *,
    output_directory: Path,
    job_id: str,
    revision_number: int,
    lock_timeout_seconds: float = 0,
) -> Path:
    """Publish one diagnostic audit without overwriting an existing artifact."""

    filename = f"{job_id}_revision_{revision_number:03d}_audit.json"
    if Path(job_id).name != job_id or any(character in job_id for character in "/\\\x00"):
        raise OutputReservationError("Revision job ID is unsafe for audit filenames")
    with output_directory_lock(output_directory, timeout_seconds=lock_timeout_seconds):
        path = output_directory / filename
        temporary = output_directory / f".{filename}.{uuid4()}.tmp"
        payload = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        descriptor: int | None = None
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(temporary, flags, 0o600)
            remaining = memoryview(payload)
            while remaining:
                remaining = remaining[os.write(descriptor, remaining) :]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.link(temporary, path)
        except FileExistsError as error:
            raise OutputReservationError(f"Revision audit already exists: {path}") from error
        except OSError as error:
            raise OutputReservationError(f"Cannot publish revision audit: {path}") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
            with suppress(FileNotFoundError):
                temporary.unlink()
        return path
