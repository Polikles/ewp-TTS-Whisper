"""Stable application-facing operations shared by user interfaces."""

from ewp_transcripts import __version__
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import DoctorResult


def application_version() -> str:
    """Return the installed EWP-transcripts version without loading ML backends."""

    return __version__


def doctor() -> DoctorResult:
    """Return lightweight, sanitized environment diagnostics."""

    return run_doctor()
