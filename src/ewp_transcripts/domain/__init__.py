"""Stable domain types used by application services and adapters."""

from ewp_transcripts.domain.enums import DiagnosticStatus
from ewp_transcripts.domain.models import DiagnosticCheck, DoctorResult

__all__ = ["DiagnosticCheck", "DiagnosticStatus", "DoctorResult"]
