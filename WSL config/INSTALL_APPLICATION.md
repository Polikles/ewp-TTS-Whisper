# Install the internal MVP candidate

The supported installation is a source checkout synchronized from the committed
`uv.lock`. Installation does not download transcription models.

## 1. Clone into the Linux filesystem

```bash
mkdir -p "$HOME/transkrypcje"
cd "$HOME/transkrypcje"
git clone <AUTHENTICATED-REPOSITORY-URL> ewp-transcripts
cd ewp-transcripts
```

The repository is public but `0.1.0` is an internal release candidate. No public version
tag or hosted release exists; use the intended commit on `main`.

## 2. Install the locked environment

```bash
uv sync --locked
uv pip check
uv run --locked transcriber --version
uv run --locked transcriber --help
```

Expected application version: `0.1.0`. Help must list `doctor`, `inspect`, `dry-run`,
`transcribe`, `export`, and `clean`.

## 3. Check the machine before model setup

```bash
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
uv run --locked transcriber doctor
```

On a fresh machine, `doctor` should pass Python, WSL, Ubuntu, FFmpeg, GPU, and CUDA but
exit with code 3 because pinned model snapshots are not present. Continue with
[`MODEL_SETUP.md`](MODEL_SETUP.md); transcription never downloads a missing model.

## 4. Update an existing checkout

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
git pull --ff-only
uv sync --locked
uv pip check
```

Review `CHANGELOG.md` before using a newer commit on irreplaceable archive material.
