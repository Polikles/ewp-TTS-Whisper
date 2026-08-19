# EWP-transcripts work status

Last updated: **2026-08-19**.

## Current state

Version `0.1.1` is an **internal release candidate** on `main`. It is usable for the
owner's archive, but it is not tagged or published as a public release. The repository
is public and is licensed under `AGPL-3.0-or-later`; the complete license is included in
source and distribution artifacts.

The functional and operational MVP gates are complete:

- all 386 automated checks pass;
- locked installation passed in a fresh Ubuntu 24.04.4 WSL2 distribution;
- installed-wheel transcription passed offline on the RTX 3090;
- realistic Polish inputs through 151 minutes, sequential batches, interruption/restart,
  all advertised formats, grouping topologies, diarization, and exports are accepted;
- short and complete-episode YouTube subtitle readability/timing reviews passed;
- canonical JSON is the immutable source of truth for all derived exports.

Dataset-dependent English, three-speaker, timestamp, and DER/JER quality measurements
remain explicitly deferred by ADR-0014. They are not implementation blockers.

## Authoritative next step

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
from layout-aware program/surround downmix and diarization.

Future cloud and loopback/local LLM APIs require distinct, explicit privacy warnings and
reject, accept-once, or scoped persistent-consent choices. Strict offline mode blocks
cloud endpoints. General-user readiness also requires a top-level `Instructions/`
operator runbook covering every shipped command and workflow.

Do not hand-edit canonical JSON. Preserve each original result and store accepted
corrections as immutable revision snapshots.

## V2 priority order

1. Package the corrected 24-episode corpus as private benchmark evidence and record the
   remaining revision-workflow defects.
2. Implement explicit safe handling for 3+ channel isolated-speaker and program/surround
   topologies.
3. Benchmark and add local/cloud API correction through the same revision engine and
   consent contract.
4. Add manual then automated translation using a separate immutable translation artifact.
5. Add synchronized standalone/embeddable HTML export, including later bilingual output.
6. Consider small project-scoped dictionaries only if benchmarks justify them; do not
   add a global dictionary.
7. Reopen English, three-speaker, timestamp, DER/JER, preset, and hardware gates as
   suitable references become available.

## Repository hygiene

- Current operator documentation lives under `WSL config/`.
- Historical Phase 0–9 and release-validation procedures live under
  `archive/mvp-validation-runbooks/` and are not current user instructions.
- Historical MVP planning documents live under `archive/mvp-planning/`.
- The active product contracts, ADRs, schemas, examples, and V2 roadmap remain under
  `docs/`, `schemas/`, and `examples/`.
