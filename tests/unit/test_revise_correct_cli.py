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
    assert "non-final review candidate" in result.stdout
    assert "--model" in result.stdout
    assert "--provider" in result.stdout
    assert "--endpoint" in result.stdout
    assert "--allow-remote-endpoi" in result.stdout
    assert "--allow-cloud" in result.stdout
    assert "--api-key-env" in result.stdout
    assert "--output-mode" in result.stdout
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


def test_cloud_is_blocked_offline_before_api_key_or_request(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())

    result = runner.invoke(
        app,
        [
            "revise",
            "correct",
            str(base),
            "--provider",
            "openrouter",
            "--model",
            "qwen/qwen-2.5-72b-instruct",
            "--consent",
            "once",
        ],
    )

    assert result.exit_code == 4
    assert "leave this machine" in result.stderr
    assert "offline mode blocks cloud" in result.stderr
    assert "API key is missing" not in result.stderr
    assert not (tmp_path / "correction-state-ewp-transcripts").exists()


def test_rejected_cloud_consent_needs_no_api_key(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())

    result = runner.invoke(
        app,
        [
            "revise",
            "correct",
            str(base),
            "--provider",
            "openrouter",
            "--model",
            "qwen/qwen-2.5-72b-instruct",
            "--allow-cloud",
            "--consent",
            "reject",
        ],
    )

    assert result.exit_code == 4
    assert "leave this machine" in result.stderr
    assert "no request was made" in result.stderr
    assert "API key is missing" not in result.stderr


def test_remote_endpoint_requires_opt_in_and_prints_network_warning(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    arguments = [
        "revise",
        "correct",
        str(base),
        "--model",
        "model",
        "--endpoint",
        "http://100.99.201.120:1234/v1",
        "--consent",
        "reject",
    ]

    denied = runner.invoke(app, arguments)
    opted_in = runner.invoke(app, [*arguments, "--allow-remote-endpoint"])

    assert denied.exit_code == 2
    assert "Invalid LM Studio" in denied.stderr
    assert opted_in.exit_code == 4
    assert "sent over the network" in opted_in.stderr
    assert "no request was made" in opted_in.stderr
