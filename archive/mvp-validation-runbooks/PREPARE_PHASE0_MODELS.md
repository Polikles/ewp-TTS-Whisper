# Prepare Phase 0 models explicitly

Run this only after sections 0–10 of [`PREPARE_PHASE0_WSL.md`](PREPARE_PHASE0_WSL.md) pass.

This stage downloads all resources explicitly before inference. It does not run ASR, alignment, or diarization yet. Run one section at a time and stop on the first unexpected result.

## 1. Restore paths and privacy controls

Open a fresh WSL shell if desired, then run:

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"
export NLTK_DATA="$EWP_PHASE0_SPIKE/models/nltk_data"
export PYANNOTE_METRICS_ENABLED=0

cd "$EWP_PHASE0_SPIKE"
mkdir -p "$EWP_PHASE0_SPIKE/models/nltk_data"
mkdir -p "$EWP_PHASE0_SPIKE/evidence"
```

Verify without dumping the environment:

```bash
test -f uv.lock && echo "uv.lock: present"
test -f "$EWP_PHASE0_DATA/audio/p0-01-single-short.wav" && echo "P0-01: present"
test -f "$EWP_PHASE0_DATA/audio/p0-03-two-speakers-mixed-overlap.wav" && echo "P0-03: present"
test "$PYANNOTE_METRICS_ENABLED" = 0 && echo "pyannote telemetry: disabled"
```

## 2. Verify the Hugging Face CLI

```bash
uv run --locked hf --help >/dev/null && echo "hf CLI: OK"
```

Do not upgrade `huggingface-hub` or install a second CLI if this fails. Stop and report the error.

## 3. Inspect public model downloads

The first ASR candidate and WhisperX's default Polish alignment model are:

```text
Systran/faster-whisper-large-v3
jonatasgrosman/wav2vec2-large-xlsr-53-polish
```

The locked `huggingface-hub==0.36.2` CLI does not support the newer `hf download --dry-run` option. Query repository metadata through the locked Python API instead; this makes a network request but does not download model files:

```bash
uv run --locked python - <<'PY'
from huggingface_hub import HfApi

api = HfApi()
for repo_id in (
    "Systran/faster-whisper-large-v3",
    "jonatasgrosman/wav2vec2-large-xlsr-53-polish",
):
    info = api.model_info(repo_id, files_metadata=True)
    sizes = [item.size for item in info.siblings if item.size is not None]
    print(f"repo={repo_id}")
    print(f"revision={info.sha}")
    print(f"files={len(info.siblings)}")
    print(f"known_size_bytes={sum(sizes)}")
PY
```

Record the reported revisions, file counts, and sizes before continuing. The revision returned here should match the snapshot directory created by the subsequent download unless the upstream repository changes between the two operations.

## 4. Download and capture immutable ASR/alignment revisions

```bash
export EWP_ASR_SNAPSHOT="$(uv run --locked hf download Systran/faster-whisper-large-v3)"
export EWP_ALIGN_PL_SNAPSHOT="$(uv run --locked hf download jonatasgrosman/wav2vec2-large-xlsr-53-polish)"
```

Verify the returned paths exist:

```bash
test -d "$EWP_ASR_SNAPSHOT" && echo "ASR snapshot: present"
test -d "$EWP_ALIGN_PL_SNAPSHOT" && echo "Polish alignment snapshot: present"
```

Record only the immutable snapshot directory names:

```bash
printf 'ASR revision: %s\n' "$(basename "$EWP_ASR_SNAPSHOT")"
printf 'Polish alignment revision: %s\n' "$(basename "$EWP_ALIGN_PL_SNAPSHOT")"
```

Do not publish the complete cache path when a revision hash is sufficient.

## 5. Download NLTK sentence data explicitly

WhisperX alignment attempts to download `punkt_tab` automatically when it is absent. Prevent hidden runtime downloads by preparing it now:

```bash
(
    cd /tmp
    "$EWP_PHASE0_SPIKE/.venv/bin/python" -P -m nltk.downloader \
        -d "$NLTK_DATA" punkt_tab
)
```

`-P` tells Python not to prepend the potentially unsafe current working directory to its module search path. In this environment, invoking Python through `uv run` still leaves the project root available during import initialization, so `regex` deliberately rejects the import. The subshell changes only this command's working directory to `/tmp` and invokes the interpreter from the already synchronized locked environment directly. No packages are installed or changed, and the interactive shell remains in the spike directory afterward.

Verify:

```bash
test -d "$NLTK_DATA/tokenizers/punkt_tab" && echo "NLTK punkt_tab: present"
```

## 6. Prepare the gated Community-1 download

Confirm that model terms are accepted. Create or retrieve a read-only Hugging Face token, but do not paste it into the command line or shell history.

Read it into the current shell without echoing:

```bash
read -rsp "Hugging Face read token: " HF_TOKEN
echo
export HF_TOKEN
test -n "$HF_TOKEN" && echo "HF_TOKEN: present" || echo "HF_TOKEN: missing"
```

The `hf` command reads `HF_TOKEN` from the environment. Do not use `--token "$HF_TOKEN"`, because command arguments may be visible to other local processes.

Inspect the gated repository metadata using the token from the environment:

```bash
uv run --locked python - <<'PY'
from huggingface_hub import HfApi

