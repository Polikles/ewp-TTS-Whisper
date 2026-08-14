# CLI Specification

Working command name: `transcriber`.

## 1. General rules

- Every command supports `--config PATH`.
- CLI flags override TOML values.
- `transcribe --non-interactive` disables all prompts.
- `doctor`, `inspect`, and `dry-run` support `--json-output`; structured transcription
  logging is selected through configuration.
- Secrets are never printed.

## 2. `doctor`

Checks the environment without running transcription.

```text
transcriber doctor [--config PATH] [--json-output]
```

Checks include:

- WSL2 and distribution;
- GPU visibility through `nvidia-smi`;
- CUDA availability in PyTorch;
- FFmpeg and ffprobe;
- supported Python version;
- ASR, alignment, and diarization models;
- `HF_TOKEN` presence reported only as `present` or `missing`;
- local model readiness for offline transcription.

The CUDA check runs in a short child Python process. No transcription model is loaded.

## 3. `inspect`

```text
transcriber inspect [INPUT] [OPTIONS]
```

Does not run ASR. Returns:

- discovered files;
- media streams;
- detected groups;
- audio parameters;
- channel classification;
- hashes;
- structured warning-only audio-quality diagnostics;
- existing results and the skip/process decision.

Options:

```text
--recursive
--language pl|en|auto
--config PATH
--channel-mode auto|mono|dual-mono|split-speakers|mixed-stereo
--speaker-count auto|N
--allow-duration-mismatch
--json-output
--group PATH                    # repeatable; alternative to INPUT
--group-id ID                   # required with --group
```

## 4. `dry-run`

```text
transcriber dry-run [INPUT] [OPTIONS]
```

Performs discovery, probing, grouping, hashing, existing-result lookup, and export planning. It does not load ASR models or create final files.

Options are `--group`, `--group-id`, `--output-dir`, `--recursive`, `--language`,
`--config`, `--channel-mode`, `--speaker-count`, `--force`,
`--allow-duration-mismatch`, and `--json-output`.

For every job, output must include:

```text
PROCESS / SKIP / ERROR
job_id
sources
speakers
channel decision
language
result version
planned output paths
warnings
```

## 5. `transcribe`

```text
transcriber transcribe [INPUT] [OPTIONS]
```

Primary options:

```text
--output-dir PATH
--group PATH                   # repeatable; alternative to INPUT
--group-id ID                  # required with --group
--recursive
--config PATH
--language pl|en|auto
--speaker-count auto|N
--speaker NAME                 # single-speaker input
--speaker-map SOURCE=NAME      # repeatable
--channel-mode auto|mono|dual-mono|split-speakers|mixed-stereo
--preset accurate
--format txt                   # repeatable
--format srt
--format vtt
--segments
--force
--allow-duration-mismatch
--keep-temp
--non-interactive
```

Default post-transcription exports are defined in TOML. `results.json` is always created and does not require a flag.

`--speaker NAME` applies only to a single, non-split source and implies the
single-speaker use case. `--speaker-map SOURCE=NAME` may be repeated; `SOURCE`
is the exact input filename including its extension, not a path, stem, or
pattern. Unknown, repeated, ambiguous, and split-source mappings are rejected.
The two options cannot be combined. Explicit labels are applied before
duplicate/version planning, recorded with `speaker_source = "explicit"`, and
participate in the episode signature.

### Output directory

- single file without `--output-dir`: source directory;
- directory batch without `--output-dir`: `<input>/output-ewp-transcripts`;
- explicit `--output-dir`: selected directory with a safe output naming structure.

## 6. Explicit file group

Contract:

```text
transcriber transcribe \
    --group FILE1 \
    --group FILE2 \
    [--group FILE3 ...] \
    --group-id JOB_ID
```

`--group` is repeatable and creates exactly one job from at least two regular files.
`--group-id` is mandatory and supplies the collision-safe output identity; it is never
guessed from unrelated filenames. A positional `INPUT` cannot be combined with
`--group`. Speaker labels may come from each filename's final suffix or
`--speaker-map`.

`inspect` and `dry-run` accept the same explicit-group options. Without `--output-dir`,
outputs are written beside the first listed source. Explicit source order is preserved
in identity and provenance.

## 7. `export`

```text
transcriber export RESULTS_JSON [OPTIONS]
```

Options:

```text
--format txt
--format srt
--format vtt
--format segments
--segments
--output-dir PATH
--force
--config PATH
--subtitle-preset youtube
--speaker-labels on-change|always|never
```

