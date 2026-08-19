"""Private immutable cache of validated correction chunk responses."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.correction import validate_correction_response
from ewp_transcripts.correction_execution import (
    CorrectionExecutionMetrics,
    CorrectionExecutionPolicy,
    execute_correction_call,
)
from ewp_transcripts.domain.correction import (
    CorrectionProvider,
    CorrectionRequest,
    CorrectionResponse,
)
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError


class CorrectionResumeEntry(BaseModel):
    """Strict persisted response bound to one complete operation identity."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    operation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    response: CorrectionResponse


@dataclass(frozen=True, slots=True)
class CorrectionCallOutcome:
    response: CorrectionResponse
    resumed: bool
    state_path: Path
    metrics: CorrectionExecutionMetrics


def call_correction_resumable(
    provider: CorrectionProvider,
    request: CorrectionRequest,
    *,
    state_directory: Path,
    execution_policy: CorrectionExecutionPolicy | None = None,
) -> CorrectionCallOutcome:
    """Reuse only an exactly bound validated response or publish one new response."""

    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(state_directory, 0o700)
    state_path = state_directory / f"{request.operation_id}.json"
    if state_path.exists():
        entry = _load_entry(state_path, provider, request)
        return CorrectionCallOutcome(
            entry.response,
            True,
            state_path,
            CorrectionExecutionMetrics(attempts=0, retries=0, elapsed_ms=0),
        )

    execution = execute_correction_call(provider, request, policy=execution_policy)
    response = execution.response
    entry = CorrectionResumeEntry(
        schema_version="1.0",
        operation_id=request.operation_id,
        provider_id=provider.provider_id,
        model_id=provider.model_id,
        prompt_id=request.prompt_id,
        response=response,
    )
    payload = (entry.model_dump_json(indent=2) + "\n").encode()
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".correction-", dir=state_directory)
        temporary_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_path, state_path)
        except FileExistsError:
            entry = _load_entry(state_path, provider, request)
            return CorrectionCallOutcome(
                entry.response,
                True,
                state_path,
                CorrectionExecutionMetrics(attempts=0, retries=0, elapsed_ms=0),
            )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return CorrectionCallOutcome(response, False, state_path, execution.metrics)


def _load_entry(
    path: Path,
    provider: CorrectionProvider,
    request: CorrectionRequest,
) -> CorrectionResumeEntry:
    try:
        entry = CorrectionResumeEntry.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise InvalidCorrectionResponseError(
            f"Cannot read valid correction resume state: {path}"
        ) from error
    if (
        entry.operation_id != request.operation_id
        or entry.provider_id != provider.provider_id
        or entry.model_id != provider.model_id
        or entry.prompt_id != request.prompt_id
    ):
        raise InvalidCorrectionResponseError("Correction resume state identity does not match")
    validate_correction_response(request, entry.response)
    return entry
