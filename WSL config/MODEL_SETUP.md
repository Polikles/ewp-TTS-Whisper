# Prepare the pinned models explicitly

Run this from the synchronized repository after `INSTALL_APPLICATION.md`. Model setup is
an explicit online operation; normal transcription remains offline and never downloads a
missing resource.

For the guided path, run `./scripts/setup-models.sh`. It performs the exact pinned downloads
and checks below, and privately prompts for the gated Hugging Face token. The remaining
sections document the equivalent manual procedure for inspection and troubleshooting.
First-time users should follow [`HUGGING_FACE_TOKEN.md`](HUGGING_FACE_TOKEN.md) for the
browser-based terms, read-only token, hidden prompt, and revocation steps.

## 1. Prepare cache locations

```bash
cd "$HOME/transkrypcje/ewp-transcripts"
export HF_HOME="$HOME/.cache/huggingface"
export NLTK_DATA="$HOME/nltk_data"
mkdir -p "$HF_HOME" "$NLTK_DATA"
chmod 700 "$HF_HOME"
```

## 2. Download public immutable snapshots

```bash
uv run --locked hf download Systran/faster-whisper-large-v2 \
    --revision f0fe81560cb8b68660e564f55dd99207059c092e
uv run --locked hf download jonatasgrosman/wav2vec2-large-xlsr-53-polish \
    --revision 6b1cea36bd8bc5f65ec8081667cd9c0207d51970
uv run --locked hf download facebook/wav2vec2-base-960h \
    --revision 22aad52d435eb6dbaf354bdad9b0da84ce7d6156

(
    cd /tmp
    "$HOME/transkrypcje/ewp-transcripts/.venv/bin/python" -P -m nltk.downloader \
        -d "$NLTK_DATA" punkt_tab
)
```

The English aligner is installed because `en` and `auto` are supported execution modes,
although English quality is not yet characterized by the reference corpus.

## 3. Download the gated diarization snapshot

First accept the terms for `pyannote/speaker-diarization-community-1` in the Hugging Face
account and create a read-only token. Read it without echoing or placing it in history:

```bash
read -rsp "Hugging Face read token: " HF_TOKEN
echo
export HF_TOKEN
test -n "$HF_TOKEN" && echo "HF_TOKEN: present"

uv run --locked hf download pyannote/speaker-diarization-community-1 \
    --revision 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee

unset HF_TOKEN
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: removed"
```

Never pass the token as a command argument or include it in shared output.

## 4. Verify exact snapshots and readiness

```bash
test -d "$HF_HOME/hub/models--Systran--faster-whisper-large-v2/snapshots/f0fe81560cb8b68660e564f55dd99207059c092e" \
    && echo "ASR model: present"
test -d "$HF_HOME/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/6b1cea36bd8bc5f65ec8081667cd9c0207d51970" \
    && echo "Polish alignment: present"
test -d "$HF_HOME/hub/models--facebook--wav2vec2-base-960h/snapshots/22aad52d435eb6dbaf354bdad9b0da84ce7d6156" \
    && echo "English alignment: present"
test -d "$HF_HOME/hub/models--pyannote--speaker-diarization-community-1/snapshots/3533c8cf8e369892e6b79ff1bf80f7b0286a54ee" \
    && echo "Diarization model: present"
test -d "$NLTK_DATA/tokenizers/punkt_tab" && echo "NLTK punkt_tab: present"

test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
uv run --locked transcriber doctor
```

Every required check should pass. Keep `NLTK_DATA="$HOME/nltk_data"` in the shell used
for transcription, or configure the same standard location in the user's environment.
