# System requirements

## Required for the MVP reference environment

| Component | Requirement |
|---|---|
| Host | Windows 11 with virtualization enabled |
| WSL | Current stable WSL, distribution running as WSL2 |
| Distribution | Ubuntu 24.04 LTS |
| GPU | NVIDIA RTX 3090, 24 GB VRAM |
| Driver | Current Windows NVIDIA driver with WSL support |
| Python | 3.12 |
| Package manager | `uv`; exact version recorded during the spike |
| Media tools | FFmpeg and ffprobe from Ubuntu packages |
| Storage | Linux-filesystem space for source checkout, environments, models, and work files |
| Network | Required during initial package and model setup; not required for normal offline transcription |

## Capacity guidance

Exact minimum free-space and RAM requirements must be recorded during the compatibility and long-file tests. Until measured, reserve enough Linux-filesystem space for the Git checkout, Python environment, model snapshots, working audio, retained failure artifacts, and external test data.

Do not publish an unsupported numeric minimum before these measurements exist.

## Expected paths

```text
/home/<user>/projects/ewp-transcripts
/home/<user>/.cache/ewp-transcripts
/home/<user>/.cache/huggingface
```

Source recordings may be read from Windows drives, but temporary audio, environments, caches, and active development files should remain in the Linux filesystem for performance.
