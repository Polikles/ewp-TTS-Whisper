"""Stable domain types used by application services and adapters."""

from ewp_transcripts.domain.enums import DiagnosticStatus, DiscoverySkipReason
from ewp_transcripts.domain.models import (
    AudioStream,
    DiagnosticCheck,
    DiscoveredFile,
    DiscoveryResult,
    DoctorResult,
    EpisodeCandidate,
    GroupedSource,
    MediaProbeResult,
    SkippedPath,
    SourceFingerprint,
)

__all__ = [
    "AudioStream",
    "DiagnosticCheck",
    "DiagnosticStatus",
    "DiscoveredFile",
    "DiscoveryResult",
    "DiscoverySkipReason",
    "DoctorResult",
    "EpisodeCandidate",
    "GroupedSource",
    "MediaProbeResult",
    "SkippedPath",
    "SourceFingerprint",
]
