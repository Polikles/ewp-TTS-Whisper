"""Tests for private validated correction response resume state."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from ewp_transcripts.correction import (
    DeterministicMockCorrectionProvider,
    build_correction_request,
    plan_correction_chunks,
)
from ewp_transcripts.correction_state import call_correction_resumable
from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionResponse
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript


@dataclass
class CountingProvider:
    calls: int = 0

    @property
    def provider_id(self) -> str:
        return "counting-mock"

    @property
    def model_id(self) -> str:
        return "v1"

    @property
    def endpoint_kind(self) -> Literal["mock"]:
        return "mock"

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        del timeout_seconds
        self.calls += 1
        return DeterministicMockCorrectionProvider().correct(request)


def _request() -> CorrectionRequest:
    transcript = EffectiveTranscript(
        language="pl",
        tokens=(
            EffectiveToken(
                token_id="word_000001",
                text="tekst",
                speaker_id="speaker_001",
                source_word_ids=("word_000001",),
                start_ms=0,
                end_ms=100,
                timing_source="aligned",
                overlap=False,
                active_speaker_ids=("speaker_001",),
            ),
        ),
    )
    return build_correction_request(
        transcript,
        plan_correction_chunks(transcript)[0],
        prompt_id="faithful-pl-v1",
        provider_id="counting-mock",
        model_id="v1",
    )


def test_validated_response_is_resumed_without_second_provider_call(tmp_path: Path) -> None:
    provider = CountingProvider()
    request = _request()

    first = call_correction_resumable(provider, request, state_directory=tmp_path / "state")
    second = call_correction_resumable(provider, request, state_directory=tmp_path / "state")

    assert first.resumed is False
    assert second.resumed is True
    assert provider.calls == 1
    assert first.response == second.response
    assert first.metrics.attempts == 1
    assert second.metrics.attempts == 0
    assert first.state_path.stat().st_mode & 0o777 == 0o600


def test_corrupt_resume_state_is_rejected_without_provider_call(tmp_path: Path) -> None:
    provider = CountingProvider()
    request = _request()
    state = tmp_path / "state"
    state.mkdir()
    (state / f"{request.operation_id}.json").write_text("invalid", encoding="utf-8")

    with pytest.raises(InvalidCorrectionResponseError, match="resume state"):
        call_correction_resumable(provider, request, state_directory=state)

    assert provider.calls == 0
