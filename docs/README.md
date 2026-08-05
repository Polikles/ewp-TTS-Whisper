# Documentation Index

## Normative documents

| Document | Scope |
|---|---|
| [01 - Product scope](01-product-scope.md) | Purpose, users, MVP, and exclusions |
| [02 - Requirements](02-requirements.md) | Functional and non-functional requirements with identifiers |
| [03 - Architecture](03-architecture.md) | Modules, pipeline, and responsibility boundaries |
| [04 - Input and grouping](04-input-and-grouping.md) | Files, directories, episode groups, channels, and SHA-256 |
| [05 - CLI specification](05-cli-specification.md) | Commands, options, exit codes, and interactive behavior |
| [06 - Configuration](06-configuration.md) | TOML, presets, and configuration precedence |
| [07 - Results data model](07-results-data-model.md) | Canonical output and partial-state files |
| [08 - Export formats](08-export-formats.md) | TXT, SRT, VTT, and optional segments JSON |
| [09 - State, errors, and logging](09-state-errors-and-logging.md) | Versioning, atomicity, retries, and warnings |
| [10 - WSL2 installation](10-wsl2-installation.md) | Reference environment, CUDA, models, and offline setup |
| [11 - Security and privacy](11-security-and-privacy.md) | Privacy, tokens, temporary files, and network use |
| [12 - Testing and acceptance](12-testing-and-acceptance.md) | Application and audio-material checklists |
| [14 - Dependency baseline](14-dependency-baseline.md) | Verified environment starting point |
| [15 - Glossary](15-glossary.md) | Standardized terminology |
| [16 - Risk register](16-risk-register.md) | Technical risks and mitigations |
| [17 - Definition of Done](17-definition-of-done-mvp.md) | MVP completion criteria |
| [18 - Quality evaluation](18-quality-evaluation.md) | Manifest-driven WER/CER reports and review diffs |
| [20 - MVP requirements traceability](20-mvp-requirements-traceability.md) | Requirement-by-requirement implementation, test, evidence, and deferral status |
| [99 - Version 2 roadmap](99-roadmap-v2.md) | GUI, audio repair, LLMs, benchmarks, and Docker |
| [Sources](SOURCES.md) | Official technical sources used by the specification |

## Architecture Decision Records

- [ADR-0001: WSL2 as the reference environment](adr/0001-wsl2-reference-environment.md)
- [ADR-0002: Canonical results JSON](adr/0002-canonical-results-json.md)
- [ADR-0003: Conservative channel classification](adr/0003-channel-classification.md)
- [ADR-0004: SHA-256 and non-destructive versioning](adr/0004-hashing-and-versioning.md)
- [ADR-0005: No audio repair in the MVP](adr/0005-no-audio-repair-in-mvp.md)
- [ADR-0006: Interface-independent application core](adr/0006-interface-independent-core.md)
- [ADR-0007: Accurate-preset ASR model selection](adr/0007-accurate-preset-asr-model.md)
- [ADR-0008: Mixed-source speaker diarization](adr/0008-mixed-source-diarization.md)
- [ADR-0009: Long-duration operational baseline](adr/0009-long-duration-operational-baseline.md)
- [ADR-0010: Isolated wheel installation procedure](adr/0010-isolated-wheel-installation.md)
- [ADR-0011: Language-specific offline alignment selection](adr/0011-multilingual-alignment-selection.md)
- [ADR-0012: Explicit group identity and validation contract](adr/0012-explicit-group-contract.md)
- [ADR-0013: Release observability and speaker order](adr/0013-release-observability-and-speaker-order.md)
- [ADR-0014: Dataset-dependent quality gates](adr/0014-dataset-dependent-quality-gates.md)
- [ADR-0015: MVP input format matrix](adr/0015-input-format-matrix.md)
- [ADR-0016: Subtitle readability and correction boundary](adr/0016-subtitle-readability-and-correction-boundary.md)
- [ADR-0017: Content-aware directory discovery after MVP](adr/0017-content-aware-directory-discovery.md)
- [ADR-0018: Synthetic fast-speech and recorder-noise acceptance](adr/0018-fast-noisy-audio-acceptance.md)
- [ADR-0019: Fresh Ubuntu 24.04 WSL installation](adr/0019-fresh-wsl-installation.md)

## Implementation guidance

- [Architecture and coding rules](ARCHITECTURE_AND_CODING_RULES.md)
- [Archived MVP planning documents](../archive/mvp-planning/README.md)
- [Testing strategy](TESTING_STRATEGY.md)
- [WSL setup and verification](../WSL%20config/README.md)

## Machine-readable artifacts

- `schemas/results.schema.json` - JSON Schema for canonical results.
- `schemas/segments.schema.json` - JSON Schema for the derived segment export.
- `examples/config.example.toml` - complete example configuration.
- `examples/results.example.json` - minimal valid result.
- `examples/segments.example.json` - example sentence-level export.
