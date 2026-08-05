"""Tests for subtitle cue construction and serialization."""

from pathlib import Path

import pytest

from ewp_transcripts.config import SubtitlesConfig
from ewp_transcripts.domain.canonical import CanonicalWord, load_canonical_result
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


@pytest.mark.parametrize("connective", ["i", "na", "to"])
def test_wrap_avoids_polish_connective_at_end_of_visible_line(connective: str) -> None:
    lines = wrap_subtitle_text(
        f"To jest pierwsza część {connective} druga część zdania.",
        max_lines=2,
        max_chars_per_line=28,
    )

    assert lines[0].split()[-1] != connective


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


def test_nearby_same_speaker_fragments_merge_across_rhetorical_pause() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first, second = result.transcript.segments
    first_words = tuple(
        word.model_copy(
            update={
                "text": text,
                "start_ms": 1000 + index * 350,
                "end_ms": 1300 + index * 350,
                "speaker_id": "speaker_001",
            }
        )
        for index, (word, text) in enumerate(zip(first.words[:2], ("Może", "i"), strict=True))
    )
    first = first.model_copy(
        update={
            "start_ms": 1000,
            "end_ms": 1650,
            "text": "Może i",
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
            "words": first_words,
        }
    )
    second_words = tuple(
        word.model_copy(
            update={
                "text": text,
                "start_ms": 2450 + index * 250,
                "end_ms": 2650 + index * 250,
                "speaker_id": "speaker_001",
            }
        )
        for index, (word, text) in enumerate(
            zip(second.words[:3], ("nikt", "nie", "zauważy."), strict=True)
        )
    )
    second = second.model_copy(
        update={
            "start_ms": 2450,
            "end_ms": 3150,
            "text": "nikt nie zauważy.",
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
            "words": second_words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (first, second)})}
    )

    cues = build_subtitle_cues(result)

    assert cues == (
        SubtitleCue(
            start_ms=1000,
            end_ms=3150,
            lines=("jan: Może i nikt nie zauważy.",),
            speaker_id="speaker_001",
        ),
    )


def test_trailing_fragment_is_rebalanced_without_exceeding_limits() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    original = result.transcript.segments[0]
    words = tuple(
        original.words[0].model_copy(
            update={
                "word_id": f"word_balance_{index}",
                "text": "aa",
                "start_ms": 1000 + index * 500,
                "end_ms": 1400 + index * 500,
            }
        )
        for index in range(10)
    )
    segment = original.model_copy(
        update={
            "start_ms": words[0].start_ms,
            "end_ms": words[-1].end_ms,
            "text": " ".join(word.text for word in words),
            "words": words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (segment,)})}
    )
    config = SubtitlesConfig(
        max_lines=1,
        max_chars_per_line=20,
        max_chars_per_second=100,
        min_words_per_cue=4,
        speaker_labels="never",
    )

    cues = build_subtitle_cues(result, config)

    assert tuple(len(" ".join(cue.lines).split()) for cue in cues) == (6, 4)
    assert all(len(line) <= 20 for cue in cues for line in cue.lines)


def test_short_standalone_sentence_surrounded_by_silence_is_preserved() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first, second = result.transcript.segments
    first_words = tuple(
        word.model_copy(update={"text": text})
        for word, text in zip(first.words[:2], ("Tak", "jest."), strict=True)
    )
    first = first.model_copy(
        update={"text": "Tak jest.", "words": first_words, "end_ms": first_words[-1].end_ms}
    )
    second_words = tuple(
        word.model_copy(
            update={
                "text": text,
                "start_ms": 7000 + index * 400,
                "end_ms": 7300 + index * 400,
                "speaker_id": "speaker_001",
            }
        )
        for index, (word, text) in enumerate(
            zip(second.words[:4], ("Dalsza", "część", "tej", "wypowiedzi."), strict=True)
        )
    )
    second = second.model_copy(
        update={
            "start_ms": 7000,
            "end_ms": second_words[-1].end_ms,
            "text": "Dalsza część tej wypowiedzi.",
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
            "words": second_words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (first, second)})}
    )

    cues = build_subtitle_cues(result)

    assert cues[0].lines == ("jan: Tak jest.",)
    assert cues[1].lines == ("Dalsza część tej wypowiedzi.",)


