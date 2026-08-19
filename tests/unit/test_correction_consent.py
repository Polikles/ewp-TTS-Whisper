"""Tests for correction API privacy consent policy."""

from pathlib import Path

import pytest

from ewp_transcripts.correction_consent import (
    CLOUD_API_WARNING,
    LOCAL_API_WARNING,
    CorrectionConsentRecord,
    CorrectionConsentScope,
    EndpointKind,
    authorize_correction_api,
    correction_api_warning,
    load_correction_consents,
    persist_correction_consent,
)
from ewp_transcripts.domain.errors import CorrectionConsentError


def _scope(
    kind: EndpointKind = "cloud", *, endpoint: str = "api.example/v1"
) -> CorrectionConsentScope:
    return CorrectionConsentScope(
        provider_id="provider-a",
        endpoint_kind=kind,
        endpoint_identity=endpoint,
    )


def test_mock_needs_no_consent_or_warning() -> None:
    decision = authorize_correction_api(
        _scope("mock", endpoint="in-process"),
        offline=True,
        interactive=False,
        choice=None,
    )

    assert decision.authorized is True
    assert decision.warning is None


def test_offline_cloud_is_blocked_even_with_persisted_consent() -> None:
    scope = _scope()

    with pytest.raises(CorrectionConsentError, match="offline mode"):
        authorize_correction_api(
            scope,
            offline=True,
            interactive=False,
            choice=None,
            stored_records=(CorrectionConsentRecord(scope=scope),),
        )


def test_noninteractive_mode_never_infers_consent() -> None:
    with pytest.raises(CorrectionConsentError, match="non-interactive"):
        authorize_correction_api(
            _scope("local", endpoint="http://127.0.0.1:11434"),
            offline=True,
            interactive=False,
            choice=None,
        )


def test_accept_once_does_not_request_persistence() -> None:
    decision = authorize_correction_api(
        _scope(),
        offline=False,
        interactive=False,
        choice="accept_once",
    )

    assert decision.authorized is True
    assert decision.persist_scope is None
    assert decision.warning == CLOUD_API_WARNING


def test_persistent_consent_is_exact_scope_only() -> None:
    scope = _scope("local", endpoint="http://127.0.0.1:11434")
    accepted = authorize_correction_api(
        scope,
        offline=True,
        interactive=True,
        choice="accept_persistently",
    )
    assert accepted.persist_scope is not None
    record = CorrectionConsentRecord(scope=accepted.persist_scope)
    reused = authorize_correction_api(
        scope,
        offline=True,
        interactive=False,
        choice=None,
        stored_records=(record,),
    )

    assert reused.authorized is True
    with pytest.raises(CorrectionConsentError, match="consent is required"):
        authorize_correction_api(
            _scope("local", endpoint="http://127.0.0.1:9999"),
            offline=True,
            interactive=False,
            choice=None,
            stored_records=(record,),
        )


def test_local_and_cloud_warnings_are_distinct() -> None:
    assert correction_api_warning("local") == LOCAL_API_WARNING
    assert correction_api_warning("cloud") == CLOUD_API_WARNING
    assert LOCAL_API_WARNING != CLOUD_API_WARNING


def test_persistent_store_is_private_atomic_and_deduplicated(tmp_path: Path) -> None:
    path = tmp_path / "config" / "correction-consent.json"
    scope = _scope("local", endpoint="http://127.0.0.1:11434")

    persist_correction_consent(path, scope)
    persist_correction_consent(path, scope)

    records = load_correction_consents(path)
    assert [record.scope for record in records] == [scope]
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert not tuple(path.parent.glob(".consent-*"))


def test_invalid_persistent_store_is_not_silently_replaced(tmp_path: Path) -> None:
    path = tmp_path / "correction-consent.json"
    path.write_text("invalid", encoding="utf-8")

    with pytest.raises(CorrectionConsentError, match="consent store"):
        persist_correction_consent(path, _scope())

    assert path.read_text(encoding="utf-8") == "invalid"
