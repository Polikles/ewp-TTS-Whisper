# Changelog

All notable changes to EWP-transcripts are documented here.

## Unreleased

### Added

- Added the normative v0.3 automated-correction contract: provider-neutral adapters,
  faithful-repair policy, deterministic single-owner chunks with read-only overlap,
  proposed-change validation, scoped API consent, retry/resume/batch behavior, immutable
  revision provenance, private-corpus benchmark requirements, and acceptance checklist.
- Added the first provider-neutral correction primitives: strict request/response/change
  models, deterministic gap-free editable chunking with bounded read-only context, stable
  operation/content hashes, and a network-free deterministic mock provider.
- Added local provider-response verification that rejects wrong operation identities,
  overlapping, unsorted, out-of-range, or source-mismatched proposals and any corrected
  text that cannot be reconstructed exactly from the explicit proposed-change list.
- Connected validated mock responses to ordinary review anchors and the existing
  deterministic revision aligner, producing immutable LLM-provenance snapshots without
  letting providers construct mappings or artifacts. Added explicit `mock` endpoint
  provenance for network-free test revisions.
- Added strict `[correction]` configuration for target, maximum editable, and read-only
  context token counts, including packaged/example defaults and invalid-order rejection.
- Added application-facing mock correction preview and atomic apply operations that use
  resolved configuration, preserve the canonical result, and publish through the existing
  locked revision allocator.

### Documentation

- Clarified that review of the official `uv` installer is optional unless local policy
  requires it, replaced the clone placeholder with the public repository URL, and added
  current dependency/model download and free-space estimates to installation guidance.
- Added a root Requirements section covering the validated WSL2/Ubuntu/RTX 3090 baseline,
  expected but unvalidated Ubuntu deployment shapes, and future per-preset requirements.
- Added a v0.3 backlog item for a reviewable installation and verification script.
- Scoped the v0.3 installer to fresh installations, kept existing-installation updates
  separate, and specified future README Prerequisites, How to install, and How to use
  sections. Standardized storage guidance at a recommended 20 GB minimum (preferably
  SSD) while deferring RAM/VRAM qualification to preset validation.
- Recorded acceptance of the second model-free fresh-WSL installation and postponed
  redundant full model/runtime revalidation until later functional changes require it.
- Assigned automated local/cloud correction and fresh-install onboarding to v0.3; moved
  translation, synchronized HTML export and its acceptance tests, and optional
  project-scoped dictionaries to v0.4. Kept advanced 3+ channel handling in the later
  roadmap without assigning a release.

## 0.2.0 — internal release candidate — 2026-08-19

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
- Added strict transcript-revision configuration and the model-free `revise prepare`
  CLI for single canonical results and deterministic directory batches.
- Added deterministic per-anchor review alignment with merge, split, insertion, deletion,
  punctuation, speaker-reassignment, ambiguity, statistics, and provenance handling.
- Added non-mutating `revise preview` and atomic single-file `revise apply`, with
  `apply --no-apply` using the same validation and alignment path as preview.
- Added deterministic directory preview/apply, recursive opt-in, per-review failure
  isolation, and runtime-configured continue/stop behavior.
- Added safe external-editor review workflow with config/`VISUAL`/`EDITOR` resolution,
  automatic apply after a successful close, and a revision-free `--no-apply` path that
  retains the edited review.
- Added the shared effective-transcript resolver and revision-aware TXT/SRT/VTT/segments
  export through `--revision none|latest|PATH`, with inherited timing, corrected speakers,
  distinct filenames, and revision provenance in segments JSON.
- Added reconstructable base-relative revision audits, standalone `revise audit`, and
  optional `revise apply --audit` publication without making audit data authoritative.
- Added exact parent-revision identity verification, standalone child snapshots, and
  sibling revision behavior that shares a base without implying false lineage.
- Added deterministic revision-aware directory export with compatible revision
  selection, natural result ordering, per-result failure isolation, recursive opt-in,
  safe duplicate replay, aggregate/JSON reporting, and mixed-batch exit code 5.
- Defined future LLM correction as conservative transcription repair rather than prose
  editing, with mandatory proposed-change lists and independently reconstructed audits.
- Defined explicit multichannel topology handling, scoped cloud/local API privacy
  consent, and the complete future `Instructions/` operator-runbook release requirement.
- Defined the input preference order: synchronized mono files per speaker first,
  split-speaker stereo second, and reviewed diarization for mixed program audio. The
  future 3+ channel fallback is automatic only for recognized layouts and uses a
  dedicated topology confirmation—not `--force`—when layout evidence is insufficient.
- Recorded that advanced 3+ channel implementation is deferred to V2 or later. The
  completed 24-episode audio/corrected-transcript corpus remains a private benchmark
  outside Git until all episodes are public and a separate publication review passes.
