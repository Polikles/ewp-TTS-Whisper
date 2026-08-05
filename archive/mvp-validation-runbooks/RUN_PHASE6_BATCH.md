# Run the Phase 6 sequential batch gate

This gate validates deterministic directory processing with one GPU job at a time. A
success sandbox checks natural order and duplicate replay. A separate controlled sandbox
puts an unsupported mixed-stereo file before a valid mono file to prove failure isolation,
continue-after-error behavior, exit code 5, and retained-workspace cleanup.

## 0. Update and prepare external batch inputs

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P6_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase6-batch-XXXXXXXX)"
export EWP_P6_SUCCESS="$EWP_P6_ROOT/success"
export EWP_P6_FAILURE="$EWP_P6_ROOT/failure"
mkdir -p "$EWP_P6_SUCCESS/input" "$EWP_P6_FAILURE/input"

cp "$EWP_TESTDATA/audio/p0-01-single-short.wav" \
    "$EWP_P6_SUCCESS/input/episode2.wav"
cp "$EWP_TESTDATA/audio/p0-02-single-representative.wav" \
    "$EWP_P6_SUCCESS/input/episode10.wav"
cp "$EWP_TESTDATA/audio/p2-03-mixed-stereo.wav" \
    "$EWP_P6_FAILURE/input/episode2_mixed.wav"
cp "$EWP_TESTDATA/audio/p0-01-single-short.wav" \
    "$EWP_P6_FAILURE/input/episode10_mono.wav"

printf '[runtime]\nwork_root = "%s"\n' "$EWP_P6_SUCCESS/work" \
    > "$EWP_P6_SUCCESS/transcriber.toml"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P6_FAILURE/work" \
    > "$EWP_P6_FAILURE/transcriber.toml"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P6_ROOT"
