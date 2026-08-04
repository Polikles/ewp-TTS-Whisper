"""Tests for grouped media validation and episode signatures."""

from collections.abc import Callable
from pathlib import Path

import pytest

from ewp_transcripts.discovery import discover_input, group_discovered_files
from ewp_transcripts.domain import (
    AudioStream,
    ChannelMetrics,
    DiscoveryResult,
    EpisodeCandidate,
    InspectionResult,
    MediaProbeResult,
)
from ewp_transcripts.domain.enums import ChannelMode, WarningCode
from ewp_transcripts.domain.errors import (
    DurationMismatchError,
    MultipleAudioStreamsError,
    SampleRateMismatchError,
)
from ewp_transcripts.inspection import (
    apply_explicit_speaker_labels,
    calculate_episode_signature,
    inspect_episode,
)


def _episode(tmp_path: Path) -> EpisodeCandidate:
    for name in ("episode-anna.wav", "episode-jan.wav"):
        (tmp_path / name).write_bytes(name.encode())
    files = discover_input(tmp_path, supported_extensions=("wav",)).files
    return group_discovered_files(files)[0]


def _probe(
    durations: dict[str, int],
    sample_rates: dict[str, int] | None = None,
    channels: int = 1,
) -> Callable[[Path], MediaProbeResult]:
    def probe(path: Path) -> MediaProbeResult:
        sample_rate = (sample_rates or {}).get(path.name, 48000)
        stream = AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=sample_rate,
            channels=channels,
            duration_ms=durations[path.name],
        )
        return MediaProbeResult(
            path=path,
            format_names=("wav",),
            duration_ms=durations[path.name],
            audio_streams=(stream,),
        )

    return probe


@pytest.mark.parametrize("difference_ms", [0, 100])
def test_duration_difference_through_100_ms_is_accepted(
    tmp_path: Path,
    difference_ms: int,
) -> None:
    episode = _episode(tmp_path)
    result = inspect_episode(
        episode,
        probe=_probe({"episode-anna.wav": 1000, "episode-jan.wav": 1000 + difference_ms}),
    )

    assert result.warnings == ()


@pytest.mark.parametrize("difference_ms", [101, 500])
def test_duration_difference_through_500_ms_warns(
    tmp_path: Path,
    difference_ms: int,
) -> None:
    episode = _episode(tmp_path)
    result = inspect_episode(
        episode,
        probe=_probe({"episode-anna.wav": 1000, "episode-jan.wav": 1000 + difference_ms}),
    )

    assert result.warnings[0].context["difference_ms"] == difference_ms
    assert result.warnings[0].context["override_used"] is False


