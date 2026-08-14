"""Narrow suppression for accepted third-party model-loading notices."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Iterator
from contextlib import contextmanager

_LIGHTNING_MIGRATION_LOGGERS = (
    "lightning.pytorch.utilities.migration.utils",
    "pytorch_lightning.utilities.migration.utils",
)


@contextmanager
def suppress_accepted_model_loading_notices() -> Iterator[None]:
    """Hide only dependency notices whose behavior is already intentional."""

    loggers = tuple(logging.getLogger(name) for name in _LIGHTNING_MIGRATION_LOGGERS)
    previous_levels = tuple(logger.level for logger in loggers)
    for logger in loggers:
        logger.setLevel(logging.WARNING)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"TensorFloat-32 \(TF32\) has been disabled.*",
                category=UserWarning,
                module=r"pyannote\.audio\.utils\.reproducibility",
            )
            yield
    finally:
        for logger, level in zip(loggers, previous_levels, strict=True):
            logger.setLevel(level)
