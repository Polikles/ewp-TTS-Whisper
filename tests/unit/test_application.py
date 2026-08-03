"""Tests for composed application services."""

from pathlib import Path

from ewp_transcripts.application import inspect_input
from ewp_transcripts.config import ApplicationConfig, ChannelsConfig, GroupingConfig
from ewp_transcripts.domain import AudioStream, ChannelMetrics, MediaProbeResult
from ewp_transcripts.domain.enums import ChannelMode


def test_inspect_input_composes_discovery_grouping_and_inspection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "show-Ada.wav").write_bytes(b"ada")
    (tmp_path / "show-Jan.wav").write_bytes(b"jan")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    def probe(path: Path) -> MediaProbeResult:
        stream = AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=48000,
            channels=2,
            duration_ms=1000,
        )
        return MediaProbeResult(
            path=path,
            format_names=("wav",),
            duration_ms=1000,
            audio_streams=(stream,),
        )

    metrics = ChannelMetrics(
        sample_rate_hz=16000,
        analyzed_samples_per_channel=16000,
        window_ms=500,
        windows=2,
        correlation=0.9999,
        normalized_difference_rms=0.001,
        left_rms_dbfs=-20.0,
        right_rms_dbfs=-20.0,
        left_peak_dbfs=-1.0,
        right_peak_dbfs=-1.0,
        clipping_sample_ratio=0.0,
        channel_rms_difference_db=0.0,
        left_activity_threshold_dbfs=-50.0,
        right_activity_threshold_dbfs=-50.0,
        left_only_ratio=0.0,
        right_only_ratio=0.0,
        both_active_ratio=1.0,
        neither_active_ratio=0.0,
    )
    from ewp_transcripts import application

    original_inspect = application.inspect_episode

    def inspect_with_adapters(episode, **kwargs):
        return original_inspect(
            episode,
            probe=probe,
            **kwargs,
        )

    monkeypatch.setattr(application, "inspect_episode", inspect_with_adapters)
    monkeypatch.setattr(application, "measure_file_channels", lambda path: metrics)
    config = ApplicationConfig(
        grouping=GroupingConfig(speaker_suffix_separator="-"),
        channels=ChannelsConfig(),
    )

    result = inspect_input(tmp_path, config=config)

    assert [path.reason.value for path in result.discovery.skipped] == ["unsupported-extension"]
    assert [episode.job_id for episode in result.episodes] == ["show"]
    assert [source.speaker_label for source in result.episodes[0].sources] == ["Ada", "Jan"]
    assert all(
        source.channel_mode is ChannelMode.DUAL_MONO for source in result.episodes[0].sources
    )
