# CLI Specification

Working command name: `transcriber`.

## 1. General rules

- Every command supports `--config PATH`.
- CLI flags override TOML values.
- `--non-interactive` disables all prompts.
- `--json-output` writes a machine-readable operation result to stdout; logs go to stderr.
- `--verbose` and `--debug` increase log detail.
- Secrets are never printed.

## 2. `doctor`

Checks the environment without running transcription.

```text
transcriber doctor
```

Checks include:

- WSL2 and distribution;
- GPU visibility through `nvidia-smi`;
- CUDA availability in PyTorch;
- FFmpeg and ffprobe;
- Python and lockfile state;
- free space in the work directory;
- ASR, alignment, and diarization models;
- `HF_TOKEN` presence reported only as `present` or `missing`;
- offline readiness.

## 3. `inspect`

```text
transcriber inspect INPUT [OPTIONS]
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
--channel-mode auto|mono|dual-mono|split-speakers|mixed-stereo
--speaker-count auto|N
--allow-duration-mismatch
```

## 4. `dry-run`

```text
transcriber dry-run INPUT [OPTIONS]
```

Performs discovery, probing, grouping, hashing, existing-result lookup, and export planning. It does not load ASR models or create final files.

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
transcriber transcribe INPUT [OPTIONS]
```

Primary options:

```text
--output-dir PATH
--recursive
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

Recommended contract:

```text
transcriber transcribe --group FILE1 FILE2 [FILE3 ...]
```

`--group` creates exactly one job. Speaker labels may come from suffixes or `--speaker-map`.

An implementation may alternatively support a manifest, but the syntax choice must not change domain rules.

## 7. `export`

```text
transcriber export RESULTS_JSON [OPTIONS]
```

Options:

```text
--format txt
--format srt
--format vtt
--segments
--output-dir PATH
--force
--subtitle-preset youtube
--speaker-labels on-change|always|never
```

The command does not open audio or load models. An existing export is skipped without `--force`; with `--force`, the next version number is created.

## 8. `clean`

```text
transcriber clean all-workdirs
```

Safety options:

```text
--dry-run
--older-than DAYS
--yes
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
