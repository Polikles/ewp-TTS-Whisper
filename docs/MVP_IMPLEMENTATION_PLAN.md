# MVP Implementation Plan

## 1. Delivery approach

Build the MVP as sequential vertical slices. Each phase must leave the repository in a usable, tested state. Do not begin the next phase until the current phase exit criteria are met.

The order is designed to reduce risk:

1. prove the dependency stack;
2. establish contracts and tooling;
3. implement all non-ML behavior;
4. integrate the simplest ASR path;
5. add complex input topologies;
6. add diarization last;
7. harden with the external dataset and long-duration tests.

## Phase 0 — Dependency and GPU spike

### Goal

Prove that the selected Python, PyTorch, CUDA, WhisperX, alignment, pyannote, FFmpeg, and model versions work together under the target WSL2 environment.

### Work

- create a temporary spike branch or isolated script outside the production package;
- confirm Python 3.12 and uv environment creation;
- confirm `nvidia-smi` and `torch.cuda.is_available()`;
- transcribe a short Polish recording;
- run word-level alignment;
- run diarization on a short multi-speaker recording;
- verify model use after network access is disabled;
- observe peak VRAM and model unloading behavior;
- identify required environment variables and model-cache locations;
- lock the working dependency set in `uv.lock`.

### Deliverables

- documented compatible dependency set;
- initial `uv.lock`;
- short technical note with CUDA/model setup assumptions;
- reusable GPU smoke case or test fixture reference.

### Exit criteria

- transcription, alignment, and diarization each run successfully on the RTX 3090;
- a second run works offline after explicit setup;
- no production architecture is based on unverified library assumptions.

## Phase 1 — Repository scaffold and quality gate

### Goal

Create the smallest production package with local quality tooling and stable entry points.

### Work

Create only the files needed now:

```text
src/ewp_transcripts/
├── __init__.py
├── __main__.py
├── application.py
├── cli.py
├── config.py
├── domain/
│   ├── __init__.py
│   ├── models.py
│   ├── enums.py
│   └── errors.py
└── resources/
    ├── __init__.py
    └── default-config.toml
```

Also create:

- `pyproject.toml`;
- `.python-version`;
- `.gitignore`;
- `.editorconfig`;
- `.gitattributes`;
- `Makefile`;
- `scripts/check.sh`;
- initial tests;
- CLI `--help` and `--version`;
- a lightweight `doctor` command.

### Deliverables

- installable package;
- `transcriber` entry point;
- local quality gate;
- basic configuration loading;
- typed error and result foundations.

### Exit criteria

The following succeed:

```bash
uv sync --locked
uv run transcriber --help
uv run transcriber --version
uv run transcriber doctor
make check
uv build
```

`--help`, `--version`, and `doctor` must not initialize CUDA models.

## Phase 2 — Input discovery and media inspection

Status: **complete and validated on 2026-08-03**.

### Goal

Implement `inspect` without any ASR or diarization dependency.

### Work

Add:

- `discovery.py`;
- `media/probe.py`;
- `media/channels.py`;
- supporting domain models and tests.

Implement:

- single file and directory input;
- non-recursive default;
- explicit recursive mode;
- natural sorting;
- Windows/WSL/POSIX path normalization;
- media probing by content, not extension alone;
- multiple-audio-track detection;
- SHA-256 per source;
- `episode-speaker.ext` grouping rules;
- episode signature;
- duration and sample-rate validation;
- channel classification;
- basic audio-quality warnings;
- planned output base names.

### Deliverables

`ewp-transcripts inspect <input>` produces a structured and human-readable report.

### Exit criteria

- all documented source/grouping cases are covered by unit tests;
- real ffprobe integration tests pass;
- ambiguous stereo warns and selects one channel in the plan;
- grouped files follow the 100 ms warning and 500 ms rejection policy;
- no source file is modified.

## Phase 3 — Dry-run, workdirs, storage, and versioning

Status: **complete and validated on 2026-08-03**.

### Goal

Make the complete execution plan deterministic before adding models.

### Work

Add:

- `workdirs.py`;
- `storage.py`;
- `dry_run` application/CLI behavior.

