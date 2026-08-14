"""Tests for the model-free export CLI adapter."""

import sys
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.application import apply_review_file, prepare_review_file
from ewp_transcripts.cli import app
from ewp_transcripts.config import ApplicationConfig

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
