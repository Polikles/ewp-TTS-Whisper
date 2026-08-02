# Prepare the Phase 0 ASR model comparison

This checkpoint prepares the controlled `large-v2` versus `large-v3` comparison defined by [`../docs/adr/0007-accurate-preset-asr-model.md`](../docs/adr/0007-accurate-preset-asr-model.md). It records corpus identities and downloads the additional candidate explicitly. It does not run inference yet.

## 1. Restore paths

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"

export EWP_P001_AUDIO="$EWP_PHASE0_DATA/audio/p0-01-single-short.wav"
export EWP_P002_AUDIO="$EWP_PHASE0_DATA/audio/p0-02-single-representative.wav"
export EWP_P003_AUDIO="$EWP_PHASE0_DATA/audio/p0-03-two-speakers-mixed-overlap.wav"

export EWP_P001_REFERENCE="$EWP_PHASE0_DATA/references/p0-01-single-short.txt"
export EWP_P002_REFERENCE="$EWP_PHASE0_DATA/references/p0-02-single-representative.txt"
export EWP_P003_REFERENCE="$EWP_PHASE0_DATA/references/p0-03-two-speakers-mixed-overlap.txt"

cd "$EWP_PHASE0_SPIKE"
```

If a reference has a different filename, change only its corresponding variable. Do not rename a verified reference merely to satisfy this runbook.

## 2. Verify six corpus inputs

```bash
test -f "$EWP_P001_AUDIO" && echo "P0-01 audio: present"
test -f "$EWP_P002_AUDIO" && echo "P0-02 audio: present"
test -f "$EWP_P003_AUDIO" && echo "P0-03 audio: present"
test -f "$EWP_P001_REFERENCE" && echo "P0-01 reference: present"
test -f "$EWP_P002_REFERENCE" && echo "P0-02 reference: present"
test -f "$EWP_P003_REFERENCE" && echo "P0-03 reference: present"
```

Expected: all six checks print `present`.

References may contain one sentence per line and correct punctuation. They must not contain speaker-label metadata such as `Mówca 1`, `Mówca 2`, or `SPEAKER_00` unless those words were actually spoken.

Check likely label patterns without printing transcript content:

```bash
if grep -Eiq '^[[:space:]]*(mówca|speaker)[[:space:]_:-]*[0-9]+' \
    "$EWP_P001_REFERENCE" "$EWP_P002_REFERENCE" "$EWP_P003_REFERENCE"; then
    echo "speaker-label check: REVIEW REQUIRED"
else
    echo "speaker-label check: PASS"
fi
```

This is a guard, not a complete semantic inspection. The owner remains responsible for confirming that metadata labels are absent.

## 3. Record immutable corpus hashes

```bash
sha256sum \
    "$EWP_P001_AUDIO" "$EWP_P001_REFERENCE" \
    "$EWP_P002_AUDIO" "$EWP_P002_REFERENCE" \
    "$EWP_P003_AUDIO" "$EWP_P003_REFERENCE"
```

These six hashes will be recorded in ADR-0007. Do not send transcript contents.

## 4. Confirm the locked environment and existing candidate

```bash
test -f "$EWP_PHASE0_SPIKE/uv.lock" && echo "uv.lock: present"
test -x "$EWP_PHASE0_SPIKE/.venv/bin/python" && echo "locked Python: present"

export EWP_ASR_V3_REVISION="edaa852ec7e145841d8ffdb056a99866b5f0a478"
export EWP_ASR_V3_SNAPSHOT="$HF_HOME/hub/models--Systran--faster-whisper-large-v3/snapshots/$EWP_ASR_V3_REVISION"
test -d "$EWP_ASR_V3_SNAPSHOT" && echo "large-v3 snapshot: present"
```

Expected: all three checks pass.

## 5. Inspect `large-v2` metadata without downloading

Network access is required for this preparation step. Keep tokens unset; `large-v2` is public.

```bash
unset HF_TOKEN
unset HF_HUB_OFFLINE
unset TRANSFORMERS_OFFLINE

uv run --locked python - <<'PY'
from huggingface_hub import HfApi

repo_id = "Systran/faster-whisper-large-v2"
info = HfApi().model_info(repo_id, files_metadata=True)
sizes = [item.size for item in info.siblings if item.size is not None]
print(f"repo={repo_id}")
print(f"revision={info.sha}")
print(f"files={len(info.siblings)}")
print(f"known_size_bytes={sum(sizes)}")
PY
```

Record the revision, file count, and known size.

## 6. Download and verify the immutable `large-v2` snapshot

```bash
export EWP_ASR_V2_SNAPSHOT="$(
    uv run --locked hf download Systran/faster-whisper-large-v2
)"

test -d "$EWP_ASR_V2_SNAPSHOT" && echo "large-v2 snapshot: present"
printf 'large-v2 revision: %s\n' "$(basename "$EWP_ASR_V2_SNAPSHOT")"
```

The downloaded snapshot basename must match the metadata revision from section 5. Do not publish the complete cache path.

## 7. Return to local-only controls

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

Do not run inference yet. The comparison script must use both immutable local snapshot paths under identical controls.

## Stop point

Send:

```text
six input checks: PASS / FAIL
speaker-label check: PASS / REVIEW REQUIRED
P0-01 audio SHA-256:
P0-01 reference SHA-256:
P0-02 audio SHA-256:
P0-02 reference SHA-256:
P0-03 audio SHA-256:
P0-03 reference SHA-256:
large-v3 snapshot: PASS / FAIL
large-v2 metadata revision/files/size:
large-v2 downloaded revision:
large-v2 revision match: PASS / FAIL
HF_TOKEN absent: PASS / FAIL
```

Do not send transcript text, audio, model files, full cache paths, tokens, or environment dumps.

## Primary sources

- [faster-whisper model conversion and model references](https://github.com/SYSTRAN/faster-whisper)
- [Hugging Face Hub download guide](https://huggingface.co/docs/huggingface_hub/en/guides/download)
