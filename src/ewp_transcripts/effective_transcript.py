"""Runtime resolution of raw or revised transcript text onto canonical timing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ewp_transcripts.domain.canonical import (
    CanonicalResult,
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWord,
)
from ewp_transcripts.domain.revision import (
    TranscriptRevision,
    sha256_file,
    validate_revision_base,
)


@dataclass(frozen=True, slots=True)
class EffectiveToken:
    """Corrected text with resolved canonical timing provenance."""

    token_id: str
    text: str
    speaker_id: str
    source_word_ids: tuple[str, ...]
    start_ms: int
    end_ms: int
    timing_source: str


@dataclass(frozen=True, slots=True)
class EffectiveTranscript:
    """One runtime transcript selected for all derived exporters."""

    language: str
    tokens: tuple[EffectiveToken, ...]
    revision_number: int | None = None


def resolve_effective_transcript(
    base: CanonicalResult,
    revision: TranscriptRevision | None = None,
    *,
    base_path: Path | None = None,
) -> EffectiveTranscript:
    """Resolve raw words or one compatible full revision into timed runtime tokens."""

    canonical_words = tuple(word for segment in base.transcript.segments for word in segment.words)
    if revision is None:
        return EffectiveTranscript(
            language=base.transcript.language,
            tokens=tuple(
                EffectiveToken(
                    token_id=word.word_id,
                    text=word.text,
                    speaker_id=word.speaker_id or _segment_speaker(base, word.word_id),
                    source_word_ids=(word.word_id,),
                    start_ms=word.start_ms,
                    end_ms=word.end_ms,
                    timing_source=word.timestamp_source,
                )
                for word in canonical_words
            ),
        )
    if base_path is None:
        raise ValueError("base_path is required when resolving a revision")
    validate_revision_base(revision, base, base_sha256=sha256_file(base_path))
    by_id = {word.word_id: word for word in canonical_words}
    tokens: list[EffectiveToken] = []
    for token in revision.transcript.tokens:
        if token.source_word_ids:
            mapped = tuple(by_id[word_id] for word_id in token.source_word_ids)
            start_ms, end_ms = mapped[0].start_ms, mapped[-1].end_ms
            timing_source = "canonical_mapping"
        else:
            assert token.insertion_anchor is not None
            anchor = token.insertion_anchor
            neighbor_id = anchor.before_word_id or anchor.after_word_id
            assert neighbor_id is not None
            neighbor = by_id[neighbor_id]
            start_ms, end_ms = neighbor.start_ms, neighbor.end_ms
            timing_source = (
                "following_word" if anchor.before_word_id is not None else "previous_word"
            )
        tokens.append(
            EffectiveToken(
                token_id=token.token_id,
                text=token.text,
                speaker_id=token.speaker_id,
                source_word_ids=token.source_word_ids,
                start_ms=start_ms,
                end_ms=end_ms,
                timing_source=timing_source,
            )
        )
    # Base validation guarantees mapped order. Insertion anchors retain textual order;
    # normalize tied/adjacent display positions without inventing new timestamps.
    return EffectiveTranscript(
        language=revision.transcript.language,
        tokens=tuple(tokens),
        revision_number=revision.revision_number,
    )


def effective_canonical_result(
    base: CanonicalResult,
    effective: EffectiveTranscript,
) -> CanonicalResult:
    """Project runtime tokens into the stable canonical interfaces used by exporters."""

    groups: list[list[EffectiveToken]] = []
    for token in effective.tokens:
        if not groups or groups[-1][-1].speaker_id != token.speaker_id:
            groups.append([])
        groups[-1].append(token)
    segments = tuple(
        CanonicalSegment(
            segment_id=f"effective_{index:06d}",
            start_ms=min(token.start_ms for token in group),
            end_ms=max(token.end_ms for token in group),
            text=" ".join(token.text for token in group),
            speaker_id=group[0].speaker_id,
            overlap=False,
            active_speaker_ids=(group[0].speaker_id,),
            source_ids=(),
            confidence=None,
            words=_projected_words(group),
        )
        for index, group in enumerate(groups, start=1)
    )
    transcript = CanonicalTranscript(language=effective.language, segments=segments)
    return base.model_copy(update={"transcript": transcript})


def _projected_words(group: list[EffectiveToken]) -> tuple[CanonicalWord, ...]:
    """Keep tokens sharing one inherited timing group together for subtitle planning."""

    timing_groups: list[list[EffectiveToken]] = []
    for token in group:
        if (
            not timing_groups
            or timing_groups[-1][-1].start_ms != token.start_ms
            or timing_groups[-1][-1].end_ms != token.end_ms
        ):
            timing_groups.append([])
        timing_groups[-1].append(token)
    return tuple(
        CanonicalWord(
            word_id=items[0].token_id,
            text=" ".join(item.text for item in items),
            start_ms=items[0].start_ms,
            end_ms=items[0].end_ms,
            timestamp_source=(
                "aligned"
                if all(item.timing_source == "canonical_mapping" for item in items)
                else "segment_fallback"
            ),
            speaker_id=items[0].speaker_id,
            confidence=None,
        )
        for items in timing_groups
    )


def _segment_speaker(base: CanonicalResult, word_id: str) -> str:
    for segment in base.transcript.segments:
        if any(word.word_id == word_id for word in segment.words):
            speaker = segment.speaker_id
            if speaker is None and len(segment.active_speaker_ids) == 1:
                speaker = segment.active_speaker_ids[0]
            if speaker is not None:
                return speaker
    raise ValueError(f"Canonical word has no effective speaker: {word_id}")
