# Run the Phase 0 integrated two-speaker smoke test

Run this after the component gates in [`RUN_PHASE0_ASR_ALIGNMENT.md`](RUN_PHASE0_ASR_ALIGNMENT.md) and [`RUN_PHASE0_DIARIZATION.md`](RUN_PHASE0_DIARIZATION.md) pass.

This gate processes P0-03 through the complete inference sequence:

```text
audio -> ASR -> word alignment -> exclusive diarization -> speaker assignment
```

It runs all stages in one process and unloads each GPU model before loading the next. Transcript-bearing artifacts remain in the external spike workspace and must not be committed.

## 1. Restore immutable paths and offline controls

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"
export NLTK_DATA="$EWP_PHASE0_SPIKE/models/nltk_data"
export PYANNOTE_METRICS_ENABLED=0

export EWP_ASR_REVISION="edaa852ec7e145841d8ffdb056a99866b5f0a478"
export EWP_ALIGN_PL_REVISION="6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
export EWP_DIARIZATION_REVISION="3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"

export EWP_ASR_SNAPSHOT="$HF_HOME/hub/models--Systran--faster-whisper-large-v3/snapshots/$EWP_ASR_REVISION"
export EWP_ALIGN_PL_SNAPSHOT="$HF_HOME/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/$EWP_ALIGN_PL_REVISION"
export EWP_DIARIZATION_SNAPSHOT="$HF_HOME/hub/models--pyannote--speaker-diarization-community-1/snapshots/$EWP_DIARIZATION_REVISION"
export EWP_WHISPERX_VAD_MODEL="$EWP_PHASE0_SPIKE/.venv/lib/python3.12/site-packages/whisperx/assets/pytorch_model.bin"

export EWP_P003_AUDIO="$EWP_PHASE0_DATA/audio/p0-03-two-speakers-mixed-overlap.wav"
export EWP_P003_INTEGRATED_JSON="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers.json"
export EWP_P003_INTEGRATED_TEXT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers.txt"
export EWP_P003_INTEGRATED_REPORT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-report.json"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

cd "$EWP_PHASE0_SPIKE"
mkdir -p "$EWP_PHASE0_SPIKE/evidence"
```

Do not set `HF_TOKEN`.

## 2. Verify all inputs

```bash
test -x "$EWP_PHASE0_SPIKE/.venv/bin/python" && echo "locked Python: present"
test -f "$EWP_P003_AUDIO" && echo "P0-03 audio: present"
test -d "$EWP_ASR_SNAPSHOT" && echo "ASR snapshot: present"
test -d "$EWP_ALIGN_PL_SNAPSHOT" && echo "Polish alignment snapshot: present"
test -d "$EWP_DIARIZATION_SNAPSHOT" && echo "Community-1 snapshot: present"
test -d "$NLTK_DATA/tokenizers/punkt_tab" && echo "NLTK punkt_tab: present"
test -f "$EWP_WHISPERX_VAD_MODEL" && echo "bundled WhisperX VAD model: present"
test "$PYANNOTE_METRICS_ENABLED" = 0 && echo "pyannote telemetry: disabled"
test "$HF_HUB_OFFLINE" = 1 && echo "Hub offline mode: enabled"
test "$TRANSFORMERS_OFFLINE" = 1 && echo "Transformers offline mode: enabled"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

Expected: all eleven checks pass.

## 3. Record idle GPU state

```bash
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
```

## 4. Run the integrated sequence

The fixed smoke settings are Polish, `float16`, ASR batch size 4, bundled Pyannote VAD, and exactly two diarization speakers.

