"""Stable domain types used by application services and adapters."""

from ewp_transcripts.domain.enums import DiagnosticStatus, DiscoverySkipReason
from ewp_transcripts.domain.models import (
    DiagnosticCheck,
    DiscoveredFile,
    DiscoveryResult,
    DoctorResult,
    SkippedPath,
)

__all__ = [
    "DiagnosticCheck",
    "DiagnosticStatus",
    "DiscoveredFile",
    "DiscoveryResult",
    "DiscoverySkipReason",
    "DoctorResult",
    "SkippedPath",
]
