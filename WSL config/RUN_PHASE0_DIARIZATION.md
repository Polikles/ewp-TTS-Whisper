# Run the Phase 0 two-speaker diarization smoke test

Run this after the accepted P0-01 ASR/alignment replay in [`RUN_PHASE0_ASR_ALIGNMENT.md`](RUN_PHASE0_ASR_ALIGNMENT.md). This gate runs the pinned local Community-1 pipeline on P0-03 and verifies both regular and exclusive diarization. It does not run ASR or assign words to speakers yet.

The two JSON outputs therefore contain only speaker-labelled time intervals. They are not transcripts and are not expected to contain text. ASR/alignment and word-to-speaker assignment are a separate integration gate after this component test passes.

P0-03 is known to contain exactly two speakers and three audible overlaps, so this first compatibility run fixes `num_speakers=2`. Transcript-bearing data is not used.

## 1. Restore paths and offline controls

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"
export PYANNOTE_METRICS_ENABLED=0

export EWP_DIARIZATION_REVISION="3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
export EWP_DIARIZATION_SNAPSHOT="$HF_HOME/hub/models--pyannote--speaker-diarization-community-1/snapshots/$EWP_DIARIZATION_REVISION"
export EWP_P003_AUDIO="$EWP_PHASE0_DATA/audio/p0-03-two-speakers-mixed-overlap.wav"
export EWP_P003_STANDARD="$EWP_PHASE0_SPIKE/evidence/p0-03-diarization-standard.json"
export EWP_P003_EXCLUSIVE="$EWP_PHASE0_SPIKE/evidence/p0-03-diarization-exclusive.json"
export EWP_P003_REPORT="$EWP_PHASE0_SPIKE/evidence/p0-03-diarization-report.json"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

cd "$EWP_PHASE0_SPIKE"
mkdir -p "$EWP_PHASE0_SPIKE/evidence"
```

Do not set `HF_TOKEN`. Community-1 must load from the local immutable snapshot.

## 2. Verify inputs

```bash
test -x "$EWP_PHASE0_SPIKE/.venv/bin/python" && echo "locked Python: present"
test -f "$EWP_P003_AUDIO" && echo "P0-03 audio: present"
test -d "$EWP_DIARIZATION_SNAPSHOT" && echo "Community-1 snapshot: present"
test "$PYANNOTE_METRICS_ENABLED" = 0 && echo "pyannote telemetry: disabled"
test "$HF_HUB_OFFLINE" = 1 && echo "Hub offline mode: enabled"
test "$TRANSFORMERS_OFFLINE" = 1 && echo "Transformers offline mode: enabled"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

Expected: all seven checks pass.

## 3. Record idle GPU state

```bash
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
```

## 4. Run regular and exclusive diarization

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
from pyannote.audio import Pipeline
import whisperx

snapshot = os.environ["EWP_DIARIZATION_SNAPSHOT"]
audio_path = Path(os.environ["EWP_P003_AUDIO"])
standard_path = Path(os.environ["EWP_P003_STANDARD"])
exclusive_path = Path(os.environ["EWP_P003_EXCLUSIVE"])
report_path = Path(os.environ["EWP_P003_REPORT"])

def rows(annotation):
    return [
        {
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
        }
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]

def overlap_seconds(items):
    events = []
    for item in items:
        events.append((item["start"], 1))
        events.append((item["end"], -1))
    events.sort(key=lambda event: (event[0], event[1]))
    active = 0
    previous = None
    overlap = 0.0
    for timestamp, delta in events:
        if previous is not None and active >= 2:
            overlap += timestamp - previous
        active += delta
        previous = timestamp
    return round(overlap, 3)

def speaker_seconds(items):
    totals = {}
    for item in items:
        speaker = item["speaker"]
        totals[speaker] = totals.get(speaker, 0.0) + item["end"] - item["start"]
    return {speaker: round(value, 3) for speaker, value in sorted(totals.items())}

torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()

started = time.perf_counter()
pipeline = Pipeline.from_pretrained(snapshot)
pipeline.to(torch.device("cuda"))
torch.cuda.synchronize()
load_seconds = time.perf_counter() - started

audio = whisperx.load_audio(str(audio_path))
audio_data = {
    "waveform": torch.from_numpy(audio).unsqueeze(0),
    "sample_rate": 16000,
}

