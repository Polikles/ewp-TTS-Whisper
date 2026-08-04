# Run Phase 9 SIGINT cancellation and restart validation

This gate interrupts a real GPU transcription inside a two-job directory batch. It
proves that the active job becomes durably `cancelled`, no final result is published,
the next queued job never starts, diagnostic workspace data is retained, and an
ordinary restart processes both jobs safely from the beginning.

All mutable files remain under a fresh external sandbox. The procedure signals only the
recorded background transcriber PID; do not use process-name matching or a broad kill.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_INTERRUPT_LONG="$EWP_TESTDATA/audio/p9-03-long-two-speakers-polish.mp3"
export EWP_P9_INTERRUPT_SHORT="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P9_INTERRUPT_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-interrupt-XXXXXXXX)"
export EWP_P9_INTERRUPT_INPUT="$EWP_P9_INTERRUPT_ROOT/input"
export EWP_P9_INTERRUPT_OUTPUT="$EWP_P9_INTERRUPT_ROOT/output"
export EWP_P9_INTERRUPT_EVIDENCE="$EWP_P9_INTERRUPT_ROOT/evidence"
export EWP_P9_INTERRUPT_CONFIG="$EWP_P9_INTERRUPT_ROOT/transcriber.toml"
mkdir -p \
    "$EWP_P9_INTERRUPT_INPUT" \
    "$EWP_P9_INTERRUPT_OUTPUT" \
    "$EWP_P9_INTERRUPT_EVIDENCE"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_INTERRUPT_ROOT/work" \
    > "$EWP_P9_INTERRUPT_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P9_INTERRUPT_ROOT"
```

The log must contain commit `d3d3819` or later. At that commit, 231 tests should pass.

## 1. Prepare and verify the controlled two-job batch

```bash
cp "$EWP_P9_INTERRUPT_LONG" "$EWP_P9_INTERRUPT_INPUT/episode01-long.mp3"
cp "$EWP_P9_INTERRUPT_SHORT" "$EWP_P9_INTERRUPT_INPUT/episode02-never-started.wav"

sha256sum "$EWP_P9_INTERRUPT_INPUT"/*

uv run --locked transcriber dry-run "$EWP_P9_INTERRUPT_INPUT" \
    --speaker-count 2 --output-dir "$EWP_P9_INTERRUPT_OUTPUT"
```

Accepted hashes:

```text
8039ac3b9b9e09491639dea73eae5a6f70f3beebaeb042a304666ed9606d9869  episode01-long.mp3
7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33  episode02-never-started.wav
```

The dry run must plan `episode01-long` before `episode02-never-started`. Both use exact
speaker count 2 so the restart uses one stable batch configuration; the second fixture
may identify fewer active clusters, but it must not run before cancellation.

## 2. Start transcription in the background and interrupt the active job

```bash
set +e
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P9_INTERRUPT_INPUT" \
    --config "$EWP_P9_INTERRUPT_CONFIG" \
    --speaker-count 2 \
    --output-dir "$EWP_P9_INTERRUPT_OUTPUT" \
    --non-interactive \
    > "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stdout.txt" \
    2> "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stderr.txt" &
export EWP_P9_INTERRUPT_PID=$!
set -e
printf 'transcriber pid=%s\n' "$EWP_P9_INTERRUPT_PID"
ps -o pid=,ppid=,stat=,args= -p "$EWP_P9_INTERRUPT_PID"

for attempt in $(seq 1 60); do
    if grep -q 'Performing voice activity detection' \
        "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stdout.txt"; then
        echo "active transcription observed: PASS"
        break
    fi
    if ! kill -0 "$EWP_P9_INTERRUPT_PID" 2>/dev/null; then
        echo "transcriber exited before SIGINT" >&2
        break
    fi
    sleep 1
done

grep -q 'Performing voice activity detection' \
    "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stdout.txt" \
    || { echo "active transcription was not observed" >&2; false; }
sleep 10
kill -INT "$EWP_P9_INTERRUPT_PID"

set +e
wait "$EWP_P9_INTERRUPT_PID"
export EWP_P9_INTERRUPT_EXIT=$?
set -e
printf 'interrupted exit=%s\n' "$EWP_P9_INTERRUPT_EXIT"
cat "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stdout.txt"
cat "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stderr.txt"
```

The recorded command must still be alive when signalled. Do not substitute `pkill`,
`killall`, an unresolved process substitution, or a guessed PID. Expected exit code is
6, with one cancelled job and no completed, skipped, or failed job.

## 3. Validate durable cancellation and queue stop

```bash
test "$EWP_P9_INTERRUPT_EXIT" -eq 6 && echo "SIGINT exit code: PASS"

uv run --locked python - \
    "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stdout.txt" \
    "$EWP_P9_INTERRUPT_OUTPUT" \
    "$EWP_P9_INTERRUPT_ROOT/work" <<'PY'
import json
import sys
from pathlib import Path

stdout_path = Path(sys.argv[1])
output = Path(sys.argv[2])
work_root = Path(sys.argv[3])
text = stdout_path.read_text(encoding="utf-8")

assert "CANCELLED episode01-long" in text
assert "ERROR USER_CANCELLED: Transcription cancelled by user" in text
assert "SUMMARY completed=0 skipped=0 failed=0 cancelled=1" in text
assert "episode02-never-started" not in text

failed = output / "episode01-long_results.failed.json"
assert failed.is_file()
state = json.loads(failed.read_text(encoding="utf-8"))
assert state["status"] == "cancelled"
assert state["failure_code"] == "USER_CANCELLED"
assert state["result_version"] == 1
assert not (output / "episode01-long_results.json").exists()
assert not (output / "episode02-never-started_results.json").exists()
assert not list(output.glob("*.partial.json"))

workdirs = [path for path in work_root.glob("*/*") if path.is_dir()]
assert len(workdirs) == 1, workdirs
assert workdirs[0].name == "episode01-long"
print(f"PASS durable cancellation: retained_workdir={workdirs[0]}")
PY

