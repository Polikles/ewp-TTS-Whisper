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

## Phase 4 repeated-export validation evidence

On 2026-08-03, the target WSL workstation validated derived-export versioning at commit
`9c00f8c`:

- a first run created TXT, SRT, VTT, and segments JSON at result version 1;
- repeating all four formats without `--force` reported four `SKIP` decisions and left
  every existing file byte-for-byte unchanged;
- repeating with `--force` selected one coordinated version 2 and created all four
  `_v002` paths;
- version-1 and version-2 TXT, SRT, and VTT hashes matched because their content is a
  deterministic transformation of the same canonical transcript and configuration;
- segments hashes differed only because that schema intentionally records the export's
  `generated_at` provenance timestamp;
- the canonical result hash remained
  `6ab17f931db9037d9ca982f7a111336ae931c1ee6368f2a6bcfb0ba575323b0c`;
- no temporary file remained and the repository worktree was clean.

The forced export hashes were:

```text
d3cfbe6df477b47fd6bd9e27ddafc7243e62d622d3813aba5da2df68c6dc22ee  S01E01_segments_v002.json
0c61b0cdf2ff00dcf63ed254b8e3d686613ad32bfadef2d65aef94abcaac5b1d  S01E01_subtitles_v002.srt
7bb305e38d7a5df65c0ec5c83eb6c4398de3b8d8a8fe7f12cd3eaced7844be58  S01E01_subtitles_v002.vtt
16b0993ded8a17bc1bfc934a6c9ea97b3adc5671e36130e25b643e1674d045e3  S01E01_transcript_v002.txt
```

## Phase 5 failed-state restart evidence

On 2026-08-03, the final Phase 5 target gate deliberately configured a nonexistent ASR
snapshot while retaining the correct immutable revision name. The production command:

- exited with the documented application error code 4;
- printed only `Pinned local ASR model snapshot is unavailable`, without a traceback,
  transcript text, token, or internal path discovery;
- atomically replaced running state with a v1 `failed` record using failure code
  `SPEECH_ENGINE_ERROR`;
- created no completed result and left no partial state;
- retained its marker-owned workspace and prepared working WAV for diagnostics.

After changing only the sandbox configuration to the valid local snapshot, the next
offline invocation restarted inspection and inference from the beginning. Because the v1
failed diagnostic occupied that coordinated output set, allocation safely advanced to
v2 without overwriting evidence. The restart published schema-valid canonical JSON plus
TXT/SRT/VTT, with 13 segments and 226 words. A subsequent invocation skipped the v2
result and all exports without model loading. The v1 failed-state hash remained unchanged,
and its workspace was then removed through marker-verified cleanup. No partial, temporary,
or job workdir remained; the WSL worktree was clean.

External evidence hashes:

```text
f1384e7c04300492ad78a946d663c137eacf63f61ebe063e4e804c211c8626ed  p0-01-single-short_results.failed.json
d978cf9745c4b344e4e1d14fd03c57b2289eab0b6a1950915d65e3f8bbc142cf  p0-01-single-short_results_v002.json
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  p0-01-single-short_subtitles_v002.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  p0-01-single-short_subtitles_v002.vtt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  p0-01-single-short_transcript_v002.txt
```

This accepts the Phase 5 rule that failed attempts are immutable diagnostics rather than
resumable checkpoints. A corrected run starts over and uses the first wholly unoccupied
coordinated version.

## Phase 6 sequential batch evidence

On 2026-08-03, the target WSL workstation passed the Phase 6 batch gate at commit
`ea0dcbb` with all 186 repository tests passing:

- dry-run and execution used numeric natural order: `episode2`, then `episode10`;
- two Polish mono jobs ran sequentially and produced schema-valid canonical results with
  226 and 614 words plus all default exports;
- both successful workdirs were cleaned and no failed/partial state remained;
- duplicate replay skipped both canonical results and all six exports without model
  loading or mutation;
- a separate batch processed unsupported mixed stereo first and valid mono second;
- the first job produced sanitized `UNSUPPORTED_PIPELINE_SCOPE_ERROR` failed state;
- the later mono job still completed, proving job isolation and continue-after-error;
- the CLI returned exit code 5 with summary
  `completed=1 skipped=0 failed=1 cancelled=0`;
- the retained failed workspace was removed through marker-verified cleanup;
- no partial or temporary file remained and the repository worktree was clean.

Successful-batch artifact hashes:

```text
8e8cdffd6d41d821c760262129eac283e3da4699f00ddfbd7671af9e7c529e69  episode10_results.json
f4093a4321c8f2df41556dc8a1d09db95457f764678b387e4938194b371003cf  episode10_subtitles.srt
e2e43fc7e49dde3c0a5a128a10d181bde996b04f5cb1190cf60149a1c5cf3ab0  episode10_subtitles.vtt
58e52795a49a2c9cf73b9a189aa5e34fabd0aff7147a15bd592f5c145fafea63  episode10_transcript.txt
1f6ccf1f720d4e516523b0acb5a352efe46d517b1869993833d8dd1acbde4e9e  episode2_results.json
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  episode2_subtitles.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  episode2_subtitles.vtt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  episode2_transcript.txt
```

