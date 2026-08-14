# Correct and publish transcripts

This workflow applies to the unreleased v0.2.0 development version on `main`. It keeps
the original canonical result immutable and stores every accepted correction as a
separate full revision.

## 1. Files that are authoritative

Keep these files:

- `*_results.json` — immutable transcription result; never edit or overwrite it;
- `*.review.txt` — human-editable work file;
- `*_revision_NNN.json` — immutable accepted corrected transcript;
- corrected TXT/SRT/VTT/segments exports — replaceable files derived from the result and
  selected revision;
- `*_audit.json` — optional diagnostics; useful, but never required to reconstruct a
  revision.

The ground-truth corpus consists of the exact base `results.json` plus the accepted
revision JSON. A corrected TXT file alone is not sufficient ground truth.

## 2. Recommended one-file workflow

Configure an editor in `transcriber.toml`:

```toml
[revision]
editor = "code --wait"
```

An empty value falls back to `VISUAL`, then `EDITOR`. Run:

```bash
uv run --locked transcriber revise edit ./output/episode_results.json \
  --output-dir ./output \
  --audit
```

`revise edit` creates a review, waits for the editor, and treats a successful editor
close as approval to apply it. Use `--no-apply` when you want to save the review without
creating a revision:

```bash
uv run --locked transcriber revise edit ./output/episode_results.json --no-apply
```

The `--editor "COMMAND ..."` option overrides configuration for one invocation. The
command is parsed into arguments and is never executed through a shell.

## 3. Staged workflow and batch review

Prepare one result or every result in a directory:

```bash
uv run --locked transcriber revise prepare ./output/episode_results.json \
  --output-dir ./reviews

uv run --locked transcriber revise prepare ./output \
  --output-dir ./reviews
```

Directories are non-recursive by default. Add `--recursive` only intentionally.

Edit ordinary transcript text and `@@ speaker speaker_NNN` directives. Do not edit:

- `#` metadata headers;
- `@@ anchor` ranges;
- canonical JSON or revision JSON;
- timestamps, which are inherited from canonical word mappings.

Line breaks inside ordinary review text are presentation only. Correct sentence
boundaries with punctuation. Keep genuine repetitions and fillers unless the recording
shows they are transcription errors.

Preview without writing a revision:

```bash
uv run --locked transcriber revise preview ./reviews/episode.review.txt \
  --results-dir ./output

uv run --locked transcriber revise apply ./reviews/episode.review.txt \
  --results-dir ./output --no-apply
```

These commands execute the same validation and alignment path. Apply after preview:

```bash
uv run --locked transcriber revise apply ./reviews/episode.review.txt \
  --results-dir ./output --output-dir ./output --audit
```

Directories can be supplied to `preview` and `apply`. A failed item is isolated; the
configured runtime batch policy decides whether later reviews continue. Any mixed batch
returns exit code 5.

## 4. Generate corrected exports

Using `latest` is convenient when revisions are stored beside their base result:

```bash
uv run --locked transcriber export ./output/episode_results.json \
  --revision latest \
  --format txt --format srt --format vtt --format segments
```

Use an explicit path when revisions are stored elsewhere or when selecting a benchmark
branch:

```bash
uv run --locked transcriber export ./output/episode_results.json \
  --revision ./revisions/episode_revision_001.json \
  --format txt --format srt --format vtt --format segments
```

`--revision none`, or omitting `--revision`, regenerates raw canonical exports. Revised
exports have `_revision_NNN` in their names and never overwrite raw exports.

## 5. Audit an existing revision

Reconstruct and publish detailed diagnostics:

```bash
uv run --locked transcriber revise audit ./output/episode_revision_001.json \
  --results-dir ./output
```

Use `--no-write --json-output` to inspect the audit without creating a file. Audits list
substitutions, punctuation changes, merges, splits, insertions, deletions, and speaker
changes. They are diagnostic output, not correction state.

## 6. Errors and recovery

- Base hash mismatch: select the exact `results.json` used to prepare the review. Do not
  update the hash manually.
- Invalid anchor: restore the generated anchors or prepare a new review and copy only
  corrected ordinary text into it.
- Unknown speaker: use an existing `speaker_NNN` from the generated review/base result.
- Ambiguous alignment warning: inspect that anchor carefully, especially repeated words;
  the condition is reported rather than silently hidden.
- Editor failure or non-zero exit: the review remains saved and no revision is created.
- Existing audit/export: retain it or select a new output/version; do not overwrite
  immutable artifacts manually.

All revision and export commands are model-free and audio-free. For command-specific
options run, for example:

```bash
uv run --locked transcriber revise apply --help
uv run --locked transcriber export --help
```
