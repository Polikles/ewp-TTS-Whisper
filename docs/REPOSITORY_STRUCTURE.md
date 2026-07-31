# Repository Structure

## 1. Design principle

`ewp-transcripts` should remain a single Python application organized as a modular monolith. The repository must be easy to navigate for one maintainer, while keeping stable boundaries for a future GUI and Docker packaging.

Do not create every file in this document on day one. Create modules when the corresponding implementation phase begins. The structure below is the intended end state for the MVP.

## 2. Target tree

```text
ewp-transcripts/
├── docs/
├── examples/
├── schemas/
├── src/
│   └── ewp_transcripts/
│       ├── __init__.py
│       ├── __main__.py
│       ├── application.py
│       ├── cli.py
│       ├── config.py
│       ├── discovery.py
│       ├── pipeline.py
│       ├── speakers.py
│       ├── storage.py
│       ├── workdirs.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── enums.py
│       │   └── errors.py
│       ├── media/
│       │   ├── __init__.py
│       │   ├── probe.py
│       │   ├── channels.py
│       │   └── ffmpeg.py
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── protocols.py
│       │   ├── whisperx.py
│       │   └── pyannote.py
│       ├── exporters/
│       │   ├── __init__.py
│       │   ├── transcript.py
│       │   ├── subtitles.py
│       │   └── segments.py
│       └── resources/
│           ├── __init__.py
│           └── default-config.toml
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_discovery.py
│   │   ├── test_channels.py
│   │   ├── test_speakers.py
│   │   ├── test_storage.py
│   │   └── test_exporters.py
│   ├── integration/
│   │   ├── test_inspect.py
│   │   ├── test_dry_run.py
│   │   ├── test_export.py
│   │   └── test_pipeline_mocked.py
│   ├── e2e/
│   │   ├── README.md
│   │   └── test_pipeline.py
│   └── fixtures/
│       ├── README.md
│       └── generate_audio.py
├── scripts/
│   ├── check.sh
│   ├── test_integration.sh
│   ├── test_e2e.sh
│   └── release_check.sh
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .python-version
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
└── uv.lock
```

Files under `docs/`, `examples/`, and `schemas/` are intentionally not described individually here because they already exist and contain the product specification, examples, and data contracts.

## 3. Production package

### `src/ewp_transcripts/__init__.py`

Minimal package entry. It should expose the installed application version and, if needed, a very small stable public API. It must not load configuration, models, CUDA, or perform filesystem operations during import.

### `src/ewp_transcripts/__main__.py`

Supports:

```bash
python -m ewp_transcripts
```

It should delegate directly to the CLI entry function and contain no command definitions or business logic.

### `src/ewp_transcripts/application.py`

Stable application service layer used by both the CLI and the future GUI. It should expose high-level operations such as:

- `doctor`;
- `inspect`;
- `dry_run`;
- `transcribe`;
- `export`;
- `clean`.

It converts interface-level requests into domain operations and returns typed results. It must not print to the terminal, display GUI dialogs, call `sys.exit`, or depend on Typer/Rich.

### `src/ewp_transcripts/cli.py`

Terminal interface and Typer application. It contains command definitions, CLI argument parsing, TTY prompts, progress presentation, result summaries, and exit-code mapping.

It must remain a thin adapter. It must not implement media probing, hashing, grouping, model execution, result serialization, or subtitle generation.

If this module becomes genuinely difficult to navigate, it may later become a `cli/` package. Do not split it pre-emptively.

### `src/ewp_transcripts/config.py`

Configuration models and loading logic. Responsibilities:

- load packaged defaults;
- load user and project TOML files;
- apply CLI overrides;
- validate values;
- expose one resolved configuration object;
- track the effective configuration written into `results.json`.

Precedence:

```text
CLI > explicitly selected configuration > project configuration > user configuration > preset > packaged defaults
```

If configuration becomes too large, split it later into `config/models.py`, `config/loader.py`, and `config/merge.py`.

### `src/ewp_transcripts/discovery.py`

Input discovery and episode grouping. Responsibilities:

- normalize Windows, WSL, and POSIX paths;
- accept a file or directory;
- ignore subdirectories unless recursion is explicitly enabled;
- filter supported or FFmpeg-decodable files;
- natural-sort inputs;
- group `episode-speaker.ext` sources;
- apply the documented speaker-suffix rules;
- calculate SHA-256 per source;
- calculate the deterministic episode signature;
- detect existing matching outputs during planning.