```

The log must contain commit `d1a23e7` or later. At that commit, 186 tests should pass.
All copied inputs and generated outputs remain outside the repository.

## 1. Verify copied input identity and natural plan order

```bash
sha256sum "$EWP_P6_SUCCESS/input"/* "$EWP_P6_FAILURE/input"/*

uv run --locked transcriber dry-run "$EWP_P6_SUCCESS/input" \
    --speaker-count 1 \
    --output-dir "$EWP_P6_SUCCESS/output"
```

Expected source hashes:

```text
7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33  episode2.wav
32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a  episode10.wav
c93657e1501e293f72ef8d18e1042dfe574fc66ebca5020152dc3470f7fac27e  episode2_mixed.wav
7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33  episode10_mono.wav
```

The dry run must list `episode2` before `episode10`, proving numeric natural order rather
than lexical `episode10`/`episode2` order.

## 2. Run the two-file batch offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P6_SUCCESS/input" \
    --config "$EWP_P6_SUCCESS/transcriber.toml" \
    --output-dir "$EWP_P6_SUCCESS/output"
```

Expected summary structure:

```text
COMPLETED episode2
COMPLETED episode10
SUMMARY completed=2 skipped=0 failed=0 cancelled=0
```

Model logs for `episode10` must begin only after `episode2` completes. A download, token
request, traceback, CUDA OOM, or overlapping GPU job is a failure.

## 3. Validate successful results and cleanup

```bash
uv run --locked python - "$EWP_P6_SUCCESS" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
schema = json.loads((Path.cwd() / "schemas/results.schema.json").read_text(encoding="utf-8"))
counts = {}
for job in ("episode2", "episode10"):
    result_path = root / "output" / f"{job}_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(result)) == []
    assert result["status"] == "completed"
    assert result["result_version"] == 1
    words = [word for segment in result["transcript"]["segments"] for word in segment["words"]]
    assert words and all(word["speaker_id"] == "speaker_001" for word in words)
    counts[job] = len(words)
    for suffix in ("transcript.txt", "subtitles.srt", "subtitles.vtt"):
        path = root / "output" / f"{job}_{suffix}"
        assert path.is_file() and path.stat().st_size > 0, path
assert not list((root / "output").glob("*.partial.json"))
assert not list((root / "output").glob("*.failed.json"))
print(f"successful batch words: {counts}")
print("successful batch schemas and exports: PASS")
PY

test -z "$(find "$EWP_P6_SUCCESS/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "successful batch workdir cleanup: PASS"
```

The earlier baselines suggest approximately 226 and 612 words respectively. Record the
actual counts; schema validity and complete words are authoritative.

## 4. Verify duplicate batch replay without model loading

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P6_SUCCESS/input" \
    --config "$EWP_P6_SUCCESS/transcriber.toml" \
    --output-dir "$EWP_P6_SUCCESS/output"
```

Both jobs and all six exports must report `SKIP`, in `episode2`, `episode10` order. The
summary must be `completed=0 skipped=2 failed=0 cancelled=0`, with no model-loading log.

## 5. Run the controlled partial-failure batch

```bash
set +e
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P6_FAILURE/input" \
    --config "$EWP_P6_FAILURE/transcriber.toml" \
    --output-dir "$EWP_P6_FAILURE/output" \
    > "$EWP_P6_FAILURE/batch.stdout" \
    2> "$EWP_P6_FAILURE/batch.stderr"
EWP_P6_FAILURE_EXIT=$?
set -e

cat "$EWP_P6_FAILURE/batch.stdout"
cat "$EWP_P6_FAILURE/batch.stderr"
printf 'partial failure exit=%s\n' "$EWP_P6_FAILURE_EXIT"
test "$EWP_P6_FAILURE_EXIT" -eq 5 && echo "partial failure exit code: PASS"
! grep -q 'Traceback' "$EWP_P6_FAILURE/batch.stderr" \
    && echo "partial failure sanitization: PASS"
```

Expected ordered summary:

```text
FAILED episode2_mixed
  ERROR UNSUPPORTED_PIPELINE_SCOPE_ERROR: Single-speaker pipeline supports mono or one selected working channel
COMPLETED episode10_mono
SUMMARY completed=1 skipped=0 failed=1 cancelled=0
```

The first job must create failed state and must not prevent the later mono job from
running to completion.

## 6. Validate isolated states and clean the failed workspace

```bash
uv run --locked python - "$EWP_P6_FAILURE" <<'PY'
import json
import sys
from pathlib import Path
from uuid import UUID

from jsonschema import Draft202012Validator

from ewp_transcripts.domain import WorkDirectory
from ewp_transcripts.workdirs import MARKER_FILENAME, cleanup_work_directory

root = Path(sys.argv[1])
output = root / "output"
failed_path = output / "episode2_mixed_results.failed.json"
failed = json.loads(failed_path.read_text(encoding="utf-8"))
assert failed["status"] == "failed"
assert failed["failure_code"] == "UNSUPPORTED_PIPELINE_SCOPE_ERROR"
assert not (output / "episode2_mixed_results.json").exists()
assert not list(output.glob("*.partial.json"))

result_path = output / "episode10_mono_results.json"
result = json.loads(result_path.read_text(encoding="utf-8"))
schema = json.loads((Path.cwd() / "schemas/results.schema.json").read_text(encoding="utf-8"))
assert list(Draft202012Validator(schema).iter_errors(result)) == []
assert result["status"] == "completed"

run_id = UUID(failed["run_id"])
path = root / "work" / str(run_id) / failed["job_id"]
cleanup_work_directory(
    WorkDirectory(
        work_root=root / "work",
        run_id=run_id,
        job_id=failed["job_id"],
        path=path,
        marker_path=path / MARKER_FILENAME,
    )
)
print("isolated failed and completed states: PASS")
print("retained failed workspace cleanup: PASS")
PY

test -z "$(find "$EWP_P6_FAILURE/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "partial-failure batch workdirs cleaned: PASS"
```

## 7. Record evidence

```bash
sha256sum "$EWP_P6_SUCCESS/output"/*
sha256sum "$EWP_P6_FAILURE/output"/*
find "$EWP_P6_ROOT" -type f -name '.*.tmp' -print
git status --short
```

No temporary file may remain. Repository status must be empty except for
`LICENSE_SKETCH.TXT` if present locally.

Send back:

- quality gate, GPU line, source hashes, and dry-run order;
- first and duplicate success-batch summaries;
- actual word counts and all PASS lines;
- captured partial-failure output, exit code, and sanitization result;
- state/cleanup PASS lines and every output hash;
- repository status and any unexpected warning, download, traceback, or CUDA error.

Do not send audio, model files, tokens, or transcript content.
