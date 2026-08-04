"""Replaceable speech-engine contracts with no eager ML imports."""

from ewp_transcripts.engines.protocols import (
    AlignedSegment,
    AlignedTranscript,
    AlignedWord,
    AlignmentEngine,
    AsrEngine,
    DiarizationEngine,
    DiarizationResult,
    DiarizationTurn,
    EngineModelInfo,
    TranscriptionDraft,
    TranscriptionSegment,
)
from ewp_transcripts.engines.pyannote import PyannoteDiarizationEngine
from ewp_transcripts.engines.whisperx import WhisperXAlignmentEngine, WhisperXAsrEngine

__all__ = [
    "AlignedSegment",
    "AlignedTranscript",
    "AlignedWord",
    "AlignmentEngine",
    "AsrEngine",
    "DiarizationEngine",
    "DiarizationResult",
    "DiarizationTurn",
    "EngineModelInfo",
    "PyannoteDiarizationEngine",
    "TranscriptionDraft",
    "TranscriptionSegment",
    "WhisperXAlignmentEngine",
    "WhisperXAsrEngine",
]
