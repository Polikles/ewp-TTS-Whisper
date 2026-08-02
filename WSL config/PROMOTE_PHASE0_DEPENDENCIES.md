# Promote the validated Phase 0 dependency lock

Run this after ADR-0007 selects the accurate-preset model. The root [`../pyproject.toml`](../pyproject.toml) contains the validated Phase 0 Python/ML dependency definition under the production project name `ewp-transcripts`.

The accepted spike lock was created with root project name `ewp-transcripts-phase0-spike`, so its byte hash cannot remain unchanged after promotion. This procedure starts from that exact lock and updates root-project metadata offline, preventing an unintended fresh transitive resolution.

## 1. Update the application checkout

```bash
export EWP_PHASE0_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"

cd "$EWP_PHASE0_REPO"
git pull --ff-only
test -f pyproject.toml && echo "application pyproject: present"
test -f "$EWP_PHASE0_SPIKE/uv.lock" && echo "accepted spike lock: present"
```

Stop if the repository has unrelated uncommitted changes.

## 2. Reconfirm the accepted spike lock

```bash
sha256sum "$EWP_PHASE0_SPIKE/uv.lock"
```

Required SHA-256:

```text
a309c86ba2a06b86842ee3cb56dffc76a15e635f72a2f46bdf5847e7ab88c14c
```

Do not continue on a mismatch.

## 3. Copy the accepted lock into the application repository

The application repository must not already contain a different lock:

```bash
test ! -e "$EWP_PHASE0_REPO/uv.lock" \
    && cp "$EWP_PHASE0_SPIKE/uv.lock" "$EWP_PHASE0_REPO/uv.lock"
test -f "$EWP_PHASE0_REPO/uv.lock" && echo "application lock: copied"
```

This is a local copy of a known artifact, not a resolver run.

## 4. Update only root-project metadata offline

```bash
cd "$EWP_PHASE0_REPO"
uv lock --offline
```

Expected: uv updates the root project from `ewp-transcripts-phase0-spike==0.0.0` to `ewp-transcripts==0.1.0` using the local cache. No network access or package-version upgrade is allowed.

Record the promoted lock hash:

```bash
sha256sum uv.lock
```

The promoted hash will differ from the spike hash because root project metadata changed.

## 5. Verify the promoted resolution

```bash
uv tree --locked | sed -n '1,160p'
```

Confirm these exact packages remain:

```text
whisperx 3.8.6
torch 2.8.0+cu128
torchaudio 2.8.0+cu128
torchvision 0.23.0+cu128
torchcodec 0.7.0
pyannote-audio 4.0.7
faster-whisper 1.2.1
ctranslate2 4.8.1
huggingface-hub 0.36.2
transformers 4.57.6
triton 3.4.0
```

Stop if any resolved package version changes.

## 6. Verify an offline locked installation

Do not reuse or replace the spike environment. Let the application repository create its own `.venv` from the promoted lock:

```bash
uv sync --locked --offline
uv pip check
uv run --locked --offline python --version
uv run --locked --offline python -c "import whisperx; print('whisperx import: OK')"
```

Expected: Python 3.12, compatible packages, and a successful WhisperX import without network access.

## 7. Inspect repository scope

```bash
git status --short
git diff -- pyproject.toml
```

Expected new generated artifact: `uv.lock`. The local `.venv` must be ignored and must not be committed. Do not stage models, caches, evidence, transcripts, or test audio.

## Stop point

Send:

```text
application pyproject: PASS / FAIL
accepted spike lock SHA-256: PASS / FAIL
offline metadata update: PASS / FAIL
promoted uv.lock SHA-256:
all required versions unchanged: PASS / FAIL
offline uv sync: PASS / FAIL
uv pip check: PASS / FAIL
Python version:
WhisperX import: PASS / FAIL
sanitized git status:
```

Do not send the complete lockfile, model paths, caches, tokens, or environment dumps.
