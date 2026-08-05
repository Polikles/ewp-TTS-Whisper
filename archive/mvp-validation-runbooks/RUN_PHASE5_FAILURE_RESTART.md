# Run the Phase 5 failed-state and restart gate

This final Phase 5 gate deliberately points ASR at a nonexistent local snapshot. It
verifies a sanitized pre-publication failure, immutable failed-state evidence, retained
workspace diagnostics, and a corrected from-the-beginning restart at the next free
version. It never modifies or removes the real model snapshot.

## 0. Update and create an isolated sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P5_FAIL_INPUT="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P5_FAIL_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase5-failure-XXXXXXXX)"
export EWP_P5_FAIL_OUTPUT="$EWP_P5_FAIL_ROOT/output"
export EWP_P5_FAIL_CONFIG="$EWP_P5_FAIL_ROOT/transcriber.toml"
export EWP_ASR_REV="f0fe81560cb8b68660e564f55dd99207059c092e"
export EWP_ALIGN_REV="6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
export EWP_ASR_VALID="$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-large-v2/snapshots/$EWP_ASR_REV"
export EWP_ALIGN_VALID="$HOME/.cache/huggingface/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/$EWP_ALIGN_REV"
export EWP_ASR_MISSING="$EWP_P5_FAIL_ROOT/missing-asr/$EWP_ASR_REV"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -s "$EWP_P5_FAIL_INPUT" && echo "P0-01 input: present"
test -d "$EWP_ASR_VALID" && echo "valid ASR snapshot: present"
test -d "$EWP_ALIGN_VALID" && echo "valid alignment snapshot: present"
test ! -e "$EWP_ASR_MISSING" && echo "controlled missing ASR path: absent"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

The log must contain commit `cb01b1f` or later. At that commit, 181 tests should pass.
Treat the named checks as authoritative if later commits legitimately add tests.

## 1. Write the deliberately failing configuration

```bash
printf '[models]\nasr_snapshot_path = "%s"\nalignment_snapshot_path = "%s"\n\n[runtime]\nwork_root = "%s"\n' \
    "$EWP_ASR_MISSING" "$EWP_ALIGN_VALID" "$EWP_P5_FAIL_ROOT/work" \
    > "$EWP_P5_FAIL_CONFIG"
```

The missing path still ends with the correct immutable revision, so strict configuration
is valid. Do not create that path and do not rename or move the real snapshot.

## 2. Run and capture the controlled failure

```bash
set +e
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_FAIL_INPUT" \
    --config "$EWP_P5_FAIL_CONFIG" \
    --output-dir "$EWP_P5_FAIL_OUTPUT" \
    > "$EWP_P5_FAIL_ROOT/failure.stdout" \
    2> "$EWP_P5_FAIL_ROOT/failure.stderr"
EWP_P5_FAIL_EXIT=$?
set -e

printf 'controlled failure exit=%s\n' "$EWP_P5_FAIL_EXIT"
cat "$EWP_P5_FAIL_ROOT/failure.stdout"
cat "$EWP_P5_FAIL_ROOT/failure.stderr"
test "$EWP_P5_FAIL_EXIT" -eq 4 && echo "controlled failure exit code: PASS"
! grep -q 'Traceback' "$EWP_P5_FAIL_ROOT/failure.stderr" \
    && echo "sanitized failure output: PASS"
```

Expected error text is `Pinned local ASR model snapshot is unavailable`. There must be
no model download, token request, transcript content, or Python traceback.

## 3. Verify failed state and retained workspace

```bash
uv run --locked python - "$EWP_P5_FAIL_ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
output = root / "output"
failed_path = output / "p0-01-single-short_results.failed.json"
assert failed_path.is_file()
failed = json.loads(failed_path.read_text(encoding="utf-8"))
assert failed["status"] == "failed"
assert failed["result_version"] == 1
assert failed["failure_code"] == "SPEECH_ENGINE_ERROR"
assert failed["failure_message"] == "Pinned local ASR model snapshot is unavailable"
assert not (output / "p0-01-single-short_results.json").exists()
assert not (output / "p0-01-single-short_results.partial.json").exists()
workspace = root / "work" / failed["run_id"] / failed["job_id"]
assert (workspace / ".ewp-transcripts-work.json").is_file()
assert (workspace / "source_001-working.wav").is_file()
print("failed state v1: PASS")
print("no final result after failure: PASS")
print("failed workspace retention: PASS")
PY

export EWP_P5_FAILED_HASH="$(sha256sum \
    "$EWP_P5_FAIL_OUTPUT/p0-01-single-short_results.failed.json" | cut -d' ' -f1)"
printf 'failed-state sha256=%s\n' "$EWP_P5_FAILED_HASH"
```