started = time.perf_counter()
output = pipeline(audio_data, num_speakers=2)
torch.cuda.synchronize()
diarization_seconds = time.perf_counter() - started
torch_peak_mib = round(torch.cuda.max_memory_allocated() / 1024**2, 1)

standard = rows(output.speaker_diarization)
exclusive_annotation = getattr(output, "exclusive_speaker_diarization", None)
if exclusive_annotation is None:
    raise RuntimeError("Community-1 did not return exclusive_speaker_diarization")
exclusive = rows(exclusive_annotation)

for path, value in ((standard_path, standard), (exclusive_path, exclusive)):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

del output
del pipeline
gc.collect()
torch.cuda.empty_cache()
torch.cuda.synchronize()
after_unload_mib = round(torch.cuda.memory_allocated() / 1024**2, 1)

report = {
    "case": "P0-03",
    "diarization_revision": os.environ["EWP_DIARIZATION_REVISION"],
    "requested_speakers": 2,
    "load_seconds": round(load_seconds, 3),
    "diarization_seconds": round(diarization_seconds, 3),
    "torch_peak_mib": torch_peak_mib,
    "after_unload_torch_mib": after_unload_mib,
    "standard_speakers": sorted({item["speaker"] for item in standard}),
    "standard_turns": len(standard),
    "standard_overlap_seconds": overlap_seconds(standard),
    "standard_speaker_seconds": speaker_seconds(standard),
    "exclusive_available": True,
    "exclusive_speakers": sorted({item["speaker"] for item in exclusive}),
    "exclusive_turns": len(exclusive),
    "exclusive_overlap_seconds": overlap_seconds(exclusive),
    "exclusive_speaker_seconds": speaker_seconds(exclusive),
    "standard_output": standard_path.name,
    "exclusive_output": exclusive_path.name,
}
with report_path.open("w", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")

print(json.dumps(report, indent=2))
PY
)
```

Expected warnings:

- Pyannote may disable TF32 to protect reproducibility.
- Lightning may report an in-memory checkpoint-format upgrade. Do not run its suggested command against model files in the immutable cache.

Stop if any network download, access-token request, CUDA error, or missing exclusive-diarization error occurs.

## 5. Verify sanitized artifacts

```bash
test -s "$EWP_P003_STANDARD" && echo "standard diarization: present"
test -s "$EWP_P003_EXCLUSIVE" && echo "exclusive diarization: present"
test -s "$EWP_P003_REPORT" && echo "sanitized report: present"
sha256sum "$EWP_P003_STANDARD" "$EWP_P003_EXCLUSIVE"
cat "$EWP_P003_REPORT"
```

Expected:

- exactly two labels appear in both outputs;
- regular diarization has a positive overlap duration for this fixture;
- exclusive diarization is available and has zero overlap duration;
- the unload value is small relative to the peak.

## 6. Manual gross-correctness review

Review the external interval files against the audio or project timeline. Speaker label names are arbitrary; assess consistency rather than whether `SPEAKER_00` represents a particular person.

Record:

- whether both people receive distinct, mostly consistent labels;
- obvious false speaker changes or long missed turns;
- whether regular diarization represents the three known overlap regions at least approximately;
- whether exclusive diarization remains useful for later word assignment;
- overall `PASS` or `FAIL` for compatibility and gross correctness.

Exact DER/JER requires a manually timestamped speaker reference and is deferred.

If only an untimestamped reference transcript is available, do not infer speaker accuracy from it. Record the component gate as a technical pass when model execution and structural checks succeed, and leave manual speaker-accuracy assessment pending until the integrated speaker-labelled transcript or a timestamped speaker reference exists.

## Stop point

Send:

```text
idle GPU state:
complete sanitized report JSON:
standard and exclusive SHA-256 values:
manual gross-correctness check: PASS / FAIL
manual notes:
warnings or errors:
```

Do not send tokens, audio, model files, full cache paths, or environment dumps.

## Primary sources

- [Community-1 model card, offline loading, speaker constraints, and exclusive diarization](https://huggingface.co/pyannote/speaker-diarization-community-1)
- [WhisperX 3.8.6 diarization integration](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/diarize.py)
