# Phase 0 dependency and GPU spike

## Goal

Prove one compatible, reproducible dependency set for Python 3.12, CUDA-enabled PyTorch, WhisperX, alignment, pyannote, and FFmpeg on the verified RTX 3090 workstation.

This spike is not production application code. Its successful dependency resolution becomes the initial project lockfile and dependency baseline.

## Preconditions

- [`VERIFIED_BASELINE.md`](VERIFIED_BASELINE.md) passes;
- the repository is checked out in the WSL Linux filesystem;
- the recordings specified in [`TEST_MEDIA_PREPARATION.md`](TEST_MEDIA_PREPARATION.md) are available;
- gated-model terms and a read-only Hugging Face token are available when the diarization stage begins.

## Work stages

### 1. Isolated workspace

Follow [`PREPARE_PHASE0_WSL.md`](PREPARE_PHASE0_WSL.md). Use Python 3.12 through `uv`; do not install ML packages globally or into the system Python.

### 2. Resolve dependencies

Begin with Candidate A from [`DEPENDENCY_CANDIDATE_MATRIX.md`](DEPENDENCY_CANDIDATE_MATRIX.md). Verify the resulting versions of:

- Python;
- uv;
- PyTorch and its CUDA runtime;
- torchaudio;
- WhisperX;
- faster-whisper/CTranslate2;
- pyannote.audio;
- huggingface-hub and transformers;
- FFmpeg and ffprobe.

Do not accept prereleases or unpinned main-branch dependencies.

### 3. CUDA smoke test

Required evidence:

- `torch.cuda.is_available()` is true;
- device is the RTX 3090;
- a small tensor operation completes on CUDA;
- versions and CUDA runtime are recorded without dumping the full environment.

Accepted results are recorded in [`PHASE0_RESULTS.md`](PHASE0_RESULTS.md). After the environment gate passes, follow [`PREPARE_PHASE0_MODELS.md`](PREPARE_PHASE0_MODELS.md).

### 4. ASR and alignment

Run a short Polish recording through transcription and word alignment. Record:

- selected ASR model and revision;
- selected Polish alignment model and revision;
- compute type and batch size;
- stage duration and peak VRAM where available;
- whether numbers, punctuation, or symbols lack timestamps;
- sanitized errors and warnings, without publishing transcript text by default.

Use the restartable procedure in [`RUN_PHASE0_ASR_ALIGNMENT.md`](RUN_PHASE0_ASR_ALIGNMENT.md).

### 5. Diarization

After explicit gated-model setup, run a short multi-speaker recording. Confirm model loading, speaker intervals, exclusive diarization availability when supported, and no token exposure.

Use [`RUN_PHASE0_DIARIZATION.md`](RUN_PHASE0_DIARIZATION.md).

### 6. Model unloading

Run stages sequentially and observe whether model references and GPU allocations can be released sufficiently for the next stage and a second job.

First run the complete single-job sequence in [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md). A subsequent gate repeats the job to test second-run stability.

### 7. Offline replay

Repeat the smoke case with local models, no token, offline environment variables, and outbound access disabled. Missing local resources must fail instead of downloading.

### 8. Freeze and document

Only after all stages pass:

- commit the exact `uv.lock`;
- update `docs/14-dependency-baseline.md`;
- record model IDs and revisions;
- record the validated batch size and peak VRAM;
- document any required compatibility constraints;
- retain a reusable GPU smoke-test case reference.

## Exit criteria

- ASR, Polish alignment, and diarization succeed on the RTX 3090;
- a second run succeeds offline;
- no production design depends on an unverified backend assumption;
- the compatible dependency set is locked and reproducible;
- secrets, private audio, model caches, and transcript output remain uncommitted.

## User input checkpoints

Input is needed when:

1. confirming that the prepared media passes the documented ffprobe checks;
2. confirming acceptance of gated model terms and token availability;
3. running GPU commands inside the local WSL environment;
4. approving the final dependency/model baseline after results are measured.
