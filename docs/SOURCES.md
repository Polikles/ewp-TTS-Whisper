# Technical Sources

Verification date: 2026-07-29.

## WhisperX

- Repository: https://github.com/m-bain/whisperX
- PyPI: https://pypi.org/project/whisperx/
- Releases: https://github.com/m-bain/whisperX/releases

Verified baseline facts:

- stable release 3.8.6;
- Python requirement `>=3.10,<3.14`;
- known limitations involving overlap, diarization, and timestamps for some numbers or symbols.

## pyannote

- Toolkit: https://github.com/pyannote/pyannote-audio
- Community-1 model card: https://huggingface.co/pyannote/speaker-diarization-community-1

Verified facts:

- the model requires acceptance of access terms;
- after download, it can run locally and offline;
- regular and exclusive diarization outputs are available.

## WSL and CUDA

- NVIDIA CUDA on WSL: https://docs.nvidia.com/cuda/wsl-user-guide/index.html
- Microsoft WSL installation: https://learn.microsoft.com/windows/wsl/install
- Microsoft filesystem guidance: https://learn.microsoft.com/windows/wsl/filesystems
- Ubuntu on WSL: https://ubuntu.com/wsl

## FFmpeg

- ffprobe: https://ffmpeg.org/ffprobe-all.html
- filters: https://ffmpeg.org/ffmpeg-filters.html

## faster-whisper

- Repository: https://github.com/SYSTRAN/faster-whisper

Used to confirm availability of the `large-v3` model. The final `accurate` preset model must be selected through project benchmarks rather than upstream descriptions alone.
