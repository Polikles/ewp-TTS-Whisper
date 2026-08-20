# EWP-transcripts work status

Last updated: **2026-08-19**.

## Current state

Version `0.2.0` is an **internal beta candidate** on `main`. It is usable for the
owner's archive, but it is not tagged or published as a public release. The repository
is public and is licensed under `AGPL-3.0-or-later`; the complete license is included in
source and distribution artifacts.

The functional and operational MVP gates are complete:

- all 400 automated checks pass;
- locked installation passed in a fresh Ubuntu 24.04.4 WSL2 distribution;
- installed-wheel transcription passed offline on the RTX 3090;
- realistic Polish inputs through 151 minutes, sequential batches, interruption/restart,
  all advertised formats, grouping topologies, diarization, and exports are accepted;
- short and complete-episode YouTube subtitle readability/timing reviews passed;
- canonical JSON is the immutable source of truth for all derived exports.

A second clean Ubuntu 24.04.4 WSL2 installation (`Ubuntu-test-repo-ewp`) independently
passed release-runbook steps 0–4 at commit `f7d7b76`: base tools/GPU discovery, locked
sync and package compatibility, all automated checks, 0.2.0 build/help, expected
missing-model diagnostics, and model-free inspect/dry-run/cleanup. The checkout remained
clean. Repeating model download and full transcription on this second VM is intentionally
postponed: those paths already passed on the previous fresh VM, while this run was scoped
to reproducible installation and model-free behavior. Perform a new full fresh-machine
runtime validation after later functional requirements materially change that path.

Dataset-dependent English, three-speaker, timestamp, and DER/JER quality measurements
remain explicitly deferred by ADR-0014. They are not implementation blockers.

## Authoritative next step

