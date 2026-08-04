# Model and Hugging Face setup

This procedure is completed only after the dependency spike has selected exact model identifiers and revisions.

## 1. Account-side preparation

The user must sign in to Hugging Face, accept the terms for every gated model required by the selected pyannote pipeline, and create a read-only user access token.

Never paste the token into project files, issue reports, logs, or chat transcripts.

## 2. Session-only token

Set the token without placing it directly in shell history:

```bash
read -rsp "Hugging Face token: " HF_TOKEN
echo
export HF_TOKEN
```

Verify presence without printing the value:

```bash
test -n "$HF_TOKEN" && echo "HF_TOKEN: present" || echo "HF_TOKEN: missing"
```

## 3. Cache location

```bash
export HF_HOME="$HOME/.cache/huggingface"
mkdir -p "$HF_HOME"
chmod 700 "$HF_HOME"
```

Hugging Face documents `HF_HOME` as the root for its token and cache data.

## 4. Explicit downloads

Use `hf download` or the selected library's explicit setup operation only after model IDs and revisions are pinned. Never rely on transcription to download a missing gated model.

The final command template will be filled during the Phase 0 spike:

```text
hf download <pinned-model-id> --revision <pinned-revision>
```

Source: [Hugging Face — Download files from the Hub](https://huggingface.co/docs/huggingface_hub/en/guides/download).

The accepted MVP model revisions are recorded in `docs/14-dependency-baseline.md`.
After download, set `models.asr_snapshot_path`, `models.alignment_snapshot_path`, and
`models.english_alignment_snapshot_path` in configuration to their exact snapshot
directories.
Each directory name must be the corresponding revision hash. The packaged defaults
match the standard cache created under `$HOME/.cache/huggingface`; override the paths
when `HF_HOME` points elsewhere. Runtime transcription uses these paths directly and
does not download or discover models.

The English alignment snapshot is public and does not require `HF_TOKEN`:

```bash
uv run --locked hf download facebook/wav2vec2-base-960h \
    --revision 22aad52d435eb6dbaf354bdad9b0da84ce7d6156
```

This is an explicit setup operation, not a transcription-time fallback.

## Input needed later

Before gated-model verification, confirm only that the required terms have been accepted, a read-only token exists, and it is available as `HF_TOKEN` in the spike shell.
