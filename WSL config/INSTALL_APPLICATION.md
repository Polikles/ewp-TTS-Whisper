# Install EWP-transcripts in WSL

Status: **planned; not executable yet**.

This will become the clean-machine installation and update guide for actually running EWP-transcripts after the Phase 0 dependency stack and production package exist.

It is intentionally separate from [`PREPARE_PHASE0_WSL.md`](PREPARE_PHASE0_WSL.md):

- the spike guide tests candidate dependencies and may be discarded;
- this guide will consume the approved repository `uv.lock`;
- users will not manually reconstruct the dependency matrix;
- gated model downloads will remain explicit;
- normal transcription will run offline without hidden downloads.

## Planned final flow

1. Verify WSL, Ubuntu, NVIDIA passthrough, and FFmpeg.
2. Clone a tagged EWP-transcripts release into the Linux filesystem.
3. Install the documented `uv` version.
4. Run `uv sync --locked` using the committed production lockfile.
5. Run `transcriber doctor` without loading full models.
6. Explicitly download pinned ASR, alignment, and diarization models.
7. Run an optional deep GPU/model check.
8. Verify offline readiness.
9. Run the first `inspect`, `dry-run`, and `transcribe` operations.

Do not fill in production commands until the relevant application commands and lockfile exist. Until then, use the base WSL documentation and the Phase 0 spike guide.
