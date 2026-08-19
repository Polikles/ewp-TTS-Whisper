"""Plain-text transcript rendering from the canonical result model."""

from __future__ import annotations

import re

from ewp_transcripts.domain.canonical import CanonicalResult, CanonicalSegment

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_NON_BREAKING_ABBREVIATIONS = frozenset(
    {
        "dr.",
        "etc.",
        "inż.",
        "itd.",
        "itp.",
        "m.in.",
        "mgr.",
        "mr.",
        "mrs.",
        "np.",
        "prof.",
        "st.",
        "tj.",
        "tzn.",
        "tzw.",
        "tys.",
        "vs.",
    }
)
_NON_BREAKING_TOKEN_SUFFIXES = (".com", ".edu", ".pl")


def split_sentences(text: str) -> tuple[str, ...]:
    """Split canonical text without changing its words or punctuation."""

    normalized = " ".join(text.split())
    if not normalized:
        return ()
    pieces = _SENTENCE_BOUNDARY.split(normalized)
    sentences: list[str] = []
    pending = pieces[0]
    for piece in pieces[1:]:
        final_token = pending.rsplit(maxsplit=1)[-1].casefold()
        if _is_non_breaking_token(final_token):
            pending = f"{pending} {piece}"
        else:
            sentences.append(pending)
            pending = piece
    sentences.append(pending)
    return tuple(sentences)


def render_transcript(result: CanonicalResult) -> str:
    """Render UTF-8-ready TXT with one sentence per line and speaker blocks."""

    labels = {speaker.speaker_id: speaker.speaker_label for speaker in result.speakers}
    show_labels = len(result.speakers) > 1
    blocks: list[str] = []
    current_speaker: str | None | object = object()
    current_lines: list[str] = []

    for segment in result.transcript.segments:
        speaker_id = _effective_speaker(segment)
        sentences = split_sentences(segment.text)
        if not sentences:
            continue
        if speaker_id != current_speaker:
            if current_lines:
                blocks.append("\n".join(current_lines))
            current_lines = []
            current_speaker = speaker_id
            if show_labels:
                label = labels[speaker_id] if speaker_id is not None else "Unknown"
                current_lines.append(f"{label}:")
        current_lines.extend(sentences)

    if current_lines:
        blocks.append("\n".join(current_lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _effective_speaker(segment: CanonicalSegment) -> str | None:
    if segment.speaker_id is not None:
        return segment.speaker_id
    if len(segment.active_speaker_ids) == 1:
        return segment.active_speaker_ids[0]
    return None


def _looks_like_initial(token: str) -> bool:
    return len(token) == 2 and token[0].isalpha() and token[1] == "."


def _is_non_breaking_token(token: str) -> bool:
    return (
        token in _NON_BREAKING_ABBREVIATIONS
        or token.endswith(_NON_BREAKING_TOKEN_SUFFIXES)
        or _looks_like_initial(token)
    )
