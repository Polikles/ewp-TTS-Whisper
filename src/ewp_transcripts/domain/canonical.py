"""Strict canonical result models matching ``schemas/results.schema.json``."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Sha256 = str
TimedEventKind = Literal["speech", "music", "laugh", "cough", "note"]


class CanonicalModel(BaseModel):
    """Frozen schema object that rejects undocumented fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CanonicalEpisode(CanonicalModel):
    episode_id: str = Field(min_length=1)
    episode_signature_sha256: Sha256 = Field(pattern=r"^[a-f0-9]{64}$")
    source_topology: Literal["single_file", "file_group", "split_channels"]
    language: Literal["pl", "en", "auto"]
    detected_language: str | None = None


class CanonicalSource(CanonicalModel):
    source_id: str = Field(pattern=r"^source_[0-9]{3,}$")
    input_path: str
    normalized_path: str
    filename: str = Field(min_length=1)
    sha256: Sha256 = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: Literal["audio", "video"]
    container: str | None = None
    codec: str | None = None
    stream_index: int = Field(ge=0)
    stream_language: str | None = None
    channel_selection: Literal["all", "mono"] | int
    duration_ms: int = Field(ge=0)
    sample_rate_hz: int = Field(ge=1)
    channel_count: int = Field(ge=1)
    speaker_id: str | None = None
    speaker_label: str | None = None

    @field_validator("channel_selection")
    @classmethod
    def validate_channel_index(
        cls, value: Literal["all", "mono"] | int
    ) -> Literal["all", "mono"] | int:
        if isinstance(value, int) and value < 0:
            raise ValueError("channel index must be non-negative")
        return value


class CanonicalSpeaker(CanonicalModel):
    speaker_id: str = Field(pattern=r"^speaker_[0-9]{3,}$")
    speaker_label: str = Field(min_length=1)
    speaker_source: Literal["explicit", "filename", "channel_metadata", "diarization", "default"]
    first_seen_ms: int = Field(ge=0)
    source_ids: tuple[str, ...] = ()

    @field_validator("source_ids")
    @classmethod
    def unique_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source_ids must be unique")
        return value


class CanonicalModelReference(CanonicalModel):
    role: Literal["asr", "alignment", "diarization", "vad"]
    name: str = Field(min_length=1)
    revision: str | None = None
    local_path: str | None = None


