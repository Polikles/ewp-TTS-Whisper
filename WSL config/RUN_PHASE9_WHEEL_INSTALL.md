# Run Phase 9 isolated wheel-install validation

This gate builds the distributable wheel and source archive, creates a fresh external
Python 3.12 virtual environment, installs the exact locked runtime dependency set
offline, and installs the wheel without resolving dependencies from its looser package
metadata. Commands then run outside the source checkout to prove the installed wheel is
being imported.

This is an isolated-package installation test on the accepted Ubuntu 24.04 WSL2 system.
It does not replace the later fresh-OS/WSL clean-room release test.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_WHEEL_INPUT="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P9_WHEEL_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-wheel-XXXXXXXX)"
export EWP_P9_WHEEL_ARTIFACTS="$EWP_P9_WHEEL_ROOT/artifacts"
export EWP_P9_WHEEL_VENV="$EWP_P9_WHEEL_ROOT/venv"
export EWP_P9_WHEEL_OUTPUT="$EWP_P9_WHEEL_ROOT/output"
export EWP_P9_WHEEL_EVIDENCE="$EWP_P9_WHEEL_ROOT/evidence"
export EWP_P9_WHEEL_CONFIG="$EWP_P9_WHEEL_ROOT/transcriber.toml"
export EWP_P9_WHEEL_REQUIREMENTS="$EWP_P9_WHEEL_EVIDENCE/runtime-requirements.txt"
mkdir -p \
    "$EWP_P9_WHEEL_ARTIFACTS" \
    "$EWP_P9_WHEEL_OUTPUT" \
    "$EWP_P9_WHEEL_EVIDENCE"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_WHEEL_ROOT/work" \
    > "$EWP_P9_WHEEL_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P9_WHEEL_ROOT"
