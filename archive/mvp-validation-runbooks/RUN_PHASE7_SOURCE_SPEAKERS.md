# Run the Phase 7 source-speaker gate

This gate validates the two non-diarized multi-speaker topologies introduced in Phase 7:

- one split-speaker stereo file, transcribed once per channel;
- one grouped episode containing a lossless mono file per speaker.

Both cases use the existing P2-01 recording. The grouped fixture is derived by separating
its left and right channels, so no additional recording or reference transcript is
required. The application must run streams sequentially with pinned local models, retain
overlap and repeated speech, publish one canonical result, and generate labelled exports.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P7_INPUT="$EWP_TESTDATA/audio/p2-01-split-speakers.wav"
export EWP_P7_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase7-sources-XXXXXXXX)"
export EWP_P7_SPLIT="$EWP_P7_ROOT/split"
export EWP_P7_GROUP="$EWP_P7_ROOT/group"
mkdir -p "$EWP_P7_SPLIT/input" "$EWP_P7_GROUP/input"

cp "$EWP_P7_INPUT" "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav"

printf '[runtime]\nwork_root = "%s"\n' "$EWP_P7_SPLIT/work" \
    > "$EWP_P7_SPLIT/transcriber.toml"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P7_GROUP/work" \
    > "$EWP_P7_GROUP/transcriber.toml"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P7_ROOT"
```

The log must contain commit `33060f6` or later. At that commit, 199 tests should pass.
All fixtures and generated results remain outside the repository.

## 1. Verify and derive the grouped-source fixture

```bash
sha256sum "$EWP_P7_INPUT" "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav"

ffmpeg -hide_banner -loglevel error -i "$EWP_P7_INPUT" \
    -af 'pan=mono|c0=c0' -c:a pcm_s16le \
    "$EWP_P7_GROUP/input/p7-group-Left.wav"
ffmpeg -hide_banner -loglevel error -i "$EWP_P7_INPUT" \
    -af 'pan=mono|c0=c1' -c:a pcm_s16le \
    "$EWP_P7_GROUP/input/p7-group-Right.wav"