export EWP_P9_CANCELLED_HASH="$(sha256sum \
    "$EWP_P9_INTERRUPT_OUTPUT/episode01-long_results.failed.json" | cut -d' ' -f1)"
printf 'cancelled-state sha256=%s\n' "$EWP_P9_CANCELLED_HASH"
```

The stderr may contain accepted dependency diagnostics, but must not contain an
application traceback:

```bash
! grep -q 'Traceback' "$EWP_P9_INTERRUPT_EVIDENCE/interrupted.stderr.txt" \
    && echo "SIGINT output sanitization: PASS"
```

## 4. Restart normally from the beginning

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P9_INTERRUPT_INPUT" \
    --config "$EWP_P9_INTERRUPT_CONFIG" \
    --speaker-count 2 \
    --output-dir "$EWP_P9_INTERRUPT_OUTPUT" \
    --non-interactive
```

Expected outcome:

- `episode01-long` processes as result version 2 because cancelled version 1 remains
  immutable;
- `episode02-never-started` processes as result version 1;
- summary is `completed=2 skipped=0 failed=0 cancelled=0`.

## 5. Validate restart results and cancellation immutability

```bash
uv run --locked python - \
    "$EWP_P9_INTERRUPT_OUTPUT" "$EWP_P9_CANCELLED_HASH" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

output = Path(sys.argv[1])
cancelled_hash = sys.argv[2]
schema = json.loads(Path("schemas/results.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)

cancelled = output / "episode01-long_results.failed.json"
assert hashlib.sha256(cancelled.read_bytes()).hexdigest() == cancelled_hash
cancelled_state = json.loads(cancelled.read_text(encoding="utf-8"))
assert cancelled_state["status"] == "cancelled"

expected = {
    "episode01-long_results_v002.json": 2,
    "episode02-never-started_results.json": 1,
}
for filename, version in expected.items():
    result = json.loads((output / filename).read_text(encoding="utf-8"))
    validator.validate(result)
    assert result["status"] == "completed"
    assert result["result_version"] == version
    assert result["transcript"]["segments"]
    print(f"PASS restart result: {filename}")

assert not list(output.glob("*.partial.json"))
print("cancelled-state immutability: PASS")
PY
```

## 6. Duplicate replay and retained-workspace cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P9_INTERRUPT_INPUT" \
    --config "$EWP_P9_INTERRUPT_CONFIG" \
    --speaker-count 2 \
    --output-dir "$EWP_P9_INTERRUPT_OUTPUT" \
    --non-interactive

uv run --locked transcriber clean all-workdirs \
    --config "$EWP_P9_INTERRUPT_CONFIG" --yes --older-than 0

test -z "$(find "$EWP_P9_INTERRUPT_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "interruption workdir cleanup: PASS"
sha256sum "$EWP_P9_INTERRUPT_OUTPUT"/*results*.json
git status --short
```

Both completed results and their exports must report `SKIP` without model loading. The
marker-verified cleanup must remove the one retained cancelled workspace but preserve
all output artifacts. Repository status must be empty.

## 7. Evidence to return

Return:

- Step 0 test count, token check, GPU line, and sandbox path;
- two accepted input hashes and dry-run order;
- recorded PID line, active-transcription PASS, exit code, cancellation summary, and
  sanitized stderr result;
- durable cancellation PASS, retained workdir, and cancelled-state hash;
- restart and duplicate summaries plus restart/immutability PASS lines;
- cleanup PASS, final state/result hashes, and empty repository status.

Do not send audio, transcripts, full canonical JSON, workdir contents, tokens, or model
files.