This file may be split only after grouping, fingerprinting, or scanning becomes independently complex.

### `src/ewp_transcripts/pipeline.py`

Main orchestration layer. It coordinates the sequence:

```text
discovery
→ media inspection
→ source validation
→ channel preparation
→ transcription
→ alignment
→ diarization or source-based speaker attribution
→ timeline merge
→ canonical result
→ derived exports
```

The pipeline decides what happens next but delegates each technical operation. It must not duplicate FFmpeg, exporter, storage, or engine implementation details.

### `src/ewp_transcripts/speakers.py`

Speaker-related domain logic. Responsibilities:

- assign stable internal `speaker_id` values;
- assign display labels from explicit parameters, filenames, channel metadata, or defaults;
- normalize diarization clusters to chronological `Speaker1`, `Speaker2`, and so on;
- map source files or channels to speakers;
- merge speaker timelines;
- preserve overlaps when available;
- provide speaker transitions used by TXT/SRT/VTT exporters.

Automatic voice-biometric speaker recognition is outside this module and outside the project scope.

### `src/ewp_transcripts/storage.py`

Persistence of canonical results and output versioning. Responsibilities:

- read and validate existing `*_results.json` files;
- compare stored SHA-256 values and episode signatures;
- skip completed matching results unless `--force` is used;
- allocate `_v002`, `_v003`, and later suffixes consistently for the whole output set;
- write `.partial.json` while processing;
- preserve `.failed.json` after errors;
- atomically promote a completed result to final `*_results.json`;
- validate output against the JSON Schema.

Derived exports are written through exporters, but naming/version selection should remain coordinated with storage.

### `src/ewp_transcripts/workdirs.py`

Temporary workspace lifecycle. Responsibilities:

- choose a Linux-filesystem work root under WSL;
- create one isolated directory per episode run;
- provide paths for extracted and split temporary audio;
- delete temporary data after success;
- retain temporary data after failure;
- support a retain-always mode;
- implement safe cleanup commands;
- never delete model caches, configuration, or final outputs.

This abstraction should work unchanged when the application is later placed in a Docker container.

## 4. Domain package

### `src/ewp_transcripts/domain/__init__.py`

Exports stable domain types for use by the rest of the application. It should not contain implementation logic or import infrastructure libraries.

### `src/ewp_transcripts/domain/models.py`

Typed canonical data models, preferably using Pydantic where serialization and validation are important. Expected models include:

- source file and source group;
- media stream and channel information;
- inspection result;
- warning/diagnostic;
- speaker;
- word and transcript segment;
- overlap interval;
- execution plan;
- job metadata;
- canonical transcription result.

The model structure must match the repository JSON Schemas. Split this file later only if independent model groups become difficult to maintain.

### `src/ewp_transcripts/domain/enums.py`

Closed value sets used throughout the project, for example:

- channel mode;
- language mode;
- speaker source;
- timestamp source;
- job status;
- output format;
- warning code.

Use enums instead of scattering raw string constants through the codebase.

### `src/ewp_transcripts/domain/errors.py`

Controlled application exceptions. Examples:

- invalid configuration;
- unsupported or damaged media;
- missing FFmpeg;
- missing model;
- duration mismatch;
- sample-rate mismatch;
- invalid result JSON;
- transcription or diarization failure.

The CLI and future GUI should convert these exceptions into their own presentation format.

## 5. Media package

### `src/ewp_transcripts/media/__init__.py`

Exports the supported media operations. It should not initialize processes or contain substantive implementation.

### `src/ewp_transcripts/media/probe.py`

Safe ffprobe adapter and normalized media inspection. Responsibilities:

- invoke ffprobe without `shell=True`;
- parse JSON output;
- identify container and codecs;
- list audio streams;
- report duration, sample rate, channel count, and channel layout;
- expose audio-track language/name metadata;
- detect malformed or undecodable inputs;
- produce basic non-destructive audio-quality warnings required by the MVP.

### `src/ewp_transcripts/media/channels.py`

Audio-channel classification. Responsibilities:

