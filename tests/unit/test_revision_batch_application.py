"""Tests for isolated batch review preview and apply."""

from pathlib import Path

from ewp_transcripts.application import prepare_review_file, process_review_batch
from ewp_transcripts.config import ApplicationConfig, RuntimeConfig

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def _case(tmp_path: Path, *, continue_after_error: bool = True):
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    results.mkdir()
    base = results / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    prepared = prepare_review_file(base, output_directory=tmp_path / "prepared").path
    reviews.mkdir()
    (reviews / "episode2.review.txt").write_bytes(prepared.read_bytes())
    (reviews / "episode3.review.txt").write_text("invalid", encoding="utf-8")
    (reviews / "episode10.review.txt").write_bytes(prepared.read_bytes())
    config = ApplicationConfig(
        runtime=RuntimeConfig(
            work_root=tmp_path / "work",
            continue_batch_after_error=continue_after_error,
        )
    )
    return results, reviews, config


def test_batch_apply_isolates_failure_and_allocates_valid_revisions(tmp_path: Path) -> None:
    results, reviews, config = _case(tmp_path)
    output = tmp_path / "revisions"

    outcome = process_review_batch(
        reviews,
        config=config,
        results_directory=results,
        output_directory=output,
    )

    assert [job.status for job in outcome.jobs] == ["applied", "failed", "applied"]
    assert outcome.applied == 2
    assert outcome.failed == 1
    assert sorted(path.name for path in output.glob("*.json")) == [
        "S01E01_revision_001.json",
        "S01E01_revision_002.json",
    ]


def test_batch_preview_stop_policy_writes_nothing(tmp_path: Path) -> None:
    results, reviews, config = _case(tmp_path, continue_after_error=False)
    output = tmp_path / "revisions"

    outcome = process_review_batch(
        reviews,
        config=config,
        results_directory=results,
        output_directory=output,
        apply=False,
    )

    assert [job.status for job in outcome.jobs] == ["previewed", "failed"]
    assert outcome.stopped_early is True
    assert not output.exists()
