"""Explicit cloud correction adapter for OpenRouter's OpenAI-compatible API."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from ewp_transcripts.domain.correction import (
    CorrectionRequest,
    CorrectionResponse,
    CorrectionUsage,
)
from ewp_transcripts.domain.errors import (
    PermanentCorrectionProviderError,
    RetryableCorrectionProviderError,
)
from ewp_transcripts.lm_studio_adapter import _chat_request, _parse_chat_response

JsonObject = dict[str, Any]
HttpTransport = Callable[[str, Mapping[str, str], bytes, float], JsonObject]
_REQUEST_CONTRACT = "speaker-blocks-v2"


@dataclass(frozen=True, slots=True)
class OpenRouterAdapterConfig:
    model_id: str
    endpoint: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    output_mode: Literal["json-schema", "json-text"] = "json-schema"
    temperature: float = 0.0
    reasoning_max_tokens: int | None = None

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("OpenRouter model_id must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("OpenRouter temperature must be between 0 and 2")
        if self.output_mode not in {"json-schema", "json-text"}:
            raise ValueError("OpenRouter output_mode must be json-schema or json-text")
        if (
            not self.api_key_env
            or not self.api_key_env.replace("_", "A").isalnum()
            or self.api_key_env[0].isdigit()
        ):
            raise ValueError("OpenRouter api_key_env must be an environment-variable name")
        if self.reasoning_max_tokens is not None and self.reasoning_max_tokens < 0:
            raise ValueError("OpenRouter reasoning_max_tokens must not be negative")
        _normalized_endpoint(self.endpoint)


class OpenRouterCorrectionProvider:
    """Cloud adapter that resolves its bearer secret only after consent succeeds."""

    def __init__(
        self,
        config: OpenRouterAdapterConfig,
        *,
        transport: HttpTransport | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._config = config
        self._endpoint = _normalized_endpoint(config.endpoint)
        self._transport = transport or _urllib_transport
        self._environment = environment if environment is not None else os.environ

    @property
    def provider_id(self) -> str:
        return "openrouter"

    @property
    def model_id(self) -> str:
        return self._config.model_id

    @property
    def endpoint_kind(self) -> Literal["cloud"]:
        return "cloud"

    @property
    def endpoint_identity(self) -> str:
        return self._endpoint

    @property
    def provenance_parameters(self) -> dict[str, str | int | float | bool | None]:
        return {
            "output_mode": self._config.output_mode,
            "temperature": self._config.temperature,
            "request_contract": _REQUEST_CONTRACT,
            "require_parameters": True,
            "allow_fallbacks": False,
            "reasoning_max_tokens": self._config.reasoning_max_tokens,
        }

    def prompt_sha256(self, prompt_id: str) -> str:
        # The common request/response contract is intentionally identical to LM Studio.
        from ewp_transcripts.lm_studio_adapter import (
            LmStudioAdapterConfig,
            LmStudioCorrectionProvider,
        )

        local = LmStudioCorrectionProvider(
            LmStudioAdapterConfig(
                model_id=self.model_id,
                output_mode=self._config.output_mode,
                temperature=self._config.temperature,
            )
        )
        identity = {
            "base_prompt_sha256": local.prompt_sha256(prompt_id),
            "provider_parameters": self.provenance_parameters,
        }
        material = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(material.encode()).hexdigest()

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        if timeout_seconds is None or timeout_seconds <= 0:
            raise ValueError("OpenRouter calls require a positive timeout")
        api_key = self._environment.get(self._config.api_key_env, "").strip()
        if not api_key:
            raise PermanentCorrectionProviderError(
                f"OpenRouter API key is missing; set {self._config.api_key_env}"
            )
        payload_document = _chat_request(self._config, request)  # type: ignore[arg-type]
        payload_document["provider"] = {
            "require_parameters": True,
            "allow_fallbacks": False,
        }
        if self._config.reasoning_max_tokens is not None:
            payload_document["reasoning"] = {
                "max_tokens": self._config.reasoning_max_tokens,
            }
        document = self._transport(
            f"{self._endpoint}/chat/completions",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json.dumps(payload_document, ensure_ascii=False, separators=(",", ":")).encode(),
            timeout_seconds,
        )
        response = _parse_chat_response(
            document,
            request,
            output_mode=self._config.output_mode,
            provider_label="OpenRouter",
        )
        usage = document.get("usage")
        if isinstance(usage, dict):
            response = response.model_copy(
                update={
                    "usage": CorrectionUsage(
                        input_tokens=_optional_nonnegative_int(usage.get("prompt_tokens")),
                        output_tokens=_optional_nonnegative_int(usage.get("completion_tokens")),
                        cost_usd_micros=_optional_cost_micros(usage.get("cost")),
                    )
                }
            )
        return response


def _optional_nonnegative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PermanentCorrectionProviderError("OpenRouter returned invalid usage data")
    return value


def _optional_cost_micros(value: object) -> int | None:
    if value is None:
        return None
    try:
        cost = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PermanentCorrectionProviderError("OpenRouter returned invalid usage data") from None
    if not cost.is_finite() or cost < 0:
        raise PermanentCorrectionProviderError("OpenRouter returned invalid usage data")
    return int((cost * Decimal(1_000_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _normalized_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("OpenRouter endpoint must be an uncredentialed HTTPS URL")
    path = parsed.path.rstrip("/")
    if not path.endswith("/api/v1"):
        raise ValueError("OpenRouter endpoint path must end in /api/v1")
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
            raise RetryableCorrectionProviderError("OpenRouter request failed") from None
        raise PermanentCorrectionProviderError("OpenRouter request was rejected") from None
    except (TimeoutError, urllib.error.URLError):
        raise RetryableCorrectionProviderError("OpenRouter is temporarily unavailable") from None
    except (OSError, json.JSONDecodeError):
        raise PermanentCorrectionProviderError("OpenRouter returned unreadable data") from None
    if not isinstance(document, dict):
        raise PermanentCorrectionProviderError("OpenRouter returned unreadable data")
    return document
