# EWP-transcripts work status

Last updated: **2026-08-14**.

## Current state

Version `0.1.1` is an **internal release candidate** on `main`. It is usable for the
owner's archive, but it is not tagged or published as a public release. The repository
is public and is licensed under `AGPL-3.0-or-later`; the complete license is included in
source and distribution artifacts.

The functional and operational MVP gates are complete:

- all 368 automated checks pass;
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
`WSL config/REVISE_TRANSCRIPTS.md`: prepare, manual Windows Notepad edit, preview/apply,
audit, and revision-aware export all worked. The minimal workflow is accepted for the
MVP, although manual editing remains intentionally labor-intensive.

Resume with this bulk-workflow plan:

1. Transcribe the selected episode batch and verify that every expected canonical
   `*_results.json` completed successfully.
2. Run non-recursive `revise prepare` on the result directory and verify one distinct
   review per canonical result, with no failed items or naming collisions.
3. Manually correct the prepared `.review.txt` files in Windows Notepad. This is the
   user-input interval; no immutable revisions are created yet.
4. Run directory `revise preview` if desired, then directory `revise apply --audit` with
   explicit results and revision output directories. Verify per-item summaries and
   revision/audit pairing.
5. Add and test deterministic directory/batch support for revision-aware `export` before
   the operator bulk-export test; the current `transcriber export` command accepts one
   canonical result at a time.
6. Export corrected TXT/SRT/VTT/segments for the complete batch and verify counts,
   provenance, collision-safe names, and failure isolation.
7. Record usability defects before beginning correction of all 24 podcast episodes.

Steps 1, 2, 4, and 6 require terminal evidence from the owner's WSL/archive environment.
Step 3 requires the owner's manual transcript corrections. Step 5 is repository work and
does not require user input unless a new product decision appears.

Immutable revision models, exact base-result compatibility, anchored alignment,
configuration, safe model-free single/batch review, effective transcript export,
detailed audit, and parent/sibling full-snapshot lineage are implemented and covered by
automated tests.

Do not hand-edit canonical JSON. Preserve each original result and store accepted
corrections as immutable revision snapshots.

## V2 priority order

1. Complete bulk revision-aware export and validate the full v0.2.0 batch correction
   workflow.
2. Manually revise all 24 podcast episodes to create the first ground-truth corpus and
   record revision-workflow defects.
3. Benchmark and add local/cloud API correction through the same revision engine.
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
