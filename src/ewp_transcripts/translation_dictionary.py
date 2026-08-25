"""Strict, explicitly selected project dictionaries for automated translation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ewp_transcripts.domain.translation import Language


class TranslationDictionaryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source: str = Field(min_length=1, pattern=r".*\S.*")
    target: str = Field(min_length=1, pattern=r".*\S.*")


class ProjectTranslationDictionary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    dictionary_version: Literal["1.0"] = "1.0"
    dictionary_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    project_id: str = Field(min_length=1)
    job_ids: tuple[str, ...] = Field(min_length=1)
    source_language: Language
    target_language: Language
    entries: tuple[TranslationDictionaryEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_entries(self) -> ProjectTranslationDictionary:
        if len(set(self.job_ids)) != len(self.job_ids):
            raise ValueError("translation dictionary job IDs must be unique")
        if "*" in self.job_ids and self.job_ids != ("*",):
            raise ValueError("project-wide translation dictionaries must use only '*' scope")
        sources = [entry.source.casefold() for entry in self.entries]
        if len(set(sources)) != len(sources):
            raise ValueError("translation dictionary source entries must be unique")
        return self

    def applies_to(self, job_id: str) -> bool:
        """Return whether this explicitly selected dictionary covers one project job."""

        return self.job_ids == ("*",) or job_id in self.job_ids


def load_project_translation_dictionary(
    path: Path,
) -> tuple[ProjectTranslationDictionary, str]:
    payload = path.read_bytes()
    dictionary = ProjectTranslationDictionary.model_validate_json(payload)
    return dictionary, hashlib.sha256(payload).hexdigest()