```bash
(
    cd /tmp
    "$EWP_PHASE0_SPIKE/.venv/bin/python" -P - <<'PY'
import gc
import json
import os
import time
from pathlib import Path

import pandas as pd
import torch
from pyannote.audio import Pipeline
import whisperx

audio_path = Path(os.environ["EWP_P003_AUDIO"])
json_path = Path(os.environ["EWP_P003_INTEGRATED_JSON"])
text_path = Path(os.environ["EWP_P003_INTEGRATED_TEXT"])
report_path = Path(os.environ["EWP_P003_INTEGRATED_REPORT"])

device = "cuda"
compute_type = "float16"
batch_size = 4
vad_method = "pyannote"

def sync():
    torch.cuda.synchronize()

def allocated_mib():
    return round(torch.cuda.memory_allocated() / 1024**2, 1)

def peak_mib():
    return round(torch.cuda.max_memory_allocated() / 1024**2, 1)

def reset_peak():
    torch.cuda.reset_peak_memory_stats()

def cleanup_after_unload():
    gc.collect()
    torch.cuda.empty_cache()
    sync()
    return allocated_mib()

def annotation_frame(annotation):
    frame = pd.DataFrame(
        annotation.itertracks(yield_label=True),
        columns=["segment", "label", "speaker"],
    )
    frame["start"] = frame["segment"].apply(lambda segment: segment.start)
    frame["end"] = frame["segment"].apply(lambda segment: segment.end)
    return frame

def json_default(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")

torch.cuda.empty_cache()
audio = whisperx.load_audio(str(audio_path))

# ASR with bundled local VAD.
reset_peak()
started = time.perf_counter()
asr_model = whisperx.load_model(
    os.environ["EWP_ASR_SNAPSHOT"],
    device,
    compute_type=compute_type,
    language="pl",
    vad_method=vad_method,
    local_files_only=True,
)
sync()
asr_load_seconds = time.perf_counter() - started

started = time.perf_counter()
asr_result = asr_model.transcribe(
    audio,
    batch_size=batch_size,
    language="pl",
    task="transcribe",
)
sync()
asr_seconds = time.perf_counter() - started
asr_peak_mib = peak_mib()
del asr_model
after_asr_unload_mib = cleanup_after_unload()

# Polish word alignment.
reset_peak()
started = time.perf_counter()
align_model, align_metadata = whisperx.load_align_model(
    language_code="pl",
    device=device,
    model_name=os.environ["EWP_ALIGN_PL_SNAPSHOT"],
    model_cache_only=True,
)
sync()
alignment_load_seconds = time.perf_counter() - started

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
alignment_peak_mib = peak_mib()
del align_model
after_alignment_unload_mib = cleanup_after_unload()

# Community-1 and exclusive diarization.
reset_peak()
started = time.perf_counter()
diarization_pipeline = Pipeline.from_pretrained(
    os.environ["EWP_DIARIZATION_SNAPSHOT"]
)
diarization_pipeline.to(torch.device(device))
sync()
diarization_load_seconds = time.perf_counter() - started

audio_data = {
    "waveform": torch.from_numpy(audio).unsqueeze(0),
    "sample_rate": 16000,
}
started = time.perf_counter()
diarization_output = diarization_pipeline(audio_data, num_speakers=2)
sync()
diarization_seconds = time.perf_counter() - started
diarization_peak_mib = peak_mib()

exclusive = getattr(diarization_output, "exclusive_speaker_diarization", None)
if exclusive is None:
    raise RuntimeError("Community-1 did not return exclusive_speaker_diarization")
exclusive_frame = annotation_frame(exclusive)

speaker_result = whisperx.assign_word_speakers(
    exclusive_frame,
    aligned_result,
    fill_nearest=True,
)

del diarization_output
del diarization_pipeline
after_diarization_unload_mib = cleanup_after_unload()

json_path.parent.mkdir(parents=True, exist_ok=True)
with json_path.open("w", encoding="utf-8") as stream:
    json.dump(speaker_result, stream, ensure_ascii=False, indent=2, default=json_default)
    stream.write("\n")

with text_path.open("w", encoding="utf-8") as stream:
    for segment in speaker_result.get("segments", []):
        start = segment.get("start", 0.0)
        end = segment.get("end", start)
        speaker = segment.get("speaker", "UNASSIGNED")
        text = segment.get("text", "").strip()
        stream.write(f"[{start:8.3f} -> {end:8.3f}] {speaker}: {text}\n")

segments = speaker_result.get("segments", [])
words = [word for segment in segments for word in segment.get("words", [])]
segment_speakers = sorted({
    segment["speaker"] for segment in segments if "speaker" in segment
})
word_speakers = sorted({word["speaker"] for word in words if "speaker" in word})
words_per_speaker = {
    speaker: sum(word.get("speaker") == speaker for word in words)
    for speaker in word_speakers
}
speaker_changes = sum(
    left.get("speaker") != right.get("speaker")
    for left, right in zip(words, words[1:])
    if "speaker" in left and "speaker" in right
)

report = {
    "case": "P0-03",
    "language": asr_result.get("language"),
    "compute_type": compute_type,
    "batch_size": batch_size,
    "vad_method": vad_method,
    "requested_speakers": 2,
    "asr_revision": os.environ["EWP_ASR_REVISION"],
    "alignment_revision": os.environ["EWP_ALIGN_PL_REVISION"],
    "diarization_revision": os.environ["EWP_DIARIZATION_REVISION"],
    "asr_load_seconds": round(asr_load_seconds, 3),
    "asr_seconds": round(asr_seconds, 3),
    "alignment_load_seconds": round(alignment_load_seconds, 3),
    "alignment_seconds": round(alignment_seconds, 3),
    "diarization_load_seconds": round(diarization_load_seconds, 3),
    "diarization_seconds": round(diarization_seconds, 3),
    "asr_torch_peak_mib": asr_peak_mib,
    "alignment_torch_peak_mib": alignment_peak_mib,
    "diarization_torch_peak_mib": diarization_peak_mib,
    "after_asr_unload_torch_mib": after_asr_unload_mib,
    "after_alignment_unload_torch_mib": after_alignment_unload_mib,
    "after_diarization_unload_torch_mib": after_diarization_unload_mib,
    "segments": len(segments),
    "words": len(words),
    "untimed_words": sum("start" not in word or "end" not in word for word in words),
    "unassigned_segments": sum("speaker" not in segment for segment in segments),
    "unassigned_words": sum("speaker" not in word for word in words),
    "segment_speakers": segment_speakers,
    "word_speakers": word_speakers,
    "words_per_speaker": words_per_speaker,
    "word_speaker_changes": speaker_changes,
    "exclusive_intervals": len(exclusive_frame),
    "json_output": json_path.name,
    "text_output": text_path.name,
}
with report_path.open("w", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")

print(json.dumps(report, indent=2))
PY
)
```

