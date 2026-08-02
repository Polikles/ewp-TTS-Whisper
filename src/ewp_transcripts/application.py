"""Stable application-facing operations shared by user interfaces."""

from ewp_transcripts import __version__


def application_version() -> str:
    """Return the installed EWP-transcripts version without loading ML backends."""

    return __version__