def test_short_cross_segment_fragment_borrows_timed_words_from_following_cue() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first, second = result.transcript.segments
    first_words = tuple(
        first.words[0].model_copy(
            update={
                "word_id": f"word_cross_first_{index}",
                "text": "aa",
                "start_ms": 1000 + index * 500,
                "end_ms": 1400 + index * 500,
                "speaker_id": "speaker_001",
            }
        )
        for index in range(1)
    )
    first = first.model_copy(
        update={
            "start_ms": first_words[0].start_ms,
            "end_ms": first_words[-1].end_ms,
            "text": "aa",
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
            "words": first_words,
        }
    )
    second_words = tuple(
        second.words[0].model_copy(
            update={
                "word_id": f"word_cross_second_{index}",
                "text": "aa",
                "start_ms": 2300 + index * 500,
                "end_ms": 2700 + index * 500,
                "speaker_id": "speaker_001",
            }
        )
        for index in range(8)
    )
    second = second.model_copy(
        update={
            "start_ms": second_words[0].start_ms,
            "end_ms": second_words[-1].end_ms,
            "text": " ".join(word.text for word in second_words),
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
            "words": second_words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (first, second)})}
    )
    config = SubtitlesConfig(
        max_lines=1,
        max_chars_per_line=14,
        max_chars_per_second=100,
        min_words_per_cue=3,
        speaker_labels="never",
    )

    cues = build_subtitle_cues(result, config)

    assert tuple(len(" ".join(cue.lines).split()) for cue in cues) == (3, 3, 3)
    assert cues[0].end_ms == second_words[1].end_ms
    assert cues[1].start_ms == second_words[2].start_ms


def test_on_change_label_reserves_capacity_only_for_first_speaker_chunk() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    original = result.transcript.segments[1]
    words = tuple(
        original.words[0].model_copy(
            update={
                "word_id": f"word_label_capacity_{index}",
                "text": "aa",
                "start_ms": 1000 + index * 500,
                "end_ms": 1400 + index * 500,
                "speaker_id": "speaker_002",
            }
        )
        for index in range(12)
    )
    segment = original.model_copy(
        update={
            "start_ms": words[0].start_ms,
            "end_ms": words[-1].end_ms,
            "text": " ".join(word.text for word in words),
            "speaker_id": "speaker_002",
            "active_speaker_ids": ("speaker_002",),
            "words": words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (segment,)})}
    )
    config = SubtitlesConfig(
        max_lines=1,
        max_chars_per_line=20,
        max_chars_per_second=100,
        speaker_labels="on-change",
    )

    cues = build_subtitle_cues(result, config)

    assert tuple(len(" ".join(cue.lines).removeprefix("anna: ").split()) for cue in cues) == (5, 7)
    assert cues[0].lines[0].startswith("anna: ")
    assert not cues[1].lines[0].startswith("anna: ")