Expected warnings are the accepted Pyannote TF32 warning and possibly Lightning's in-memory checkpoint-format notice. Do not modify cached or installed model files in response.

Stop on any download, token request, CUDA error, missing exclusive diarization, or stage exception.

## 5. Verify artifacts

```bash
test -s "$EWP_P003_INTEGRATED_JSON" && echo "integrated JSON: present"
test -s "$EWP_P003_INTEGRATED_TEXT" && echo "speaker text: present"
test -s "$EWP_P003_INTEGRATED_REPORT" && echo "sanitized report: present"
sha256sum "$EWP_P003_INTEGRATED_JSON" "$EWP_P003_INTEGRATED_TEXT"
cat "$EWP_P003_INTEGRATED_REPORT"
```

Expected:

- `language` is `pl`;
- segment and word counts are positive;
- `untimed_words`, `unassigned_segments`, and `unassigned_words` are zero;
- both speaker labels appear at segment and word level;
- allocations fall back near the previously observed post-unload baseline.

## 6. Manual review

Open the external text file locally:

```bash
less "$EWP_P003_INTEGRATED_TEXT"
```

Compare it with the untimestamped reference and listen around questionable speaker changes. Speaker IDs are arbitrary; determine once which label corresponds to which person, then assess consistency.

Record separately:

- transcription omissions, substitutions, and hallucinations;
- whether speaker labels remain consistent for each person;
- obvious false or missed speaker changes;
- behavior around the three known overlap regions;
- whether the speaker-labelled text is practically reviewable;
- overall `PASS` or `FAIL` for integrated compatibility and gross correctness.

This review does not replace formal WER/CER or DER/JER measurement.

## Stop point

Send:

```text
idle GPU state:
complete sanitized report JSON:
integrated JSON and text SHA-256 values:
manual integrated check: PASS / FAIL
manual transcription notes:
manual speaker/overlap notes:
warnings or errors:
```

Do not send full transcript text, audio, tokens, model files, cache paths, or environment dumps.

## Primary sources

- [WhisperX 3.8.6 ASR API](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/asr.py)
- [WhisperX 3.8.6 alignment API](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/alignment.py)
- [WhisperX 3.8.6 word-speaker assignment](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/diarize.py)
- [Community-1 exclusive diarization and offline use](https://huggingface.co/pyannote/speaker-diarization-community-1)
