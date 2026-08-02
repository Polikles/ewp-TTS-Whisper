# Install EWP-transcripts in WSL

Status: **Phase 1 scaffold installation is executable; transcription steps remain pending**.

This guide installs the current EWP-transcripts package from its committed lockfile. The Phase 1 commands (`--help`, `--version`, and `doctor`) are available. Model setup and transcription commands will be added only when their implementation phases are complete.

It is intentionally separate from [`PREPARE_PHASE0_WSL.md`](PREPARE_PHASE0_WSL.md):

- the spike guide tests candidate dependencies and may be discarded;
- this guide will consume the approved repository `uv.lock`;
- users will not manually reconstruct the dependency matrix;
- gated model downloads will remain explicit;
- normal transcription will run offline without hidden downloads.

## Current installation

Keep the repository in the WSL Linux filesystem, not under `/mnt/c` or `/mnt/d`:

```bash
cd ~/transkrypcje
git clone <REPOSITORY-URL> ewp-transcripts
cd ewp-transcripts
uv sync --locked
```

For an existing checkout:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
uv sync --locked
```

Verify the installed scaffold:

```bash
uv run transcriber --help
uv run transcriber --version
uv run transcriber doctor
make check
uv build
```

`doctor` does not load Torch, WhisperX, pyannote, or transcription models. A missing required environment capability returns exit code 3. `HF_TOKEN` is reported only as present or missing; its value is never printed.

## Planned complete application flow

1. Verify WSL, Ubuntu, NVIDIA passthrough, and FFmpeg.
2. Clone a tagged EWP-transcripts release into the Linux filesystem.
3. Install the documented `uv` version.
4. Run `uv sync --locked` using the committed production lockfile.
5. Run `transcriber doctor` without loading full models.
6. Explicitly download pinned ASR, alignment, and diarization models.
7. Run an optional deep GPU/model check.
8. Verify offline readiness.
9. Run the first `inspect`, `dry-run`, and `transcribe` operations.

Steps 6–9 are not yet application commands. Use the Phase 0 runbooks only for model/GPU validation until the corresponding production implementation is complete.
