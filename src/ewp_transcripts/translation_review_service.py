"""Prepare exact-lineage editable translation reviews."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ewp_transcripts import __version__
from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.errors import InvalidTranslationError
from ewp_transcripts.domain.revision import load_transcript_revision, sha256_file
from ewp_transcripts.domain.translation import (
    Language,
    TranslationCanonicalSource,
    TranslationParent,
    TranslationRevisionSource,
    TranslationSource,
    TranslationStyle,
    load_transcript_translation,
)
from ewp_transcripts.domain.translation_review import (
    TranslationReview,
    TranslationReviewHeader,
    TranslationReviewUnit,
)
from ewp_transcripts.effective_transcript import resolve_effective_transcript
from ewp_transcripts.translation_units import plan_translation_units


def validate_translation_review_source(
    review: TranslationReview,
    result_path: Path,
    *,
    revision_path: Path | None = None,
    parent_translation_path: Path | None = None,
) -> None:
    """Fail closed unless all machine-owned review fields match the exact source."""

    expected = prepare_translation_review(
        result_path,
        target_language=review.header.target_language,
        revision_path=revision_path,
        parent_translation_path=parent_translation_path,
        style=review.header.style,
        generated_at=review.header.generated_at,
    )
    if review.header != expected.header:
        raise InvalidTranslationError("Translation review metadata does not match the exact source")
    actual_machine_fields = tuple(unit.model_dump(exclude={"target_text"}) for unit in review.units)
    expected_machine_fields = tuple(
        unit.model_dump(exclude={"target_text"}) for unit in expected.units
    )
    if actual_machine_fields != expected_machine_fields:
        raise InvalidTranslationError("Translation review units do not match the exact source")


def prepare_translation_review(
    result_path: Path,
    *,
    target_language: Language,
    revision_path: Path | None = None,
    parent_translation_path: Path | None = None,
    style: TranslationStyle | None = None,
    generated_at: datetime | None = None,
) -> TranslationReview:
    """Prepare blank target-language units from raw or one exact compatible revision."""

    base = load_canonical_result(result_path)
    revision = load_transcript_revision(revision_path) if revision_path is not None else None
    effective = resolve_effective_transcript(base, revision, base_path=result_path)
    if effective.language not in {"pl", "en"}:
        raise ValueError("translation source language must resolve to pl or en")
    if effective.language == target_language:
        raise ValueError("translation source and target languages must differ")
    canonical = TranslationCanonicalSource(
        job_id=base.job_id,
        result_version=base.result_version,
        schema_version=base.schema_version,
        sha256=sha256_file(result_path),
        filename=result_path.name,
    )
    if revision is None:
        source = TranslationSource(canonical_result=canonical, verification="raw")
    else:
        assert revision_path is not None
        source_revision = TranslationRevisionSource(
            revision_id=revision.revision_id,
            revision_number=revision.revision_number,
            sha256=sha256_file(revision_path),
            filename=revision_path.name,
            method=revision.provenance.method,
        )
        source = TranslationSource(
            canonical_result=canonical,
            transcript_revision=source_revision,
            verification=(
                "manually_verified"
                if revision.provenance.method == "manual"
                else "automated_candidate"
            ),
        )
    units = plan_translation_units(effective)
    parent = (
        load_transcript_translation(parent_translation_path)
        if parent_translation_path is not None
        else None
    )
    parent_identity = None
    parent_targets: dict[str, str] = {}
    if parent is not None:
        assert parent_translation_path is not None
        if (
            parent.job_id != base.job_id
            or parent.direction.source_language != effective.language
            or parent.direction.target_language != target_language
            or parent.style != (style or TranslationStyle())
            or parent.source != source
        ):
            raise InvalidTranslationError(
                "Parent translation does not match the exact source, direction, or style"
            )
        planned_identity = tuple(
            (
                unit.unit_id,
                unit.speaker_id,
                unit.source_token_ids,
                unit.source_text_sha256,
                unit.start_ms,
                unit.end_ms,
            )
            for unit in units
        )
        parent_unit_identity = tuple(
            (
                unit.unit_id,
                unit.speaker_id,
                unit.source_token_ids,
                unit.source_text_sha256,
                unit.start_ms,
                unit.end_ms,
            )
            for unit in parent.units
        )
        if planned_identity != parent_unit_identity:
            raise InvalidTranslationError("Parent translation units do not match the exact source")
        parent_identity = TranslationParent(
            translation_id=parent.translation_id,
            translation_number=parent.translation_number,
            sha256=sha256_file(parent_translation_path),
            filename=parent_translation_path.name,
        )
        parent_targets = {unit.unit_id: unit.target_text for unit in parent.units}
    return TranslationReview(
        header=TranslationReviewHeader(
            job_id=base.job_id,
            source=source,
            source_language=cast(Language, effective.language),
            target_language=target_language,
            style=style or TranslationStyle(),
            generated_at=generated_at or datetime.now(UTC),
            application_version=__version__,
            parent_translation=parent_identity,
        ),
        units=tuple(
            TranslationReviewUnit(
                unit_id=unit.unit_id,
                speaker_id=unit.speaker_id,
                source_token_ids=unit.source_token_ids,
                source_text=unit.source_text,
                source_text_sha256=unit.source_text_sha256,
                start_ms=unit.start_ms,
                end_ms=unit.end_ms,
                target_text=parent_targets.get(unit.unit_id, ""),
            )
            for unit in units
        ),
    )
