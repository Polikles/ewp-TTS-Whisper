from pathlib import Path

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.review import ReviewSpeakerBlock
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.revision_service import build_revision
from ewp_transcripts.web_dictionaries import GuiDictionaryController
from ewp_transcripts.web_workflows import GuiWorkflowController

ROOT = Path(__file__).resolve().parents[2]


def test_gui_dictionary_retains_decisions_and_publishes(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    revisions = tmp_path / "revisions"
    canonical.mkdir()
    revisions.mkdir()
    source_result = ROOT / "examples/results.example.json"
    result = canonical / "case_results.json"
    result.write_bytes(source_result.read_bytes())
    review = prepare_review(result)
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
    revision = build_revision(edited, load_canonical_result(result), base_path=result)
    (revisions / "S01E01_revision_001.json").write_text(
        revision.model_dump_json(), encoding="utf-8"
    )
    paths = GuiWorkflowController((tmp_path.resolve(),))
    controller = GuiDictionaryController(resolve_path=paths.resolve_allowed_path)

    proposal = controller.propose(
        canonical_directory=str(canonical),
        revision_directory=str(revisions),
        output_root=str(tmp_path),
        project_id="example",
        minimum_occurrences=1,
        previous_dictionary="",
    )
    decisions = [
        {"source": item["source"], "target": item["target"], "status": "rejected"}
        for item in proposal["candidates"]
    ]
    saved = controller.save(
        proposal_path=proposal["proposal_path"],
        expected_sha256=proposal["proposal_sha256"],
        decisions=decisions,
    )
    published = controller.publish(
        proposal_path=saved["proposal_path"],
        dictionary_id="example-pl-v1",
        output_root=str(tmp_path),
    )

    assert saved["counts"]["pending"] == 0
    assert Path(published["dictionary_path"]).is_file()
    assert all(item["status"] == "rejected" for item in published["dictionary"]["entries"])
