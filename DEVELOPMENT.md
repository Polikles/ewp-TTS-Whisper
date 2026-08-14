# Development

## Current starting point

1. Read `WORK_STATUS.md` for the active resume point.
2. Read the relevant product contract under `docs/` and accepted ADRs.
3. Use `docs/99-roadmap-v2.md` for post-MVP priorities.
4. Keep canonical schemas backward compatible or explicitly version changes.
5. Keep private audio, transcripts, model files, tokens, workdirs, and generated evidence
   outside the repository.

The Phase 0–9 implementation plans and validation procedures are historical and live
under `archive/`; they no longer define the active workflow.

## Local setup and quality gate

```bash
uv sync --locked
make check
uv build --offline
```

`make check` uses the synchronized environment and does not download models. Changes to
FFmpeg, model adapters, CUDA behavior, performance, or real transcription require a
focused external test against the private dataset in addition to the local gate.

## Change discipline

- Python 3.12 and the committed uv lockfile;
- strict typing and focused typed domain models;
- CLI-independent application services;
- lazy model imports and no hidden network access;
- subprocess argument lists without `shell=True`;
- deterministic, non-destructive filesystem behavior;
- small synthetic fixtures in Git and private/long material outside Git;
- requirement, ADR, schema, CLI, and changelog updates when their contracts change.

## Versions

- use semantic versioning for the application;
- version canonical schemas separately;
- treat ML changes as prerelease candidates until quality evidence is rerun;
- state quality-baseline changes and deferrals in release notes.

## Commit and pull-request titles

Use `<type>(<scope>): <summary>` for every commit and pull-request title. Supported
types are `docs`, `func`, `fix`, `test`, `refactor`, and `chore`. Keep the summary short
and imperative. Functional requirements should use their requirement ID as the scope,
for example `func(FR-XXX): add corrected transcript import`.

Every user-visible change must include a `CHANGELOG.md` entry. Accumulate work under
`Unreleased`, then move those entries into a dated release section and bump the semantic
version for each identifiable internal or public build. Do not append later fixes to an
older version section.
