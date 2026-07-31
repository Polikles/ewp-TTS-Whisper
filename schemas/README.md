# JSON Schemas

The schemas use JSON Schema Draft 2020-12.

- `results.schema.json` — canonical results and partial/failed state files.
- `segments.schema.json` — optional derived segment export.

`$id` uses the `example.invalid` domain until a public repository URL is chosen. Replace it with a stable URI before the first release.

Structural schema validation does not replace semantic validation. The implementation must also validate chronology, speaker/source references, consistency between status and filename, and episode-signature correctness.
