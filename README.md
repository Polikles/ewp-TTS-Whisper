# EWP Transcriber

> EWP-transcripts is a local-first CLI application for accurate transcription of audio recordings. The executable is named `transcriber`.

## Status

- MVP implementation: feature-complete for the validated Polish workflows; release audit and clean-environment validation remain in progress.
- MVP reference environment: Windows + WSL2 + Ubuntu + NVIDIA CUDA.
- Reference hardware: NVIDIA RTX 3090 with 24 GB VRAM; lower-memory GPUs have not been validated.
- Validated source language: Polish.
- Reference backend: WhisperX with pyannote speaker diarization.

## Known limitations before the first MVP release

- English and automatic language selection are part of the MVP contract because large-v2 is multilingual. The complete English path, especially word alignment, still requires validation with an English sample before its quality can be characterized.
- The current manually verified quality corpus contains three Polish cases and has no timestamp or diarization annotations. WER/CER are baselined; timestamp accuracy and DER/JER remain to be baselined after the corpus is expanded.
- Subtitle syntax and export constraints are covered automatically, but playback review in the target player or a private YouTube upload is still pending.
- The wheel has passed an isolated offline installation and transcription test on the reference WSL machine. A fresh Ubuntu 24.04 WSL installation test is still pending.
- Explicit CLI grouping, complete `doctor` model-readiness checks, and the final CLI/documentation conformance pass remain release-audit items.

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

Operational WSL2 setup and verification instructions are in [`WSL config/`](WSL%20config/README.md).

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
