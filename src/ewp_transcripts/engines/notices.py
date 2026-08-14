"""Narrow suppression for accepted third-party backend notices."""

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
def suppress_accepted_backend_notices() -> Iterator[None]:
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
            warnings.filterwarnings(
                "ignore",
                message=r"std\(\): degrees of freedom is <= 0\..*",
                category=UserWarning,
                module=r"pyannote\.audio\.models\.blocks\.pooling",
            )
            yield
    finally:
        for logger, level in zip(loggers, previous_levels, strict=True):
            logger.setLevel(level)
