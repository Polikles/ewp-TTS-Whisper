"""Tests for shared lexical quality metrics and hypothesis readers."""

import json
from itertools import product
from pathlib import Path

from ewp_transcripts.quality import (
    error_counts,
    normalize_transcript,
    read_hypothesis,
    score,
    word_error_diff,
)


def _full_counts(reference: str, hypothesis: str) -> tuple[int, int, int]:
    previous = [(index, 0, index, 0) for index in range(len(reference) + 1)]
    for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
        current = [(hypothesis_index, 0, 0, hypothesis_index)]
        for reference_index, reference_item in enumerate(reference, start=1):
            if reference_item == hypothesis_item:
                current.append(previous[reference_index - 1])
                continue
            diagonal = previous[reference_index - 1]
            left = current[reference_index - 1]
            above = previous[reference_index]
            current.append(
                min(
                    (
                        (diagonal[0] + 1, diagonal[1] + 1, diagonal[2], diagonal[3]),
                        (left[0] + 1, left[1], left[2] + 1, left[3]),
                        (above[0] + 1, above[1], above[2], above[3] + 1),
                    ),
                    key=lambda value: (value[0], value[2] + value[3], value[3]),
                )
            )
        previous = current
    return previous[-1][1:]


def test_normalization_preserves_accepted_phase0_policy() -> None:
    assert normalize_transcript("To jest ŁÓDŹ.\nCzy działa?") == "to jest łódź czy działa"
    assert normalize_transcript("pomyślę 15") != normalize_transcript("pomysle piętnaście")


def test_score_preserves_substitution_and_deletion_counts() -> None:
    report = score("jeden dwa trzy cztery", "jeden zły cztery")

    assert report["wer"] == 0.5
    assert report["word_errors"] == {
        "substitutions": 1,
        "deletions": 1,
        "insertions": 0,
        "reference_units": 4,
        "errors": 2,
    }


def test_optimized_scorer_matches_exact_distance_on_small_sequences() -> None:
    samples = ["".join(items) for length in range(5) for items in product("ab", repeat=length)]

    for reference in samples:
        for hypothesis in samples:
            counts = error_counts(reference, hypothesis)
            assert counts.errors == sum(_full_counts(reference, hypothesis))


def test_adaptive_scorer_handles_long_near_identical_text() -> None:
    reference = "a" * 50_000
    hypothesis = reference[:25_000] + "b" + reference[25_001:]

    counts = error_counts(reference, hypothesis)

    assert counts.errors == counts.substitutions == 1


def test_auto_reader_supports_canonical_result_without_speaker_metadata(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            {
                "transcript": {
                    "segments": [
                        {"text": "Pierwsze zdanie.", "speaker_id": "speaker_001"},
                        {"text": "Drugie zdanie!", "speaker_id": "speaker_002"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    text, selected_format = read_hypothesis(path, "auto")

    assert text == "Pierwsze zdanie. Drugie zdanie!"
    assert selected_format == "canonical-json"


def test_word_diff_contains_only_changed_normalized_words() -> None:
    operations = word_error_diff("Ala ma dwa koty", "ala ma trzy koty dziś")

    assert operations == ("~ dwa -> trzy", "+ dziś")