The v0.3 automated-correction contract is now defined in
`docs/22-v0.3-automated-correction.md`. Provider-neutral request/response/change models,
the deterministic single-owner chunk planner, network-free mock provider, strict response
reconstruction validator, and mock-to-review-to-revision vertical slice are implemented.
Strict correction chunk configuration, single-file and failure-isolated directory
preview/apply, and private immutable validated resume entries are implemented. Explicit
resume directories are wired through single and batch application paths. Exact-hash
benchmark manifests validate canonical/intermediate/candidate/gold lineage and report
the initial lexical baseline. The pure consent policy now covers distinct local/cloud
warnings, strict offline blocking, and exact-scope persistence without any HTTP adapter.
The atomic private consent store is implemented without credentials. Provider calls now
have bounded explicit retries, adapter timeout budgets, and sanitized operational metrics.
Provider exception details are suppressed at the application boundary. Wiring metrics into
benchmark reports and completing broader artifact payload scans are next. The neutral
response now supports optional input/output token and micro-USD cost accounting. Real
provider selection is now recorded: LM Studio is the first local OpenAI-compatible
backend, with Ollama deferred; OpenRouter follows only after local benchmarks. The LM
Studio adapter and network-free contract tests are implemented, but no real transcript
has yet been sent to it. The generic application path now gates the provider before
request construction and applies configured retries/timeouts. `revise correct` now exposes
single-result LM Studio preview/apply, exact model and loopback endpoint selection,
reject/once/persist consent, and private resumable state. Prompt content and response
schema hashes invalidate stale resume entries. The next gate is a synthetic LM Studio
smoke run followed by local benchmark/report execution. Cloud credentials, API calls,
and cost remain separately gated.
The first local runtime identity is `qwen2.5-14b-instruct`; LM Studio loaded its Q8_0
variant at 32K context using approximately 18.5 GB VRAM on the RTX 3090. The operator's
server uses a Tailscale-like address, so non-loopback endpoints require explicit opt-in
and a stronger warning rather than being silently treated as loopback.
The first synthetic Qwen smoke request reached LM Studio but was safely rejected because
its proposed `before` text did not exactly match the indexed editable source. No validated
resume state or revision was published. The prompt contract is now `faithful-correction-v2`
with explicit index/verbatim reconstruction rules; the same smoke case must be rerun.
The v2 rerun also failed safely: Qwen proposed `transcription.` to `transcriptions.` as
`punctuation` while leaving corrected text unchanged. Prompt v3 now requires a final
reconstruction check and local validation enforces category-compatible edits. Rerun remains
the next gate; contradictory content is not auto-repaired or persisted.
The v3 synthetic preview then passed end to end against the configured LM Studio endpoint:
8 revision tokens, zero warnings, and no published revision. Cached-response reuse and
immutable apply also passed: the same validated response was reused without a second LM
Studio request, and `S01E01_revision_001.json` was published separately from the unchanged
canonical input. Resume, revision, and lock artifacts were all mode `0600`. The synthetic
LM Studio adapter smoke gate is complete. A private-corpus operator runbook now gates the
Qwen baseline behind short/medium/long pilot review before sequential full-corpus candidate
generation. Operator-facing manifest construction and report generation remain the next
implementation slice before final benchmark scores can be claimed.
The first real-corpus Qwen pilot stopped safely on all three cases because provider
`before` spans did not exactly match editable source text. No candidate revisions were
published. Observed runtime load was approximately 23.3 GB VRAM with 95%+ GPU utilization.
Privacy review also confirmed that LM Studio developer logs display full transcript
payloads. A content-free mismatch diagnostic is being added before rerunning only the
shortest case. That diagnostic proved Qwen copied the token at editable position 65 but
reported span 59:60. The LM Studio wire protocol now uses stable inclusive token IDs and
prompt v4; the adapter maps them to validated half-open core spans. Only the shortest case
was rerun, revealing that Qwen treated the declared inclusive end ID as exclusive. Prompt
v5 now requires the explicit ordered list of every changed token ID, eliminating boundary
interpretation entirely. Only the shortest case must be rerun next; the full corpus remains
blocked. The value-free diagnostic showed a structurally valid response that grouped
non-adjacent token IDs into one change. Prompt v6 now defines one contiguous replacement
per object and separate objects for non-adjacent edits. The next response used a correct
contiguous span but removed punctuation inside its `before` audit copy. Prompt v7 now
requires minimal spans and copy-only `before` evidence with a concrete generic example.
The next response copied an exact 11-token source span but listed only four IDs. Prompt v8
now requires one stable start ID plus exact `before`; the adapter derives the unique
contiguous end locally. A 120/160-token small-chunk rerun still selected the wrong start,
proving chunk size was not the root cause. The approved prompt-v9 redesign now requests
corrected editable text only and derives exact changes, categories, speaker mapping, and
revision audit locally, analogous to the existing human-review boundary. The shortest case
produced a local diff crossing a speaker boundary because plain corrected text omitted that
boundary. Prompt v10 now round-trips the exact ordered speaker-block structure and derives
changes independently per block. The shortest case must be rerun; the full corpus remains
blocked.
The traceability matrix now marks each v0.3 requirement as implemented or partial rather
than leaving completed neutral infrastructure labelled merely planned.

The single-episode v0.2.0 revision pilot passed with the staged workflow documented in
`WSL config/REVISE_TRANSCRIPTS.md`: prepare, manual Windows VS Code edit, preview/apply,
audit, and revision-aware export all worked. The minimal workflow is accepted for the
MVP, although manual editing remains intentionally labor-intensive.

The bulk-workflow plan has also passed:

1. Transcribe the selected episode batch and verify that every expected canonical
   `*_results.json` completed successfully.
2. Run non-recursive `revise prepare` on the result directory and verify one distinct
   review per canonical result, with no failed items or naming collisions.
3. Manually correct the prepared `.review.txt` files in Windows VS Code. This is the
   user-input interval; no immutable revisions are created yet.
4. Run directory `revise preview` if desired, then directory `revise apply --audit` with
   explicit results and revision output directories. Verify per-item summaries and
   revision/audit pairing.