class CanonicalStage(CanonicalModel):
    name: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    duration_ms: int = Field(ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class CanonicalAudioQuality(CanonicalModel):
    integrated_lufs: float | None = None
    true_peak_dbfs: float | None = None
    rms_dbfs: float | None = None
    dc_offset: float | None = None
    clipping_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    silence_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    channel_level_difference_db: float | None = None


class CanonicalEnvironment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow", strict=True)

    os: str
    wsl_distribution: str | None = None
    python: str
    ffmpeg: str | None = None
    whisperx: str | None = None
    pytorch: str | None = None
    cuda_runtime: str | None = None
    device: str
    compute_type: str
    batch_size: int | None = Field(default=None, ge=1)
    peak_vram_bytes: int | None = Field(default=None, ge=0)


class CanonicalChannelAnalysis(CanonicalModel):
    requested_mode: Literal["auto", "mono", "dual_mono", "split_speakers", "mixed_stereo"]
    detected_mode: Literal["mono", "dual_mono", "split_speakers", "mixed_stereo", "ambiguous"]
    effective_mode: Literal["mono", "dual_mono", "split_speakers", "mixed_stereo"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metrics: dict[str, Any] = Field(default_factory=dict)


class CanonicalProcessing(CanonicalModel):
    preset: str
    effective_config: dict[str, Any]
    environment: CanonicalEnvironment
    models: tuple[CanonicalModelReference, ...]
    channel_analysis: CanonicalChannelAnalysis
    audio_quality: CanonicalAudioQuality
    stages: tuple[CanonicalStage, ...]


class CanonicalWord(CanonicalModel):
    word_id: str
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    timestamp_source: Literal["aligned", "interpolated", "segment_fallback"]
    speaker_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_time_order(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("word end_ms must not precede start_ms")
        return self


class CanonicalSegment(CanonicalModel):
    segment_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    kind: TimedEventKind = "speech"
    speaker_id: str | None
    overlap: bool
    active_speaker_ids: tuple[str, ...]
    source_ids: tuple[str, ...] = ()
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    words: tuple[CanonicalWord, ...]

    @model_validator(mode="after")
    def validate_segment(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("segment end_ms must not precede start_ms")
        if len(self.active_speaker_ids) != len(set(self.active_speaker_ids)):
            raise ValueError("active_speaker_ids must be unique")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("source_ids must be unique")
        if len({word.word_id for word in self.words}) != len(self.words):
            raise ValueError("word IDs must be unique within a segment")
        for word in self.words:
            if word.start_ms < self.start_ms or word.end_ms > self.end_ms:
                raise ValueError("word timestamps must fit inside their segment")
        return self


class CanonicalTranscript(CanonicalModel):
    language: str
    segments: tuple[CanonicalSegment, ...]

    @model_validator(mode="after")
    def validate_segments(self) -> Self:
        if len({segment.segment_id for segment in self.segments}) != len(self.segments):
            raise ValueError("segment IDs must be unique")
        if any(
            current.start_ms < previous.start_ms
            for previous, current in zip(self.segments, self.segments[1:], strict=False)
        ):
            raise ValueError("segments must be sorted chronologically")
        return self


class CanonicalWarning(CanonicalModel):
    code: str = Field(pattern=r"^[A-Z0-9_]+$")
    severity: Literal["info", "warning", "error"]
    message: str
    stage: str | None = None
    source_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class CanonicalError(CanonicalModel):
    code: str
    message: str
    stage: str
    exception_type: str | None = None
    safe_details: dict[str, Any] = Field(default_factory=dict)


class CanonicalOutput(CanonicalModel):
    format: Literal["results_json", "segments_json", "txt", "srt", "vtt"]
    path: str
    sha256: Sha256 | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class CanonicalResult(CanonicalModel):
    """Immutable source of truth for completed or terminal transcription output."""

    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    application_version: str = Field(min_length=1)
    run_id: UUID
    job_id: str = Field(min_length=1)
    status: Literal["running", "completed", "failed", "cancelled"]
    created_at: datetime
    completed_at: datetime | None = None
    result_version: int = Field(ge=1)
    episode: CanonicalEpisode
    sources: tuple[CanonicalSource, ...] = Field(min_length=1)
    speakers: tuple[CanonicalSpeaker, ...] = Field(min_length=1)
    processing: CanonicalProcessing
    transcript: CanonicalTranscript
    warnings: tuple[CanonicalWarning, ...]
    error: CanonicalError | None = None
    initial_outputs: tuple[CanonicalOutput, ...] = ()

    @model_validator(mode="after")
    def validate_references_and_status(self) -> Self:
        source_ids = [source.source_id for source in self.sources]
        speaker_ids = [speaker.speaker_id for speaker in self.speakers]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")
        if len(speaker_ids) != len(set(speaker_ids)):
            raise ValueError("speaker IDs must be unique")
        source_set = set(source_ids)
        speaker_set = set(speaker_ids)
        for speaker in self.speakers:
            if not set(speaker.source_ids) <= source_set:
                raise ValueError("speaker source_ids must reference known sources")
        for source in self.sources:
            if source.speaker_id is not None and source.speaker_id not in speaker_set:
                raise ValueError("source speaker_id must reference a known speaker")
        for segment in self.transcript.segments:
            referenced_speakers = set(segment.active_speaker_ids)
            if segment.speaker_id is not None:
                referenced_speakers.add(segment.speaker_id)
            referenced_speakers.update(
                word.speaker_id for word in segment.words if word.speaker_id is not None
            )
            if not referenced_speakers <= speaker_set:
                raise ValueError("transcript must reference known speakers")
            if not set(segment.source_ids) <= source_set:
                raise ValueError("segment source_ids must reference known sources")
        if self.status == "completed" and self.completed_at is None:
            raise ValueError("completed results require completed_at")
        if self.status == "completed" and self.error is not None:
            raise ValueError("completed results cannot contain an error")
        if self.status in {"failed", "cancelled"} and self.error is None:
            raise ValueError("failed and cancelled results require an error")
        return self


def load_canonical_result(path: Path) -> CanonicalResult:
    """Read and strictly validate one canonical JSON result."""

    return CanonicalResult.model_validate_json(path.read_text(encoding="utf-8"))
