"""Render and parse the strict human-editable EWP-TRANSLATION 1 format."""

from __future__ import annotations

import json
from pathlib import Path

from ewp_transcripts.domain.errors import InvalidTranslationError
from ewp_transcripts.domain.translation_review import (
    TranslationReview,
    TranslationReviewHeader,
    TranslationReviewUnit,
)

_MAGIC = "EWP-TRANSLATION 1"
_METADATA_PREFIX = "# metadata: "
_UNIT_PREFIX = "@@ "


def render_translation_review(review: TranslationReview) -> str:
    """Render stable UTF-8 review text with only target lines intended for editing."""

    metadata = json.dumps(
        review.header.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    lines = [_MAGIC, f"{_METADATA_PREFIX}{metadata}", ""]
    for unit in review.units:
        token_ids = ",".join(unit.source_token_ids)
        lines.extend(
            (
                (
                    f"{_UNIT_PREFIX}{unit.unit_id} {unit.speaker_id} {unit.start_ms} "
                    f"{unit.end_ms} {unit.source_text_sha256} {token_ids}"
                ),
                f"< {unit.source_text}",
                f"> {unit.target_text}",
                "",
            )
        )
    return "\n".join(lines)


def parse_translation_review(serialized: str) -> TranslationReview:
    """Parse review text and fail closed on damaged machine-owned content."""

    lines = serialized.splitlines()
    if len(lines) < 2 or lines[0] != _MAGIC or not lines[1].startswith(_METADATA_PREFIX):
        raise InvalidTranslationError("Translation review header is invalid")
    try:
        header = TranslationReviewHeader.model_validate_json(lines[1][len(_METADATA_PREFIX) :])
        units: list[TranslationReviewUnit] = []
        index = 2
        while index < len(lines):
            if not lines[index]:
                index += 1
                continue
            directive = lines[index]
            if not directive.startswith(_UNIT_PREFIX) or index + 2 >= len(lines):
                raise ValueError("invalid unit directive")
            fields = directive[len(_UNIT_PREFIX) :].split()
            if len(fields) != 6:
                raise ValueError("invalid unit fields")
            source_line, target_line = lines[index + 1], lines[index + 2]
            if not source_line.startswith("< ") or not target_line.startswith("> "):
                raise ValueError("invalid source or target line")
            units.append(
                TranslationReviewUnit(
                    unit_id=fields[0],
                    speaker_id=fields[1],
                    start_ms=int(fields[2]),
                    end_ms=int(fields[3]),
                    source_text_sha256=fields[4],
                    source_token_ids=tuple(fields[5].split(",")),
                    source_text=source_line[2:],
                    target_text=target_line[2:],
                )
            )
            index += 3
        return TranslationReview(header=header, units=tuple(units))
    except (ValueError, TypeError) as error:
        raise InvalidTranslationError("Translation review content is invalid") from error


def load_translation_review(path: Path) -> TranslationReview:
    try:
        return parse_translation_review(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise InvalidTranslationError(f"Cannot read translation review: {path}") from error
