"""Closed value sets for the EWP-transcripts domain."""

from enum import StrEnum


class DiagnosticStatus(StrEnum):
    """Outcome of one environment diagnostic."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class LanguageMode(StrEnum):
    """Supported language selection modes."""

    POLISH = "pl"
    ENGLISH = "en"
    AUTO = "auto"


class ChannelMode(StrEnum):
    """Supported input channel interpretations."""

    AUTO = "auto"
    MONO = "mono"
    DUAL_MONO = "dual-mono"
    SPLIT_SPEAKERS = "split-speakers"
    MIXED_STEREO = "mixed-stereo"


class DiscoverySkipReason(StrEnum):
    """Reason a directory entry was not selected for inspection."""

    SYMLINK = "symlink"
    UNSUPPORTED_EXTENSION = "unsupported-extension"


class WarningSeverity(StrEnum):
    """Severity of a non-destructive application warning."""

    WARNING = "warning"


class WarningCode(StrEnum):
    """Warning codes introduced by current implementation phases."""

    INPUT_DURATION_MISMATCH = "INPUT_DURATION_MISMATCH"
