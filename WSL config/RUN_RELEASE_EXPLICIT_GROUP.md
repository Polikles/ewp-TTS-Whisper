# Validate explicit group inputs

This runbook proves that independently named source files can be forced into one episode
with a caller-selected collision-safe `group_id`. It reuses the existing P2-01 fixture
and does not modify the source recording.

## 0. Synchronize and prepare an isolated sandbox

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_GROUP_SOURCE="$EWP_TESTDATA/audio/p2-01-split-speakers.wav"
export EWP_GROUP_ROOT="$(mktemp -d "$EWP_TESTDATA/phase10-explicit-group-XXXXXXXX")"
export EWP_GROUP_INPUT="$EWP_GROUP_ROOT/input"
export EWP_GROUP_OUTPUT="$EWP_GROUP_ROOT/output"
export EWP_GROUP_WORK="$EWP_GROUP_ROOT/work"
export EWP_GROUP_ID="p10-explicit-group"
mkdir -p "$EWP_GROUP_INPUT" "$EWP_GROUP_OUTPUT" "$EWP_GROUP_WORK"

test -s "$EWP_GROUP_SOURCE" && echo "P2-01 source: present"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
printf 'sandbox=%s\n' "$EWP_GROUP_ROOT"
```

Expected commit: `f8c8fd7` or later and 251 passing tests.

## 1. Export two unrelated mono source names

```bash
ffmpeg -v error -y -i "$EWP_GROUP_SOURCE" -af 'pan=mono|c0=c0' \
    "$EWP_GROUP_INPUT/alpha-track.wav"
ffmpeg -v error -y -i "$EWP_GROUP_SOURCE" -af 'pan=mono|c0=c1' \
    "$EWP_GROUP_INPUT/unrelated-voice.wav"

for path in "$EWP_GROUP_INPUT"/*.wav; do
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=duration -of default=noprint_wrappers=1 "$path"
done
sha256sum "$EWP_GROUP_INPUT"/*.wav
```

Both files must be mono, 44.1 kHz, and approximately 142.442 seconds long. Their stems
do not share an automatic group base.

## 2. Configure isolated mutable storage

```bash
cat > "$EWP_GROUP_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false

[runtime]
work_root = "$EWP_GROUP_WORK"
EOF
```

## 3. Inspect the explicit group

```bash
uv run --locked transcriber inspect \
    --group "$EWP_GROUP_INPUT/alpha-track.wav" \
    --group "$EWP_GROUP_INPUT/unrelated-voice.wav" \
    --group-id "$EWP_GROUP_ID" \
    --config "$EWP_GROUP_ROOT/transcriber.toml" \
    --json-output > "$EWP_GROUP_ROOT/inspect.json"

uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ['EWP_GROUP_ROOT'], 'inspect.json').read_text())
assert len(report['episodes']) == 1
episode = report['episodes'][0]
assert episode['job_id'] == os.environ['EWP_GROUP_ID']
assert [item['fingerprint']['filename'] for item in episode['sources']] == [
    'alpha-track.wav', 'unrelated-voice.wav'
]
assert len(episode['sources']) == 2
print('explicit group inspection: PASS')
PY
```

## 4. Verify planning and mandatory identity

```bash
uv run --locked transcriber dry-run \
    --group "$EWP_GROUP_INPUT/alpha-track.wav" \
    --group "$EWP_GROUP_INPUT/unrelated-voice.wav" \
    --group-id "$EWP_GROUP_ID" \
    --output-dir "$EWP_GROUP_OUTPUT" \
    --config "$EWP_GROUP_ROOT/transcriber.toml"

set +e
uv run --locked transcriber dry-run \
    --group "$EWP_GROUP_INPUT/alpha-track.wav" \
    --group "$EWP_GROUP_INPUT/unrelated-voice.wav" \
    --output-dir "$EWP_GROUP_OUTPUT" \
    --config "$EWP_GROUP_ROOT/transcriber.toml" \
    > "$EWP_GROUP_ROOT/missing-id.stdout" 2> "$EWP_GROUP_ROOT/missing-id.stderr"
EWP_GROUP_MISSING_ID_EXIT=$?
set -e
test "$EWP_GROUP_MISSING_ID_EXIT" -eq 2 && echo "mandatory group-id: PASS"
```

The valid plan must contain exactly one `PROCESS p10-explicit-group` job and output
`p10-explicit-group_results.json`. The controlled invalid call must not create output.

## 5. Run the complete offline grouped-source pipeline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe \
    --group "$EWP_GROUP_INPUT/alpha-track.wav" \
    --group "$EWP_GROUP_INPUT/unrelated-voice.wav" \
    --group-id "$EWP_GROUP_ID" \
    --speaker-map alpha-track.wav=Left \
    --speaker-map unrelated-voice.wav=Right \
    --output-dir "$EWP_GROUP_OUTPUT" \
    --config "$EWP_GROUP_ROOT/transcriber.toml" \
    --non-interactive
```

## 6. Validate canonical identity, source order, and exports

```bash
export EWP_GROUP_RESULT="$EWP_GROUP_OUTPUT/${EWP_GROUP_ID}_results.json"

uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

result = json.loads(Path(os.environ['EWP_GROUP_RESULT']).read_text(encoding='utf-8'))
assert result['job_id'] == os.environ['EWP_GROUP_ID']
assert result['status'] == 'completed'
assert [item['filename'] for item in result['sources']] == [
    'alpha-track.wav', 'unrelated-voice.wav'
]
assert [item['speaker_label'] for item in result['speakers']] == ['Left', 'Right']
assert all(item['speaker_source'] == 'explicit' for item in result['speakers'])
assert result['transcript']['segments']
words = [word for segment in result['transcript']['segments'] for word in segment['words']]
assert words
untimed = sum(word['start_ms'] is None or word['end_ms'] is None for word in words)
print(f"explicit group canonical result: PASS segments={len(result['transcript']['segments'])}, words={len(words)}, untimed={untimed}")
PY

for name in \
    "${EWP_GROUP_ID}_results.json" \
    "${EWP_GROUP_ID}_transcript.txt" \
    "${EWP_GROUP_ID}_subtitles.srt" \
    "${EWP_GROUP_ID}_subtitles.vtt"
do
    test -s "$EWP_GROUP_OUTPUT/$name" && echo "present: $name"
done
```

## 7. Verify duplicate replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe \
    --group "$EWP_GROUP_INPUT/alpha-track.wav" \
    --group "$EWP_GROUP_INPUT/unrelated-voice.wav" \
    --group-id "$EWP_GROUP_ID" \
    --speaker-map alpha-track.wav=Left \
    --speaker-map unrelated-voice.wav=Right \
    --output-dir "$EWP_GROUP_OUTPUT" \
    --config "$EWP_GROUP_ROOT/transcriber.toml" \
    --non-interactive

test -z "$(find "$EWP_GROUP_WORK" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "explicit group workdir cleanup: PASS"
sha256sum "$EWP_GROUP_OUTPUT"/*
git status --short
```

The replay must report `SKIP`, all exports must remain unchanged, no job workdir may
remain, and repository status must be empty.
