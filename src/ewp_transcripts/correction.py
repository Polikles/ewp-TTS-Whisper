"""Deterministic chunk planning and network-free correction test provider."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from ewp_transcripts.correction_dictionary import (
    ProjectCorrectionDictionary,
    select_correction_dictionary_terms,
)
from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result
from ewp_transcripts.domain.correction import (
    CorrectionCategory,
    CorrectionChange,
    CorrectionProvider,
    CorrectionRequest,
    CorrectionResponse,
    CorrectionToken,
    CorrectionUsage,
)
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.domain.review import ReviewAnchor, ReviewSpeakerBlock
from ewp_transcripts.domain.revision import (
    RevisionDictionaryProvenance,
    RevisionLlmProvenance,
    RevisionProvenance,
    TranscriptRevision,
    load_transcript_revision,
    sha256_file,
)
from ewp_transcripts.effective_transcript import (
    EffectiveToken,
    EffectiveTranscript,
    resolve_effective_transcript,
)
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision

_TOKEN_DRIFT_RATIO = 0.10
_TOKEN_DRIFT_FLOOR = 4
_NUMERIC_LITERAL = re.compile(r"\d+(?:[.,]\d+)*")


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
        end = _mapping_safe_end(tokens, start, end)
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


def _mapping_safe_end(tokens: tuple[EffectiveToken, ...], start: int, end: int) -> int:
    """Keep tokens sharing one canonical mapping inside one editable chunk."""

    if end >= len(tokens):
        return end

    def safe(boundary: int) -> bool:
        left = tokens[boundary - 1].source_word_ids
        right = tokens[boundary].source_word_ids
        return bool(left and right and set(left).isdisjoint(right))

    if safe(end):
        return end
    candidate = end - 1
    while candidate > start:
        if safe(candidate):
            return candidate
        candidate -= 1
    candidate = end + 1
    while candidate < len(tokens):
        if safe(candidate):
            return candidate
        candidate += 1
    return len(tokens)


def build_correction_request(
    transcript: EffectiveTranscript,
    chunk: CorrectionChunk,
    *,
    prompt_id: str,
    provider_id: str,
    model_id: str,
    prompt_sha256: str | None = None,
    dictionary: ProjectCorrectionDictionary | None = None,
    dictionary_sha256: str | None = None,
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

    resolved_prompt_sha256 = prompt_sha256 or hashlib.sha256(prompt_id.encode()).hexdigest()
    editable_text = " ".join(
        transcript.tokens[index].text for index in range(chunk.editable_start, chunk.editable_end)
    )
    dictionary_terms = (
        select_correction_dictionary_terms(dictionary, editable_text) if dictionary else ()
    )
    dictionary_identity = (
        f"{dictionary.dictionary_id}\0{dictionary_sha256}" if dictionary is not None else "none"
    )
    operation_id = hashlib.sha256(
        (
            f"{provider_id}\0{model_id}\0{prompt_id}\0{resolved_prompt_sha256}\0"
            f"{transcript.language}\0"
            f"{chunk.chunk_index}\0{chunk.editable_start}:{chunk.editable_end}\0"
            f"{chunk.context_start}:{chunk.context_end}\0{chunk.content_sha256}\0"
            f"{dictionary_identity}"
        ).encode()
    ).hexdigest()
    return CorrectionRequest(
        operation_id=operation_id,
        prompt_id=prompt_id,
        prompt_sha256=resolved_prompt_sha256,
        language=_supported_language(transcript.language),
        dictionary_id=dictionary.dictionary_id if dictionary is not None else None,
        dictionary_sha256=dictionary_sha256,
        dictionary_terms=dictionary_terms,
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

    @property
    def endpoint_identity(self) -> str:
        return "in-process"

    @property
    def provenance_parameters(self) -> dict[str, str | int | float | bool | None]:
        return {"request_contract": "deterministic-replacements-v1"}

    def prompt_sha256(self, prompt_id: str) -> str:
        return hashlib.sha256(f"ewp-mock-v1\0{prompt_id}".encode()).hexdigest()

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        del timeout_seconds
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
            usage=CorrectionUsage(
                input_tokens=(
                    len(request.preceding_context)
                    + len(request.editable_tokens)
                    + len(request.following_context)
                ),
                output_tokens=len(corrected),
                cost_usd_micros=0,
            ),
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
            expected_sha256 = hashlib.sha256(before.encode("utf-8")).hexdigest()[:16]
            reported_sha256 = hashlib.sha256(change.before.encode("utf-8")).hexdigest()[:16]
            reported_width = len(change.before.split())
            reported_matches = [
                index
                for index in range(len(request.editable_tokens) - reported_width + 1)
                if " ".join(
                    token.text for token in request.editable_tokens[index : index + reported_width]
                )
                == change.before
            ]
            match_summary = ",".join(str(index) for index in reported_matches[:8]) or "none"
            raise InvalidCorrectionResponseError(
                "Correction response before text does not match the editable source "
                f"(span={change.start_index}:{change.end_index}, "
                f"expected_tokens={change.end_index - change.start_index}, "
                f"reported_tokens={reported_width}, "
                f"expected_chars={len(before)}, reported_chars={len(change.before)}, "
                f"expected_sha256={expected_sha256}, reported_sha256={reported_sha256}, "
                f"reported_match_count={len(reported_matches)}, "
                f"reported_match_positions={match_summary})"
            )
        if not _change_category_matches(change.before, change.after, change.category):
            raise InvalidCorrectionResponseError(
                "Correction response change category does not match its text edit"
            )
        corrected.extend(change.after.split())
        previous_end = change.end_index
    corrected.extend(token.text for token in request.editable_tokens[previous_end:])
    if " ".join(corrected) != _normalize_provider_text(response.corrected_text):
        raise InvalidCorrectionResponseError(
            "Correction response proposed changes do not reconstruct corrected text"
        )
    return tuple(corrected)


def derive_correction_response(
    request: CorrectionRequest,
    *,
    corrected_text: str,
    usage: CorrectionUsage | None = None,
) -> CorrectionResponse:
    """Derive an exact local change list from provider-corrected editable text."""

    source = tuple(token.text for token in request.editable_tokens)
    corrected = tuple(corrected_text.split())
    changes: list[CorrectionChange] = []
    matcher = SequenceMatcher(a=source, b=corrected, autojunk=False)
    for tag, source_start, source_end, corrected_start, corrected_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        before = " ".join(source[source_start:source_end])
        after = " ".join(corrected[corrected_start:corrected_end])
        changes.append(
            CorrectionChange(
                start_index=source_start,
                end_index=source_end,
                before=before,
                after=after,
                category=_derived_category(before, after),
            )
        )
    response = CorrectionResponse(
        operation_id=request.operation_id,
        corrected_text=" ".join(corrected),
        proposed_changes=tuple(changes),
        usage=usage,
    )
    validate_correction_response(request, response)
    return response


def _derived_category(before: str, after: str) -> CorrectionCategory:
    if not before or not after:
        return "asr_lexical"
    if before.casefold() == after.casefold():
        return "capitalization"
    if _without_punctuation(before) == _without_punctuation(after):
        return "punctuation"
    if _without_punctuation(before).casefold() == _without_punctuation(after).casefold():
        return "sentence_boundary"
    return "asr_lexical"


def _change_category_matches(before: str, after: str, category: str) -> bool:
    if category == "punctuation":
        return _without_punctuation(before) == _without_punctuation(after)
    if category == "capitalization":
        return before.casefold() == after.casefold()
    if category == "sentence_boundary":
        return _without_punctuation(before).casefold() == _without_punctuation(after).casefold()
    return True


def _without_punctuation(value: str) -> str:
    characters = "".join(
        character for character in value if not unicodedata.category(character).startswith("P")
    )
    return " ".join(characters.split())


def build_correction_revision(
    result_path: Path,
    provider: CorrectionProvider,
    *,
    source_revision_path: Path | None = None,
    config: CorrectionChunkConfig | None = None,
    prompt_id: str = "faithful-correction-v1",
    resume_directory: Path | None = None,
    execution_policy: object | None = None,
    dictionary: ProjectCorrectionDictionary | None = None,
    dictionary_sha256: str | None = None,
) -> TranscriptRevision:
    """Build one provider-backed revision without publishing it."""

    from ewp_transcripts.correction_execution import CorrectionExecutionPolicy

    if execution_policy is not None and not isinstance(execution_policy, CorrectionExecutionPolicy):
        raise TypeError("execution_policy must be CorrectionExecutionPolicy")

    base = load_canonical_result(result_path)
    parent = (
        load_transcript_revision(source_revision_path) if source_revision_path is not None else None
    )
    effective = resolve_effective_transcript(base, parent, base_path=result_path)
    if dictionary is not None:
        if dictionary_sha256 is None:
            raise InvalidCorrectionResponseError("Correction dictionary SHA-256 is required")
        if base.job_id not in dictionary.job_ids:
            raise InvalidCorrectionResponseError("Correction dictionary does not include this job")
    chunks = plan_correction_chunks(effective, config)
    corrected_blocks: list[tuple[ReviewSpeakerBlock, ...]] = []
    for chunk in chunks:
        request = build_correction_request(
            effective,
            chunk,
            prompt_id=prompt_id,
            provider_id=provider.provider_id,
            model_id=provider.model_id,
            prompt_sha256=provider.prompt_sha256(prompt_id),
            dictionary=dictionary,
            dictionary_sha256=dictionary_sha256,
        )
        if resume_directory is None:
            from ewp_transcripts.correction_execution import execute_correction_call

            response = execute_correction_call(
                provider,
                request,
                policy=execution_policy,
            ).response
        else:
            # Local import keeps persistence dependent on the correction contract while
            # allowing the pure planner/validator module to remain independently usable.
            from ewp_transcripts.correction_state import call_correction_resumable

            response = call_correction_resumable(
                provider,
                request,
                state_directory=resume_directory,
                execution_policy=execution_policy,
            ).response
        corrected = validate_correction_response(request, response)
        _require_numeric_literals_unchanged(request, response)
        _require_conservative_token_drift(request, response)
        speakers = _corrected_speakers(request, response)
        corrected_blocks.append(_group_corrected_blocks(corrected, speakers))
    prepared = prepare_review(result_path)
    anchors = _correction_review_anchors(base, effective, chunks, corrected_blocks)
    header = prepared.header
    if parent is not None:
        assert source_revision_path is not None
        header = header.model_copy(
            update={
                "source_revision_id": parent.revision_id,
                "source_revision_sha256": sha256_file(source_revision_path),
                "source_revision_number": parent.revision_number,
            }
        )
    review = prepared.model_copy(update={"header": header, "anchors": anchors})
    prompt_sha256 = provider.prompt_sha256(prompt_id)
    revision = build_revision(
        review,
        base,
        base_path=result_path,
        provenance=RevisionProvenance(
            method="llm",
            interface="api",
            llm=RevisionLlmProvenance(
                provider=provider.provider_id,
                model=provider.model_id,
                endpoint_kind=provider.endpoint_kind,
                prompt_id=prompt_id,
                prompt_sha256=prompt_sha256,
                parameters=getattr(provider, "provenance_parameters", None),
                dictionary=(
                    RevisionDictionaryProvenance(
                        version=dictionary.dictionary_version,
                        dictionary_id=dictionary.dictionary_id,
                        project_id=dictionary.project_id,
                        sha256=dictionary_sha256,
                        proposal_sha256=dictionary.proposal_sha256,
                    )
                    if dictionary is not None and dictionary_sha256 is not None
                    else None
                ),
            ),
        ),
        parent_revision=parent,
        parent_path=source_revision_path,
        preserve_speaker_attribution=True,
    )
    if revision.statistics.speaker_changes:
        raise InvalidCorrectionResponseError(
            "Automated correction changed speaker attribution during revision alignment"
        )
    return revision


def _mapped_edge_word_id(tokens: tuple[EffectiveToken, ...], *, first: bool) -> str:
    ordered = tokens if first else tuple(reversed(tokens))
    for token in ordered:
        if token.source_word_ids:
            return token.source_word_ids[0 if first else -1]
    raise InvalidCorrectionResponseError(
        "Automated correction chunk contains no canonical word mapping"
    )


def _correction_review_anchors(
    base: CanonicalResult,
    effective: EffectiveTranscript,
    chunks: tuple[CorrectionChunk, ...],
    blocks: list[tuple[ReviewSpeakerBlock, ...]],
) -> tuple[ReviewAnchor, ...]:
    canonical_words = tuple(word for segment in base.transcript.segments for word in segment.words)
    positions = {word.word_id: index for index, word in enumerate(canonical_words)}
    starts = [0]
    for chunk in chunks[1:]:
        word_id = _mapped_edge_word_id(
            effective.tokens[chunk.editable_start : chunk.editable_end], first=True
        )
        starts.append(positions[word_id])
    if any(right <= left for left, right in zip(starts, starts[1:], strict=False)):
        raise InvalidCorrectionResponseError(
            "Automated correction chunks cannot be mapped to disjoint canonical anchors"
        )
    anchors: list[ReviewAnchor] = []
    for index, (start, speaker_blocks) in enumerate(zip(starts, blocks, strict=True)):
        end = starts[index + 1] - 1 if index + 1 < len(starts) else len(canonical_words) - 1
        anchors.append(
            ReviewAnchor(
                first_word_id=canonical_words[start].word_id,
                last_word_id=canonical_words[end].word_id,
                speaker_blocks=speaker_blocks,
            )
        )
    return tuple(anchors)


# Compatibility alias while the first network-free slice remains referenced by tests.
build_mock_correction_revision = build_correction_revision


def _require_conservative_token_drift(
    request: CorrectionRequest, response: CorrectionResponse
) -> None:
    source_count = len(request.editable_tokens)
    corrected_count = len(response.corrected_text.split())
    allowed_drift = max(
        _TOKEN_DRIFT_FLOOR,
        int(source_count * _TOKEN_DRIFT_RATIO + 0.999999),
    )
    if abs(corrected_count - source_count) > allowed_drift:
        raise InvalidCorrectionResponseError(
            "Automated correction changed editable token count beyond the conservative safety limit"
        )


def _require_numeric_literals_unchanged(
    request: CorrectionRequest, response: CorrectionResponse
) -> None:
    """Prevent automated correction from silently changing recognized numeric values."""

    source_text = " ".join(token.text for token in request.editable_tokens)
    source_numbers = tuple(_NUMERIC_LITERAL.findall(source_text))
    corrected_numbers = tuple(_NUMERIC_LITERAL.findall(response.corrected_text))
    if corrected_numbers != source_numbers:
        raise InvalidCorrectionResponseError(
            "Automated correction changed a recognized numeric literal"
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
        if not changed_speakers:
            adjacent_speakers = {
                request.editable_tokens[index].speaker_id
                for index in (change.start_index - 1, change.start_index)
                if 0 <= index < len(request.editable_tokens)
            }
            if len(adjacent_speakers) != 1:
                raise InvalidCorrectionResponseError(
                    "Correction response insertion is at an ambiguous speaker boundary"
                )
            changed_speakers = adjacent_speakers
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
