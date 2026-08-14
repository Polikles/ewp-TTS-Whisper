# EWP-transcripts work status

Last updated: **2026-08-05**.

## Current state

Version `0.1.0` is an **internal release candidate** on `main`. It is usable for the
owner's archive, but it is not tagged or published as a public release. The repository
is public; no public license has been selected. `LICENSE_SKETCH.TXT` remains private,
untracked, and excluded from build artifacts.

The functional and operational MVP gates are complete:

- all 285 automated checks pass;
- locked installation passed in a fresh Ubuntu 24.04.4 WSL2 distribution;
- installed-wheel transcription passed offline on the RTX 3090;
- realistic Polish inputs through 151 minutes, sequential batches, interruption/restart,
  all advertised formats, grouping topologies, diarization, and exports are accepted;
- short and complete-episode YouTube subtitle readability/timing reviews passed;
- canonical JSON is the immutable source of truth for all derived exports.

Dataset-dependent English, three-speaker, timestamp, and DER/JER quality measurements
remain explicitly deferred by ADR-0014. They are not implementation blockers.

## Authoritative next step

Begin an internal production pilot on 3–5 representative archive episodes. Follow
`WSL config/USE_CURRENT_MVP.md` and collect structured observations with
`WSL config/FEEDBACK_FOR_V2.md`.

Do not hand-edit canonical JSON. Preserve each original result and keep corrections as
separate review material until the V2 correction-layer contract exists.

## V2 priority order

1. Run the archive pilot and classify recurring correction/review needs.
2. Implement a versioned correction layer anchored to canonical words, speakers, and
   timestamps; regenerate every export from one corrected revision.
3. Add synchronized standalone/embeddable HTML transcript export for the blog player.
4. Convert licensed, manually corrected excerpts into a larger ground-truth corpus.
5. Reopen English, three-speaker, timestamp, DER/JER, preset, and hardware gates as
   suitable references become available.
6. Continue with lower-priority V2 items in `docs/99-roadmap-v2.md`.

## Repository hygiene

- Current operator documentation lives under `WSL config/`.
- Historical Phase 0–9 and release-validation procedures live under
  `archive/mvp-validation-runbooks/` and are not current user instructions.
- Historical MVP planning documents live under `archive/mvp-planning/`.
- The active product contracts, ADRs, schemas, examples, and V2 roadmap remain under
  `docs/`, `schemas/`, and `examples/`.
