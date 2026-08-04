"""Tests for shared lexical quality metrics and hypothesis readers."""

import json
from pathlib import Path

from ewp_transcripts.quality import (
    normalize_transcript,
    read_hypothesis,
    score,
    word_error_diff,
)


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
