# ADR-0019: Fresh Ubuntu 24.04 WSL installation

- Status: accepted
- Date: 2026-08-05

## Decision

The MVP clean-installation gate is accepted on a dedicated Ubuntu 24.04.4 LTS WSL2
distribution, separate from the established development distribution. The run validates
the committed locked source installation and complements ADR-0010, which already proves
isolated wheel provenance and a complete offline GPU transcription.

## Environment

The host reported WSL 2.7.11.0, Linux kernel 6.18.33.2, and Windows build
10.0.26200.8875. Both the established `Ubuntu-24.04` distribution and dedicated
`Ubuntu-ProjectB` distribution ran as WSL2. Inside the clean distribution:

- Ubuntu reported 24.04.4 LTS;
- the kernel reported `6.18.33.2-microsoft-standard-WSL2`;
- the project checkout was initially absent;
- Git 2.43.0, FFmpeg/ffprobe 6.1.1, and RTX 3090 passthrough were available;
- no Linux NVIDIA display driver was installed.

The run installed the required base packages after refreshing apt metadata. It did not
perform a complete `apt upgrade`; that does not invalidate the clean-install test because
the tested starting point was the current fresh Ubuntu 24.04.4 image and every required
system and application capability passed. The operational runbook now states both
`apt upgrade` and the uv installation commands explicitly rather than only linking to
their supporting guides.

## Installation and package evidence

Commit `a096d0d` was cloned into the clean distribution. `uv sync --locked` installed
139 packages, `uv pip check` found them mutually compatible, and all 279 automated tests
passed. The source distribution and wheel built successfully, application version
`0.1.0` ran, and help exposed all six MVP commands.

```text
b4bdea1f4c28aa66ce36a3820e33ba2ab81d4edc70d89b19c0f84de42c3faf61  uv.lock
0f6c30fe8b07573c14bcbc46049bda4b2773eae97eb78b68c59c2c28d7d1b82e  ewp_transcripts-0.1.0-py3-none-any.whl
e2decb0816eeb41f66d4a9f1eda2912b15ce88440c4329f57987110e3fb18cdb  ewp_transcripts-0.1.0.tar.gz
```

## Diagnostic and model-free evidence

The clean environment intentionally contained no model snapshots and no `HF_TOKEN`.
`doctor --json-output` returned the expected readiness exit code 3 while passing Python,
WSL, distribution, FFmpeg, ffprobe, GPU, CUDA, and token-sanitization checks. Its missing
model checks included the documented preparation guidance.

Inspect, dry-run, and cleanup preview then ran against a generated mono 48 kHz WAV
without loading models, creating a canonical plan but no result or workdir.

```text
a9d5e54cde6e2ebe2ca76eca8d42002217cec8c83d85d8080fd996de45e5c607  installation-smoke.wav
602a2d8e827a4b44e6472701b07d840bf26d153a306a96fce9e369277c9fbb70  doctor.json
b4cf72184bf97d095ed83128c2eebf34c96439c39a99ca20a5df154e6b17379d  inspect.json
3a3830e76396a7c8284cd7fcb3202f3d61aec48e65fd5a75a41ebe8d27ab2da2  dry-run.txt
d6da1a250ea89bf6afcc6848b4c2381bae78d829c4fe8009ac03211c8df7158b  clean.txt
```

## Consequences

The fresh-OS installation condition is complete. Installing model snapshots in every
new distribution is not required to repeat this gate: pinned-model preparation and real
offline transcription are already independently covered by the production GPU runbooks
and ADR-0010.

## 2026-08-25 cross-workflow follow-up

A second dedicated Ubuntu 24.04.4 WSL2 distribution (`Ubuntu-test-C`) extended the original
installation decision after the correction, translation, dictionary, YTT, and HTML workflows
existed. The host reported WSL 2.7.11.0 and kernel 6.18.33.2; the guest exposed the RTX 3090
with 24 GB VRAM. The guided installer supplied Git, FFmpeg/ffprobe, ripgrep, uv 0.12.5, and
the locked Python environment. The separate model setup installed and verified the pinned
ASR, Polish and English alignment, diarization, and NLTK resources without retaining an
`HF_TOKEN`.

The clean distribution then completed:

- the locked source checks and package build;
- offline `s0e00` transcription to canonical JSON, preview TXT, and segments JSON;
- a three-second replay that skipped completed outputs without changing the canonical hash;
- Gemini 2.5 Flash correction with the versioned project dictionary and recorded provenance;
- candidate-backed manual-review preparation;
- deterministic TXT, SRT, VTT, srv3 YTT, HTML, and segments export from the manually verified
  private revision;
- LM Studio/Bielik automated translation candidate publication, audit reconstruction, and
  candidate-backed translation-review preparation.

Runtime artifacts remained in disposable `/tmp` directories, private benchmark material and
API credentials remained outside Git, and the OpenRouter key was removed after use. This
closes the manual installation-through-workflow qualification; it does not convert automated
correction or translation candidates into final, manually verified artifacts.
