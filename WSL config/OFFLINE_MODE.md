# Offline operation

The packaged configuration defaults to `offline = true`, uses exact local snapshot
paths, and forbids transcription-time downloads. Prepare all models first with
`MODEL_SETUP.md`.

## Verify readiness

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
export NLTK_DATA="$HOME/nltk_data"
unset HF_TOKEN
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
uv run --locked transcriber doctor
```

For an additional library-level guard during a production run:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

Then use `transcriber inspect`, `dry-run`, or `transcribe` normally. A missing snapshot
must produce setup guidance rather than a network attempt. Do not clear the Hugging Face
or NLTK caches while a job is active.

An environment-level network-block test and byte-stable offline replay were completed
during MVP validation. The historical procedure is preserved under
`archive/mvp-validation-runbooks/`; it is not required for ordinary use.
