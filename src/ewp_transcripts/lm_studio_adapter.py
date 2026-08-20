"""OpenAI-compatible local correction adapter for LM Studio."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ewp_transcripts.correction import derive_correction_response, validate_correction_response
from ewp_transcripts.domain.correction import (
    CorrectionChange,
    CorrectionRequest,
    CorrectionResponse,
    CorrectionUsage,
)
from ewp_transcripts.domain.errors import (
    InvalidCorrectionResponseError,
    PermanentCorrectionProviderError,
    RetryableCorrectionProviderError,
)

JsonObject = dict[str, Any]
HttpTransport = Callable[[str, Mapping[str, str], bytes, float], JsonObject]

FAITHFUL_CORRECTION_SYSTEM_PROMPT = """You correct faithful speech transcripts.
Change only obvious ASR lexical errors, proper-name spelling, conservative punctuation,
capitalization, or sentence boundaries. Preserve speakers, meaning, malformed speech,
fillers, repetitions, self-corrections, grammar, and style. Never paraphrase, summarize,
translate, censor, or add facts. Do not change text merely to make it sound more natural.
Context is read-only. Return only the requested JSON.

Return exactly one speaker_blocks item for every editable_speaker_blocks item, in the same
order and with the same speaker_id. Correct only each block's text, with tokens separated by
one ASCII space. Never merge, split, add, delete, reorder, or relabel speaker blocks. Never
include preceding_read_only_context or following_read_only_context. Preserve editable text
exactly unless a clearly necessary faithful correction is allowed by the first paragraph.
Copy operation_id exactly. The local application independently derives exact source spans,
before/after text, categories, mappings, and revision audit inside each speaker block. If no
correction is clearly necessary, return each editable block unchanged. Prefer no change when
uncertain.
"""


class _LmStudioSpeakerBlock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    speaker_id: str = Field(min_length=1)
    corrected_text: str = Field(min_length=1)


class _LmStudioResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(min_length=1)
    speaker_blocks: tuple[_LmStudioSpeakerBlock, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LmStudioAdapterConfig:
    model_id: str
    endpoint: str = "http://127.0.0.1:1234/v1"
    allow_remote_endpoint: bool = False
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("LM Studio model_id must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("LM Studio temperature must be between 0 and 2")
        _normalized_endpoint(self.endpoint, allow_remote=self.allow_remote_endpoint)


class LmStudioCorrectionProvider:
    """Provider-neutral adapter for an explicitly scoped LM Studio API."""

    def __init__(
        self,
        config: LmStudioAdapterConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._endpoint = _normalized_endpoint(
            config.endpoint,
            allow_remote=config.allow_remote_endpoint,
        )
        self._transport = transport or _urllib_transport

    @property
    def provider_id(self) -> str:
        return "lm-studio"

    @property
    def model_id(self) -> str:
        return self._config.model_id

    @property
    def endpoint_kind(self) -> Literal["local"]:
        return "local"

    @property
    def endpoint_identity(self) -> str:
        return self._endpoint

    def prompt_sha256(self, prompt_id: str) -> str:
        material = json.dumps(
            {
                "prompt_id": prompt_id,
                "system": FAITHFUL_CORRECTION_SYSTEM_PROMPT,
                "response_schema": _LmStudioResponse.model_json_schema(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(material.encode()).hexdigest()

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        if timeout_seconds is None or timeout_seconds <= 0:
            raise ValueError("LM Studio calls require a positive timeout")
        payload = json.dumps(
            _chat_request(self._config, request),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        document = self._transport(
            f"{self._endpoint}/chat/completions",
            {"Content-Type": "application/json"},
            payload,
            timeout_seconds,
        )
        return _parse_chat_response(document, request)


def _chat_request(config: LmStudioAdapterConfig, request: CorrectionRequest) -> JsonObject:
    editable_blocks = _speaker_blocks(request)
    transcript = {
        "operation_id": request.operation_id,
        "language": request.language,
        "output_contract": "return the same ordered speaker blocks with corrected text only",
        "preceding_read_only_context": [token.model_dump() for token in request.preceding_context],
        "editable_tokens": [token.model_dump() for token in request.editable_tokens],
        "editable_speaker_blocks": [
            {"speaker_id": speaker_id, "text": text}
            for speaker_id, _start, _end, text in editable_blocks
        ],
        "following_read_only_context": [token.model_dump() for token in request.following_context],
    }
    return {
        "model": config.model_id,
        "temperature": config.temperature,
        "messages": [
            {"role": "system", "content": FAITHFUL_CORRECTION_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(transcript, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "correction_response",
                "strict": True,
                "schema": _LmStudioResponse.model_json_schema(),
            },
        },
    }


def _parse_chat_response(document: JsonObject, request: CorrectionRequest) -> CorrectionResponse:
    try:
        choices = document["choices"]
        content = choices[0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError
        wire_response = _LmStudioResponse.model_validate_json(content)
        if wire_response.operation_id != request.operation_id:
            raise InvalidCorrectionResponseError("LM Studio response operation ID does not match")
        usage = document.get("usage")
        correction_usage = None
        if isinstance(usage, dict):
            correction_usage = CorrectionUsage(
                input_tokens=_optional_nonnegative_int(usage.get("prompt_tokens")),
                output_tokens=_optional_nonnegative_int(usage.get("completion_tokens")),
            )
        response = _derive_blocked_response(
            request,
            wire_response,
            usage=correction_usage,
        )
    except ValidationError as error:
        details = ",".join(
            f"{'.'.join(str(part) for part in item['loc']) or '<root>'}:{item['type']}"
            for item in error.errors(include_url=False, include_input=False)[:8]
        )
        raise InvalidCorrectionResponseError(
            f"LM Studio returned an invalid correction response (schema_errors={details})"
        ) from error
    except ValueError as error:
        raise InvalidCorrectionResponseError(
            f"LM Studio returned an invalid correction response ({error})"
        ) from error
    except (IndexError, KeyError, TypeError) as error:
        raise InvalidCorrectionResponseError(
            "LM Studio returned an invalid correction response"
        ) from error
    return response


def _speaker_blocks(request: CorrectionRequest) -> list[tuple[str, int, int, str]]:
    blocks: list[tuple[str, int, int, str]] = []
    start = 0
    while start < len(request.editable_tokens):
        speaker_id = request.editable_tokens[start].speaker_id
        end = start + 1
        while (
            end < len(request.editable_tokens)
            and request.editable_tokens[end].speaker_id == speaker_id
        ):
            end += 1
        text = " ".join(token.text for token in request.editable_tokens[start:end])
        blocks.append((speaker_id, start, end, text))
        start = end
    return blocks


def _derive_blocked_response(
    request: CorrectionRequest,
    wire_response: _LmStudioResponse,
    *,
    usage: CorrectionUsage | None,
) -> CorrectionResponse:
    source_blocks = _speaker_blocks(request)
    if len(wire_response.speaker_blocks) != len(source_blocks):
        raise ValueError("LM Studio changed the editable speaker-block count")
    corrected_tokens: list[str] = []
    changes: list[CorrectionChange] = []
    for returned, (speaker_id, start, end, _text) in zip(
        wire_response.speaker_blocks,
        source_blocks,
        strict=True,
    ):
        if returned.speaker_id != speaker_id:
            raise ValueError("LM Studio changed editable speaker-block identity or order")
        block_request = request.model_copy(
            update={
                "editable_tokens": request.editable_tokens[start:end],
                "preceding_context": (),
                "following_context": (),
            }
        )
        derived = derive_correction_response(
            block_request,
            corrected_text=returned.corrected_text,
        )
        corrected_tokens.extend(derived.corrected_text.split())
        changes.extend(
            change.model_copy(
                update={
                    "start_index": change.start_index + start,
                    "end_index": change.end_index + start,
                }
            )
            for change in derived.proposed_changes
        )
    response = CorrectionResponse(
        operation_id=request.operation_id,
        corrected_text=" ".join(corrected_tokens),
        proposed_changes=tuple(changes),
        usage=usage,
    )
    validate_correction_response(request, response)
    return response


def _optional_nonnegative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("invalid usage")
    return value


def is_loopback_endpoint(endpoint: str) -> bool:
    """Return whether a syntactically valid endpoint names the local host."""

    return urlsplit(endpoint).hostname in {"127.0.0.1", "localhost", "::1"}


def _normalized_endpoint(endpoint: str, *, allow_remote: bool) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("LM Studio endpoint must be an uncredentialed HTTP(S) URL")
    if not is_loopback_endpoint(endpoint) and not allow_remote:
        raise ValueError("Remote LM Studio endpoint requires explicit opt-in")
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        raise ValueError("LM Studio endpoint path must end in /v1")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _urllib_transport(
    url: str,
    headers: Mapping[str, str],
    payload: bytes,
    timeout_seconds: float,
) -> JsonObject:
    request = urllib.request.Request(url, data=payload, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            document = json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code in {408, 409, 425, 429} or error.code >= 500:
            raise RetryableCorrectionProviderError("LM Studio request failed") from None
        raise PermanentCorrectionProviderError("LM Studio request was rejected") from None
    except (TimeoutError, urllib.error.URLError):
        raise RetryableCorrectionProviderError("LM Studio is temporarily unavailable") from None
    except (OSError, json.JSONDecodeError):
        raise PermanentCorrectionProviderError("LM Studio returned unreadable data") from None
    if not isinstance(document, dict):
        raise PermanentCorrectionProviderError("LM Studio returned unreadable data")
    return document
