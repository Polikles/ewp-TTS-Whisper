"""Tests for deterministic plain-text transcript exports."""

import json
from pathlib import Path
from typing import Any

import pytest

from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result
from ewp_transcripts.exporters.transcript import render_transcript, split_sentences

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"


def test_renders_example_with_speaker_blocks_and_no_timestamps() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    rendered = render_transcript(result)

    assert rendered == (
        "jan:\nWelcome to another episode.\n\nanna:\nToday we discuss transcription.\n"
    )
    assert "1240" not in rendered


def test_consecutive_segments_from_same_speaker_share_one_block() -> None:
    example = _example_data()
    example["transcript"]["segments"][1]["speaker_id"] = "speaker_001"
    example["transcript"]["segments"][1]["active_speaker_ids"] = ["speaker_001"]
    for word in example["transcript"]["segments"][1]["words"]:
        word["speaker_id"] = "speaker_001"
    result = CanonicalResult.model_validate_json(json.dumps(example))

    assert render_transcript(result) == (
        "jan:\nWelcome to another episode.\nToday we discuss transcription.\n"
    )


def test_single_speaker_omits_label_and_splits_sentences() -> None:
    example = _example_data()
    example["sources"] = example["sources"][:1]
    example["speakers"] = example["speakers"][:1]
    example["transcript"]["segments"] = example["transcript"]["segments"][:1]
    example["transcript"]["segments"][0]["text"] = "Pierwsze zdanie. Drugie zdanie!"
    result = CanonicalResult.model_validate_json(json.dumps(example))

    assert render_transcript(result) == "Pierwsze zdanie.\nDrugie zdanie!\n"


def test_sentence_split_preserves_abbreviations_and_repetitions() -> None:
    assert split_sentences("Rozmawiam z dr. Kowalskim. Tak, tak. Naprawdę?") == (
        "Rozmawiam z dr. Kowalskim.",
        "Tak, tak.",
        "Naprawdę?",
    )


@pytest.mark.parametrize("abbreviation", ["m.in.", "np.", "tzw.", "vs."])
def test_sentence_split_does_not_break_after_common_abbreviation(abbreviation: str) -> None:
    assert split_sentences(f"Obejmuje to {abbreviation} ten przykład. Następne zdanie.") == (
        f"Obejmuje to {abbreviation} ten przykład.",
        "Następne zdanie.",
    )


def _example_data() -> dict[str, Any]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
