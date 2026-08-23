"""Tests for exact-scope automated-translation consent."""

from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import TranslationProviderError
from ewp_transcripts.translation_consent import (
    TranslationConsentScope,
    authorize_translation_api,
    load_translation_consents,
    persist_translation_consent,
)


def test_mock_bypasses_consent_but_local_requires_explicit_choice() -> None:
    mock = TranslationConsentScope(
        provider_id="mock", endpoint_kind="mock", endpoint_identity="in-process"
    )
    local = TranslationConsentScope(
        provider_id="lm-studio",
        endpoint_kind="local",
        endpoint_identity="http://127.0.0.1:1234/v1",
    )

    assert authorize_translation_api(mock, offline=True, interactive=False, choice=None).authorized
    with pytest.raises(TranslationProviderError, match="consent is required"):
        authorize_translation_api(local, offline=True, interactive=False, choice=None)


def test_persisted_scope_is_exact_and_private(tmp_path: Path) -> None:
    path = tmp_path / "translation-consent.json"
    scope = TranslationConsentScope(
        provider_id="lm-studio",
        endpoint_kind="local",
        endpoint_identity="http://127.0.0.1:1234/v1",
    )

    persist_translation_consent(path, scope)
    records = load_translation_consents(path)

    assert records[0].scope == scope
    assert path.stat().st_mode & 0o777 == 0o600
    assert authorize_translation_api(
        scope, offline=True, interactive=False, choice=None, stored_records=records
    ).authorized
