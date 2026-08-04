# Run Phase 9 ten-job batch stability validation

This gate processes ten equal short recordings through one production directory-batch
process. It checks natural ordering, continued completion, per-job stage timing, bounded
GPU memory, post-run GPU-memory release, duplicate replay, and workspace cleanup.

The copied inputs and all generated evidence remain in the external test-data tree. Do
not commit them to the application repository.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_BATCH_SOURCE="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P9_BATCH_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-batch-XXXXXXXX)"
export EWP_P9_BATCH_INPUT="$EWP_P9_BATCH_ROOT/input"
export EWP_P9_BATCH_OUTPUT="$EWP_P9_BATCH_ROOT/output"
export EWP_P9_BATCH_EVIDENCE="$EWP_P9_BATCH_ROOT/evidence"
export EWP_P9_BATCH_CONFIG="$EWP_P9_BATCH_ROOT/transcriber.toml"
mkdir -p "$EWP_P9_BATCH_INPUT" "$EWP_P9_BATCH_OUTPUT" "$EWP_P9_BATCH_EVIDENCE"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_BATCH_ROOT/work" \
    > "$EWP_P9_BATCH_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P9_BATCH_ROOT"
```

The log must contain commit `38d7ec5` or later. At that commit, 231 tests should pass.

## 1. Prepare ten immutable-equivalent external inputs

```bash
test -s "$EWP_P9_BATCH_SOURCE" && echo "P0-01 source: present"
sha256sum "$EWP_P9_BATCH_SOURCE"

for number in $(seq -w 1 10); do
    cp "$EWP_P9_BATCH_SOURCE" "$EWP_P9_BATCH_INPUT/episode$number.wav"
done

