# Validate installation in a fresh Ubuntu 24.04 WSL distribution

This is the final clean-environment release gate. It validates a new OS distribution,
online locked dependency installation, package build, CLI registration, CUDA visibility,
expected missing-model guidance, and model-free media operations. It does not repeat the
already accepted isolated-wheel offline transcription from ADR-0010.

Use a dedicated disposable WSL distribution. Do not remove or modify the existing
working distribution.

## 0. Create and identify the clean distribution

In PowerShell, follow `INSTALL_WSL.md` to install a separate Ubuntu 24.04 WSL2
distribution. Use the exact identifiers reported by your installed `wsl` version rather
than guessing a distribution name. Then record:

```powershell
wsl --version
wsl --list --verbose
```

Stop here unless the new dedicated distribution reports WSL version 2. All subsequent
commands run inside that new distribution as its normal non-root user.

## 1. Verify the untouched OS and install base tools

```bash
cat /etc/os-release
uname -r
test ! -e "$HOME/transkrypcje/ewp-transcripts" \
    && echo "project checkout initially absent: PASS"

sudo apt update
sudo apt upgrade
sudo apt install build-essential ca-certificates curl ffmpeg git

git --version
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
```

Expected: Ubuntu 24.04, a Microsoft WSL2 kernel, working FFmpeg/ffprobe, and the NVIDIA
GPU passed through from Windows. Do not install a Linux NVIDIA display driver.

## 2. Install uv and clone the release candidate

Download the official uv installer, optionally inspect it if your environment's security
policy requires source review, and run the exact file you downloaded. Ordinary users are
not expected to perform an undefined security audit of the script:

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/ewp-uv-install.sh
less /tmp/ewp-uv-install.sh
sh /tmp/ewp-uv-install.sh
```

Open a new shell (or apply the PATH instruction printed by the installer), then run:

```bash
uv --version
mkdir -p "$HOME/transkrypcje"
cd "$HOME/transkrypcje"
git clone https://github.com/Polikles/ewp-transcripts.git ewp-transcripts
cd ewp-transcripts
git log -1 --oneline
git status --short
```

Expected commit: `4ce45d6` or later and an empty Git status.

## 3. Install exactly from the committed lock and build artifacts

Allow for approximately 4–4.5 GB of network transfer for the locked Python/CUDA
environment. The pinned model preparation performed later adds approximately 8.5 GB,
for roughly 13 GB of total downloads. Reserve at least 20 GB of free Linux-filesystem
space, preferably on an SSD, for the checkout, environment, model caches, build
artifacts, and temporary files. Storage is not expected to differ materially by preset;
RAM and VRAM requirements will be qualified later per preset.

```bash
uv sync --locked
uv pip check
make check
uv build

uv run --locked transcriber --version
uv run --locked transcriber --help
sha256sum uv.lock dist/ewp_transcripts-*.whl dist/ewp_transcripts-*.tar.gz
```

Expected: 604 or more tests, compatible installed packages, version `0.5.0`, all current
top-level commands in help, and both wheel and source distribution artifacts.

## 4. Validate clean-machine diagnostics

The clean distribution intentionally has no model snapshots and no token. Capture the
expected readiness failure without treating it as an installation failure:

```bash
export EWP_FRESH_ROOT="$(mktemp -d "$HOME/ewp-fresh-install-XXXXXXXX")"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"

set +e
uv run --locked transcriber doctor --json-output \
    > "$EWP_FRESH_ROOT/doctor.json"
export EWP_FRESH_DOCTOR_EXIT=$?
set -e
test "$EWP_FRESH_DOCTOR_EXIT" -eq 3 && echo "expected model-readiness exit: PASS"

uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ['EWP_FRESH_ROOT'], 'doctor.json').read_text())
checks = {check['code']: check for check in report['checks']}
for code in ('python', 'wsl2', 'distribution', 'ffmpeg', 'ffprobe', 'gpu', 'cuda', 'hf_token'):
    assert checks[code]['status'] == 'pass', (code, checks[code])
for code in ('asr_model', 'alignment_model', 'diarization_model'):
    assert checks[code]['status'] == 'fail', (code, checks[code])
assert checks['hf_token']['context'] == {'present': False}
serialized = json.dumps(report)
assert 'WSL config/MODEL_SETUP.md' in serialized
print('fresh WSL diagnostics and missing-model guidance: PASS')
PY
```

## 5. Validate model-free application operations

```bash
mkdir -p "$EWP_FRESH_ROOT/input" "$EWP_FRESH_ROOT/output" "$EWP_FRESH_ROOT/work"
ffmpeg -v error -y -f lavfi -i "sine=frequency=440:duration=3" \
    -ac 1 -ar 48000 -c:a pcm_s16le "$EWP_FRESH_ROOT/input/installation-smoke.wav"

cat > "$EWP_FRESH_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false
[runtime]
work_root = "$EWP_FRESH_ROOT/work"
EOF

uv run --locked transcriber inspect "$EWP_FRESH_ROOT/input/installation-smoke.wav" \
    --config "$EWP_FRESH_ROOT/transcriber.toml" --json-output \
    > "$EWP_FRESH_ROOT/inspect.json"
uv run --locked transcriber dry-run "$EWP_FRESH_ROOT/input/installation-smoke.wav" \
    --config "$EWP_FRESH_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_FRESH_ROOT/output" \
    > "$EWP_FRESH_ROOT/dry-run.txt"
uv run --locked transcriber clean all-workdirs \
    --config "$EWP_FRESH_ROOT/transcriber.toml" --dry-run \
    > "$EWP_FRESH_ROOT/clean.txt"

test ! -e "$EWP_FRESH_ROOT/output/installation-smoke_results.json" \
    && echo "model-free commands created no result: PASS"
sha256sum "$EWP_FRESH_ROOT/input/installation-smoke.wav" \
    "$EWP_FRESH_ROOT/doctor.json" "$EWP_FRESH_ROOT/inspect.json" \
    "$EWP_FRESH_ROOT/dry-run.txt" "$EWP_FRESH_ROOT/clean.txt"
git status --short
```

Inspect and dry-run must identify one mono source and plan canonical JSON plus the TXT
preview and segments JSON without loading or downloading models. Cleanup preview must
select nothing. Git status
must be empty. `LICENSE` must be present in the clean checkout and built distributions.

## 6. Preserve evidence and dispose only by explicit choice

Keep the distribution until the hashes and outputs above are recorded in the release
ADR. Removing the dedicated distribution later is destructive and is outside this
runbook; use an explicit PowerShell action only after verifying its exact name and after
deciding that the evidence is no longer needed.
