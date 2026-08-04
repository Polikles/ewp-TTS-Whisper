# ADR-0010: Isolated wheel installation procedure

- Status: accepted
- Date: 2026-08-04

## Decision

Release-candidate wheel validation uses a fresh external Python 3.12 virtual
environment and two distinct installation steps:

1. `uv sync --project REPOSITORY --active --locked --offline --no-dev
   --no-install-project` installs the exact runtime dependency graph from native
   `uv.lock`, including per-package CUDA index provenance, without installing the source
   checkout;
2. `uv pip install WHEEL --offline --no-deps` installs only the built application
   artifact and cannot re-resolve or mutate the accepted dependency set.

Validation commands run outside the repository. The imported `ewp_transcripts` module
must resolve under the isolated environment's `site-packages`, and a short real
transcription must complete with model hubs offline.

The pip-compatible runtime requirements export remains hashed release evidence. It is
not the authoritative offline installation input because requirements format cannot
represent uv's per-package index selection and may require simple-index metadata absent
from an offline cache.

## Rationale

Installing the wheel directly with dependency resolution would test its broad package
metadata against whatever indexes happen to be current rather than reproduce the
accepted ML/CUDA environment. Installing the source project through ordinary `uv sync`
would make it difficult to prove that the wheel is complete and importable. Native-lock
dependency synchronization followed by a no-dependency wheel install satisfies both
reproducibility and artifact-provenance requirements.

## Target validation evidence

On 2026-08-04, the procedure from commit `e25753a` completed on Ubuntu 24.04 under WSL2
with an RTX 3090. The source environment passed all 231 automated tests, `HF_TOKEN` was
absent, and the isolated environment contained 124 mutually compatible packages.

Built artifacts:

```text
5cb1fe561d45f3b830b66274c3008ad844fb931fbd3f85dc35c5de202721affd  ewp_transcripts-0.1.0-py3-none-any.whl
8bfc980f1919e44b71b9a7dfe3287ccd74ea25634cd35cd277c3ef28e7a74562  ewp_transcripts-0.1.0.tar.gz
```

Dependency evidence:

```text
b4bdea1f4c28aa66ce36a3820e33ba2ab81d4edc70d89b19c0f84de42c3faf61  uv.lock
99d40de8958a6eed4a312aaf31e4fa943ce65fa92348c1f41aae125be5304a19  runtime-requirements.txt
```

The installed environment exactly matched the accepted critical versions:

- EWP-transcripts 0.1.0;
- WhisperX 3.8.6;
- PyTorch, torchaudio, and torchvision 2.8.0/2.8.0/0.23.0 with `+cu128`;
- torchcodec 0.7.0;
- pyannote.audio 4.0.7;
- faster-whisper 1.2.1 and CTranslate2 4.8.1;
- Transformers 4.57.6 and Triton 3.4.0;
- CUDA runtime 12.8 with the NVIDIA GeForce RTX 3090 visible.

`transcriber --version`, help, all six MVP command registrations, `doctor`, `inspect`,
and `dry-run` worked from the installed environment. Import provenance was:

```text
/home/linuch/transkrypcje/ewp-transcripts-testdata/phase0/phase9-wheel-XHlT9wE1/venv/lib/python3.12/site-packages/ewp_transcripts/__init__.py
```

P0-01 then completed through the installed wheel with Hugging Face Hub and Transformers
offline, generated canonical JSON plus TXT/SRT/VTT, validated against the authoritative
schema, skipped all artifacts on duplicate replay, and left no workdir. The repository
remained clean.

External smoke-test hashes:

```text
093e3d450cc9c1a68b2b8c71fc2d0f7aa0a2a303d124662d7e6ec3b89ccb93e1  p0-01-single-short_results.json
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  p0-01-single-short_subtitles.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  p0-01-single-short_subtitles.vtt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  p0-01-single-short_transcript.txt
800d7b8d5ef4bd4186658f799c728c53896ffa254dca3a2b4a441e2f21674d72  inspect.json
```

## Procedural corrections

The first runbook revision carried the original promoted Phase 0 lock hash. Commit
`4939354` recorded the current committed hash after development-only JSON Schema tooling
was added; accepted runtime ML versions were unchanged.

The first isolated dependency attempt used `uv pip sync` with the exported requirements
and failed offline while resolving `annotated-doc`. The subsequent intentional
`--no-deps` wheel install left eight missing application dependencies and was correctly
rejected by `uv pip check`. No command from that incomplete environment was accepted as
evidence. Commit `e25753a` switched dependency installation to native locked `uv sync`,
recreated the venv, and passed the complete gate.

## Consequences and limits

This proves that the wheel contains and exposes the application correctly and works with
the locked runtime graph on the already-qualified workstation. It is not a fresh-OS
test: the system packages, uv cache, model cache, WSL distribution, FFmpeg, and NVIDIA
driver were already prepared. The MVP release gate still requires executing the
documented installation flow in a fresh Ubuntu 24.04 WSL distribution or equivalent
clean validation VM.
