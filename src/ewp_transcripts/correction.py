"""Deterministic chunk planning and network-free correction test provider."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from ewp_transcripts.domain.correction import (
    CorrectionChange,
    CorrectionRequest,
    CorrectionResponse,
    CorrectionToken,
)
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript


@dataclass(frozen=True, slots=True)
class CorrectionChunkConfig:
    target_tokens: int = 600
    max_tokens: int = 800
    context_tokens: int = 80

    def __post_init__(self) -> None:
        if self.target_tokens < 1:
            raise ValueError("target_tokens must be positive")
        if self.max_tokens < self.target_tokens:
            raise ValueError("max_tokens must be at least target_tokens")
        if self.context_tokens < 0:
            raise ValueError("context_tokens must not be negative")


@dataclass(frozen=True, slots=True)
class CorrectionChunk:
    chunk_index: int
    editable_start: int
    editable_end: int
    context_start: int
    context_end: int
    content_sha256: str


def plan_correction_chunks(
    transcript: EffectiveTranscript,
    config: CorrectionChunkConfig | None = None,
) -> tuple[CorrectionChunk, ...]:
    """Partition effective tokens once while adding bounded read-only context."""

    config = config or CorrectionChunkConfig()
    tokens = transcript.tokens
    if not tokens:
        return ()
    chunks: list[CorrectionChunk] = []
    start = 0
    while start < len(tokens):
        end = _choose_editable_end(tokens, start, config)
        context_start = max(0, start - config.context_tokens)
        context_end = min(len(tokens), end + config.context_tokens)
        digest = hashlib.sha256()
        for token in tokens[context_start:context_end]:
            digest.update(token.token_id.encode())
            digest.update(b"\0")
            digest.update(token.text.encode())
            digest.update(b"\0")
            digest.update(token.speaker_id.encode())
            digest.update(b"\n")
        chunks.append(
            CorrectionChunk(
                chunk_index=len(chunks),
                editable_start=start,
                editable_end=end,
                context_start=context_start,
                context_end=context_end,
                content_sha256=digest.hexdigest(),
            )
        )
        start = end
    return tuple(chunks)


def build_correction_request(
    transcript: EffectiveTranscript,
    chunk: CorrectionChunk,
    *,
    prompt_id: str,
) -> CorrectionRequest:
    """Build a provider request with editable ownership explicit in its structure."""

    def convert(index: int) -> CorrectionToken:
        token = transcript.tokens[index]
        return CorrectionToken(
            local_index=index - chunk.editable_start,
            token_id=token.token_id,
            text=token.text,
            speaker_id=token.speaker_id,
        )

    operation_id = hashlib.sha256(
        f"{prompt_id}:{transcript.language}:{chunk.chunk_index}:{chunk.content_sha256}".encode()
    ).hexdigest()
    return CorrectionRequest(
        operation_id=operation_id,
        prompt_id=prompt_id,
        language=_supported_language(transcript.language),
        preceding_context=tuple(
            convert(index) for index in range(chunk.context_start, chunk.editable_start)
        ),
        editable_tokens=tuple(
            convert(index) for index in range(chunk.editable_start, chunk.editable_end)
        ),
        following_context=tuple(
            convert(index) for index in range(chunk.editable_end, chunk.context_end)
        ),
    )


class DeterministicMockCorrectionProvider:
    """In-process provider used to test contracts without network or model access."""

    def __init__(
        self,
        replacements: dict[str, tuple[str, Literal["asr_lexical", "proper_name"]]] | None = None,
    ) -> None:
        self._replacements = replacements or {}

    @property
    def provider_id(self) -> str:
        return "ewp-mock"

    @property
    def model_id(self) -> str:
        return "deterministic-replacements-v1"

    @property
    def endpoint_kind(self) -> Literal["mock"]:
        return "mock"

    def correct(self, request: CorrectionRequest) -> CorrectionResponse:
        corrected: list[str] = []
        changes: list[CorrectionChange] = []
        for index, token in enumerate(request.editable_tokens):
            replacement = self._replacements.get(token.text)
            if replacement is None:
                corrected.append(token.text)
                continue
            after, category = replacement
            corrected.append(after)
            changes.append(
                CorrectionChange(
                    start_index=index,
                    end_index=index + 1,
                    before=token.text,
                    after=after,
                    category=category,
                )
            )
        return CorrectionResponse(
            operation_id=request.operation_id,
            corrected_text=" ".join(corrected),
            proposed_changes=tuple(changes),
        )


def validate_correction_response(
    request: CorrectionRequest,
    response: CorrectionResponse,
) -> tuple[str, ...]:
    """Validate proposed spans and reconstruct the provider's corrected token stream."""

    if response.operation_id != request.operation_id:
        raise InvalidCorrectionResponseError("Correction response operation ID does not match")
    changes = response.proposed_changes
    previous_end = 0
    corrected: list[str] = []
    for change in changes:
        if change.start_index < previous_end:
            raise InvalidCorrectionResponseError(
                "Correction response changes overlap or are unsorted"
            )
        if change.end_index > len(request.editable_tokens):
            raise InvalidCorrectionResponseError(
                "Correction response change is outside editable text"
            )
        corrected.extend(
            token.text for token in request.editable_tokens[previous_end : change.start_index]
        )
        before = " ".join(
            token.text for token in request.editable_tokens[change.start_index : change.end_index]
        )
        if before != change.before:
            raise InvalidCorrectionResponseError(
                "Correction response before text does not match the editable source"
            )
        corrected.extend(change.after.split())
        previous_end = change.end_index
    corrected.extend(token.text for token in request.editable_tokens[previous_end:])
    if " ".join(corrected) != _normalize_provider_text(response.corrected_text):
        raise InvalidCorrectionResponseError(
            "Correction response proposed changes do not reconstruct corrected text"
        )
    return tuple(corrected)


def _choose_editable_end(
    tokens: tuple[EffectiveToken, ...],
    start: int,
    config: CorrectionChunkConfig,
) -> int:
    remaining = len(tokens) - start
    if remaining <= config.max_tokens:
        return len(tokens)
    target = start + config.target_tokens
    maximum = min(len(tokens), start + config.max_tokens)
    candidates = [
        boundary
        for boundary in range(start + 1, maximum + 1)
        if _is_preferred_boundary(tokens, boundary)
    ]
    if not candidates:
        return maximum
    return min(candidates, key=lambda boundary: (abs(boundary - target), boundary))


def _is_preferred_boundary(tokens: tuple[EffectiveToken, ...], boundary: int) -> bool:
    previous = tokens[boundary - 1]
    if previous.text.rstrip().endswith((".", "?", "!")):
        return True
    return boundary < len(tokens) and previous.speaker_id != tokens[boundary].speaker_id


def _supported_language(language: str) -> Literal["pl", "en"]:
    if language == "pl":
        return "pl"
    if language == "en":
        return "en"
    raise ValueError(f"Automated correction requires a resolved language: {language}")


def _normalize_provider_text(text: str) -> str:
    return " ".join(text.split())
