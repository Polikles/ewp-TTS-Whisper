"""Configuration-driven correction-provider construction."""

from __future__ import annotations

from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.correction import CorrectionProvider
from ewp_transcripts.domain.errors import InvalidConfigurationError
from ewp_transcripts.lm_studio_adapter import (
    LmStudioAdapterConfig,
    LmStudioCorrectionProvider,
)


def create_correction_provider(config: ApplicationConfig) -> CorrectionProvider:
    """Construct only an explicitly configured provider without making an API call."""

    correction = config.correction
    if correction.provider == "lm-studio":
        try:
            adapter_config = LmStudioAdapterConfig(
                model_id=correction.model,
                endpoint=correction.endpoint,
                temperature=correction.temperature,
            )
        except ValueError as error:
            raise InvalidConfigurationError("Invalid LM Studio correction configuration") from error
        return LmStudioCorrectionProvider(adapter_config)
    raise InvalidConfigurationError(
        "No correction provider is configured; set correction.provider and correction.model"
    )