Implement:

- default output directory rules;
- workdir allocation under the Linux filesystem;
- existing result discovery;
- SHA/episode-signature comparison;
- skip behavior without `--force`;
- `_v002`, `_v003` allocation with `--force`;
- separate override for duration mismatch;
- `.partial.json`, `.failed.json`, and final naming policy;
- safe cleanup operations;
- dry-run summary of process/skip/error decisions.

### Deliverables

`ewp-transcripts dry-run <input>` reports exactly what a real run would do without creating work audio or loading models.

### Exit criteria

- version allocation and skip policy have full unit coverage;
- dry-run output matches documented output paths;
- cleanup cannot delete final outputs or model caches;
- interruption/failure state models are defined and tested;
- integration tests pass with real filesystem operations.

## Phase 4 — Canonical result model and derived exporters

### Goal

Complete the output side before connecting ASR.

### Work

Implement canonical domain models matching `results.schema.json` and optional `segments.schema.json`.

Add:

- `exporters/transcript.py`;
- `exporters/subtitles.py`;
- `exporters/segments.py`.

Implement:

- canonical result serialization and schema validation;
- reading canonical example results;
- plain TXT generation;
- sentence-per-line behavior;
- speaker labels at first occurrence and after changes;
- SRT and VTT cue generation;
- configurable cue defaults;
- optional segments export;
- `export` command that never loads models or reads source audio;
- output version behavior for repeated export operations.

### Deliverables

From an existing example `*_results.json`, the application can generate valid TXT, SRT, VTT, and optional segments output.

### Exit criteria

- example results validate against the schema;
- all exports pass unit and integration tests;
- subtitle constraints and speaker-label behavior are tested;
- export works with CUDA unavailable;
- no exporter depends on WhisperX/pyannote structures.

## Phase 5 — Single-file, single-speaker transcription

### Goal

Deliver the first real end-to-end transcription path with minimal branching.

### Supported path

- one audio file;
- mono or one selected working channel;
- explicit `speaker_count = 1`;
- default Polish language;
- no diarization;
- canonical result plus requested exports.

### Work

Add:

- `media/ffmpeg.py`;
- `engines/protocols.py`;
- `engines/whisperx.py`;
- initial `pipeline.py`.

Implement:

- working WAV preparation;
- lazy WhisperX model loading;
- transcription;
- word-level alignment;
- missing-timestamp fallback metadata;
- one deterministic speaker;
- model/runtime metadata;
- stage timings;
- partial/failed/final result lifecycle;
- temporary file cleanup after success;
- retained workdir after failure;
- exports after canonical result completion.

### Deliverables

A real Polish single-speaker file can be processed from CLI to final outputs.

### Exit criteria

- GPU smoke test passes;
- canonical result validates against schema;
- output can be regenerated with `export` without ASR;
- a failed run produces diagnostic failed state and restarts from the beginning next time;
- completed matching SHA is skipped;
- forced rerun creates `_v002` consistently.

## Phase 6 — Batch processing

### Goal

Support production directory processing while still avoiding speaker diarization complexity.

### Work

Implement:

- directory batch execution;
- one episode at a time;
- continue-after-error behavior;
- final completed/skipped/warnings/failed summary;
- cancellation behavior and cancelled state;
- natural processing order.

### Deliverables

The application can process a directory of independent single-speaker audio files predictably.

### Exit criteria

- one failed episode does not corrupt or stop unrelated jobs unless explicitly configured later;
- exit codes correctly represent partial batch failure;
- batch summaries are deterministic;
- no GPU jobs run concurrently in the MVP.

## Phase 7 — Multiple synchronized sources and stereo modes

### Goal

Support edited podcast timelines with one speaker per file or channel.

### Work

Implement:

- grouped mono sources with one speaker per source;
- speaker labels from explicit parameters and filenames;
- fallback labels;
- split-speaker stereo;
- dual-mono one-channel behavior;
- ambiguous-stereo warning/fallback;
- explicit channel-mode override;
- independent per-source/channel transcription;
- shared-timeline merge;
- overlap preservation when both sources are active;
- no cross-channel transcript deduplication in the MVP.

