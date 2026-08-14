"""Tests for reconstructable revision diagnostics."""

import json
from pathlib import Path

from ewp_transcripts.application import apply_review_file, audit_revision_file, prepare_review_file
from ewp_transcripts.config import ApplicationConfig

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def _revision(tmp_path: Path):
    base = tmp_path / "S01E01_results.json"
    base.write_bytes(EXAMPLE.read_bytes())
    review = prepare_review_file(base, output_directory=tmp_path / "reviews").path
    review.write_text(
        review.read_text(encoding="utf-8").replace(
            "Today we discuss transcription.",
            "Today we carefully discuss corrected transcription.",
        ),
        encoding="utf-8",
    )
    return base, apply_review_file(review, config=ApplicationConfig())


def test_audit_is_reconstructed_and_published_without_transcript_dependency(
    tmp_path: Path,
) -> None:
    base, applied = _revision(tmp_path)

    outcome = audit_revision_file(
        applied.revision_path,
        config=ApplicationConfig(),
        results_directory=base.parent,
        output_directory=tmp_path / "audit",
    )

    assert outcome.audit_path is not None
    persisted = json.loads(outcome.audit_path.read_text(encoding="utf-8"))
    classifications = {change["classification"] for change in persisted["changes"]}
    assert "insertion" in classifications
    assert persisted["revision"]["revision_number"] == 1
    assert persisted["statistics"] == applied.revision.statistics.model_dump(mode="json")


def test_nonpublishing_audit_writes_nothing(tmp_path: Path) -> None:
    base, applied = _revision(tmp_path)
    before = set(tmp_path.rglob("*"))

    outcome = audit_revision_file(
        applied.revision_path,
        config=ApplicationConfig(),
        results_directory=base.parent,
        publish=False,
    )

    assert outcome.audit_path is None
    assert set(tmp_path.rglob("*")) == before
    assert outcome.audit["generated_at"]
