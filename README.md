# EWP Transcriber

> EWP-transcripts is a local-first CLI application for accurate transcription of audio recordings. The executable is named `transcriber`.

## Status

- MVP implementation: functional and operational gates complete for the validated Polish workflows; version `0.1.1` is an internal release candidate, not a public release.
- MVP reference environment: Windows + WSL2 + Ubuntu + NVIDIA CUDA.
- Reference hardware: NVIDIA RTX 3090 with 24 GB VRAM; lower-memory GPUs have not been validated.
- Validated source language: Polish.
- Reference backend: WhisperX with pyannote speaker diarization.

## Known limitations before the first MVP release

- English and automatic language selection are part of the MVP contract because large-v2 is multilingual. The complete English path, especially word alignment, still requires validation with an English sample before its quality can be characterized.
- The current manually verified quality corpus contains three Polish cases and has no timestamp or diarization annotations. WER/CER are baselined; timestamp accuracy and DER/JER remain to be baselined after the corpus is expanded.
- Subtitle syntax, readability, and timing passed short and complete-episode YouTube reviews.
- The wheel passed isolated offline transcription, and the complete locked source installation passed in a fresh Ubuntu 24.04 WSL2 distribution.
- Three-speaker and full-English quality validation remain deferred until representative archive-derived material exists.

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

Release history is recorded in [`CHANGELOG.md`](CHANGELOG.md).

Operational WSL2 setup and verification instructions are in [`WSL config/`](WSL%20config/README.md).

Recommended starting documents:

1. [`docs/01-product-scope.md`](docs/01-product-scope.md) — MVP purpose and boundaries.
2. [`docs/02-requirements.md`](docs/02-requirements.md) — functional and non-functional requirements.
3. [`docs/03-architecture.md`](docs/03-architecture.md) — architecture and processing pipeline.
4. [`docs/05-cli-specification.md`](docs/05-cli-specification.md) — CLI contract.
5. [`docs/07-results-data-model.md`](docs/07-results-data-model.md) — canonical data model.
6. [`docs/12-testing-and-acceptance.md`](docs/12-testing-and-acceptance.md) — tests and acceptance criteria.
7. [`docs/13-transcript-revisions.md`](docs/13-transcript-revisions.md) — accepted planned v0.2.0 revision contract.
8. [`docs/21-v0.2.0-transcript-revision-plan.md`](docs/21-v0.2.0-transcript-revision-plan.md) — implementation and acceptance plan.
9. [`docs/99-roadmap-v2.md`](docs/99-roadmap-v2.md) — post-0.1 priorities.

## Examples and schemas

- [`examples/config.example.toml`](examples/config.example.toml)
- [`examples/results.example.json`](examples/results.example.json)
- [`examples/segments.example.json`](examples/segments.example.json)
- [`examples/review.example.txt`](examples/review.example.txt)
- [`examples/revision.example.json`](examples/revision.example.json)
- [`schemas/results.schema.json`](schemas/results.schema.json)
- [`schemas/segments.schema.json`](schemas/segments.schema.json)
- [`schemas/ewp-review.schema.md`](schemas/ewp-review.schema.md)
- [`schemas/revision.schema.json`](schemas/revision.schema.json)

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

## License

Copyright © 2025–2026 Polikles.

EWP Transcriber is free software licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE)
(`AGPL-3.0-or-later`).

You may use, modify, and redistribute the software, including commercially, subject to
the GNU AGPL. Modified versions remain subject to its copyleft requirements, including
the source-code requirements applicable to modified versions used for remote network
interaction.

The software is provided without warranty, as described in Sections 15 and 16 of the GNU
AGPL. Alternative licensing terms may be available directly from the copyright holder.