The command does not open audio or load models. An existing export is skipped without `--force`; with `--force`, the next version number is created.

### Revision selection (planned v0.2.0)

`export` additionally accepts:

```text
--revision none|latest|PATH
```

Omitting `--revision` is equivalent to `--revision none` and preserves the v0.1 raw
canonical export path. `latest` means the highest allocated revision number whose exact
base-result SHA-256 matches `RESULTS_JSON`. Explicit paths are recommended for benchmark
branches. Revision-aware export remains audio-free and model-free.

## 7a. `revise`

```text
transcriber revise prepare INPUT [OPTIONS]
transcriber revise apply INPUT [OPTIONS]
transcriber revise preview INPUT [OPTIONS]
transcriber revise edit INPUT [OPTIONS]
transcriber revise audit REVISION [OPTIONS]
```

`prepare` accepts a completed `results.json` or a directory containing completed results.
`apply` and `preview` accept an `EWP-REVIEW 1` file or a directory of review files.
Directory operations use deterministic natural ordering and do not recurse unless
`--recursive` is supplied.

Common options:

```text
--output-dir PATH
--recursive
--config PATH
--results-dir PATH             # resolve base results for review files
--json-output                  # preview/batch structured outcome where supported
```

### `revise prepare`

Creates human-readable `.review.txt` work files with immutable base metadata, stable word
anchors, speaker directives, and editable transcript text. It never modifies the base
result. Batch prepare is part of v0.2.0, not a later convenience feature.

### `revise apply`

```text
transcriber revise apply REVIEW [--no-apply] [--audit] [OPTIONS]
```

Normal apply parses the review, verifies the exact base-result SHA-256, runs deterministic
anchored alignment, validates the complete revision snapshot, and publishes a new
`*_revision_NNN.json` atomically. `--audit` additionally writes detailed diagnostic change
data.

`--no-apply` performs the complete parse/alignment/validation and preview computation but
does not publish a revision or derived exports.

### `revise preview`

```text
transcriber revise preview REVIEW [OPTIONS]
```

This is the user-facing alias for the non-mutating apply path. It is semantically
equivalent to:

```text
transcriber revise apply REVIEW --no-apply
```

The equivalence MUST appear in `--help`. Both CLI forms call the same application
operation.

### `revise edit`

```text
transcriber revise edit RESULTS_JSON [--no-apply] [OPTIONS]
```

The command prepares a review file, starts the configured external editor, and waits for
it to close. **Saving the file and closing the editor with exit status zero is treated as
approval to create a revision automatically.** Supplying `--no-apply` keeps the edited
review file but suppresses automatic apply. A non-zero editor exit does not create a
revision.

The editor is executed as an argument vector, never through `shell=True`.

### `revise audit`

Reconstructs a detailed base-relative audit from a full revision and its immutable base
result. Parent-relative reconstruction additionally requires the parent revision artifact.
Audit data is diagnostic and is not needed to export the revision.

## 8. `clean`

```text
transcriber clean all-workdirs
```

Safety options:

```text
--dry-run
--older-than DAYS
--yes
--config PATH
```

Exactly one of `--dry-run` or `--yes` is required. The command considers only valid
application-owned workspace markers immediately below the configured work root. Unknown
directories, symbolic links, invalid markers, final results, exports, models, tokens, and
configuration are never removed. `--older-than` currently uses the ownership marker's
modification time; changing diagnostic content therefore cannot make a workspace eligible
earlier.

Filtering retained workspaces by `failed`, `cancelled`, or deliberately retained after
success is deferred until a versioned marker records the terminal retention reason and an
immutable creation timestamp. Model-cache deletion remains a separately named operation
outside the MVP and requires separate confirmation.

## 9. Exit codes

| Code | Meaning |
|---:|---|
| 0 | all jobs completed or were validly skipped |
| 1 | general or unexpected error |
| 2 | invalid arguments or configuration |
| 3 | missing dependency, model, or environment capability |
| 4 | input error or no supported media stream |
| 5 | at least one batch job failed |
| 6 | interrupted by the user |
| 7 | lock or concurrent-write conflict |
| 8 | data-schema mismatch |

## 10. Interactive mode

A prompt is allowed only when stdin and stderr are TTYs. MVP decisions should have a deterministic default or require a flag.

In non-interactive mode, a missing required decision fails the affected job instead of blocking the process.
