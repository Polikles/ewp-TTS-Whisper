"""Network-isolated tests for the LM Studio translation adapter."""

import json
from pathlib import Path

import pytest

from ewp_transcripts.automated_translation import build_automated_translation_request
from ewp_transcripts.domain.errors import InvalidTranslationResponseError
from ewp_transcripts.translation_lm_studio import (
    LmStudioTranslationConfig,
    LmStudioTranslationProvider,
)
from ewp_transcripts.translation_review_service import prepare_translation_review

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_adapter_sends_owned_unit_and_read_only_context() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, payload, timeout):  # type: ignore[no-untyped-def]
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "choices": [
                {"finish_reason": "stop", "message": {"content": '{"target_text":"Witamy."}'}}
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 2},
        }

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="qwen-test"), transport=transport
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    response = provider.translate(request, timeout_seconds=12)

    payload = json.loads(captured["payload"])
    task = json.loads(payload["messages"][1]["content"])
    assert captured["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert task["owned_unit"]["unit_id"] == "tu_000001"
    assert task["following_read_only_context"][0]["unit_id"] == "tu_000002"
    assert response.operation_id == request.operation_id
    assert response.target_text == "Witamy."
    assert response.usage is not None and response.usage.input_tokens == 20


def test_adapter_rejects_remote_endpoint_by_default() -> None:
    with pytest.raises(ValueError, match="loopback"):
        LmStudioTranslationConfig(model_id="model", endpoint="http://example.com/v1")


def test_json_text_mode_omits_unsupported_response_format() -> None:
    captured: dict[str, object] = {}

    def transport(_url, _headers, payload, _timeout):  # type: ignore[no-untyped-def]
        captured["payload"] = payload
        return {"choices": [{"message": {"content": '{"target_text":"Witamy."}'}}]}

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="bielik", output_mode="json-text"),
        transport=transport,
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    response = provider.translate(request, timeout_seconds=1)

    payload = json.loads(captured["payload"])
    assert "response_format" not in payload
    assert "PLAIN-JSON COMPATIBILITY MODE" in payload["messages"][0]["content"]
    assert response.target_text == "Witamy."
    assert provider.provenance_parameters["output_mode"] == "json-text"


def test_plain_text_mode_preserves_dialogue_quotes_without_json_serialization() -> None:
    dialogue = 'I immediately say, "Let\'s do it together".'
    captured: dict[str, object] = {}

    def transport(_url, _headers, payload, _timeout):  # type: ignore[no-untyped-def]
        captured["payload"] = payload
        return {"choices": [{"finish_reason": "stop", "message": {"content": dialogue}}]}

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="bielik", output_mode="plain-text"),
        transport=transport,
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    response = provider.translate(request, timeout_seconds=1)

    payload = json.loads(captured["payload"])
    assert "response_format" not in payload
    assert "PLAIN-TEXT COMPATIBILITY MODE" in payload["messages"][0]["content"]
    assert response.target_text == dialogue
    assert provider.provenance_parameters["output_mode"] == "plain-text"


@pytest.mark.parametrize("field", ["target_text", "translated_text"])
def test_plain_text_mode_unwraps_strict_single_field_json(field: str) -> None:
    def transport(_url, _headers, _payload, _timeout):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": json.dumps({field: "Wrapped translation."})}}]}

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="bielik", output_mode="plain-text"),
        transport=transport,
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    response = provider.translate(request, timeout_seconds=1)

    assert response.target_text == "Wrapped translation."


def test_plain_text_mode_rejects_extra_json_fields() -> None:
    def transport(_url, _headers, _payload, _timeout):  # type: ignore[no-untyped-def]
        return {
            "choices": [
                {"message": {"content": '{"translated_text":"Translation.","note":"extra"}'}}
            ]
        }

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="bielik", output_mode="plain-text"),
        transport=transport,
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    with pytest.raises(InvalidTranslationResponseError):
        provider.translate(request, timeout_seconds=1)


def test_adapter_sanitizes_invalid_response_without_content() -> None:
    secret = "private transcript phrase"

    def transport(_url, _headers, _payload, _timeout):  # type: ignore[no-untyped-def]
        return {"choices": [{"message": {"content": secret}}]}

    provider = LmStudioTranslationProvider(
        LmStudioTranslationConfig(model_id="model"), transport=transport
    )
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    request = build_automated_translation_request(review, 0, provider=provider)

    with pytest.raises(InvalidTranslationResponseError) as captured:
        provider.translate(request, timeout_seconds=1)

    assert secret not in str(captured.value)
