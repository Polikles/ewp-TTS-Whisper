# EWP-transcripts work status

Last updated: **2026-08-14**.

## Current state

Version `0.1.1` is an **internal release candidate** on `main`. It is usable for the
owner's archive, but it is not tagged or published as a public release. The repository
is public and is licensed under `AGPL-3.0-or-later`; the complete license is included in
source and distribution artifacts.

The functional and operational MVP gates are complete:

- all 353 automated checks pass;
- locked installation passed in a fresh Ubuntu 24.04.4 WSL2 distribution;
- installed-wheel transcription passed offline on the RTX 3090;
- realistic Polish inputs through 151 minutes, sequential batches, interruption/restart,
  all advertised formats, grouping topologies, diarization, and exports are accepted;
- short and complete-episode YouTube subtitle readability/timing reviews passed;
- canonical JSON is the immutable source of truth for all derived exports.

Dataset-dependent English, three-speaker, timestamp, and DER/JER quality measurements
remain explicitly deferred by ADR-0014. They are not implementation blockers.

## Authoritative next step

Continue implementing the accepted v0.2.0 transcript-revision contract. Strict immutable
revision models, exact base-result compatibility checks, and anchored alignment are
implemented; the next slice is revision-aware effective transcript/export. Revision
configuration, filename allocation, atomic storage, strict `EWP-REVIEW 1`
parsing/rendering, safe model-free single/batch `revise prepare`, and single-file
single/directory `revise preview`/`revise apply`, and safe external-editor review are
implemented.

Do not hand-edit canonical JSON. Until the revision pipeline is implemented and tested,
preserve each original result and keep corrections as separate review material.

## V2 priority order

1. Implement and test v0.2.0 manual full-snapshot transcript revisions and revision-aware
   exports.
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
