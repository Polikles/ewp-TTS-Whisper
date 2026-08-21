"""Network-isolated tests for the explicit OpenRouter correction adapter."""

import json
from collections.abc import Mapping
from typing import Any

import pytest

from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionToken
from ewp_transcripts.domain.errors import PermanentCorrectionProviderError
from ewp_transcripts.openrouter_adapter import (
    OpenRouterAdapterConfig,
    OpenRouterCorrectionProvider,
)


def _request() -> CorrectionRequest:
    return CorrectionRequest(
        operation_id="operation-1",
        prompt_id="faithful-correction-v11",
        prompt_sha256="0" * 64,
        language="pl",
        editable_tokens=(
            CorrectionToken(
                local_index=0,
                token_id="word_000001",
                text="postrzymać.",
                speaker_id="speaker_001",
            ),
        ),
    )


def test_adapter_sends_bearer_request_and_parses_usage_cost() -> None:
    captured: dict[str, Any] = {}

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        captured.update(
            url=url, headers=dict(headers), payload=json.loads(payload), timeout=timeout
        )
        content = {
            "operation_id": "operation-1",
            "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "powstrzymać."}],
        }
        return {
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "cost": "0.0012345",
            },
        }

    provider = OpenRouterCorrectionProvider(
        OpenRouterAdapterConfig(model_id="qwen/qwen-2.5-72b-instruct"),
        transport=transport,
        environment={"OPENROUTER_API_KEY": "private-key"},
    )
    response = provider.correct(_request(), timeout_seconds=12)

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer private-key"
    assert captured["payload"]["provider"] == {
        "require_parameters": True,
        "allow_fallbacks": False,
    }
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert response.corrected_text == "powstrzymać."
    assert response.usage is not None
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 20
    assert response.usage.cost_usd_micros == 1235


def test_missing_key_fails_without_calling_transport_or_exposing_a_secret() -> None:
    called = False

    def transport(*args: object) -> dict[str, Any]:
        nonlocal called
        called = True
        return {}

    provider = OpenRouterCorrectionProvider(
        OpenRouterAdapterConfig(model_id="model"),
        transport=transport,
        environment={},
    )

    with pytest.raises(PermanentCorrectionProviderError, match="OPENROUTER_API_KEY"):
        provider.correct(_request(), timeout_seconds=2)
    assert not called


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://openrouter.ai/api/v1",
        "https://user:secret@openrouter.ai/api/v1",
        "https://openrouter.ai/v1",
        "https://openrouter.ai/api/v1?key=secret",
    ],
)
def test_adapter_rejects_unsafe_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="OpenRouter endpoint"):
        OpenRouterAdapterConfig(model_id="model", endpoint=endpoint)


def test_secret_does_not_affect_prompt_identity_or_provenance() -> None:
    config = OpenRouterAdapterConfig(model_id="model")
    first = OpenRouterCorrectionProvider(config, environment={"OPENROUTER_API_KEY": "one"})
    second = OpenRouterCorrectionProvider(config, environment={"OPENROUTER_API_KEY": "two"})

    assert first.prompt_sha256("prompt") == second.prompt_sha256("prompt")
    assert "one" not in repr(first)
    assert "two" not in repr(second)
    assert "api_key" not in json.dumps(first.provenance_parameters)