5. Run the implemented deterministic revision-aware directory `export` and capture its
   per-result and aggregate outcome.
6. Export corrected TXT/SRT/VTT/segments for the complete batch and verify counts,
   provenance, collision-safe names, and failure isolation.
7. Record usability defects before beginning correction of all 24 podcast episodes.

The first complete archive transcription batch produced 19 completed jobs, 4 valid
duplicate skips, and one post-transcription subtitle-export failure (`S2E8p2`). Its
canonical result and TXT/segments exports are valid; SRT and VTT fail in cue construction.
Long silence in inactive per-speaker tracks is valid input. The exact safe subtitle
invariant was an explicitly overlapping cue shifted 201 ms before its predecessor by
final repartitioning. Final chronological ordering is now restored without removing or
flattening the overlap; archive re-export remains to be verified.

Manual archive review also identified recurring sentence-export breaks after `m.in.`,
`np.`, `tzw.`, and `vs.`; these abbreviations are now handled deterministically.
Silence-associated ASR hallucinations remain an evidence-driven tuning item: do not add
phrase-specific deletion rules, and do not replace isolated-speaker sources with a mixed
recording solely to hide silence. Preserve affected windows for VAD/ASR comparison.

The complete archive review found two revision-preparation defects to reproduce before
v0.2.0 acceptance: some review boundaries moved a few correctly attributed words to the
adjacent speaker, and one sentence was absent from the middle of a speaker block even
though the canonical transcript contained it. The logged Amara.org-style alignment
hallucination did not appear in the canonical transcripts. Treat these as separate
review-rendering evidence; do not add phrase-specific filtering based on the log line.

Steps 1, 2, 4, and 6 require terminal evidence from the owner's WSL/archive environment.
The owner completed all 24 manual revisions. Revision-aware archive export was reproduced
locally against the exact copied canonical/revision pairs after repairing revised overlap,
insertion-gap, and group-order projection: 24 jobs and 96 derived artifacts passed, and
duplicate replay skipped all 96. The owner then completed the corrected archive export
without errors and successfully exercised bulk reapply/re-export after fixing additional
manual typos.

Immutable revision models, exact base-result compatibility, anchored alignment,
configuration, safe model-free single/batch review, effective transcript export,
detailed audit, and parent/sibling full-snapshot lineage are implemented and covered by
automated tests.

Current input behavior now explicitly warns on filename whitespace while preserving the
exact filename. The CLI path must be quoted; spaces are not stripped because doing so
could collapse distinct filenames. Three-or-more-channel media remains a documented
limitation: the current ambiguous fallback can select only channel 0 and must not be
treated as complete. The V2 design separates isolated-speaker multichannel splitting
from layout-aware program/surround downmix and diarization. Separate synchronized mono
files per speaker are the preferred input; split-speaker stereo is second-best, while
ordinary multi-speaker stereo requires manual speaker-attribution review. Recognized 3+
channel layouts will downmix automatically with a prominent warning; unknown layouts
will require a dedicated topology choice rather than overloaded `--force`.

Future cloud and loopback/local LLM APIs require distinct, explicit privacy warnings and
reject, accept-once, or scoped persistent-consent choices. Strict offline mode blocks
cloud endpoints. General-user readiness also requires a top-level `Instructions/`
operator runbook covering every shipped command and workflow.

Do not hand-edit canonical JSON. Preserve each original result and store accepted
corrections as immutable revision snapshots.

## Release priority order

1. Preserve the completed 24-episode audio/corrected-transcript corpus privately outside
   Git and use it for future ASR, preset, correction, and translation benchmarks.
2. In v0.3, benchmark and add local/cloud API correction through the same revision engine
   and consent contract; also deliver the fresh-install verification script and README
   onboarding restructure.
3. In v0.4, add manual then automated translation using a separate immutable translation
   artifact.
4. In v0.4, add and test synchronized standalone/embeddable HTML export, including later
   bilingual output.
