"""Provider-neutral automated-correction contracts."""

from __future__ import annotations

from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

CorrectionCategory = Literal[
    "asr_lexical",
    "proper_name",
    "punctuation",
    "capitalization",
    "sentence_boundary",
]


class CorrectionModel(BaseModel):
    """Frozen strict model for one correction-provider boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CorrectionToken(CorrectionModel):
    # Editable tokens are zero-based. Preceding context deliberately uses negative
    # positions and following context uses positions beyond the editable length.
    local_index: int
    token_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)


class CorrectionChange(CorrectionModel):
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    before: str
    after: str
    category: CorrectionCategory

    @model_validator(mode="after")
    def validate_span(self) -> Self:
        if self.end_index < self.start_index:
            raise ValueError("correction change end must not precede its start")
        if not self.before and not self.after:
            raise ValueError("correction changes must insert, delete, or replace text")
        return self


class CorrectionRequest(CorrectionModel):
    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: Literal["pl", "en"]
    preceding_context: tuple[CorrectionToken, ...] = ()
    editable_tokens: tuple[CorrectionToken, ...] = Field(min_length=1)
    following_context: tuple[CorrectionToken, ...] = ()


class CorrectionUsage(CorrectionModel):
    """Optional non-secret usage reported by an adapter for one request."""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd_micros: int | None = Field(default=None, ge=0)


class CorrectionResponse(CorrectionModel):
    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(min_length=1)
    corrected_text: str = Field(min_length=1)
    proposed_changes: tuple[CorrectionChange, ...]
    usage: CorrectionUsage | None = None


class CorrectionProvider(Protocol):
    """Small adapter boundary shared by mock, local API, and cloud API providers."""

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

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse: ...
