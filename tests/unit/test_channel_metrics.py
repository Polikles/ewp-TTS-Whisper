"""Tests for pure stereo channel measurements."""

from ewp_transcripts.media.channel_metrics import measure_stereo_channels


def _signal(amplitude: int, count: int) -> list[int]:
    return [amplitude if index % 2 else -amplitude for index in range(count)]


def test_exact_dual_mono_has_perfect_similarity() -> None:
    signal = _signal(10000, 400)

    metrics = measure_stereo_channels(zip(signal, signal, strict=True), sample_rate_hz=100)

    assert metrics.correlation == 1.0
    assert metrics.normalized_difference_rms == 0.0
    assert metrics.channel_rms_difference_db == 0.0
    assert metrics.left_peak_dbfs < 0.0
    assert metrics.clipping_sample_ratio == 0.0
    assert metrics.both_active_ratio == 1.0


def test_clipping_ratio_counts_samples_near_pcm_full_scale() -> None:
    samples = [(32767, -32768), (1000, -1000)]

    metrics = measure_stereo_channels(samples, sample_rate_hz=2)

    assert metrics.left_peak_dbfs < 0.0
    assert metrics.right_peak_dbfs == 0.0
    assert metrics.clipping_sample_ratio == 0.5


def test_split_activity_states_are_measured_per_window() -> None:
    active = _signal(10000, 10)
    silent = [0] * 10
    samples = [
        *zip(active, silent, strict=True),
        *zip(silent, active, strict=True),
        *zip(active, active, strict=True),
        *zip(silent, silent, strict=True),
    ]

    metrics = measure_stereo_channels(
        samples,
        sample_rate_hz=10,
        window_ms=1000,
    )

    assert metrics.left_only_ratio == 0.25
    assert metrics.right_only_ratio == 0.25
    assert metrics.both_active_ratio == 0.25
    assert metrics.neither_active_ratio == 0.25


def test_different_active_signals_are_not_dual_mono() -> None:
    left = _signal(10000, 400)
    right = [value // 2 if index % 3 else -value for index, value in enumerate(left)]

    metrics = measure_stereo_channels(zip(left, right, strict=True), sample_rate_hz=100)

    assert metrics.correlation < 0.995
    assert metrics.normalized_difference_rms > 0.0