sha256sum "$EWP_P9_BATCH_INPUT"/*.wav
```

The source and every copy must have this accepted hash:

```text
7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33
```

Copies deliberately have distinct job IDs while retaining identical audio complexity,
making chronological resource and timing comparisons meaningful.

## 2. Verify the batch plan

```bash
uv run --locked transcriber dry-run "$EWP_P9_BATCH_INPUT" \
    --speaker-count 1 --output-dir "$EWP_P9_BATCH_OUTPUT" \
    > "$EWP_P9_BATCH_EVIDENCE/dry-run.txt"
cat "$EWP_P9_BATCH_EVIDENCE/dry-run.txt"

uv run --locked python - "$EWP_P9_BATCH_EVIDENCE/dry-run.txt" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
jobs = re.findall(r"^PROCESS (episode\d+)$", text, flags=re.MULTILINE)
assert jobs == [f"episode{number:02d}" for number in range(1, 11)], jobs
print("ten-job natural-order plan: PASS")
PY
```

The dry run must not create a result, export, or work directory.

## 3. Run one measured ten-job batch offline

Start the GPU sampler, retain two seconds of pre-run baseline, run the batch through one
CLI process, and retain five seconds of post-run samples:

```bash
nvidia-smi \
    --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total \
    --format=csv,noheader,nounits --loop=1 \
    > "$EWP_P9_BATCH_EVIDENCE/batch.gpu.csv" &
export EWP_P9_BATCH_MONITOR_PID=$!
sleep 2

set +e
/usr/bin/time -v -o "$EWP_P9_BATCH_EVIDENCE/batch.time.txt" \
    env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P9_BATCH_INPUT" \
    --config "$EWP_P9_BATCH_CONFIG" \
    --speaker-count 1 \
    --output-dir "$EWP_P9_BATCH_OUTPUT" \
    --non-interactive \
    > "$EWP_P9_BATCH_EVIDENCE/batch.stdout.txt" \
    2> "$EWP_P9_BATCH_EVIDENCE/batch.stderr.txt"
export EWP_P9_BATCH_EXIT=$?
sleep 5
kill "$EWP_P9_BATCH_MONITOR_PID" 2>/dev/null
wait "$EWP_P9_BATCH_MONITOR_PID" 2>/dev/null
set -e

printf 'batch exit=%s\n' "$EWP_P9_BATCH_EXIT"
cat "$EWP_P9_BATCH_EVIDENCE/batch.stdout.txt"
cat "$EWP_P9_BATCH_EVIDENCE/batch.stderr.txt"
```

Exit code must be zero and the summary must report exactly ten completed jobs. A
download, token request, traceback, CUDA OOM, failed/cancelled job, or early stop fails
the gate. Previously accepted dependency warnings may recur.

## 4. Validate ordering, results, schemas, and per-job stage timings

```bash
uv run --locked python - \
    "$EWP_P9_BATCH_EVIDENCE/batch.stdout.txt" \
    "$EWP_P9_BATCH_OUTPUT" <<'PY'
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

stdout_path = Path(sys.argv[1])
output_root = Path(sys.argv[2])
text = stdout_path.read_text(encoding="utf-8")
jobs = re.findall(r"^COMPLETED (episode\d+)$", text, flags=re.MULTILINE)
expected = [f"episode{number:02d}" for number in range(1, 11)]
assert jobs == expected, jobs
assert "SUMMARY completed=10 skipped=0 failed=0 cancelled=0" in text

schema = json.loads(Path("schemas/results.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)
stage_totals = []
for job in expected:
    result_path = output_root / f"{job}_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    validator.validate(result)
    assert result["status"] == "completed"
    assert len(result["speakers"]) == 1
    assert result["transcript"]["segments"]
    assert sum(len(segment["words"]) for segment in result["transcript"]["segments"]) > 0
    for suffix in ("_transcript.txt", "_subtitles.srt", "_subtitles.vtt"):
        export = output_root / f"{job}{suffix}"
        assert export.stat().st_size > 0, export
    stages = result["processing"]["stages"]
    durations = {stage["name"]: stage["duration_ms"] for stage in stages}
    stage_total = sum(durations.values())
    stage_totals.append(stage_total)
    print(f"PASS {job}: stage_total_ms={stage_total}, stages={durations}")

first_half = sum(stage_totals[:5]) / 5
second_half = sum(stage_totals[5:]) / 5
assert second_half <= first_half * 1.5, (first_half, second_half)
print(
    f"per-job timing stability: PASS first_half_mean_ms={first_half:.1f} "
    f"second_half_mean_ms={second_half:.1f}"
)
PY
```

The 50% timing tolerance detects gross degradation while allowing normal workstation
load variation. This comparison uses canonical stage durations, not only terminal wall
time.

## 5. Check GPU-memory stability and release

Ten equal-duration jobs make equal chronological bins a useful conservative comparison.
The first and last samples are pre/post-run baselines; each bin reports its absolute
sampled VRAM peak, including desktop allocation.

```bash
uv run --locked python - "$EWP_P9_BATCH_EVIDENCE/batch.gpu.csv" <<'PY'
import csv
import sys
from pathlib import Path

with Path(sys.argv[1]).open(encoding="utf-8", newline="") as handle:
    rows = list(csv.reader(handle))
used = [int(row[3].strip()) for row in rows if len(row) == 5]
assert len(used) >= 20, len(used)

active = used[2:-5]
assert len(active) >= 10
bins = []
for index in range(10):
    start = index * len(active) // 10
    end = (index + 1) * len(active) // 10
    bins.append(max(active[start:end]))

baseline_before = max(used[:2])
baseline_after = max(used[-5:])
first_three_peak = max(bins[:3])
last_three_peak = max(bins[-3:])
assert last_three_peak <= first_three_peak + 1024, bins
assert baseline_after <= baseline_before + 512, (baseline_before, baseline_after)

print(f"GPU bin peaks MiB: {bins}")
print(
    f"GPU memory stability: PASS baseline_before_mib={baseline_before} "
    f"baseline_after_mib={baseline_after}"
)
PY

grep -E 'Elapsed \(wall clock\)|Maximum resident set size' \
    "$EWP_P9_BATCH_EVIDENCE/batch.time.txt"
```

If desktop GPU usage changed during the run, report it rather than loosening thresholds
or rerunning until a preferred number appears.

## 6. Verify duplicate replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P9_BATCH_INPUT" \
    --config "$EWP_P9_BATCH_CONFIG" \
    --speaker-count 1 \
    --output-dir "$EWP_P9_BATCH_OUTPUT" \
    --non-interactive \
    > "$EWP_P9_BATCH_EVIDENCE/replay.stdout.txt" \
    2> "$EWP_P9_BATCH_EVIDENCE/replay.stderr.txt"

cat "$EWP_P9_BATCH_EVIDENCE/replay.stdout.txt"
cat "$EWP_P9_BATCH_EVIDENCE/replay.stderr.txt"

uv run --locked python - "$EWP_P9_BATCH_EVIDENCE/replay.stdout.txt" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
jobs = re.findall(r"^SKIPPED (episode\d+)$", text, flags=re.MULTILINE)
assert jobs == [f"episode{number:02d}" for number in range(1, 11)], jobs
assert "SUMMARY completed=0 skipped=10 failed=0 cancelled=0" in text
print("ten-job duplicate replay: PASS")
PY

test ! -s "$EWP_P9_BATCH_EVIDENCE/replay.stderr.txt" \
    && echo "duplicate replay loaded no models: PASS"
test -z "$(find "$EWP_P9_BATCH_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "batch stability workdir cleanup: PASS"
sha256sum "$EWP_P9_BATCH_OUTPUT"/*_results.json
git status --short
```

Repository status must be empty. `LICENSE_SKETCH.TXT` is absent in WSL and is not part
of this gate.

## 7. Evidence to return

Return:

- Step 0 test count, token check, initial GPU line, and sandbox path;
- accepted source/copy hashes and natural-order PASS;
- batch exit, completion summary, and accepted stderr warnings;
- ten per-job stage summaries and timing-stability PASS;
- GPU bin peaks, pre/post baseline, wall time, peak process RAM, and stability PASS;
- duplicate summary, cleanup PASS, ten result hashes, and empty repository status.

Do not send audio, transcripts, full canonical JSON, GPU sample files, tokens, or model
files.
