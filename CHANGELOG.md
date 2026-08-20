# Changelog

All notable changes to EWP-transcripts are documented here.

## Unreleased

### Added

- Added the normative v0.3 automated-correction contract: provider-neutral adapters,
  faithful-repair policy, deterministic single-owner chunks with read-only overlap,
  locally derived change validation, scoped API consent, retry/resume/batch behavior, immutable
  revision provenance, private-corpus benchmark requirements, and acceptance checklist.
- Added the first provider-neutral correction primitives: strict request/response/change
  models, deterministic gap-free editable chunking with bounded read-only context, stable
  operation/content hashes, and a network-free deterministic mock provider.
- Added local provider-response verification that rejects wrong operation identities and
  deterministically derives exact insert/delete/replace changes from corrected editable
  text before revision construction.
- Connected validated mock responses to ordinary review anchors and the existing
  deterministic revision aligner, producing immutable LLM-provenance snapshots without
  letting providers construct mappings or artifacts. Added explicit `mock` endpoint
  provenance for network-free test revisions.
- Added strict `[correction]` configuration for target, maximum editable, and read-only
  context token counts, including packaged/example defaults and invalid-order rejection.
- Added application-facing mock correction preview and atomic apply operations that use
  resolved configuration, preserve the canonical result, and publish through the existing
  locked revision allocator.
- Added deterministic non-recursive mock correction batches with natural result ordering,
  preview/apply modes, per-result failure isolation, aggregate counts, and the existing
  continue-or-stop batch policy.
- Hardened resumable correction operation identities with provider, model, prompt,
  language, editable/context bounds, chunk index, and content hash.
- Added private, mode-restricted, immutable per-chunk resume entries. Only fully validated
  responses with an exact provider/model/prompt/operation identity are reused; corrupt or
  stale entries fail before another provider call.
- Added strict hash-bound automated-correction benchmark manifests and lexical reports
  for canonical-to-gold and earlier-revision-to-gold tasks, with exact base-lineage
  validation and no transcript text in reports.
- Wired an explicit resume directory into single and batch correction operations so
  validated chunk responses can be reused without repeating provider calls; preview
  remains write-free when no resume directory is supplied.
- Added a provider-independent correction API consent policy with distinct local/cloud
  warnings, strict-offline cloud blocking, reject/accept-once/persist choices, exact-scope
  reuse, mock bypass, and non-interactive denial by default.
- Added an atomic private consent store containing only exact non-secret scopes, with
  missing-store denial semantics, strict corruption handling, and duplicate suppression.
- Added bounded provider execution with adapter-enforced per-attempt timeouts, explicit
  retryable/permanent failure classes, retry counts, and sanitized latency metrics.
- Provider execution now replaces adapter exception details with stable sanitized errors,
  preventing request text, endpoint details, or credentials from escaping through failures.
- The provider-neutral response contract now carries optional token and micro-USD usage;
  execution outcomes combine it with request, retry, and latency measurements.
- Added the first real provider adapter for LM Studio's OpenAI-compatible loopback API,
  with a faithful-transcript structured prompt, strict JSON parsing, usage capture,
  injectable network-free tests, and rejection of remote or credential-bearing URLs.
- Added disabled-by-default LM Studio correction configuration for exact model/endpoint,
  prompt, chunking, timeout/retry policy, temperature, and private consent-store location.
- Added the production correction application boundary: exact-scope consent is resolved
  and optionally persisted before request construction, configured timeout/retry policy
  is applied, and local/mock provenance records the provider's actual endpoint kind.
- Added `transcriber revise correct` for single-result LM Studio correction with exact
  model/endpoint selection, warning and reject/once/persist consent, preview/apply modes,
  private resumable chunk state, and zero-call rejection behavior.
- Prompt provenance and resume identity now hash the adapter's actual system prompt and
  structured-response schema, preventing stale response reuse after prompt-contract edits.
- Added `transcriber benchmark correction build|report` to create private exact-hash
  bundles, select the latest compatible manual gold, and report separate
  canonical-to-gold, canonical-to-LLM, and gold-to-LLM lexical comparisons without
  transcript text.
