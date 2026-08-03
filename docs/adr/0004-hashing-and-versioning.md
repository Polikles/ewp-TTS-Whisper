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

Every file in one output set uses the role-first version convention:

```text
episode_results.json
episode_transcript.txt
episode_results_v002.json
episode_results_v002.partial.json
episode_results_v002.failed.json
episode_transcript_v002.txt
episode_subtitles_v002.srt
episode_subtitles_v002.vtt
episode_segments_v002.json
```

The version suffix follows the output role. Planned files are placed directly in the
resolved output directory; the application does not add per-job subdirectories.

## Consequences

The output directory requires locking during lookup and version allocation.
