"""Explicitly consented automated-correction operation for the local GUI."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ewp_transcripts.application import CorrectionApplyOutcome, apply_correction
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.correction_dictionary import load_project_correction_dictionary
from ewp_transcripts.correction_providers import create_correction_provider
from ewp_transcripts.domain.errors import ApplicationError


class GuiCorrectionError(ApplicationError):
    """Controlled GUI correction failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


PathResolver = Callable[..., Path]
CorrectionRunner = Callable[..., CorrectionApplyOutcome]
ProviderPreflight = Callable[[Any, ApplicationConfig], None]


class GuiCorrectionController:
    """Generate one non-final correction candidate without browser-held secrets."""

    def __init__(
        self,
        *,
        config: ApplicationConfig,
        resolve_path: PathResolver,
        runner: CorrectionRunner = apply_correction,
        preflight: ProviderPreflight | None = None,
        operation_lock: threading.Lock | None = None,
    ) -> None:
        self._config = config
        self._resolve_path = resolve_path
        self._runner = runner
        self._preflight = preflight or _preflight_provider
        self._lock = operation_lock or threading.Lock()

    def generate(
        self,
        *,
        result: str,
        output_directory: str,
        resume_directory: str,
        provider_name: str,
        model: str,
        endpoint: str,
        allow_remote_endpoint: bool,
        allow_cloud: bool,
        reasoning_max_tokens: int | None,
        dictionary_path: str,
        project_id: str,
        confirmed: bool,
    ) -> dict[str, Any]:
        if not confirmed:
            raise GuiCorrectionError(
                "GUI_CORRECTION_CONFIRMATION_REQUIRED",
                "Confirm provider disclosure and non-final candidate review requirements.",
            )
        if provider_name not in {"lm-studio", "openrouter"}:
            raise GuiCorrectionError("GUI_CORRECTION_PROVIDER_INVALID", "Unknown provider")
        if not model.strip():
            raise GuiCorrectionError("GUI_CORRECTION_MODEL_REQUIRED", "Model is required")
        if provider_name == "openrouter" and not allow_cloud:
            raise GuiCorrectionError(
                "GUI_CORRECTION_CLOUD_OPT_IN_REQUIRED",
                "OpenRouter requires explicit cloud opt-in.",
            )
        result_path = self._resolve_path(result)
        output_path = self._resolve_path(output_directory, directory=True)
        resume_path = self._resolve_path(resume_directory, directory=True)
        dictionary = None
        dictionary_sha256 = None
        if project_id and not dictionary_path:
            raise GuiCorrectionError(
                "GUI_CORRECTION_DICTIONARY_INVALID",
                "A project ID cannot be selected without a dictionary.",
            )
        if dictionary_path:
            dictionary, dictionary_sha256 = load_project_correction_dictionary(
                self._resolve_path(dictionary_path)
            )
            if project_id and project_id != dictionary.project_id:
                raise GuiCorrectionError(
                    "GUI_CORRECTION_DICTIONARY_INVALID",
                    "The selected project ID does not match the dictionary.",
                )
            project_id = dictionary.project_id
        correction_updates: dict[str, Any] = {
            "provider": provider_name,
            "model": model.strip(),
            "allow_remote_endpoint": allow_remote_endpoint,
        }
        if provider_name == "lm-studio":
            correction_updates["endpoint"] = endpoint.strip()
        else:
            correction_updates["openrouter_endpoint"] = endpoint.strip()
            correction_updates["openrouter_reasoning_max_tokens"] = reasoning_max_tokens
        config = self._config.model_copy(
            update={
                "general": self._config.general.model_copy(
                    update={"offline": not allow_cloud, "interactive": False}
                ),
                "correction": self._config.correction.model_copy(update=correction_updates),
            }
        )
        provider = create_correction_provider(config)
        self._preflight(provider, config)
        if not self._lock.acquire(blocking=False):
            raise GuiCorrectionError(
                "GUI_CORRECTION_BUSY", "Another GUI correction is already running."
            )
        try:
            outcome = self._runner(
                result_path,
                config=config,
                provider=provider,
                consent_choice="accept_once",
                output_directory=output_path,
                resume_directory=resume_path,
                dictionary=dictionary,
                dictionary_sha256=dictionary_sha256,
                dictionary_project_id=project_id or None,
            )
        finally:
            self._lock.release()
        revision = outcome.revision
        return {
            "candidate_path": str(outcome.revision_path),
            "result_path": str(outcome.base_result_path),
            "job_id": revision.job_id,
            "revision_number": revision.revision_number,
            "provider": provider.provider_id,
            "model": provider.model_id,
            "endpoint_kind": provider.endpoint_kind,
            "statistics": revision.statistics.model_dump(mode="json"),
            "warnings": [warning.model_dump(mode="json") for warning in revision.warnings],
            "dictionary": (
                revision.provenance.llm.dictionary.model_dump(mode="json")
                if revision.provenance.llm and revision.provenance.llm.dictionary
                else None
            ),
            "final": False,
        }


def _preflight_provider(provider: Any, config: ApplicationConfig) -> None:
    """Fail quickly when credentials, backend, or exact model are unavailable."""

    headers = {"Accept": "application/json"}
    if provider.provider_id == "openrouter":
        key = os.environ.get(config.correction.openrouter_api_key_env, "").strip()
        if not key:
            raise GuiCorrectionError(
                "GUI_CORRECTION_CREDENTIAL_MISSING",
                "Server environment variable "
                f"{config.correction.openrouter_api_key_env} is missing.",
            )
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        f"{provider.endpoint_identity.rstrip('/')}/models", headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=3.0) as response:  # noqa: S310
            payload = response.read(1_048_577)
            if len(payload) > 1_048_576:
                raise ValueError("Provider model response is too large")
            document = json.loads(payload)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise GuiCorrectionError(
            "GUI_CORRECTION_BACKEND_UNAVAILABLE",
            "Correction backend did not pass the three-second readiness check.",
        ) from error
    models = document.get("data") if isinstance(document, dict) else None
    identifiers = {
        item.get("id") for item in models or () if isinstance(item, dict) and item.get("id")
    }
    if provider.model_id not in identifiers:
        raise GuiCorrectionError(
            "GUI_CORRECTION_MODEL_UNAVAILABLE",
            "The selected exact model is not available from the correction backend.",
        )
