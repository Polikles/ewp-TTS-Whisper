"""Tests for parent and sibling full-snapshot revision lineage."""

from pathlib import Path

from ewp_transcripts.application import apply_review_file, prepare_review_file
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.revision import load_transcript_revision, sha256_file
from ewp_transcripts.export_service import ExportFormat, export_result
from ewp_transcripts.review_format import load_review, render_review

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_child_records_exact_parent_but_exports_as_standalone_snapshot(tmp_path: Path) -> None:
    base = tmp_path / "S01E01_results.json"
    base.write_bytes(EXAMPLE.read_bytes())
    first_review = prepare_review_file(base, output_directory=tmp_path / "reviews").path
    first = apply_review_file(first_review, config=ApplicationConfig())

    prepared = load_review(prepare_review_file(base, output_directory=tmp_path / "reviews").path)
    parent_header = prepared.header.model_copy(
        update={
            "source_revision_id": first.revision.revision_id,
            "source_revision_sha256": sha256_file(first.revision_path),
            "source_revision_number": first.revision.revision_number,
        }
    )
    parent_review = prepared.model_copy(update={"header": parent_header})
    parent_review_path = tmp_path / "reviews" / "child.review.txt"
    parent_review_path.write_text(render_review(parent_review), encoding="utf-8")

    child = apply_review_file(parent_review_path, config=ApplicationConfig())

    assert child.revision.parent_revision is not None
    assert child.revision.parent_revision.revision_id == first.revision.revision_id
    assert child.revision.parent_revision.sha256 == sha256_file(first.revision_path)
    first.revision_path.unlink()
    exported = export_result(
        base,
        formats=(ExportFormat.TXT,),
        revision=child.revision_path,
    )
    assert exported.revision_number == child.revision.revision_number


def test_reapplying_base_review_creates_sibling_without_parent(tmp_path: Path) -> None:
    base = tmp_path / "S01E01_results.json"
    base.write_bytes(EXAMPLE.read_bytes())
    review = prepare_review_file(base, output_directory=tmp_path / "reviews").path

    first = apply_review_file(review, config=ApplicationConfig())
    sibling = apply_review_file(review, config=ApplicationConfig())

    assert first.revision.parent_revision is None
    assert sibling.revision.parent_revision is None
    loaded = load_transcript_revision(sibling.revision_path)
    assert loaded.base_result.sha256 == first.revision.base_result.sha256
    assert loaded.revision_id != first.revision.revision_id
