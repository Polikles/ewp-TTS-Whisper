# State, Errors, Logging, and Versioning

## 1. Working directory

Every job receives a directory in the WSL filesystem, for example:

```text
~/.cache/ewp-transcripts/work/<run_id>/<job_id>/
```

It may contain decoded WAV files, extracted channels, raw backend output, and diagnostic artifacts.

- after success: remove unless `--keep-temp` is used;
- after failure or cancellation: preserve;
- only final results are written to the output directory.

Allocation creates an owner-only `<work_root>/<run_id>/<job_id>/` directory with a small
ownership marker. Cleanup accepts only the exact typed workspace returned by allocation,
requires the marker to match its run and job identity, rejects symlinks, and removes only
that job directory. It never recursively removes the work root, run root, output
directory, model cache, or siblings.

## 2. Atomic writes

1. Create the work directory.
2. Write state to `_results.partial.json.tmp`.
3. Flush and `fsync` when available.
4. Rename to `_results.partial.json`.
5. After success, create a final temporary file in the destination directory.
6. Validate it against the schema.
7. Atomically rename it to `_results.json`.

The Phase 3 reservation implementation publishes the initial running state with an
exclusive same-filesystem hard link from a fully written and `fsync`ed temporary file.
This provides no-overwrite semantics unavailable from a normal replacing rename. The
directory is then `fsync`ed before the temporary link is removed. Reservation is planned
again while holding the output-directory lock, so a stale dry-run decision is never used
for mutation.

On filesystems or mounts without reliable atomic rename semantics, the implementation must emit a warning and use a safe copy-and-verify strategy.

## 3. Existing-result lookup

The application searches the output directory for `results*.json` and compares `episode_signature_sha256`.

### Same signature

- without `--force`: warning and SKIP;
- with `--force`: create `_v002`, `_v003`, and so on.

### Same job ID, different signature

A new version is created automatically because the source differs. The application emits a source-name collision warning.

### Same signature, different source filename

This is still a duplicate. Without `--force`, the job is skipped and the existing result is reported.

## 4. Version allocation

- no suffix means version 1;
- the first additional version is `_v002`;
- numbers use at least three digits through 999;
- allocation occurs while holding an output-directory lock;
- every file created by one run uses the same version number.

## 5. Batch errors

- failure of one job is recorded and the batch continues;
- the summary contains Completed, Skipped, Warnings, Failed, and Cancelled counts;
- the process returns a non-zero exit code when at least one job failed;
- `Ctrl+C` marks the current job as `cancelled`, removes temporary files being finalized, and stops the queue.

## 6. Warning codes

Minimum catalog:

```text
CHANNEL_CLASSIFICATION_AMBIGUOUS
INPUT_DURATION_MISMATCH
INPUT_SAMPLE_RATE_MISMATCH
AUDIO_CLIPPING
AUDIO_LOW_LEVEL
AUDIO_CHANNEL_IMBALANCE
AUDIO_HIGH_SILENCE_RATIO
WORD_ALIGNMENT_MISSING
WORD_TIMESTAMP_INTERPOLATED
OVERLAPPING_SPEECH
DIARIZATION_LOW_CONFIDENCE
LANGUAGE_CODE_SWITCHING_POSSIBLE
EXISTING_RESULT_SKIPPED
SOURCE_NAME_COLLISION
NON_ATOMIC_OUTPUT_FILESYSTEM
```

## 7. Logging

Default format: human-readable text. Optional format: JSON Lines.

Every structured record should include:

- timestamp;
- level;
- event code;
- `run_id`;
- `job_id`;
- source when relevant;
- stage;
- elapsed time;
- safe context.

Logs MUST NOT contain:

- `HF_TOKEN`;
- full transcript text by default;
- audio content;
- arbitrary environment dumps.

## 8. Locks

The application MUST prevent concurrent writes to the same output directory.

Mutable storage operations use a persistent `.ewp-transcripts.lock` file in the resolved
output directory and an exclusive Linux/WSL `flock`. The lock file stores only the holder
PID and acquisition timestamp. It is not deleted on release: retaining one inode avoids a
race in which a waiter holds the old inode while a new process locks a replacement file.
Kernel lock ownership is authoritative, so a leftover metadata timestamp does not itself
mean the directory is locked. The configured timeout controls how long acquisition waits;
the MVP default of zero fails immediately.

Transitions to `failed` or `cancelled` reacquire the same directory lock and verify the
persisted run ID, job ID, episode signature, version, and current `running` status against
the in-memory reservation. A complete terminal record is published exclusively before
the running record is removed. If cleanup is interrupted, both parseable records may
remain and the version stays occupied; neither record is overwritten.
