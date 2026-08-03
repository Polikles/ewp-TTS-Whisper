"""Backend-neutral ASR and alignment models plus structural engine interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EngineModel(BaseModel):
    """Strict immutable value returned across an external-engine boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class EngineModelInfo(EngineModel):
    role: Literal["asr", "alignment"]
    name: str = Field(min_length=1)
    revision: str | None = None
    local_path: Path | None = None
    library_versions: dict[str, str] = Field(default_factory=dict)


class TranscriptionSegment(EngineModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("transcription segment end must not precede start")
        return self


class TranscriptionDraft(EngineModel):
    language: str = Field(min_length=1)
    segments: tuple[TranscriptionSegment, ...]

    @model_validator(mode="after")
    def validate_chronology(self) -> Self:
        if any(
            current.start_ms < previous.start_ms
            for previous, current in zip(self.segments, self.segments[1:], strict=False)
        ):
            raise ValueError("transcription segments must be sorted chronologically")
        return self


class AlignedWord(EngineModel):
    text: str = Field(min_length=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("aligned word end must not precede start")
        return self


class AlignedSegment(EngineModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    words: tuple[AlignedWord, ...]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("aligned segment end must not precede start")
        for word in self.words:
            if word.start_ms is not None and word.start_ms < self.start_ms:
                raise ValueError("aligned word starts before its segment")
            if word.end_ms is not None and word.end_ms > self.end_ms:
                raise ValueError("aligned word ends after its segment")
        return self


class AlignedTranscript(EngineModel):
    language: str = Field(min_length=1)
    segments: tuple[AlignedSegment, ...]

    @model_validator(mode="after")
    def validate_chronology(self) -> Self:
        if any(
            current.start_ms < previous.start_ms
            for previous, current in zip(self.segments, self.segments[1:], strict=False)
        ):
            raise ValueError("aligned segments must be sorted chronologically")
        return self


class AsrEngine(Protocol):
    """Replaceable ASR stage; implementations must load dependencies lazily."""

    @property
    def model_info(self) -> EngineModelInfo: ...

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str,
        batch_size: int,
    ) -> TranscriptionDraft: ...

    def close(self) -> None:
        """Release stage resources, including GPU model references."""
        ...


class AlignmentEngine(Protocol):
    """Replaceable word-alignment stage independent from backend dictionaries."""

    @property
    def model_info(self) -> EngineModelInfo: ...

    def align(
        self,
        audio_path: Path,
        transcription: TranscriptionDraft,
        *,
        language: str,
    ) -> AlignedTranscript: ...

    def close(self) -> None:
        """Release stage resources, including GPU model references."""
        ...
