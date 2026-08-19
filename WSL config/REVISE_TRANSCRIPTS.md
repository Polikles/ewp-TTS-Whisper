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

The revision JSON intentionally stores corrected tokens rather than a second copy of
canonical segments. Each corrected token maps back to canonical word IDs, so timing and
provenance remain anchored in `results.json`. Corrected sentence and speaker segments are
derived from `results.json + revision.json` during export. This avoids two independently
editable segment structures that could disagree.

## 2. Recommended workflow: Windows VS Code

The current recommended workflow is:

```text
prepare -> edit the review manually in Windows -> apply -> export
```

It works for long transcripts and does not require the transcriber to launch an editor.
In the examples below, replace the paths with the directory containing your result.

### 2.1. Prepare the editable review

```bash
uv run --locked transcriber revise prepare \
  "C:\Users\YOUR_NAME\Documents\EWP\episode_results.json" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\reviews"
```

Use the exact `REVIEW` path printed by the command in the following steps.

### 2.2. Edit and save it in Windows VS Code

Open the reported `.review.txt` directly from Windows Explorer with Windows VS Code. It
is preferred over Notepad because **Change All Occurrences** and search/replace can fix a
repeated mistranscription consistently across a long episode. Review every replacement
before saving: a spelling may be correct in one context and wrong in another.

The review file is already on the Windows filesystem. Open it from Windows Explorer or
from an existing Windows VS Code window; do not launch `code`, `notepad.exe`, or another
GUI through `transcriber revise edit`. WSL launchers may return before editing finishes
or fail to open the requested path, causing an unchanged or prematurely applied review.
Windows Notepad remains an acceptable fallback for small corrections.

Edit ordinary transcript text and `@@ speaker speaker_NNN` directives. Do not edit:

- `#` metadata headers;
- `@@ anchor` ranges;
- canonical JSON or revision JSON;
- timestamps, which are inherited from canonical word mappings.

Line breaks inside ordinary review text are presentation only. Correct sentence
boundaries with punctuation. Keep genuine repetitions and fillers unless the recording
shows they are transcription errors.

An optional validation-only preview can be run before applying:

```bash
uv run --locked transcriber revise preview \
  "C:\Users\YOUR_NAME\Documents\EWP\reviews\episode.review.txt" \
  --results-dir "C:\Users\YOUR_NAME\Documents\EWP"
```

### 2.3. Apply the saved review

```bash
uv run --locked transcriber revise apply \
  "C:\Users\YOUR_NAME\Documents\EWP\reviews\episode.review.txt" \
  --results-dir "C:\Users\YOUR_NAME\Documents\EWP" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\output" \
  --audit
```

Retain the reported `*_revision_NNN.json`; it is the accepted correction artifact.

### 2.4. Export the corrected transcript

Use the explicit revision path printed by apply:

```bash
uv run --locked transcriber export \
  "C:\Users\YOUR_NAME\Documents\EWP\episode_results.json" \
  --revision "C:\Users\YOUR_NAME\Documents\EWP\output\episode_revision_001.json" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\output" \
  --format txt --format srt --format vtt --format segments
```

## 3. Bulk revision workflow

Use three separate directories for a batch:

- `results` — the canonical `*_results*.json` files selected for correction;
- `reviews` — editable `*.review.txt` files;
- `revisions` — accepted immutable revisions and optional audits.

Keep only the intended canonical version of each episode in `results`. Directory
commands process every matching file they discover; old result versions are separate
inputs rather than automatically superseded files.

### 3.1. Prepare all reviews

```bash
uv run --locked transcriber revise prepare \
  "C:\Users\YOUR_NAME\Documents\EWP\results" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\reviews"
```

A successful batch ends with output similar to:

```text
SUMMARY prepared=24 failed=0 stopped_early=false
```

Confirm that `reviews` contains one review for every intended result before editing.
Directory discovery is non-recursive by default. Add `--recursive` only when the input
directory deliberately contains results in subdirectories.

### 3.2. Edit the reviews in Windows

