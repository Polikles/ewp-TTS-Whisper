"""Tests for lightweight environment diagnostics."""

import subprocess
import sys
from collections.abc import Sequence

import pytest
from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.doctor import run_doctor
from ewp_transcripts.domain import DiagnosticStatus


def _successful_runner(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    stdout = "NVIDIA GeForce RTX 3090, 24576\n" if "nvidia-smi" in arguments[0] else "ok\n"
    return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")


def _all_executables(name: str) -> str:
    return f"/usr/bin/{name}"


def test_doctor_passes_on_validated_baseline_without_importing_ml() -> None:
    result = run_doctor(
        finder=_all_executables,
        runner=_successful_runner,
        environ={},
        python_version=(3, 12, 3),
        kernel_release="6.18.0-microsoft-standard-WSL2",
        os_release={"ID": "ubuntu", "VERSION_ID": "24.04"},
    )

    assert result.ready is True
    assert all(check.status is DiagnosticStatus.PASS for check in result.checks)
    assert "torch" not in sys.modules
    assert "whisperx" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_doctor_fails_when_gpu_is_missing() -> None:
    def finder(name: str) -> str | None:
        return None if name == "nvidia-smi" else f"/usr/bin/{name}"

    result = run_doctor(
        finder=finder,
        runner=_successful_runner,
        python_version=(3, 12, 3),
        kernel_release="6.18.0-microsoft-standard-WSL2",
        os_release={"ID": "ubuntu", "VERSION_ID": "24.04"},
    )

    assert result.ready is False
    gpu_check = next(check for check in result.checks if check.code == "gpu")
    assert gpu_check.status is DiagnosticStatus.FAIL


def test_doctor_json_returns_environment_exit_code_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-secret-that-must-not-be-printed"
    monkeypatch.setenv("HF_TOKEN", secret)
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--json-output"])

    assert result.exit_code == 3
    assert '"ready": false' in result.stdout
    assert "HF_TOKEN is present" in result.stdout
    assert secret not in result.stdout