Controlled partial-failure artifact hashes:

```text
ec6677ee85400f96e7f9991af3340883a0db7f1b16f98d15ca97af5f0138de06  episode10_mono_results.json
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  episode10_mono_subtitles.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  episode10_mono_subtitles.vtt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  episode10_mono_transcript.txt
8a350ee8238decddb8dd6a251d723771656a7d4a1b029446d9651f869f8a6c23  episode2_mixed_results.failed.json
```

This accepts deterministic sequential batching: completed, skipped, and failed jobs have
independent durable state, and one failure does not broaden or corrupt another job's
scope. Cancellation remains covered by automated lifecycle/CLI tests and maps to durable
`cancelled` state plus exit code 6.

## Phase 7 canonical-first recovery and cleanup evidence

The first split-channel and grouped-source runs on 2026-08-04 published their completed
canonical JSON before a derived subtitle-ordering error. As required by the storage
decision, neither result was rolled back, overwritten, or converted into failed canonical
state. Both processes retained their marker-owned workdirs because the complete command
had not succeeded.

After commit `33060f6`, ordinary invocation found the identical episode signatures,
skipped both canonical results, and generated only the missing exports without loading
models. A further duplicate replay skipped all canonical and derived outputs. The two
diagnostic workdirs were then removed using the run IDs and job IDs from their canonical
results plus marker-verified cleanup. No workdir, partial state, temporary file, or
uncommitted repository change remained.

This accepts canonical-first recovery for multi-stream jobs and confirms that recovery
does not implicitly delete an older process's retained diagnostics.

## Phase 9 privacy-oriented workdir cleanup evidence

On 2026-08-04, commit `5449c1b` passed the target WSL cleanup gate with all 217 automated
tests passing. A controlled ten-day-old workspace and a recent workspace were allocated
through the production marker writer beside an invalid marker and a model-like unknown
directory.

- `--older-than 5 --dry-run` selected only the old workspace and removed nothing;
- the confirmed age-filtered command removed exactly that old workspace;
- an unfiltered confirmed command then removed exactly the remaining recent workspace;
- the invalid marker was never trusted or removed;
- the unknown model-like sibling was never selected, and its hash remained
  `9372c470eeadd5ecd9c3c74c2b3cb633f8e2f2fad799250a0f70d652b6b825e4`;
- no result, export, model, configuration, or unowned path was modified.

This accepts the MVP `clean all-workdirs` boundary: exactly one of `--dry-run` or `--yes`
is mandatory, age filtering is based on the ownership marker, and deletion revalidates
ownership immediately before removing each workspace. Retention-reason filters remain
deferred until versioned marker metadata can distinguish failed, cancelled, and
deliberately retained successful jobs.

## Phase 9 production SIGINT and restart evidence

On 2026-08-04, commit `cf12efa` passed a real cancellation gate on the target WSL2 RTX
3090 workstation. A two-job batch started the 50-minute P9-03 recording first. After
pyannote VAD was observed, the recorded transcriber PID received `SIGINT`.

The process:

- exited with the documented cancellation code 6;
- reported `completed=0 skipped=0 failed=0 cancelled=1`;
- durably published `episode01-long_results.failed.json` with status `cancelled`, code
  `USER_CANCELLED`, and result version 1;
- published no final result and left no partial state;
- stopped before the queued `episode02-never-started` job began;
- retained exactly the cancelled job's marker-owned diagnostic workspace;
- emitted no application traceback.

An ordinary offline restart processed the cancelled long job from the beginning as
`episode01-long_results_v002.json`, then processed the previously untouched short job as
version 1. Both canonical results validated, while the cancelled-state hash remained
unchanged. Duplicate replay skipped both completed jobs without model loading, and
marker-safe cleanup removed exactly the retained cancelled workspace.

External artifact hashes:

```text
0dca68a60a1f663b332ec410479f04599b470654efafc209bc4b65705d10bfe6  episode01-long_results.failed.json
0e0600ddf7e76e550207236bf486ad06487cf7d8274383ee993690070b4e099d  episode01-long_results_v002.json
71b95ed3f7e27272f7271ca27362b27b32cec0dd22c796496af1fea333ba76ae  episode02-never-started_results.json
```

The first procedural attempt was stopped by shell job control before application
workspace allocation because the background command inherited terminal stdin. Commit
`cf12efa` corrected the runbook by redirecting stdin from `/dev/null` and by avoiding
interactive-shell `errexit`. The abandoned attempt selected zero owned workspaces during
cleanup and produced no acceptance evidence.
