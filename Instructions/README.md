# EWP Transcriber — complete CLI runbook

This is the current operator entry point for the internal command-line application. It
covers every shipped command. The application is not yet a public release.

## 1. Install and prepare the machine

The supported environment is Ubuntu 24.04 under WSL2 with Python 3.12, FFmpeg, `uv`, and
an NVIDIA CUDA-capable GPU. Follow the detailed setup documents in order:

The current locked environment downloads approximately 4–4.5 GB before model setup.
The pinned ASR, Polish/English alignment, and diarization snapshots add approximately
8.5 GB, making the complete network transfer roughly 13 GB. Reserve at least 20 GB of
free space on the Linux filesystem, preferably on an SSD, plus space for source audio
and outputs. The recommended storage minimum is not expected to vary materially by
preset. RAM, VRAM, and runtime requirements will be characterized later per preset.

1. [`../WSL config/SYSTEM_REQUIREMENTS.md`](../WSL%20config/SYSTEM_REQUIREMENTS.md)
2. [`../WSL config/INSTALL_WSL.md`](../WSL%20config/INSTALL_WSL.md)
3. [`../WSL config/INSTALL_TOOLS.md`](../WSL%20config/INSTALL_TOOLS.md)
4. [`../WSL config/CUDA_SETUP.md`](../WSL%20config/CUDA_SETUP.md)
5. [`../WSL config/INSTALL_APPLICATION.md`](../WSL%20config/INSTALL_APPLICATION.md)
6. [`../WSL config/MODEL_SETUP.md`](../WSL%20config/MODEL_SETUP.md)
7. [`../WSL config/OFFLINE_MODE.md`](../WSL%20config/OFFLINE_MODE.md)

Normal source-checkout use begins in the repository:

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
uv sync --locked
uv pip check
uv run --locked transcriber --version
uv run --locked transcriber --help
```

After cloning, a fresh Ubuntu 24.04 checkout can install the base packages, uv/Python,
locked environment, and run diagnostics through the reviewable script:

```bash
./scripts/install-fresh-ubuntu.sh --install
```

It asks before system changes, does not update Git, and never downloads gated models.
Use `./scripts/install-fresh-ubuntu.sh --verify-only` for a read-only recheck. Model setup
remains the separate explicit step in `WSL config/MODEL_SETUP.md`.

The top-level help lists commands. Every command has its own options:

```bash
uv run --locked transcriber COMMAND --help
uv run --locked transcriber revise COMMAND --help
```

The staged private-corpus procedure for v0.3 local LLM correction candidates is in
[`../WSL config/RUN_V03_LOCAL_LLM_BENCHMARK.md`](../WSL%20config/RUN_V03_LOCAL_LLM_BENCHMARK.md).
It requires a three-case pilot before any full-corpus run.

## 2. Configuration and paths

Configuration precedence, from lowest to highest, is:

1. packaged defaults;
2. selected preset;
3. `$HOME/.config/ewp-transcripts/config.toml`;
4. `transcriber.toml` in the terminal's current working directory;
5. the file supplied with `--config PATH`;
6. CLI options.

For the normal source checkout, the project file is exactly:

```text
/home/<user>/transkrypcje/ewp-transcripts/transcriber.toml
```

Run commands from that directory or pass `--config` explicitly. Paths containing spaces
are supported and preserved; quote the complete path. Windows paths such as
`C:\Users\name\recordings` and WSL paths such as `/mnt/c/Users/name/recordings` are both
accepted. Linux-side output/work directories are faster for large jobs.

## 3. Check readiness: `doctor`

```bash
uv run --locked transcriber doctor
uv run --locked transcriber doctor --json-output
```

`doctor` checks Python, WSL/Ubuntu, FFmpeg, GPU/CUDA, pinned local models, and whether
`HF_TOKEN` is present without printing the secret. On a fresh installation, missing model
messages point to `WSL config/MODEL_SETUP.md`. Do not transcribe until required checks
pass.

## 4. Inspect inputs: `inspect`

Always inspect unfamiliar material before transcription:

```bash
uv run --locked transcriber inspect "/path/to/episode.wav"
uv run --locked transcriber inspect "/path/to/season"
uv run --locked transcriber inspect "/path/to/season" --json-output
```

Inspection is model-free. It reports discovery/grouping, duration, streams, channel mode,
speaker-source hints, hashes, and warnings. Directory discovery is non-recursive unless
`--recursive` is supplied.

Preferred multi-speaker input order:

1. one synchronized mono file per speaker;
2. one two-channel file with an isolated speaker in each channel;
3. a mono/stereo program mix followed by diarization and manual attribution review.

Avoid 3+ channel sources in the current release: the warning fallback can use only
channel 0 and may omit dialogue. Ordinary two-speaker stereo is accepted, but inferred
speaker attribution is not guaranteed.

## 5. Group synchronized speaker files

Automatic filename grouping uses final suffixes such as:

```text
episode-Damian.wav
episode-Szymon.wav
```

For unrelated filenames, provide an explicit collision-safe group identity:

```bash
uv run --locked transcriber inspect \
  --group "/path/to/left.wav" \
  --group "/path/to/right.wav" \
  --group-id "episode-001"
