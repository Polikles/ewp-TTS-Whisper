"""Tests for warning-only audio-quality policy."""

from ewp_transcripts.config import QualityConfig
from ewp_transcripts.domain import ChannelMetrics, WarningCode
from ewp_transcripts.media.quality import quality_warnings


def _metrics(**overrides: float | int) -> ChannelMetrics:
    values: dict[str, float | int] = {
        "sample_rate_hz": 16000,
        "analyzed_samples_per_channel": 160000,
        "window_ms": 500,
        "windows": 20,
        "correlation": 0.5,
        "normalized_difference_rms": 0.5,
        "left_rms_dbfs": -20.0,
        "right_rms_dbfs": -20.0,
        "left_peak_dbfs": -1.0,
        "right_peak_dbfs": -1.0,
        "clipping_sample_ratio": 0.0,
        "channel_rms_difference_db": 0.0,
        "left_activity_threshold_dbfs": -50.0,
        "right_activity_threshold_dbfs": -50.0,
        "left_only_ratio": 0.0,
        "right_only_ratio": 0.0,
        "both_active_ratio": 1.0,
        "neither_active_ratio": 0.0,
    }
    values.update(overrides)
    return ChannelMetrics.model_validate(values)


def test_all_quality_conditions_emit_structured_warnings() -> None:
    metrics = _metrics(
        left_rms_dbfs=-42.0,
        right_rms_dbfs=-50.0,
        clipping_sample_ratio=0.001,
        channel_rms_difference_db=8.0,
        neither_active_ratio=0.75,
    )

    warnings = quality_warnings(metrics, original_channels=2, config=QualityConfig())

    assert [warning.code for warning in warnings] == [
        WarningCode.AUDIO_CLIPPING,
        WarningCode.AUDIO_LOW_LEVEL,
        WarningCode.AUDIO_CHANNEL_IMBALANCE,
        WarningCode.AUDIO_HIGH_SILENCE_RATIO,
    ]


def test_healthy_audio_has_no_quality_warning() -> None:
    assert quality_warnings(_metrics(), original_channels=2, config=QualityConfig()) == ()


def test_mono_does_not_emit_channel_imbalance() -> None:
    warnings = quality_warnings(
        _metrics(channel_rms_difference_db=20.0),
        original_channels=1,
        config=QualityConfig(),
    )

    assert WarningCode.AUDIO_CHANNEL_IMBALANCE not in {item.code for item in warnings}


def test_quality_analysis_can_be_disabled() -> None:
    warnings = quality_warnings(
        _metrics(clipping_sample_ratio=1.0),
        original_channels=2,
        config=QualityConfig(analyze=False),
    )

    assert warnings == ()
