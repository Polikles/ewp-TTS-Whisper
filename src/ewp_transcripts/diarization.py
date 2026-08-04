"""Deterministic reconciliation of diarization turns with canonical word timing."""

from __future__ import annotations

from dataclasses import dataclass

from ewp_transcripts.domain.canonical import (
    CanonicalSegment,
    CanonicalTranscript,
    CanonicalWarning,
    CanonicalWord,
)
from ewp_transcripts.domain.enums import WarningCode
from ewp_transcripts.engines import DiarizationResult, DiarizationTurn


@dataclass(frozen=True, slots=True)
class ReconciledSpeaker:
    """Stable public speaker identity derived from one backend label."""

    backend_label: str
    speaker_id: str
    speaker_label: str
    first_seen_ms: int


@dataclass(frozen=True, slots=True)
class ReconciledDiarization:
    """Speaker-attributed transcript plus public identities and diagnostics."""

    transcript: CanonicalTranscript
    speakers: tuple[ReconciledSpeaker, ...]
    warnings: tuple[CanonicalWarning, ...]


def reconcile_diarization(
    transcript: CanonicalTranscript,
    diarization: DiarizationResult,
    *,
    source_id: str,
    use_exclusive_for_words: bool,
) -> ReconciledDiarization:
    """Assign speakers without hiding overlap or inventing uncertain attribution."""

    speakers = _speaker_map(diarization)
    by_backend = {speaker.backend_label: speaker for speaker in speakers}
    assignment_turns = (
        diarization.exclusive_turns
        if use_exclusive_for_words and diarization.exclusive_turns is not None
        else diarization.turns
    )
    missing_words = 0
    ambiguous_words = 0
    segments: list[CanonicalSegment] = []
    for segment in transcript.segments:
        words: list[CanonicalWord] = []
        for word in segment.words:
            backend_label, ambiguous = _assign_interval(
                word.start_ms,
                word.end_ms,
                assignment_turns,
            )
            if ambiguous:
                ambiguous_words += 1
            elif backend_label is None:
                missing_words += 1
            speaker_id = (
                by_backend[backend_label].speaker_id
                if backend_label is not None and backend_label in by_backend
                else None
            )
            words.append(word.model_copy(update={"speaker_id": speaker_id}))

        primary = _primary_speaker(tuple(words))
        active = _active_speakers(segment, diarization.turns, by_backend)
        if primary is not None and primary not in active:
            active = (*active, primary)
        segments.append(
            segment.model_copy(
                update={
                    "speaker_id": primary,
                    "overlap": len(active) > 1,
                    "active_speaker_ids": active,
                    "words": tuple(words),
                }
            )
        )

    warnings: list[CanonicalWarning] = []
    if missing_words:
        warnings.append(
            CanonicalWarning(
                code=WarningCode.SPEAKER_ASSIGNMENT_MISSING.value,
                severity="warning",
                message="Some timed words were not covered by a diarization turn.",
                stage="diarize",
                source_id=source_id,
                context={"affected_words": missing_words},
            )
        )
    if ambiguous_words:
        warnings.append(
            CanonicalWarning(
                code=WarningCode.SPEAKER_ASSIGNMENT_AMBIGUOUS.value,
                severity="warning",
                message="Some timed words matched multiple speakers equally.",
                stage="diarize",
                source_id=source_id,
                context={"affected_words": ambiguous_words},
            )
        )
    return ReconciledDiarization(
        transcript=transcript.model_copy(update={"segments": tuple(segments)}),
        speakers=speakers,
        warnings=tuple(warnings),
    )


def _speaker_map(diarization: DiarizationResult) -> tuple[ReconciledSpeaker, ...]:
    first_seen: dict[str, int] = {}
    turns = (*diarization.turns, *(diarization.exclusive_turns or ()))
    for turn in turns:
        first_seen[turn.speaker_label] = min(
            turn.start_ms,
            first_seen.get(turn.speaker_label, turn.start_ms),
        )
    ordered = sorted(first_seen.items(), key=lambda item: (item[1], item[0]))
    return tuple(
        ReconciledSpeaker(
            backend_label=backend_label,
            speaker_id=f"speaker_{index:03d}",
            speaker_label=f"Speaker{index}",
            first_seen_ms=start_ms,
        )
        for index, (backend_label, start_ms) in enumerate(ordered, start=1)
    )


def _assign_interval(
    start_ms: int,
    end_ms: int,
    turns: tuple[DiarizationTurn, ...],
) -> tuple[str | None, bool]:
    scores: dict[str, int] = {}
    for turn in turns:
        overlap = max(0, min(end_ms, turn.end_ms) - max(start_ms, turn.start_ms))
        if overlap:
            scores[turn.speaker_label] = scores.get(turn.speaker_label, 0) + overlap
    if not scores and start_ms == end_ms:
        for turn in turns:
            if turn.start_ms <= start_ms < turn.end_ms:
                scores[turn.speaker_label] = 1
    if not scores:
        return None, False
    best = max(scores.values())
    labels = sorted(label for label, score in scores.items() if score == best)
    if len(labels) != 1:
        return None, True
    return labels[0], False


def _primary_speaker(words: tuple[CanonicalWord, ...]) -> str | None:
    scores: dict[str, int] = {}
    for word in words:
        if word.speaker_id is None:
            continue
        scores[word.speaker_id] = scores.get(word.speaker_id, 0) + max(
            1, word.end_ms - word.start_ms
        )
    if not scores:
        return None
    best = max(scores.values())
    speakers = sorted(speaker for speaker, score in scores.items() if score == best)
    return speakers[0] if len(speakers) == 1 else None


def _active_speakers(
    segment: CanonicalSegment,
    turns: tuple[DiarizationTurn, ...],
    by_backend: dict[str, ReconciledSpeaker],
) -> tuple[str, ...]:
    active = {
        by_backend[turn.speaker_label].speaker_id
        for turn in turns
        if turn.speaker_label in by_backend
        and segment.start_ms < turn.end_ms
        and turn.start_ms < segment.end_ms
    }
    order = {speaker.speaker_id: index for index, speaker in enumerate(by_backend.values())}
    return tuple(sorted(active, key=lambda speaker_id: (order[speaker_id], speaker_id)))
