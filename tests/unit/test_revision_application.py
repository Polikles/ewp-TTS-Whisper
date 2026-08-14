"""Tests for application-level revision preview and publication."""

from pathlib import Path

from ewp_transcripts.application import (
    apply_review_file,
    prepare_review_file,
    preview_review_file,
)
from ewp_transcripts.config import ApplicationConfig, RuntimeConfig

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_preview_locates_parent_base_and_writes_nothing(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    review_path = prepare_review_file(base, output_directory=tmp_path / "reviews").path
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())

    outcome = preview_review_file(review_path)

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    assert outcome.base_result_path == base
    assert outcome.revision.revision_number == 1
    assert after == before


def test_apply_allocates_immutable_revision_numbers(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    review_path = prepare_review_file(base, output_directory=tmp_path / "reviews").path
    config = ApplicationConfig(runtime=RuntimeConfig(work_root=tmp_path / "work"))

    first = apply_review_file(review_path, config=config)
    second = apply_review_file(review_path, config=config)

    assert first.revision.revision_number == 1
    assert first.revision_path.name == "S01E01_revision_001.json"
    assert second.revision.revision_number == 2
    assert second.revision_path.name == "S01E01_revision_002.json"
    assert first.revision_path.read_bytes() != second.revision_path.read_bytes()
