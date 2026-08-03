"""Stable application-facing operations shared by user interfaces."""

from __future__ import annotations

import platform
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import UUID, uuid4

from ewp_transcripts import __version__
from ewp_transcripts.config import ApplicationConfig, load_config
from ewp_transcripts.discovery import discover_input, group_discovered_files
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import (
    DiscoveryResult,
    DoctorResult,
    DryRunResult,
    EpisodeInspection,
    InspectionResult,
    JobReservation,
)
from ewp_transcripts.domain.canonical import CanonicalEnvironment
from ewp_transcripts.domain.enums import JobStateStatus, PlanDecision
from ewp_transcripts.domain.errors import ApplicationError, UnsupportedPipelineScopeError
from ewp_transcripts.engines import AlignmentEngine, AsrEngine
from ewp_transcripts.engines.whisperx import WhisperXAlignmentEngine, WhisperXAsrEngine

# Re-exported here to keep user interfaces on the application boundary.
from ewp_transcripts.export_service import ExportFormat, ExportOutcome, export_result
from ewp_transcripts.inspection import inspect_episode
from ewp_transcripts.media import measure_file_channels
from ewp_transcripts.pipeline import run_single_speaker_pipeline
from ewp_transcripts.state import finalize_job_result, reserve_job, transition_job_state
from ewp_transcripts.storage import (
    find_existing_results,
    plan_job_outputs,
    resolve_output_directory,
)
from ewp_transcripts.workdirs import allocate_work_directory, cleanup_work_directory

__all__ = [
    "ExportFormat",
    "ExportOutcome",
    "application_version",
    "discover",
    "doctor",
    "dry_run",
    "export_result",
    "inspect_input",
    "transcribe_one",
]

AsrFactory = Callable[[ApplicationConfig], AsrEngine]
AlignmentFactory = Callable[[ApplicationConfig], AlignmentEngine]


@dataclass(frozen=True, slots=True)
class TranscriptionOutcome:
    """User-facing outcome of one complete transcription lifecycle."""

    decision: PlanDecision
    job_id: str
    result_path: Path
    exports: ExportOutcome | None = None


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
        language=effective_config.general.language,
        jobs=jobs,
    )


def transcribe_one(
    input_path: str | Path,
    *,
    config: ApplicationConfig,
    output_directory: Path | None = None,
    force: bool = False,
    allow_duration_mismatch: bool = False,
    run_id: UUID | None = None,
    asr_factory: AsrFactory | None = None,
    alignment_factory: AlignmentFactory | None = None,
) -> TranscriptionOutcome:
    """Run one Phase 5 single-source/single-speaker job through safe publication."""

    if config.diarization.speaker_count != 1:
        raise UnsupportedPipelineScopeError("Phase 5 transcribe requires speaker_count = 1")
    inspected = inspect_input(
        input_path,
        config=config,
        allow_duration_mismatch=allow_duration_mismatch,
    )
    if len(inspected.episodes) != 1:
        raise UnsupportedPipelineScopeError("Phase 5 transcribe requires exactly one episode")
    episode = inspected.episodes[0]
    destination = resolve_output_directory(
        inspected.discovery,
        config=config.outputs,
        explicit_directory=output_directory,
    )
    reservation = reserve_job(
        episode,
        output_directory=destination,
        run_id=run_id or uuid4(),
        force=force,
        config=config.outputs,
        lock_timeout_seconds=config.runtime.lock_timeout_seconds,
    )
    if reservation.plan.decision is PlanDecision.SKIP:
        existing = reservation.plan.existing_result
        assert existing is not None
        return TranscriptionOutcome(
            decision=PlanDecision.SKIP,
            job_id=episode.job_id,
            result_path=existing.path,
        )

    return _process_reservation(
        episode,
        reservation,
        config=config,
        asr_factory=asr_factory or _whisperx_asr,
        alignment_factory=alignment_factory or _whisperx_alignment,
    )


def _process_reservation(
    episode: EpisodeInspection,
    reservation: JobReservation,
    *,
    config: ApplicationConfig,
    asr_factory: AsrFactory,
    alignment_factory: AlignmentFactory,
) -> TranscriptionOutcome:
    state = reservation.state
    assert state is not None
    workspace = None
    published = False
    succeeded = False
    try:
        workspace = allocate_work_directory(
            config.runtime.work_root,
            run_id=state.run_id,
            job_id=episode.job_id,
        )
        result = run_single_speaker_pipeline(
            episode,
            reservation,
            workspace,
            config=config,
            environment=_runtime_environment(config),
            asr_engine=asr_factory(config),
            alignment_engine=alignment_factory(config),
        )
        result_path = finalize_job_result(
            reservation,
            result,
            lock_timeout_seconds=config.runtime.lock_timeout_seconds,
        )
        published = True
        formats = _configured_export_formats(config)
        exports = (
            export_result(
                result_path,
                formats=formats,
                subtitles_config=config.subtitles,
            )
            if formats
            else None
        )
        outcome = TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id=episode.job_id,
            result_path=result_path,
            exports=exports,
        )
        succeeded = True
        return outcome
    except Exception as error:
        if not published:
            transition_job_state(
                reservation,
                status=JobStateStatus.FAILED,
                failure_code=_failure_code(error),
                failure_message=_failure_message(error),
                lock_timeout_seconds=config.runtime.lock_timeout_seconds,
            )
        raise
    finally:
        retain = (
            config.runtime.keep_temp_on_success if succeeded else config.runtime.keep_temp_on_error
        )
        if workspace is not None and not retain:
            cleanup_work_directory(workspace)


def _configured_export_formats(config: ApplicationConfig) -> tuple[ExportFormat, ...]:
    return tuple(
        format_
        for enabled, format_ in (
            (config.outputs.generate_txt, ExportFormat.TXT),
            (config.outputs.generate_srt, ExportFormat.SRT),
            (config.outputs.generate_vtt, ExportFormat.VTT),
            (config.outputs.generate_segments_json, ExportFormat.SEGMENTS),
        )
        if enabled
    )


def _whisperx_asr(config: ApplicationConfig) -> AsrEngine:
    return WhisperXAsrEngine(
        config.models.asr_snapshot_path,
        revision=config.models.asr_revision,
        device=config.models.device,
        compute_type=config.models.compute_type,
    )


def _whisperx_alignment(config: ApplicationConfig) -> AlignmentEngine:
    return WhisperXAlignmentEngine(
        config.models.alignment_snapshot_path,
        revision=config.models.alignment_revision,
        device=config.models.device,
    )


def _runtime_environment(config: ApplicationConfig) -> CanonicalEnvironment:
    return CanonicalEnvironment(
        os=platform.platform(),
        wsl_distribution=None,
        python=platform.python_version(),
        whisperx=_distribution_version("whisperx"),
        pytorch=_distribution_version("torch"),
        device=config.models.device,
        compute_type=config.models.compute_type,
        batch_size=config.models.batch_size,
    )


def _distribution_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _failure_code(error: Exception) -> str:
    if isinstance(error, ApplicationError):
        name = type(error).__name__
        code = "".join(
            f"_{character}" if character.isupper() else character.upper() for character in name
        )
        return code.lstrip("_")
    return "TRANSCRIPTION_FAILED"


def _failure_message(error: Exception) -> str:
    if isinstance(error, ApplicationError) and str(error):
        return str(error)[:1000]
    return "Unexpected transcription failure"
