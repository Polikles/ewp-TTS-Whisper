"""Stable application-facing operations shared by user interfaces."""

from pathlib import Path

from ewp_transcripts import __version__
from ewp_transcripts.config import ApplicationConfig, load_config
from ewp_transcripts.discovery import discover_input, group_discovered_files
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import DiscoveryResult, DoctorResult, DryRunResult, InspectionResult
from ewp_transcripts.inspection import inspect_episode
from ewp_transcripts.media import measure_file_channels
from ewp_transcripts.storage import (
    find_existing_results,
    plan_job_outputs,
    resolve_output_directory,
)


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
            channel_analyzer=measure_file_channels,
            channels_config=effective_config.channels,
            quality_config=effective_config.quality,
            duration_warning_ms=effective_config.grouping.duration_warning_ms,
            duration_error_ms=effective_config.grouping.duration_error_ms,
            allow_duration_mismatch=allow_duration_mismatch,
        )
        for episode in episodes
    )
    return InspectionResult(discovery=discovery, episodes=inspections)


def dry_run(
    input_path: str | Path,
    *,
    config: ApplicationConfig | None = None,
    output_directory: Path | None = None,
    force: bool = False,
    allow_duration_mismatch: bool = False,
) -> DryRunResult:
    """Build a complete batch execution plan without creating outputs or workdirs."""

    effective_config = load_config() if config is None else config
    inspection = inspect_input(
        input_path,
        config=effective_config,
        allow_duration_mismatch=allow_duration_mismatch,
    )
    destination = resolve_output_directory(
        inspection.discovery,
        config=effective_config.outputs,
        explicit_directory=output_directory,
    )
    existing = find_existing_results(destination)
    jobs = tuple(
        plan_job_outputs(
            episode,
            output_directory=destination,
            existing_results=existing,
            force=force,
            config=effective_config.outputs,
        )
        for episode in inspection.episodes
    )
    return DryRunResult(
        inspection=inspection,
        output_directory=destination,
        jobs=jobs,
    )
