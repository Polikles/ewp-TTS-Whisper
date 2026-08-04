# Validate release-readiness diagnostics

This runbook verifies that `doctor` checks the complete local runtime required by the MVP without loading transcription models or exposing `HF_TOKEN`.

## 0. Synchronize and run local gates

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
uv sync --locked
uv pip check
make check
git status --short
```

Expected commit: `0ad771c` or later. `git status --short` must be empty.

## 1. Verify the human-readable report

```bash
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
uv run --locked transcriber doctor
printf 'doctor exit=%s\n' "$?"
```

Expected checks are:

```text
python
wsl2
distribution
ffmpeg
ffprobe
gpu
cuda
asr_model
alignment_model
diarization_model
hf_token
```

All checks must report `PASS`, the exit code must be `0`, and no model should be loaded into GPU memory.

## 2. Verify the JSON report and secret handling

```bash
uv run --locked transcriber doctor --json-output > /tmp/ewp-doctor.json

uv run --locked python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path('/tmp/ewp-doctor.json').read_text(encoding='utf-8'))
expected = {
    'python', 'wsl2', 'distribution', 'ffmpeg', 'ffprobe', 'gpu', 'cuda',
    'asr_model', 'alignment_model', 'english_alignment_model',
    'diarization_model', 'hf_token',
}
checks = {item['code']: item for item in report['checks']}
assert report['ready'] is True
assert set(checks) == expected
assert all(item['status'] == 'pass' for item in checks.values())
assert checks['hf_token']['context']['present'] is False
print('doctor JSON readiness: PASS')
PY

! grep -qE 'hf_[A-Za-z0-9]{20,}|test-secret' /tmp/ewp-doctor.json \
    && echo "doctor secret scan: PASS"
```

Do not share the complete JSON if paths contain a private username. The PASS lines and the list of check codes are sufficient evidence.

## 3. Verify explicit configuration precedence

```bash
uv run --locked transcriber doctor --config /dev/null --json-output \
    > /tmp/ewp-doctor-explicit.json

uv run --locked python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path('/tmp/ewp-doctor-explicit.json').read_text(encoding='utf-8'))
assert report['ready'] is True
models = {
    item['code']: item['context']['revision']
    for item in report['checks']
    if item['code'].endswith('_model')
}
assert set(models) == {
    'asr_model', 'alignment_model', 'english_alignment_model', 'diarization_model'
}
print('doctor explicit config: PASS')
PY
```

`/dev/null` is an explicitly selected, valid empty TOML file, so the packaged defaults remain effective while the `--config` path is exercised. A deliberate missing-model failure is covered by automated tests and does not require moving or renaming the real snapshots.
