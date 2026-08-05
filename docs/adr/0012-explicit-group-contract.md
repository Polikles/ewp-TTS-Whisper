# ADR-0012: Explicit group identity and validation contract

- Status: accepted
- Date: 2026-08-04

## Decision

Files whose names do not satisfy automatic episode grouping may be forced into exactly
one episode using repeatable `--group FILE` options. An explicit group:

- requires at least two unique regular files;
- requires a caller-supplied, path-safe `--group-id JOB_ID`;
- cannot be combined with positional `INPUT`;
- preserves supplied source order in identity and provenance;
- remains subject to decodability, sample-rate, duration, channel, and speaker validation;
- uses the first listed source directory when `--output-dir` is absent;
- supports exact-filename `--speaker-map` overrides;
- participates normally in signatures, duplicate detection, versioning, exports, state,
  locking, and cleanup.

The application must not guess an output identity from unrelated filenames. This closes
FR-B04 while preventing accidental output-name collisions.

## Evidence

Commit `f8c8fd7` or later passed all 251 automated tests. Coverage includes ordered
explicit discovery, duplicate-path rejection, unsafe group IDs, default and filename
speaker provenance, CLI conflicts, application routing, and all three planning/execution
entry points.

The reference Ubuntu 24.04 WSL2 workstation then executed
[`RUN_RELEASE_EXPLICIT_GROUP.md`](../../archive/mvp-validation-runbooks/RUN_RELEASE_EXPLICIT_GROUP.md)
using the two isolated channels of P2-01 under unrelated filenames:

```text
87b13d0226a27a112c0211483eab1c05dab259c22bc737c1bbc880883d1b6d1c  alpha-track.wav
69471eaad337d9eed36ac0f179fa889e05f58236c5b7181ccbe11b118d0b4886  unrelated-voice.wav
```

Both files were mono PCM at 44.1 kHz and 142.442086 seconds. Inspection created exactly
one `p10-explicit-group` episode. Planning selected version 1 and a controlled call
without `--group-id` failed with the expected argument error.

The complete local-only GPU pipeline produced canonical JSON plus TXT, SRT, and VTT.
The canonical result contained two explicitly labelled sources, 18 segments, 314 words,
and no untimed words. Duplicate replay skipped the result and every export without
leaving a job workspace.

Accepted output hashes:

```text
0906f4cde84e6e7814fdeb895f8339c90b745cb3e3e08fbf4e3d2c14d16eb202  p10-explicit-group_results.json
7568b675d1044eab813c012de43acfff0aeb23690675a8073d63f4119fd986da  p10-explicit-group_subtitles.srt
5d3b0f63492a5f33276fe504afd8c6731f4109adb1385997c318997869b7129d  p10-explicit-group_subtitles.vtt
fa01eec7eba1c041aac83070da10b4521dc383c3caa80919a87ebaa3ac2bea2c  p10-explicit-group_transcript.txt
```

## Consequences

Automatic final-hyphen grouping remains the convenient default and does not require
`--group`. Explicit grouping is a deliberate override for sources that the user knows
share one timeline. Requiring `--group-id` adds a small amount of CLI input in exchange
for deterministic, collision-safe result naming.
