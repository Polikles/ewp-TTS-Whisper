# Verify an existing environment

Run this before installing or changing anything. Commands are intentionally read-only.

Do not include usernames, tokens, complete environment dumps, SSH configuration, or private paths when sharing results.

## 1. Windows PowerShell

```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
wsl --version
wsl --status
wsl --list --verbose
nvidia-smi
```

Share the Windows version/build, WSL version, distribution name and WSL generation, GPU name, and driver version.

## 2. Ubuntu terminal

```bash
cat /etc/os-release
uname -r
uname -m
nvidia-smi
python3 --version
command -v uv && uv --version
git --version
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
df -h "$HOME"
```

If `nvidia-smi` is missing from `PATH`, also run:

```bash
/usr/lib/wsl/lib/nvidia-smi
```

## 3. Optional existing Python environment

Only if PyTorch is already installed in the environment you intend to inspect:

```bash
python3 -c "import torch; print('torch', torch.__version__); print('torch CUDA', torch.version.cuda); print('available', torch.cuda.is_available()); print('device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Do not install PyTorch merely to run this optional check.

## 4. Result template

```text
Windows version/build:
WSL version:
Distribution and WSL generation:
Ubuntu version:
Kernel:
Architecture:
GPU:
Windows driver:
nvidia-smi in WSL: OK / explicit path / failed
Python:
uv:
Git:
FFmpeg:
ffprobe:
Free Linux-home space:
Existing torch/CUDA, if any:
```

The first user input needed for Phase 0 is this completed, sanitized template.

The target workstation results from 2026-07-31 are recorded in [`VERIFIED_BASELINE.md`](VERIFIED_BASELINE.md).
