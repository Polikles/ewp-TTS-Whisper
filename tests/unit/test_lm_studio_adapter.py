"""Tests for the network-isolated LM Studio correction adapter."""

import json
from collections.abc import Mapping
from typing import Any

import pytest

from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionToken
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.lm_studio_adapter import (
    FAITHFUL_CORRECTION_SYSTEM_PROMPT,
    JSON_TEXT_OUTPUT_INSTRUCTION,
    LmStudioAdapterConfig,
    LmStudioCorrectionProvider,
)


def _request() -> CorrectionRequest:
    return CorrectionRequest(
        operation_id="operation-1",
        prompt_id="faithful-correction-v11",
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
            "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "OpenAI"}],
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
    assert "Never insert or delete words to repair grammar" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "If two plausible corrections exist, make no change" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "explicit dictionary" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    assert "same speaker_id" in FAITHFUL_CORRECTION_SYSTEM_PROMPT
    user = json.loads(captured["payload"]["messages"][1]["content"])
    assert "same ordered speaker blocks" in user["output_contract"]
    assert user["editable_speaker_blocks"] == [{"speaker_id": "speaker_001", "text": "Open AI"}]
    assert user["preceding_read_only_context"][0]["text"] == "kontekst"
    assert "editable_tokens" not in user
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert response.corrected_text == "OpenAI"
    assert response.proposed_changes[0].start_index == 0
    assert response.proposed_changes[0].end_index == 2
    assert response.usage is not None
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 25


def test_json_text_mode_omits_response_format_and_keeps_strict_parsing() -> None:
    captured: dict[str, Any] = {}
    content = {
        "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "OpenAI"}],
    }

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        captured.update(payload=json.loads(payload))
        return {"choices": [{"message": {"content": json.dumps(content)}}]}

    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="bielik", output_mode="json-text"),
        transport=transport,
    )

    response = provider.correct(_request(), timeout_seconds=2)

    assert "response_format" not in captured["payload"]
    assert JSON_TEXT_OUTPUT_INSTRUCTION in captured["payload"]["messages"][0]["content"]
    assert "TASK_INPUT:" in captured["payload"]["messages"][1]["content"]
    assert "REQUIRED_RESPONSE_TEMPLATE:" in captured["payload"]["messages"][1]["content"]
    assert '"speaker_blocks"' in captured["payload"]["messages"][1]["content"]
    assert response.corrected_text == "OpenAI"


def test_json_text_mode_rejects_markdown_wrapped_json() -> None:
    content = {
        "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "OpenAI"}],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="bielik", output_mode="json-text"),
        transport=lambda *args: {
            "choices": [{"message": {"content": f"```json\n{json.dumps(content)}\n```"}}]
        },
    )

    with pytest.raises(InvalidCorrectionResponseError, match="schema_errors="):
        provider.correct(_request(), timeout_seconds=2)


def test_json_text_mode_rejects_redundant_operation_id() -> None:
    content = {
        "operation_id": "operation-1,",
        "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "OpenAI"}],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="bielik", output_mode="json-text"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError, match="operation_id:extra_forbidden"):
        provider.correct(_request(), timeout_seconds=2)


def test_output_mode_changes_prompt_identity() -> None:
    schema_provider = LmStudioCorrectionProvider(LmStudioAdapterConfig(model_id="model"))
    text_provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model", output_mode="json-text")
    )

    assert schema_provider.prompt_sha256("prompt") != text_provider.prompt_sha256("prompt")


def test_request_omits_redundant_editable_token_metadata() -> None:
    captured: dict[str, Any] = {}

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        captured.update(payload=json.loads(payload))
        content = {
            "operation_id": "operation-1",
            "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "Open AI"}],
        }
        return {"choices": [{"message": {"content": json.dumps(content)}}]}

    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"), transport=transport
    )
    provider.correct(_request(), timeout_seconds=2)

    task = json.loads(captured["payload"]["messages"][1]["content"])
    assert "editable_tokens" not in task
    assert task["editable_speaker_blocks"] == [{"speaker_id": "speaker_001", "text": "Open AI"}]


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
    assert "schema_errors=" in str(raised.value)
    assert secret not in str(raised.value)


def test_adapter_schema_diagnostic_excludes_private_field_values() -> None:
    private_text = "private transcript response"
    content = {
        "operation_id": "operation-1",
        "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "Open AI"}],
        "obsolete_private_field": private_text,
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError) as raised:
        provider.correct(_request(), timeout_seconds=2)

    message = str(raised.value)
    assert "obsolete_private_field:extra_forbidden" in message
    assert private_text not in message


def test_adapter_rejects_changed_speaker_block_identity() -> None:
    content = {
        "operation_id": "operation-1",
        "speaker_blocks": [{"speaker_id": "speaker_002", "corrected_text": "Open AI"}],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError, match="speaker-block identity"):
        provider.correct(_request(), timeout_seconds=2)


def test_adapter_derives_changes_independently_inside_speaker_blocks() -> None:
    request = _request().model_copy(
        update={
            "editable_tokens": (
                _request().editable_tokens[0],
                _request().editable_tokens[1].model_copy(update={"speaker_id": "speaker_002"}),
            )
        }
    )
    content = {
        "operation_id": "operation-1",
        "speaker_blocks": [
            {"speaker_id": "speaker_001", "corrected_text": "OPEN"},
            {"speaker_id": "speaker_002", "corrected_text": "AI."},
        ],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    response = provider.correct(request, timeout_seconds=2)

    assert response.corrected_text == "OPEN AI."
    assert [(change.start_index, change.end_index) for change in response.proposed_changes] == [
        (0, 1),
        (1, 2),
    ]


def test_adapter_rejects_excessive_speaker_block_token_drift() -> None:
    tokens = tuple(
        CorrectionToken(
            local_index=index,
            token_id=f"word_{index + 1:06d}",
            text=f"token{index}",
            speaker_id="speaker_001",
        )
        for index in range(20)
    )
    request = _request().model_copy(update={"editable_tokens": tokens})
    content = {
        "operation_id": "operation-1",
        "speaker_blocks": [{"speaker_id": "speaker_001", "corrected_text": "token0"}],
    }
    provider = LmStudioCorrectionProvider(
        LmStudioAdapterConfig(model_id="model"),
        transport=lambda *args: {"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with pytest.raises(InvalidCorrectionResponseError, match="conservative safety limit"):
        provider.correct(request, timeout_seconds=2)
