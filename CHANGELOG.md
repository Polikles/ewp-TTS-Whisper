# Changelog

All notable changes to EWP-transcripts are documented here.

## Unreleased

### Added

- Expanded the future GUI backlog with explicit About, License, and Source Code sections,
  including a direct link to the public repository.
- Licensed the project under GNU AGPL v3.0 or later, included the full license in source
  and distribution artifacts, and documented contribution and warranty terms.
- Added the first v0.2.0 implementation slice: strict immutable transcript-revision
  domain models, artifact loading, and exact canonical-base compatibility validation.
- Added locked revision-number allocation and atomic, no-overwrite publication with
  base-result-version-aware filenames.
- Added strict `EWP-REVIEW 1` parsing and deterministic rendering with directive escaping,
  extension-header preservation, and stable base/anchor/speaker validation errors.
- Added model-free review preparation from completed canonical results, with complete
  segment-boundary anchors and speaker-turn preservation.
- Added locked, non-destructive review-file publication and an application-facing
  single-file review preparation operation.
- Added deterministic non-recursive result discovery and isolated batch review
  preparation with the configured continue/stop policy.
- Accepted the planned v0.2.0 manual transcript-revision contract, including immutable
  full snapshots, `EWP-REVIEW 1`, revision-aware export, schema/example artifacts, and
  the implementation acceptance plan, with automated contract-artifact validation.
- Prioritized the 24-episode corrected corpus, later local/cloud LLM correction, separate
  manual/automated translation pipeline, synchronized HTML export, and optional
  project-scoped dictionaries in the post-0.1 roadmap.

## 0.1.1 — internal release candidate — 2026-08-14

Backward-compatible operator and transcription fixes found during the fresh-WSL archive
pilot.

### Changed

- Replaced the implementation-era work status with the current internal-candidate
  status and V2 agenda.
- Consolidated live WSL documentation around fresh installation, current MVP operation,
  and actionable V2 feedback; historical validation material now lives under
  `archive/`.
- Top-level CLI help now points users to `transcriber COMMAND --help` for
  command-specific options.
- Standardized commit and pull-request titles as `<type>(<scope>): <summary>`.

### Fixed

- Missing-model diagnostics now point directly to `WSL config/MODEL_SETUP.md`.
- Windows drive paths are normalized before CLI file/directory dispatch and output-path
  planning, so directory transcription correctly uses the batch workflow.
- An omitted `--speaker-count` now preserves the configured `auto` default instead of
  silently forcing one speaker; `--speaker-count 1` remains the explicit fast path.
- Accepted Lightning checkpoint-migration, pyannote TF32-reproducibility, and pyannote
  short-window pooling notices are narrowly suppressed across the operations that emit
  them; unrelated backend warnings remain visible.

### Validated

- 289 automated formatting, linting, typing, unit, integration, schema, documentation,
  and traceability checks.
- Windows-path directory batch dispatch and output placement.
- Automatic and exact-count speaker selection, including a real two-speaker mono rerun.

## 0.1.0 — internal release candidate — 2026-08-05

Initial functional MVP release candidate.

### Added

- Local-first `doctor`, `inspect`, `dry-run`, `transcribe`, `export`, and `clean`
  commands with a CLI-independent application boundary.
- Deterministic single-file, natural-order directory, filename-derived, and explicit
  collision-safe group discovery.
- Conservative mono, dual-mono, split-speaker, mixed-stereo, and ambiguous-channel
  classification with explicit overrides and warning-only audio diagnostics.
- Offline pinned WhisperX large-v2 ASR, Polish/English alignment selection, pyannote
  diarization, chronological speaker normalization, and overlap provenance.
- Schema-versioned canonical JSON with integer-millisecond timestamps, timestamp-source
  provenance, source hashes, model revisions, effective configuration, stage timing,
  VRAM metrics, structured warnings, and sanitized failures.
- Regeneratable TXT, sentence-level segments JSON, and readability-balanced SRT/VTT.
- Atomic partial/failed/final state transitions, signature-based duplicate skipping,
  versioned forced reruns, output locking, interruption recovery, sequential batch
  isolation, and marker-verified privacy cleanup with age filtering.
- Manifest-driven WER/CER reports and error-only review diffs.
- Reproducible locked CUDA 12.8 dependency graph and Python 3.12 wheel/sdist packaging.

### Validated

- 279 automated formatting, linting, typing, unit, integration, schema, documentation,
  and traceability checks.
- WAV at 44.1/48 kHz, MP3, FLAC, M4A/AAC, Ogg/Opus, dual mono, split speakers,
  separate mono sources, mixed overlap, clipping, imbalance, long silence, fast speech,
  light recorder noise, and repeated intro/outro material.
- Polish recordings from 95 seconds through 151 minutes on an RTX 3090 under Ubuntu
  24.04 WSL2, including ten-job batch stability and real SIGINT restart.
- Short and complete 34.7-minute YouTube SRT/VTT readability and timing reviews.
- Offline installed-wheel transcription and locked installation in a fresh Ubuntu
  24.04.4 WSL2 distribution.

### Known limitations and deferrals

- Quantitative English, Polish/English code-switch, and three-speaker quality remains
  deferred until representative archive-derived references exist. The `pl`, `en`, and
  `auto` execution modes are implemented.
- Timestamp accuracy and DER/JER lack manually annotated reference data; provenance and
  structural behavior are covered, but quantitative thresholds are deferred.
- The lexical corpus contains only three manually verified Polish cases and is not yet
  statistically representative.
- Arbitrary FFmpeg-decodable extensions work as direct files; content-aware discovery of
  arbitrary-extension files inside directories is deferred to V2.
- Transcription correction, synchronized HTML, speaker-colored web presentation, and
  source-aware subtitle editing are V2 workflow items.
- The accurate preset is validated only on the reference RTX 3090; lower-memory GPUs do
  not yet have supported presets or performance claims.

### Distribution note

This version is for internal use and is not a public release. No public license is
declared in this release candidate. The private
`LICENSE_SKETCH.TXT` draft is deliberately excluded from both wheel and source
distribution artifacts. Do not create or push a public version tag, publish a hosted
release, or distribute artifacts for third-party use until the owner decides the
application is ready and chooses and commits the intended license terms.
