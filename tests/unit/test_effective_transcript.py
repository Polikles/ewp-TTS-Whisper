"""Tests for raw and revised effective transcript resolution."""

from pathlib import Path

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.review import ReviewSpeakerBlock
from ewp_transcripts.effective_transcript import (
    EffectiveToken,
    EffectiveTranscript,
    effective_canonical_result,
    resolve_effective_transcript,
)
from ewp_transcripts.exporters import build_subtitle_cues
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
    assert inserted.timing_source in {
        "following_word",
        "previous_word",
        "interpolated_gap",
    }
    assert "corrected episode." in projected.transcript.segments[0].text


def test_revision_projection_preserves_cross_speaker_overlap_for_subtitles(
    tmp_path: Path,
) -> None:
    base = load_canonical_result(RESULT)
    first, second = base.transcript.segments
    last_word = first.words[-1].model_copy(update={"end_ms": second.start_ms + 180})
    first = first.model_copy(
        update={
            "end_ms": last_word.end_ms,
            "overlap": True,
            "active_speaker_ids": ("speaker_001", "speaker_002"),
            "words": (*first.words[:-1], last_word),
        }
    )
    second = second.model_copy(
        update={
            "overlap": True,
            "active_speaker_ids": ("speaker_001", "speaker_002"),
        }
    )
    base = base.model_copy(
        update={"transcript": base.transcript.model_copy(update={"segments": (first, second)})}
    )
    base_path = tmp_path / "S01E01_results.json"
    base_path.write_text(base.model_dump_json(indent=2), encoding="utf-8")
    review = prepare_review(base_path)
    revision = build_revision(review, base, base_path=base_path)

    effective = resolve_effective_transcript(base, revision, base_path=base_path)
    projected = effective_canonical_result(base, effective)
    cues = build_subtitle_cues(projected)

    assert any(segment.overlap for segment in projected.transcript.segments)
    assert any(cue.overlap for cue in cues)


def test_long_inserted_run_is_partitionable_across_canonical_gap(tmp_path: Path) -> None:
    base = load_canonical_result(RESULT)
    first, second = base.transcript.segments
    final_word = first.words[-1].model_copy(update={"start_ms": 10_000, "end_ms": 11_000})
    first = first.model_copy(
        update={"end_ms": final_word.end_ms, "words": (*first.words[:-1], final_word)}
    )
    base = base.model_copy(
        update={"transcript": base.transcript.model_copy(update={"segments": (first, second)})}
    )
    # Keep canonical segment order while placing the next speaker after the enlarged gap.
    shifted_words = tuple(
        word.model_copy(update={"start_ms": word.start_ms + 8_000, "end_ms": word.end_ms + 8_000})
        for word in second.words
    )
    second = second.model_copy(
        update={
            "start_ms": second.start_ms + 8_000,
            "end_ms": second.end_ms + 8_000,
            "words": shifted_words,
        }
    )
    base = base.model_copy(
        update={"transcript": base.transcript.model_copy(update={"segments": (first, second)})}
    )
    base_path = tmp_path / "S01E01_results.json"
    base_path.write_text(base.model_dump_json(indent=2), encoding="utf-8")
    review = prepare_review(base_path)
    inserted_text = " ".join(f"inserted{index}" for index in range(19))
    first_block = (
        review.anchors[0]
        .speaker_blocks[0]
        .model_copy(update={"text": f"Welcome to another {inserted_text} episode."})
    )
    first_anchor = review.anchors[0].model_copy(
        update={"speaker_blocks": (first_block, *review.anchors[0].speaker_blocks[1:])}
    )
    review = review.model_copy(update={"anchors": (first_anchor, *review.anchors[1:])})
    revision = build_revision(review, base, base_path=base_path)

    effective = resolve_effective_transcript(base, revision, base_path=base_path)
    inserted = [token for token in effective.tokens if token.text.startswith("inserted")]
    projected = effective_canonical_result(base, effective)
    cues = build_subtitle_cues(projected)

    assert len(inserted) == 19
    assert len({(token.start_ms, token.end_ms) for token in inserted}) == 19
    assert len(cues) > 1


def test_revision_projection_orders_overlapping_speaker_groups_chronologically() -> None:
    base = load_canonical_result(RESULT)
    effective = EffectiveTranscript(
        language="en",
        revision_number=1,
        tokens=(
            EffectiveToken(
                token_id="rt_000001",
                text="Later textual group.",
                speaker_id="speaker_002",
                source_word_ids=("word_000001",),
                start_ms=1_100,
                end_ms=1_300,
                timing_source="canonical_mapping",
                overlap=True,
                active_speaker_ids=("speaker_001", "speaker_002"),
            ),
            EffectiveToken(
                token_id="rt_000002",
                text="Earlier overlapping group.",
                speaker_id="speaker_001",
                source_word_ids=("word_000002",),
                start_ms=1_000,
                end_ms=1_400,
                timing_source="canonical_mapping",
                overlap=True,
                active_speaker_ids=("speaker_001", "speaker_002"),
            ),
        ),
    )

    projected = effective_canonical_result(base, effective)

    assert [segment.start_ms for segment in projected.transcript.segments] == [1_000, 1_100]