- distinguish mono, dual mono, split speakers, mixed stereo, and ambiguous cases;
- calculate correlation and other documented classification signals;
- expose confidence and diagnostics;
- honor an explicitly forced channel mode;
- apply the MVP fallback: ambiguous stereo emits a warning and uses one channel.

The classifier should be independently testable with synthetic fixtures.

### `src/ewp_transcripts/media/ffmpeg.py`

Media transformation adapter. Responsibilities:

- convert input to the working WAV format;
- split stereo channels when required;
- downmix or select one channel for dual-mono/ambiguous input;
- write only to the current workdir;
- preserve original input files unchanged.

All subprocess calls must use argument arrays and provide useful diagnostic errors.

## 6. Engine package

### `src/ewp_transcripts/engines/__init__.py`

Exports engine interfaces and factories. It must not import or initialize torch, WhisperX, or pyannote at module import time.

### `src/ewp_transcripts/engines/protocols.py`

Small structural interfaces for replaceable external engines, primarily:

- transcription/alignment engine;
- diarization engine.

These protocols allow pipeline testing without CUDA and make future model comparison possible. Do not introduce interfaces for ordinary internal modules that are not replaceable boundaries.

### `src/ewp_transcripts/engines/whisperx.py`

WhisperX adapter. Responsibilities:

- lazy dependency import;
- model loading and unloading;
- device and compute-type selection;
- Polish/English transcription;
- word-level alignment;
- conversion from WhisperX-specific structures to domain models;
- fallback metadata for missing word timestamps;
- capture model/library/runtime metadata;
- free VRAM between phases when appropriate.

No other module should depend on WhisperX-specific dictionaries or APIs.

### `src/ewp_transcripts/engines/pyannote.py`

pyannote diarization adapter. Responsibilities:

- lazy dependency import;
- local model discovery;
- explicit error when the model is unavailable;
- optional speaker-count constraints;
- overlap extraction where available;
- conversion to domain speaker intervals;
- offline operation after models are installed.

Token handling belongs to explicit model setup commands, not normal transcription runs.

## 7. Exporter package

### `src/ewp_transcripts/exporters/__init__.py`

Exporter registry and public export functions. It maps requested output formats to their implementation.

### `src/ewp_transcripts/exporters/transcript.py`

Plain-text transcript generation. Rules:

- no timestamps;
- one sentence per line;
- speaker labels only for multi-speaker material;
- label on the first speaker occurrence and after speaker changes;
- preserve meaningful repetition and self-correction;
- do not rewrite or paraphrase canonical text.

### `src/ewp_transcripts/exporters/subtitles.py`

Shared subtitle cue generation and SRT/VTT serialization. Responsibilities:

- segment text on natural linguistic boundaries;
- enforce configurable line count, line length, cue duration, and reading-speed targets;
- avoid cutting words and speaker transitions;
- display a speaker label at the first occurrence and after a change;
- produce accurate SRT and WebVTT timestamps;
- use canonical word/segment timestamps and documented fallbacks.

Split into a package only after cue generation and SRT/VTT serialization become independently large.

### `src/ewp_transcripts/exporters/segments.py`

Optional `*_segments.json` generation. It must derive all data from the canonical result without reading audio or invoking ML models.

## 8. Packaged resources

### `src/ewp_transcripts/resources/__init__.py`

Accesses packaged files through `importlib.resources`, avoiding assumptions about editable installs or repository-relative paths.

### `src/ewp_transcripts/resources/default-config.toml`

Normative runtime defaults. It should contain the same defaults described in documentation, including:

- Polish language;
- channel-mode auto;
- non-recursive directory processing;
- accurate preset;
- output behavior;
- subtitle cue defaults;
- workdir cleanup policy;
- model names and local cache expectations.

## 9. Tests

### `tests/conftest.py`

Shared fixtures and helpers:

- temporary directories;
- test configuration;
- fake transcription and diarization engines;
- canonical result builders;
- GPU/model availability markers;
- external test-dataset location.

### `tests/unit/test_config.py`

Tests defaults, TOML parsing, precedence, validation, and invalid values.

### `tests/unit/test_discovery.py`

Tests file/directory scanning, non-recursive defaults, grouping conventions, speaker suffix rules, SHA-256, and episode signatures.

### `tests/unit/test_channels.py`

Tests synthetic mono, dual-mono, split-speaker, mixed-stereo, and ambiguous channel cases, including forced-mode overrides.

### `tests/unit/test_speakers.py`

