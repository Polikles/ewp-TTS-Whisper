# EWP Transcriber

> This repository documents the MVP of a local offline CLI tool for accurate transcription of audio recordings and audio tracks extracted from video files.

## Status

- Functional specification: ready for implementation.
- MVP reference environment: Windows + WSL2 + Ubuntu + NVIDIA CUDA.
- Reference hardware: NVIDIA RTX 3090 with 24 GB VRAM [testing lower spec is in TODO].
- Primary source language: Polish; English is available as an optional mode.
- Reference backend: WhisperX with pyannote speaker diarization.

## Primary outputs

Every successfully completed job creates a canonical file:

```text
<job_id>_results.json
```

Optional exports are generated from that canonical file:

```text
<job_id>_segments.json
<job_id>_transcript.txt
<job_id>_subtitles.srt
<job_id>_subtitles.vtt
```

Reprocessing the same source with `--force` creates a consistently versioned result set:

```text
<job_id>_results_v002.json
<job_id>_transcript_v002.txt
<job_id>_subtitles_v002.srt
<job_id>_subtitles_v002.vtt
```

## Documentation

The complete index is available in [`docs/README.md`](docs/README.md).

Recommended starting documents:

1. [`docs/01-product-scope.md`](docs/01-product-scope.md) — MVP purpose and boundaries.
2. [`docs/02-requirements.md`](docs/02-requirements.md) — functional and non-functional requirements.
3. [`docs/03-architecture.md`](docs/03-architecture.md) — architecture and processing pipeline.
4. [`docs/05-cli-specification.md`](docs/05-cli-specification.md) — CLI contract.
5. [`docs/07-results-data-model.md`](docs/07-results-data-model.md) — canonical data model.
6. [`docs/12-testing-and-acceptance.md`](docs/12-testing-and-acceptance.md) — tests and acceptance criteria.
7. [`docs/13-implementation-plan.md`](docs/13-implementation-plan.md) — implementation plan.

## Examples and schemas

- [`examples/config.example.toml`](examples/config.example.toml)
- [`examples/results.example.json`](examples/results.example.json)
- [`examples/segments.example.json`](examples/segments.example.json)
- [`schemas/results.schema.json`](schemas/results.schema.json)
- [`schemas/segments.schema.json`](schemas/segments.schema.json)

## Core project rules

- Audio and transcript text remain on the local machine during transcription.
- Final JSON files are the source of truth; TXT, SRT, and VTT are derived exports.
- Source files are never modified.
- Completed jobs with the same SHA-256 signature are skipped unless `--force` is used.

### Additional rules:
- Subdirectories are ignored unless recursion is explicitly enabled.
- Ambiguous stereo is handled conservatively as a single channel and produces a warning.

## Normative precedence

If documents conflict, use the following order:

1. ADRs accepted at a later date.
2. `docs/02-requirements.md`.
3. Detailed specifications in `docs/`.
4. Examples in `examples/`.
