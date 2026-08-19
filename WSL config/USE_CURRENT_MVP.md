# Use the current MVP

Run commands from the synchronized repository:

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
export NLTK_DATA="$HOME/nltk_data"
```

Use `uv run --locked transcriber ...` so the committed dependency graph is always used.
Run the top-level or command-specific help whenever an option is unclear:

```bash
uv run --locked transcriber --help
uv run --locked transcriber inspect --help
uv run --locked transcriber transcribe --help
```

## 1. Check readiness

```bash
uv run --locked transcriber doctor
```

Do not transcribe until every required environment and model check passes.

## 2. Inspect before processing

Single file:

```bash
uv run --locked transcriber inspect "/path/to/episode.mp3"
```

Directory, non-recursive by default:

```bash
uv run --locked transcriber inspect "/path/to/season"
```

Windows drive paths such as `C:\Users\name\recordings` and their WSL equivalents such
as `/mnt/c/Users/name/recordings` are both accepted. The same applies to `--output-dir`.
Keep quotes around paths containing spaces. For performance, Linux-side output and work
directories are preferred for large runs, even when source recordings remain on a
Windows drive.

Inspect reports source grouping, channel classification, duration, warnings, and the
processing mode without loading ASR models. Add `--json-output` when retaining a
machine-readable report.

## 3. Plan outputs without inference

```bash
uv run --locked transcriber dry-run "/path/to/season" \
    --speaker-count auto \
    --output-dir "/path/to/output"
```

Review every `PROCESS`, `SKIP`, warning, source assignment, and output path. Use an exact
positive speaker count when known; use `1` for a genuine single-speaker recording.
If `--speaker-count` is omitted, the configured default is `auto`. This is the safe
choice for a directory containing a mixture of one-speaker and multi-speaker recordings,
although it performs diarization even for mono files that happen to contain one speaker.

## 4. Transcribe offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "/path/to/season" \
    --speaker-count auto \
    --output-dir "/path/to/output" \
    --non-interactive
```

Default language is Polish. Use `--language en` or `--language auto` only when needed;
those execution paths are supported, but English quality has not yet been characterized
against a representative reference corpus.

Every completed job creates immutable canonical `*_results.json` plus configured TXT,
SRT, and VTT exports. A repeated identical job is skipped. `--force` creates the next
coordinated `_vNNN` result/export set and never overwrites an existing file.

## 5. Choose the correct source topology

The preferred multi-speaker input is one synchronized mono file per speaker. This gives
the strongest speaker identity. A two-channel file with one isolated speaker per channel
is the next-best option. Ordinary stereo containing two or more speakers is accepted and
downmixed, but diarized speaker attribution is not guaranteed and must be reviewed and
corrected manually before use as reference data.

Avoid 3+ channel input in the current release. Its conservative classifier warns but can
fall back to channel 0, which may omit dialogue. Until the guarded layout-aware downmix
is implemented, export isolated channels as synchronized mono files or create a known
good mono program mix before transcription.

Automatic filename group:

```text
episode-anna.wav
episode-jan.wav
```

The final hyphen suffix supplies speaker labels and both files form job `episode`.

Explicit group for unrelated filenames:

```bash
uv run --locked transcriber dry-run \
    --group "/path/to/left.wav" \
    --group "/path/to/right.wav" \
    --group-id "episode-stable-id" \
    --speaker-map "left.wav=Anna" \
    --speaker-map "right.wav=Jan" \
    --output-dir "/path/to/output"
```

Repeat the same options with `transcribe` after reviewing the plan. Grouped files must
share sample rate and timeline; differences above 500 ms require the dedicated
`--allow-duration-mismatch` decision. `--force` never bypasses input safety checks.

For a known split-speaker stereo file, inspect automatic classification first. Override
only with source knowledge:

```bash
uv run --locked transcriber transcribe "/path/to/split.wav" \
    --channel-mode split-speakers --output-dir "/path/to/output" --non-interactive
```

## 6. Regenerate exports without audio or models

```bash
uv run --locked transcriber export "/path/to/episode_results.json" \
    --format txt --format srt --format vtt \
    --output-dir "/path/to/reexported"
```

Add `--format segments` for the optional sentence-level JSON. Existing exports are
skipped; `--force` creates a versioned set. Do not edit canonical JSON to correct text.

## 7. Handle failures and retained workspaces

A failed or interrupted job preserves sanitized `*.failed.json` state and its owned work
directory for diagnosis. Correct the cause and rerun; processing restarts safely and
selects a new version when necessary.

Preview privacy cleanup:

```bash
uv run --locked transcriber clean all-workdirs --dry-run --older-than 7
```

Remove only the marker-verified selection after reviewing it:

```bash
uv run --locked transcriber clean all-workdirs --yes --older-than 7
```

Cleanup never removes source audio, final results, exports, unknown directories, or
model caches.

## 8. Preserve internal-pilot evidence

Keep source recordings, canonical results, corrections, and review notes outside the
repository. Follow [`FEEDBACK_FOR_V2.md`](FEEDBACK_FOR_V2.md) for the first archive pilot.
