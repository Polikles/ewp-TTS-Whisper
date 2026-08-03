# EWP-transcripts WSL setup

This directory is the operational runbook for preparing and validating the EWP-transcripts reference environment. The normative environment and product constraints remain in [`docs/10-wsl2-installation.md`](../docs/10-wsl2-installation.md).

## Reference environment

- Windows 11;
- WSL2;
- Ubuntu 24.04 LTS;
- NVIDIA RTX 3090 with the current Windows driver;
- Python 3.12 managed through `uv`;
- FFmpeg and ffprobe;
- CUDA-enabled PyTorch, WhisperX, alignment, and pyannote versions selected by the Phase 0 compatibility spike.

## Recommended order

1. Run [`VERIFY_ENVIRONMENT.md`](VERIFY_ENVIRONMENT.md) against an existing WSL installation.
2. If WSL or Ubuntu is missing, follow [`INSTALL_WSL.md`](INSTALL_WSL.md).
3. Install only the stable base tools from [`INSTALL_TOOLS.md`](INSTALL_TOOLS.md).
4. Verify GPU passthrough with [`CUDA_SETUP.md`](CUDA_SETUP.md).
5. Run the dependency compatibility spike before pinning ML packages.
6. Prepare gated models with [`MODEL_SETUP.md`](MODEL_SETUP.md).
7. Verify offline behavior with [`OFFLINE_MODE.md`](OFFLINE_MODE.md).
8. Consult [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) when a check fails.

The target workstation's current verified state is recorded in [`VERIFIED_BASELINE.md`](VERIFIED_BASELINE.md). The next execution procedure is [`PHASE0_SPIKE.md`](PHASE0_SPIKE.md).

Prepare the spike recordings according to [`TEST_MEDIA_PREPARATION.md`](TEST_MEDIA_PREPARATION.md).

The prepared files and probe results are recorded in [`PHASE0_MEDIA_INVENTORY.md`](PHASE0_MEDIA_INVENTORY.md).

The first dependency hypothesis is documented in [`DEPENDENCY_CANDIDATE_MATRIX.md`](DEPENDENCY_CANDIDATE_MATRIX.md).

Prepare and validate the isolated environment with [`PREPARE_PHASE0_WSL.md`](PREPARE_PHASE0_WSL.md). Install and verify the current production scaffold with [`INSTALL_APPLICATION.md`](INSTALL_APPLICATION.md).

Accepted evidence is accumulated in [`PHASE0_RESULTS.md`](PHASE0_RESULTS.md). After the environment passes, acquire models with [`PREPARE_PHASE0_MODELS.md`](PREPARE_PHASE0_MODELS.md), run the P0-01 ASR/alignment gate with [`RUN_PHASE0_ASR_ALIGNMENT.md`](RUN_PHASE0_ASR_ALIGNMENT.md), run the P0-03 Community-1 component gate with [`RUN_PHASE0_DIARIZATION.md`](RUN_PHASE0_DIARIZATION.md), then combine all stages with [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md).

The accepted repository-scaffold and quality-gate evidence is recorded in [`PHASE1_RESULTS.md`](PHASE1_RESULTS.md).

Measure the initial mono, dual-mono, split-speaker, and mixed-stereo calibration fixtures with [`MEASURE_PHASE2_CHANNELS.md`](MEASURE_PHASE2_CHANNELS.md).

Validate the integrated production inspection command and accepted channel classifications
with [`RUN_PHASE2_INSPECT.md`](RUN_PHASE2_INSPECT.md).

Validate all four warning-only audio diagnostics with generated mechanics fixtures using
[`RUN_PHASE2_QUALITY_DIAGNOSTICS.md`](RUN_PHASE2_QUALITY_DIAGNOSTICS.md).

Validate read-only Phase 3 process/skip/version planning with controlled external result
states using [`RUN_PHASE3_DRY_RUN.md`](RUN_PHASE3_DRY_RUN.md).

Validate Phase 3 cross-process locking, atomic state transitions, and marker-guarded
workdir cleanup using [`RUN_PHASE3_STORAGE_STATE.md`](RUN_PHASE3_STORAGE_STATE.md).

After the first integrated job, verify second-run stability with [`RUN_PHASE0_REPEAT.md`](RUN_PHASE0_REPEAT.md).

Then prove offline operation with the environment-level block in [`RUN_PHASE0_NETWORK_BLOCK.md`](RUN_PHASE0_NETWORK_BLOCK.md).

After technical reproducibility passes, prepare the accurate-preset benchmark with [`PREPARE_PHASE0_MODEL_COMPARISON.md`](PREPARE_PHASE0_MODEL_COMPARISON.md).

Run the prepared benchmark with [`RUN_PHASE0_MODEL_COMPARISON.md`](RUN_PHASE0_MODEL_COMPARISON.md).

After ADR-0007 selects the default model, promote the validated dependency lock with [`PROMOTE_PHASE0_DEPENDENCIES.md`](PROMOTE_PHASE0_DEPENDENCIES.md).

## Safety rules

- Do not install a Linux NVIDIA display driver inside WSL.
- Do not guess or independently pin PyTorch, CUDA runtime, WhisperX, or pyannote versions before the compatibility spike.
- Do not store tokens in this repository, TOML files, shell history, logs, or diagnostic output.
- Do not commit model files, caches, private recordings, or generated transcripts.
- Keep the repository, virtual environment, model cache, and work directories in the WSL Linux filesystem rather than under `/mnt/c` or `/mnt/d`.

## Official sources

- [Microsoft WSL installation](https://learn.microsoft.com/windows/wsl/install)
- [Microsoft WSL filesystem guidance](https://learn.microsoft.com/windows/wsl/filesystems)
- [NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
- [uv installation](https://docs.astral.sh/uv/getting-started/installation/)
- [PyTorch local installation selector](https://pytorch.org/get-started/locally/)
- [Hugging Face Hub downloads](https://huggingface.co/docs/huggingface_hub/en/guides/download)
