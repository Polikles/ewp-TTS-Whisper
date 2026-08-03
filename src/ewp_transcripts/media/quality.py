"""Warning-only policy for lightweight audio-quality measurements."""

from ewp_transcripts.config import QualityConfig
from ewp_transcripts.domain import ApplicationWarning, ChannelMetrics, WarningCode


def quality_warnings(
    metrics: ChannelMetrics,
    *,
    original_channels: int,
    config: QualityConfig,
) -> tuple[ApplicationWarning, ...]:
    """Return structured warnings without modifying or repairing source audio."""

    if not config.analyze:
        return ()
    warnings: list[ApplicationWarning] = []
    if config.detect_clipping and metrics.clipping_sample_ratio >= config.clipping_min_sample_ratio:
        warnings.append(
            ApplicationWarning(
                code=WarningCode.AUDIO_CLIPPING,
                message="Audio contains samples at or near PCM full scale.",
                context={
                    "clipping_sample_ratio": metrics.clipping_sample_ratio,
                    "threshold": config.clipping_min_sample_ratio,
                },
            )
        )

    loudest_rms = max(metrics.left_rms_dbfs, metrics.right_rms_dbfs)
    if config.detect_low_level and loudest_rms <= config.low_level_max_rms_dbfs:
        warnings.append(
            ApplicationWarning(
                code=WarningCode.AUDIO_LOW_LEVEL,
                message="Overall audio level is low.",
                context={
                    "loudest_rms_dbfs": loudest_rms,
                    "threshold_dbfs": config.low_level_max_rms_dbfs,
                },
            )
        )

    if (
        config.detect_channel_imbalance
        and original_channels == 2
        and metrics.channel_rms_difference_db >= config.channel_imbalance_min_rms_difference_db
    ):
        warnings.append(
            ApplicationWarning(
                code=WarningCode.AUDIO_CHANNEL_IMBALANCE,
                message="Stereo channels have materially different RMS levels.",
                context={
                    "difference_db": metrics.channel_rms_difference_db,
                    "threshold_db": config.channel_imbalance_min_rms_difference_db,
                },
            )
        )

    if (
        config.detect_silence_ratio
        and metrics.neither_active_ratio >= config.high_silence_min_ratio
    ):
        warnings.append(
            ApplicationWarning(
                code=WarningCode.AUDIO_HIGH_SILENCE_RATIO,
                message="A high proportion of analysis windows contain no active channel.",
                context={
                    "silence_ratio": metrics.neither_active_ratio,
                    "threshold": config.high_silence_min_ratio,
                },
            )
        )
    return tuple(warnings)
