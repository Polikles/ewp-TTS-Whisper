# Run the Phase 8 mixed-source diarization gate

This gate validates the production diarization path for one source containing multiple
speakers. It covers an exact two-speaker request on clean mixed stereo and automatic
speaker counting on deliberately overlapping mono material. Both jobs must use pinned
local models, preserve regular diarization overlap, use the exclusive timeline for word
assignment, publish canonical results, and generate labelled exports.

This is a topology and integration gate. It does not report WER, CER, or DER: the current
references do not contain speaker-timestamp annotations, and the Phase 9 corpus will
provide the larger evidence set required for meaningful quality metrics.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P8_EXACT_INPUT="$EWP_TESTDATA/audio/p2-03-mixed-stereo.wav"
export EWP_P8_AUTO_INPUT="$EWP_TESTDATA/audio/p0-03-two-speakers-mixed-overlap.wav"
export EWP_P8_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase8-diarization-XXXXXXXX)"
export EWP_P8_EXACT="$EWP_P8_ROOT/exact-two"
export EWP_P8_AUTO="$EWP_P8_ROOT/automatic-overlap"
mkdir -p "$EWP_P8_EXACT" "$EWP_P8_AUTO"

printf '[runtime]\nwork_root = "%s"\n' "$EWP_P8_EXACT/work" \
    > "$EWP_P8_EXACT/transcriber.toml"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P8_AUTO/work" \
    > "$EWP_P8_AUTO/transcriber.toml"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P8_ROOT"
```

The log must contain commit `1daa955` or later. At that commit, 214 tests should pass.
All generated results and workspaces remain outside the repository.

## 1. Verify fixtures and pinned local snapshots

```bash
for path in "$EWP_P8_EXACT_INPUT" "$EWP_P8_AUTO_INPUT"; do
    test -s "$path" && echo "present: $(basename "$path")"
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=duration -of default=noprint_wrappers=1 "$path"
done
sha256sum "$EWP_P8_EXACT_INPUT" "$EWP_P8_AUTO_INPUT"

export EWP_ASR_SNAPSHOT="$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-large-v2/snapshots/f0fe81560cb8b68660e564f55dd99207059c092e"
export EWP_ALIGN_SNAPSHOT="$HOME/.cache/huggingface/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
export EWP_DIARIZATION_SNAPSHOT="$HOME/.cache/huggingface/hub/models--pyannote--speaker-diarization-community-1/snapshots/3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
test -d "$EWP_ASR_SNAPSHOT" && echo "ASR snapshot: present"
test -d "$EWP_ALIGN_SNAPSHOT" && echo "alignment snapshot: present"
test -d "$EWP_DIARIZATION_SNAPSHOT" && echo "diarization snapshot: present"
```

Accepted fixture hashes:

```text
c93657e1501e293f72ef8d18e1042dfe574fc66ebca5020152dc3470f7fac27e  p2-03-mixed-stereo.wav
a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba  p0-03-two-speakers-mixed-overlap.wav
```

P2-03 must be stereo PCM S16LE at 44.1 kHz and approximately 105.167 seconds.
P0-03 must be mono PCM S16LE at 48 kHz and approximately 489.448 seconds.

## 2. Inspect and dry-run both cases

```bash
uv run --locked transcriber inspect "$EWP_P8_EXACT_INPUT"
uv run --locked transcriber inspect "$EWP_P8_AUTO_INPUT"

uv run --locked transcriber dry-run "$EWP_P8_EXACT_INPUT" \
    --speaker-count 2 --output-dir "$EWP_P8_EXACT/output"
uv run --locked transcriber dry-run "$EWP_P8_AUTO_INPUT" \
    --speaker-count auto --output-dir "$EWP_P8_AUTO/output"
```

Expected processing decisions:

- P2-03: `detected=mixed-stereo, processing=mixed-stereo`;
- P0-03: `detected=mono, processing=mono`.

Each dry run must report `PROCESS`, the requested count, and version 1. It must not create
the output directory or load any model.

## 3. Run exact-count diarization offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P8_EXACT_INPUT" \
    --config "$EWP_P8_EXACT/transcriber.toml" \
    --speaker-count 2 \
    --output-dir "$EWP_P8_EXACT/output"
```

Expected terminal structure:

```text
PROCESS p2-03-mixed-stereo
RESULT .../p2-03-mixed-stereo_results.json
WROTE .../p2-03-mixed-stereo_transcript.txt
WROTE .../p2-03-mixed-stereo_subtitles.srt
WROTE .../p2-03-mixed-stereo_subtitles.vtt
```

ASR, alignment, and diarization must run sequentially. A download, token request,
traceback, CUDA OOM, or network access is a failure. The accepted Lightning checkpoint
upgrade notice, TF32 reproducibility warning, and short-window `std()` warning may recur.

