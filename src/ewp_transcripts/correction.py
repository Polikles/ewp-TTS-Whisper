"""Deterministic chunk planning and network-free correction test provider."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.correction import (
    CorrectionChange,
    CorrectionRequest,
    CorrectionResponse,
    CorrectionToken,
)
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.domain.review import ReviewAnchor, ReviewSpeakerBlock
from ewp_transcripts.domain.revision import (
    RevisionLlmProvenance,
    RevisionProvenance,
    TranscriptRevision,
)
from ewp_transcripts.effective_transcript import (
    EffectiveToken,
    EffectiveTranscript,
    resolve_effective_transcript,
)
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision


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
    provider_id: str,
    model_id: str,
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
        (
            f"{provider_id}\0{model_id}\0{prompt_id}\0{transcript.language}\0"
            f"{chunk.chunk_index}\0{chunk.editable_start}:{chunk.editable_end}\0"
            f"{chunk.context_start}:{chunk.context_end}\0{chunk.content_sha256}"
        ).encode()
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


def build_mock_correction_revision(
    result_path: Path,
    provider: DeterministicMockCorrectionProvider,
    *,
    config: CorrectionChunkConfig | None = None,
    prompt_id: str = "faithful-correction-v1",
) -> TranscriptRevision:
    """Exercise provider-to-review-to-revision flow without network or persistence."""

    base = load_canonical_result(result_path)
    effective = resolve_effective_transcript(base)
    chunks = plan_correction_chunks(effective, config)
    anchors: list[ReviewAnchor] = []
    for chunk in chunks:
        request = build_correction_request(
            effective,
            chunk,
            prompt_id=prompt_id,
            provider_id=provider.provider_id,
            model_id=provider.model_id,
        )
        response = provider.correct(request)
        corrected = validate_correction_response(request, response)
        speakers = _corrected_speakers(request, response)
        anchors.append(
            ReviewAnchor(
                first_word_id=effective.tokens[chunk.editable_start].source_word_ids[0],
                last_word_id=effective.tokens[chunk.editable_end - 1].source_word_ids[-1],
                speaker_blocks=_group_corrected_blocks(corrected, speakers),
            )
        )
    prepared = prepare_review(result_path)
    review = prepared.model_copy(update={"anchors": tuple(anchors)})
    prompt_sha256 = hashlib.sha256(prompt_id.encode()).hexdigest()
    return build_revision(
        review,
        base,
        base_path=result_path,
        provenance=RevisionProvenance(
            method="llm",
            interface="api",
            llm=RevisionLlmProvenance(
                provider=provider.provider_id,
                model=provider.model_id,
                endpoint_kind="mock",
                prompt_id=prompt_id,
                prompt_sha256=prompt_sha256,
                parameters=None,
            ),
        ),
    )


def _corrected_speakers(
    request: CorrectionRequest,
    response: CorrectionResponse,
) -> tuple[str, ...]:
    speakers: list[str] = []
    previous_end = 0
    for change in response.proposed_changes:
        speakers.extend(
            token.speaker_id for token in request.editable_tokens[previous_end : change.start_index]
        )
        changed_speakers = {
            token.speaker_id
            for token in request.editable_tokens[change.start_index : change.end_index]
        }
        if len(changed_speakers) != 1:
            raise InvalidCorrectionResponseError(
                "Correction response change crosses a speaker boundary"
            )
        speakers.extend([next(iter(changed_speakers))] * len(change.after.split()))
        previous_end = change.end_index
    speakers.extend(token.speaker_id for token in request.editable_tokens[previous_end:])
    return tuple(speakers)


def _group_corrected_blocks(
    corrected: tuple[str, ...],
    speakers: tuple[str, ...],
) -> tuple[ReviewSpeakerBlock, ...]:
    blocks: list[ReviewSpeakerBlock] = []
    current_speaker: str | None = None
    words: list[str] = []
    for word, speaker in zip(corrected, speakers, strict=True):
        if current_speaker is not None and speaker != current_speaker:
            blocks.append(ReviewSpeakerBlock(speaker_id=current_speaker, text=" ".join(words)))
            words = []
        current_speaker = speaker
        words.append(word)
    if current_speaker is not None:
        blocks.append(ReviewSpeakerBlock(speaker_id=current_speaker, text=" ".join(words)))
    return tuple(blocks)


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