def test_three_cue_speaker_opening_is_revisited_after_continuation_balances() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first_template, second_template = result.transcript.segments

    def timed_words(
        texts: tuple[str, ...], starts: tuple[int, ...], *, prefix: str
    ) -> tuple[CanonicalWord, ...]:
        return tuple(
            second_template.words[0].model_copy(
                update={
                    "word_id": f"word_{prefix}_{index}",
                    "text": text,
                    "start_ms": start,
                    "end_ms": start + 160,
                    "speaker_id": "speaker_002",
                }
            )
            for index, (text, start) in enumerate(zip(texts, starts, strict=True))
        )

    first_speaker = first_template
    opening_words = timed_words(("Może", "i"), (15444, 15584), prefix="opening")
    opening = second_template.model_copy(
        update={
            "start_ms": 15444,
            "end_ms": 15744,
            "text": "Może i",
            "speaker_id": "speaker_002",
            "active_speaker_ids": ("speaker_002",),
            "words": opening_words,
        }
    )
    orphan_words = timed_words(("nikt",), (15784,), prefix="orphan")
    orphan = second_template.model_copy(
        update={
            "start_ms": 15784,
            "end_ms": 15964,
            "text": "nikt",
            "speaker_id": "speaker_002",
            "active_speaker_ids": ("speaker_002",),
            "words": orphan_words,
        }
    )
    continuation_texts = (
        "nie",
        "zauważy,",
        "ale",
        "pamiętajmy,",
        "że",
        "internet",
        "nie",
        "zapomina.",
    )
    continuation_starts = tuple(16004 + index * 450 for index in range(len(continuation_texts)))
    continuation_words = timed_words(continuation_texts, continuation_starts, prefix="continuation")
    continuation = second_template.model_copy(
        update={
            "start_ms": continuation_words[0].start_ms,
            "end_ms": continuation_words[-1].end_ms,
            "text": " ".join(continuation_texts),
            "speaker_id": "speaker_002",
            "active_speaker_ids": ("speaker_002",),
            "words": continuation_words,
        }
    )
    result = result.model_copy(
        update={
            "transcript": result.transcript.model_copy(
                update={"segments": (first_speaker, opening, orphan, continuation)}
            )
        }
    )

    cues = build_subtitle_cues(result)
    speaker_two_cues = [cue for cue in cues if cue.speaker_id == "speaker_002"]

    assert len(speaker_two_cues) == 1
    assert speaker_two_cues[0].end_ms - speaker_two_cues[0].start_ms >= 1000
    assert " ".join(speaker_two_cues[0].lines).startswith("anna: Może i nikt nie zauważy")


def test_connective_moves_from_end_of_cue_to_following_fragment() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    original = result.transcript.segments[0]
    texts = (*("aa" for _ in range(6)), "i", *("aa" for _ in range(4)))
    words = tuple(
        original.words[0].model_copy(
            update={
                "word_id": f"word_connective_{index}",
                "text": text,
                "start_ms": 1000 + index * 500,
                "end_ms": 1400 + index * 500,
            }
        )
        for index, text in enumerate(texts)
    )
    segment = original.model_copy(
        update={
            "start_ms": words[0].start_ms,
            "end_ms": words[-1].end_ms,
            "text": " ".join(texts),
            "words": words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (segment,)})}
    )
    config = SubtitlesConfig(
        max_lines=1,
        max_chars_per_line=20,
        max_chars_per_second=100,
        speaker_labels="never",
    )

    cues = build_subtitle_cues(result, config)

    assert " ".join(cues[0].lines).split()[-1] != "i"
    assert " ".join(cues[1].lines).split()[0] == "i"


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


def test_overlapping_speaker_chunks_are_globally_sorted_before_labelling() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    first, second = result.transcript.segments
    late_word = first.words[-1].model_copy(
        update={
            "word_id": "word_late",
            "text": "Continuation.",
            "start_ms": 5000,
            "end_ms": 6000,
        }
    )
    first = first.model_copy(
        update={
            "end_ms": 6000,
            "text": f"{first.text} Continuation.",
            "overlap": True,
            "active_speaker_ids": ("speaker_001", "speaker_002"),
            "words": (*first.words, late_word),
        }
    )
    second_words = tuple(
        word.model_copy(update={"start_ms": 4200 + index * 100, "end_ms": 4280 + index * 100})
        for index, word in enumerate(second.words)
    )
    second = second.model_copy(
        update={
            "start_ms": 4200,
            "end_ms": 5000,
            "overlap": True,
            "active_speaker_ids": ("speaker_001", "speaker_002"),
            "words": second_words,
        }
    )
    result = result.model_copy(
        update={"transcript": result.transcript.model_copy(update={"segments": (first, second)})}
    )

    cues = build_subtitle_cues(result, SubtitlesConfig(max_duration_ms=3000))

    assert [cue.start_ms for cue in cues] == sorted(cue.start_ms for cue in cues)
    speaker_ids = [cue.speaker_id for cue in cues]
    first_second = speaker_ids.index("speaker_002")
    return_to_first = speaker_ids.index("speaker_001", first_second)
    assert cues[0].lines[0].startswith("jan:")
    assert cues[first_second].lines[0].startswith("anna:")
    assert cues[return_to_first].lines[0].startswith("jan:")
    assert "Continuation" in render_srt(cues)
