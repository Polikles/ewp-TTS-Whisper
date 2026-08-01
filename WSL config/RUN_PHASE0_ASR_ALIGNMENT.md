# Run the Phase 0 Polish ASR and alignment smoke test

Run this only after [`PREPARE_PHASE0_MODELS.md`](PREPARE_PHASE0_MODELS.md) passes. This test processes `P0-01` with the pinned local ASR and Polish alignment snapshots. It does not run diarization.

Run one section at a time and stop on the first unexpected result. Transcript-bearing output remains in the external spike workspace and must not be committed.

## 1. Restore paths and offline-loading controls

Open a fresh WSL shell and run:

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"
export NLTK_DATA="$EWP_PHASE0_SPIKE/models/nltk_data"
export PYANNOTE_METRICS_ENABLED=0

export EWP_ASR_REVISION="edaa852ec7e145841d8ffdb056a99866b5f0a478"
export EWP_ALIGN_PL_REVISION="6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
export EWP_ASR_SNAPSHOT="$HF_HOME/hub/models--Systran--faster-whisper-large-v3/snapshots/$EWP_ASR_REVISION"
export EWP_ALIGN_PL_SNAPSHOT="$HF_HOME/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/$EWP_ALIGN_PL_REVISION"
export EWP_P001_AUDIO="$EWP_PHASE0_DATA/audio/p0-01-single-short.wav"
export EWP_P001_OUTPUT="$EWP_PHASE0_SPIKE/evidence/p0-01-asr-aligned-pyannote-vad.json"
export EWP_P001_REPORT="$EWP_PHASE0_SPIKE/evidence/p0-01-asr-alignment-pyannote-vad-report.json"
export EWP_WHISPERX_VAD_MODEL="$EWP_PHASE0_SPIKE/.venv/lib/python3.12/site-packages/whisperx/assets/pytorch_model.bin"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