repo_id = "pyannote/speaker-diarization-community-1"
info = HfApi().model_info(repo_id, files_metadata=True)
sizes = [item.size for item in info.siblings if item.size is not None]
print(f"repo={repo_id}")
print(f"revision={info.sha}")
print(f"files={len(info.siblings)}")
print(f"known_size_bytes={sum(sizes)}")
PY
```

Expected: metadata is returned rather than HTTP 401/403. This confirms API access but the complete download remains the definitive gated-access test.

## 7. Download and capture the Community-1 revision

```bash
export EWP_DIARIZATION_SNAPSHOT="$(uv run --locked hf download pyannote/speaker-diarization-community-1)"
test -d "$EWP_DIARIZATION_SNAPSHOT" && echo "Community-1 snapshot: present"
printf 'Community-1 revision: %s\n' "$(basename "$EWP_DIARIZATION_SNAPSHOT")"
```

Do not print `HF_TOKEN`.

## 8. Remove token access after download

```bash
unset HF_TOKEN
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: removed from shell"
```

Normal offline loading must use the local Community-1 snapshot without a token.

## 9. Record cache size without listing sensitive paths

```bash
du -sh "$HF_HOME"
du -sh "$NLTK_DATA"
```

## Stop point

Send these sanitized results:

```text
hf CLI: PASS / FAIL
ASR metadata revision/files/size:
Polish alignment metadata revision/files/size:
ASR revision:
Polish alignment revision:
NLTK punkt_tab: PASS / FAIL
Community-1 access: PASS / FAIL
Community-1 metadata revision/files/size:
Community-1 revision:
HF_TOKEN removed: PASS / FAIL
HF cache size:
NLTK data size:
```

Do not send tokens, complete cache paths, model files, transcript content, or full command-history output.

## Restart behavior

Re-running `hf download` for the same repository uses the local cache and should return the same snapshot path when the upstream revision has not changed. After revisions are recorded, subsequent setup documentation will use those immutable revisions explicitly.

Do not clear the Hugging Face or NLTK caches between the online and offline tests.

## Accepted target-workstation result

This procedure passed on the target workstation on 2026-08-01. The accepted revisions and sanitized cache measurements are recorded in [`PHASE0_RESULTS.md`](PHASE0_RESULTS.md). The non-fatal NLTK `runpy` warning observed during `punkt_tab` acquisition did not prevent download, extraction, or directory verification.

## Primary sources

- [Hugging Face download guide](https://huggingface.co/docs/huggingface_hub/en/guides/download)
- [WhisperX 3.8.6 Polish alignment mapping](https://raw.githubusercontent.com/m-bain/whisperX/v3.8.6/whisperx/alignment.py)
- [Community-1 model card](https://huggingface.co/pyannote/speaker-diarization-community-1)
- [NLTK data installation](https://www.nltk.org/data.html)
- [Python 3.12 safe-path option (`-P`)](https://docs.python.org/3.12/using/cmdline.html#cmdoption-P)
