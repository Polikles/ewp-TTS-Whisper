"""Tests for model-free review preparation from canonical results."""

from datetime import UTC, datetime
from pathlib import Path

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.review import validate_review_base
from ewp_transcripts.domain.revision import sha256_file
from ewp_transcripts.review_format import parse_review, render_review
from ewp_transcripts.review_service import prepare_review

ROOT = Path(__file__).resolve().parents[2]
RESULT_EXAMPLE = ROOT / "examples/results.example.json"
NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def test_prepare_review_covers_base_and_preserves_speaker_turns() -> None:
    review = prepare_review(RESULT_EXAMPLE, generated_at=NOW, application_version="0.2.0")
    base = load_canonical_result(RESULT_EXAMPLE)

    validate_review_base(review, base, base_sha256=sha256_file(RESULT_EXAMPLE))
    assert review.header.base_result_file == RESULT_EXAMPLE.name
    assert review.anchors[0].first_word_id == "word_000001"
    assert review.anchors[-1].last_word_id == "word_000008"
    assert [block.speaker_id for block in review.anchors[0].speaker_blocks] == [
        "speaker_001",
        "speaker_002",
    ]


def test_small_anchor_target_splits_only_at_segment_boundaries() -> None:
    review = prepare_review(
        RESULT_EXAMPLE,
        anchor_target_words=4,
        generated_at=NOW,
    )

    assert [(anchor.first_word_id, anchor.last_word_id) for anchor in review.anchors] == [
        ("word_000001", "word_000004"),
        ("word_000005", "word_000008"),
    ]


def test_prepared_review_round_trips_without_changing_canonical_file() -> None:
    before = RESULT_EXAMPLE.read_bytes()
    review = prepare_review(RESULT_EXAMPLE, generated_at=NOW)

    reparsed = parse_review(render_review(review))

    assert reparsed == review
    assert RESULT_EXAMPLE.read_bytes() == before
