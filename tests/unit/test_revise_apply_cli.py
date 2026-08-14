"""Tests for revision preview and apply CLI behavior."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.application import prepare_review_file
from ewp_transcripts.cli import app

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
runner = CliRunner()


def _case(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    results.mkdir()
    base = results / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    review = prepare_review_file(base, output_directory=reviews).path
    return results, review


def test_preview_and_apply_no_apply_write_no_revision(tmp_path: Path) -> None:
    results, review = _case(tmp_path)
    revisions = tmp_path / "revisions"

    preview = runner.invoke(
        app,
        ["revise", "preview", str(review), "--results-dir", str(results)],
    )
    no_apply = runner.invoke(
        app,
        [
            "revise",
            "apply",
            str(review),
            "--results-dir",
            str(results),
            "--output-dir",
            str(revisions),
            "--no-apply",
        ],
    )

    assert preview.exit_code == no_apply.exit_code == 0
    assert preview.stdout == no_apply.stdout
    assert not revisions.exists()


def test_apply_publishes_revision_and_json_reports_path(tmp_path: Path) -> None:
    results, review = _case(tmp_path)
    revisions = tmp_path / "revisions"

    result = runner.invoke(
        app,
        [
            "revise",
            "apply",
            str(review),
            "--results-dir",
            str(results),
            "--output-dir",
            str(revisions),
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["revision_number"] == 1
    assert Path(payload["revision_path"]).name == "S01E01_revision_001.json"
    assert Path(payload["revision_path"]).is_file()


def test_directory_apply_reports_mixed_batch_and_exit_five(tmp_path: Path) -> None:
    results, review = _case(tmp_path)
    batch = tmp_path / "batch"
    revisions = tmp_path / "revisions"
    batch.mkdir()
    (batch / "episode2.review.txt").write_bytes(review.read_bytes())
    (batch / "episode3.review.txt").write_text("invalid", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "revise",
            "apply",
            str(batch),
            "--results-dir",
            str(results),
            "--output-dir",
            str(revisions),
            "--json-output",
        ],
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["applied"] == 1
    assert payload["failed"] == 1
    assert [job["status"] for job in payload["jobs"]] == ["applied", "failed"]
