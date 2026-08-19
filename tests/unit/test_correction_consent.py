"""Tests for correction API privacy consent policy."""

import pytest

from ewp_transcripts.correction_consent import (
    CLOUD_API_WARNING,
    LOCAL_API_WARNING,
    CorrectionConsentRecord,
    CorrectionConsentScope,
    EndpointKind,
    authorize_correction_api,
    correction_api_warning,
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
