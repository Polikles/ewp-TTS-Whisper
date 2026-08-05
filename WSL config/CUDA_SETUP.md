# CUDA and GPU passthrough

## Critical rule

Install the NVIDIA display driver on Windows. Do not install a Linux NVIDIA display
driver inside WSL; the Windows driver exposes the GPU to WSL2.

## 1. Verify Windows

Run in PowerShell:

```powershell
nvidia-smi
wsl --update
wsl --shutdown
```

Reopen Ubuntu after WSL shuts down.

## 2. Verify WSL passthrough

```bash
nvidia-smi
```

If it is not on `PATH`, try `/usr/lib/wsl/lib/nvidia-smi`. The CUDA version displayed by
`nvidia-smi` describes driver compatibility, not the installed PyTorch runtime.

## 3. Verify the locked PyTorch runtime

After `uv sync --locked`:

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
uv run --locked python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no CUDA device')"
```

Required: CUDA is available and the expected NVIDIA GPU is named. Do not install a
global CUDA toolkit or replace the locked PyTorch packages independently.
