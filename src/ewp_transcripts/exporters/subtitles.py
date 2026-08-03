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


def build_subtitle_cues(
    result: CanonicalResult, config: SubtitlesConfig | None = None
) -> tuple[SubtitleCue, ...]:
    """Build bounded cues without reading media or invoking inference libraries."""

    settings = config or SubtitlesConfig()
    labels = {speaker.speaker_id: speaker.speaker_label for speaker in result.speakers}
    multiple_speakers = len(result.speakers) > 1
    cues: list[SubtitleCue] = []
    previous_speaker: str | None | object = object()

    for segment in result.transcript.segments:
        speaker_id = _effective_speaker(segment)
        first_show_label = _show_speaker_label(
            settings.speaker_labels,
            multiple_speakers=multiple_speakers,
            speaker_id=speaker_id,
            previous_speaker=previous_speaker,
            first_chunk=True,
        )
        label = labels[speaker_id] if speaker_id is not None else "Unknown"
        first_prefix = f"{label}: " if first_show_label else ""
        repeated_prefix = f"{label}: " if settings.speaker_labels == "always" else ""
        chunks = _segment_chunks(
            segment,
            settings,
            first_prefix=first_prefix,
            repeated_prefix=repeated_prefix,
        )
        for index, (start_ms, end_ms, text) in enumerate(chunks):
            show_label = _show_speaker_label(
                settings.speaker_labels,
                multiple_speakers=multiple_speakers,
                speaker_id=speaker_id,
                previous_speaker=previous_speaker,
                first_chunk=index == 0,
            )
            if show_label:
                label = labels[speaker_id] if speaker_id is not None else "Unknown"
                text = f"{label}: {text}"
            lines = wrap_subtitle_text(
                text,
                max_lines=settings.max_lines,
                max_chars_per_line=settings.max_chars_per_line,
            )
            cues.append(
                SubtitleCue(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    lines=lines,
                    speaker_id=speaker_id,
                    overlap=segment.overlap,
                )
            )
            previous_speaker = speaker_id
    return _extend_short_cues(tuple(cues), settings)


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
) -> list[tuple[int, int, str]]:
    if not segment.words:
        return [(segment.start_ms, segment.end_ms, segment.text.strip())]
    chunks: list[tuple[int, int, str]] = []
    current: list[CanonicalWord] = []
    for word in segment.words:
        candidate = [*current, word]
        text = _word_text(candidate)
        prefix = first_prefix if not chunks else repeated_prefix
        displayed_text = f"{prefix}{text}"
        duration_ms = candidate[-1].end_ms - candidate[0].start_ms
        chars_per_second = len(text) * 1000 / max(duration_ms, 1)
        exceeds = (
            not _fits_line_limits(displayed_text, settings)
            or duration_ms > settings.max_duration_ms
            or chars_per_second > settings.max_chars_per_second
        )
        if current and exceeds:
            chunks.append(_word_chunk(current))
            current = [word]
        else:
            current = candidate
        if (
            current[-1].text.rstrip().endswith((".", "!", "?"))
            and len(_word_text(current)) >= settings.target_chars_per_line
        ):
            chunks.append(_word_chunk(current))
            current = []
    if current:
        chunks.append(_word_chunk(current))
    return chunks


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