## 4. Correct only the configuration and restart offline

```bash
printf '[models]\nasr_snapshot_path = "%s"\nalignment_snapshot_path = "%s"\n\n[runtime]\nwork_root = "%s"\n' \
    "$EWP_ASR_VALID" "$EWP_ALIGN_VALID" "$EWP_P5_FAIL_ROOT/work" \
    > "$EWP_P5_FAIL_CONFIG"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_FAIL_INPUT" \
    --config "$EWP_P5_FAIL_CONFIG" \
    --output-dir "$EWP_P5_FAIL_OUTPUT"
```

The retry must run inference from the beginning, report `PROCESS`, and publish
`_results_v002.json` plus coordinated v2 TXT/SRT/VTT. Version 1 remains occupied only by
the immutable failed diagnostic.

## 5. Validate the successful restart and preserved failure

```bash
uv run --locked python - "$EWP_P5_FAIL_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
repo = Path.cwd()
result_path = root / "p0-01-single-short_results_v002.json"
result = json.loads(result_path.read_text(encoding="utf-8"))
schema = json.loads((repo / "schemas/results.schema.json").read_text(encoding="utf-8"))
assert list(Draft202012Validator(schema).iter_errors(result)) == []
assert result["status"] == "completed"
assert result["result_version"] == 2
assert len(result["transcript"]["segments"]) == 13
words = [word for segment in result["transcript"]["segments"] for word in segment["words"]]
assert len(words) == 226
for name in (
    "p0-01-single-short_transcript_v002.txt",
    "p0-01-single-short_subtitles_v002.srt",
    "p0-01-single-short_subtitles_v002.vtt",
):
    assert (root / name).is_file() and (root / name).stat().st_size > 0, name
assert (root / "p0-01-single-short_results.failed.json").is_file()
assert not list(root.glob("*.partial.json"))
print("successful restart v2: PASS")
print("failed-state preservation: PASS")
print("no running state: PASS")
PY

test "$(sha256sum "$EWP_P5_FAIL_OUTPUT/p0-01-single-short_results.failed.json" \
    | cut -d' ' -f1)" = "$EWP_P5_FAILED_HASH" \
    && echo "failed-state immutability: PASS"
```

## 6. Verify duplicate skip and clean the retained failed workspace

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P5_FAIL_INPUT" \
    --config "$EWP_P5_FAIL_CONFIG" \
    --output-dir "$EWP_P5_FAIL_OUTPUT"

uv run --locked python - "$EWP_P5_FAIL_ROOT" <<'PY'
import json
import sys
from pathlib import Path
from uuid import UUID

from ewp_transcripts.domain import WorkDirectory
from ewp_transcripts.workdirs import MARKER_FILENAME, cleanup_work_directory

root = Path(sys.argv[1])
failed = json.loads(
    (root / "output/p0-01-single-short_results.failed.json").read_text(encoding="utf-8")
)
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
print("retained failed workspace cleanup: PASS")
PY

test -z "$(find "$EWP_P5_FAIL_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "all job workdirs cleaned: PASS"
```

The duplicate invocation must skip v2 and all three exports without model loading.

## 7. Record evidence

```bash
sha256sum "$EWP_P5_FAIL_OUTPUT"/*
find "$EWP_P5_FAIL_OUTPUT" -maxdepth 1 \
    \( -name '*.partial.json' -o -name '.*.tmp' \) -print
git status --short
```

The preserved `.failed.json` is expected. No partial or temporary file may remain, and
repository status must be empty except for `LICENSE_SKETCH.TXT` if present locally.

Send back:

- quality-gate and input/snapshot checks;
- captured failure exit, sanitized error, and Step 3 PASS lines;
- restart and duplicate command output;
- Steps 5–6 PASS lines;
- all final hashes and repository status;
- any unexpected warning, traceback, download, or CUDA error.

Do not send audio, model files, tokens, or transcript content.
