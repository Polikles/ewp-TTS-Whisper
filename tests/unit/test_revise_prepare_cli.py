"""Tests for the model-free ``revise prepare`` CLI adapter."""

import json
import shutil
import sys
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
runner = CliRunner()


def test_revise_prepare_single_file_writes_review_without_ml_imports(tmp_path: Path) -> None:
    result_path = tmp_path / "episode_results.json"
    output = tmp_path / "reviews"
    shutil.copyfile(EXAMPLE, result_path)

    result = runner.invoke(
        app,
        ["revise", "prepare", str(result_path), "--output-dir", str(output)],
    )

    assert result.exit_code == 0
    assert "SUMMARY prepared=1 failed=0 stopped_early=false" in result.stdout
    assert (output / "S01E01.review.txt").is_file()
    assert "torch" not in sys.modules
    assert "whisperx" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_revise_prepare_directory_json_reports_isolated_failure(tmp_path: Path) -> None:
    source = tmp_path / "results"
    output = tmp_path / "reviews"
    source.mkdir()
    shutil.copyfile(EXAMPLE, source / "episode2_results.json")
    (source / "episode3_results.json").write_text("invalid", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "revise",
            "prepare",
            str(source),
            "--output-dir",
            str(output),
            "--json-output",
        ],
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["prepared"] == 1
    assert payload["failed"] == 1
    assert [job["status"] for job in payload["jobs"]] == ["prepared", "failed"]
    assert payload["jobs"][1]["failure_code"] == "REVISION_BASE_HASH_MISMATCH"


def test_revise_prepare_help_documents_model_free_options() -> None:
    result = runner.invoke(app, ["revise", "prepare", "--help"])

    assert result.exit_code == 0
    assert "without loading audio or ML models" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--recursive" in result.stdout
    assert "--json-output" in result.stdout
