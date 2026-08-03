# ADR-0004: SHA-256, Episode Signatures, and Non-Destructive Versioning

- Status: accepted
- Date: 2026-07-29

## Decision

- every file has a SHA-256 hash;
- every group has a deterministic episode signature;
- an existing identical signature is skipped without `--force`;
- `--force` creates `_v002`, `_v003`, and so on;
- the same name with a different signature automatically creates a new version;
- no result is overwritten.

Every file in one output set uses the role-first version convention:

```text
episode_results.json
episode_transcript.txt
episode_results_v002.json
episode_results_v002.partial.json
episode_results_v002.failed.json
episode_transcript_v002.txt
episode_subtitles_v002.srt
episode_subtitles_v002.vtt
episode_segments_v002.json
```

The version suffix follows the output role. Planned files are placed directly in the
resolved output directory; the application does not add per-job subdirectories.

## Consequences

The output directory requires locking during lookup and version allocation.

## Phase 3 dry-run validation evidence

On 2026-08-03, the production `transcriber dry-run` path passed four controlled external
filesystem scenarios using episode signature
`69d2c8f753e9180b9dccf51e02d4b5247c8695ca30606aeb603bcc027e953d29`:

| Scenario | Expected decision | Result |
|---|---|---|
| no existing result | `PROCESS`, version 1 | PASS |
| identical completed signature | `SKIP` with `EXISTING_RESULT_SKIPPED` | PASS |
| identical result plus occupied v2 partial, with `--force` | `PROCESS`, version 3 | PASS |
| same job ID with a different signature | `PROCESS`, version 2 with `SOURCE_NAME_COLLISION` | PASS |

The missing planned destination remained absent, and hashes of all controlled state files
were identical before and after every dry-run. The human report displayed the skip
decision, Polish language, source/speaker mapping, mono channel decision, existing result
path, and structured warning.

External JSON report hashes:

```text
e3a72a3fd88e489d6e473647fde2afa2963f0bd81e826576505728e15b8fe144  collision.json
bc3b27171be9d4a0462486be82c4e81365806a757e5367d6542fa4989ae06944  duplicate.json
d3ba4825760b731c25a741d211cc76b9fbceea21d2cc1cd7339b310c7ad186e8  forced.json
909d3a45b1ef2ec9388a7589f0d9807a19e6211df7ff817e7e477ae6f78cbdbd  new-job.json
```

This validates the read-only planner, not concurrent reservation. The target WSL
workstation passed all 101 tests with a clean worktree. Locking remains required before
mutable result allocation is safe.
