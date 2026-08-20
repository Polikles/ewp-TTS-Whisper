"""Tests for the network-isolated LM Studio correction adapter."""

import json
from collections.abc import Mapping
from typing import Any

import pytest

from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionToken
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.lm_studio_adapter import (
    FAITHFUL_CORRECTION_SYSTEM_PROMPT,
    LmStudioAdapterConfig,
    LmStudioCorrectionProvider,
)


def _request() -> CorrectionRequest:
    return CorrectionRequest(
        operation_id="operation-1",
        prompt_id="faithful-correction-v5",
        prompt_sha256="0" * 64,
        language="pl",
        preceding_context=(
            CorrectionToken(
                local_index=-1,
                token_id="word_000001",
                text="kontekst",
                speaker_id="speaker_001",
            ),
        ),
        editable_tokens=(
            CorrectionToken(
                local_index=0,
                token_id="word_000002",
                text="Open",
                speaker_id="speaker_001",
            ),
            CorrectionToken(
                local_index=1,
                token_id="word_000003",
                text="AI",
                speaker_id="speaker_001",
            ),
        ),
    )


def test_adapter_sends_structured_faithful_request_and_parses_usage() -> None:
    captured: dict[str, Any] = {}

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        captured.update(
            url=url, headers=dict(headers), payload=json.loads(payload), timeout=timeout
        )
        content = {
            "operation_id": "operation-1",
            "corrected_text": "OpenAI",
            "proposed_changes": [
                {
                    "source_token_ids": ["word_000002", "word_000003"],
                    "before": "Open AI",
                    "after": "OpenAI",
                    "category": "proper_name",
                }
            ],
        }
        return {
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 25},
        }

    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="qwen-test"), transport=transport
    )
    response = provider.correct(_request(), timeout_seconds=9)

    assert captured["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert captured["timeout"] == 9
    assert "paraphrase" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "before MUST equal" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "Never count array positions" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "Lexical\nword-form changes" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    user = json.loads(captured["payload"]["messages"][1]["content"])
    assert "every changed editable token ID" in user["index_contract"]
    assert user["preceding_read_only_context"][0]["text"] == "kontekst"
    assert user["editable_tokens"][0]["token_id"] == "word_000002"
    assert response.corrected_text == "OpenAI"
    assert response.proposed_changes[0].start_index == 0
    assert response.proposed_changes[0].end_index == 2
    assert response.usage is not None
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 25


@pytest.mark.parametrize(
    "endpoint",
    [
        "ftp://127.0.0.1:1234/v1",
        "http://192.168.1.2:1234/v1",
        "http://user:secret@localhost:1234/v1",
        "http://localhost:1234/api",
    ],
)
def test_adapter_rejects_unsafe_or_unapproved_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="LM Studio endpoint"):
        LmStudioAdapterConfig(model_id="model", endpoint=endpoint)


def test_adapter_accepts_remote_endpoint_only_with_explicit_opt_in() -> None:
    config = LmStudioAdapterConfig(
        model_id="model",
        endpoint="http://100.99.201.120:1234/v1",
        allow_remote_endpoint=True,
    )
    provider = LmStudioCorrectionProvider(config, transport=lambda *args: {})

    assert provider.endpoint_identity == "http://100.99.201.120:1234/v1"


def test_adapter_rejects_malformed_content_without_exposing_it() -> None:
    secret = "private transcript and token"

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        return {"choices": [{"message": {"content": secret}}]}

    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"), transport=transport
    )
    with pytest.raises(InvalidCorrectionResponseError) as raised:
        provider.correct(_request(), timeout_seconds=2)
    assert secret not in str(raised.value)


def test_adapter_rejects_change_that_references_read_only_token_id() -> None:
    content = {
        "operation_id": "operation-1",
        "corrected_text": "Open AI",
        "proposed_changes": [
            {
                "source_token_ids": ["word_000001"],
                "before": "private",
                "after": "changed",
                "category": "asr_lexical",
            }
        ],
    }

    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError, match="invalid correction response"):
        provider.correct(_request(), timeout_seconds=2)


def test_adapter_rejects_noncontiguous_change_token_ids() -> None:
    request = _request().model_copy(
        update={
            "editable_tokens": (
                *_request().editable_tokens,
                CorrectionToken(
                    local_index=2,
                    token_id="word_000004",
                    text="dalej",
                    speaker_id="speaker_001",
                ),
            )
        }
    )
    content = {
        "operation_id": "operation-1",
        "corrected_text": "Open AI dalej",
        "proposed_changes": [
            {
                "source_token_ids": ["word_000002", "word_000004"],
                "before": "private",
                "after": "changed",
                "category": "asr_lexical",
            }
        ],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError, match="invalid correction response"):
        provider.correct(request, timeout_seconds=2)
