# ADR-0005: No Audio Repair in the MVP

- Status: accepted
- Date: 2026-07-29

## Decision

The MVP may analyze basic quality metrics and emit warnings, but it does not denoise,
normalize, or otherwise modify audio.

## Rationale

An automatic filter may damage speech, and different defects require different methods. Typical input is assumed to have already been edited because EWP-transcripts is a post-production tool.

## Consequences

Audio repair and comparison of original versus repaired transcription are deferred to version 2.

## Phase 2 validation evidence

On 2026-08-03, the production `transcriber inspect` path detected all four required
warning conditions in deterministic external PCM fixtures:

| Fixture | Required warning | Result |
|---|---|---|
| Q2-01 | `AUDIO_CLIPPING` | PASS |
| Q2-02 | `AUDIO_LOW_LEVEL` | PASS |
| Q2-03 | `AUDIO_CHANNEL_IMBALANCE` | PASS |
| Q2-04 | `AUDIO_HIGH_SILENCE_RATIO` | PASS |

The human-readable Q2-01 report displayed `WARNING AUDIO_CLIPPING` while returning a
normal inspection result. This confirms that warnings are visible and non-fatal.

The fixture hashes before and after inspection were identical:

```text
fd9db167d6fce87aaf436b9d6ba8976bd62849eb4dd99d4feebbd2f20818f810  q2-01-clipping.wav
233825d66ba057bd2937aa6e2953073f39a7264274d0a96fe375f4956dd76edf  q2-02-low-level.wav
9226218ae611b1e78caf9eb4ae9bbda08102ebaf42e4af560c42b2804c13d04f  q2-03-imbalance.wav
01f8aa8ddb61437eab728f06acb1a5bcbb55482dcd3a9443c2a080efeb0fcc09  q2-04-high-silence.wav
```

This provides direct evidence that analysis did not modify source audio. The external
JSON inspection report has SHA-256:

```text
918eaf7cd3349f9eb3d796eb45e5d5fe16c2fdb7933d9759ebe1817dfeeaaeb4  quality-inspection.json
```

These synthetic files validate diagnostic mechanics and thresholds, not their precision
or recall on a representative speech corpus. Threshold recalibration remains required
after the larger dataset exists. The target WSL workstation subsequently passed the full
repository gate with 75 tests, no skipped FFmpeg test, and a clean worktree. The same 75
tests also pass on the development VM after installing FFmpeg 8.0.1.
