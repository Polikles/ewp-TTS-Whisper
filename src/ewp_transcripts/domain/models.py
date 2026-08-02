"""Typed foundational domain models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.enums import DiagnosticStatus


class DiagnosticCheck(BaseModel):
    """One sanitized environment check returned by ``doctor``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    status: DiagnosticStatus
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class DoctorResult(BaseModel):
    """Complete lightweight environment diagnostic result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    application_version: str
    ready: bool
    checks: tuple[DiagnosticCheck, ...]
