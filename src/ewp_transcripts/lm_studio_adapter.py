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

from ewp_transcripts.domain.correction import (
    CorrectionCategory,
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

Each proposed_changes item is exactly one contiguous source replacement. Its
source_token_ids MUST list every token in that one contiguous span in original order,
including any internally unchanged token needed inside a multi-token replacement. Copy
these IDs exactly. Never group non-adjacent corrections into one item; emit a separate
change item for every non-adjacent correction. The list MUST be non-empty and contain no
read-only context ID. Never count array positions and never invent boundary semantics.
For every change, before MUST equal the source token texts named by
source_token_ids joined with exactly one ASCII space, including original punctuation and
capitalization. Changes MUST be sorted and non-overlapping. corrected_text MUST exactly
equal all editable token texts after applying proposed_changes, joined with exactly one
ASCII space. Copy operation_id exactly.
Never include read-only context in corrected_text or changes. If no correction is clearly
necessary, return the editable text unchanged and an empty proposed_changes list.
Category rules are strict: punctuation may change punctuation only; capitalization may
change letter case only; sentence_boundary may change punctuation/case only. Lexical
word-form changes are never punctuation changes. Before returning JSON, reconstruct
corrected_text from the proposed changes yourself. If it differs from your proposed
corrected_text, remove or fix the inconsistent change. Prefer no change when uncertain.

Use the smallest contiguous source span that fully contains the edit. `before` is copy-only
audit evidence: copy it from the source before writing `after`, and never apply any intended
correction to `before`. Example: if editable token `word_17` is `anna.` and the following
token is `Witamy`, a capitalization-only correction is
{"source_token_ids":["word_17"],"before":"anna.","after":"Anna.","category":"capitalization"}.
Do not include the unchanged following token, and do not write `before` as `Anna.` or `anna`.
"""


class _LmStudioChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source_token_ids: tuple[str, ...] = Field(min_length=1)
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)
    category: CorrectionCategory


class _LmStudioResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(min_length=1)
    corrected_text: str = Field(min_length=1)
    proposed_changes: tuple[_LmStudioChange, ...]


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
    transcript = {
        "operation_id": request.operation_id,
        "language": request.language,
        "index_contract": (
            "source_token_ids lists every changed editable token ID in original contiguous "
            "order; before is the exact one-space join of those token texts"
        ),
        "preceding_read_only_context": [token.model_dump() for token in request.preceding_context],
        "editable_tokens": [token.model_dump() for token in request.editable_tokens],
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
        response = _to_correction_response(wire_response, request)
        usage = document.get("usage")
        if isinstance(usage, dict):
            response = response.model_copy(
                update={
                    "usage": CorrectionUsage(
                        input_tokens=_optional_nonnegative_int(usage.get("prompt_tokens")),
                        output_tokens=_optional_nonnegative_int(usage.get("completion_tokens")),
                    )
                }
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
    if response.operation_id != request.operation_id:
        raise InvalidCorrectionResponseError("LM Studio response operation ID does not match")
    return response


def _to_correction_response(
    response: _LmStudioResponse,
    request: CorrectionRequest,
) -> CorrectionResponse:
    positions = {token.token_id: index for index, token in enumerate(request.editable_tokens)}
    changes: list[CorrectionChange] = []
    for change in response.proposed_changes:
        try:
            change_positions = [positions[token_id] for token_id in change.source_token_ids]
        except KeyError as error:
            raise ValueError("LM Studio change references a non-editable token ID") from error
        if len(change_positions) != len(set(change_positions)):
            raise ValueError("LM Studio change token IDs are duplicated")
        start = change_positions[0]
        if change_positions != list(range(start, start + len(change_positions))):
            summary = ",".join(str(position) for position in change_positions[:16])
            raise ValueError(
                "LM Studio change token IDs are not ordered and contiguous "
                f"(positions={summary}, count={len(change_positions)})"
            )
        changes.append(
            CorrectionChange(
                start_index=start,
                end_index=start + len(change_positions),
                before=change.before,
                after=change.after,
                category=change.category,
            )
        )
    return CorrectionResponse(
        operation_id=response.operation_id,
        corrected_text=response.corrected_text,
        proposed_changes=tuple(changes),
    )


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
