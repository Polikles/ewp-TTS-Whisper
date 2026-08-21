"""Configuration-driven correction-provider construction."""

from __future__ import annotations

from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.correction import CorrectionProvider
from ewp_transcripts.domain.errors import InvalidConfigurationError
from ewp_transcripts.lm_studio_adapter import (
    LmStudioAdapterConfig,
    LmStudioCorrectionProvider,
)
from ewp_transcripts.openrouter_adapter import (
    OpenRouterAdapterConfig,
    OpenRouterCorrectionProvider,
)


def create_correction_provider(config: ApplicationConfig) -> CorrectionProvider:
    """Construct only an explicitly configured provider without making an API call."""

    correction = config.correction
    if correction.provider == "lm-studio":
        try:
            adapter_config = LmStudioAdapterConfig(
                model_id=correction.model,
                endpoint=correction.endpoint,
                allow_remote_endpoint=correction.allow_remote_endpoint,
                output_mode=correction.output_mode,
                temperature=correction.temperature,
            )
        except ValueError as error:
            raise InvalidConfigurationError("Invalid LM Studio correction configuration") from error
        return LmStudioCorrectionProvider(adapter_config)
    if correction.provider == "openrouter":
        try:
            openrouter_config = OpenRouterAdapterConfig(
                model_id=correction.model,
                endpoint=correction.openrouter_endpoint,
                api_key_env=correction.openrouter_api_key_env,
                output_mode=correction.output_mode,
                temperature=correction.temperature,
            )
        except ValueError as error:
            raise InvalidConfigurationError(
                "Invalid OpenRouter correction configuration"
            ) from error
        return OpenRouterCorrectionProvider(openrouter_config)
    raise InvalidConfigurationError(
        "No correction provider is configured; set correction.provider and correction.model"
    )
