"""Typed EWP-TRANSLATION 1 manual review models."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ewp_transcripts.domain.translation import (
    Language,
    TranslationDictionaryProvenance,
    TranslationParent,
    TranslationSource,
    TranslationStyle,
)


class TranslationReviewModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class TranslationReviewHeader(TranslationReviewModel):
    job_id: str = Field(min_length=1)
    source: TranslationSource
    source_language: Language
    target_language: Language
    style: TranslationStyle
    generated_at: datetime
    application_version: str = Field(min_length=1)
    parent_translation: TranslationParent | None = None
    dictionary: TranslationDictionaryProvenance | None = None

    @model_validator(mode="after")
    def validate_header(self) -> Self:
        if self.source_language == self.target_language:
            raise ValueError("translation review languages must differ")
        if self.job_id != self.source.canonical_result.job_id:
            raise ValueError("translation review and source job IDs must match")
        if self.generated_at.tzinfo is None:
            raise ValueError("translation review creation time must include timezone")
        return self


class TranslationReviewUnit(TranslationReviewModel):
    unit_id: str = Field(pattern=r"^tu_[0-9]{6,}$")
    speaker_id: str = Field(pattern=r"^speaker_[0-9]{3,}$")
    source_token_ids: tuple[str, ...] = Field(min_length=1)
    source_text: str = Field(min_length=1, pattern=r".*\S.*")
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    target_text: str = ""

    @field_validator("source_text", "target_text")
    @classmethod
    def require_single_line(cls, value: str) -> str:
        if any(character in value for character in ("\n", "\r", "\x00")):
            raise ValueError("translation review text must be one normalized line")
        return value

    @model_validator(mode="after")
    def validate_timing(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("translation review unit end must not precede start")
        if hashlib.sha256(self.source_text.encode("utf-8")).hexdigest() != self.source_text_sha256:
            raise ValueError("translation review source text SHA-256 does not match")
        return self


class TranslationReview(TranslationReviewModel):
    format_version: int = Field(default=1, ge=1, le=1)
    header: TranslationReviewHeader
    units: tuple[TranslationReviewUnit, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_units(self) -> Self:
        unit_ids = [unit.unit_id for unit in self.units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("translation review unit IDs must be unique")
        token_ids = [token_id for unit in self.units for token_id in unit.source_token_ids]
        if len(token_ids) != len(set(token_ids)):
            raise ValueError("translation review source tokens must be owned exactly once")
        return self
