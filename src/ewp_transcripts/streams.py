"""Deterministic independent-stream planning for source-based speakers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ewp_transcripts.domain import EpisodeInspection, InspectedSource
from ewp_transcripts.domain.enums import ChannelMode
from ewp_transcripts.domain.errors import UnsupportedPipelineScopeError


@dataclass(frozen=True, slots=True)
class SpeakerStream:
    """One independently prepared and transcribed speaker-bearing stream."""

    source: InspectedSource
    source_id: str
    speaker_id: str
    speaker_label: str
    speaker_source: Literal["filename", "channel_metadata", "default"]
    channel_index: int


def plan_speaker_streams(inspection: EpisodeInspection) -> tuple[SpeakerStream, ...]:
    """Map one inspected episode to stable source/channel speaker work items."""

    if len(inspection.sources) == 1:
        source = inspection.sources[0]
        if source.channel_classification.processing_mode is ChannelMode.SPLIT_SPEAKERS:
            if source.stream.channels != 2:
                raise UnsupportedPipelineScopeError(
                    "Split-speaker processing requires exactly two channels"
                )
            return tuple(
                SpeakerStream(
                    source=source,
                    source_id="source_001",
                    speaker_id=f"speaker_{channel + 1:03d}",
                    speaker_label=f"Speaker{channel + 1}",
                    speaker_source="default",
                    channel_index=channel,
                )
                for channel in range(2)
            )
        return (_source_stream(source, position=1),)

    streams = tuple(
        _source_stream(source, position=position)
        for position, source in enumerate(inspection.sources, start=1)
    )
    return streams


def _source_stream(source: InspectedSource, *, position: int) -> SpeakerStream:
    mode = source.channel_classification.processing_mode
    if mode not in {ChannelMode.MONO, ChannelMode.DUAL_MONO}:
        raise UnsupportedPipelineScopeError(
            "Grouped-source processing requires mono or one selected working channel"
        )
    channel_index = source.channel_classification.selected_channel_index
    if channel_index is None:
        raise UnsupportedPipelineScopeError("Source-based speaker has no selected channel")
    label = source.speaker_label or f"Speaker{position}"
    return SpeakerStream(
        source=source,
        source_id=f"source_{position:03d}",
        speaker_id=f"speaker_{position:03d}",
        speaker_label=label,
        speaker_source="filename" if source.speaker_label else "default",
        channel_index=channel_index,
    )
