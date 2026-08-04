# Phase 1 results

Validated on **2026-08-02** against the target Ubuntu 24.04 WSL2 workstation with an NVIDIA GeForce RTX 3090.

## Status

**PASS**.

## Accepted checks

```text
uv sync --locked=PASS
transcriber --help=PASS
transcriber --version=0.1.0
transcriber doctor=PASS (exit 0)
make check=PASS
pytest=18 passed
ruff check=PASS
ruff format --check=PASS
mypy strict=PASS
uv build wheel=PASS
uv build source distribution=PASS
git worktree after validation=clean
```

The human-readable and JSON doctor outputs reported Python 3.12.3, WSL2, Ubuntu 24.04, FFmpeg, ffprobe, and the RTX 3090 as available. `HF_TOKEN` was missing and no secret value was exposed. Help, version, and doctor completed without loading transcription models.

## Release-readiness diagnostic expansion

Repeated on **2026-08-04** after commit `0ad771c` using
[`RUN_RELEASE_DOCTOR.md`](RUN_RELEASE_DOCTOR.md).

```text
make check=PASS (232 tests)
python=PASS
wsl2=PASS
distribution=PASS
ffmpeg=PASS
ffprobe=PASS
gpu=PASS
cuda=PASS
asr_model=PASS
alignment_model=PASS
diarization_model=PASS
hf_token=PASS (absent)
doctor exit=0
doctor JSON readiness=PASS
doctor secret scan=PASS
doctor explicit config=PASS
```

This closes the lightweight environment, PyTorch CUDA, pinned-model readiness, explicit
configuration, sanitized JSON, and exit-code portions of FR-G04. CUDA was checked in a
child Python process; no ASR, alignment, or diarization model was loaded.

## Host-independent test correction

The first WSL `make check` exposed a test that assumed the executing host had no GPU. Application behavior was correct: WSL detected the RTX 3090 and returned exit code 0. Commit `79f2d46` replaced the physical-host assumption with an injected missing-GPU diagnostic. The repeated quality gate passed all 18 tests on both the CPU development VM and the GPU WSL workstation.
