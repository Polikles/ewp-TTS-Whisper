"""Tests for configuration-driven provider construction."""

import pytest

from ewp_transcripts.config import ApplicationConfig, CorrectionConfig
from ewp_transcripts.correction_providers import create_correction_provider
from ewp_transcripts.domain.errors import InvalidConfigurationError


def test_lm_studio_provider_uses_exact_configured_identity() -> None:
    provider = create_correction_provider(
        ApplicationConfig(
            correction=CorrectionConfig(
                provider="lm-studio",
                model="qwen2.5-32b-instruct",
                endpoint="http://localhost:1234/v1",
            )
        )
    )

    assert provider.provider_id == "lm-studio"
    assert provider.model_id == "qwen2.5-32b-instruct"
    assert provider.endpoint_identity == "http://localhost:1234/v1"


def test_disabled_provider_cannot_be_inferred() -> None:
    with pytest.raises(InvalidConfigurationError, match="No correction provider"):
        create_correction_provider(ApplicationConfig())


def test_remote_lm_studio_endpoint_is_rejected_as_configuration_error() -> None:
    config = ApplicationConfig(
        correction=CorrectionConfig(
            provider="lm-studio",
            model="model",
            endpoint="http://example.com/v1",
        )
    )

    with pytest.raises(InvalidConfigurationError, match="Invalid LM Studio"):
        create_correction_provider(config)
