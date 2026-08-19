"""Scoped privacy consent policy for local and cloud correction APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.errors import CorrectionConsentError

ConsentChoice = Literal["reject", "accept_once", "accept_persistently"]
EndpointKind = Literal["local", "cloud", "mock"]
WARNING_POLICY_VERSION: Literal["correction-api-v1"] = "correction-api-v1"

LOCAL_API_WARNING = (
    "Transcript text will be sent to a separate local API process. EWP Transcriber "
    "cannot guarantee what that process logs, retains, or forwards."
)
CLOUD_API_WARNING = (
    "Transcript text will leave this machine and be sent to a cloud API provider. "
    "This operation is not offline and may be subject to provider retention policies."
)


class ConsentModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CorrectionConsentScope(ConsentModel):
    provider_id: str = Field(min_length=1)
    endpoint_kind: EndpointKind
    endpoint_identity: str = Field(min_length=1)
    operation_class: Literal["transcript_correction"] = "transcript_correction"
    warning_policy_version: Literal["correction-api-v1"] = WARNING_POLICY_VERSION


class CorrectionConsentRecord(ConsentModel):
    scope: CorrectionConsentScope


@dataclass(frozen=True, slots=True)
class ConsentDecision:
    authorized: bool
    persist_scope: CorrectionConsentScope | None
    warning: str | None


def correction_api_warning(endpoint_kind: EndpointKind) -> str | None:
    if endpoint_kind == "local":
        return LOCAL_API_WARNING
    if endpoint_kind == "cloud":
        return CLOUD_API_WARNING
    return None


def authorize_correction_api(
    scope: CorrectionConsentScope,
    *,
    offline: bool,
    interactive: bool,
    choice: ConsentChoice | None,
    stored_records: tuple[CorrectionConsentRecord, ...] = (),
) -> ConsentDecision:
    """Authorize only explicit or exact persisted consent before request serialization."""

    if scope.endpoint_kind == "mock":
        return ConsentDecision(True, None, None)
    warning = correction_api_warning(scope.endpoint_kind)
    assert warning is not None
    if offline and scope.endpoint_kind == "cloud":
        raise CorrectionConsentError("Strict offline mode blocks cloud correction APIs")
    if any(record.scope == scope for record in stored_records):
        return ConsentDecision(True, None, warning)
    if choice is None:
        mode = "interactive" if interactive else "non-interactive"
        raise CorrectionConsentError(
            f"Correction API consent is required in {mode} mode before transcript transfer"
        )
    if choice == "reject":
        raise CorrectionConsentError("Correction API use was rejected; no request was made")
    if choice == "accept_once":
        return ConsentDecision(True, None, warning)
    return ConsentDecision(True, scope, warning)