def test_duration_difference_above_500_ms_requires_override(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    probe = _probe({"episode-anna.wav": 1000, "episode-jan.wav": 1501})

    with pytest.raises(DurationMismatchError):
        inspect_episode(episode, probe=probe)

    result = inspect_episode(episode, probe=probe, allow_duration_mismatch=True)
    assert result.warnings[0].context["override_used"] is True


def test_sample_rate_mismatch_is_rejected(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    probe = _probe(
        {"episode-anna.wav": 1000, "episode-jan.wav": 1000},
        {"episode-anna.wav": 48000, "episode-jan.wav": 44100},
    )

    with pytest.raises(SampleRateMismatchError):
        inspect_episode(episode, probe=probe)


def test_multiple_audio_streams_require_selection(tmp_path: Path) -> None:
    episode = _episode(tmp_path)

    def probe(path: Path) -> MediaProbeResult:
        streams = tuple(
            AudioStream(
                index=index,
                codec="flac",
                sample_rate_hz=48000,
                channels=1,
                duration_ms=1000,
            )
            for index in (0, 2)
        )
        return MediaProbeResult(
            path=path,
            format_names=("matroska",),
            duration_ms=1000,
            audio_streams=streams,
        )

    with pytest.raises(MultipleAudioStreamsError):
        inspect_episode(episode, probe=probe)

    selected = {source.fingerprint.path: 2 for source in episode.sources}
    result = inspect_episode(episode, probe=probe, selected_streams=selected)
    assert [source.stream.index for source in result.sources] == [2, 2]


def test_episode_signature_is_stable_and_source_order_sensitive(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    result = inspect_episode(
        episode,
        probe=_probe({"episode-anna.wav": 1000, "episode-jan.wav": 1000}),
    )

    assert (
        calculate_episode_signature(result.job_id, result.sources)
        == result.episode_signature_sha256
    )
    assert (
        calculate_episode_signature(result.job_id, tuple(reversed(result.sources)))
        != result.episode_signature_sha256
    )
    assert calculate_episode_signature("renamed", result.sources) != result.episode_signature_sha256
    assert [source.speaker_id for source in result.sources] == ["speaker_001", "speaker_002"]


def test_explicit_speaker_map_changes_label_provenance_and_signature(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    inspected = inspect_episode(
        episode,
        probe=_probe({"episode-anna.wav": 1000, "episode-jan.wav": 1000}),
    )
    result = InspectionResult(
        discovery=DiscoveryResult(
            input_path=tmp_path,
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=(inspected,),
    )

    updated = apply_explicit_speaker_labels(
        result,
        speaker_map={"episode-anna.wav": "Damian"},
    )

    assert updated.episodes[0].sources[0].speaker_label == "Damian"
    assert updated.episodes[0].sources[0].speaker_source == "explicit"
    assert updated.episodes[0].sources[1].speaker_source == "filename"
    assert updated.episodes[0].episode_signature_sha256 != inspected.episode_signature_sha256


def test_stereo_metrics_are_classified_and_enter_the_signature(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    metrics = ChannelMetrics(
        sample_rate_hz=16000,
        analyzed_samples_per_channel=160000,
        window_ms=500,
        windows=20,
        correlation=-0.001,
        normalized_difference_rms=1.3,
        left_rms_dbfs=-27.0,
        right_rms_dbfs=-28.0,
        left_peak_dbfs=-2.0,
        right_peak_dbfs=-3.0,
        clipping_sample_ratio=0.0,
        channel_rms_difference_db=1.0,
        left_activity_threshold_dbfs=-50.0,
        right_activity_threshold_dbfs=-50.0,
        left_only_ratio=0.5,
        right_only_ratio=0.4,
        both_active_ratio=0.05,
        neither_active_ratio=0.05,
    )

    result = inspect_episode(
        episode,
        probe=_probe(
            {"episode-anna.wav": 1000, "episode-jan.wav": 1000},
            channels=2,
        ),
        channel_analyzer=lambda path: metrics,
    )

    assert all(
        source.channel_classification.detected_mode is ChannelMode.SPLIT_SPEAKERS
        for source in result.sources
    )
    assert all(source.channel_metrics == metrics for source in result.sources)
    assert all(source.channel_mode is ChannelMode.SPLIT_SPEAKERS for source in result.sources)


def test_quality_warnings_are_attached_to_episode(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    metrics = ChannelMetrics(
        sample_rate_hz=16000,
        analyzed_samples_per_channel=16000,
        window_ms=500,
        windows=2,
        correlation=1.0,
        normalized_difference_rms=0.0,
        left_rms_dbfs=-40.0,
        right_rms_dbfs=-40.0,
        left_peak_dbfs=0.0,
        right_peak_dbfs=0.0,
        clipping_sample_ratio=0.01,
        channel_rms_difference_db=0.0,
        left_activity_threshold_dbfs=-50.0,
        right_activity_threshold_dbfs=-50.0,
        left_only_ratio=0.0,
        right_only_ratio=0.0,
        both_active_ratio=0.25,
        neither_active_ratio=0.75,
    )

    result = inspect_episode(
        episode,
        probe=_probe({"episode-anna.wav": 1000, "episode-jan.wav": 1000}),
        channel_analyzer=lambda path: metrics,
    )

    assert {warning.code for warning in result.warnings} == {
        WarningCode.AUDIO_CLIPPING,
        WarningCode.AUDIO_LOW_LEVEL,
        WarningCode.AUDIO_HIGH_SILENCE_RATIO,
    }
