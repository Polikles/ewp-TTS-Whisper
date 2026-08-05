# Validate release observability and chronological speakers

This offline GPU gate validates chronological default speaker numbering, clean JSON Lines
stdout, elapsed-time and peak-VRAM metrics, and actionable missing-model errors.

## 0. Synchronize and create a sandbox

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_OBS_INPUT="$EWP_TESTDATA/audio/p2-01-split-speakers.wav"
export EWP_OBS_ROOT="$(mktemp -d "$EWP_TESTDATA/release-observability-XXXXXXXX")"
export EWP_OBS_OUTPUT="$EWP_OBS_ROOT/output"
export EWP_OBS_WORK="$EWP_OBS_ROOT/work"
mkdir -p "$EWP_OBS_OUTPUT" "$EWP_OBS_WORK"

test -s "$EWP_OBS_INPUT" && echo "P2-01 source: present"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_OBS_ROOT"
```

Expected commit: `16a07af` or later and 254 passing tests.

## 1. Configure JSON Lines output

```bash
cat > "$EWP_OBS_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false

[runtime]
work_root = "$EWP_OBS_WORK"
log_format = "jsonl"
EOF
```

## 2. Run split-speaker transcription offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_OBS_INPUT" \
    --config "$EWP_OBS_ROOT/transcriber.toml" \
    --speaker-count 2 --output-dir "$EWP_OBS_OUTPUT" --non-interactive \
    > "$EWP_OBS_ROOT/transcribe.jsonl" 2> "$EWP_OBS_ROOT/transcribe.stderr"

cat "$EWP_OBS_ROOT/transcribe.jsonl"
cat "$EWP_OBS_ROOT/transcribe.stderr"
export EWP_OBS_RESULT="$EWP_OBS_OUTPUT/p2-01-split-speakers_results.json"
```

WhisperX, Lightning, and pyannote messages are acceptable on stderr. They must not corrupt
the JSON Lines file.

## 3. Validate structured output and canonical metrics

```bash
uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ['EWP_OBS_ROOT'])
records = [json.loads(line) for line in (root / 'transcribe.jsonl').read_text().splitlines()]
assert records and records[-1]['event'] == 'TRANSCRIPTION_COMPLETED'
assert records[-1]['job_id'] == 'p2-01-split-speakers'
assert records[-1]['run_id']
assert isinstance(records[-1]['elapsed_ms'], int) and records[-1]['elapsed_ms'] > 0
required = {'timestamp', 'level', 'event', 'run_id', 'job_id', 'source', 'stage', 'elapsed_ms', 'context'}
assert all(required <= record.keys() for record in records)

result = json.loads(Path(os.environ['EWP_OBS_RESULT']).read_text(encoding='utf-8'))
speakers = result['speakers']
assert [(item['speaker_id'], item['speaker_label']) for item in speakers] == [
    ('speaker_001', 'Speaker1'), ('speaker_002', 'Speaker2')
]
assert speakers[0]['first_seen_ms'] < speakers[1]['first_seen_ms']
assert speakers[0]['speaker_source'] == speakers[1]['speaker_source'] == 'channel_metadata'
assert result['processing']['environment']['peak_vram_bytes'] > 0
stages = result['processing']['stages']
assert stages and all(isinstance(item['duration_ms'], int) for item in stages)
first = min(result['transcript']['segments'], key=lambda item: (item['start_ms'], item['end_ms']))
assert first['speaker_id'] == 'speaker_001'
print(f"release observability: PASS speakers={len(speakers)}, stages={len(stages)}, peak_vram_bytes={result['processing']['environment']['peak_vram_bytes']}")
PY
```

## 4. Verify actionable missing-model failure

```bash
cat > "$EWP_OBS_ROOT/missing-model.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false
[models]
asr_snapshot_path = "$EWP_OBS_ROOT/model-does-not-exist/asr-revision"
asr_revision = "asr-revision"
[runtime]
work_root = "$EWP_OBS_ROOT/failure-work"
EOF

set +e
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_TESTDATA/audio/p0-01-single-short.wav" \
    --config "$EWP_OBS_ROOT/missing-model.toml" --speaker-count 1 \
    --output-dir "$EWP_OBS_ROOT/failure-output" --non-interactive \
    > "$EWP_OBS_ROOT/failure.stdout" 2> "$EWP_OBS_ROOT/failure.stderr"
EWP_OBS_FAILURE_EXIT=$?
set -e
test "$EWP_OBS_FAILURE_EXIT" -eq 4 && echo "missing model exit: PASS"
grep -q 'docs/10-wsl2-installation.md' "$EWP_OBS_ROOT/failure.stderr" \
    && echo "missing model setup guidance: PASS"
! grep -q 'Traceback' "$EWP_OBS_ROOT/failure.stderr" \
    && echo "missing model sanitization: PASS"
```

## 5. Verify replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_OBS_INPUT" \
    --config "$EWP_OBS_ROOT/transcriber.toml" \
    --speaker-count 2 --output-dir "$EWP_OBS_OUTPUT" --non-interactive \
    > "$EWP_OBS_ROOT/replay.jsonl" 2> "$EWP_OBS_ROOT/replay.stderr"

uv run --locked python - <<'PY'
import json
import os
from pathlib import Path
record = json.loads(Path(os.environ['EWP_OBS_ROOT'], 'replay.jsonl').read_text())
assert record['event'] == 'TRANSCRIPTION_SKIPPED'
assert record['context']['decision'] == 'skip'
print('structured duplicate replay: PASS')
PY

test -z "$(find "$EWP_OBS_WORK" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "successful workdir cleanup: PASS"
sha256sum "$EWP_OBS_OUTPUT"/*
git status --short
```

The Git status should be empty. Do not copy or commit `LICENSE_SKETCH.TXT`.
