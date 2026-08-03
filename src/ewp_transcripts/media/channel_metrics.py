"""Pure stereo-similarity and channel-activity measurements."""

from __future__ import annotations

import math
from collections.abc import Iterable

from ewp_transcripts.domain import ChannelMetrics

_PCM16_FULL_SCALE = 32768.0
_DBFS_FLOOR = -120.0


def _dbfs(sum_squares: float, count: int) -> float:
    if count == 0 or sum_squares <= 0:
        return _DBFS_FLOOR
    rms = math.sqrt(sum_squares / count) / _PCM16_FULL_SCALE
    return max(_DBFS_FLOOR, 20.0 * math.log10(rms))


def measure_stereo_channels(
    samples: Iterable[tuple[int, int]],
    *,
    sample_rate_hz: int,
    window_ms: int = 500,
    activity_floor_dbfs: float = -50.0,
    activity_dynamic_range_db: float = 35.0,
) -> ChannelMetrics:
    """Measure decoded signed-16-bit stereo samples without classifying them."""

    if sample_rate_hz < 1 or window_ms < 1:
        raise ValueError("sample rate and window size must be positive")
    window_size = max(1, round(sample_rate_hz * window_ms / 1000))
    count = 0
    sum_left = 0.0
    sum_right = 0.0
    sum_left_squares = 0.0
    sum_right_squares = 0.0
    sum_products = 0.0
    sum_difference_squares = 0.0
    window_count = 0
    window_left_squares = 0.0
    window_right_squares = 0.0
    window_levels: list[tuple[float, float]] = []

    for left, right in samples:
        left_value = float(left)
        right_value = float(right)
        count += 1
        window_count += 1
        sum_left += left_value
        sum_right += right_value
        sum_left_squares += left_value * left_value
        sum_right_squares += right_value * right_value
        sum_products += left_value * right_value
        difference = left_value - right_value
        sum_difference_squares += difference * difference
        window_left_squares += left_value * left_value
        window_right_squares += right_value * right_value
        if window_count == window_size:
            window_levels.append(
                (
                    _dbfs(window_left_squares, window_count),
                    _dbfs(window_right_squares, window_count),
                )
            )
            window_count = 0
            window_left_squares = 0.0
            window_right_squares = 0.0

    if window_count:
        window_levels.append(
            (
                _dbfs(window_left_squares, window_count),
                _dbfs(window_right_squares, window_count),
            )
        )
    if count == 0:
        raise ValueError("at least one stereo sample is required")

    centered_left = sum_left_squares - (sum_left * sum_left / count)
    centered_right = sum_right_squares - (sum_right * sum_right / count)
    centered_product = sum_products - (sum_left * sum_right / count)
    denominator = math.sqrt(max(0.0, centered_left) * max(0.0, centered_right))
    correlation = centered_product / denominator if denominator else 0.0
    correlation = max(-1.0, min(1.0, correlation))
    normalized_difference = math.sqrt(
        sum_difference_squares / max(sum_left_squares, sum_right_squares, 1.0)
    )
    left_rms = _dbfs(sum_left_squares, count)
    right_rms = _dbfs(sum_right_squares, count)

    peak_left = max(level[0] for level in window_levels)
    peak_right = max(level[1] for level in window_levels)
    left_threshold = max(activity_floor_dbfs, peak_left - activity_dynamic_range_db)
    right_threshold = max(activity_floor_dbfs, peak_right - activity_dynamic_range_db)
    state_counts = {"left": 0, "right": 0, "both": 0, "neither": 0}
    for left_level, right_level in window_levels:
        left_active = left_level >= left_threshold
        right_active = right_level >= right_threshold
        if left_active and right_active:
            state_counts["both"] += 1
        elif left_active:
            state_counts["left"] += 1
        elif right_active:
            state_counts["right"] += 1
        else:
            state_counts["neither"] += 1

    windows = len(window_levels)
    return ChannelMetrics(
        sample_rate_hz=sample_rate_hz,
        analyzed_samples_per_channel=count,
        window_ms=window_ms,
        windows=windows,
        correlation=correlation,
        normalized_difference_rms=normalized_difference,
        left_rms_dbfs=left_rms,
        right_rms_dbfs=right_rms,
        channel_rms_difference_db=abs(left_rms - right_rms),
        left_activity_threshold_dbfs=left_threshold,
        right_activity_threshold_dbfs=right_threshold,
        left_only_ratio=state_counts["left"] / windows,
        right_only_ratio=state_counts["right"] / windows,
        both_active_ratio=state_counts["both"] / windows,
        neither_active_ratio=state_counts["neither"] / windows,
    )
