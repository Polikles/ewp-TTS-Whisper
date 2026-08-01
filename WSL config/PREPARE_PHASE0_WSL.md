# Prepare local WSL for the Phase 0 spike

This runbook creates a reproducible, isolated dependency environment on the verified WSL workstation. It does not install packages globally and does not create production EWP-transcripts modules.

Run one numbered section at a time. Stop after the first unexpected result and record the command and sanitized error before changing anything.

## Relationship to the final application setup

This is an experimental setup procedure. The future application installation guide will use the dependency set approved here and run `uv sync --locked` against the repository's production `uv.lock`.

Do not present this spike procedure as the eventual end-user installation process. Shared base-system steps remain in:

- [`INSTALL_WSL.md`](INSTALL_WSL.md);
- [`INSTALL_TOOLS.md`](INSTALL_TOOLS.md);
- [`CUDA_SETUP.md`](CUDA_SETUP.md);
- [`MODEL_SETUP.md`](MODEL_SETUP.md);
- [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

## Paths used below

```text
Application repository:
/home/linuch/transkrypcje/ewp-transcripts

External test data:
/home/linuch/transkrypcje/ewp-transcripts-testdata/phase0

Disposable spike project:
/home/linuch/transkrypcje/ewp-transcripts-spike

Spike evidence:
/home/linuch/transkrypcje/ewp-transcripts-spike/evidence
```

The spike project and evidence stay outside the application Git repository.

## 0. Open a clean WSL shell

Start Ubuntu 24.04, then ensure the shell begins in the Linux filesystem:

```bash
cd "$HOME"
pwd
```

Expected:

```text
/home/linuch
```

Do not run the spike from `/mnt/c`, `/mnt/d`, or another Windows-mounted directory.

## 1. Confirm the known baseline

```bash
cat /etc/os-release | grep -E '^(PRETTY_NAME|VERSION_ID)='
uname -m
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
python3 --version
uv --version
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
```

Expected essentials:

- Ubuntu 24.04;
- `x86_64`;
- RTX 3090;
- Python 3.12;
- uv 0.12.0 for the first run;
- FFmpeg and ffprobe 6.1.1.

Small patch-version differences after normal system updates must be recorded, not silently ignored.

## 2. Confirm the media files

```bash
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
test -d "$EWP_PHASE0_DATA/audio" && echo "audio directory: OK"
find "$EWP_PHASE0_DATA/audio" -maxdepth 1 -type f -printf '%f\n' | sort
```

Expected filenames:

```text
p0-01-single-short.wav
p0-02-single-representative.wav
p0-03-two-speakers-mixed-overlap.wav
p0-04-two-speakers-dual-mono.mp3
```

Confirm the P0-01 checked reference exists without printing its content:

```bash
find "$EWP_PHASE0_DATA/references" -maxdepth 1 -type f -printf '%f\n' | sort
```

If the reference directory uses another safe location, record it before continuing.

## 3. Create the isolated spike project

The directory must not already contain an unrelated project:

```bash
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
test ! -e "$EWP_PHASE0_SPIKE" && mkdir -p "$EWP_PHASE0_SPIKE/evidence"
cd "$EWP_PHASE0_SPIKE"
pwd
```

If the directory already exists, stop and inspect it. Do not delete or overwrite it blindly.

Create `pyproject.toml` with this exact initial content:

```toml
[project]
name = "ewp-transcripts-phase0-spike"
version = "0.0.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "pyannote-audio==4.0.7",
    "torch==2.8.0",
    "torchaudio==2.8.0",
    "torchcodec==0.7.0",
    "torchvision==0.23.0",
    "whisperx==3.8.6",
]

[tool.uv]
environments = ["sys_platform == 'linux' and platform_machine == 'x86_64'"]

[tool.uv.sources]
torch = { index = "pytorch-cu128" }
torchaudio = { index = "pytorch-cu128" }
torchvision = { index = "pytorch-cu128" }
triton = { index = "pytorch-cu128" }

[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
```

Why these index rules matter: PyTorch packages must come from the official CUDA 12.8 index, while normal Python dependencies continue to come from PyPI. The explicit index prevents unrelated packages from being taken from the PyTorch repository.

## 4. Resolve and lock before installation

```bash
cd "$EWP_PHASE0_SPIKE"
uv lock
```

Expected:

- resolution succeeds without prereleases;
- `uv.lock` is created when `uv lock` runs;
- Python remains in the 3.12 family;
- no Git/main-branch dependencies appear.

Record the resolver output in the session notes. Do not add overrides merely to force a failed solution.

## 5. Inspect the lock before installation

```bash
uv tree --locked
```

Confirm at minimum:

```text
whisperx 3.8.6
torch 2.8.0
torchaudio 2.8.0
torchvision 0.23.0
torchcodec 0.7.0
pyannote-audio 4.0.7
```

Also record the resolved versions of:

```text
ctranslate2
faster-whisper
huggingface-hub
transformers
triton
```

Stop if the lock includes WhisperX `3.8.7rc1` or any other prerelease.

## 6. Install exactly from the lock

This step downloads a large CUDA-enabled environment:

```bash
uv sync --locked
```

Do not activate `.venv`; use `uv run --locked` for every test.

After installation:

```bash
uv pip check
uv run --locked python --version
uv run --locked python -c "import whisperx; print('whisperx import: OK')"
```

Expected:

- dependency check succeeds;
- Python reports 3.12.x;
- WhisperX imports without downloading models.

## 7. Capture a concise version report

Run from the spike directory:

```bash
uv run --locked python - <<'PY'
from importlib.metadata import version

packages = (
    "whisperx",
    "torch",
    "torchaudio",
    "torchvision",
    "torchcodec",
    "pyannote.audio",
    "faster-whisper",
    "ctranslate2",
    "huggingface-hub",
    "transformers",
    "triton",
)
for package in packages:
    print(f"{package}={version(package)}")
PY
```

Save or copy this output into the Phase 0 evidence notes. Do not use `pip freeze` as the primary report; `uv.lock` is the complete reproducibility record.

## 8. Verify CUDA through PyTorch

```bash
uv run --locked python - <<'PY'
import torch

print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available")

device = torch.device("cuda:0")
print(f"device={torch.cuda.get_device_name(device)}")
a = torch.arange(1_000_000, device=device, dtype=torch.float32)
b = (a * 2).sum()
torch.cuda.synchronize(device)
print(f"tensor_result={b.item():.1f}")
print(f"allocated_bytes={torch.cuda.memory_allocated(device)}")
print(f"peak_allocated_bytes={torch.cuda.max_memory_allocated(device)}")
PY
```

Required:

- `cuda_available=True`;
- device identifies the RTX 3090;
- tensor operation completes without an exception.

## 9. Verify TorchCodec and FFmpeg integration

```bash
uv run --locked python - <<'PY'
import os
from pathlib import Path
from torchcodec.decoders import AudioDecoder

path = Path(os.environ["EWP_PHASE0_DATA"]) / "audio" / "p0-01-single-short.wav"
samples = AudioDecoder(str(path)).get_all_samples()
print(f"path={path.name}")
print(f"shape={tuple(samples.data.shape)}")
print(f"sample_rate={samples.sample_rate}")
print(f"duration_seconds={samples.duration_seconds:.3f}")
PY
```

Expected:

- one decoded channel;
- 48,000 Hz;
- approximately 95.376 seconds;
- no shared-library or TorchCodec error.

## 10. Set privacy controls before model work

```bash
export HF_HOME="$HOME/.cache/huggingface"
export PYANNOTE_METRICS_ENABLED=0
mkdir -p "$HF_HOME"
chmod 700 "$HF_HOME"
```

Do not set `HF_TOKEN` yet. ASR/alignment model selection and explicit model downloads are the next runbook stage.

## Stop point

After sections 0–10 pass, send these sanitized results:

```text
uv lock: PASS / FAIL
uv sync --locked: PASS / FAIL
uv pip check: PASS / FAIL
resolved package version report:
CUDA report:
TorchCodec report:
```

Do not send the full lockfile, environment variables, usernames, tokens, transcripts, or model-cache paths unless specifically needed to diagnose a failure.

## Safe restart procedure

The authoritative inputs are `pyproject.toml` and `uv.lock`. To retest installation without changing resolution:

1. preserve both files and evidence;
2. move the existing `.venv` aside or remove only that exact `.venv` after confirming the path;
3. run `uv sync --locked` again;
4. repeat sections 6–9.

Never remove `$HOME`, the application repository, test data, Hugging Face cache, or the whole `transkrypcje` directory to restart a spike.

## Official references

- [uv package indexes](https://docs.astral.sh/uv/concepts/indexes/)
- [uv project locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [WhisperX 3.8.6 metadata](https://raw.githubusercontent.com/m-bain/whisperX/v3.8.6/pyproject.toml)
- [PyTorch 2.8 installation matrix](https://pytorch.org/get-started/previous-versions/)
- [TorchCodec compatibility](https://github.com/meta-pytorch/torchcodec#compatibility-with-torch-versions)