```

Repeat `--group` for every source. Use `--speaker-map "left.wav=Damian"` and another
mapping for `right.wav` during `transcribe` when filename labels are unsuitable. Grouped
files must share a timeline and sample rate. `--allow-duration-mismatch` is the dedicated
override for differences above the normal limit; `--force` does not bypass input checks.

## 6. Plan safely: `dry-run`

```bash
uv run --locked transcriber dry-run "/path/to/season" \
  --speaker-count auto \
  --output-dir "/path/to/output"
```

Review every `PROCESS`, `SKIP`, source assignment, channel decision, warning, result
version, and output path. Dry-run creates no final output or work directory and loads no
model. Use `--speaker-count 1` only for a genuine one-speaker recording; use an exact
positive count when known, otherwise `auto`.

## 7. Transcribe: `transcribe`

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "/path/to/season" \
  --speaker-count auto \
  --output-dir "/path/to/output" \
  --non-interactive
```

Polish is the default. `--language en` and `--language auto` are supported but not yet
quality-qualified on a representative English corpus. Useful options include:

- `--format txt|srt|vtt` (repeatable) and `--segments`;
- `--speaker NAME` for one known single-speaker source;
- repeatable `--speaker-map SOURCE=NAME` for grouped sources;
- `--channel-mode split-speakers` only with source knowledge;
- `--keep-temp` to retain an owned successful workspace;
- `--force` to create the next `_vNNN` result set without overwriting.

Every successful job creates immutable `*_results.json`. TXT/SRT/VTT/segments are
derived and regenerable. Duplicate matching jobs skip safely. Never edit canonical JSON.

## 8. Export raw results: `export`

Single result:

```bash
uv run --locked transcriber export "/path/to/episode_results.json" \
  --format txt --format srt --format vtt --format segments \
  --output-dir "/path/to/exports"
```

Directory batch:

```bash
uv run --locked transcriber export "/path/to/results" \
  --format txt --format srt --format vtt --format segments \
  --output-dir "/path/to/exports"
```

Export is audio-free, model-free, and non-recursive unless `--recursive` is supplied.
Existing identical destinations skip; `--force` creates later export versions.
`--speaker-labels on-change|always|never` changes subtitle labels.

## 9. Correct transcripts: `revise`

The recommended workflow is `prepare -> edit in Windows VS Code -> preview -> apply ->
export`. Keep canonical results, reviews, revisions, audits, and exports in separate
directories.

### Prepare one or many reviews

```bash
uv run --locked transcriber revise prepare "/path/to/results" \
  --output-dir "/path/to/reviews"
```

Edit `*.review.txt` in Windows VS Code. Its search and **Change All Occurrences** tools
are preferable for long transcripts. Preserve all `#` metadata, `@@ anchor`, and
`@@ speaker` directives. Edit only transcript text and existing speaker assignments.

### Preview without writing

```bash
uv run --locked transcriber revise preview "/path/to/reviews" \
  --results-dir "/path/to/results"
```

