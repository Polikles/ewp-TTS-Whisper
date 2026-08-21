# EWP Transcriber

> EWP-transcripts is a local-first CLI application for accurate transcription of audio recordings. The executable is named `transcriber`.

## Status

- MVP implementation: functional and operational gates complete for the validated Polish workflows; version `0.2.0` remains an internal beta candidate, not a public release.
- MVP reference environment: Windows + WSL2 + Ubuntu + NVIDIA CUDA.
- Reference hardware: NVIDIA RTX 3090 with 24 GB VRAM; lower-memory GPUs have not been validated.
- Validated source language: Polish.
- Reference backend: WhisperX with pyannote speaker diarization.
- The v0.2.0 transcript-revision workflow is implemented and acceptance-audited on
  `main`; local wheel/sdist packaging and model-free installed-wheel validation passed.

## Known limitations before the first MVP release

- English and automatic language selection are part of the MVP contract because large-v2 is multilingual. The complete English path, especially word alignment, still requires validation with an English sample before its quality can be characterized.
- The current manually verified quality corpus contains three Polish cases and has no timestamp or diarization annotations. WER/CER are baselined; timestamp accuracy and DER/JER remain to be baselined after the corpus is expanded.
- Subtitle syntax, readability, and timing passed short and complete-episode YouTube reviews.
- The wheel passed isolated offline transcription, and the complete locked source installation passed in a fresh Ubuntu 24.04 WSL2 distribution.
- Three-speaker and full-English quality validation remain deferred until representative archive-derived material exists.

## Requirements

- Ubuntu 24.04 on WSL2 is the validated environment. Bare-metal Ubuntu and an Ubuntu
  virtual machine with working NVIDIA GPU passthrough are expected deployment shapes but
  have not yet passed the complete release gate.
- An NVIDIA CUDA-capable GPU is required for the current presets. Validation was
  performed on an NVIDIA GeForce RTX 3090 with 24 GB VRAM; minimum hardware requirements
  for future presets have not yet been characterized.
- At least 20 GB of free Linux-filesystem space is recommended, preferably on an SSD.
  This minimum applies across the planned presets; audio inputs and generated results
  require additional space. RAM and VRAM requirements will be validated later and
  documented per preset.

See [`Instructions/README.md`](Instructions/README.md) for the current manual installation
workflow and its approximate download sizes.

## How to install

Create Ubuntu 24.04 under WSL2, install `git`, clone the public repository into the Linux
filesystem, then use the reviewable installer from the checkout:

```bash
sudo apt update
sudo apt install git
mkdir -p "$HOME/transkrypcje"
git clone https://github.com/Polikles/ewp-transcripts.git \
  "$HOME/transkrypcje/ewp-transcripts"
cd "$HOME/transkrypcje/ewp-transcripts"
./scripts/install-fresh-ubuntu.sh --install
```

The script explicitly confirms system changes, installs the locked application
environment, and verifies diagnostics. It does not update an existing checkout or
download gated models. Complete model preparation separately using
[`WSL config/MODEL_SETUP.md`](WSL%20config/MODEL_SETUP.md). Run the read-only verification
again at any time with `./scripts/install-fresh-ubuntu.sh --verify-only`.

## How to use

Transcribe one file or a directory after `doctor` reports model readiness:

```bash
uv run --locked transcriber transcribe "/path/to/input" \
  --output-dir "/path/to/results"
```

The recommended correction workflow stages editable reviews before publishing immutable
revisions:

```bash
uv run --locked transcriber revise prepare "/path/to/results" \
  --output-dir "/path/to/reviews"
uv run --locked transcriber revise preview "/path/to/reviews" \
  --results-dir "/path/to/results"
uv run --locked transcriber revise apply "/path/to/reviews" \
  --results-dir "/path/to/results" --output-dir "/path/to/revisions" --audit
```

See [`Instructions/README.md`](Instructions/README.md) for every command, batch operation,
export mode, recovery path, and automated-correction privacy warning.

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

Start with the complete current CLI operator runbook in
[`Instructions/README.md`](Instructions/README.md). It covers installation links and all
shipped commands, including batch transcription, revision, export, recovery, and cleanup.

The complete index is available in [`docs/README.md`](docs/README.md).

Release history is recorded in [`CHANGELOG.md`](CHANGELOG.md).

Operational WSL2 setup and verification instructions are in [`WSL config/`](WSL%20config/README.md).
The current manual correction workflow is in
[`WSL config/REVISE_TRANSCRIPTS.md`](WSL%20config/REVISE_TRANSCRIPTS.md).

Recommended starting documents:

1. [`docs/01-product-scope.md`](docs/01-product-scope.md) — MVP purpose and boundaries.
2. [`docs/02-requirements.md`](docs/02-requirements.md) — functional and non-functional requirements.
3. [`docs/03-architecture.md`](docs/03-architecture.md) — architecture and processing pipeline.
4. [`docs/05-cli-specification.md`](docs/05-cli-specification.md) — CLI contract.
5. [`docs/07-results-data-model.md`](docs/07-results-data-model.md) — canonical data model.
6. [`docs/12-testing-and-acceptance.md`](docs/12-testing-and-acceptance.md) — tests and acceptance criteria.
7. [`docs/13-transcript-revisions.md`](docs/13-transcript-revisions.md) — implemented v0.2.0 revision contract.
8. [`docs/21-v0.2.0-transcript-revision-plan.md`](docs/21-v0.2.0-transcript-revision-plan.md) — implementation and acceptance plan.
9. [`docs/99-roadmap-v2.md`](docs/99-roadmap-v2.md) — post-0.1 priorities.
10. [`docs/22-v0.3-automated-correction.md`](docs/22-v0.3-automated-correction.md) — accepted v0.3 correction contract and acceptance checklist.

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
