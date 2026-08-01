# Phase 0 dependency candidate matrix

Research date: **2026-08-01**.

This is the first compatibility candidate, not an approved production baseline. Versions become authoritative only after installation, GPU, ASR, alignment, diarization, unloading, and offline tests pass on the target workstation.

## Candidate A — WhisperX upstream-native stack

| Component | Candidate | Reason |
|---|---|---|
| Python | 3.12.x | MVP requirement; supported by WhisperX and TorchCodec |
| uv | 0.12.0 | verified on target workstation |
| WhisperX | 3.8.6 | latest stable release; exclude `3.8.7rc1` prerelease |
| PyTorch | 2.8.0, CUDA 12.8 wheel | exact family required by WhisperX 3.8.6 upstream metadata |
| torchaudio | 2.8.0 | matched to PyTorch 2.8.0 |
| torchvision | 0.23.0 | matched to PyTorch 2.8.0 and WhisperX metadata |
| TorchCodec | 0.7.x, initially 0.7.0 | compatible with PyTorch 2.8 and Python 3.12; within WhisperX's `>=0.6,<0.8` constraint |
| pyannote.audio | 4.0.7 candidate | current stable release satisfying WhisperX's `>=4.0.0`; must be proven with 3.8.6 |
| diarization model | `pyannote/speaker-diarization-community-1` pinned revision | required local open-source pipeline; revision recorded after download |
| faster-whisper | resolver-selected `>=1.2.0` | WhisperX constraint; exact version captured in lockfile |
| CTranslate2 | resolver-selected `>=4.5.0` | WhisperX constraint; exact version captured in lockfile |
| huggingface-hub | resolver-selected `<1.0.0` | WhisperX 3.8.6 upper bound; exact version captured in lockfile |
| transformers | resolver-selected `>=4.48.0` | WhisperX constraint; exact version captured in lockfile and tested for alignment compatibility |
| FFmpeg/ffprobe | 6.1.1-3ubuntu5 | verified Ubuntu installation; supported by TorchCodec's FFmpeg 4–8 range |

## Why CUDA 12.8

WhisperX 3.8.6's tagged `pyproject.toml` directs Linux x86_64 PyTorch packages to the official `cu128` index. PyTorch publishes the matched set:

```text
torch==2.8.0
torchvision==0.23.0
torchaudio==2.8.0
```

The workstation driver reports CUDA UMD compatibility 13.3, which is newer than the candidate CUDA 12.8 runtime. Actual execution must still be proven; the driver display alone is not the acceptance test.

## Important constraints and risks

### TorchCodec

TorchCodec's compatibility table maps versions 0.6 and 0.7 to PyTorch 2.8 and Python 3.9–3.13. Start with 0.7.0 because it is the newest family allowed by WhisperX 3.8.6.

TorchCodec dynamically uses the installed FFmpeg shared libraries. The spike must explicitly decode P0-01 before testing pyannote.

### pyannote.audio

WhisperX requires pyannote.audio 4 or newer. Version 4 switched audio I/O from torchaudio to TorchCodec and introduced the Community-1 pipeline features needed by this project, including exclusive diarization.

Version 4.0.7 is newer than WhisperX 3.8.6, so compatibility is a test hypothesis. If it fails, do not perform ad-hoc downgrades in place. Record the failure and create a fresh candidate environment with the nearest justified 4.0.x version.

### Hugging Face and Transformers

WhisperX 3.8.6 requires `huggingface-hub<1.0.0` but provides no Transformers upper bound. The resolved versions must be recorded and tested for:

- ASR model download and local reload;
- Polish alignment model download and local reload;
- Community-1 download and local reload;
- true offline execution.

### Telemetry

pyannote.audio 4 provides optional metrics telemetry. EWP-transcripts requires no telemetry, so the spike and final application must set:

```bash
export PYANNOTE_METRICS_ENABLED=0
```

This does not replace the network-blocked offline test.

## Candidate rejection conditions

Reject Candidate A if any of the following remains unresolved:

- dependency resolution requires a prerelease or source from a branch;
- TorchCodec cannot load Ubuntu FFmpeg libraries;
- PyTorch does not see the RTX 3090;
- WhisperX ASR or Polish alignment fails;
- Community-1 or exclusive diarization fails;
- model unloading prevents a second sequential run;
- a fully cached offline run attempts network access;
- a required workaround would violate lazy loading, privacy, or reproducibility rules.

## Evidence to capture

- `uv.lock` and concise package-version list;
- PyTorch version, embedded CUDA runtime, and device name;
- TorchCodec decode result;
- ASR, alignment, and diarization smoke results;
- model IDs and immutable revisions;
- stage timings and peak VRAM;
- offline replay result;
- sanitized failure notes for rejected candidates.

## Primary sources

- [WhisperX 3.8.6 project metadata](https://raw.githubusercontent.com/m-bain/whisperX/v3.8.6/pyproject.toml)
- [WhisperX releases](https://github.com/m-bain/whisperX/releases)
- [PyTorch 2.8.0 installation matrix](https://pytorch.org/get-started/previous-versions/)
- [TorchCodec compatibility table](https://github.com/meta-pytorch/torchcodec#compatibility-with-torch-versions)
- [pyannote.audio releases](https://github.com/pyannote/pyannote-audio/releases)
- [pyannote.audio on PyPI](https://pypi.org/project/pyannote-audio/)
- [Community-1 model card](https://huggingface.co/pyannote/speaker-diarization-community-1)
