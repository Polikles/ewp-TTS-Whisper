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

## Phase 3 mutable-storage validation evidence

On 2026-08-03, commit `292e1ea` passed the target WSL mutable-storage gate:

- a second process was denied while the output lock was held;
- the lock was immediately reusable after release;
- atomic running reservations selected versions 1 and 2 without collision;
- version 1 transitioned from `running` to a complete `failed` record;
- no state temporary file remained;
- an isolated owner-marked workdir was allocated and removed;
- cleanup preserved a sibling model-like file;
- all 122 tests passed and the repository worktree was clean.

Retained external evidence hashes:

```text
68adc3a0d0354f17324e5c00e9f5995ca0eb1919086cbad9756659cb2f87b607  locked-output/.ewp-transcripts.lock
32f6f8e665589a598a552b122aa25080d4e06ec8f5d86fbe0e230b88d62effda  state-output/.ewp-transcripts.lock
f840aee698cb5a730ddaae3e74af2d5e89937e454981181f444644b3d8567e85  state-output/controlled-job_results.failed.json
6d6b48717800d31b217df636ac540b0fc1eaa974e2fef093209dcf9b580238b6  state-output/controlled-job_results_v002.partial.json
8b893f618d203777879e2479dfddc0a758ae742203940cddb74955180aa46469  work-root/model-cache-must-remain/model.bin
```

Lock-file hashes are evidence for this run only because acquisition metadata contains a
PID and timestamp. The retained failed and partial records are controlled mechanics
artifacts, not resumable transcription checkpoints. A later run must restart the job.