```

The log must contain commit `76cc592` or later. At that commit, 231 tests should pass.

## 1. Build and hash release artifacts

```bash
uv build --out-dir "$EWP_P9_WHEEL_ARTIFACTS"
find "$EWP_P9_WHEEL_ARTIFACTS" -maxdepth 1 -type f -printf '%f\n' | sort
sha256sum "$EWP_P9_WHEEL_ARTIFACTS"/*

export EWP_P9_WHEEL_PATH="$(find "$EWP_P9_WHEEL_ARTIFACTS" -maxdepth 1 \
    -name 'ewp_transcripts-0.1.0-py3-none-any.whl' -print -quit)"
export EWP_P9_SDIST_PATH="$(find "$EWP_P9_WHEEL_ARTIFACTS" -maxdepth 1 \
    -name 'ewp_transcripts-0.1.0.tar.gz' -print -quit)"
test -s "$EWP_P9_WHEEL_PATH" && echo "wheel: present"
test -s "$EWP_P9_SDIST_PATH" && echo "sdist: present"
```

Exactly one version-0.1.0 wheel and one source archive must exist. Record both hashes.

## 2. Export the immutable runtime lock projection

```bash
uv export --locked --no-dev --no-emit-project --emit-index-url --no-header \
    --output-file "$EWP_P9_WHEEL_REQUIREMENTS"
sha256sum uv.lock "$EWP_P9_WHEEL_REQUIREMENTS"

grep -E '^(torch|torchaudio|torchvision|torchcodec|triton|whisperx|pyannote-audio)==' \
    "$EWP_P9_WHEEL_REQUIREMENTS"
```

The `requirements.txt` per-package-index warning is expected because that format cannot
encode uv's per-package source mapping. Installation remains offline and hash-checked,
so it can only consume the already cached artifacts selected by `uv.lock`. Required
versions include:

```text
torch==2.8.0+cu128
torchaudio==2.8.0+cu128
torchvision==0.23.0+cu128
torchcodec==0.7.0
triton==3.4.0
whisperx==3.8.6
pyannote-audio==4.0.7
```

The accepted `uv.lock` hash remains:

```text
c32602b6b9c3cf8edefdb861609029b8a05cd4ae1dd4cb51b4c69d31352a1359
```

Stop if it differs.

## 3. Create a fresh venv and synchronize locked dependencies offline

```bash
uv venv --python /usr/bin/python3 "$EWP_P9_WHEEL_VENV"

uv pip sync "$EWP_P9_WHEEL_REQUIREMENTS" \
    --python "$EWP_P9_WHEEL_VENV/bin/python" \
    --offline --require-hashes --strict

uv pip install "$EWP_P9_WHEEL_PATH" \
    --python "$EWP_P9_WHEEL_VENV/bin/python" \
    --offline --no-deps

uv pip check --python "$EWP_P9_WHEEL_VENV/bin/python"
```

No package may be resolved or downloaded from the network. The application wheel is
installed only after exact dependencies and cannot mutate them.

## 4. Prove wheel provenance outside the checkout

```bash
cd "$EWP_P9_WHEEL_ROOT"

"$EWP_P9_WHEEL_VENV/bin/python" - <<'PY'
from pathlib import Path

import ewp_transcripts

module_path = Path(ewp_transcripts.__file__).resolve()
print(f"module_path={module_path}")
assert "site-packages" in module_path.parts
assert "ewp-transcripts/src" not in str(module_path)
print("installed wheel provenance: PASS")
PY

"$EWP_P9_WHEEL_VENV/bin/transcriber" --version
"$EWP_P9_WHEEL_VENV/bin/transcriber" --help
"$EWP_P9_WHEEL_VENV/bin/transcriber" doctor
```

Version must be `0.1.0`, help must list all six MVP commands, and `doctor` must pass on
the reference WSL2/GPU system without revealing a token.

## 5. Verify exact runtime package versions and CUDA

```bash
"$EWP_P9_WHEEL_VENV/bin/python" - <<'PY'
from importlib.metadata import version

import torch

expected = {
    "ewp-transcripts": "0.1.0",
    "whisperx": "3.8.6",
    "torch": "2.8.0+cu128",
    "torchaudio": "2.8.0+cu128",
    "torchvision": "0.23.0+cu128",
    "torchcodec": "0.7.0",
    "pyannote-audio": "4.0.7",
    "faster-whisper": "1.2.1",
    "ctranslate2": "4.8.1",
    "transformers": "4.57.6",
    "triton": "3.4.0",
}
for package, wanted in expected.items():
    actual = version(package)
    assert actual == wanted, (package, actual, wanted)
    print(f"PASS {package}={actual}")

assert torch.cuda.is_available()
assert torch.version.cuda == "12.8"
print(f"PASS CUDA device={torch.cuda.get_device_name(0)} runtime={torch.version.cuda}")
PY
```

## 6. Run model-free commands from the installed wheel

```bash
"$EWP_P9_WHEEL_VENV/bin/transcriber" inspect "$EWP_P9_WHEEL_INPUT" \
    --json-output > "$EWP_P9_WHEEL_EVIDENCE/inspect.json"

"$EWP_P9_WHEEL_VENV/bin/transcriber" dry-run "$EWP_P9_WHEEL_INPUT" \
    --speaker-count 1 --output-dir "$EWP_P9_WHEEL_OUTPUT" \
    > "$EWP_P9_WHEEL_EVIDENCE/dry-run.txt"

"$EWP_P9_WHEEL_VENV/bin/python" - \
    "$EWP_P9_WHEEL_EVIDENCE/inspect.json" \
    "$EWP_P9_WHEEL_EVIDENCE/dry-run.txt" <<'PY'
import json
import sys
from pathlib import Path

inspection = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert len(inspection["episodes"]) == 1
source = inspection["episodes"][0]["sources"][0]
assert source["channel_classification"]["processing_mode"] == "mono"
plan = Path(sys.argv[2]).read_text(encoding="utf-8")
assert "PROCESS p0-01-single-short" in plan
assert "result version: 1" in plan
assert not list(Path(sys.argv[2]).parent.parent.joinpath("output").glob("*"))
print("installed model-free commands: PASS")
PY
```

## 7. Run one real transcription from the installed wheel offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    "$EWP_P9_WHEEL_VENV/bin/transcriber" transcribe "$EWP_P9_WHEEL_INPUT" \
    --config "$EWP_P9_WHEEL_CONFIG" \
    --speaker-count 1 \
    --output-dir "$EWP_P9_WHEEL_OUTPUT" \
    --non-interactive
```

The command must report `PROCESS`, one canonical `RESULT`, and three `WROTE` exports.
A download, token request, traceback, CUDA OOM, or source-checkout import fails the gate.

## 8. Validate outputs, replay, and cleanup

Use the repository environment only as an independent JSON Schema validator; the
application invocation remains the installed wheel:

```bash
cd "$EWP_REPO"
uv run --locked python - "$EWP_P9_WHEEL_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

output = Path(sys.argv[1])
result_path = output / "p0-01-single-short_results.json"
result = json.loads(result_path.read_text(encoding="utf-8"))
schema = json.loads(Path("schemas/results.schema.json").read_text(encoding="utf-8"))
Draft202012Validator(schema).validate(result)
assert result["application_version"] == "0.1.0"
assert result["status"] == "completed"
assert len(result["speakers"]) == 1
assert result["transcript"]["segments"]
for suffix in ("_transcript.txt", "_subtitles.srt", "_subtitles.vtt"):
    path = output / f"p0-01-single-short{suffix}"
    assert path.stat().st_size > 0, path
print("installed-wheel canonical result and exports: PASS")
PY

cd "$EWP_P9_WHEEL_ROOT"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    "$EWP_P9_WHEEL_VENV/bin/transcriber" transcribe "$EWP_P9_WHEEL_INPUT" \
    --config "$EWP_P9_WHEEL_CONFIG" \
    --speaker-count 1 \
    --output-dir "$EWP_P9_WHEEL_OUTPUT" \
    --non-interactive

test -z "$(find "$EWP_P9_WHEEL_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "installed-wheel workdir cleanup: PASS"
sha256sum "$EWP_P9_WHEEL_OUTPUT"/*
sha256sum "$EWP_P9_WHEEL_EVIDENCE/inspect.json" \
    "$EWP_P9_WHEEL_EVIDENCE/runtime-requirements.txt"

cd "$EWP_REPO"
git status --short
```

Replay must skip the canonical result and all exports without model-loading logs.
Repository status must be empty.

## 9. Evidence to return

Return:

- Step 0 test count, token check, GPU line, and sandbox path;
- wheel, sdist, lockfile, and runtime-requirements hashes;
- offline sync/install/check summaries;
- module path and provenance PASS;
- version/help/doctor summaries plus package/CUDA PASS lines;
- model-free PASS and first-run/duplicate summaries;
- canonical/export and cleanup PASS lines;
- result/export, inspection, and runtime-requirements hashes;
- empty repository status.

Do not send the requirements file, wheel contents, audio, transcript, canonical JSON,
tokens, model files, or caches.
