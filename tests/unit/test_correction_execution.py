"""Tests for bounded correction-provider execution."""

from dataclasses import dataclass, field
from typing import Literal

import pytest

from ewp_transcripts.correction import DeterministicMockCorrectionProvider
from ewp_transcripts.correction_execution import (
    CorrectionExecutionPolicy,
    execute_correction_call,
)
from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionResponse, CorrectionToken
from ewp_transcripts.domain.errors import (
    InvalidCorrectionResponseError,
    PermanentCorrectionProviderError,
    RetryableCorrectionProviderError,
)


@dataclass
class _Provider:
    failures: list[Exception] = field(default_factory=list)
    calls: int = 0
    timeouts: list[float | None] = field(default_factory=list)

    provider_id: str = "test-provider"
    model_id: str = "test-model"
    endpoint_kind: Literal["local"] = "local"

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        self.calls += 1
        self.timeouts.append(timeout_seconds)
        if self.failures:
            raise self.failures.pop(0)
        return DeterministicMockCorrectionProvider().correct(request)


def _request() -> CorrectionRequest:
    return CorrectionRequest(
        operation_id="operation",
        prompt_id="prompt",
        language="pl",
        editable_tokens=(
            CorrectionToken(
                local_index=0,
                token_id="word_000001",
                text="tekst",
                speaker_id="speaker_001",
            ),
        ),
    )


def test_retryable_failures_are_bounded_and_reported() -> None:
    provider = _Provider(failures=[RetryableCorrectionProviderError("temporary")])
    sleeps: list[float] = []
    times = iter((10.0, 10.25))

    outcome = execute_correction_call(
        provider,
        _request(),
        policy=CorrectionExecutionPolicy(
            timeout_seconds=7.0,
            max_attempts=2,
            retry_delay_seconds=0.5,
        ),
        sleep=sleeps.append,
        monotonic=lambda: next(times),
    )

    assert provider.timeouts == [7.0, 7.0]
    assert sleeps == [0.5]
    assert outcome.metrics.attempts == 2
    assert outcome.metrics.retries == 1
    assert outcome.metrics.elapsed_ms == 250


def test_retryable_failure_stops_at_attempt_limit() -> None:
    provider = _Provider(
        failures=[
            RetryableCorrectionProviderError("temporary"),
            RetryableCorrectionProviderError("still temporary"),
        ]
    )

    with pytest.raises(RetryableCorrectionProviderError, match="bounded retries") as raised:
        execute_correction_call(
            provider,
            _request(),
            policy=CorrectionExecutionPolicy(max_attempts=2, retry_delay_seconds=0),
            sleep=lambda _: None,
        )

    assert provider.calls == 2
    assert "still temporary" not in str(raised.value)


def test_permanent_and_invalid_responses_are_not_retried() -> None:
    secret = "private request content and credential"
    permanent = _Provider(failures=[PermanentCorrectionProviderError(secret)])
    with pytest.raises(PermanentCorrectionProviderError) as raised:
        execute_correction_call(permanent, _request())
    assert permanent.calls == 1
    assert secret not in str(raised.value)

    class InvalidProvider(_Provider):
        def correct(
            self,
            request: CorrectionRequest,
            *,
            timeout_seconds: float | None = None,
        ) -> CorrectionResponse:
            self.calls += 1
            return CorrectionResponse(
                operation_id="wrong-operation",
                corrected_text="tekst",
                proposed_changes=(),
            )

    invalid = InvalidProvider()
    with pytest.raises(InvalidCorrectionResponseError):
        execute_correction_call(invalid, _request())
    assert invalid.calls == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"max_attempts": 0}, "max_attempts"),
        ({"retry_delay_seconds": -1}, "retry_delay_seconds"),
    ],
)
def test_invalid_execution_policy_is_rejected(kwargs: dict[str, float | int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        CorrectionExecutionPolicy(**kwargs)
