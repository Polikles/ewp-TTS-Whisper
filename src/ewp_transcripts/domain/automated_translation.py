"""Provider-neutral automated-translation request and response contracts."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.translation import Language, TranslationStyle


class AutomatedTranslationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class TranslationContextUnit(AutomatedTranslationModel):
    unit_id: str = Field(pattern=r"^tu_[0-9]{6,}$")
    speaker_id: str = Field(pattern=r"^speaker_[0-9]{3,}$")
    source_text: str = Field(min_length=1, pattern=r".*\S.*")


class AutomatedTranslationRequest(AutomatedTranslationModel):
    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_language: Language
    target_language: Language
    style: TranslationStyle
    preceding_context: tuple[TranslationContextUnit, ...] = ()
    unit: TranslationContextUnit
    following_context: tuple[TranslationContextUnit, ...] = ()


class AutomatedTranslationUsage(AutomatedTranslationModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd_micros: int | None = Field(default=None, ge=0)


class AutomatedTranslationResponse(AutomatedTranslationModel):
    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    unit_id: str = Field(pattern=r"^tu_[0-9]{6,}$")
    target_text: str = Field(min_length=1, pattern=r".*\S.*")
    usage: AutomatedTranslationUsage | None = None
    warning_codes: tuple[str, ...] = ()


class AutomatedTranslationProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def endpoint_kind(self) -> Literal["local", "cloud", "mock"]: ...

    @property
    def endpoint_identity(self) -> str: ...

    @property
    def provenance_parameters(self) -> dict[str, str | int | float | bool | None]: ...

    def prompt_sha256(self, prompt_id: str) -> str: ...

    def translate(
        self,
        request: AutomatedTranslationRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> AutomatedTranslationResponse: ...