This is equivalent to `revise apply ... --no-apply`. A failed item in a continuing batch
does not invalidate successful items, but the command returns exit code 5.

### Apply and optionally audit

```bash
uv run --locked transcriber revise apply "/path/to/reviews" \
  --results-dir "/path/to/results" \
  --output-dir "/path/to/revisions" \
  --audit
```

Apply publishes immutable `*_revision_NNN.json`; `--audit` adds reconstructable detailed
diagnostics. If one review fails, repair and apply only that file—do not rerun the entire
directory unless additional revisions are intended.

### External-editor shortcut

```bash
uv run --locked transcriber revise edit "/path/to/episode_results.json" \
  --editor "nano" --audit
```

Successful editor close automatically applies only if the review changed, unless
`--no-apply` is supplied. GUI launchers can return before a file closes; the staged VS
Code workflow above is safer. `VISUAL` and `EDITOR` are environment-variable names whose
values must contain an installed editor command; they are not literal commands.

### Reconstruct an audit

```bash
uv run --locked transcriber revise audit "/path/to/episode_revision_001.json" \
  --results-dir "/path/to/results" \
  --output-dir "/path/to/revisions"
```

Use `--no-write --json-output` to inspect reconstructed diagnostics without publication.

The detailed revision guide is
[`../WSL config/REVISE_TRANSCRIPTS.md`](../WSL%20config/REVISE_TRANSCRIPTS.md).

### Automated correction with LM Studio or OpenRouter (v0.3 development)

This command is implemented for controlled local benchmarking but has not yet completed
the three-model acceptance run. In LM Studio, load exactly the intended model and start
its local OpenAI-compatible server. Confirm the exact identifier without sending a
transcript:

An automated revision is always a **review candidate**, never a final or accepted
transcript. WER/CER does not validate punctuation or quotation marks, and tested models
can miss ASR errors or introduce plausible-looking substitutions, deletions, paraphrases,
and improper names. Manually review wording, speaker attribution, punctuation, quotation
marks, and sentence boundaries before exporting it as accepted work. Only a manually
accepted revision may serve as final publication text or benchmark gold.

```bash
curl -fsS http://127.0.0.1:1234/v1/models | \
  uv run --locked python -c \
  'import json,sys; print("\n".join(item["id"] for item in json.load(sys.stdin)["data"]))'
```

Preview still calls the API and stores validated private resume responses; it only
avoids publishing a revision. The first call requires explicit consent:

```bash
uv run --locked transcriber revise correct "/path/to/episode_results.json" \
  --model "EXACT_MODEL_ID_FROM_LM_STUDIO" \
  --endpoint "http://127.0.0.1:1234/v1" \
  --consent once \
  --preview \
  --resume-dir "/private/path/lm-studio-model-name/resume"
```

After inspecting the preview, publish an immutable revision. Reusing the same resume
directory avoids repeating already validated chunks:

```bash
uv run --locked transcriber revise correct "/path/to/episode_results.json" \
  --model "EXACT_MODEL_ID_FROM_LM_STUDIO" \
  --consent once \
  --output-dir "/private/path/lm-studio-model-name/revisions" \
  --resume-dir "/private/path/lm-studio-model-name/resume"
```

To run automated correction on text that already has an immutable revision, keep the
canonical result as the first argument and select the exact parent explicitly:

```bash
uv run --locked transcriber revise correct "/path/to/episode_results.json" \
  --revision "/path/to/episode_revision_001.json" \
  --model "EXACT_MODEL_ID_FROM_LM_STUDIO" \
  --consent once \
  --output-dir "/private/path/model/revisions"
```

The output is a complete child revision rather than a patch. It retains the parent's
accepted text, records the parent's exact identity/hash/number, and can be exported even
if the parent file is later archived. An incompatible parent fails before transcript text
is sent to the provider.

