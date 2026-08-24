"""Runtime resolution of raw or revised transcript text onto canonical timing."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ewp_transcripts.domain.canonical import (
    CanonicalResult,
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWord,
    TimedEventKind,
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
    overlap: bool
    active_speaker_ids: tuple[str, ...]
    kind: TimedEventKind = "speech"


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
    context_by_word_id = {
        word.word_id: (segment.overlap, segment.active_speaker_ids, segment.kind)
        for segment in base.transcript.segments
        for word in segment.words
    }
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
                    overlap=context_by_word_id[word.word_id][0],
                    active_speaker_ids=tuple(sorted(context_by_word_id[word.word_id][1])),
                    kind=context_by_word_id[word.word_id][2],
                )
                for word in canonical_words
            ),
        )
    if base_path is None:
        raise ValueError("base_path is required when resolving a revision")
    validate_revision_base(revision, base, base_sha256=sha256_file(base_path))
    by_id = {word.word_id: word for word in canonical_words}
    insertion_timings = _resolve_insertion_timings(revision, by_id)
    tokens: list[EffectiveToken] = []
    for token_index, token in enumerate(revision.transcript.tokens):
        if token.source_word_ids:
            mapped = tuple(by_id[word_id] for word_id in token.source_word_ids)
            start_ms, end_ms = mapped[0].start_ms, mapped[-1].end_ms
            timing_source = "canonical_mapping"
            contexts = tuple(context_by_word_id[word_id] for word_id in token.source_word_ids)
        else:
            assert token.insertion_anchor is not None
            anchor = token.insertion_anchor
            start_ms, end_ms, timing_source = insertion_timings[token_index]
            neighbor_ids = tuple(
                word_id
                for word_id in (anchor.after_word_id, anchor.before_word_id)
                if word_id is not None
            )
            contexts = tuple(context_by_word_id[word_id] for word_id in neighbor_ids)
        active_speaker_ids = tuple(
            sorted(
                {
                    token.speaker_id,
                    *(
                        speaker_id
                        for context_overlap, active_speakers, _kind in contexts
                        if context_overlap
                        for speaker_id in active_speakers
                    ),
                }
            )
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
                overlap=any(overlap for overlap, _speakers, _kind in contexts),
                kind=_resolved_kind(contexts),
                active_speaker_ids=active_speaker_ids,
            )
        )
    # Base validation guarantees mapped order. Insertion anchors retain textual order;
    # normalize tied/adjacent display positions without inventing new timestamps.
    return EffectiveTranscript(
        language=revision.transcript.language,
        tokens=_mark_cross_speaker_timing_overlaps(tuple(tokens)),
        revision_number=revision.revision_number,
    )


def effective_canonical_result(
    base: CanonicalResult,
    effective: EffectiveTranscript,
) -> CanonicalResult:
    """Project runtime tokens into the stable canonical interfaces used by exporters."""

    groups: list[list[EffectiveToken]] = []
    for token in effective.tokens:
        if not groups or _effective_group_key(groups[-1][-1]) != _effective_group_key(token):
            groups.append([])
        groups[-1].append(token)
    ordered_groups = sorted(
        enumerate(groups),
        key=lambda item: (
            min(token.start_ms for token in item[1]),
            max(token.end_ms for token in item[1]),
            item[0],
        ),
    )
    segments = tuple(
        CanonicalSegment(
            segment_id=f"effective_{index:06d}",
            start_ms=min(token.start_ms for token in group),
            end_ms=max(token.end_ms for token in group),
            text=" ".join(token.text for token in group),
            kind=group[0].kind,
            speaker_id=group[0].speaker_id,
            overlap=group[0].overlap,
            active_speaker_ids=group[0].active_speaker_ids,
            source_ids=(),
            confidence=None,
            words=_projected_words(group),
        )
        for index, (_, group) in enumerate(ordered_groups, start=1)
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


def _effective_group_key(
    token: EffectiveToken,
) -> tuple[str, bool, tuple[str, ...], TimedEventKind]:
    return token.speaker_id, token.overlap, token.active_speaker_ids, token.kind


def _resolved_kind(
    contexts: tuple[tuple[bool, tuple[str, ...], TimedEventKind], ...],
) -> TimedEventKind:
    kinds = {kind for _overlap, _speakers, kind in contexts}
    if len(kinds) != 1:
        raise ValueError("Revision token cannot combine canonical segments of different kinds")
    return next(iter(kinds))


def _mark_cross_speaker_timing_overlaps(
    tokens: tuple[EffectiveToken, ...],
) -> tuple[EffectiveToken, ...]:
    """Preserve valid concurrent speech after corrected speaker-turn reconstruction."""

    overlap_speakers: list[set[str]] = [set(token.active_speaker_ids) for token in tokens]
    active: list[int] = []
    ordered_indices = sorted(
        range(len(tokens)),
        key=lambda index: (tokens[index].start_ms, tokens[index].end_ms, index),
    )
    for index in ordered_indices:
        token = tokens[index]
        active = [other for other in active if tokens[other].end_ms > token.start_ms]
        for other in active:
            previous = tokens[other]
            if (
                previous.speaker_id != token.speaker_id
                and token.start_ms < previous.end_ms
                and previous.start_ms < token.end_ms
            ):
                overlap_speakers[index].add(previous.speaker_id)
                overlap_speakers[other].add(token.speaker_id)
        active.append(index)

    return tuple(
        replace(
            token,
            overlap=token.overlap or len(overlap_speakers[index]) > 1,
            active_speaker_ids=tuple(sorted(overlap_speakers[index])),
        )
        for index, token in enumerate(tokens)
    )


def _resolve_insertion_timings(
    revision: TranscriptRevision,
    canonical_words: dict[str, CanonicalWord],
) -> dict[int, tuple[int, int, str]]:
    """Spread consecutive inserted tokens across a real gap when both bounds exist."""

    resolved: dict[int, tuple[int, int, str]] = {}
    tokens = revision.transcript.tokens
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.source_word_ids:
            index += 1
            continue
        assert token.insertion_anchor is not None
        end = index + 1
        while (
            end < len(tokens)
            and not tokens[end].source_word_ids
            and tokens[end].insertion_anchor == token.insertion_anchor
        ):
            end += 1
        anchor = token.insertion_anchor
        previous = (
            canonical_words[anchor.after_word_id] if anchor.after_word_id is not None else None
        )
        following = (
            canonical_words[anchor.before_word_id] if anchor.before_word_id is not None else None
        )
        count = end - index
        if previous is not None and following is not None and following.start_ms > previous.end_ms:
            gap_start = previous.end_ms
            gap_ms = following.start_ms - gap_start
            for offset, token_index in enumerate(range(index, end)):
                start_ms = gap_start + gap_ms * offset // count
                end_ms = gap_start + gap_ms * (offset + 1) // count
                resolved[token_index] = (start_ms, end_ms, "interpolated_gap")
        else:
            neighbor = following or previous
            assert neighbor is not None
            timing_source = "following_word" if following is not None else "previous_word"
            for token_index in range(index, end):
                resolved[token_index] = (neighbor.start_ms, neighbor.end_ms, timing_source)
        index = end
    return resolved
