"""Static safety and interface checks for the fresh Ubuntu installer."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/install-fresh-ubuntu.sh"
MODEL_SCRIPT = ROOT / "scripts/setup-models.sh"


def test_fresh_install_script_has_valid_bash_syntax_and_safe_default() -> None:
    checked = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    help_result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert checked.returncode == 0, checked.stderr
    assert help_result.returncode == 0
    assert "--verify-only" in help_result.stdout
    assert "Read-only" in help_result.stdout
    assert "does not clone/update Git" in help_result.stdout
    assert "download gated transcription models" in help_result.stdout


def test_fresh_install_requires_explicit_install_and_preserves_model_boundary() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'mode="verify"' in text
    assert '--install) mode="install"' in text
    assert 'if [[ "$mode" == "install" ]]' in text
    assert "uv sync --locked" in text
    assert "--no-sync transcriber doctor --json-output" in text
    assert "MODEL_SETUP.md" in text
    assert "git pull" not in text
    assert "git clone" not in text
    assert "huggingface-cli download" not in text
    assert "hf download" not in text


def test_model_setup_script_has_valid_syntax_and_explicit_security_boundary() -> None:
    checked = subprocess.run(
        ["bash", "-n", str(MODEL_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    help_result = subprocess.run(
        ["bash", str(MODEL_SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert checked.returncode == 0, checked.stderr
    assert help_result.returncode == 0
    assert "--public-only" in help_result.stdout
    assert "read-only token" in help_result.stdout

    text = MODEL_SCRIPT.read_text(encoding="utf-8")
    assert "read -r -s" in text
    assert "export HF_TOKEN" in text
    assert "unset HF_TOKEN" in text
    assert "f0fe81560cb8b68660e564f55dd99207059c092e" in text
    assert "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee" in text
    assert "uv run --locked transcriber doctor" in text
    assert "git pull" not in text
