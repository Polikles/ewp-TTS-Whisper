"""Tests for safe review publication and the application-facing prepare operation."""

from pathlib import Path

from ewp_transcripts.application import prepare_review_file
from ewp_transcripts.review_format import load_review
from ewp_transcripts.review_service import prepare_review
from ewp_transcripts.review_storage import publish_review, review_filename

ROOT = Path(__file__).resolve().parents[2]
RESULT_EXAMPLE = ROOT / "examples/results.example.json"


def test_review_filename_uses_human_editable_suffix_and_versions() -> None:
    assert review_filename(job_id="episode", version=1) == "episode.review.txt"
    assert review_filename(job_id="episode", version=2) == "episode.review_v002.txt"


def test_review_publication_never_overwrites_existing_work(tmp_path: Path) -> None:
    review = prepare_review(RESULT_EXAMPLE)

    first = publish_review(review, output_directory=tmp_path)
    first_bytes = first.read_bytes()
    second = publish_review(review, output_directory=tmp_path)

    assert first.name == "S01E01.review.txt"
    assert second.name == "S01E01.review_v002.txt"
    assert first.read_bytes() == first_bytes
    assert load_review(first) == review
    assert load_review(second) == review


def test_application_prepare_publishes_to_explicit_directory(tmp_path: Path) -> None:
    output = tmp_path / "review"

    outcome = prepare_review_file(RESULT_EXAMPLE, output_directory=output)

    assert outcome.path.parent == output
    assert outcome.path.is_file()
    assert outcome.review == load_review(outcome.path)
