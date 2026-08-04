# Dependency Baseline

The Phase 0 runtime dependency set was verified on **2026-08-02**. Its initially
promoted application lock had SHA-256
`c32602b6b9c3cf8edefdb861609029b8a05cd4ae1dd4cb51b4c69d31352a1359`.
Later schema-validation development tooling added `jsonschema` and its lock-only
transitive packages without changing the accepted runtime ML versions. The current
committed `uv.lock` SHA-256 is
`b4bdea1f4c28aa66ce36a3820e33ba2ab81d4edc70d89b19c0f84de42c3faf61`.

## 1. Environment

| Component | MVP decision |
|---|---|
| Host | Windows 11 |
| Runtime | WSL2 |
| Distribution | Ubuntu 24.04 LTS |
| Python | 3.12 |
| GPU | NVIDIA RTX 3090, 24 GB |
| Dependency management | `uv` + lockfile |
| Media tooling | FFmpeg + ffprobe |

Ubuntu 26.04 LTS has been released, but 24.04 remains the baseline until the complete ML/CUDA compatibility matrix passes.

## 2. ML backend

| Component | Baseline |
|---|---|
| WhisperX | 3.8.6, stable PyPI release |
| WhisperX Python requirement | `>=3.10,<3.14` according to package metadata |
| ASR model | `Systran/faster-whisper-large-v2` revision `f0fe81560cb8b68660e564f55dd99207059c092e` for the `accurate` preset |
| Diarization | local `pyannote/speaker-diarization-community-1` |
| Polish alignment | `jonatasgrosman/wav2vec2-large-xlsr-53-polish` revision `6b1cea36bd8bc5f65ec8081667cd9c0207d51970` |
| English alignment | select and pin after validation |

ADR-0007 records the three-case `large-v2`/`large-v3` comparison and the initial `large-v2` decision. The corpus is small, so the decision must be reevaluated on the larger manually verified Polish dataset. `large-v3` remains configurable.

## 3. Recommended application libraries

The ML dependency versions are frozen by `pyproject.toml` and the promoted `uv.lock`. Select and lock the remaining application libraries when their modules are introduced:

- CLI: Typer or an equivalent strongly typed library;
- models and validation: Pydantic 2;
- tests: pytest and Hypothesis;
- code quality: Ruff and mypy or pyright;
- WER/CER: jiwer;
- JSON Schema: Draft 2020-12;
- logging: structlog, or different structured layer that prevents secret leakage.

## 4. Pinning policy

- no wildcard dependency ranges;
- no dependencies from main branches in a release;
- prereleases only in isolated experiments;
- ML upgrades require the full quality benchmark;
- the lockfile is committed;
- `results.json` records versions actually used by the run.

## 5. Known backend limitations

- overlap in mixed material is not handled perfectly;
- diarization may miscount or misassign speakers;
- numbers and symbols may lack aligned timestamps;
- large-v2 provides multilingual English ASR and the MVP retains explicit `en` and
  automatic language selection, but English end-to-end quality is provisional until a
  language-appropriate pinned aligner and English smoke sample are validated;
- alignment is language-dependent;
- multichannel audio passed directly to pyannote is downmixed, so channel classification must occur first.