- Added correction-specific lexical normalization that excludes balanced parenthetical
  and square-bracket review annotations, preventing manual speaker notes from being
  counted as ASR or LLM errors.
- Tightened the LM Studio correction prompt to v11 after the Qwen 14B v10 pilot scored
  worse than raw ASR against manual gold. Copying is now the default; grammar repair,
  stylistic rewriting, ambiguous edits, and dictionary-free terminology normalization
  are explicitly forbidden.
- Added an explicit LM Studio `json-text` compatibility mode for model/chat-template
  combinations that fail grammar-constrained structured output. JSON Schema remains the
  default; the fallback omits only `response_format`, retains strict whole-response schema
  parsing and all correction safety gates, and has a distinct prompt/resume identity.
- Plain-JSON compatibility requests now include an initialized response template and
  explicitly distinguish immutable task input from the only allowed response keys. This
  prevents unconstrained models from echoing request fields as their response contract.
- Removed the redundant opaque operation ID from the synchronous plain-JSON fallback
  response after Bielik copied it with a one-character mutation. The application binds the
  response locally while retaining exact block count, order, speaker, text, and drift gates.
- Added the correction `output_mode` setting to the editable example configuration and a
  parity regression test; it was already present in packaged defaults and the CLI.
- Removed obsolete per-token metadata from LM Studio requests after a 120-token Qwen 32B
  chunk exhausted an 8K context before completing its JSON response. Speaker-block text and
  bounded context remain provider-visible; exact token identity stays local. The versioned
  wire contract now participates in prompt/resume identity.

### Validation

- The three-case private Bielik 3.0 11B Q8_0 pilot passed the explicit plain-JSON adapter
  contract with no speaker changes. It remained deliberately conservative but scored
  `0.00767339` WER against manual gold versus `0.00747664` for raw ASR, so it does not yet
  pass the correction-quality gate. Private transcript text and artifacts remain outside
  the repository.
- Manual audit classified Bielik's five affected tokens: one correct repair, one still-wrong
  plausible repair, one newly wrong substitution, and a harmful two-word deletion. The
  resulting net two additional word errors exactly account for the measured regression.
- The compact-contract Qwen 2.5 32B three-case pilot completed without warnings and
  improved lexical WER by 1.3% over raw ASR, but took about 36 minutes 41 seconds. Manual
  audit found five useful repairs, two harmful changes, and two context-dependent
  punctuation edits, so a larger-chunk performance/quality pilot is required before any
  full-corpus run.

### Documentation

- Updated v0.3 traceability and acceptance status to distinguish implemented neutral
  infrastructure from provider-dependent prompt, CLI, benchmark, and review work.

- Documented exact LM Studio model discovery, explicit local consent, safe preview/apply
  and resume paths, initial local benchmark candidates, and the deferred OpenRouter stage.
- Updated implementation status after completing LM Studio CLI/consent wiring and exact
  prompt-content provenance; the first real local smoke run remains an operator gate.
- Added benchmark-gated correction preset targets: GTX 1070 as the lowest planned GPU
  validation floor, optional CPU-only operation with 16 GB recommended RAM, and a later
  separate Apple Silicon build with 16 GB unified memory. Recorded candidate model and
  quantization matrices plus rented MacinCloud/Scaleway CLI/GUI validation provenance.
- Made non-loopback LM Studio endpoints explicitly configurable for LAN/VPN/Tailscale-like
  use while retaining loopback by default, exact-scope consent, and an additional network
  warning. Recorded the Qwen 14B Q8_0 32K/18.5 GB VRAM observation and planned Bielik
  Q8_0 versus CPU-offloaded F16 comparison as configuration-specific evidence.
- Added the post-functional public benchmark plan: BIGOS, FLEURS, Common Voice, and
  Multilingual LibriSpeech for lexical evaluation; VoxConverse and AMI for diarization;
  strict split/license/provenance rules; an optional separate general Polish dictionary;
  and a later licensed three-or-more-speaker public-podcast evaluation tier.
