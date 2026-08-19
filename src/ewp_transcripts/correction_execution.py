"""Bounded provider-call execution with sanitized operational metrics."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ewp_transcripts.correction import validate_correction_response
from ewp_transcripts.domain.correction import (
    CorrectionProvider,
    CorrectionRequest,
    CorrectionResponse,
)
from ewp_transcripts.domain.errors import RetryableCorrectionProviderError


@dataclass(frozen=True, slots=True)
class CorrectionExecutionPolicy:
    timeout_seconds: float = 60.0
    max_attempts: int = 3
    retry_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class CorrectionExecutionMetrics:
    attempts: int
    retries: int
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class CorrectionExecutionOutcome:
    response: CorrectionResponse
    metrics: CorrectionExecutionMetrics


def execute_correction_call(
    provider: CorrectionProvider,
    request: CorrectionRequest,
    *,
    policy: CorrectionExecutionPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> CorrectionExecutionOutcome:
    """Call an adapter with a per-attempt timeout and retry only explicit failures."""

    policy = policy or CorrectionExecutionPolicy()
    started = monotonic()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            response = provider.correct(request, timeout_seconds=policy.timeout_seconds)
            validate_correction_response(request, response)
            elapsed_ms = max(0, round((monotonic() - started) * 1000))
            return CorrectionExecutionOutcome(
                response=response,
                metrics=CorrectionExecutionMetrics(
                    attempts=attempt,
                    retries=attempt - 1,
                    elapsed_ms=elapsed_ms,
                ),
            )
        except RetryableCorrectionProviderError:
            if attempt == policy.max_attempts:
                raise
            sleep(policy.retry_delay_seconds)
    raise AssertionError("positive max_attempts guarantees a return or provider error")
