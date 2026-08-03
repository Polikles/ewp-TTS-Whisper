"""Tests for subtitle cue construction and serialization."""

from pathlib import Path

import pytest

from ewp_transcripts.config import SubtitlesConfig
from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.exporters.subtitles import (
    SubtitleCue,
    build_subtitle_cues,
    render_srt,
    render_vtt,
    wrap_subtitle_text,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"


def test_builds_bounded_cues_with_labels_on_speaker_changes() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    cues = build_subtitle_cues(result)

    assert len(cues) == 2
    assert cues[0] == SubtitleCue(
        start_ms=1240,
        end_ms=3900,
        lines=("jan: Welcome to another episode.",),
        speaker_id="speaker_001",
    )
    assert cues[1] == SubtitleCue(
        start_ms=4320,
        end_ms=6320,
        lines=("anna: Today we discuss transcription.",),
        speaker_id="speaker_002",
    )
    assert all(len(cue.lines) <= 2 for cue in cues)
    assert all(len(line) <= 46 for cue in cues for line in cue.lines)


def test_srt_and_vtt_have_valid_headers_timestamps_and_spacing() -> None:
    cues = (
        SubtitleCue(1240, 3900, ("First cue.",), "speaker_001"),
        SubtitleCue(4320, 6320, ("Second cue.",), "speaker_002"),
    )

    assert render_srt(cues) == (
        "1\n00:00:01,240 --> 00:00:03,900\nFirst cue.\n\n"
        "2\n00:00:04,320 --> 00:00:06,320\nSecond cue.\n"
    )
    assert render_vtt(cues) == (
        "WEBVTT\n\n"
        "00:00:01.240 --> 00:00:03.900\nFirst cue.\n\n"
        "00:00:04.320 --> 00:00:06.320\nSecond cue.\n"
    )


def test_never_mode_suppresses_speaker_labels() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    config = SubtitlesConfig(speaker_labels="never")

    cues = build_subtitle_cues(result, config)

    assert cues[0].lines == ("Welcome to another episode.",)
    assert cues[1].lines == ("Today we discuss transcription.",)


def test_wraps_only_at_word_boundaries_and_rejects_impossible_text() -> None:
    assert wrap_subtitle_text("one two three four", max_lines=2, max_chars_per_line=10) == (
        "one two",
        "three four",
    )
    with pytest.raises(ValueError, match="word exceeds"):
        wrap_subtitle_text("extraordinary", max_lines=2, max_chars_per_line=5)
    with pytest.raises(ValueError, match="exceeds max_lines"):
        wrap_subtitle_text("one two three", max_lines=1, max_chars_per_line=5)


def test_short_cue_extension_stops_before_next_cue() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first = result.transcript.segments[0]
    short_word = first.words[0].model_copy(update={"end_ms": 1400})
    short = first.model_copy(update={"end_ms": 1400, "text": "Welcome", "words": (short_word,)})
    following = result.transcript.segments[1].model_copy(update={"start_ms": 1600, "end_ms": 2500})
    following_words = tuple(
        word.model_copy(update={"start_ms": 1600 + index * 100, "end_ms": 1680 + index * 100})
        for index, word in enumerate(following.words)
    )
    following = following.model_copy(update={"words": following_words})
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (short, following)})}
    )

    cues = build_subtitle_cues(result)

    assert cues[0].end_ms == 1520
    assert cues[1].start_ms == 1600


def test_chunking_uses_real_wrapping_limit_not_only_total_capacity() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    original = result.transcript.segments[0]
    texts = ("a" * 30, "b" * 30, "c" * 30)
    words = tuple(
        original.words[0].model_copy(
            update={
                "word_id": f"word_test_{index}",
                "text": text,
                "start_ms": 1000 + index * 2000,
                "end_ms": 3000 + index * 2000,
            }
        )
        for index, text in enumerate(texts)
    )
    segment = original.model_copy(
        update={
            "start_ms": 1000,
            "end_ms": 7000,
            "text": " ".join(texts),
            "words": words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (segment,)})}
    )

    cues = build_subtitle_cues(result)

    assert len(cues) == 2
    assert tuple(line for cue in cues for line in cue.lines) == (
        f"jan: {texts[0]}",
        texts[1],
        texts[2],
    )
    assert all(len(cue.lines) <= 2 for cue in cues)
    assert all(len(line) <= 46 for cue in cues for line in cue.lines)


def test_serializers_reject_accidental_overlap_but_allow_explicit_overlap() -> None:
    ordinary = (
        SubtitleCue(1000, 2000, ("First",), "speaker_001"),
        SubtitleCue(1900, 2500, ("Second",), "speaker_002"),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        render_srt(ordinary)

    explicit = (
        ordinary[0],
        SubtitleCue(1900, 2500, ("Second",), "speaker_002", overlap=True),
    )
    assert "Second" in render_vtt(explicit)