Tests speaker IDs, display labels, source priority, chronological normalization, transitions, and overlap representation.

### `tests/unit/test_storage.py`

Tests skip behavior, `--force`, version allocation, atomic result promotion, partial/failed files, and schema validation.

### `tests/unit/test_exporters.py`

Tests sentence layout, repeated-word preservation, speaker labels, subtitle cue limits, timestamps, and segments output.

### `tests/integration/test_inspect.py`

Runs discovery, real ffprobe, validation, and channel classification on small local fixtures.

### `tests/integration/test_dry_run.py`

Tests execution planning, output paths, existing-result detection, version selection, track-selection errors, and warning reporting without running models.

### `tests/integration/test_export.py`

Generates all supported exports from repository example results and validates their structure.

### `tests/integration/test_pipeline_mocked.py`

Runs the full pipeline with fake ML engines but real filesystem, workdir, storage, and exporters.

### `tests/e2e/README.md`

Documents the external dataset, required environment variables, model requirements, expected runtime, markers, and comparison metrics.

### `tests/e2e/test_pipeline.py`

Runs full local GPU tests with FFmpeg, WhisperX, alignment, pyannote where required, canonical results, and derived exports.

### `tests/fixtures/README.md`

Describes fixture purpose, provenance, and licensing. Repository fixtures must be small and must not contain private production recordings.

### `tests/fixtures/generate_audio.py`

Generates small deterministic audio fixtures for mechanics testing: silence, tones, clipping, different lengths, sample rates, dual mono, and distinct stereo channels.

## 10. Local scripts

### `scripts/check.sh`

Fast local quality gate. It should run formatting checks, lint, type checking, unit tests, schema/example validation, and package build.

### `scripts/test_integration.sh`

Runs integration tests requiring FFmpeg and real filesystem operations but not GPU models.

### `scripts/test_e2e.sh`

Runs selected GPU/E2E tests against the external dataset referenced by `EWP_TRANSCRIPTS_TEST_DATASET`.

### `scripts/release_check.sh`

Runs the complete pre-release suite: quality gate, integration, selected E2E, offline smoke test, long-file tests when requested, wheel build, and clean-environment installation smoke test.

## 11. Root files

### `.editorconfig`

Repository-wide encoding, indentation, line-ending, and final-newline rules.

### `.gitattributes`

LF normalization and binary-file handling, especially for any small audio fixtures.

### `.gitignore`

Must exclude virtual environments, Python caches, model caches, tokens, `.env`, workdirs, logs, private audio, generated transcripts, coverage data, and build output.

### `.python-version`

Pins the development Python minor version, expected to be Python 3.12 for the MVP.

### `AGENTS.md`

Normative instructions for coding agents, including scope, architecture boundaries, tests, and definition of done.

### `CHANGELOG.md`

User-visible changes organized by release. It should contain an `Unreleased` section from the beginning.

### `CONTRIBUTING.md`

Local development workflow, branching/commit conventions, required test commands, and expectations for documentation/schema changes.

### `LICENSE`

Project license selected by the repository owner before public release.

### `Makefile`

Memorable local commands wrapping scripts and uv operations. Recommended targets:

```text
sync
check
test
test-integration
test-gpu
test-e2e
test-long
release-check
```

### `README.md`

Project purpose, MVP scope, supported environment, quick start, basic CLI examples, and links to detailed documentation.

### `pyproject.toml`

Single source for package metadata, entry point, dependencies, optional ML dependencies, development groups, build configuration, Ruff, mypy, pytest markers, and coverage settings.

### `uv.lock`

Committed exact dependency resolution. It is required for reproducible development, clean-room testing, and future Docker builds.

## 12. Future additions

### GUI v2

Add a `gui/` package under `src/ewp_transcripts/`. It must call `application.py`, not `cli.py`. Long-running tasks should execute in worker threads or processes appropriate for the chosen GUI framework.

### Docker

Later additions may include:

```text
Dockerfile
.dockerignore
compose.yaml
docker/
```

The core code should not change materially because paths, model locations, workdirs, non-interactive behavior, and tokens are already configuration-driven.

### When to split modules

Split an existing file only when it has independent reasons to change, distinct tests, optional heavy dependencies, a separate public contract, or poor navigability. Do not split files based only on an arbitrary line-count threshold.
