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


def test_explicit_remote_lm_studio_endpoint_is_constructed() -> None:
    provider = create_correction_provider(
        ApplicationConfig(
            correction=CorrectionConfig(
                provider="lm-studio",
                model="qwen2.5-14b-instruct",
                endpoint="http://100.99.201.120:1234/v1",
                allow_remote_endpoint=True,
            )
        )
    )

    assert provider.endpoint_identity == "http://100.99.201.120:1234/v1"


def test_openrouter_provider_is_cloud_and_does_not_require_key_at_construction() -> None:
    provider = create_correction_provider(
        ApplicationConfig(
            correction=CorrectionConfig(
                provider="openrouter",
                model="qwen/qwen-2.5-72b-instruct",
            )
        )
    )

    assert provider.provider_id == "openrouter"
    assert provider.endpoint_kind == "cloud"
    assert provider.endpoint_identity == "https://openrouter.ai/api/v1"
