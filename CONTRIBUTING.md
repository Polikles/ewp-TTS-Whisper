# Contributing

## Rules

1. Every functional change must reference an FR/NFR requirement or add an ADR.
2. A CLI change requires an update to `docs/05-cli-specification.md` and a contract test.
3. A JSON change requires updates to the schema, examples, and `schema_version`.
4. An ML backend update requires a quality regression benchmark.
5. Secrets and private audio samples must never be committed to the repository.

## Pull request checklist

- [ ] Linting and type checking pass.
- [ ] Documentation is updated.
- [ ] Existing data is not overwritten.
- [ ] The offline path needs no network access.
- [ ] Generated results conform to the schema.
- [ ] WER, timestamp, or DER impact has been evaluated when the change affects ML behavior.
