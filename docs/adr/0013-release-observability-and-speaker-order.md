# ADR-0013: Release observability and chronological default speakers

- Status: accepted
- Date: 2026-08-04

## Decision

Automatically generated speaker identities are assigned by first chronological speech,
not source or channel order. Explicit and filename-derived labels remain unchanged, while
canonical speaker IDs and default `SpeakerN` labels are consistent across sources,
speakers, segments, words, overlap metadata, and processing-stage details.

`runtime.log_format = "jsonl"` makes application records on stdout valid JSON Lines and
routes incidental backend output to stderr. Records contain timestamp, level, event,
run/job identity, stage, elapsed milliseconds, and safe context. Canonical results retain
detailed stage timings and now populate `processing.environment.peak_vram_bytes` from
PyTorch when CUDA runtime metrics are available.

Missing pinned ASR, alignment, and diarization snapshots report the preparation document
and doctor command instead of only stating that the snapshot is absent.

## Evidence

Commits `ff5bc13`, `f76410a`, `7b5dcc4`, and `16a07af` passed the complete automated
suite, ending with 254 tests. The Ubuntu 24.04 WSL2 RTX 3090 workstation then executed
[`RUN_RELEASE_OBSERVABILITY.md`](../../WSL%20config/RUN_RELEASE_OBSERVABILITY.md) from
commit `9de5b3c`.

P2-01 completed offline in 21,482 ms. JSONL stdout contained one parseable
`TRANSCRIPTION_COMPLETED` record with run and job identity; WhisperX, Lightning, and
pyannote messages appeared only on stderr. The canonical result contained two speakers,
eight measured stages, chronological `Speaker1`/`Speaker2` identities, and a PyTorch peak
allocation of 1,780,463,104 bytes.

A controlled missing-ASR-snapshot run returned exit code 4, included
`docs/10-wsl2-installation.md`, and emitted no traceback. Duplicate replay produced a
structured skip record and left no successful work directory.

Accepted output hashes:

```text
c3cb48e918f198e06ca2bba5483f28cd5fa52ae7a982f7add6365ebc1599e6a4  p2-01-split-speakers_results.json
145620b0962095ba852ac1533cd67d516c977723f812d91b06b8ad2dd71a1923  p2-01-split-speakers_subtitles.srt
2f2d3093af71a6cde7991c976ff04a172ee6e93349c3addcf0cdca77d11331c6  p2-01-split-speakers_subtitles.vtt
bb9bdb17be9a08b3bfe2814786f769a60d27ba4b988c85f5b351754c726fc015  p2-01-split-speakers_transcript.txt
```

## Consequences

Source order remains stable provenance and does not imply speaker chronology. Structured
stdout is suitable for automation, while operators can retain backend diagnostics from
stderr. `peak_vram_bytes` is the observed PyTorch process allocation peak, not total GPU
board usage reported by `nvidia-smi`.