## 4. Run automatic-count overlap diarization offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P8_AUTO_INPUT" \
    --config "$EWP_P8_AUTO/transcriber.toml" \
    --speaker-count auto \
    --output-dir "$EWP_P8_AUTO/output"
```

The same local-only and sequential requirements apply. Automatic mode must complete with
two speakers on this accepted fixture. It may omit or misrecognize simultaneous speech;
that known ASR limitation is not a technical failure as long as detected overlap is
represented honestly in the canonical timeline.

## 5. Validate canonical results and labelled exports

```bash
uv run --locked python - "$EWP_P8_ROOT" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
schema = json.loads((Path.cwd() / "schemas/results.schema.json").read_text(encoding="utf-8"))
cases = {
    "exact": (root / "exact-two/output/p2-03-mixed-stereo_results.json", 2, False),
    "auto": (
        root / "automatic-overlap/output/p0-03-two-speakers-mixed-overlap_results.json",
        "auto",
        True,
    ),
}

for case, (path, requested_count, require_overlap) in cases.items():
    result = json.loads(path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(result)) == []
    assert result["status"] == "completed"
    assert result["episode"]["source_topology"] == "single_file"
    assert len(result["sources"]) == 1
    assert result["processing"]["effective_config"]["diarization"]["speaker_count"] \
        == requested_count
    assert [stage["name"] for stage in result["processing"]["stages"]] == [
        "prepare_audio", "transcribe", "align", "normalize", "diarize",
        "reconcile_speakers",
    ]
    models = {model["role"]: model for model in result["processing"]["models"]}
    assert set(models) == {"asr", "alignment", "diarization"}
    assert models["asr"]["revision"] == "f0fe81560cb8b68660e564f55dd99207059c092e"
    assert models["alignment"]["revision"] == \
        "6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
    assert models["diarization"]["revision"] == \
        "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
    assert len(result["speakers"]) == 2
    assert [speaker["speaker_id"] for speaker in result["speakers"]] == [
        "speaker_001", "speaker_002"
    ]
    assert [speaker["speaker_label"] for speaker in result["speakers"]] == [
        "Speaker1", "Speaker2"
    ]
    assert all(speaker["speaker_source"] == "diarization"
               for speaker in result["speakers"])
    segments = result["transcript"]["segments"]
    words = [word for segment in segments for word in segment["words"]]
    assert words
    assert {word["speaker_id"] for word in words if word["speaker_id"]} \
        == {"speaker_001", "speaker_002"}
    if require_overlap:
        assert any(segment["overlap"] for segment in segments)
        assert any(len(segment["active_speaker_ids"]) > 1 for segment in segments)
    for suffix in ("transcript.txt", "subtitles.srt", "subtitles.vtt"):
        export = path.with_name(path.name.replace("results.json", suffix))
        assert export.is_file() and export.stat().st_size > 0, export
    transcript = path.with_name(path.name.replace("results.json", "transcript.txt")) \
        .read_text(encoding="utf-8")
    assert "Speaker1:" in transcript and "Speaker2:" in transcript
    print(
        f"PASS {case}: speakers=2, segments={len(segments)}, words={len(words)}, "
        f"overlap_segments={sum(segment['overlap'] for segment in segments)}"
    )
print("canonical diarization, attribution, provenance, overlap, and exports: PASS")
PY
```

Words not covered by a diarization turn or tied between speakers may remain unassigned,
but the result must contain the corresponding structured warning. The validator never
invents an identity for such words.

## 6. Verify duplicate replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P8_EXACT_INPUT" \
    --config "$EWP_P8_EXACT/transcriber.toml" --speaker-count 2 \
    --output-dir "$EWP_P8_EXACT/output"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P8_AUTO_INPUT" \
    --config "$EWP_P8_AUTO/transcriber.toml" --speaker-count auto \
    --output-dir "$EWP_P8_AUTO/output"

test -z "$(find "$EWP_P8_EXACT/work" "$EWP_P8_AUTO/work" \
    -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "Phase 8 workdir cleanup: PASS"
```

Both results and all six exports must report `SKIP`, without model-loading logs. No job
workdir may remain.

## 7. Record evidence

```bash
sha256sum "$EWP_P8_EXACT/output"/*
sha256sum "$EWP_P8_AUTO/output"/*
find "$EWP_P8_ROOT" -type f -name '.*.tmp' -print
git status --short
```

No temporary file may remain. Repository status must be empty except for
`LICENSE_SKETCH.TXT` if present locally.

Send back:

- quality gate and GPU line;
- fixture hashes and ffprobe summaries;
- inspection and dry-run decisions;
- exact-count and automatic-count first-run terminal summaries;
- every PASS line and actual speaker, segment, word, overlap, and warning counts;
- duplicate replay summaries and all output hashes;
- repository status and any unexpected download, token request, warning, traceback, or
  CUDA error.

Do not send audio, model files, tokens, or full transcript content.
