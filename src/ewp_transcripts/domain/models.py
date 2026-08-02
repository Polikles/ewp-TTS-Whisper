"""Typed foundational domain models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.enums import (
    ChannelMode,
    DiagnosticStatus,
    DiscoverySkipReason,
    WarningCode,
    WarningSeverity,
)


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


class SourceFingerprint(BaseModel):
    """Content identity calculated without modifying the source file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    filename: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class GroupedSource(BaseModel):
    """Fingerprinted source with an optional filename-derived speaker label."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fingerprint: SourceFingerprint
    speaker_label: str | None = None


class EpisodeCandidate(BaseModel):
    """Filename-derived episode candidate before media compatibility checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str = Field(min_length=1)
    sources: tuple[GroupedSource, ...] = Field(min_length=1)


class ApplicationWarning(BaseModel):
    """Structured warning that does not modify source media."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: WarningCode
    severity: WarningSeverity = WarningSeverity.WARNING
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class InspectedSource(BaseModel):
    """Fingerprinted source paired with one selected audio stream."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fingerprint: SourceFingerprint
    stream: AudioStream
    duration_ms: int = Field(ge=0)
    channel_mode: ChannelMode = ChannelMode.AUTO
    speaker_id: str = Field(pattern=r"^speaker_[0-9]{3,}$")
    speaker_label: str | None = None


class EpisodeInspection(BaseModel):
    """Validated grouped-source metadata before channel classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str = Field(min_length=1)
    episode_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_ms: int = Field(ge=0)
    sample_rate_hz: int = Field(gt=0)
    sources: tuple[InspectedSource, ...] = Field(min_length=1)
    warnings: tuple[ApplicationWarning, ...] = ()
