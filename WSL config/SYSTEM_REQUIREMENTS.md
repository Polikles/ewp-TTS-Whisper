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
| Package manager | `uv`; dependencies are reproduced from the committed lockfile |
| Media tools | FFmpeg and ffprobe from Ubuntu packages |
| Storage | Linux-filesystem space for source checkout, environments, models, and work files |
| Network | Required during initial package and model setup; not required for normal offline transcription |

## Capacity guidance

Reserve enough Linux-filesystem space for the Git checkout, Python environment, model
snapshots, working audio, retained failure artifacts, and archive outputs. The accepted
151-minute test peaked near 4.14 GiB process RAM and 14.6 GiB sampled total GPU use on the
24 GiB reference GPU, but these observations are not minimum hardware guarantees.

Do not publish an unsupported numeric minimum before these measurements exist.

## Expected paths

```text
/home/<user>/transkrypcje/ewp-transcripts
/home/<user>/.cache/ewp-transcripts
/home/<user>/.cache/huggingface
```

Source recordings may be read from Windows drives, but temporary audio, environments, caches, and active development files should remain in the Linux filesystem for performance.
