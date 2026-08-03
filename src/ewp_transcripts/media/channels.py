"""Conservative, measurable channel-topology classification."""

from __future__ import annotations

from ewp_transcripts.config import ChannelsConfig
from ewp_transcripts.domain import (
    ApplicationWarning,
    ChannelClassification,
    ChannelMetrics,
    WarningCode,
)
from ewp_transcripts.domain.enums import ChannelMode


def _implausible_override(
    original_channels: int,
    requested: ChannelMode,
) -> tuple[ApplicationWarning, ...]:
    if original_channels == 1 and requested is not ChannelMode.MONO:
        return (
            ApplicationWarning(
                code=WarningCode.CHANNEL_MODE_OVERRIDE_IMPLAUSIBLE,
                message="The forced channel mode is implausible for a mono stream.",
                context={"original_channels": original_channels, "requested": requested.value},
            ),
        )
    if original_channels != 2 and requested in {
        ChannelMode.DUAL_MONO,
        ChannelMode.SPLIT_SPEAKERS,
        ChannelMode.MIXED_STEREO,
    }:
        return (
            ApplicationWarning(
                code=WarningCode.CHANNEL_MODE_OVERRIDE_IMPLAUSIBLE,
                message="The forced channel mode expects a two-channel stream.",
                context={"original_channels": original_channels, "requested": requested.value},
            ),
        )
    return ()


def classify_channels(
    *,
    original_channels: int,
    metrics: ChannelMetrics | None,
    config: ChannelsConfig,
) -> ChannelClassification:
    """Classify one stream conservatively, falling back to one channel when ambiguous."""

    requested = config.mode
    if requested is not ChannelMode.AUTO:
        return ChannelClassification(
            original_channels=original_channels,
            detected_mode=requested,
            processing_mode=requested,
            selected_channel_index=0 if requested is ChannelMode.DUAL_MONO else None,
            warnings=_implausible_override(original_channels, requested),
        )

    if original_channels == 1:
        return ChannelClassification(
            original_channels=1,
            detected_mode=ChannelMode.MONO,
            processing_mode=ChannelMode.MONO,
            selected_channel_index=0,
        )
    if original_channels != 2 or metrics is None:
        return _ambiguous(original_channels, config)

    if (
        metrics.correlation >= config.dual_mono_min_correlation
        and metrics.channel_rms_difference_db <= config.dual_mono_max_rms_difference_db
        and metrics.normalized_difference_rms <= config.dual_mono_max_normalized_difference
    ):
        return ChannelClassification(
            original_channels=2,
            detected_mode=ChannelMode.DUAL_MONO,
            processing_mode=ChannelMode.DUAL_MONO,
            selected_channel_index=0,
        )

    exclusive_ratio = metrics.left_only_ratio + metrics.right_only_ratio
    if (
        metrics.correlation <= config.split_max_correlation
        and metrics.left_only_ratio >= config.split_min_each_exclusive_ratio
        and metrics.right_only_ratio >= config.split_min_each_exclusive_ratio
        and exclusive_ratio >= config.split_min_total_exclusive_ratio
    ):
        return ChannelClassification(
            original_channels=2,
            detected_mode=ChannelMode.SPLIT_SPEAKERS,
            processing_mode=ChannelMode.SPLIT_SPEAKERS,
        )

    if (
        metrics.both_active_ratio >= config.mixed_min_both_active_ratio
        and metrics.normalized_difference_rms >= config.mixed_min_normalized_difference
    ):
        return ChannelClassification(
            original_channels=2,
            detected_mode=ChannelMode.MIXED_STEREO,
            processing_mode=ChannelMode.MIXED_STEREO,
        )

    return _ambiguous(original_channels, config)


def _ambiguous(
    original_channels: int,
    config: ChannelsConfig,
) -> ChannelClassification:
    processing_mode = config.ambiguous_fallback
    return ChannelClassification(
        original_channels=original_channels,
        detected_mode=ChannelMode.AMBIGUOUS,
        processing_mode=processing_mode,
        selected_channel_index=0,
        warnings=(
            ApplicationWarning(
                code=WarningCode.CHANNEL_CLASSIFICATION_AMBIGUOUS,
                message="Channel topology is ambiguous; one channel will be used.",
                context={"fallback": processing_mode.value},
            ),
        ),
    )
