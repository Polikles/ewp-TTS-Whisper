# Prepare pinned English alignment

This procedure adds the language-specific word-alignment snapshot required by explicit
English and automatic language modes. The large-v2 ASR snapshot remains shared by Polish
and English.

## 0. Synchronize the application

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
uv sync --locked
make check
```

Expected commit: `aafd879` or later and 238 passing tests.

## 1. Confirm the immutable model metadata

```bash
export EWP_EN_ALIGN_REPO="facebook/wav2vec2-base-960h"
export EWP_EN_ALIGN_REVISION="22aad52d435eb6dbaf354bdad9b0da84ce7d6156"

uv run --locked python - <<'PY'
import json
import os
from urllib.request import urlopen

repo = os.environ['EWP_EN_ALIGN_REPO']
revision = os.environ['EWP_EN_ALIGN_REVISION']
with urlopen(f'https://huggingface.co/api/models/{repo}/revision/{revision}') as response:
    metadata = json.load(response)
assert metadata['sha'] == revision, metadata['sha']
print(f'repo={repo}')
print(f'revision={metadata["sha"]}')
print(f'files={len(metadata.get("siblings", []))}')
PY
```

This is the only step that queries model metadata. It must report the exact configured
revision.

## 2. Download the snapshot explicitly

```bash
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"

uv run --locked hf download "$EWP_EN_ALIGN_REPO" \
    --revision "$EWP_EN_ALIGN_REVISION"
```

The model is public, so no token is needed. Record the final snapshot path printed by the
command; do not share private usernames from that path.

## 3. Verify the standard cache location

```bash
export EWP_EN_ALIGN_SNAPSHOT="$HOME/.cache/huggingface/hub/models--facebook--wav2vec2-base-960h/snapshots/$EWP_EN_ALIGN_REVISION"

test -d "$EWP_EN_ALIGN_SNAPSHOT" && echo "English alignment snapshot: present"
test -s "$EWP_EN_ALIGN_SNAPSHOT/config.json" && echo "English alignment config: present"
test -s "$EWP_EN_ALIGN_SNAPSHOT/vocab.json" && echo "English alignment vocabulary: present"
printf 'English alignment revision: %s\n' "$(basename "$EWP_EN_ALIGN_SNAPSHOT")"
du -sh "$EWP_EN_ALIGN_SNAPSHOT"
```

If `HF_HOME` points somewhere else, set `models.english_alignment_snapshot_path` in
`transcriber.toml` to the printed snapshot directory.

## 4. Verify readiness for each language mode

```bash
uv run --locked transcriber doctor --json-output > /tmp/ewp-doctor-pl.json

printf '[general]\nlanguage = "en"\n' > /tmp/ewp-doctor-en.toml
uv run --locked transcriber doctor --config /tmp/ewp-doctor-en.toml --json-output \
    > /tmp/ewp-doctor-en.json

printf '[general]\nlanguage = "auto"\n' > /tmp/ewp-doctor-auto.toml
uv run --locked transcriber doctor --config /tmp/ewp-doctor-auto.toml --json-output \
    > /tmp/ewp-doctor-auto.json

uv run --locked python - <<'PY'
import json
from pathlib import Path

for mode in ('pl', 'en', 'auto'):
    report = json.loads(Path(f'/tmp/ewp-doctor-{mode}.json').read_text(encoding='utf-8'))
    assert report['ready'] is True, mode
    checks = {item['code']: item['status'] for item in report['checks']}
    assert checks['english_alignment_model'] == 'pass', (mode, checks)
    print(f'doctor language={mode}: PASS')
PY
```

## 5. Prove offline model loading without audio

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked python - <<'PY'
import os
from pathlib import Path

from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

snapshot = Path(os.environ['EWP_EN_ALIGN_SNAPSHOT'])
processor = Wav2Vec2Processor.from_pretrained(snapshot, local_files_only=True)
model = Wav2Vec2ForCTC.from_pretrained(snapshot, local_files_only=True)
print(f'English processor vocabulary: {len(processor.tokenizer.get_vocab())}')
print(f'English alignment model type: {model.config.model_type}')
print('English alignment offline load: PASS')
PY
```

This loads only the alignment model. End-to-end English transcription quality remains
provisional until an English recording becomes available.
