"""Lightweight environment diagnostics with no ML imports."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ewp_transcripts import __version__
from ewp_transcripts.domain import DiagnosticCheck, DiagnosticStatus, DoctorResult

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
ExecutableFinder = Callable[[str], str | None]


def _run_command(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _python_check(version_info: tuple[int, int, int]) -> DiagnosticCheck:
    supported = (3, 12) <= version_info[:2] < (3, 13)
    return DiagnosticCheck(
        code="python",
        status=DiagnosticStatus.PASS if supported else DiagnosticStatus.FAIL,
        message="Python version is supported." if supported else "Python 3.12 is required.",
        context={"version": ".".join(map(str, version_info))},
    )


def _wsl_check(kernel_release: str) -> DiagnosticCheck:
    is_wsl = "microsoft" in kernel_release.casefold()
    return DiagnosticCheck(
        code="wsl2",
        status=DiagnosticStatus.PASS if is_wsl else DiagnosticStatus.WARNING,
        message="WSL2 environment detected." if is_wsl else "WSL2 was not detected.",
    )


def _ubuntu_check(os_release: Mapping[str, str]) -> DiagnosticCheck:
    distribution = os_release.get("ID", "unknown")
    version = os_release.get("VERSION_ID", "unknown")
    supported = distribution == "ubuntu" and version == "24.04"
    return DiagnosticCheck(
        code="distribution",
        status=DiagnosticStatus.PASS if supported else DiagnosticStatus.WARNING,
        message=(
            "Ubuntu 24.04 baseline detected."
            if supported
            else "Environment differs from the validated Ubuntu 24.04 baseline."
        ),
        context={"distribution": distribution, "version": version},
    )


def _command_check(
    executable: str,
    arguments: Sequence[str],
    finder: ExecutableFinder,
    runner: CommandRunner,
) -> DiagnosticCheck:
    path = finder(executable)
    if path is None:
        return DiagnosticCheck(
            code=executable,
            status=DiagnosticStatus.FAIL,
            message=f"Required executable '{executable}' is missing.",
        )

    try:
        completed = runner([path, *arguments])
    except (OSError, subprocess.SubprocessError) as error:
        return DiagnosticCheck(
            code=executable,
            status=DiagnosticStatus.FAIL,
            message=f"Unable to run '{executable}'.",
            context={"error_type": type(error).__name__},
        )

    return DiagnosticCheck(
        code=executable,
        status=(DiagnosticStatus.PASS if completed.returncode == 0 else DiagnosticStatus.FAIL),
        message=(
            f"Executable '{executable}' is available."
            if completed.returncode == 0
            else f"Executable '{executable}' returned an error."
        ),
        context={"exit_code": completed.returncode},
    )


def _gpu_check(finder: ExecutableFinder, runner: CommandRunner) -> DiagnosticCheck:
    executable = finder("nvidia-smi")
    if executable is None:
        return DiagnosticCheck(
            code="gpu",
            status=DiagnosticStatus.FAIL,
            message="NVIDIA GPU visibility is unavailable: nvidia-smi is missing.",
        )

    try:
        completed = runner(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ]
        )
    except (OSError, subprocess.SubprocessError) as error:
        return DiagnosticCheck(
            code="gpu",
            status=DiagnosticStatus.FAIL,
            message="NVIDIA GPU query failed.",
            context={"error_type": type(error).__name__},
        )

    output = completed.stdout.strip()
    if completed.returncode != 0 or not output:
        return DiagnosticCheck(
            code="gpu",
            status=DiagnosticStatus.FAIL,
            message="NVIDIA GPU query returned no usable device.",
            context={"exit_code": completed.returncode},
        )

    return DiagnosticCheck(
        code="gpu",
        status=DiagnosticStatus.PASS,
        message="NVIDIA GPU is visible.",
        context={"device": output.splitlines()[0]},
    )


def _token_check(environ: Mapping[str, str]) -> DiagnosticCheck:
    present = bool(environ.get("HF_TOKEN"))
    return DiagnosticCheck(
        code="hf_token",
        status=DiagnosticStatus.PASS,
        message=f"HF_TOKEN is {'present' if present else 'missing'}.",
        context={"present": present},
    )


def _read_os_release(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value.strip().strip('"')
    return values


def run_doctor(
    *,
    finder: ExecutableFinder = shutil.which,
    runner: CommandRunner = _run_command,
    environ: Mapping[str, str] = os.environ,
    python_version: tuple[int, int, int] = sys.version_info[:3],
    kernel_release: str = platform.release(),
    os_release: Mapping[str, str] | None = None,
) -> DoctorResult:
    """Run deterministic lightweight checks without importing ML backends."""

    release = _read_os_release(Path("/etc/os-release")) if os_release is None else os_release
    checks = (
        _python_check(python_version),
        _wsl_check(kernel_release),
        _ubuntu_check(release),
        _command_check("ffmpeg", ["-version"], finder, runner),
        _command_check("ffprobe", ["-version"], finder, runner),
        _gpu_check(finder, runner),
        _token_check(environ),
    )
    return DoctorResult(
        application_version=__version__,
        ready=all(check.status is not DiagnosticStatus.FAIL for check in checks),
        checks=checks,
    )