sha256sum "$EWP_P7_GROUP/input"/*.wav
for path in "$EWP_P7_GROUP/input"/*.wav; do
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=duration -of default=noprint_wrappers=1 "$path"
done
```

The source and copied source must both have the accepted P2-01 hash:

```text
868542600305d4cb7514b45130ec67e2cab94bc817e9fa9f6db451c0b999a0a3
```

Record both derived hashes. Each derived file must be mono PCM S16LE at 44.1 kHz and
approximately 142.442 seconds long.

## 2. Inspect and dry-run both topologies

```bash
uv run --locked transcriber inspect "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav"
uv run --locked transcriber inspect "$EWP_P7_GROUP/input"

uv run --locked transcriber dry-run "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav" \
    --speaker-count 1 --output-dir "$EWP_P7_SPLIT/output"
uv run --locked transcriber dry-run "$EWP_P7_GROUP/input" \
    --speaker-count 1 --output-dir "$EWP_P7_GROUP/output"
```

Expected inspection decisions:

- P2-01: `detected=split-speakers, processing=split-speakers`;
- both grouped files: `detected=mono, processing=mono`;
- grouped job ID: `p7-group`, with labels `Left` and `Right` in natural source order.

Each dry run must report one `PROCESS` job with two speaker-bearing streams. Neither
command may create its output directory.

## 3. Run split-channel transcription offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe \
    "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav" \
    --config "$EWP_P7_SPLIT/transcriber.toml" \
    --output-dir "$EWP_P7_SPLIT/output"
```

Expected terminal structure:

```text
PROCESS p2-01-split-speakers
RESULT .../p2-01-split-speakers_results.json
WROTE .../p2-01-split-speakers_transcript.txt
WROTE .../p2-01-split-speakers_subtitles.srt
WROTE .../p2-01-split-speakers_subtitles.vtt
```

ASR and alignment should load twice, once for each channel, and each stage must finish
before the next stream begins. A diarization log, download, token request, traceback,
CUDA OOM, or concurrent model pass is a failure. The accepted Lightning checkpoint
upgrade notice and TF32 reproducibility warning may recur.

## 4. Run grouped-source transcription offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P7_GROUP/input" \
    --config "$EWP_P7_GROUP/transcriber.toml" \
    --output-dir "$EWP_P7_GROUP/output"
```

Expected summary structure:

```text
COMPLETED p7-group
SUMMARY completed=1 skipped=0 failed=0 cancelled=0
```

The same sequential, local-only, non-diarized requirements apply.

### Recovery from the pre-fix export failure

The first target execution at commit `025e56e` completed both ML streams and published
each canonical JSON, then rejected derived subtitles because chunks from overlapping
speaker segments were not globally ordered. Commit `33060f6` fixes cue ordering and
applies on-change labels after ordering.

If continuing that existing sandbox, do not delete results and do not use `--force`.
Update the application and repeat sections 3 and 4 exactly:

```bash
cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe \
    "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav" \
    --config "$EWP_P7_SPLIT/transcriber.toml" \
    --output-dir "$EWP_P7_SPLIT/output"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P7_GROUP/input" \
    --config "$EWP_P7_GROUP/transcriber.toml" \
    --output-dir "$EWP_P7_GROUP/output"
```

Both jobs must report the canonical `RESULT` as `SKIP`/`SKIPPED` and the three missing
exports as `WROTE`, without model-loading logs. This demonstrates the canonical-first
publication boundary and model-free export recovery. Batch output summarizes the grouped
job but does not list its individually recovered exports; section 5 verifies those files.
Continue with section 5 afterward.

## 5. Validate canonical results and labelled exports

```bash
uv run --locked python - "$EWP_P7_ROOT" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
schema = json.loads((Path.cwd() / "schemas/results.schema.json").read_text(encoding="utf-8"))
cases = {
    "split": (
        root / "split/output/p2-01-split-speakers_results.json",
        "split_channels",
        1,
        ["Speaker1", "Speaker2"],
    ),
    "group": (
        root / "group/output/p7-group_results.json",
        "file_group",
        2,
        ["Left", "Right"],
    ),
}

for case, (path, topology, source_count, labels) in cases.items():
    result = json.loads(path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(result)) == []
    assert result["status"] == "completed"
    assert result["episode"]["source_topology"] == topology
    assert len(result["sources"]) == source_count
    assert [speaker["speaker_label"] for speaker in result["speakers"]] == labels
    assert [speaker["speaker_id"] for speaker in result["speakers"]] == [
        "speaker_001", "speaker_002"
    ]
    assert len(result["processing"]["stages"]) == 8
    assert [stage["details"]["stream_index"] for stage in result["processing"]["stages"]] \
        == [1, 1, 1, 1, 2, 2, 2, 2]
    assert {model["role"] for model in result["processing"]["models"]} \
        == {"asr", "alignment"}
    assert any(segment["overlap"] for segment in result["transcript"]["segments"])
    assert any(len(segment["active_speaker_ids"]) == 2
               for segment in result["transcript"]["segments"])
    words = [word for segment in result["transcript"]["segments"]
             for word in segment["words"]]
    assert words
    assert {word["speaker_id"] for word in words} == {"speaker_001", "speaker_002"}
    for suffix in ("transcript.txt", "subtitles.srt", "subtitles.vtt"):
        export = path.with_name(path.name.replace("results.json", suffix))
        assert export.is_file() and export.stat().st_size > 0, export
    transcript = path.with_name(path.name.replace("results.json", "transcript.txt")) \
        .read_text(encoding="utf-8")
    assert all(f"{label}:" in transcript for label in labels)
    print(
        f"PASS {case}: sources={source_count}, speakers=2, "
        f"segments={len(result['transcript']['segments'])}, words={len(words)}"
    )
print("canonical topology, overlap, attribution, provenance, and exports: PASS")
PY
```

The test deliberately requires overlap in both representations because P2-01 contains
approximately six seconds of simultaneous speech. It does not compare WER/CER; those
metrics require the manually verified references planned for the larger corpus.

## 6. Verify duplicate replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe \
    "$EWP_P7_SPLIT/input/p2-01-split-speakers.wav" \
    --config "$EWP_P7_SPLIT/transcriber.toml" \
    --output-dir "$EWP_P7_SPLIT/output"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P7_GROUP/input" \
    --config "$EWP_P7_GROUP/transcriber.toml" \
    --output-dir "$EWP_P7_GROUP/output"

test -z "$(find "$EWP_P7_SPLIT/work" "$EWP_P7_GROUP/work" \
    -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "Phase 7 workdir cleanup: PASS"
```

Both canonical results and all six exports must report `SKIP`, without model-loading
logs. No job workdir may remain.

If this sandbox experienced the pre-fix export failure, the original processes correctly
retained their marker-owned workdirs for diagnostics. Duplicate recovery does not own and
therefore does not remove those older directories. Clean only the two workdirs identified
by their published canonical results:

```bash
uv run --locked python - "$EWP_P7_ROOT" <<'PY'
import sys
from pathlib import Path

from ewp_transcripts.domain import WorkDirectory, load_canonical_result
from ewp_transcripts.workdirs import MARKER_FILENAME, cleanup_work_directory

root = Path(sys.argv[1])
cases = (
    (root / "split/work", root / "split/output/p2-01-split-speakers_results.json"),
    (root / "group/work", root / "group/output/p7-group_results.json"),
)
for work_root, result_path in cases:
    result = load_canonical_result(result_path)
    path = work_root / str(result.run_id) / result.job_id
    cleanup_work_directory(
        WorkDirectory(
            work_root=work_root,
            run_id=result.run_id,
            job_id=result.job_id,
            path=path,
            marker_path=path / MARKER_FILENAME,
        )
    )
    print(f"cleaned retained workdir: {result.job_id}")
print("retained Phase 7 workdir cleanup: PASS")
PY

test -z "$(find "$EWP_P7_SPLIT/work" "$EWP_P7_GROUP/work" \
    -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "Phase 7 workdir cleanup: PASS"
```

## 7. Record evidence

```bash
sha256sum "$EWP_P7_SPLIT/output"/*
sha256sum "$EWP_P7_GROUP/output"/*
find "$EWP_P7_ROOT" -type f -name '.*.tmp' -print
git status --short
```

No temporary file may remain. Repository status must be empty except for
`LICENSE_SKETCH.TXT` if present locally.

Send back:

- quality gate and GPU line;
- source and derived fixture hashes plus ffprobe summaries;
- inspection and dry-run decisions;
- both first-run and duplicate terminal summaries;
- if applicable, the model-free recovery summaries;
- all PASS lines and actual segment/word counts;
- every output hash;
- repository status and any unexpected warning, download, traceback, diarization log,
  or CUDA error.

Do not send audio, model files, tokens, or full transcript content.
