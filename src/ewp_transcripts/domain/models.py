"""Typed foundational domain models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.enums import DiagnosticStatus, DiscoverySkipReason


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


class DiscoveredFile(BaseModel):
    """Regular file selected for later media inspection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    filename: str = Field(min_length=1)
    suffix: str


class SkippedPath(BaseModel):
    """Directory entry deliberately omitted during discovery."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    reason: DiscoverySkipReason


class DiscoveryResult(BaseModel):
    """Deterministic output of file discovery before media probing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_path: Path
    recursive: bool
    files: tuple[DiscoveredFile, ...]
    skipped: tuple[SkippedPath, ...]


class AudioStream(BaseModel):
    """Normalized metadata for one audio stream reported by ffprobe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int = Field(ge=0)
    codec: str = Field(min_length=1)
    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(gt=0)
    channel_layout: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    language: str | None = None
    title: str | None = None


class MediaProbeResult(BaseModel):
    """Normalized, non-destructive media inspection result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    format_names: tuple[str, ...]
    duration_ms: int = Field(ge=0)
    audio_streams: tuple[AudioStream, ...]
