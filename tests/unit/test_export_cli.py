"""Tests for the model-free export CLI adapter."""

import sys
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.application import apply_review_file, prepare_review_file
from ewp_transcripts.cli import app
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.canonical import CanonicalResult

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"
runner = CliRunner()


def test_export_cli_writes_requested_format(tmp_path: Path) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())

    result = runner.invoke(app, ["export", str(result_path), "--format", "txt"])

    assert result.exit_code == 0
    assert "Export version: 1" in result.stdout
    assert "WROTE" in result.stdout
    assert (tmp_path / "S01E01_transcript.txt").is_file()
    assert not (tmp_path / "S01E01_subtitles.srt").exists()
    assert "torch" not in sys.modules
    assert "whisperx" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_export_cli_reports_schema_failure_with_exit_code_8(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["export", str(invalid), "--format", "txt"])

    assert result.exit_code == 8
    assert "Cannot read canonical result" in result.stderr


def test_export_cli_accepts_latest_revision(tmp_path: Path) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())
    review = prepare_review_file(result_path, output_directory=tmp_path / "reviews").path
    apply_review_file(review, config=ApplicationConfig())

    result = runner.invoke(
        app,
        ["export", str(result_path), "--format", "txt", "--revision", "latest"],
    )

    assert result.exit_code == 0
    assert "Revision number: 1" in result.stdout
    assert (tmp_path / "S01E01_transcript_revision_001.txt").is_file()


def _write_batch_result(directory: Path, job_id: str) -> Path:
    result = CanonicalResult.model_validate_json(EXAMPLE_PATH.read_bytes()).model_copy(
        update={"job_id": job_id}
    )
    path = directory / f"{job_id}_results.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_export_cli_accepts_result_and_revision_directories(tmp_path: Path) -> None:
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    revisions = tmp_path / "revisions"
    exports = tmp_path / "exports"
    results.mkdir()
    for job_id in ("S01E01", "S01E02"):
        result_path = _write_batch_result(results, job_id)
        review = prepare_review_file(result_path, output_directory=reviews).path
        apply_review_file(
            review,
            config=ApplicationConfig(),
            results_directory=results,
            output_directory=revisions,
        )

    result = runner.invoke(
        app,
        [
            "export",
            str(results),
            "--revision",
            str(revisions),
            "--output-dir",
            str(exports),
            "--format",
            "txt",
            "--format",
            "segments",
        ],
    )

    assert result.exit_code == 0
    assert "SUMMARY exported=2 failed=0 written=4 skipped=0 stopped_early=false" in result.stdout
    for job_id in ("S01E01", "S01E02"):
        assert (exports / f"{job_id}_transcript_revision_001.txt").is_file()
        assert (exports / f"{job_id}_segments_revision_001.json").is_file()


def test_export_cli_isolates_missing_revision_in_directory_batch(tmp_path: Path) -> None:
    results = tmp_path / "results"
    revisions = tmp_path / "revisions"
    exports = tmp_path / "exports"
    results.mkdir()
    first = _write_batch_result(results, "S01E01")
    _write_batch_result(results, "S01E02")
    review = prepare_review_file(first, output_directory=tmp_path / "reviews").path
    apply_review_file(
        review,
        config=ApplicationConfig(),
        results_directory=results,
        output_directory=revisions,
    )

    result = runner.invoke(
        app,
        [
            "export",
            str(results),
            "--revision",
            str(revisions),
            "--output-dir",
            str(exports),
            "--format",
            "txt",
        ],
    )

    assert result.exit_code == 5
    assert "SUMMARY exported=1 failed=1 written=1 skipped=0 stopped_early=false" in result.stdout
    assert "No compatible transcript revision was found for S01E02" in result.stdout
    assert (exports / "S01E01_transcript_revision_001.txt").is_file()
