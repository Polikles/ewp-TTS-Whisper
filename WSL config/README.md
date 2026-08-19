# EWP-transcripts operator guide

This directory contains only current instructions for installing and using the internal
`0.1.1` release candidate and for collecting feedback needed for V2.

For one complete command-oriented entry point, start with
[`../Instructions/README.md`](../Instructions/README.md). The files below provide the
detailed WSL setup and revision procedures linked from that runbook.

## Fresh WSL installation

Follow these documents in order:

1. [`SYSTEM_REQUIREMENTS.md`](SYSTEM_REQUIREMENTS.md) — supported host and hardware.
2. [`INSTALL_WSL.md`](INSTALL_WSL.md) — install Ubuntu 24.04 under WSL2.
3. [`INSTALL_TOOLS.md`](INSTALL_TOOLS.md) — install FFmpeg, Git, uv, and Python 3.12.
4. [`CUDA_SETUP.md`](CUDA_SETUP.md) — verify Windows-driver GPU passthrough.
5. [`INSTALL_APPLICATION.md`](INSTALL_APPLICATION.md) — clone and synchronize the
   committed lockfile.
6. [`MODEL_SETUP.md`](MODEL_SETUP.md) — explicitly download the pinned local models.
7. [`OFFLINE_MODE.md`](OFFLINE_MODE.md) — verify normal local-only operation.

Use [`VERIFY_ENVIRONMENT.md`](VERIFY_ENVIRONMENT.md) before changing an existing system
and [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) when a check fails. The complete
clean-distribution acceptance procedure is retained as
[`RUN_RELEASE_FRESH_WSL_INSTALL.md`](RUN_RELEASE_FRESH_WSL_INSTALL.md).

## Use the current MVP

- [`USE_CURRENT_MVP.md`](USE_CURRENT_MVP.md) — inspect, plan, transcribe, export,
  version, and clean jobs safely.
- [`REVISE_TRANSCRIPTS.md`](REVISE_TRANSCRIPTS.md) — prepare, edit, preview, apply,
  audit, and export immutable corrected transcript revisions on the v0.2.0 development
  branch.
- [`FEEDBACK_FOR_V2.md`](FEEDBACK_FOR_V2.md) — run the first archive pilot and retain
  correction, performance, subtitle, and workflow evidence without modifying canonical
  results.

## Historical validation material

Phase spikes, implementation gates, benchmark procedures, and release-specific retests
are preserved under [`../archive/mvp-validation-runbooks/`](../archive/mvp-validation-runbooks/README.md).
They document how the MVP was accepted; they are not installation or usage instructions.

## Safety rules

- Do not install a Linux NVIDIA display driver inside WSL.
- Keep the repository, environment, model cache, and work directories in the WSL Linux
  filesystem rather than under `/mnt/c` or `/mnt/d`.
- Never store `HF_TOKEN` in repository files, configuration, logs, or shared feedback.
- Source recordings and transcripts remain local unless the owner explicitly chooses to
  share a sanitized excerpt.
- Never edit or overwrite `*_results.json`; it is the canonical source of truth.
