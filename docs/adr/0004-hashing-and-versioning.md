# ADR-0004: SHA-256, Episode Signatures, and Non-Destructive Versioning

- Status: accepted
- Date: 2026-07-29

## Decision

- every file has a SHA-256 hash;
- every group has a deterministic episode signature;
- an existing identical signature is skipped without `--force`;
- `--force` creates `_v002`, `_v003`, and so on;
- the same name with a different signature automatically creates a new version;
- no result is overwritten.

## Consequences

The output directory requires locking during lookup and version allocation.
