# Development

## Starting point

1. Read `docs/01-product-scope.md` and `docs/02-requirements.md`.
2. Review and accept the ADRs.
3. Create the repository structure described in Milestone 0 of `docs/13-implementation-plan.md`.
4. Treat `schemas/` as a public contract from the first vertical slice.
5. Implement `doctor`, `inspect`, and `dry-run` before the transcription pipeline.
6. Run separate WhisperX and channel-classification spikes before freezing the `accurate` preset.

## Technical recommendations

- Python 3.12;
- `uv` with a committed lockfile;
- strict typing;
- adapters around external tools;
- subprocess execution without `shell=True` for FFmpeg;
- small synthetic audio fixtures for automated tests;
- long or private audio samples stored outside the repository;
- deterministic JSON output and natural sorting.

## Branching and versions

- semantic versioning for the application;
- a separate version for the data schema;
- prereleases for ML-related changes;
- release notes must state changes to the quality baseline.
