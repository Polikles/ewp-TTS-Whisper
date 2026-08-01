# CUDA and GPU passthrough

## Critical rule

Install the NVIDIA GPU driver on Windows. Do not install a Linux NVIDIA display driver inside WSL. NVIDIA states that the Windows driver is exposed inside WSL and that installing a Linux driver there can overwrite the WSL integration.

Source: [NVIDIA — CUDA on WSL user guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

## 1. Verify the Windows side

In PowerShell:

```powershell
nvidia-smi
wsl --update
wsl --shutdown
```

Then reopen Ubuntu.

## 2. Verify the WSL side

Inside Ubuntu:

```bash
nvidia-smi
```

If it is not on `PATH`, check the WSL-provided binary directly:

```bash
/usr/lib/wsl/lib/nvidia-smi
```

Record the GPU name, displayed Windows driver version, reported CUDA compatibility version, and whether the explicit WSL path was required.

The CUDA value displayed by `nvidia-smi` is the maximum CUDA compatibility exposed by the driver; it does not prove that CUDA-enabled PyTorch is installed.

## 3. PyTorch verification belongs to the spike

Do not install a guessed global CUDA toolkit or PyTorch wheel. The compatibility spike will select the PyTorch build together with WhisperX and pyannote, using the official [PyTorch installation selector](https://pytorch.org/get-started/locally/).

After the spike environment exists, verify it with:

```bash
uv run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no CUDA device')"
```

Required outcome: `torch.cuda.is_available()` is `True` and the device name identifies the RTX 3090.
