"""Tests for narrowly scoped third-party notice suppression."""

import logging
import warnings

from ewp_transcripts.engines.notices import suppress_accepted_backend_notices


def test_suppresses_lightning_migration_info_and_restores_logger(caplog) -> None:
    logger = logging.getLogger("lightning.pytorch.utilities.migration.utils")
    original_level = logger.level

    with caplog.at_level(logging.INFO), suppress_accepted_backend_notices():
        logger.info("Lightning automatically upgraded your loaded checkpoint")

    assert "automatically upgraded" not in caplog.text
    assert logger.level == original_level


def test_suppresses_only_known_pyannote_tf32_warning() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with suppress_accepted_backend_notices():
            warnings.warn_explicit(
                "TensorFloat-32 (TF32) has been disabled for reproducibility.",
                UserWarning,
                filename="reproducibility.py",
                lineno=1,
                module="pyannote.audio.utils.reproducibility",
            )
            warnings.warn("unrelated backend warning", UserWarning, stacklevel=1)

    assert [str(item.message) for item in captured] == ["unrelated backend warning"]


def test_suppresses_only_known_pyannote_short_window_warning() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with suppress_accepted_backend_notices():
            warnings.warn_explicit(
                "std(): degrees of freedom is <= 0. Correction should be smaller.",
                UserWarning,
                filename="pooling.py",
                lineno=103,
                module="pyannote.audio.models.blocks.pooling",
            )
            warnings.warn("different numerical warning", UserWarning, stacklevel=1)

    assert [str(item.message) for item in captured] == ["different numerical warning"]
