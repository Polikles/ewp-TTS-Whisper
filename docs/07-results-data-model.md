# Canonical `results.json` Data Model

Machine-readable schema: [`../schemas/results.schema.json`](../schemas/results.schema.json).

## 1. Role

`results.json` is the immutable source of truth for a completed run. It contains enough information to create TXT, SRT, VTT, and `segments.json` without source audio and without ML models.

## 2. Filenames

```text
<job_id>_results.json
<job_id>_results_v002.json
```

During processing:

```text
<job_id>_results.partial.json
<job_id>_results.failed.json
```

The final name is used only for `status = completed`.

## 3. Top-level sections

### Metadata

- `schema_version`;
- `application_version`;
- `job_id`;
- `run_id`;
- `status`;
- `created_at`, `completed_at`;
- `result_version`.

### Episode

- episode identifier;
- `episode_signature_sha256`;
- topology: single file or group;
- selected language.

### Sources

Each source stores:

- the path supplied by the user;
- normalized working path;
- filename;
- SHA-256;
- size;
- media type;
- stream index;
- channel selection;
- duration and sample rate;
- assigned speaker.

### Processing

- effective configuration;
- model and library versions;
- stage timings;
- device and compute type;
- peak VRAM when available;
- channel classification;
- audio diagnostics.

### Speakers

Each speaker has:

```json
{
  "speaker_id": "speaker_001",
  "speaker_label": "jan",
  "speaker_source": "filename"
}
```

`speaker_id` is the stable internal key. `speaker_label` is display text and may later be edited without rebuilding references.

### Transcript

- canonical segments;
- words;
- timestamps in milliseconds;
- speaker IDs;
- overlap metadata;
- confidence when provided by a backend;
- timestamp provenance.

### Warnings

A list of structured warnings. Each warning contains a code, severity, message, and optional context.

## 4. Timestamps

Requirements:

- integer values;
- `start_ms >= 0`;
- `end_ms >= start_ms`;
- segments sorted chronologically;
- each word MUST fit inside its segment within a technical tolerance defined by the validator;
- missing alignment MUST NOT remove a word.

Fallback order:

1. `aligned`;
2. interpolation between neighboring words - `interpolated`;
3. assignment from the containing segment - `segment_fallback`.

## 5. Overlap

A segment may contain:

```json
{
  "overlap": true,
  "active_speaker_ids": ["speaker_001", "speaker_002"]
}
```

For separate channels, overlapping source segments may be preserved independently. For mixed input, detecting two active speakers does not guarantee that both utterances can be reconstructed.

## 6. Status values

- `running` - partial file only;
- `completed` - final results file only;
- `failed` - failed file;
- `cancelled` - failed/cancelled diagnostic file.

The `stages` field records stage outcomes but is not used to resume within a file. A later run restarts the entire job.

## 7. Immutability

After finalization, `results.json` is not modified by later `export` operations. Export history belongs in logs or a separate manifest, not in the canonical result.

## 8. Schema versioning

- compatible additive change: increment the minor version;
- field removal or semantic change: increment the major version;
- readers should reject unsupported major versions;
- CI validates the schema against examples and integration-test outputs.


## 9. Relationship to transcript revisions (planned v0.2.0)

Transcript correction does not change this schema or the meaning of canonical words and
segments. `results.json` continues to record what the ASR/alignment/diarization pipeline
produced.

A corrected transcript is stored in a separate full-snapshot revision described in
[`13-transcript-revisions.md`](13-transcript-revisions.md) and validated against
`schemas/revision.schema.json`. Revisions refer back to canonical `word_id` values and the
exact SHA-256 of this file.

Export code resolves either raw canonical text or a selected revision into an in-memory
`EffectiveTranscript`. This prevents editorial mutation of both `segment.text` and
`word.text` while preserving compatibility with existing v0.1 results.
