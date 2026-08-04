# ADR-0014: Defer dataset-dependent quality gates beyond the functional MVP

- Status: accepted
- Date: 2026-08-04

## Context

The current manually verified corpus contains three untimestamped Polish cases. It is
enough to establish an initial lexical WER/CER baseline and compare large-v2 with
large-v3, but it cannot produce statistically reliable release thresholds or measure
timestamp and diarization accuracy. No manually verified English sample is available.

The MVP is intended to transcribe the existing private audio archive. Those transcripts
will be manually reviewed during productive use, after which licensed excerpts can form
a much larger and more representative reference corpus. Creating synthetic thresholds
before those references exist would give false confidence.

## Decision

The functional MVP may be accepted without closing these dataset-dependent quality gates:

- end-to-end English ASR/alignment accuracy;
- Polish/English code-switch quality;
- word-start and word-end timestamp error distributions;
- diarization DER/JER and annotated overlap error;
- three-speaker quality;
- statistically meaningful regression thresholds across representative material.

These are explicit quality deferrals, not removal of functionality. Polish, English, and
automatic language modes remain available. Timestamp provenance, source-speaker
assignment, mixed-source diarization, overlap metadata, and subtitle generation remain
covered by structural, automated, and manual integration tests. Documentation must not
claim quantitative accuracy for an unmeasured language or metric.

## Existing evidence

The three-case Polish lexical baseline records:

- P0-01 WER 0.00881057 and CER 0.00326158;
- P0-02 WER 0.00814332 and CER 0.00354359;
- P0-03 WER 0.19106047 and CER 0.17072846, dominated by deliberately overlapping speech;
- macro WER 0.06933812 and CER 0.05917788;
- micro WER 0.11352170 and CER 0.09807910.

Manual review found only minor errors in P0-01/P0-02 and no notable hallucinations.
Long-duration Polish validation found near-perfect transcripts apart from occasional
names and small lexical errors, no invented speech during long silence, stable two-speaker
labels, and no false speech at concatenated episode boundaries. These observations are
useful evidence but are not substitutes for a larger annotated corpus.

## Reopening criteria

Reopen and replace this deferral when the archive workflow yields:

1. a larger licensed corpus of manually corrected Polish excerpts covering the supported
   topologies and difficult material;
2. at least one manually verified English smoke sample, followed by a representative
   English subset;
3. a manually word-aligned subset for timestamp MAE and percentile metrics;
4. speaker-time annotations for mixed-source DER/JER and overlap scoring;
5. enough cases to define regression thresholds without one recording dominating the
   conclusion.

The corpus, derived diffs, and private transcripts remain external to this repository
unless their license and privacy status explicitly permit publication.

## Consequences

The Definition of Done keeps the combined WER/CER/timestamp/DER baseline item unchecked.
Release notes and README retain the provisional English and small-corpus limitations.
Future model, alignment, or preset changes must rerun the current lexical baseline and,
once available, the expanded quality suite.
