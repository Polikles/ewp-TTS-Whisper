# Troubleshooting

## `wsl --install` prints help

WSL may already be installed. Run `wsl --list --online` and `wsl --list --verbose`, then install the required distribution explicitly. Microsoft also documents `--web-download` for Store-download problems.

## Distribution is WSL1

```powershell
wsl --set-version <distribution-name> 2
```

Do not continue with GPU setup until `wsl --list --verbose` reports version 2.

## `nvidia-smi` is unavailable inside WSL

1. Confirm it works in Windows PowerShell.
2. Run `wsl --update` and `wsl --shutdown` in PowerShell.
3. Reopen Ubuntu.
4. Try `/usr/lib/wsl/lib/nvidia-smi`.
5. Confirm the Windows driver supports WSL.

Do not fix this by installing a Linux NVIDIA display driver inside WSL.

## PyTorch reports CUDA unavailable

Check that WSL is version 2, `nvidia-smi` works inside WSL, the PyTorch build includes CUDA support, it is driver-compatible, and the command uses the intended `uv` environment.

Do not install random CUDA or PyTorch versions over the project environment. Restore it
with `uv sync --locked`.

## FFmpeg or ffprobe is missing

```bash
sudo apt update
sudo apt install ffmpeg
```

## Gated model returns 401 or 403

Confirm that the correct account accepted every required model's terms, `HF_TOKEN` is present without printing it, the token can read gated repositories, and the exact pinned model identifier is used.

## Offline run tries to connect

Confirm local model completeness and enable the library offline flags in [`OFFLINE_MODE.md`](OFFLINE_MODE.md). Treat hidden network fallback as a failed offline test.

## Work is slow under `/mnt/c` or `/mnt/d`

Move the repository, environment, caches, and workdir into `/home/<user>`. Windows-mounted paths remain acceptable for source recordings when necessary.