Open each generated review from Windows Explorer and edit it in Windows VS Code. Its
search and **Change All Occurrences** features are especially useful for recurring names
and terminology across long transcripts. Follow the editing rules in section 2.2, keep
the filenames and metadata headers unchanged, and save all files as UTF-8. Review files
may be corrected over several sessions; no model or source audio is needed for the later
commands.

### 3.3. Preview the complete batch

Previewing is optional but recommended before accepting a large corpus:

```bash
uv run --locked transcriber revise preview \
  "C:\Users\YOUR_NAME\Documents\EWP\reviews" \
  --results-dir "C:\Users\YOUR_NAME\Documents\EWP\results"
```

The command validates each review against its exact canonical result without writing a
revision. Resolve every reported failure before bulk apply. A clean 24-file preview ends
with:

```text
SUMMARY previewed=24 applied=0 failed=0 stopped_early=false
```

### 3.4. Apply all accepted reviews

```bash
uv run --locked transcriber revise apply \
  "C:\Users\YOUR_NAME\Documents\EWP\reviews" \
  --results-dir "C:\Users\YOUR_NAME\Documents\EWP\results" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\revisions" \
  --audit
```

Success writes one immutable `*_revision_NNN.json` and one `*_audit.json` per review and
ends with:

```text
SUMMARY previewed=0 applied=24 failed=0 stopped_early=false
```

Retain the canonical results and accepted revision files together as the corrected
corpus. Audits are useful diagnostics but are not authoritative correction state.

### 3.5. Handle a partial failure safely

A failed item is isolated; previously successful items remain published. A mixed batch
returns exit code 5. Whether later items continue is controlled by
`runtime.continue_batch_after_error` in the active configuration.

Do not rerun the entire review directory after a partial apply: reviews that already
succeeded would create additional revision numbers. Fix and retry only each failed
review, for example:

```bash
uv run --locked transcriber revise apply \
  "C:\Users\YOUR_NAME\Documents\EWP\reviews\failed-episode.review.txt" \
  --results-dir "C:\Users\YOUR_NAME\Documents\EWP\results" \
  --output-dir "C:\Users\YOUR_NAME\Documents\EWP\revisions" \
  --audit
```

Use `--json-output` when a script needs a machine-readable batch summary.

## 4. Optional nano shortcut

`revise edit` is an optional shortcut only for users who want to edit inside the WSL
terminal with nano. It is not the recommended Windows GUI workflow:

```bash
uv run --locked transcriber revise edit ./output/episode_results.json \
  --output-dir ./output --audit --editor "nano"
```

In nano, save with `Ctrl+O`, confirm with Enter, and exit with `Ctrl+X`. The command
applies only if the review file changed. GUI launchers are environment-dependent and
must not be assumed to wait or open the requested WSL path correctly.

For repeated nano use, configure `editor = "nano"` under `[revision]` in either:

- `/home/linuch/transkrypcje/ewp-transcripts/transcriber.toml` for the documented
  checkout; or
- `/home/linuch/.config/ewp-transcripts/config.toml` for the current user.

`VISUAL` and `EDITOR` are environment-variable names, not editor commands.

## 5. Generate corrected exports

Applying a revision writes the immutable revision and optional audit; it does not
automatically write corrected TXT, subtitle, or segments files. Generate those derived
files explicitly after accepting the revision.

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

The resulting `*_segments_revision_NNN.json` contains corrected phrase/speaker segments
and word-level timing. It is convenient for inspection and downstream applications, but
it remains replaceable derived output. The authoritative corrected state is still the
exact base result plus its accepted revision.

`--revision none`, or omitting `--revision`, regenerates raw canonical exports. Revised
exports have `_revision_NNN` in their names and never overwrite raw exports.

The current `transcriber export` command accepts one canonical result at a time; it does
not yet accept a results directory. After bulk apply, export each accepted
result/revision pair individually. Native bulk export remains planned work.

## 6. Audit an existing revision

Reconstruct and publish detailed diagnostics:

```bash
uv run --locked transcriber revise audit ./output/episode_revision_001.json \
  --results-dir ./output
```

Use `--no-write --json-output` to inspect the audit without creating a file. Audits list
substitutions, punctuation changes, merges, splits, insertions, deletions, and speaker
changes. They are diagnostic output, not correction state.

## 7. Errors and recovery

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
