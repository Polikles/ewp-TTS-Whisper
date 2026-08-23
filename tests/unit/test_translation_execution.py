"""Tests for bounded automated-translation execution."""

from pathlib import Path

from ewp_transcripts.automated_translation import (
    DeterministicMockTranslationProvider,
    build_automated_translation_request,
)
from ewp_transcripts.domain.errors import RetryableTranslationProviderError
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
