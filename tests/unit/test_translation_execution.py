"""Tests for bounded automated-translation execution."""

from pathlib import Path

import pytest

from ewp_transcripts.automated_translation import (
    DeterministicMockTranslationProvider,
    build_automated_translation_request,
)
from ewp_transcripts.domain.errors import (
    InvalidTranslationResponseError,
    PermanentTranslationHttpError,
    PermanentTranslationProviderError,
    RetryableTranslationProviderError,
)
from ewp_transcripts.translation_execution import (
    TranslationExecutionPolicy,
    execute_translation_call,
)
from ewp_transcripts.translation_review_service import prepare_translation_review
from ewp_transcripts.translation_state import summarize_translation_resume_state

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


class FlakyProvider(DeterministicMockTranslationProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def translate(self, request, *, timeout_seconds=None):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise RetryableTranslationProviderError("private adapter detail")
        return super().translate(request, timeout_seconds=timeout_seconds)


def test_execution_retries_only_sanitized_retryable_failures() -> None:
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = FlakyProvider()
    request = build_automated_translation_request(review, 0, provider=provider)

    outcome = execute_translation_call(
        provider,
        request,
        policy=TranslationExecutionPolicy(max_attempts=2, retry_delay_seconds=0),
    )

    assert outcome.metrics.attempts == 2
    assert outcome.metrics.retries == 1
    assert outcome.metrics.request_count == 2


def test_execution_retries_invalid_response_contract_failures() -> None:
    class InvalidOnceProvider(DeterministicMockTranslationProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def translate(self, request, *, timeout_seconds=None):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                raise InvalidTranslationResponseError("private malformed output")
            return super().translate(request, timeout_seconds=timeout_seconds)

    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = InvalidOnceProvider()
    request = build_automated_translation_request(review, 0, provider=provider)

    outcome = execute_translation_call(
        provider,
        request,
        policy=TranslationExecutionPolicy(max_attempts=2, retry_delay_seconds=0),
    )

    assert outcome.metrics.attempts == 2
    assert outcome.metrics.retries == 1


def test_execution_stops_invalid_responses_at_retry_limit_without_content() -> None:
    class InvalidProvider(DeterministicMockTranslationProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def translate(self, request, *, timeout_seconds=None):  # type: ignore[no-untyped-def]
            self.calls += 1
            raise InvalidTranslationResponseError("private malformed output")

    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = InvalidProvider()
    request = build_automated_translation_request(review, 0, provider=provider)

    with pytest.raises(InvalidTranslationResponseError, match="bounded retries") as raised:
        execute_translation_call(
            provider,
            request,
            policy=TranslationExecutionPolicy(max_attempts=3, retry_delay_seconds=0),
        )

    assert provider.calls == 3
    assert "private malformed output" not in str(raised.value)


def test_resume_summary_contains_no_text(tmp_path: Path) -> None:
    from ewp_transcripts.automated_translation import build_automated_translation

    build_automated_translation(
        EXAMPLE,
        DeterministicMockTranslationProvider(),
        target_language="pl",
        resume_directory=tmp_path,
    )

    summary = summarize_translation_resume_state(tmp_path)

    assert summary["units"] == 2
    assert summary["request_count"] == 2
    assert "text" not in str(summary)


def test_execution_reports_only_safe_permanent_http_status() -> None:
    class RejectedProvider(DeterministicMockTranslationProvider):
        def translate(self, request, *, timeout_seconds=None):  # type: ignore[no-untyped-def]
            raise PermanentTranslationHttpError(400)

    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = RejectedProvider()
    request = build_automated_translation_request(review, 0, provider=provider)

    with pytest.raises(PermanentTranslationProviderError, match="http_status=400"):
        execute_translation_call(provider, request)
