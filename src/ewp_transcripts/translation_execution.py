"""Bounded automated-translation execution with sanitized metrics."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ewp_transcripts.automated_translation import validate_automated_translation_response
from ewp_transcripts.domain.automated_translation import (
    AutomatedTranslationProvider,
    AutomatedTranslationRequest,
    AutomatedTranslationResponse,
)
from ewp_transcripts.domain.errors import (
    InvalidTranslationResponseError,
    PermanentTranslationHttpError,
    PermanentTranslationProviderError,
    RetryableTranslationProviderError,
)


@dataclass(frozen=True, slots=True)
class TranslationExecutionPolicy:
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
class TranslationExecutionMetrics:
    attempts: int
    retries: int
    elapsed_ms: int
    request_count: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd_micros: int | None


@dataclass(frozen=True, slots=True)
class TranslationExecutionOutcome:
    response: AutomatedTranslationResponse
    metrics: TranslationExecutionMetrics


def execute_translation_call(
    provider: AutomatedTranslationProvider,
    request: AutomatedTranslationRequest,
    *,
    policy: TranslationExecutionPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> TranslationExecutionOutcome:
    """Retry transient provider and response-contract failures within strict bounds."""

    policy = policy or TranslationExecutionPolicy()
    started = monotonic()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            response = provider.translate(request, timeout_seconds=policy.timeout_seconds)
            validate_automated_translation_response(request, response)
            usage = response.usage
            return TranslationExecutionOutcome(
                response=response,
                metrics=TranslationExecutionMetrics(
                    attempts=attempt,
                    retries=attempt - 1,
                    elapsed_ms=max(0, round((monotonic() - started) * 1000)),
                    request_count=attempt,
                    input_tokens=usage.input_tokens if usage else None,
                    output_tokens=usage.output_tokens if usage else None,
                    cost_usd_micros=usage.cost_usd_micros if usage else None,
                ),
            )
        except (RetryableTranslationProviderError, InvalidTranslationResponseError) as error:
            if attempt == policy.max_attempts:
                if isinstance(error, InvalidTranslationResponseError):
                    raise InvalidTranslationResponseError(
                        "Translation provider returned invalid responses after bounded retries"
                    ) from None
                raise RetryableTranslationProviderError(
                    "Translation provider failed after bounded retries"
                ) from None
            sleep(policy.retry_delay_seconds)
        except PermanentTranslationHttpError as error:
            raise PermanentTranslationProviderError(
                f"Translation provider rejected the request (http_status={error.status_code})"
            ) from None
        except PermanentTranslationProviderError:
            raise PermanentTranslationProviderError(
                "Translation provider reported a permanent failure"
            ) from None
    raise AssertionError("positive max_attempts guarantees a return or provider error")
