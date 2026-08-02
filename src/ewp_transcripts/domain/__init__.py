"""Stable domain types used by application services and adapters."""

from ewp_transcripts.domain.enums import (
    DiagnosticStatus,
    DiscoverySkipReason,
    WarningCode,
    WarningSeverity,
)
from ewp_transcripts.domain.models import (
    ApplicationWarning,
    AudioStream,
    DiagnosticCheck,
    DiscoveredFile,
    DiscoveryResult,
    DoctorResult,
    EpisodeCandidate,
    EpisodeInspection,
    GroupedSource,
    InspectedSource,
    MediaProbeResult,
    SkippedPath,
    SourceFingerprint,
)

__all__ = [
    "ApplicationWarning",
    "AudioStream",
    "DiagnosticCheck",
    "DiagnosticStatus",
    "DiscoveredFile",
    "DiscoveryResult",
    "DiscoverySkipReason",
    "DoctorResult",
    "EpisodeCandidate",
    "EpisodeInspection",
    "GroupedSource",
    "InspectedSource",
    "MediaProbeResult",
    "SkippedPath",
    "SourceFingerprint",
    "WarningCode",
    "WarningSeverity",
]
