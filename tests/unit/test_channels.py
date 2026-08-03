"""Tests for conservative channel classification."""

import pytest

from ewp_transcripts.config import ChannelsConfig
from ewp_transcripts.domain import ChannelMetrics, WarningCode
from ewp_transcripts.domain.enums import ChannelMode
from ewp_transcripts.media.channels import classify_channels


def _metrics(**overrides: float | int) -> ChannelMetrics:
    values: dict[str, float | int] = {
        "sample_rate_hz": 16000,
        "analyzed_samples_per_channel": 160000,
        "window_ms": 500,
        "windows": 20,
        "correlation": 0.0,
        "normalized_difference_rms": 1.0,
        "left_rms_dbfs": -24.0,
        "right_rms_dbfs": -24.0,
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


def test_structural_mono_does_not_need_metrics() -> None:
    result = classify_channels(original_channels=1, metrics=None, config=ChannelsConfig())

    assert result.detected_mode is ChannelMode.MONO
    assert result.selected_channel_index == 0


@pytest.mark.parametrize(
    ("correlation", "normalized_difference"),
    [(0.9999948496, 0.0032097624), (0.9999993372, 0.0011513833)],
)
def test_recorded_near_dual_mono_cases_are_classified(
    correlation: float,
    normalized_difference: float,
) -> None:
    metrics = _metrics(
        correlation=correlation,
        normalized_difference_rms=normalized_difference,
        channel_rms_difference_db=0.001,
        both_active_ratio=0.95,
    )

    result = classify_channels(
        original_channels=2,
        metrics=metrics,
        config=ChannelsConfig(),
    )

    assert result.detected_mode is ChannelMode.DUAL_MONO
    assert result.selected_channel_index == 0


def test_recorded_split_speaker_case_is_classified() -> None:
    metrics = _metrics(
        correlation=-0.00034489,
        normalized_difference_rms=1.366208,
        left_only_ratio=0.5368,
        right_only_ratio=0.4070,
        both_active_ratio=0.0386,
        neither_active_ratio=0.0176,
    )

    result = classify_channels(
        original_channels=2,
        metrics=metrics,
        config=ChannelsConfig(),
    )

    assert result.detected_mode is ChannelMode.SPLIT_SPEAKERS
    assert result.selected_channel_index is None


def test_recorded_mixed_stereo_case_is_classified() -> None:
    metrics = _metrics(
        correlation=0.571719,
        normalized_difference_rms=0.841335,
        channel_rms_difference_db=2.40638,
        left_only_ratio=0.00474,
        right_only_ratio=0.00474,
        both_active_ratio=0.9763,
        neither_active_ratio=0.0142,
    )

    result = classify_channels(
        original_channels=2,
        metrics=metrics,
        config=ChannelsConfig(),
    )

    assert result.detected_mode is ChannelMode.MIXED_STEREO


def test_borderline_stereo_is_ambiguous_and_uses_one_channel() -> None:
    metrics = _metrics(
        correlation=0.8,
        normalized_difference_rms=0.05,
        left_only_ratio=0.1,
        right_only_ratio=0.1,
        both_active_ratio=0.7,
        neither_active_ratio=0.1,
    )

    result = classify_channels(
        original_channels=2,
        metrics=metrics,
        config=ChannelsConfig(),
    )

    assert result.detected_mode is ChannelMode.AMBIGUOUS
    assert result.processing_mode is ChannelMode.DUAL_MONO
    assert result.selected_channel_index == 0
    assert result.warnings[0].code is WarningCode.CHANNEL_CLASSIFICATION_AMBIGUOUS


def test_implausible_forced_mode_is_visible() -> None:
    result = classify_channels(
        original_channels=1,
        metrics=None,
        config=ChannelsConfig(mode=ChannelMode.SPLIT_SPEAKERS),
    )

    assert result.processing_mode is ChannelMode.SPLIT_SPEAKERS
    assert result.warnings[0].code is WarningCode.CHANNEL_MODE_OVERRIDE_IMPLAUSIBLE
