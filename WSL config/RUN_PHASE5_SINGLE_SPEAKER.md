# Run the Phase 5 single-speaker production gate

This gate validates the real `transcriber transcribe` path on P0-01: inspection,
reservation, isolated working audio, pinned local large-v2 ASR, Polish alignment,
canonical publication, configured exports, cleanup, duplicate skipping, and a forced
offline replay. It does not use diarization and must not download a model.

## 0. Update and prepare an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P5_INPUT="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P5_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase5-single-XXXXXXXX)"
export EWP_P5_OUTPUT="$EWP_P5_ROOT/output"
export EWP_P5_CONFIG="$EWP_P5_ROOT/transcriber.toml"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -s "$EWP_P5_INPUT" && echo "P0-01 input: present"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P5_ROOT/work" > "$EWP_P5_CONFIG"
printf 'sandbox=%s\n' "$EWP_P5_ROOT"
```

The log must contain commit `1f36037` or later. At that commit, 179 tests should pass.
Treat the named checks as authoritative if later commits legitimately add tests.

## 1. Verify the exact local runtime inputs

```bash
uv run --locked python - "$EWP_P5_CONFIG" <<'PY'
import sys
from pathlib import Path

from ewp_transcripts.config import load_config

config = load_config(explicit_path=Path(sys.argv[1]))
expected = {
    "ASR": (
        config.models.asr_snapshot_path,
        "f0fe81560cb8b68660e564f55dd99207059c092e",
    ),
    "alignment": (
        config.models.alignment_snapshot_path,
        "6b1cea36bd8bc5f65ec8081667cd9c0207d51970",
    ),
}
for label, (path, revision) in expected.items():
    assert path.is_dir(), path
    assert path.name == revision, (path, revision)
    print(f"{label} snapshot: present ({revision})")
assert config.models.allow_network_downloads_during_transcription is False
assert config.general.offline is True
print("local-only configuration: PASS")
PY

test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
```

Stop if either snapshot is absent or its directory name differs from the pinned
revision. Do not set `HF_TOKEN` and do not let transcription acquire a replacement.

## 2. Run the first complete production transcription

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_INPUT" \
    --config "$EWP_P5_CONFIG" \
    --output-dir "$EWP_P5_OUTPUT"
```

Expected terminal structure:

```text
PROCESS p0-01-single-short
RESULT .../p0-01-single-short_results.json
WROTE .../p0-01-single-short_transcript.txt
WROTE .../p0-01-single-short_subtitles.srt
WROTE .../p0-01-single-short_subtitles.vtt
```

WhisperX/Pyannote may repeat the already accepted Lightning checkpoint and TF32
warnings. A download, token request, missing-snapshot fallback, traceback, or CUDA OOM
is a failure.

### Recovery from the pre-fix subtitle failure

The first target run at commit `0a54411` completed ASR/alignment and published canonical
JSON, then failed because one real segment needed more than two wrapped subtitle lines.
If continuing that same sandbox after pulling the fix, rerun the command above. It must
report `SKIP`, retain the existing canonical result, and write the missing TXT/SRT/VTT
exports without loading models. Then remove only the marker-verified retained workspace:

```bash
uv run --locked python - "$EWP_P5_ROOT" <<'PY'
import sys
from pathlib import Path

from ewp_transcripts.domain import WorkDirectory, load_canonical_result
from ewp_transcripts.workdirs import MARKER_FILENAME, cleanup_work_directory

root = Path(sys.argv[1])
result = load_canonical_result(root / "output/p0-01-single-short_results.json")
path = root / "work" / str(result.run_id) / result.job_id
workspace = WorkDirectory(
    work_root=root / "work",
    run_id=result.run_id,
    job_id=result.job_id,
    path=path,
    marker_path=path / MARKER_FILENAME,
)
cleanup_work_directory(workspace)
print("retained failed-export workspace cleanup: PASS")
PY
```

Do not delete the sandbox or canonical result. A fresh sandbox does not need this
recovery subsection.

