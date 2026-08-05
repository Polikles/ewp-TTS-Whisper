"""Subtitle cue construction and SRT/WebVTT serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ewp_transcripts.config import SubtitlesConfig
from ewp_transcripts.domain.canonical import CanonicalResult, CanonicalSegment, CanonicalWord


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    """One validated subtitle cue on the canonical millisecond timeline."""

    start_ms: int
    end_ms: int
    lines: tuple[str, ...]
    speaker_id: str | None
    overlap: bool = False


@dataclass(frozen=True, slots=True)
class _CueDraft:
    """Unlabelled cue candidate awaiting global timeline ordering."""

    start_ms: int
    end_ms: int
    text: str
    speaker_id: str | None
    overlap: bool
    sequence: int
    words: tuple[CanonicalWord, ...] = ()


def build_subtitle_cues(
    result: CanonicalResult, config: SubtitlesConfig | None = None
) -> tuple[SubtitleCue, ...]:
    """Build bounded cues without reading media or invoking inference libraries."""

    settings = config or SubtitlesConfig()
    labels = {speaker.speaker_id: speaker.speaker_label for speaker in result.speakers}
    multiple_speakers = len(result.speakers) > 1
    drafts: list[_CueDraft] = []

    for segment_index, segment in enumerate(result.transcript.segments):
        speaker_id = _effective_speaker(segment)
        label = labels[speaker_id] if speaker_id is not None else "Unknown"
        capacity_prefix = (
            f"{label}: " if multiple_speakers and settings.speaker_labels != "never" else ""
        )
        chunks = _segment_chunks(
            segment,
            settings,
            first_prefix=capacity_prefix,
            repeated_prefix=capacity_prefix,
        )
        for index, (start_ms, end_ms, text, words) in enumerate(chunks):
            drafts.append(
                _CueDraft(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                    speaker_id=speaker_id,
                    overlap=segment.overlap,
                    sequence=segment_index * 1_000_000 + index,
                    words=words,
                )
            )
    drafts.sort(key=lambda cue: (cue.start_ms, cue.end_ms, cue.sequence))
    drafts = _merge_adjacent_drafts(
        drafts,
        settings,
        labels=labels,
        multiple_speakers=multiple_speakers,
    )
    drafts = _rebalance_adjacent_drafts(
        drafts,
        settings,
        labels=labels,
        multiple_speakers=multiple_speakers,
    )

    cues: list[SubtitleCue] = []
    previous_speaker: str | None | object = object()
    for draft in drafts:
        text = draft.text
        if _show_speaker_label(
            settings.speaker_labels,
            multiple_speakers=multiple_speakers,
            speaker_id=draft.speaker_id,
            previous_speaker=previous_speaker,
            first_chunk=True,
        ):
            label = labels[draft.speaker_id] if draft.speaker_id is not None else "Unknown"
            text = f"{label}: {text}"
        cues.append(
            SubtitleCue(
                start_ms=draft.start_ms,
                end_ms=draft.end_ms,
                lines=wrap_subtitle_text(
                    text,
                    max_lines=settings.max_lines,
                    max_chars_per_line=settings.max_chars_per_line,
                ),
                speaker_id=draft.speaker_id,
                overlap=draft.overlap,
            )
        )
        previous_speaker = draft.speaker_id
    return _extend_short_cues(tuple(cues), settings)


def _merge_adjacent_drafts(
    drafts: list[_CueDraft],
    settings: SubtitlesConfig,
    *,
    labels: dict[str, str],
    multiple_speakers: bool,
) -> list[_CueDraft]:
    """Merge nearby same-speaker fragments into readable bounded cues."""

    merged: list[_CueDraft] = []
    for draft in drafts:
        if not merged:
            merged.append(draft)
            continue
        previous = merged[-1]
        gap_ms = draft.start_ms - previous.end_ms
        text = f"{previous.text} {draft.text}".strip()
        label = labels[previous.speaker_id] if previous.speaker_id is not None else "Unknown"
        prefix = f"{label}: " if multiple_speakers and settings.speaker_labels != "never" else ""
        duration_ms = draft.end_ms - previous.start_ms
        chars_per_second = len(text) * 1000 / max(duration_ms, 1)
        can_merge = (
            previous.speaker_id == draft.speaker_id
            and not previous.overlap
            and not draft.overlap
            and 0 <= gap_ms <= settings.max_merge_gap_ms
            and duration_ms <= settings.max_duration_ms
            and chars_per_second <= settings.max_chars_per_second
            and _fits_line_limits(f"{prefix}{text}", settings)
        )
        if can_merge:
            merged[-1] = _CueDraft(
                start_ms=previous.start_ms,
                end_ms=draft.end_ms,
                text=text,
                speaker_id=previous.speaker_id,
                overlap=False,
                sequence=previous.sequence,
                words=((*previous.words, *draft.words) if previous.words and draft.words else ()),
            )
        else:
            merged.append(draft)
    return merged


def _rebalance_adjacent_drafts(
    drafts: list[_CueDraft],
    settings: SubtitlesConfig,
    *,
    labels: dict[str, str],
    multiple_speakers: bool,
) -> list[_CueDraft]:
    """Move continuous sentence boundaries when a complete merge cannot fit."""

    balanced = list(drafts)
    for index in range(len(balanced) - 1):
        previous = balanced[index]
        following = balanced[index + 1]
        gap_ms = following.start_ms - previous.end_ms
        if (
            previous.speaker_id != following.speaker_id
            or previous.overlap
            or following.overlap
            or not previous.words
            or not following.words
            or not 0 <= gap_ms <= settings.max_merge_gap_ms
            or previous.text.rstrip().endswith((".", "!", "?"))
        ):
            continue
        label = labels[previous.speaker_id] if previous.speaker_id is not None else "Unknown"
        prefix = f"{label}: " if multiple_speakers and settings.speaker_labels != "never" else ""

        while (
            len(previous.words) < settings.min_words_per_cue
            and len(following.words) > settings.min_words_per_cue
        ):
            previous_candidate = _draft_with_words(previous, (*previous.words, following.words[0]))
            following_candidate = _draft_with_words(following, following.words[1:])
            if not _draft_fits(previous_candidate, settings, prefix=prefix) or not _draft_fits(
                following_candidate, settings, prefix=prefix
            ):
                break
            previous, following = previous_candidate, following_candidate

        while (
            len(following.words) < settings.min_words_per_cue
            and len(previous.words) > settings.min_words_per_cue
        ):
            previous_candidate = _draft_with_words(previous, previous.words[:-1])
            following_candidate = _draft_with_words(
                following, (previous.words[-1], *following.words)
            )
            if not _draft_fits(previous_candidate, settings, prefix=prefix) or not _draft_fits(
                following_candidate, settings, prefix=prefix
            ):
                break
            previous, following = previous_candidate, following_candidate

        balanced[index] = previous
        balanced[index + 1] = following
    return balanced


def _draft_with_words(draft: _CueDraft, words: tuple[CanonicalWord, ...]) -> _CueDraft:
    return _CueDraft(
        start_ms=words[0].start_ms,
        end_ms=words[-1].end_ms,
        text=_word_text(list(words)),
        speaker_id=draft.speaker_id,
        overlap=draft.overlap,
        sequence=draft.sequence,
        words=words,
    )


def _draft_fits(draft: _CueDraft, settings: SubtitlesConfig, *, prefix: str) -> bool:
    duration_ms = draft.end_ms - draft.start_ms
    chars_per_second = len(draft.text) * 1000 / max(duration_ms, 1)
    return (
        duration_ms <= settings.max_duration_ms
        and chars_per_second <= settings.max_chars_per_second
        and _fits_line_limits(f"{prefix}{draft.text}", settings)
    )


def render_srt(cues: tuple[SubtitleCue, ...]) -> str:
    """Serialize cues as SubRip with sequential numbering."""

    _validate_cues(cues)
    blocks = [
        f"{index}\n{_timestamp(cue.start_ms, separator=',')} --> "
        f"{_timestamp(cue.end_ms, separator=',')}\n" + "\n".join(cue.lines)
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def render_vtt(cues: tuple[SubtitleCue, ...]) -> str:
    """Serialize cues as WebVTT."""

    _validate_cues(cues)
    blocks = [
        f"{_timestamp(cue.start_ms, separator='.')} --> "
        f"{_timestamp(cue.end_ms, separator='.')}\n" + "\n".join(cue.lines)
        for cue in cues
    ]
    body = "\n\n".join(blocks)
    return "WEBVTT\n\n" + body + ("\n" if body else "")


def wrap_subtitle_text(text: str, *, max_lines: int, max_chars_per_line: int) -> tuple[str, ...]:
    """Wrap at word boundaries while enforcing hard line and line-count limits."""

    if max_lines < 1 or max_chars_per_line < 1:
        raise ValueError("subtitle line limits must be positive")
    words = text.split()
    if not words:
        raise ValueError("subtitle cue text must not be empty")
    if any(len(word) > max_chars_per_line for word in words):
        raise ValueError("a subtitle word exceeds max_chars_per_line")
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars_per_line:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if len(lines) > max_lines:
        raise ValueError("subtitle cue exceeds max_lines")
    return tuple(lines)


def _segment_chunks(
    segment: CanonicalSegment,
    settings: SubtitlesConfig,
    *,
    first_prefix: str,
    repeated_prefix: str,
) -> list[tuple[int, int, str, tuple[CanonicalWord, ...]]]:
    if not segment.words:
        return [(segment.start_ms, segment.end_ms, segment.text.strip(), ())]
    word_chunks: list[list[CanonicalWord]] = []
    current: list[CanonicalWord] = []
    for word in segment.words:
        candidate = [*current, word]
        text = _word_text(candidate)
        prefix = first_prefix if not word_chunks else repeated_prefix
        displayed_text = f"{prefix}{text}"
        duration_ms = candidate[-1].end_ms - candidate[0].start_ms
        chars_per_second = len(text) * 1000 / max(duration_ms, 1)
        exceeds = (
            not _fits_line_limits(displayed_text, settings)
            or duration_ms > settings.max_duration_ms
            or chars_per_second > settings.max_chars_per_second
        )
        if current and exceeds:
            word_chunks.append(current)
            current = [word]
        else:
            current = candidate
        if (
            current[-1].text.rstrip().endswith((".", "!", "?"))
            and len(_word_text(current)) >= settings.target_chars_per_line
        ):
            word_chunks.append(current)
            current = []
    if current:
        word_chunks.append(current)
    _rebalance_orphan_chunks(
        word_chunks,
        settings,
        first_prefix=first_prefix,
        repeated_prefix=repeated_prefix,
    )
    return [(*_word_chunk(words), tuple(words)) for words in word_chunks]


def _rebalance_orphan_chunks(
    chunks: list[list[CanonicalWord]],
    settings: SubtitlesConfig,
    *,
    first_prefix: str,
    repeated_prefix: str,
) -> None:
    """Avoid stranded sentence fragments while preserving hard cue limits."""

    if settings.min_words_per_cue <= 1:
        return

    # A short trailing fragment belongs to the preceding unfinished sentence. Move
    # its boundary left when both resulting cues remain valid.
    for index in range(1, len(chunks)):
        previous = chunks[index - 1]
        current = chunks[index]
        if _ends_sentence(previous):
            continue
        while (
            len(current) < settings.min_words_per_cue and len(previous) > settings.min_words_per_cue
        ):
            previous_candidate = previous[:-1]
            current_candidate = [previous[-1], *current]
            if not _word_chunk_fits(
                previous_candidate,
                settings,
                prefix=first_prefix if index == 1 else repeated_prefix,
            ) or not _word_chunk_fits(current_candidate, settings, prefix=repeated_prefix):
                break
            previous[:] = previous_candidate
            current[:] = current_candidate

    # A short leading fragment of an unfinished sentence can borrow from the following
    # cue. A punctuated short sentence remains independent.
    for index in range(len(chunks) - 1):
        current = chunks[index]
        following = chunks[index + 1]
        if _ends_sentence(current):
            continue
        while (
            len(current) < settings.min_words_per_cue
            and len(following) > settings.min_words_per_cue
        ):
            current_candidate = [*current, following[0]]
            following_candidate = following[1:]
            if not _word_chunk_fits(
                current_candidate,
                settings,
                prefix=first_prefix if index == 0 else repeated_prefix,
            ) or not _word_chunk_fits(following_candidate, settings, prefix=repeated_prefix):
                break
            current[:] = current_candidate
            following[:] = following_candidate


def _word_chunk_fits(words: list[CanonicalWord], settings: SubtitlesConfig, *, prefix: str) -> bool:
    if not words:
        return False
    text = _word_text(words)
    duration_ms = words[-1].end_ms - words[0].start_ms
    chars_per_second = len(text) * 1000 / max(duration_ms, 1)
    return (
        duration_ms <= settings.max_duration_ms
        and chars_per_second <= settings.max_chars_per_second
        and _fits_line_limits(f"{prefix}{text}", settings)
    )


def _ends_sentence(words: list[CanonicalWord]) -> bool:
    return bool(words and words[-1].text.rstrip().endswith((".", "!", "?")))


def _fits_line_limits(text: str, settings: SubtitlesConfig) -> bool:
    try:
        wrap_subtitle_text(
            text,
            max_lines=settings.max_lines,
            max_chars_per_line=settings.max_chars_per_line,
        )
    except ValueError:
        return False
    return True


def _word_chunk(words: list[CanonicalWord]) -> tuple[int, int, str]:
    return words[0].start_ms, words[-1].end_ms, _word_text(words)


def _word_text(words: list[CanonicalWord]) -> str:
    return " ".join(word.text.strip() for word in words if word.text.strip())


def _show_speaker_label(
    mode: Literal["on-change", "always", "never"],
    *,
    multiple_speakers: bool,
    speaker_id: str | None,
    previous_speaker: str | None | object,
    first_chunk: bool,
) -> bool:
    if not multiple_speakers or mode == "never":
        return False
    if mode == "always":
        return True
    return first_chunk and speaker_id != previous_speaker


def _effective_speaker(segment: CanonicalSegment) -> str | None:
    if segment.speaker_id is not None:
        return segment.speaker_id
    if len(segment.active_speaker_ids) == 1:
        return segment.active_speaker_ids[0]
    return None


def _extend_short_cues(
    cues: tuple[SubtitleCue, ...], settings: SubtitlesConfig
) -> tuple[SubtitleCue, ...]:
    extended: list[SubtitleCue] = []
    for index, cue in enumerate(cues):
        duration = cue.end_ms - cue.start_ms
        if duration >= settings.min_duration_ms:
            extended.append(cue)
            continue
        desired_end = cue.start_ms + settings.min_duration_ms
        maximum_end = cue.end_ms + 300
        if index + 1 < len(cues) and not (cue.overlap or cues[index + 1].overlap):
            maximum_end = min(maximum_end, cues[index + 1].start_ms - settings.min_gap_ms)
        end_ms = max(cue.end_ms, min(desired_end, maximum_end))
        extended.append(
            SubtitleCue(
                start_ms=cue.start_ms,
                end_ms=end_ms,
                lines=cue.lines,
                speaker_id=cue.speaker_id,
                overlap=cue.overlap,
            )
        )
    return tuple(extended)


def _timestamp(milliseconds: int, *, separator: Literal[",", "."]) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"


def _validate_cues(cues: tuple[SubtitleCue, ...]) -> None:
    for index, cue in enumerate(cues):
        if cue.start_ms < 0 or cue.end_ms < cue.start_ms:
            raise ValueError("subtitle cue timestamps are invalid")
        if not cue.lines or any(not line.strip() for line in cue.lines):
            raise ValueError("subtitle cues must contain non-empty lines")
        if index == 0:
            continue
        previous = cues[index - 1]
        if cue.start_ms < previous.start_ms:
            raise ValueError("subtitle cues must be sorted chronologically")
        if cue.start_ms < previous.end_ms and not (cue.overlap or previous.overlap):
            raise ValueError("ordinary subtitle cues must not overlap")