- Revised the LM Studio faithful-correction prompt to v2 after the first synthetic smoke
  response failed strict validation. The prompt now defines zero-based half-open token
  spans, verbatim `before` text, exact reconstruction, sorted changes, context exclusion,
  and the required no-change response without weakening local validation.
- Revised the prompt to v3 after Qwen returned a contradictory lexical edit and unchanged
  corrected text. Added deterministic category semantics, explicit final reconstruction,
  and conservative uncertainty rules; punctuation/capitalization/sentence-boundary labels
  can no longer conceal lexical changes.
- Recorded the successful public synthetic LM Studio preview under
  `faithful-correction-v3`: 8 revision tokens, zero warnings, and no publication. Cached
  response reuse and immutable apply subsequently passed without another provider request;
  all generated state and revision artifacts were mode `0600`.
- Added the operator runbook for the local Qwen correction benchmark: private path setup,
  exact input evidence, a short/medium/long pilot, resume-backed immutable publication,
  manual faithfulness review, and gated sequential full-corpus candidate generation.
  Final scoring remains blocked on the operator-facing manifest/report slice.
- Added content-free correction-span mismatch diagnostics (span, token counts, and
  character counts, alternate source positions, and truncated hashes) so private provider
  failures can be investigated without logging transcript text. Documented that Bash
  requires WSL paths even though the application
  accepts Windows paths, and that LM Studio developer logs expose full transcript payloads.
- Recorded the safely rejected three-case Qwen pilot and its observed RTX 3090 load of
  approximately 23.3 GB VRAM at 95%+ utilization; full-corpus execution remains blocked.
- Made both pilot loops stop at the first failed preview or apply instead of proceeding to
  later private-corpus cases.
- Replaced model-counted numeric spans in the LM Studio wire contract with copied stable
  first/last editable token IDs after the private pilot proved a six-position indexing
  error. Prompt v4 maps IDs deterministically back to core half-open spans and still rejects
  unknown/context/reversed IDs, non-verbatim before text, and inconsistent reconstruction.
- Replaced the ambiguous inclusive start/end token-ID pair with an explicit ordered list of
  every changed token ID after Qwen treated the end ID as exclusive. Prompt v5 requires
  non-empty, unique, contiguous editable IDs before the adapter derives a core span.
- Added content-free LM Studio schema diagnostics that report only failing field paths and
  validation error types, never raw response values or transcript payloads.
- Clarified in prompt v6 that every proposed-change object represents one contiguous source
  replacement and that non-adjacent corrections require separate objects. Content-free
  failures now include only the referenced numeric positions and count.
- Added prompt-v7 minimal-span and copy-only-before rules with a concrete generic example
  after Qwen removed punctuation from otherwise correctly addressed source evidence. Exact
  local before-text validation remains unchanged.
- Simplified prompt v8 to one stable start token ID plus verbatim `before` after Qwen copied
  an exact 11-token span but listed only four IDs. The adapter derives one unique contiguous
  end locally and rejects unknown/context starts or unmatched source text.
- Redesigned prompt v9 after both default and 120/160-token pilots proved redundant model
  patch metadata unreliable. LM Studio now returns corrected editable text; the application
  deterministically derives exact insert/delete/replace spans, before/after text, categories,
  speaker mapping, alignment, and audit. Optional provider annotations are advisory only.
- Added prompt-v10 speaker-block round-tripping after a text-only local diff crossed a
  speaker boundary. Block count/order/IDs are immutable and correction changes are derived
  independently inside each block.
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

### Fixed

- Added model-independent automated-correction safety gates: LM Studio speaker blocks
  cannot exceed conservative token-count drift, and revision alignment cannot publish
  any automated speaker reassignment.
- Replaced the quadratic pure-Python lexical scorer with RapidFuzz's exact optimized
  Levenshtein edit operations, allowing long podcast transcripts to produce WER/CER
  correction reports in seconds rather than stalling on character-level comparison.

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
