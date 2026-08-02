"""Stable application-facing operations shared by user interfaces."""

from pathlib import Path

from ewp_transcripts import __version__
from ewp_transcripts.config import ApplicationConfig, load_config
from ewp_transcripts.discovery import discover_input
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import DiscoveryResult, DoctorResult


def application_version() -> str:
    """Return the installed EWP-transcripts version without loading ML backends."""

    return __version__


def doctor() -> DoctorResult:
    """Return lightweight, sanitized environment diagnostics."""

    return run_doctor()


def discover(
    input_path: str | Path,
    *,
    config: ApplicationConfig | None = None,
) -> DiscoveryResult:
    """Discover candidate media paths using the resolved application configuration."""

    effective_config = load_config() if config is None else config
    return discover_input(
        input_path,
        recursive=effective_config.input.recursive,
        supported_extensions=effective_config.input.supported_audio,
    )
