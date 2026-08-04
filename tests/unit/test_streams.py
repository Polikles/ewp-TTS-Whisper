"""Tests for deterministic grouped-source and split-channel stream planning."""

import pytest

from ewp_transcripts.domain import (
    AudioStream,
    ChannelClassification,
    EpisodeInspection,
    InspectedSource,
    SourceFingerprint,
)
from ewp_transcripts.domain.enums import ChannelMode
from ewp_transcripts.domain.errors import UnsupportedPipelineScopeError
from ewp_transcripts.streams import plan_speaker_streams


def test_grouped_sources_keep_order_labels_and_selected_channels() -> None:
    inspection = _inspection(
        _source("anna.wav", speaker_id="speaker_001", label="Anna", channels=1),
        _source(
            "jan.wav",
            speaker_id="speaker_002",
            label="Jan",
            channels=2,
            detected=ChannelMode.DUAL_MONO,
            processing=ChannelMode.DUAL_MONO,
            selected=0,
        ),
    )

    streams = plan_speaker_streams(inspection)

    assert [stream.source_id for stream in streams] == ["source_001", "source_002"]
    assert [stream.speaker_id for stream in streams] == ["speaker_001", "speaker_002"]
    assert [stream.speaker_label for stream in streams] == ["Anna", "Jan"]
    assert [stream.speaker_source for stream in streams] == ["filename", "filename"]
    assert [stream.channel_index for stream in streams] == [0, 0]


def test_split_stereo_creates_two_default_speakers_for_one_source() -> None:
    inspection = _inspection(
        _source(
            "split.wav",
            speaker_id="speaker_001",
            channels=2,
            detected=ChannelMode.SPLIT_SPEAKERS,
            processing=ChannelMode.SPLIT_SPEAKERS,
            selected=None,
        )
    )

    streams = plan_speaker_streams(inspection)

    assert [stream.source_id for stream in streams] == ["source_001", "source_001"]
    assert [stream.speaker_id for stream in streams] == ["speaker_001", "speaker_002"]
    assert [stream.speaker_label for stream in streams] == ["Speaker1", "Speaker2"]
    assert [stream.speaker_source for stream in streams] == [
        "channel_metadata",
        "channel_metadata",
    ]
    assert [stream.channel_index for stream in streams] == [0, 1]


@pytest.mark.parametrize("mode", [ChannelMode.MIXED_STEREO, ChannelMode.SPLIT_SPEAKERS])
def test_group_rejects_nonselected_stereo_modes(mode: ChannelMode) -> None:
    inspection = _inspection(
        _source(
            "first.wav",
            speaker_id="speaker_001",
            channels=2,
            detected=mode,
            processing=mode,
            selected=None,
        ),
        _source("second.wav", speaker_id="speaker_002", channels=1),
    )

    with pytest.raises(UnsupportedPipelineScopeError, match="Grouped-source"):
        plan_speaker_streams(inspection)


def test_ambiguous_fallback_uses_its_selected_channel() -> None:
    inspection = _inspection(
        _source(
            "ambiguous.wav",
            speaker_id="speaker_001",
            channels=2,
            detected=ChannelMode.AMBIGUOUS,
            processing=ChannelMode.DUAL_MONO,
            selected=0,
        )
    )

    assert plan_speaker_streams(inspection)[0].channel_index == 0


def _inspection(*sources: InspectedSource) -> EpisodeInspection:
    return EpisodeInspection(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=sources,
    )


def _source(
    filename: str,
    *,
    speaker_id: str,
    channels: int,
    label: str | None = None,
    detected: ChannelMode = ChannelMode.MONO,
    processing: ChannelMode = ChannelMode.MONO,
    selected: int | None = 0,
) -> InspectedSource:
    return InspectedSource(
        fingerprint=SourceFingerprint(
            path=f"/inputs/{filename}",
            filename=filename,
            size_bytes=100,
            sha256="a" * 64,
        ),
        stream=AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=48000,
            channels=channels,
        ),
        duration_ms=1000,
        channel_mode=detected,
        channel_classification=ChannelClassification(
            original_channels=channels,
            detected_mode=detected,
            processing_mode=processing,
            selected_channel_index=selected,
        ),
        speaker_id=speaker_id,
        speaker_label=label,
        speaker_source="filename" if label is not None else "default",
    )