Use `--consent persist` only to remember the exact LM Studio provider and endpoint scope;
model and prompt identity still participate in operation/resume hashes. `--consent reject`
guarantees no API request. Even a loopback server is a separate process that may log or
forward text, so EWP Transcriber displays its local-API warning. The endpoint must be an
uncredentialed HTTP(S) `/v1` URL. Loopback (`localhost`, `127.0.0.1`, or `::1`) is the
default. A LAN, VPN, or Tailscale-like address additionally requires
`--allow-remote-endpoint` and produces a stronger warning; plain HTTP confidentiality
then depends on the underlying network or overlay and is not verified by this program:

```bash
uv run --locked transcriber revise correct "/path/to/episode_results.json" \
  --model "qwen2.5-14b-instruct" \
  --endpoint "http://100.99.201.120:1234/v1" \
  --allow-remote-endpoint --consent once --preview
```

OpenRouter is a separate paid cloud path. Transcript text leaves the machine; audio is not
uploaded. Export the key in the shell, pin the exact current model slug, and use both the
cloud opt-in and consent flags. Never paste a key into TOML, CLI arguments, logs, or
benchmark manifests:

```bash
export OPENROUTER_API_KEY="YOUR_KEY"

uv run --locked transcriber revise correct "/path/to/episode_results.json" \
  --provider openrouter \
  --model "qwen/qwen-2.5-72b-instruct" \
  --allow-cloud --consent once --preview \
  --resume-dir "/private/path/openrouter-qwen72b/resume"
```

Without `--allow-cloud`, strict-offline mode rejects the command before reading the key or
making a request. `--consent reject` also guarantees no request. `persist` remembers only
the exact non-secret provider/endpoint scope. Preview calls may incur charges. The adapter
requests no fallback routing and records non-secret parameters, token counts, and reported
cost when supplied. Cloud output requires the same manual review as local output.
Reasoning-capable cloud models must use an explicit, recorded setting for comparable runs.
For example, add `--reasoning-max-tokens 0` to disable Gemini 2.5 thinking for the initial
baseline. Enabled-reasoning runs are separate experiments because reasoning tokens affect
latency and billing.

## 10. Export corrected transcripts

Latest compatible revision per result:

```bash
uv run --locked transcriber export "/path/to/results" \
  --revision "/path/to/revisions" \
  --format txt --format srt --format vtt --format segments \
  --output-dir "/path/to/corrected"
```

For one result, use `--revision latest` or an explicit revision JSON. Use
`--revision none` for raw canonical text. Directory export with a revision directory
selects the highest revision whose exact base-result hash matches each result. Duplicate
replay skips safely without `--force`.

## 11. Recover from failures

- Exit 3: run `doctor`; install the missing dependency/model explicitly.
- Exit 4: inspect the input, streams, grouping, and supported extension.
- Exit 5: a batch partially failed; use the per-item error and retry only failed items.
- Exit 6: user cancellation; the failed state and owned workdir are retained for review.
- Exit 7: another process owns the output lock; wait or use another output directory.
- Exit 8: canonical/revision/schema mismatch; do not hand-edit JSON.

Failed/interrupted transcription restarts from the beginning. Successful items and
immutable results remain safe. See
[`../WSL config/TROUBLESHOOTING.md`](../WSL%20config/TROUBLESHOOTING.md).

## 12. Clean retained workspaces: `clean`

Preview first:

```bash
uv run --locked transcriber clean all-workdirs --dry-run --older-than 7
```

Then explicitly remove only the marker-verified selection:

```bash
uv run --locked transcriber clean all-workdirs --yes --older-than 7
```

Cleanup never removes source audio, final results/exports, unknown directories, model
caches, configuration, or tokens.

## 13. Privacy and evidence

Normal transcription and manual revision are local-first. Keep `HF_TOKEN`, source
recordings, canonical paths, transcripts, revisions, audits, correction resume state,
and private benchmark material out of Git and shared logs. LM Studio correction is an
explicit local API boundary and is not equivalent to in-process offline execution.
Cloud correction is implemented but remains strict-offline by default and requires an
explicit command opt-in, scoped consent, an environment-only key, and separate paid-run
authorization during project benchmarking.

For later benchmark feedback, use
[`../WSL config/FEEDBACK_FOR_V2.md`](../WSL%20config/FEEDBACK_FOR_V2.md).
