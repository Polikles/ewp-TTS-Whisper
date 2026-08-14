"""Public package interface for EWP-transcripts."""

from importlib.metadata import PackageNotFoundError, version


def _installed_version() -> str:
    try:
        return version("ewp-transcripts")
    except PackageNotFoundError:
        return "0.1.1"


__version__ = _installed_version()

__all__ = ["__version__"]
