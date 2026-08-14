"""Tests for raw and revised effective transcript resolution."""

from pathlib import Path

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.review import ReviewSpeakerBlock
from ewp_transcripts.effective_transcript import (
    effective_canonical_result,
    resolve_effective_transcript,
)
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "examples/results.example.json"


def test_raw_effective_transcript_preserves_every_canonical_word() -> None:
    base = load_canonical_result(RESULT)

    effective = resolve_effective_transcript(base)

    assert [token.text for token in effective.tokens] == [
        word.text for segment in base.transcript.segments for word in segment.words
    ]
    assert effective.revision_number is None


def test_revision_resolves_corrected_text_speaker_and_inherited_timing() -> None:
    base = load_canonical_result(RESULT)
    prepared = prepare_review(RESULT)
    first = ReviewSpeakerBlock(
        speaker_id="speaker_002",
        text="Welcome to another corrected episode.",
    )
    anchor = prepared.anchors[0].model_copy(
        update={"speaker_blocks": (first, prepared.anchors[0].speaker_blocks[1])}
    )
    review = prepared.model_copy(update={"anchors": (anchor,)})
    revision = build_revision(review, base, base_path=RESULT)

    effective = resolve_effective_transcript(base, revision, base_path=RESULT)
    projected = effective_canonical_result(base, effective)

    assert [token.text for token in effective.tokens[:5]] == [
        "Welcome",
        "to",
        "another",
        "corrected",
        "episode.",
    ]
    assert {token.speaker_id for token in effective.tokens[:5]} == {"speaker_002"}
    inserted = effective.tokens[3]
    assert inserted.source_word_ids == ()
    assert inserted.timing_source in {"following_word", "previous_word"}
    assert "corrected episode." in projected.transcript.segments[0].text
