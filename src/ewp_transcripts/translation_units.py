"""Deterministic speaker-safe sentence units for translation preparation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript
from ewp_transcripts.exporters.transcript import is_non_breaking_sentence_token


@dataclass(frozen=True, slots=True)
class TranslationSourceUnit:
    unit_id: str
    speaker_id: str
    source_token_ids: tuple[str, ...]
    source_text: str
    source_text_sha256: str
    start_ms: int
    end_ms: int


def plan_translation_units(transcript: EffectiveTranscript) -> tuple[TranslationSourceUnit, ...]:
    """Cover effective tokens once with sentence-oriented units that never cross speakers."""

    if not transcript.tokens:
        return ()
    groups: list[list[EffectiveToken]] = []
    current: list[EffectiveToken] = []
    for token in transcript.tokens:
        if current and token.speaker_id != current[-1].speaker_id:
            groups.append(current)
            current = []
        current.append(token)
        if _ends_sentence(token.text):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return tuple(_unit(index, tokens) for index, tokens in enumerate(groups, start=1))


def _ends_sentence(text: str) -> bool:
    token = text.strip().casefold()
    terminal = token.rstrip('"”’»')
    return terminal.endswith((".", "!", "?")) and not is_non_breaking_sentence_token(terminal)


def _unit(index: int, tokens: list[EffectiveToken]) -> TranslationSourceUnit:
    text = " ".join(token.text for token in tokens)
    return TranslationSourceUnit(
        unit_id=f"tu_{index:06d}",
        speaker_id=tokens[0].speaker_id,
        source_token_ids=tuple(token.token_id for token in tokens),
        source_text=text,
        source_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        start_ms=min(token.start_ms for token in tokens),
        end_ms=max(token.end_ms for token in tokens),
    )
