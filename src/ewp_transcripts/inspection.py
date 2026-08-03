"""Media inspection, group compatibility validation, and episode identity."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path

from ewp_transcripts.config import ChannelsConfig
from ewp_transcripts.domain import (
    ApplicationWarning,
    AudioStream,
    ChannelMetrics,
    EpisodeCandidate,
    EpisodeInspection,
    InspectedSource,
    MediaProbeResult,
    WarningCode,
)
from ewp_transcripts.domain.errors import (
    DurationMismatchError,
    MultipleAudioStreamsError,
    SampleRateMismatchError,
)
from ewp_transcripts.media import measure_file_channels, probe_media
from ewp_transcripts.media.channels import classify_channels

MediaProbe = Callable[[Path], MediaProbeResult]
ChannelAnalyzer = Callable[[Path], ChannelMetrics]


def _select_audio_stream(
    result: MediaProbeResult,
    selected_streams: Mapping[Path, int],
) -> AudioStream:
    requested = selected_streams.get(result.path)
    if requested is not None:
        for stream in result.audio_streams:
            if stream.index == requested:
                return stream
        raise MultipleAudioStreamsError(
            f"Selected audio stream {requested} is unavailable: {result.path}"
        )
    if len(result.audio_streams) != 1:
        raise MultipleAudioStreamsError(
            f"Input has multiple audio streams and requires an explicit selection: {result.path}"
        )
    return result.audio_streams[0]


def calculate_episode_signature(
    job_id: str,
    sources: tuple[InspectedSource, ...],
) -> str:
    """Hash the canonical ordered source descriptors used by one episode."""

    descriptor = {
        "job_id": job_id,
        "sources": [
            {
                "channel_mode": source.channel_mode.value,
                "sha256": source.fingerprint.sha256,
                "speaker_id": source.speaker_id,
                "speaker_label": source.speaker_label,
                "stream_index": source.stream.index,
            }
            for source in sources
        ],
    }
    serialized = json.dumps(
        descriptor,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(serialized).hexdigest()


def inspect_episode(
    episode: EpisodeCandidate,
    *,
    probe: MediaProbe = probe_media,
    selected_streams: Mapping[Path, int] | None = None,
    channel_analyzer: ChannelAnalyzer = measure_file_channels,
    channels_config: ChannelsConfig | None = None,
    duration_warning_ms: int = 100,
    duration_error_ms: int = 500,
    allow_duration_mismatch: bool = False,
) -> EpisodeInspection:
    """Probe and validate one candidate without modifying source files."""

    if duration_warning_ms < 0 or duration_error_ms < duration_warning_ms:
        raise ValueError("invalid duration thresholds")
    stream_selection = selected_streams or {}
    effective_channels_config = channels_config or ChannelsConfig()
    inspected: list[InspectedSource] = []
    channel_warnings: list[ApplicationWarning] = []
    for position, grouped_source in enumerate(episode.sources, start=1):
        result = probe(grouped_source.fingerprint.path)
        stream = _select_audio_stream(result, stream_selection)
        metrics = channel_analyzer(result.path) if stream.channels == 2 else None
        classification = classify_channels(
            original_channels=stream.channels,
            metrics=metrics,
            config=effective_channels_config,
        )
        channel_warnings.extend(classification.warnings)
        inspected.append(
            InspectedSource(
                fingerprint=grouped_source.fingerprint,
                stream=stream,
                duration_ms=(
                    stream.duration_ms if stream.duration_ms is not None else result.duration_ms
                ),
                channel_mode=classification.processing_mode,
                channel_classification=classification,
                speaker_id=f"speaker_{position:03d}",
                speaker_label=grouped_source.speaker_label,
            )
        )

    sample_rates = {source.stream.sample_rate_hz for source in inspected}
    if len(sample_rates) != 1:
        raise SampleRateMismatchError(
            f"Grouped sources have different sample rates: {episode.job_id}"
        )

    durations = [source.duration_ms for source in inspected]
    duration_difference = max(durations) - min(durations)
    if duration_difference > duration_error_ms and not allow_duration_mismatch:
        raise DurationMismatchError(
            f"Grouped-source duration difference exceeds {duration_error_ms} ms: {episode.job_id}"
        )

    warnings: list[ApplicationWarning] = list(channel_warnings)
    if duration_difference > duration_warning_ms:
        warnings.append(
            ApplicationWarning(
                code=WarningCode.INPUT_DURATION_MISMATCH,
                message="Grouped sources have different durations.",
                context={
                    "difference_ms": duration_difference,
                    "override_used": duration_difference > duration_error_ms,
                },
            )
        )

    sources = tuple(inspected)
    return EpisodeInspection(
        job_id=episode.job_id,
        episode_signature_sha256=calculate_episode_signature(episode.job_id, sources),
        duration_ms=max(durations),
        sample_rate_hz=next(iter(sample_rates)),
        sources=sources,
        warnings=tuple(warnings),
    )
