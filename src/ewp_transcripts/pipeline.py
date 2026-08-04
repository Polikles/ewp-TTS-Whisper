"""Transcription-stage orchestration independent from CLI and ML implementations."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ewp_transcripts import __version__
from ewp_transcripts.composition import merge_speaker_transcripts
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain import EpisodeInspection, InspectedSource, JobReservation, WorkDirectory
from ewp_transcripts.domain.canonical import (
    CanonicalAudioQuality,
    CanonicalChannelAnalysis,
    CanonicalEnvironment,
    CanonicalEpisode,
    CanonicalModelReference,
    CanonicalProcessing,
    CanonicalResult,
    CanonicalSource,
    CanonicalSpeaker,
    CanonicalStage,
    CanonicalWarning,
)
from ewp_transcripts.domain.enums import ChannelMode, JobStateStatus
from ewp_transcripts.domain.errors import UnsupportedPipelineScopeError
from ewp_transcripts.engines import AlignmentEngine, AsrEngine, EngineModelInfo
from ewp_transcripts.media import prepare_working_audio
from ewp_transcripts.normalization import NormalizedTranscript, normalize_single_speaker
from ewp_transcripts.streams import SpeakerStream, plan_speaker_streams

AudioPreparer = Callable[..., Path]
Clock = Callable[[], float]
Now = Callable[[], datetime]
AsrEngineFactory = Callable[[], AsrEngine]
AlignmentEngineFactory = Callable[[], AlignmentEngine]


@dataclass(frozen=True, slots=True)
class ProcessedSpeakerStream:
    """Normalized output and provenance from one independent stream pass."""

    normalized: NormalizedTranscript
    asr_model: EngineModelInfo
    alignment_model: EngineModelInfo
    stages: tuple[CanonicalStage, ...]


def run_source_speaker_pipeline(
    inspection: EpisodeInspection,
    reservation: JobReservation,
    workspace: WorkDirectory,
    *,
    config: ApplicationConfig,
    environment: CanonicalEnvironment,
    asr_engine_factory: AsrEngineFactory,
    alignment_engine_factory: AlignmentEngineFactory,
    audio_preparer: AudioPreparer = prepare_working_audio,
    clock: Clock = time.perf_counter,
    now: Now = lambda: datetime.now(UTC),
) -> CanonicalResult:
    """Run independent source/channel streams and compose one shared timeline."""

    _validate_job_identity(inspection, reservation, workspace)
    streams = plan_speaker_streams(inspection)
    if len(streams) < 2:
        raise UnsupportedPipelineScopeError(
            "Source-speaker pipeline requires at least two independent streams"
        )

    processed: list[ProcessedSpeakerStream] = []
    stages: list[CanonicalStage] = []
    for stream_index, stream in enumerate(streams, start=1):
        stream_result = process_speaker_stream(
            stream,
            workspace,
            config=config,
            asr_engine=asr_engine_factory(),
            alignment_engine=alignment_engine_factory(),
            working_filename=f"stream_{stream_index:03d}-working.wav",
            audio_preparer=audio_preparer,
            clock=clock,
        )
        processed.append(stream_result)
        stage_details = {
            "stream_index": stream_index,
            "source_id": stream.source_id,
            "speaker_id": stream.speaker_id,
            "channel_index": stream.channel_index,
        }
        stages.extend(
            stage.model_copy(update={"details": stage_details}) for stage in stream_result.stages
        )

    transcript = merge_speaker_transcripts(
        tuple(stream_result.normalized.transcript for stream_result in processed)
    )
    models = _consistent_models(tuple(processed))
    state = reservation.state
    outputs = reservation.plan.outputs
    assert state is not None and outputs is not None
    split_channels = len(inspection.sources) == 1
    sources = (
        (_canonical_source(inspection.sources[0], channel_selection="all"),)
        if split_channels
        else tuple(
            _canonical_source(
                stream.source,
                source_id=stream.source_id,
                speaker_id=stream.speaker_id,
                speaker_label=stream.speaker_label,
            )
            for stream in streams
        )
    )
    speakers = tuple(
        CanonicalSpeaker(
            speaker_id=stream.speaker_id,
            speaker_label=stream.speaker_label,
            speaker_source=stream.speaker_source,
            first_seen_ms=(
                stream_result.normalized.transcript.segments[0].start_ms
                if stream_result.normalized.transcript.segments
                else 0
            ),
            source_ids=(stream.source_id,),
        )
        for stream, stream_result in zip(streams, processed, strict=True)
    )
    warnings = (
        *_inspection_warnings(inspection),
        *(warning for stream_result in processed for warning in stream_result.normalized.warnings),
    )

    return CanonicalResult(
        schema_version="1.0",
        application_version=__version__,
        run_id=state.run_id,
        job_id=inspection.job_id,
        status="completed",
        created_at=state.created_at,
        completed_at=now(),
        result_version=outputs.result_version,
        episode=CanonicalEpisode(
            episode_id=inspection.job_id,
            episode_signature_sha256=inspection.episode_signature_sha256,
            source_topology="split_channels" if split_channels else "file_group",
            language=config.general.language.value,
            detected_language=transcript.language,
        ),
        sources=sources,
        speakers=speakers,
        processing=CanonicalProcessing(
            preset=config.general.preset,
            effective_config=config.model_dump(mode="json"),
            environment=environment,
            models=models,
            channel_analysis=_multi_channel_analysis(inspection, config),
            audio_quality=_audio_quality(inspection.sources[0]),
            stages=tuple(stages),
        ),
        transcript=transcript,
        warnings=warnings,
    )


def run_single_speaker_pipeline(
    inspection: EpisodeInspection,
    reservation: JobReservation,
    workspace: WorkDirectory,
    *,
    config: ApplicationConfig,
    environment: CanonicalEnvironment,
    asr_engine: AsrEngine,
    alignment_engine: AlignmentEngine,
    audio_preparer: AudioPreparer = prepare_working_audio,
    clock: Clock = time.perf_counter,
    now: Now = lambda: datetime.now(UTC),
) -> CanonicalResult:
    """Run the one-source/one-speaker path and return a completed result."""

    source = _validate_scope(inspection, reservation, workspace, config)
    state = reservation.state
    outputs = reservation.plan.outputs
    assert state is not None and outputs is not None
    processed = process_speaker_stream(
        SpeakerStream(
            source=source,
            source_id="source_001",
            speaker_id="speaker_001",
            speaker_label=source.speaker_label or "Speaker1",
            speaker_source="filename" if source.speaker_label else "default",
            channel_index=source.channel_classification.selected_channel_index or 0,
        ),
        workspace,
        config=config,
        asr_engine=asr_engine,
        alignment_engine=alignment_engine,
        working_filename="source_001-working.wav",
        audio_preparer=audio_preparer,
        clock=clock,
    )
    normalized = processed.normalized
    stages = processed.stages
    speaker_label = source.speaker_label or "Speaker1"
    first_seen_ms = (
        normalized.transcript.segments[0].start_ms if normalized.transcript.segments else 0
    )
    warnings = (*_inspection_warnings(inspection), *normalized.warnings)

    return CanonicalResult(
        schema_version="1.0",
        application_version=__version__,
        run_id=state.run_id,
        job_id=inspection.job_id,
        status="completed",
        created_at=state.created_at,
        completed_at=now(),
        result_version=outputs.result_version,
        episode=CanonicalEpisode(
            episode_id=inspection.job_id,
            episode_signature_sha256=inspection.episode_signature_sha256,
            source_topology="single_file",
            language=config.general.language.value,
            detected_language=normalized.transcript.language,
        ),
        sources=(
            _canonical_source(
                source,
                speaker_id="speaker_001",
                speaker_label=speaker_label,
            ),
        ),
        speakers=(
            CanonicalSpeaker(
                speaker_id="speaker_001",
                speaker_label=speaker_label,
                speaker_source="filename" if source.speaker_label else "default",
                first_seen_ms=first_seen_ms,
                source_ids=("source_001",),
            ),
        ),
        processing=CanonicalProcessing(
            preset=config.general.preset,
            effective_config=config.model_dump(mode="json"),
            environment=environment,
            models=(
                _model_reference(processed.asr_model),
                _model_reference(processed.alignment_model),
            ),
            channel_analysis=_channel_analysis(source, config),
            audio_quality=_audio_quality(source),
            stages=stages,
        ),
        transcript=normalized.transcript,
        warnings=warnings,
    )


def process_speaker_stream(
    stream: SpeakerStream,
    workspace: WorkDirectory,
    *,
    config: ApplicationConfig,
    asr_engine: AsrEngine,
    alignment_engine: AlignmentEngine,
    working_filename: str,
    audio_preparer: AudioPreparer = prepare_working_audio,
    clock: Clock = time.perf_counter,
) -> ProcessedSpeakerStream:
    """Prepare, transcribe, align, and normalize one independent speaker stream."""

    stages: list[CanonicalStage] = []
    working_audio = workspace.path / working_filename
    start = clock()
    audio_preparer(
        stream.source.fingerprint.path,
        working_audio,
        stream_index=stream.source.stream.index,
        channel_index=stream.channel_index,
    )
    stages.append(_completed_stage("prepare_audio", start, clock))

    asr_info = asr_engine.model_info
    start = clock()
    try:
        draft = asr_engine.transcribe(
            working_audio,
            language=config.general.language.value,
            batch_size=config.models.batch_size,
        )
    finally:
        asr_engine.close()
    stages.append(_completed_stage("transcribe", start, clock))

    alignment_info = alignment_engine.model_info
    start = clock()
    try:
        aligned = alignment_engine.align(
            working_audio,
            draft,
            language=draft.language,
        )
    finally:
        alignment_engine.close()
    stages.append(_completed_stage("align", start, clock))

    start = clock()
    normalized = normalize_single_speaker(
        aligned,
        speaker_id=stream.speaker_id,
        source_id=stream.source_id,
    )
    stages.append(_completed_stage("normalize", start, clock))
    return ProcessedSpeakerStream(
        normalized=normalized,
        asr_model=asr_info,
        alignment_model=alignment_info,
        stages=tuple(stages),
    )


def _validate_scope(
    inspection: EpisodeInspection,
    reservation: JobReservation,
    workspace: WorkDirectory,
    config: ApplicationConfig,
) -> InspectedSource:
    if len(inspection.sources) != 1:
        raise UnsupportedPipelineScopeError("Single-speaker pipeline requires exactly one source")
    if config.diarization.speaker_count != 1:
        raise UnsupportedPipelineScopeError("Single-speaker pipeline requires speaker_count = 1")
    source = inspection.sources[0]
    if source.channel_classification.processing_mode not in {
        ChannelMode.MONO,
        ChannelMode.DUAL_MONO,
    }:
        raise UnsupportedPipelineScopeError(
            "Single-speaker pipeline supports mono or one selected working channel"
        )
    _validate_job_identity(inspection, reservation, workspace)
    return source


def _validate_job_identity(
    inspection: EpisodeInspection,
    reservation: JobReservation,
    workspace: WorkDirectory,
) -> None:
    if reservation.state is None or reservation.plan.outputs is None:
        raise UnsupportedPipelineScopeError("Pipeline requires a processing reservation")
    if reservation.state.status is not JobStateStatus.RUNNING:
        raise UnsupportedPipelineScopeError("Pipeline requires a running reservation")
    if (
        reservation.state.job_id != inspection.job_id
        or reservation.state.episode_signature_sha256 != inspection.episode_signature_sha256
        or workspace.job_id != inspection.job_id
        or workspace.run_id != reservation.state.run_id
    ):
        raise UnsupportedPipelineScopeError("Pipeline inputs do not describe the same job")


def _completed_stage(name: str, start: float, clock: Clock) -> CanonicalStage:
    duration_ms = max(0, round((clock() - start) * 1000))
    return CanonicalStage(name=name, status="completed", duration_ms=duration_ms)


def _canonical_source(
    source: InspectedSource,
    *,
    source_id: str = "source_001",
    speaker_id: str | None = None,
    speaker_label: str | None = None,
    channel_selection: Literal["all", "mono"] | int | None = None,
) -> CanonicalSource:
    selection = channel_selection
    if selection is None:
        selection = (
            "mono"
            if source.stream.channels == 1
            else source.channel_classification.selected_channel_index
        )
    if selection is None:
        selection = "all"
    return CanonicalSource(
        source_id=source_id,
        input_path=str(source.fingerprint.path),
        normalized_path=str(source.fingerprint.path.absolute()),
        filename=source.fingerprint.filename,
        sha256=source.fingerprint.sha256,
        size_bytes=source.fingerprint.size_bytes,
        media_type="audio",
        container=source.fingerprint.path.suffix.lstrip(".") or None,
        codec=source.stream.codec,
        stream_index=source.stream.index,
        stream_language=source.stream.language,
        channel_selection=selection,
        duration_ms=source.duration_ms,
        sample_rate_hz=source.stream.sample_rate_hz,
        channel_count=source.stream.channels,
        speaker_id=speaker_id,
        speaker_label=speaker_label,
    )


def _consistent_models(
    processed: tuple[ProcessedSpeakerStream, ...],
) -> tuple[CanonicalModelReference, ...]:
    first = processed[0]
    expected = (first.asr_model, first.alignment_model)
    for stream_result in processed[1:]:
        if (stream_result.asr_model, stream_result.alignment_model) != expected:
            raise UnsupportedPipelineScopeError(
                "Independent streams used inconsistent model provenance"
            )
    return tuple(_model_reference(model) for model in expected)


def _multi_channel_analysis(
    inspection: EpisodeInspection, config: ApplicationConfig
) -> CanonicalChannelAnalysis:
    primary = _channel_analysis(inspection.sources[0], config)
    metrics = {
        "sources": [
            {
                "source_id": f"source_{index:03d}",
                "filename": source.fingerprint.filename,
                "detected_mode": _detected_channel_mode(
                    source.channel_classification.detected_mode
                ),
                "effective_mode": _effective_channel_mode(
                    source.channel_classification.processing_mode
                ),
                "metrics": (
                    source.channel_metrics.model_dump(mode="json")
                    if source.channel_metrics is not None
                    else {}
                ),
            }
            for index, source in enumerate(inspection.sources, start=1)
        ]
    }
    return primary.model_copy(update={"metrics": metrics})


def _model_reference(info: EngineModelInfo) -> CanonicalModelReference:
    return CanonicalModelReference(
        role=info.role,
        name=info.name,
        revision=info.revision,
        local_path=str(info.local_path) if info.local_path is not None else None,
    )


def _channel_analysis(
    source: InspectedSource, config: ApplicationConfig
) -> CanonicalChannelAnalysis:
    classification = source.channel_classification
    return CanonicalChannelAnalysis(
        requested_mode=_requested_channel_mode(config.channels.mode),
        detected_mode=_detected_channel_mode(classification.detected_mode),
        effective_mode=_effective_channel_mode(classification.processing_mode),
        metrics=(
            source.channel_metrics.model_dump(mode="json")
            if source.channel_metrics is not None
            else {}
        ),
    )


def _audio_quality(source: InspectedSource) -> CanonicalAudioQuality:
    metrics = source.channel_metrics
    if metrics is None:
        return CanonicalAudioQuality()
    return CanonicalAudioQuality(
        rms_dbfs=(metrics.left_rms_dbfs + metrics.right_rms_dbfs) / 2,
        clipping_ratio=metrics.clipping_sample_ratio,
        silence_ratio=metrics.neither_active_ratio,
        channel_level_difference_db=metrics.channel_rms_difference_db,
    )


def _inspection_warnings(inspection: EpisodeInspection) -> tuple[CanonicalWarning, ...]:
    return tuple(
        CanonicalWarning(
            code=warning.code.value,
            severity="warning",
            message=warning.message,
            stage="inspect",
            context=warning.context,
        )
        for warning in inspection.warnings
    )


def _requested_channel_mode(
    mode: ChannelMode,
) -> Literal["auto", "mono", "dual_mono", "split_speakers", "mixed_stereo"]:
    if mode is ChannelMode.AUTO:
        return "auto"
    if mode is ChannelMode.MONO:
        return "mono"
    if mode is ChannelMode.DUAL_MONO:
        return "dual_mono"
    if mode is ChannelMode.SPLIT_SPEAKERS:
        return "split_speakers"
    if mode is ChannelMode.MIXED_STEREO:
        return "mixed_stereo"
    raise UnsupportedPipelineScopeError("Ambiguous cannot be a requested channel mode")


def _detected_channel_mode(
    mode: ChannelMode,
) -> Literal["mono", "dual_mono", "split_speakers", "mixed_stereo", "ambiguous"]:
    if mode is ChannelMode.MONO:
        return "mono"
    if mode is ChannelMode.DUAL_MONO:
        return "dual_mono"
    if mode is ChannelMode.SPLIT_SPEAKERS:
        return "split_speakers"
    if mode is ChannelMode.MIXED_STEREO:
        return "mixed_stereo"
    if mode is ChannelMode.AMBIGUOUS:
        return "ambiguous"
    raise UnsupportedPipelineScopeError("Auto cannot be a detected channel mode")


def _effective_channel_mode(
    mode: ChannelMode,
) -> Literal["mono", "dual_mono", "split_speakers", "mixed_stereo"]:
    if mode is ChannelMode.MONO:
        return "mono"
    if mode is ChannelMode.DUAL_MONO:
        return "dual_mono"
    if mode is ChannelMode.SPLIT_SPEAKERS:
        return "split_speakers"
    if mode is ChannelMode.MIXED_STEREO:
        return "mixed_stereo"
    raise UnsupportedPipelineScopeError("Effective channel mode must be concrete")
