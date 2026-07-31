# Implementation Plan

## 1. Principle

Build a stable domain model and headless pipeline before any GUI. ML integrations are adapters. Every milestone ends with automated tests and a working vertical slice.

## 2. Milestone 0 — Repository and tooling

- package structure;
- Python 3.12 and `uv`;
- lockfile;
- linting, formatting, type checking, and test runner;
- CPU-only CI;
- TOML loading;
- data models and JSON Schema;
- application and schema versioning rules.

**Deliverable:** `doctor` can run basic checks without ML backends.

## 3. Milestone 1 — Discovery, probing, and grouping

- Windows/WSL path normalization;
- file/directory discovery;
- explicit recursion;
- ffprobe adapter;
- audio-stream selection;
- SHA-256;
- suffix-based grouping;
- duration/sample-rate validation;
- warning models;
- `inspect` and `dry-run`.

**Deliverable:** deterministic batch plan without transcription.

## 4. Milestone 2 — Single source without diarization

- working directory;
- decoding to working WAV;
- WhisperX adapter;
- alignment;
- canonical word/segment normalization;
- `speaker_count=1`;
- partial, failed, and final result files;
- schema validation.

**Deliverable:** valid `results.json` for one speaker.

## 5. Milestone 3 — Channels and groups

- dual-mono detection;
- ambiguous-stereo fallback;
- split-speaker processing;
- multi-file groups;
- shared-timeline merge;
- overlap from separate sources;
- stable speaker IDs.

**Deliverable:** multi-source results without pyannote.

## 6. Milestone 4 — Diarization

- local pyannote Community-1 integration;
- `speaker_count` auto/N;
- regular and exclusive diarization when supported by the adapter;
- word-to-speaker reconciliation;
- normalized `SpeakerN` labels;
- overlap metadata and warnings.

**Deliverable:** mixed mono with multiple speakers.

## 7. Milestone 5 — Exports

- Polish and English sentence segmentation;
- TXT;
- `segments.json`;
- cue builder;
- SRT;
- VTT;
- `on-change` labels;
- export validators;
- `export` without audio.

## 8. Milestone 6 — Versioning and batch execution

- signature lookup;
- skip behavior;
- `--force`;
- automatic version for same name with different SHA;
- locks;
- batch summary;
- cancellation;
- cleanup.

## 9. Milestone 7 — Stabilization

- full audio matrix;
- 60-minute stability test;
- sequential batch test;
- ground-truth corpus;
- WER/CER/timestamp/DER baseline;
- clean installation on a fresh WSL2 environment;
- user documentation.

## 10. Initial epics/tickets

### E-001 Domain schema

- models for Source, EpisodeJob, Speaker, Word, Segment, and Warning;
- serialization;
- schema validation;
- fixture examples.

### E-002 Media inspection

- ffprobe JSON parser;
- stream selector;
- Windows path normalizer;
- duration and sample-rate validation.

### E-003 Grouping engine

- final-hyphen parser;
- sibling grouping;
- single-file rules;
- explicit groups;
- property-based tests.

### E-004 Result repository

- signatures;
- lookup;
- versions;
- atomic writes;
- locks.

### E-005 WhisperX spike

- install a stable release;
- compare `large-v2` and `large-v3` on the Polish corpus;
- select the `accurate` preset model;
- measure VRAM and batch size;
- test alignment of numbers and symbols.

### E-006 Channel-classifier spike

- Audacity dual-mono fixtures;
- correlation, RMS, and VAD;
- thresholds and ambiguous cases.

### E-007 Subtitle builder

- sentence segmentation;
- cue heuristic or dynamic programming;
- CPS and line-length validation;
- speaker labels.

## 11. Definition of Ready for a feature ticket

A ticket is ready when it has:

- linked FR/NFR identifiers;
- defined inputs and outputs;
- error cases;
- acceptance criteria;
- a fixture or test method;
- an indication of whether it changes JSON Schema or CLI behavior.
