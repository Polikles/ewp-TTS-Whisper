"""Stable application-facing operations shared by user interfaces."""

from pathlib import Path

from ewp_transcripts import __version__
from ewp_transcripts.config import ApplicationConfig, load_config
from ewp_transcripts.discovery import discover_input, group_discovered_files
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import DiscoveryResult, DoctorResult, InspectionResult
from ewp_transcripts.inspection import inspect_episode


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


def inspect_input(
    input_path: str | Path,
    *,
    config: ApplicationConfig | None = None,
    allow_duration_mismatch: bool = False,
) -> InspectionResult:
    """Discover, group, probe, and classify input without loading ML models."""

    effective_config = load_config() if config is None else config
    discovery = discover(input_path, config=effective_config)
    episodes = group_discovered_files(
        discovery.files,
        separator=effective_config.grouping.speaker_suffix_separator,
        speaker_count=effective_config.diarization.speaker_count,
    )
    inspections = tuple(
        inspect_episode(
            episode,
            channels_config=effective_config.channels,
            duration_warning_ms=effective_config.grouping.duration_warning_ms,
            duration_error_ms=effective_config.grouping.duration_error_ms,
            allow_duration_mismatch=allow_duration_mismatch,
        )
        for episode in episodes
    )
    return InspectionResult(discovery=discovery, episodes=inspections)