5. In v0.4, consider small project-scoped dictionaries only if benchmarks justify them.
   Later public-corpus work may separately evaluate an optional, disabled-by-default
   general Polish dictionary derived from licensed training splits without contaminating
   held-out WER evaluation.
6. Reopen English, three-speaker, timestamp, DER/JER, preset, and hardware gates as
   suitable references become available.
7. Keep guarded 3+ channel isolated-speaker and program/surround handling in the later,
   release-unassigned backlog; it is explicitly not a current priority.
8. After functional requirements, qualify correction presets: a GTX 1070 low-VRAM floor,
   optional 16 GB RAM CPU-only operation, and a separate optional 16 GB unified-memory
   Apple Silicon build tested on rented MacinCloud and/or Scaleway hardware. Candidate
   model/quantization matrices are recorded in `docs/99-roadmap-v2.md`; none are current
   support claims.
9. After functional and private-benchmark completion, add pinned public-corpus tables:
   BIGOS, FLEURS, Common Voice, and Multilingual LibriSpeech for lexical evaluation;
   VoxConverse and AMI for diarization; and only later an optional licensed/manual-gold
   tier of long three-or-more-speaker public podcast discussions.

## v0.2.0 release closure

Do not expand v0.2.0 with LLM correction, dictionaries, translation, HTML, or 3+ channel
support. Before declaring the manual-revision increment complete:

1. [completed] Reconcile the stale v0.2.0 acceptance checklist against implemented
   automated tests and the completed 24-episode operator evidence.
2. [completed] Add tests for real uncovered invariants: proper-name and sentence-boundary
   edits, ambiguity and long-gap warnings, repetition preservation, anchor integrity,
   base immutability, and concurrent revision-number allocation.
3. [completed] Update remaining documentation from “planned” to “implemented” where
   appropriate and ensure root, revision, and command-specific `--help` match the
   accepted workflow.
4. [completed] Create the top-level `Instructions/` operator runbook covering every
   shipped command, including complete batch revision and revised-export recovery.
5. [completed] Bump package/version metadata to `0.2.0`, update the lock and changelog
   release entry, build wheel and sdist, and validate their contents/provenance.
6. [local portion completed] Run the automated and integration gates and an isolated
   installed-wheel smoke test for model-free prepare/preview/apply/audit and
   revision-aware TXT/SRT/VTT/segments export. A clean/fresh-WSL install with independently
   resolved locked CUDA dependencies remains external operator validation.
7. keep the release internal unless a separate decision explicitly authorizes tagging or
   public package publication.

Local 0.2.0 artifacts were built successfully. The wheel reports installed provenance
from its temporary `site-packages`, includes the console entry point, packaged defaults,
and AGPL license, while the sdist includes the license, project metadata, current
`Instructions/`, schemas, examples, source, and tests. The model-free installed-wheel
revision round trip and all four corrected exports passed. The sandbox could not perform
a fully isolated offline dependency install because its uv cache lacks the pinned CUDA
Torch wheels; do not misclassify that cache limitation as fresh-install acceptance.

Do not add the private corpus to Git merely because it exists. After every episode is
public, conduct a separate licensing, privacy, artifact-size, and distribution review
before adding any benchmark media or transcripts to the repository.

The private package currently contains 24 canonical results, 24 reviews, two immutable
revisions plus audits per result, and both revision generations of all four revised
exports. Runtime lock files have been removed. For future manifests, revision 002 is the
current accepted gold for every episode; revision 001 remains an intermediate benchmark
input. Benchmark both canonical-to-gold and revision-001-to-gold correction, resolving
lineage by base hash and revision number rather than timestamps.

## Repository hygiene

- Current operator documentation lives under `WSL config/`.
- Historical Phase 0–9 and release-validation procedures live under
  `archive/mvp-validation-runbooks/` and are not current user instructions.
- Historical MVP planning documents live under `archive/mvp-planning/`.
- The active product contracts, ADRs, schemas, examples, and V2 roadmap remain under
  `docs/`, `schemas/`, and `examples/`.