### Deliverables

A grouped episode or split-speaker stereo file produces one canonical episode result and merged exports.

### Exit criteria

- source duration and sample-rate policies are enforced;
- speaker attribution is deterministic;
- overlaps are represented in canonical JSON;
- TXT/subtitles change labels correctly at speaker transitions;
- grouped episode SHA/signature and versioning are correct;
- required E2E topology cases pass.

## Phase 8 — Mixed-source multi-speaker diarization

### Goal

Support one mono/dual-mono/mixed-stereo source containing multiple speakers.

### Work

Add:

- `engines/pyannote.py`;
- diarization branch in the pipeline.

Implement:

- optional exact speaker count;
- automatic speaker-count mode;
- diarization intervals and overlap metadata;
- chronological normalization to `Speaker1`, `Speaker2`, etc.;
- word/segment speaker assignment;
- documented fallbacks when assignment is uncertain;
- clear diagnostics for missing local model or unavailable gated access;
- offline runtime after explicit model setup.

### Deliverables

Mixed multi-speaker audio produces speaker-attributed canonical results and readable exports.

### Exit criteria

- diarization model is not loaded for source-based speaker paths;
- multi-speaker E2E cases pass;
- overlap limitations are documented and represented honestly;
- no automatic person recognition is present;
- full result schema and export tests pass.

## Phase 9 — Hardening, quality evaluation, and MVP release gate

### Goal

Demonstrate that the program is stable, reproducible, and useful on the target corpus.

### Work

- connect the external public test dataset;
- implement quality-report tooling or test helpers;
- measure WER/CER on manually corrected references;
- measure timing accuracy on selected annotated words/segments;
- measure diarization quality where annotated;
- validate subtitle constraints and manually review selected outputs;
- benchmark the accurate preset on RTX 3090;
- run files from minutes to approximately three hours;
- run sequential jobs and interruption/restart tests;
- validate offline execution;
- run clean-room WSL/VM installation from the locked dependencies;
- install and smoke-test the built wheel;
- complete user-facing setup and known-limitations documentation;
- update changelog and version.

### Deliverables

- archived acceptance-test report;
- documented default-preset performance and resource use;
- complete local release procedure;
- MVP release candidate.

### Exit criteria

All criteria in `docs/TESTING_STRATEGY.md` section “MVP test completion criteria” are satisfied, and the project’s existing MVP requirements checklist is complete.

## 2. Recommended milestone versions

A practical pre-1.0 sequence:

```text
0.1.0  repository scaffold and doctor
0.2.0  inspect and dry-run
0.3.0  canonical results and exporters
0.4.0  single-speaker GPU transcription
0.5.0  batch and synchronized sources
0.6.0  stereo modes and timeline merge
0.7.0  diarization
0.8.0  external dataset and quality tooling
0.9.0  release candidate and long-duration hardening
1.0.0  MVP acceptance criteria satisfied
```

Versions are optional planning aids, not a substitute for phase exit criteria.

## 3. Implementation-order constraints

Do not:

- implement GUI before `application.py` is stable;
- implement Docker before paths, secrets, and non-interactive behavior are configuration-driven;
- implement diarization before the deterministic source-based speaker paths work;
- implement full ASR before inspect/dry-run/storage behavior is stable;
- tune subtitle output against live WhisperX output before exporter tests work from fixed canonical JSON;
- add denoising, LLM correction, or dataset generation during the MVP phases;
- introduce a workspace or multiple packages unless independent distribution becomes a real requirement.

## 4. Agent task sizing

Each coding-agent task should target one bounded deliverable with explicit tests. Good examples:

- add configuration precedence and tests;
- add episode grouping rules and tests;
- implement ffprobe normalization for audio metadata;
- add `_v002` output-set allocation;
- generate TXT from canonical result;
- add cue segmentation for reading-speed limits;
- implement the single-speaker WhisperX adapter;
- add source-based speaker timeline merge.

Avoid broad tasks such as “implement the whole pipeline” or “finish transcription support.”
