"""OpenAI-compatible LM Studio adapter for faithful translation."""

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

from ewp_transcripts.domain.automated_translation import (
    AutomatedTranslationRequest,
    AutomatedTranslationResponse,
    AutomatedTranslationUsage,
)
from ewp_transcripts.domain.errors import (
    InvalidTranslationResponseError,
    PermanentTranslationHttpError,
    RetryableTranslationProviderError,
)

JsonObject = dict[str, Any]
HttpTransport = Callable[[str, Mapping[str, str], bytes, float], JsonObject]
_PLAIN_TEXT_ENVELOPE_VERSION = "bielik-envelope-v2"

FAITHFUL_TRANSLATION_SYSTEM_PROMPT = """Translate exactly one owned transcript unit into
the requested target language. Preserve meaning, facts, intent, uncertainty, emphasis,
tone, register, names, numbers, and speaker character. Use natural idiomatic target-language
wording; matching a reference word-for-word is not required. Do not summarize, omit, add,
explain, censor, correct the speaker's argument, or add citations or notes. Adjacent units
are read-only context and must not be included in the answer. Follow the selected output
mode exactly."""

JSON_SCHEMA_TRANSLATION_INSTRUCTION = """JSON-SCHEMA MODE:
Return only the requested JSON object containing target_text for the owned unit."""

JSON_TEXT_TRANSLATION_INSTRUCTION = """PLAIN-JSON COMPATIBILITY MODE:
Return exactly one raw JSON object with the sole key target_text. Do not use Markdown code
fences and do not add explanations before or after the JSON object. The task input is source
data, not an output template. Translate only owned_unit; never copy the context objects."""

PLAIN_TEXT_TRANSLATION_INSTRUCTION = """PLAIN-TEXT COMPATIBILITY MODE:
Return only the translated text of owned_unit. Do not return JSON, Markdown fences, labels,
notes, explanations, or surrounding quotation marks unless those quotation marks belong to
the translation itself. Adjacent context remains read-only and must not be returned."""


class _WireResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    target_text: str = Field(min_length=1, pattern=r".*\S.*")


