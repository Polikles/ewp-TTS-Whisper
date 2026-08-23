"""Tests for project correction dictionary proposal extraction."""

import json
from pathlib import Path

import pytest

from ewp_transcripts.correction_dictionary import (
    _strip_boundary_punctuation,
    approve_correction_dictionary,
    propose_correction_dictionary,
    select_correction_dictionary_terms,
    write_correction_dictionary_proposal,
)
from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.review import ReviewSpeakerBlock
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_proposal_extracts_consistent_manual_lexical_mapping(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    revisions = tmp_path / "revisions"
    canonical.mkdir()
    revisions.mkdir()
    result_path = canonical / "case_results.json"
    result_path.write_bytes(EXAMPLE.read_bytes())
    review = prepare_review(result_path)
    blocks = list(review.anchors[0].speaker_blocks)
    blocks[0] = ReviewSpeakerBlock(
        speaker_id=blocks[0].speaker_id,
        text=blocks[0].text.replace("Welcome", "Greetings"),
    )
    edited = review.model_copy(
        update={
            "anchors": (review.anchors[0].model_copy(update={"speaker_blocks": tuple(blocks)}),)
        }
    )
    revision = build_revision(edited, load_canonical_result(result_path), base_path=result_path)
    (revisions / "S01E01_revision_001.json").write_text(
        revision.model_dump_json(), encoding="utf-8"
    )

    proposal = propose_correction_dictionary(
        canonical_directory=canonical,
        revision_directory=revisions,
        project_id="example",
        minimum_occurrences=1,
    )

    assert proposal.case_count == 1
    assert [(item.source, item.target, item.status) for item in proposal.candidates] == [
        ("Welcome", "Greetings", "pending")
    ]
    assert "[[Welcome]]" in proposal.candidates[0].evidence[0].source_context
    assert "[[Greetings]]" in proposal.candidates[0].evidence[0].target_context

    proposal_path = tmp_path / "proposal.json"
    write_correction_dictionary_proposal(proposal, proposal_path)
    with pytest.raises(ValueError, match="pending candidates"):
        approve_correction_dictionary(
            proposal_path=proposal_path,
            dictionary_id="example-pl-v1",
            output_path=tmp_path / "dictionary.json",
        )

    payload = json.loads(proposal_path.read_text(encoding="utf-8"))
    payload["candidates"][0]["status"] = "approved"
    proposal_path.write_text(json.dumps(payload), encoding="utf-8")
    dictionary = approve_correction_dictionary(
        proposal_path=proposal_path,
        dictionary_id="example-pl-v1",
        output_path=tmp_path / "dictionary.json",
    )

    assert dictionary.project_id == "example"
    assert [(item.source, item.target) for item in dictionary.entries] == [("Welcome", "Greetings")]
    selected = select_correction_dictionary_terms(dictionary, "Welcome everyone")
    assert [(item.source, item.target) for item in selected] == [("Welcome", "Greetings")]
    assert select_correction_dictionary_terms(dictionary, "A welcoming message") == ()


def test_dictionary_keys_discard_boundary_quotes_and_punctuation() -> None:
    assert _strip_boundary_punctuation("Anthropic,") == "Anthropic"
    assert _strip_boundary_punctuation('"akceptuję",') == "akceptuję"
    assert _strip_boundary_punctuation("etykawpetli.pl") == "etykawpetli.pl"
