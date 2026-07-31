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
