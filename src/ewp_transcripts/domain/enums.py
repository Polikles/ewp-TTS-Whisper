"""Closed value sets for the EWP-transcripts domain."""

from enum import StrEnum


class DiagnosticStatus(StrEnum):
    """Outcome of one environment diagnostic."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
