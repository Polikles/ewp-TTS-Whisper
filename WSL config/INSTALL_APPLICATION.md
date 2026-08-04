# Install EWP-transcripts in WSL

Status: **MVP source-checkout installation is executable; release-wheel validation is
documented separately**.

This guide installs the current EWP-transcripts package from its committed lockfile.
`doctor`, `inspect`, `dry-run`, `transcribe`, `export`, and `clean` are available.

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

`doctor` does not load WhisperX, pyannote, or transcription models. It checks CUDA in a short child Python process and verifies the configured pinned model directories. A missing required environment capability or model returns exit code 3. `HF_TOKEN` is reported only as present or missing; its value is never printed.

## Complete application flow

1. Verify WSL, Ubuntu, NVIDIA passthrough, and FFmpeg.
2. Clone a tagged EWP-transcripts release into the Linux filesystem.
3. Install the documented `uv` version.
4. Run `uv sync --locked` using the committed production lockfile.
5. Run `transcriber doctor` without loading transcription models.
6. Explicitly download pinned ASR, alignment, and diarization models.
7. Run the GPU/model checks from the model-setup guide.
8. Verify offline readiness.
9. Run `inspect` and `dry-run`, then the first production `transcribe` operation.

For release evidence, build and install the distributable artifact into an isolated
environment using [`RUN_PHASE9_WHEEL_INSTALL.md`](RUN_PHASE9_WHEEL_INSTALL.md). That
procedure prevents the source checkout from satisfying imports and installs the exact
locked CUDA runtime dependency set before the wheel.