## 3. Validate canonical output and exports

```bash
uv run --locked python - "$EWP_P5_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
repo = Path.cwd()
job = "p0-01-single-short"
expected = (
    f"{job}_results.json",
    f"{job}_transcript.txt",
    f"{job}_subtitles.srt",
    f"{job}_subtitles.vtt",
)
for name in expected:
    assert (root / name).is_file() and (root / name).stat().st_size > 0, name
    print(f"present: {name}")

result = json.loads((root / f"{job}_results.json").read_text(encoding="utf-8"))
schema = json.loads((repo / "schemas/results.schema.json").read_text(encoding="utf-8"))
assert list(Draft202012Validator(schema).iter_errors(result)) == []
assert result["status"] == "completed"
assert result["result_version"] == 1
assert result["episode"]["language"] == "pl"
assert len(result["sources"]) == 1
assert len(result["speakers"]) == 1
assert result["speakers"][0]["speaker_id"] == "speaker_001"
models = {item["role"]: item for item in result["processing"]["models"]}
assert models["asr"]["revision"] == "f0fe81560cb8b68660e564f55dd99207059c092e"
assert models["alignment"]["revision"] == "6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
segments = result["transcript"]["segments"]
assert segments
words = [word for segment in segments for word in segment["words"]]
assert words
assert all(word["start_ms"] <= word["end_ms"] for word in words)
assert all(word["speaker_id"] == "speaker_001" for word in words)
print(f"PASS canonical result: segments={len(segments)}, words={len(words)}")
print("PASS pinned model provenance")
PY
```

Do not send the generated transcript text. A word count near the earlier 226-word
baseline is expected, but schema validity, complete timestamps, and manual review are
authoritative.

## 4. Verify duplicate skipping without model loading

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_INPUT" \
    --config "$EWP_P5_CONFIG" \
    --output-dir "$EWP_P5_OUTPUT"
```

Expected:

```text
SKIP p0-01-single-short
RESULT .../p0-01-single-short_results.json
```

There must be no model-loading messages and no `WROTE` line.

## 5. Run a forced offline replay

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_INPUT" \
    --config "$EWP_P5_CONFIG" \
    --output-dir "$EWP_P5_OUTPUT" \
    --force
```

This must report `PROCESS`, publish `_results_v002.json`, and write one coordinated
`_v002` TXT/SRT/VTT set. Compare the stable transcript-bearing exports:

```bash
sha256sum \
    "$EWP_P5_OUTPUT/p0-01-single-short_transcript.txt" \
    "$EWP_P5_OUTPUT/p0-01-single-short_transcript_v002.txt"

cmp \
    "$EWP_P5_OUTPUT/p0-01-single-short_transcript.txt" \
    "$EWP_P5_OUTPUT/p0-01-single-short_transcript_v002.txt" \
    && echo "offline transcript replay: identical"
```

The canonical JSON files are expected to differ because run IDs, timestamps, and stage
durations are execution metadata.

## 6. Verify final state and record evidence

```bash
test -z "$(find "$EWP_P5_OUTPUT" -maxdepth 1 \
    \( -name '*.partial.json' -o -name '*.failed.json' -o -name '.*.tmp' \) -print)" \
    && echo "terminal output state: PASS"

test -z "$(find "$EWP_P5_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "successful workdir cleanup: PASS"

sha256sum "$EWP_P5_OUTPUT"/*
git status --short
```

Repository status must be empty except for the owner's intentionally untracked
`LICENSE_SKETCH.TXT`, if present locally. Keep this sandbox until the evidence has been
recorded; it is external test data and must not be committed.

Send back:

- the quality-gate summary and GPU status line;
- snapshot and local-only `PASS` lines;
- first-run, duplicate-run, and forced-run terminal output;
- canonical validation and final-state `PASS` lines;
- transcript comparison result and all final SHA-256 lines;
- repository status and any unexpected warning or error.

Do not send audio, model files, tokens, or transcript content.
