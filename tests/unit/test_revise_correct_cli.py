"""CLI tests for explicitly consented automated correction."""

from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
runner = CliRunner()


def test_correct_help_exposes_provider_safety_controls() -> None:
    result = runner.invoke(app, ["revise", "correct", "--help"])

    assert result.exit_code == 0
    assert "--model" in result.stdout
    assert "--endpoint" in result.stdout
    assert "--consent" in result.stdout
    assert "--resume-dir" in result.stdout
    assert "--preview" in result.stdout


def test_rejected_local_consent_makes_no_state_or_revision(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())

    result = runner.invoke(
        app,
        [
            "revise",
            "correct",
            str(base),
            "--model",
            "not-loaded-and-must-not-be-called",
            "--consent",
            "reject",
        ],
    )

    assert result.exit_code == 4
    assert "separate local API process" in result.stderr
    assert "no request was made" in result.stderr
    assert not (tmp_path / "correction-state-ewp-transcripts").exists()
    assert not tuple(tmp_path.glob("*_revision_*.json"))