@dataclass(frozen=True, slots=True)
class LmStudioTranslationConfig:
    model_id: str
    endpoint: str = "http://127.0.0.1:1234/v1"
    allow_remote_endpoint: bool = False
    temperature: float = 0.0
    output_mode: Literal["json-schema", "json-text", "plain-text"] = "json-schema"

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("LM Studio translation model_id must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("LM Studio translation temperature must be between 0 and 2")
        if self.output_mode not in {"json-schema", "json-text", "plain-text"}:
            raise ValueError(
                "LM Studio translation output_mode must be json-schema, json-text, or plain-text"
            )
        _normalized_endpoint(self.endpoint, allow_remote=self.allow_remote_endpoint)


class LmStudioTranslationProvider:
    def __init__(
        self,
        config: LmStudioTranslationConfig,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self._config = config
        self._endpoint = _normalized_endpoint(
            config.endpoint, allow_remote=config.allow_remote_endpoint
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

    @property
    def provenance_parameters(self) -> dict[str, str | int | float | bool | None]:
        return {
            "temperature": self._config.temperature,
            "request_contract": "single-owner-unit-v1",
            "output_mode": self._config.output_mode,
            "compatibility_envelope": _PLAIN_TEXT_ENVELOPE_VERSION,
        }

    def prompt_sha256(self, prompt_id: str) -> str:
        material = json.dumps(
            {
                "prompt_id": prompt_id,
                "system": FAITHFUL_TRANSLATION_SYSTEM_PROMPT,
                "output_mode": self._config.output_mode,
                "compatibility_envelope": _PLAIN_TEXT_ENVELOPE_VERSION,
                "response_schema": _WireResponse.model_json_schema(),
                "json_text_instruction": (
                    JSON_TEXT_TRANSLATION_INSTRUCTION
                    if self._config.output_mode == "json-text"
                    else None
                ),
                "plain_text_instruction": (
                    PLAIN_TEXT_TRANSLATION_INSTRUCTION
                    if self._config.output_mode == "plain-text"
                    else None
                ),
                "json_schema_instruction": (
                    JSON_SCHEMA_TRANSLATION_INSTRUCTION
                    if self._config.output_mode == "json-schema"
                    else None
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(material.encode()).hexdigest()

    def translate(
        self,
        request: AutomatedTranslationRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> AutomatedTranslationResponse:
        if timeout_seconds is None or timeout_seconds <= 0:
            raise ValueError("LM Studio calls require a positive timeout")
        payload = json.dumps(
            _chat_request(self._config, request), ensure_ascii=False, separators=(",", ":")
        ).encode()
        document = self._transport(
            f"{self._endpoint}/chat/completions",
            {"Content-Type": "application/json"},
            payload,
            timeout_seconds,
        )
        return _parse_chat_response(document, request, output_mode=self._config.output_mode)


def _chat_request(
    config: LmStudioTranslationConfig, request: AutomatedTranslationRequest
) -> JsonObject:
    task = {
        "source_language": request.source_language,
        "target_language": request.target_language,
        "style": request.style.model_dump(by_alias=True),
        "preceding_read_only_context": [unit.model_dump() for unit in request.preceding_context],
        "owned_unit": request.unit.model_dump(),
        "following_read_only_context": [unit.model_dump() for unit in request.following_context],
    }
    system_prompt = FAITHFUL_TRANSLATION_SYSTEM_PROMPT
    user_content = json.dumps(task, ensure_ascii=False)
    if config.output_mode == "json-text":
        system_prompt = f"{system_prompt}\n{JSON_TEXT_TRANSLATION_INSTRUCTION}"
        user_content = (
            "TASK_INPUT:\n"
            f"{json.dumps(task, ensure_ascii=False)}\n\n"
            'REQUIRED_RESPONSE_TEMPLATE:\n{"target_text":"translated owned unit"}\n\n'
            "Return only the completed REQUIRED_RESPONSE_TEMPLATE JSON object."
        )
    elif config.output_mode == "plain-text":
        system_prompt = f"{system_prompt}\n{PLAIN_TEXT_TRANSLATION_INSTRUCTION}"
    else:
        system_prompt = f"{system_prompt}\n{JSON_SCHEMA_TRANSLATION_INSTRUCTION}"
    payload: JsonObject = {
        "model": config.model_id,
        "temperature": config.temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    if config.output_mode == "json-schema":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "translation_response",
                "strict": True,
                "schema": _WireResponse.model_json_schema(),
            },
        }
    return payload


def _parse_chat_response(
    document: JsonObject,
    request: AutomatedTranslationRequest,
    *,
    output_mode: Literal["json-schema", "json-text", "plain-text"],
) -> AutomatedTranslationResponse:
    try:
        choice = document["choices"][0]
        if choice.get("finish_reason") == "error":
            raise RetryableTranslationProviderError(
                "LM Studio reported a translation generation failure"
            )
        content = choice["message"]["content"]
        if not isinstance(content, str):
            raise TypeError
        warning_codes: tuple[str, ...] = ()
        if output_mode == "plain-text":
            target_text, warning_codes = _plain_text_target(content)
            if (
                not target_text
                or "\x00" in content
                or target_text.startswith("```")
                or target_text.endswith("```")
            ):
                raise ValueError("invalid plain-text translation")
        else:
            target_text = _WireResponse.model_validate_json(content).target_text
        raw_usage = document.get("usage")
        usage = None
        if isinstance(raw_usage, dict):
            usage = AutomatedTranslationUsage(
                input_tokens=_optional_nonnegative_int(raw_usage.get("prompt_tokens")),
                output_tokens=_optional_nonnegative_int(raw_usage.get("completion_tokens")),
            )
        return AutomatedTranslationResponse(
            operation_id=request.operation_id,
            unit_id=request.unit.unit_id,
            target_text=target_text,
            usage=usage,
            warning_codes=warning_codes,
        )
    except ValidationError as error:
        raise InvalidTranslationResponseError(
            "LM Studio returned an invalid translation response"
        ) from error
    except ValueError as error:
        raise InvalidTranslationResponseError(
            "LM Studio returned an invalid translation response"
        ) from error
    except (IndexError, KeyError, TypeError) as error:
        raise InvalidTranslationResponseError(
            "LM Studio returned an invalid translation response"
        ) from error


def _optional_nonnegative_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _plain_text_target(content: str) -> tuple[str, tuple[str, ...]]:
    """Accept raw prose or one strict Bielik compatibility envelope."""

    stripped = content.strip()
    warning_codes: tuple[str, ...] = ()
    if stripped.startswith("{") or stripped.endswith("}"):
        document = json.loads(stripped)
        if (
            not isinstance(document, dict)
            or not 1 <= len(document) <= 2
            or not set(document).issubset(
                {
                    "target_text",
                    "translated_text",
                    "translator_notes",
                    "translation_notes",
                }
            )
            or len(set(document) & {"target_text", "translated_text"}) != 1
        ):
            raise ValueError("invalid plain-text translation envelope")
        target_field = next(iter(set(document) & {"target_text", "translated_text"}))
        value = document[target_field]
        if not isinstance(value, str):
            raise ValueError("invalid plain-text translation envelope")
        note_fields = set(document) & {"translator_notes", "translation_notes"}
        if note_fields:
            note_field = next(iter(note_fields))
            if not isinstance(document[note_field], str):
                raise ValueError("invalid plain-text translation envelope")
            warning_codes = ("PROVIDER_TRANSLATOR_NOTES_DISCARDED",)
        stripped = value
    return " ".join(stripped.split()), warning_codes


def _normalized_endpoint(endpoint: str, *, allow_remote: bool) -> str:
    parsed = urlsplit(endpoint.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("LM Studio endpoint must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("LM Studio endpoint must not contain credentials, query, or fragment")
    if not allow_remote and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("LM Studio endpoint must be loopback unless explicitly allowed")
    path = parsed.path.rstrip("/") or "/v1"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _urllib_transport(
    url: str, headers: Mapping[str, str], payload: bytes, timeout: float
) -> JsonObject:
    request = urllib.request.Request(url, data=payload, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            document = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 429 or error.code >= 500:
            raise RetryableTranslationProviderError(
                "LM Studio translation request failed temporarily"
            ) from None
        raise PermanentTranslationHttpError(error.code) from None
    except (TimeoutError, urllib.error.URLError):
        raise RetryableTranslationProviderError(
            "LM Studio translation request failed temporarily"
        ) from None
    except (UnicodeError, json.JSONDecodeError):
        raise InvalidTranslationResponseError(
            "LM Studio returned an invalid translation response"
        ) from None
    if not isinstance(document, dict):
        raise InvalidTranslationResponseError("LM Studio returned an invalid translation response")
    return document
