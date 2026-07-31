# ADR-0005: No Audio Repair in the MVP

- Status: accepted
- Date: 2026-07-29

## Decision

The MVP may analyze basic quality metrics and emits warnings, but it does not denoise, normalize, or otherwise modify audio.

## Rationale

An automatic filter may damage speech, and different defects require different methods. Typical input is assumed to have already been edited because EWP-transcripts is a post-production tool.

## Consequences

Audio repair and comparison of original versus repaired transcription are deferred to version 2.
