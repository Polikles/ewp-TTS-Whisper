"""Tests for grouped media validation and episode signatures."""

from collections.abc import Callable
from pathlib import Path

import pytest

from ewp_transcripts.discovery import discover_input, group_discovered_files
from ewp_transcripts.domain import AudioStream, EpisodeCandidate, MediaProbeResult
from ewp_transcripts.domain.errors import (
    DurationMismatchError,
    MultipleAudioStreamsError,
    SampleRateMismatchError,
)
from ewp_transcripts.inspection import calculate_episode_signature, inspect_episode


def _episode(tmp_path: Path) -> EpisodeCandidate:
    for name in ("episode-anna.wav", "episode-jan.wav"):
        (tmp_path / name).write_bytes(name.encode())
    files = discover_input(tmp_path, supported_extensions=("wav",)).files
    return group_discovered_files(files)[0]


def _probe(
    durations: dict[str, int],
    sample_rates: dict[str, int] | None = None,
) -> Callable[[Path], MediaProbeResult]:
    def probe(path: Path) -> MediaProbeResult:
        sample_rate = (sample_rates or {}).get(path.name, 48000)
        stream = AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=sample_rate,
            channels=1,
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
