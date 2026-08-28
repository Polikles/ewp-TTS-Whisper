"""Automated translation candidate generation for the local GUI."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from ewp_transcripts.application import AutomatedTranslationOutcome, apply_automated_translation
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.errors import ApplicationError
from ewp_transcripts.domain.translation import Language, TranslationStyle
from ewp_transcripts.translation_dictionary import load_project_translation_dictionary
from ewp_transcripts.translation_lm_studio import (
    LmStudioTranslationConfig,
    LmStudioTranslationProvider,
)


class GuiTranslationError(ApplicationError):
    """Controlled browser translation failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


PathResolver = Callable[..., Path]
TranslationRunner = Callable[..., AutomatedTranslationOutcome]
ProviderPreflight = Callable[[LmStudioTranslationProvider], None]


class GuiTranslationController:
    """Create one immutable, explicitly non-final LM Studio candidate."""

    def __init__(
        self,
        *,
        config: ApplicationConfig,
        resolve_path: PathResolver,
        runner: TranslationRunner = apply_automated_translation,
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
        source_revision: str,
        output_directory: str,
        resume_directory: str,
        target_language: str,
        model: str,
        endpoint: str,
        allow_remote_endpoint: bool,
        output_mode: str,
        dictionary_path: str,
        confirmed: bool,
    ) -> dict[str, Any]:
        if not confirmed:
            raise GuiTranslationError(
                "GUI_TRANSLATION_CONFIRMATION_REQUIRED",
                "Confirm API disclosure and non-final translation review requirements.",
            )
        if target_language not in {"pl", "en"}:
            raise GuiTranslationError(
                "GUI_TRANSLATION_LANGUAGE_INVALID", "Target language must be pl or en."
            )
        if not model.strip():
            raise GuiTranslationError("GUI_TRANSLATION_MODEL_REQUIRED", "Model is required.")
        if output_mode not in {"json-schema", "json-text", "plain-text"}:
            raise GuiTranslationError(
                "GUI_TRANSLATION_OUTPUT_MODE_INVALID", "Unknown translation output mode."
            )
        result_path = self._resolve_path(result)
        revision_path = self._resolve_path(source_revision) if source_revision else None
        output_path = self._resolve_path(output_directory, directory=True)
        resume_path = self._resolve_path(resume_directory, directory=True)
        dictionary = None
        dictionary_sha256 = None
        if dictionary_path:
            dictionary, dictionary_sha256 = load_project_translation_dictionary(
                self._resolve_path(dictionary_path)
            )
        provider = LmStudioTranslationProvider(
            LmStudioTranslationConfig(
                model_id=model.strip(),
                endpoint=endpoint.strip(),
                allow_remote_endpoint=allow_remote_endpoint,
                output_mode=cast(Literal["json-schema", "json-text", "plain-text"], output_mode),
                temperature=0.0,
            )
        )
        self._preflight(provider)
        if not self._lock.acquire(blocking=False):
            raise GuiTranslationError(
                "GUI_TRANSLATION_BUSY", "Another GUI translation is already running."
            )
        try:
            outcome = self._runner(
                result_path,
                config=self._config,
                provider=provider,
                target_language=cast(Language, target_language),
                revision_path=revision_path,
                style=TranslationStyle(register="preserve", discourse="preserve"),
                resume_directory=resume_path,
                output_directory=output_path,
                consent_choice="accept_once",
                context_units=1,
                dictionary=dictionary,
                dictionary_sha256=dictionary_sha256,
            )
        finally:
            self._lock.release()
        translation = outcome.translation
        if outcome.translation_path is None:
            raise GuiTranslationError(
                "GUI_TRANSLATION_REQUEST_INVALID",
                "Translation candidate was not published.",
            )
        llm = translation.provenance.llm
        assert llm is not None
        return {
            "candidate_path": str(outcome.translation_path),
            "result_path": str(outcome.result_path),
            "job_id": translation.job_id,
            "translation_number": translation.translation_number,
            "direction": translation.direction.model_dump(mode="json"),
            "source_verification": translation.source.verification,
            "provider": llm.provider,
            "model": llm.model,
            "statistics": translation.statistics.model_dump(mode="json"),
            "warnings": [warning.model_dump(mode="json") for warning in translation.warnings],
            "dictionary": (
                translation.dictionary.model_dump(mode="json")
                if translation.dictionary is not None
                else None
            ),
            "final": False,
        }


def _preflight_provider(provider: LmStudioTranslationProvider) -> None:
    provider.preflight(timeout_seconds=3.0)
