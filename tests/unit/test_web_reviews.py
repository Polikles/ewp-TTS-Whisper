from pathlib import Path

import pytest

from ewp_transcripts.config import ApplicationConfig, RuntimeConfig
from ewp_transcripts.web_reviews import GuiReviewController, GuiReviewError
from ewp_transcripts.web_workflows import GuiWorkflowController

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def controller(tmp_path: Path) -> GuiReviewController:
    paths = GuiWorkflowController((tmp_path.resolve(),))
    return GuiReviewController(
        config=ApplicationConfig(runtime=RuntimeConfig(work_root=tmp_path / "work")),
        resolve_path=paths.resolve_allowed_path,
    )


def test_browser_review_prepare_edit_preview_and_apply(tmp_path: Path) -> None:
    result = tmp_path / EXAMPLE.name
    result.write_bytes(EXAMPLE.read_bytes())
    reviews = tmp_path / "reviews"
    revisions = tmp_path / "revisions"
    service = controller(tmp_path)

    prepared = service.prepare(str(result), str(reviews))
    assert prepared["source_verification"] == "canonical_asr"
    assert prepared["review_path"].endswith("S01E01.review.txt")
    assert prepared["speaker_labels"] == {"speaker_001": "jan", "speaker_002": "anna"}
    prepared["anchors"][0]["blocks"][0]["text"] += " corrected"

    saved = service.save(
        prepared["review_path"],
        str(result),
        expected_sha256=prepared["review_sha256"],
        anchors=prepared["anchors"],
    )
    assert saved["review_sha256"] != prepared["review_sha256"]
    assert saved["anchors"][0]["blocks"][0]["text"].endswith("corrected")

    preview = service.preview(saved["review_path"], str(result))
    assert preview["revision_number"] == 1
    applied = service.apply(saved["review_path"], str(result), str(revisions))
    assert applied["revision_number"] == 1
    assert Path(applied["revision_path"]).is_file()
    exported = service.export(
        str(result),
        applied["revision_path"],
        str(tmp_path / "exports"),
        ["txt", "srt", "vtt"],
    )
    assert len(exported["written"]) == 3


def test_browser_review_requires_current_hash_and_preview(tmp_path: Path) -> None:
    result = tmp_path / EXAMPLE.name
    result.write_bytes(EXAMPLE.read_bytes())
    service = controller(tmp_path)
    prepared = service.prepare(str(result), str(tmp_path / "reviews"))

    with pytest.raises(GuiReviewError, match="changed after it was loaded") as conflict:
        service.save(
            prepared["review_path"],
            str(result),
            expected_sha256="0" * 64,
            anchors=prepared["anchors"],
        )
    assert conflict.value.code == "GUI_REVIEW_CONFLICT"

    with pytest.raises(GuiReviewError, match="Preview") as missing_preview:
        service.apply(prepared["review_path"], str(result), str(tmp_path / "revisions"))
    assert missing_preview.value.code == "GUI_REVIEW_PREVIEW_REQUIRED"
