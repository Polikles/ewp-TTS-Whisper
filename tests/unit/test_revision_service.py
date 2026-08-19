"""Tests for deterministic anchored review alignment."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.errors import InvalidReviewError
from ewp_transcripts.domain.review import ReviewSpeakerBlock
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "examples/results.example.json"
NOW = datetime(2026, 8, 14, 18, 0, tzinfo=UTC)


def _review(*texts: str):
    prepared = prepare_review(RESULT, generated_at=NOW)
    blocks = tuple(
        ReviewSpeakerBlock(speaker_id=original.speaker_id, text=text)
        for original, text in zip(prepared.anchors[0].speaker_blocks, texts, strict=True)
    )
    anchor = prepared.anchors[0].model_copy(update={"speaker_blocks": blocks})
    return prepared.model_copy(update={"anchors": (anchor,)})


def test_unchanged_review_maps_every_word_once() -> None:
    base = load_canonical_result(RESULT)
    revision = build_revision(
        prepare_review(RESULT, generated_at=NOW),
        base,
        base_path=RESULT,
        created_at=NOW,
    )

    assert revision.statistics.unchanged == 8
    assert revision.statistics.revision_tokens == 8
    assert [token.source_word_ids for token in revision.transcript.tokens] == [
        (f"word_{number:06d}",) for number in range(1, 9)
    ]
    assert revision.warnings == ()


def test_alignment_classifies_punctuation_split_insertion_and_deletion() -> None:
    base = load_canonical_result(RESULT)
    review = _review(
        "Welcome to episode!",
        "Today we discuss trans cription. carefully",
    )

    revision = build_revision(review, base, base_path=RESULT, created_at=NOW)

    assert revision.statistics.deletions == 1
    assert revision.statistics.punctuation_only_changes == 1
    assert revision.statistics.splits == 1
    assert revision.statistics.insertions == 1
    inserted = revision.transcript.tokens[-1]
    assert inserted.text == "carefully"
    assert inserted.source_word_ids == ()
    assert inserted.insertion_anchor is not None


def test_alignment_classifies_exact_lexical_merge() -> None:
    base = load_canonical_result(RESULT)
    review = _review(
        "Welcome to anotherepisode.",
        "Today we discuss transcription.",
    )

    revision = build_revision(review, base, base_path=RESULT, created_at=NOW)

    assert revision.statistics.merges == 1
    merged = revision.transcript.tokens[2]
    assert merged.text == "anotherepisode."
    assert merged.source_word_ids == ("word_000003", "word_000004")


def test_alignment_handles_proper_name_and_sentence_boundary_edits() -> None:
    base = load_canonical_result(RESULT)
    review = _review(
        "Welcome to another episode,",
        "Today. we discuss OpenAI.",
    )

    revision = build_revision(review, base, base_path=RESULT, created_at=NOW)

    assert revision.statistics.punctuation_only_changes == 2
    assert revision.statistics.substitutions == 1
    assert revision.transcript.tokens[-1].text == "OpenAI."


def test_ambiguous_alignment_is_reported() -> None:
    base = load_canonical_result(RESULT)
    review = _review("x", "Today we discuss transcription.")

    revision = build_revision(review, base, base_path=RESULT, created_at=NOW)

    assert revision.alignment.ambiguous_regions == 1
    assert {warning.code for warning in revision.warnings} == {"REVISION_ALIGNMENT_AMBIGUOUS"}


def test_insertion_across_configured_long_gap_warns() -> None:
    base = load_canonical_result(RESULT)
    review = _review(
        "Welcome carefully to another episode.",
        "Today we discuss transcription.",
    )

    revision = build_revision(
        review,
        base,
        base_path=RESULT,
        long_gap_warning_ms=20,
        created_at=NOW,
    )

    assert "REVISION_INSERT_ACROSS_LONG_GAP" in {warning.code for warning in revision.warnings}


def test_unchanged_repetition_remains_duplicated(tmp_path: Path) -> None:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    data["transcript"]["segments"][0]["words"][1]["text"] = "Welcome"
    repeated_result = tmp_path / RESULT.name
    repeated_result.write_text(json.dumps(data), encoding="utf-8")
    base = load_canonical_result(repeated_result)
    review = prepare_review(repeated_result, generated_at=NOW)

    revision = build_revision(
        review,
        base,
        base_path=repeated_result,
        created_at=NOW,
    )

    assert [token.text for token in revision.transcript.tokens[:2]] == [
        "Welcome",
        "Welcome",
    ]
    assert revision.statistics.unchanged == 8


def test_review_speaker_directive_changes_mapped_attribution() -> None:
    base = load_canonical_result(RESULT)
    prepared = prepare_review(RESULT, generated_at=NOW)
    first = prepared.anchors[0].speaker_blocks[0].model_copy(update={"speaker_id": "speaker_002"})
    anchor = prepared.anchors[0].model_copy(
        update={"speaker_blocks": (first, prepared.anchors[0].speaker_blocks[1])}
    )
    review = prepared.model_copy(update={"anchors": (anchor,)})

    revision = build_revision(review, base, base_path=RESULT, created_at=NOW)

    assert revision.statistics.speaker_changes == 4
    assert {token.speaker_id for token in revision.transcript.tokens[:4]} == {"speaker_002"}


def test_apply_rejects_base_bytes_that_do_not_match_review(tmp_path: Path) -> None:
    base = load_canonical_result(RESULT)
    changed = tmp_path / RESULT.name
    changed.write_bytes(RESULT.read_bytes() + b"\n")

    with pytest.raises(InvalidReviewError) as failure:
        build_revision(
            prepare_review(RESULT, generated_at=NOW),
            base,
            base_path=changed,
            created_at=NOW,
        )

    assert failure.value.code == "REVISION_BASE_HASH_MISMATCH"
