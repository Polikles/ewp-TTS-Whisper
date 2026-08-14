"""Tests for lightweight CLI entry points."""

import subprocess
import sys

from typer.testing import CliRunner

from ewp_transcripts import __version__
from ewp_transcripts.cli import app

runner = CliRunner()


def test_help_succeeds_without_importing_ml_backends() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Local-first transcription" in result.stdout
    assert "transcriber COMMAND --help" in result.stdout
    assert "torch" not in sys.modules
    assert "whisperx" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_command_help_exposes_command_specific_options() -> None:
    result = runner.invoke(app, ["inspect", "--help"])

    assert result.exit_code == 0
    assert "--speaker-count" in result.stdout
    assert "--channel-mode" in result.stdout


def test_version_reports_installed_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_module_entry_point_reports_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ewp_transcripts", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == __version__
    assert result.stderr == ""
