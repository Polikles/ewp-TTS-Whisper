#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./scripts/setup-models.sh [--public-only] [--yes]

Explicitly download and verify the immutable model snapshots used by EWP Transcriber.

  --public-only  Download public ASR/alignment models and NLTK data, but skip pyannote.
  --yes          Skip the confirmation before network downloads.
  --help         Show this help.

The gated pyannote model requires prior acceptance of its Hugging Face terms and a
read-only token. When HF_TOKEN is absent, the script reads it privately without echoing it.
The token is never passed as a command argument or written by this script.
EOF
}

public_only="false"
confirmed="false"
while (($#)); do
    case "$1" in
        --public-only) public_only="true" ;;
        --yes) confirmed="true" ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Error: unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
if [[ ! -f "$repo_root/pyproject.toml" || ! -f "$repo_root/uv.lock" ]]; then
    printf 'Error: script is not inside an EWP Transcriber source checkout.\n' >&2
    exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' \
        'Error: uv is unavailable.' \
        'Run ./scripts/install-fresh-ubuntu.sh --install, then open a new shell.' >&2
    exit 3
fi

export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export NLTK_DATA="${NLTK_DATA:-$HOME/nltk_data}"
mkdir -p -- "$HF_HOME" "$NLTK_DATA"
chmod 700 -- "$HF_HOME"

if [[ "$confirmed" != "true" ]]; then
    printf '%s\n' \
        "Public models and language data will be downloaded into $HF_HOME and $NLTK_DATA." \
        'Normal transcription remains offline and never downloads a missing model.'
    if [[ "$public_only" != "true" ]]; then
        printf '%s\n' \
            'The gated pyannote terms must already be accepted in the Hugging Face account.'
    fi
    read -r -p 'Continue? [y/N] ' answer
    [[ "$answer" =~ ^[Yy]$ ]] || { printf 'Cancelled.\n'; exit 4; }
fi

cd -- "$repo_root"
uv run --locked hf download Systran/faster-whisper-large-v2 \
    --revision f0fe81560cb8b68660e564f55dd99207059c092e
uv run --locked hf download jonatasgrosman/wav2vec2-large-xlsr-53-polish \
    --revision 6b1cea36bd8bc5f65ec8081667cd9c0207d51970
uv run --locked hf download facebook/wav2vec2-base-960h \
    --revision 22aad52d435eb6dbaf354bdad9b0da84ce7d6156

(
    cd /tmp
    "$repo_root/.venv/bin/python" -P -m nltk.downloader -d "$NLTK_DATA" punkt_tab
)

token_was_set="false"
cleanup_token() {
    if [[ "$token_was_set" == "true" ]]; then
        unset HF_TOKEN
    fi
}
trap cleanup_token EXIT

if [[ "$public_only" != "true" ]]; then
    if [[ -z "${HF_TOKEN:-}" ]]; then
        read -r -s -p 'Hugging Face read token: ' HF_TOKEN
        printf '\n'
        export HF_TOKEN
        token_was_set="true"
    fi
    if [[ -z "${HF_TOKEN:-}" ]]; then
        printf 'Error: a non-empty Hugging Face read token is required for pyannote.\n' >&2
        exit 3
    fi
    uv run --locked hf download pyannote/speaker-diarization-community-1 \
        --revision 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
fi

test -d "$HF_HOME/hub/models--Systran--faster-whisper-large-v2/snapshots/f0fe81560cb8b68660e564f55dd99207059c092e"
test -d "$HF_HOME/hub/models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/snapshots/6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
test -d "$HF_HOME/hub/models--facebook--wav2vec2-base-960h/snapshots/22aad52d435eb6dbaf354bdad9b0da84ce7d6156"
test -d "$NLTK_DATA/tokenizers/punkt_tab"
if [[ "$public_only" != "true" ]]; then
    test -d "$HF_HOME/hub/models--pyannote--speaker-diarization-community-1/snapshots/3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
fi

cleanup_token
token_was_set="false"
printf 'Pinned model preparation completed.\n'
if [[ "$public_only" == "true" ]]; then
    printf 'Pyannote was skipped; doctor will report diarization as missing.\n'
else
    uv run --locked transcriber doctor
fi
