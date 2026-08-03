# ADR-0002: Canonical `results.json`

- Status: accepted
- Date: 2026-07-29

## Decision

Every successful run creates a rich `results.json`. TXT, SRT, VTT, and segments JSON are derived exports that do not require source audio.

## Rationale

- no repeated expensive ASR;
- subtitle parameters can be changed later;
- future GUI and dataset projects can reuse the same data;
- reproducibility and diagnostics.

## Consequences

The schema is a public project contract and requires versioning and compatibility tests.

## Phase 4 implementation and validation evidence

On 2026-08-03, the canonical-result and derived-export vertical slice passed on the
target Ubuntu 24.04 WSL2 workstation at commit `9c00f8c`:

- the locked environment resolved 139 packages and passed `uv pip check`;
- formatting, linting, strict typing, and all 150 automated tests passed;
- the checked-in canonical example produced TXT, SRT, VTT, and schema-valid segments
  JSON using only `transcriber export`;
- TXT contained speaker blocks, one sentence per line, and no timestamps;
- SRT and VTT structure, timestamps, and on-change speaker labels passed;
- segments JSON passed the authoritative schema and retained canonical-result
  provenance;
- export succeeded with `CUDA_VISIBLE_DEVICES` empty and Hugging Face/Transformers
  offline controls enabled;
- no source audio, model initialization, download, or token was required;
- no temporary export file remained and the repository worktree was clean.

The controlled external artifact hashes were:

```text
6ab17f931db9037d9ca982f7a111336ae931c1ee6368f2a6bcfb0ba575323b0c  S01E01_results.json
296de1f05a30b7cbe80d3de5f5b319789b542e1f28c1da2f18e9cf5e11de40f6  S01E01_segments.json
0c61b0cdf2ff00dcf63ed254b8e3d686613ad32bfadef2d65aef94abcaac5b1d  S01E01_subtitles.srt
7bb305e38d7a5df65c0ec5c83eb6c4398de3b8d8a8fe7f12cd3eaced7844be58  S01E01_subtitles.vtt
16b0993ded8a17bc1bfc934a6c9ea97b3adc5671e36130e25b643e1674d045e3  S01E01_transcript.txt
```

This gate proves export behavior against the controlled canonical example. Subtitle
tuning against longer live Polish results remains part of later end-to-end phases.