cd "$EWP_PHASE0_SPIKE"
mkdir -p "$EWP_PHASE0_SPIKE/evidence"
```

These offline variables prevent accidental Hub requests at the library level. A later gate will additionally block outbound network access at the environment level.

## 2. Verify every local input

```bash
test -x "$EWP_PHASE0_SPIKE/.venv/bin/python" && echo "locked Python: present"
test -f "$EWP_P001_AUDIO" && echo "P0-01 audio: present"
test -d "$EWP_ASR_SNAPSHOT" && echo "ASR snapshot: present"
test -d "$EWP_ALIGN_PL_SNAPSHOT" && echo "Polish alignment snapshot: present"
test -d "$NLTK_DATA/tokenizers/punkt_tab" && echo "NLTK punkt_tab: present"
test -f "$EWP_WHISPERX_VAD_MODEL" && echo "bundled WhisperX VAD model: present"
test "$PYANNOTE_METRICS_ENABLED" = 0 && echo "pyannote telemetry: disabled"
test "$HF_HUB_OFFLINE" = 1 && echo "Hub offline mode: enabled"
test "$TRANSFORMERS_OFFLINE" = 1 && echo "Transformers offline mode: enabled"
```

Expected: all nine checks print `present`, `disabled`, or `enabled`. Do not continue if one is missing.

## 3. Record the idle GPU state

Close other GPU-heavy applications when practical, then run:

```bash
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
```

Record the four values. GPU memory reported by `nvidia-smi` includes other Windows and WSL users, so it is context rather than process-isolated peak VRAM.

## 4. Run ASR, unload it, and run alignment

The smoke settings are deliberately conservative: Polish is fixed explicitly, CTranslate2 uses `float16`, ASR batch size is `4`, and WhisperX's bundled Pyannote VAD asset avoids an unpinned Torch Hub download. This VAD is separate from the Community-1 diarization pipeline tested later.

Run from the prepared shell:

```bash
(
    cd /tmp
    "$EWP_PHASE0_SPIKE/.venv/bin/python" -P - <<'PY'
import gc
import json
import os
import time
from pathlib import Path

import torch
import whisperx

audio_path = Path(os.environ["EWP_P001_AUDIO"])
asr_snapshot = os.environ["EWP_ASR_SNAPSHOT"]
align_snapshot = os.environ["EWP_ALIGN_PL_SNAPSHOT"]
output_path = Path(os.environ["EWP_P001_OUTPUT"])
report_path = Path(os.environ["EWP_P001_REPORT"])

device = "cuda"
compute_type = "float16"
batch_size = 4
vad_method = "pyannote"

def sync():
    torch.cuda.synchronize()

def allocated_mib():
    return round(torch.cuda.memory_allocated() / 1024**2, 1)

def json_default(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")

torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()
audio = whisperx.load_audio(str(audio_path))

sync()
started = time.perf_counter()
model = whisperx.load_model(
    asr_snapshot,
    device,
    compute_type=compute_type,
    language="pl",
    vad_method=vad_method,
    local_files_only=True,
)
sync()
asr_load_seconds = time.perf_counter() - started

started = time.perf_counter()
asr_result = model.transcribe(
    audio,
    batch_size=batch_size,
    language="pl",
    task="transcribe",
)
sync()
asr_seconds = time.perf_counter() - started
asr_peak_mib = round(torch.cuda.max_memory_allocated() / 1024**2, 1)

del model
gc.collect()
torch.cuda.empty_cache()
sync()
after_asr_unload_mib = allocated_mib()

torch.cuda.reset_peak_memory_stats()
started = time.perf_counter()
align_model, align_metadata = whisperx.load_align_model(
    language_code="pl",
    device=device,
    model_name=align_snapshot,
    model_cache_only=True,
)
sync()
align_load_seconds = time.perf_counter() - started

started = time.perf_counter()
aligned_result = whisperx.align(
    asr_result["segments"],
    align_model,
    align_metadata,
    audio,
    device,
    return_char_alignments=False,
)
sync()
alignment_seconds = time.perf_counter() - started
alignment_peak_mib = round(torch.cuda.max_memory_allocated() / 1024**2, 1)

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as stream:
    json.dump(aligned_result, stream, ensure_ascii=False, indent=2, default=json_default)
    stream.write("\n")

segments = aligned_result.get("segments", [])
words = [word for segment in segments for word in segment.get("words", [])]
untimed_segments = sum(
    "start" not in segment or "end" not in segment for segment in segments
)
untimed_words = sum("start" not in word or "end" not in word for word in words)

del align_model
gc.collect()
torch.cuda.empty_cache()
sync()
after_alignment_unload_mib = allocated_mib()

report = {
    "case": "P0-01",
    "language": asr_result.get("language"),
    "compute_type": compute_type,
    "batch_size": batch_size,
    "vad_method": vad_method,
    "asr_revision": os.environ["EWP_ASR_REVISION"],
    "alignment_revision": os.environ["EWP_ALIGN_PL_REVISION"],
    "asr_load_seconds": round(asr_load_seconds, 3),
    "asr_seconds": round(asr_seconds, 3),
    "alignment_load_seconds": round(align_load_seconds, 3),
    "alignment_seconds": round(alignment_seconds, 3),
    "asr_torch_peak_mib": asr_peak_mib,
    "alignment_torch_peak_mib": alignment_peak_mib,
    "after_asr_unload_torch_mib": after_asr_unload_mib,
    "after_alignment_unload_torch_mib": after_alignment_unload_mib,
    "segments": len(segments),
    "words": len(words),
    "untimed_segments": untimed_segments,
    "untimed_words": untimed_words,
    "aligned_output": output_path.name,
}
with report_path.open("w", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")

print(json.dumps(report, indent=2))
PY
)
```

Notes:

- The full aligned transcript is written to the external evidence directory but is not printed.
- The report contains no transcript text and is safe to send for review.
- PyTorch's allocator does not account for all CTranslate2 GPU allocations. Its peak values are useful for regression comparisons but are not the final total-VRAM measurement.
- The ASR model is deleted and the PyTorch cache cleared before the alignment model loads. The two post-unload values test this sequence at the PyTorch allocator level.
- Do not change this gate back to `vad_method="silero"`: WhisperX 3.8.6 resolves that adapter through an unpinned `torch.hub.load` call to the upstream default branch.

## 5. Verify artifacts without printing transcript text

```bash
test -s "$EWP_P001_OUTPUT" && echo "aligned output: present"
test -s "$EWP_P001_REPORT" && echo "sanitized report: present"
sha256sum "$EWP_P001_OUTPUT"
cat "$EWP_P001_REPORT"
```

Expected:

- both files are present and non-empty;
- `language` is `pl`;
- `segments` and `words` are greater than zero;
- `untimed_segments` should be zero;
- `untimed_words` is recorded for review rather than assumed to be zero.

## 6. Manual transcript check

Compare the external `p0-01-asr-aligned-pyannote-vad.json` against the manually checked P0-01 reference. Do not commit either transcript. Record only:

- obvious omissions or hallucinations;
- mishandled Polish names or terminology;
- numbers, punctuation, or symbols without timestamps;
- timestamps that are visibly out of order or outside the audio duration;
- an overall `PASS` or `FAIL` for basic usability.

Formal WER and quality-model comparison are later Phase 0 tasks; this is a compatibility and gross-correctness gate.

## Stop point

Send:

```text
idle GPU state:
complete sanitized report JSON:
aligned output SHA-256:
manual gross-correctness check: PASS / FAIL
manual notes (no transcript excerpts required):
warnings or errors:
```

Do not send audio, full transcripts, model files, cache paths, tokens, or environment dumps.

## Failure rules

- A missing local snapshot or attempted network request is a model-preparation failure; stop without allowing an automatic download.
- CUDA out-of-memory at batch size 4 is a Candidate A failure to investigate; do not silently lower the batch size.
- An ASR exception stops the test before alignment.
- An alignment exception is recorded separately from successful ASR.
- Do not add `HF_TOKEN` for this test.

## Primary sources

- [WhisperX 3.8.6 ASR loading and transcription API](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/asr.py)
- [WhisperX 3.8.6 alignment API and Polish model mapping](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/alignment.py)
- [Transformers offline mode](https://huggingface.co/docs/transformers/installation#offline-mode)
