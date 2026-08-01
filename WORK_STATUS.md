# EWP-transcripts work status

Last updated: **2026-07-31**.

Latest resume update: **2026-08-01**.

Use this file as the starting point for the next work session.

## Current stage

The project is in **Phase 0 preparation: WSL, dependency, and GPU compatibility spike**.

No application code or production package scaffold has been created yet. The current work is documentation and preparation for proving the ML dependency stack on the target workstation.

## Completed before this session

- Product and agent documentation reviewed.
- MVP ambiguities resolved with the project owner.
- Project name fixed as **EWP-transcripts**.
- CLI executable name fixed as **`transcriber`**.
- Video support deferred beyond the MVP.
- Lightweight warning-only audio diagnostics retained in the MVP; audio repair deferred.
- Default batch output directory fixed as `output-ewp-transcripts`.
- Full configuration precedence retained.
- Agent implementation plan selected as the authoritative detailed plan.
- Tests defined as local/VM/WSL-based; no GitHub Actions.
- Agent guidance moved into the repository.
- Documentation corrections committed and pushed to `main`.

Relevant pushed commits:

```text
9b188fd Add agent guidance
af43759 Align MVP documentation
```

## Completed today

### WSL documentation package

Created [`WSL config/`](WSL%20config/README.md), containing:

- system requirements;
- WSL2 and Ubuntu 24.04 installation;
- base tools and Python setup;
- CUDA/GPU passthrough rules;
- Hugging Face and gated-model preparation;
- offline-mode verification;
- environment verification;
- troubleshooting;
- Phase 0 spike requirements;
- test-media preparation.

The package is linked from the main README and documentation index.

### Target workstation verification

The target workstation baseline is recorded in [`WSL config/VERIFIED_BASELINE.md`](WSL%20config/VERIFIED_BASELINE.md).

Verified:

- Windows 11 build family `26200`;
- WSL `2.7.11.0`, generation 2;
- Ubuntu 24.04.4 LTS;
- x86_64;
- NVIDIA RTX 3090 with 24 GB VRAM;
- GPU passthrough and `nvidia-smi` working inside WSL;
- Windows NVIDIA driver `610.62`;
- CUDA UMD compatibility reported as `13.3`;
- Python 3.12.3;
- uv 0.12.0;
- Git 2.43.0;
- FFmpeg/ffprobe 6.1.1;
- approximately 954 GB free in the Linux filesystem;
- PyTorch not installed, providing a clean spike starting point.

Repository location on the target WSL workstation:

```text
/home/linuch/transkrypcje/ewp-transcripts
```

### Test-media specification

The required excerpts are defined in [`WSL config/TEST_MEDIA_PREPARATION.md`](WSL%20config/TEST_MEDIA_PREPARATION.md):

- `P0-01`: 60–90 seconds, one Polish speaker;
- `P0-02`: 4–6 minutes, representative single-speaker Polish material;
- `P0-03`: 5–8 minutes, two speakers mixed into mono;
- optional `P0-04`: existing dual-mono MP3 for later channel-classifier work.

Recommended external dataset path:

```text
/home/linuch/transkrypcje/ewp-transcripts-testdata/phase0/
```

## Current repository state

The WSL documentation created today is intentionally **not committed yet**. It should be reviewed against the live media preparation and dependency spike before being committed.

An unrelated untracked file named `LICENSE_SKETCH.TXT` exists in the repository. It belongs to the project owner and must not be modified, staged, or committed as part of the WSL documentation work unless explicitly requested.

At the end of today, documentation link validation and `git diff --check` passed.

## Next user actions

1. Prepare `P0-01`, `P0-02`, and `P0-03` according to the media specification.
2. Create a manually checked reference transcript for `P0-01`.
3. Run the documented ffprobe command against each prepared file.
4. Confirm whether the optional dual-mono MP3 has identical left and right channels, with the complete two-speaker mix present in both.
5. Keep the Hugging Face token secret. Only confirm later that `HF_TOKEN` is present in the WSL spike shell.

## Exact resume point

Resume with these steps:

1. Review the ffprobe output for `P0-01`, `P0-02`, and `P0-03`.
2. Correct the WSL/media documentation if live preparation exposed any issue.
3. Research and define the candidate compatibility matrix for:
   - Python 3.12;
   - CUDA-enabled PyTorch and torchaudio;
   - WhisperX;
   - faster-whisper/CTranslate2;
   - pyannote.audio and `speaker-diarization-community-1`;
   - transformers and huggingface-hub.
4. Create a small isolated Phase 0 spike environment and scripts; do not create production application modules yet.
5. Run the CUDA smoke test on the local WSL workstation.
6. Run `P0-01` through Polish ASR and alignment.
7. Run `P0-03` through diarization after explicit model setup.
8. Repeat the smoke run offline.
9. Record versions, model revisions, VRAM, timings, limitations, and failures.
10. Only after the stack passes, create and commit the initial `uv.lock` and update the dependency baseline.

## 2026-08-01 media update

The four Phase 0 recordings have been exported and probed. Their authoritative metadata and readiness assessment are recorded in [`WSL config/PHASE0_MEDIA_INVENTORY.md`](WSL%20config/PHASE0_MEDIA_INVENTORY.md).

Immediate resume point:

1. Check left/right identity for P0-01 and P0-04 using the documented FFmpeg difference command.
2. Confirm whether the manually checked P0-01 transcript is ready.
3. Rename the cases to stable `p0-XX` identifiers.
4. Then define and execute the dependency compatibility matrix.

Media gate update: completed. P0-01 is true mono and its manually checked reference is ready. P0-04 is a near-identical lossy dual-mono fixture with a decoded left/right residual of `-71.1 dB` mean and `-41.2 dB` peak. Proceed with the dependency compatibility matrix.

Dependency research update: Candidate A is documented in [`WSL config/DEPENDENCY_CANDIDATE_MATRIX.md`](WSL%20config/DEPENDENCY_CANDIDATE_MATRIX.md). It follows the stable WhisperX 3.8.6 upstream stack: PyTorch 2.8.0/cu128, matched audio/vision packages, TorchCodec 0.7, and pyannote.audio 4.0.7 as the first compatibility hypothesis.

WSL execution update: the exact restartable environment procedure is documented in [`WSL config/PREPARE_PHASE0_WSL.md`](WSL%20config/PREPARE_PHASE0_WSL.md). The future production installation procedure has a separate placeholder at [`WSL config/INSTALL_APPLICATION.md`](WSL%20config/INSTALL_APPLICATION.md) and must be completed only after the production lockfile and CLI exist.

## Decisions still intentionally open

These must be resolved by measurements, not guessed in advance:

- final ASR model for the `accurate` preset;
- exact PyTorch/CUDA/WhisperX/pyannote versions;
- Polish and English alignment models and revisions;
- validated batch size;
- peak VRAM and model-unloading procedure;
- final channel-classification thresholds;
- public external dataset license and redistribution permissions.

## Phase 0 exit criteria

Phase 0 is complete only when:

- CUDA-enabled PyTorch sees the RTX 3090;
- Polish ASR and word alignment succeed;
- two-speaker diarization succeeds;
- a second run succeeds with network access disabled;
- the compatible dependency set is locked and reproducible;
- models, tokens, private data, caches, and generated transcripts remain outside the application repository.
