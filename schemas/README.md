# JSON Schemas

The schemas use JSON Schema Draft 2020-12.

- `results.schema.json` — canonical results and partial/failed state files. Schema `1.1` adds
  segment `kind`; older artifacts default to `speech` in the domain model.
- `segments.schema.json` — optional derived segment export; schema `1.1` emits event kind.
- `revision.schema.json` — immutable corrected transcript snapshots.
- `translation.schema.json` — immutable complete Polish-English translation snapshots.

New schemas use stable public repository URLs. Older schemas retain their original IDs
until a deliberate schema-version migration changes them.

Structural schema validation does not replace semantic validation. The implementation
must also validate chronology, speaker/source references, consistency between status and
filename, episode-signature correctness, translation direction, source verification,
complete token ownership, and snapshot statistics.