- Expanded post-0.2 goals for local/cloud correction benchmarks, manual review of model
  revisions, manual/automatic translation lineage, approved project-dictionary candidate
  mining, and synchronized accessible HTML player testing. Added an explicit v0.2.0
  release-closure checklist without importing those later features into its scope.
- Defined private-corpus gold selection: the highest compatible revision is accepted
  gold, while earlier revisions remain intermediate inputs for raw-to-gold and
  revision-to-gold correction benchmarks.
- Closed the v0.2.0 manual-revision acceptance checklist against automated and private
  24-episode operator evidence. Added explicit regression coverage for proper-name and
  sentence-boundary edits, ambiguous alignment, long-gap insertion warnings, repeated
  words, anchor integrity, base immutability, and concurrent revision allocation.
- Added the top-level `Instructions/` operator entry point covering installation links
  and every shipped CLI workflow. Clarified root/revision help discovery and corrected
  batch-capable `export`, `revise preview`, and `revise apply` argument help.
- Added a concise WSL operator runbook for preparing, editing, previewing, applying,
  auditing, exporting, retaining, and recovering transcript revisions.
- Added optional audit publication to the automatic `revise edit` apply path.
- Clarified editor setup with exact project/user configuration paths, a copy-pasteable
  nano workflow, and errors that distinguish editor commands from environment variables.
- Prevented automatic revision creation when an external editor exits without changing
  the review, and documented staged Windows-editor review for long transcripts.
- Clarified that revisions intentionally store corrected token mappings, while corrected
  phrase/speaker segments are materialized as revision-aware derived exports.
- Made staged prepare, manual Windows Notepad editing, apply, and export the primary
  correction runbook; retained `revise edit --editor nano` as an optional shortcut.
- Documented the complete bulk correction workflow: directory preparation, manual
  editing, batch preview/apply with audits, partial-failure handling, safe targeted
  retries, and the current one-result-at-a-time export limitation.
- Made Windows VS Code the preferred manual review editor because its search and
  change-all-occurrences tools accelerate repeated corrections; retained Notepad as a
  small-edit fallback and documented why GUI editors must be opened outside `revise
  edit`.
- Recorded archive-review evidence for incorrect generated-review speaker boundaries
  and a missing review sentence, while distinguishing a log-only alignment hallucination
  from canonical transcript content.
- Accepted the planned v0.2.0 manual transcript-revision contract, including immutable
  full snapshots, `EWP-REVIEW 1`, revision-aware export, schema/example artifacts, and
  the implementation acceptance plan, with automated contract-artifact validation.
- Prioritized the 24-episode corrected corpus, later local/cloud LLM correction, separate
  manual/automated translation pipeline, synchronized HTML export, and optional
  project-scoped dictionaries in the post-0.1 roadmap.

### Validated

- Built the internal 0.2.0 wheel and sdist with synchronized metadata, console entry
  point, packaged defaults, AGPL license, and current source instructions. An isolated
  wheel-provenance smoke test passed prepare, preview, apply, audit, and revised
  TXT/SRT/VTT/segments export without audio or models.
- Passed the first real-episode staged revision pilot using Windows Notepad: review
  preparation, validation, immutable apply, audit, and corrected export completed
  without modifying the canonical result.
- Passed revision-aware bulk export on 24 manually corrected podcast results: all TXT,
  SRT, VTT, and segments outputs were generated (96 artifacts), and duplicate replay
  skipped all 96 without creating new versions.

### Changed

- Export failures now identify the failing format and a fixed allowlist of safe renderer
  invariants while continuing to suppress arbitrary internal or transcript details.
- Invalid review-body directives and text placement now report the exact review-file line
  number, making isolated batch failures directly repairable without reapplying
  successful reviews.
- Source filenames containing whitespace now emit a structured warning and remain
  accepted unchanged when their complete CLI paths are quoted.

### Fixed

- Preserved canonical and timing-derived overlap metadata while projecting corrected
  revision tokens, sorted reconstructed overlapping speaker groups chronologically, and
  interpolated consecutive inserted tokens across bounded canonical gaps. This prevents
  revised subtitle overlap and line-limit failures without changing accepted text or
  canonical timing anchors.
- Restored chronological ordering after final subtitle repartitioning so explicitly
  overlapping speaker cues cannot make SRT/VTT export fail after long silent intervals
  or fallback alignment.
- Prevented plain-text sentence splitting after common abbreviations including `m.in.`,
  `np.`, `tzw.`, and `vs.`.
- Prevented plain-text sentence splitting after `tys.` and address tokens ending in
  `.pl`, `.eu`, `.com`, or `.edu`, including the project domains `etykawpetli.pl` and
  `ethicsintheloop.eu`.

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
