# EWP-transcripts work status

Last updated: **2026-07-31**.

Latest resume update: **2026-08-01**.

Use this file as the starting point for the next work session.

## Current stage

The project is in **Phase 0 execution: integrated GPU pipeline validation**.

No application code or production package scaffold has been created yet. The dependency, CUDA, model-acquisition, ASR/alignment, and diarization component gates have passed on the target workstation. The next gate combines those components in one sequential job.

## Authoritative resume point

Resume with [`WSL config/RUN_PHASE0_INTEGRATED.md`](WSL%20config/RUN_PHASE0_INTEGRATED.md), starting at section 1.

The owner should run sections 1–6 in local WSL and return the sanitized stop-point evidence. Stop immediately if the run attempts a download, requests a token, fails on CUDA, or does not return exclusive diarization.

After the integrated gate passes:

1. record its accepted evidence in [`WSL config/PHASE0_RESULTS.md`](WSL%20config/PHASE0_RESULTS.md);
2. run a second complete job to verify repeated sequential loading and unloading;
3. perform the environment-level network-blocked replay;
4. continue the preliminary model/preset comparison;
5. promote the approved dependency definition and external spike lockfile only after all Phase 0 gates pass.

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

The confirmed WSL spike documentation through the integrated-run instructions is included in the session-closing documentation commit.

An untracked file named `LICENSE_SKETCH.TXT` exists in the repository. It belongs to the project owner and remains intentionally uncommitted.

At the end of today, documentation link validation and `git diff --check` passed.

## Backlog

- Review `LICENSE_SKETCH.TXT`, select and finalize the future repository license, then replace the sketch with the appropriately named final license file in a dedicated change. Do not commit the sketch as the repository license without that review.
- Build the manifest-driven corpus WER/CER runner and human-readable transcript diff after additional manually verified references are available.

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

Resolver update: Phase 0 sections 0–5 passed. `uv lock` resolved 117 packages under CPython 3.12.3. Key versions are CTranslate2 4.8.1, faster-whisper 1.2.1, huggingface-hub 0.36.2, Transformers 4.57.6, and Triton 3.4.0. PyTorch-family versions correctly use the `+cu128` suffix. Continue with `PREPARE_PHASE0_WSL.md` sections 6–10.

Environment gate update: sections 6–10 passed. The lock hash is `a309c86ba2a06b86842ee3cb56dffc76a15e635f72a2f46bdf5847e7ab88c14c`; dependency checks, WhisperX import, CUDA tensor execution on RTX 3090, and TorchCodec decoding all passed. Evidence is in [`WSL config/PHASE0_RESULTS.md`](WSL%20config/PHASE0_RESULTS.md). Continue with [`WSL config/PREPARE_PHASE0_MODELS.md`](WSL%20config/PREPARE_PHASE0_MODELS.md).

Model-preparation update: path/privacy checks and the `hf` CLI check passed. Step 3 stopped safely because `huggingface-hub==0.36.2` does not support the newer `hf download --dry-run` flag. The runbook now uses the compatible `HfApi.model_info` metadata query. Resume at model-preparation step 3.

Public-model update: metadata inspection and downloads passed for the ASR and Polish alignment models, and their downloaded snapshot names match the recorded immutable revisions. The NLTK command exposed Python's safe-path protection for the `regex` import, and `python -P` alone was insufficient in the uv project context. This is not a compatibility stopper. The runbook now invokes the already locked virtualenv interpreter from `/tmp`, with `-P`. Resume at model-preparation step 5, verify `punkt_tab`, then continue to the gated Community-1 steps.

Model-acquisition gate update: **passed**. NLTK `punkt_tab` is installed, Community-1 gated access and download succeeded at revision `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`, the downloaded revision matched the metadata query, and `HF_TOKEN` was removed from the shell. Cache sizes were 6.8 GB for Hugging Face and 15 MB for NLTK. Next, prepare and run the P0-01 Polish ASR and word-alignment smoke test using only the recorded local snapshots.

ASR/alignment execution update: the restartable P0-01 procedure is documented in [`WSL config/RUN_PHASE0_ASR_ALIGNMENT.md`](WSL%20config/RUN_PHASE0_ASR_ALIGNMENT.md). It fixes Polish explicitly, uses `float16` and batch size 4, loads both immutable snapshots locally with library offline controls, unloads ASR before alignment, retains transcript-bearing output only in the external spike workspace, and emits a sanitized measurement report. Resume at section 1 of that runbook.

Initial ASR/alignment result: **compatibility and gross-correctness PASS**. P0-01 completed in 4.095 seconds for ASR plus 1.175 seconds for alignment after model loads; all 226 generated words were timestamped. Manual comparison against the 227-word clean-studio reference found one substitution, one short omission, and minor punctuation differences. The run also exposed an unpinned Torch Hub download made by WhisperX's Silero VAD adapter, so it is not accepted as the local-only replay. The runbook now uses WhisperX's bundled Pyannote VAD asset and distinct output names. Rerun that corrected gate before moving to diarization. A manifest-driven corpus WER/CER and human-readable diff runner has been added to the testing backlog.

Bundled-VAD replay update: **PASS**. The corrected Pyannote-VAD run made no network download, produced the same transcript and manual quality assessment, timestamped every generated word, and released PyTorch allocations to 8.1 MiB after each stage. The Lightning in-memory checkpoint upgrade notice and Pyannote TF32 reproducibility warning are accepted; do not modify the installed checkpoint. The P0-03 regular/exclusive Community-1 procedure is ready in [`WSL config/RUN_PHASE0_DIARIZATION.md`](WSL%20config/RUN_PHASE0_DIARIZATION.md). Resume at section 1.

Community-1 component update: **technical PASS; manual speaker accuracy pending**. P0-03 ran locally without a token or download, produced two labels, returned both regular and exclusive diarization, and unloaded to 8.1 MiB of PyTorch allocation. Regular output contained 22 turns and 59.012 seconds of detected overlap; exclusive output contained 50 non-overlapping turns. These files intentionally contain only speaker intervals. The untimestamped reference cannot validate boundaries or overlap duration. Next, prepare the integrated P0-03 ASR, alignment, exclusive-diarization, and word-speaker-assignment gate so the owner can review speaker-labelled text.

Integrated-gate update: the restartable full P0-03 sequence is ready in [`WSL config/RUN_PHASE0_INTEGRATED.md`](WSL%20config/RUN_PHASE0_INTEGRATED.md). It runs ASR, Polish alignment, Community-1 exclusive diarization, and word-speaker assignment in one process; unloads every GPU model between stages; writes JSON and readable speaker-labelled text only to the external evidence directory; and emits sanitized performance, allocation, timestamp, and assignment counts. Resume at section 1.

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
