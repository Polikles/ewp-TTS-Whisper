# Validate fast speech and light recorder noise

This gate derives two generic stress fixtures from the verified P0-02 Polish reference:
tempo-accelerated speech and speech mixed with low-level pink noise. It checks the full
offline pipeline and records lexical scores without changing the source or repository.

## 0. Synchronize and create a sandbox

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_STRESS_SOURCE="$EWP_TESTDATA/audio/p0-02-single-representative.wav"
export EWP_STRESS_REFERENCE="$EWP_TESTDATA/references/p0-02-single-representative.txt"
export EWP_STRESS_ROOT="$(mktemp -d "$EWP_TESTDATA/release-stress-audio-XXXXXXXX")"
export EWP_STRESS_INPUT="$EWP_STRESS_ROOT/input"
export EWP_STRESS_OUTPUT="$EWP_STRESS_ROOT/output"
export EWP_STRESS_EVIDENCE="$EWP_STRESS_ROOT/evidence"
export EWP_STRESS_WORK="$EWP_STRESS_ROOT/work"
mkdir -p "$EWP_STRESS_INPUT" "$EWP_STRESS_OUTPUT" \
    "$EWP_STRESS_EVIDENCE" "$EWP_STRESS_WORK"

test -s "$EWP_STRESS_SOURCE" && echo "P0-02 source: present"
test -s "$EWP_STRESS_REFERENCE" && echo "P0-02 reference: present"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
printf 'sandbox=%s\n' "$EWP_STRESS_ROOT"
```

Expected commit: `18b418a` or later and 279 passing tests.

## 1. Derive and inspect the fixtures

```bash
ffmpeg -v error -y -i "$EWP_STRESS_SOURCE" \
    -filter:a "atempo=1.6" -c:a pcm_s16le \
    "$EWP_STRESS_INPUT/fast-polish.wav"

ffmpeg -v error -y -i "$EWP_STRESS_SOURCE" \
    -f lavfi -i "anoisesrc=color=pink:amplitude=0.02:sample_rate=48000" \
    -filter_complex "[0:a]aresample=48000[source];[source][1:a]amix=inputs=2:duration=first:normalize=0[out]" \
    -map "[out]" -ac 1 -c:a pcm_s16le \
    "$EWP_STRESS_INPUT/light-recorder-noise.wav"

for path in "$EWP_STRESS_INPUT"/*.wav; do
    echo "FILE=$(basename "$path")"
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=duration -of default=noprint_wrappers=1 "$path"
done
sha256sum "$EWP_STRESS_SOURCE" "$EWP_STRESS_REFERENCE" "$EWP_STRESS_INPUT"/*.wav
```

Both fixtures must be mono PCM. The fast fixture should be approximately 62.5% of the
source duration; the noisy fixture should retain the source duration.

## 2. Configure, inspect, and dry-run

```bash
cat > "$EWP_STRESS_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false
[runtime]
work_root = "$EWP_STRESS_WORK"
EOF

uv run --locked transcriber inspect "$EWP_STRESS_INPUT" \
    --config "$EWP_STRESS_ROOT/transcriber.toml" --json-output \
    > "$EWP_STRESS_EVIDENCE/inspect.json"

uv run --locked transcriber dry-run "$EWP_STRESS_INPUT" \
    --config "$EWP_STRESS_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_STRESS_OUTPUT"
```

The plan must contain `fast-polish` followed by `light-recorder-noise`, both as
single-source jobs.

## 3. Run the complete offline batch

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_STRESS_INPUT" \
    --config "$EWP_STRESS_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_STRESS_OUTPUT" --non-interactive
```

The summary must report `completed=2 skipped=0 failed=0 cancelled=0`.

## 4. Validate results and calculate lexical evidence

```bash
uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

output = Path(os.environ['EWP_STRESS_OUTPUT'])
for job_id in ('fast-polish', 'light-recorder-noise'):
    path = output / f'{job_id}_results.json'
    result = json.loads(path.read_text(encoding='utf-8'))
    assert result['status'] == 'completed'
    assert result['transcript']['segments']
    words = [word for segment in result['transcript']['segments'] for word in segment['words']]
    assert words
    for suffix in ('_transcript.txt', '_subtitles.srt', '_subtitles.vtt'):
        assert (output / f'{job_id}{suffix}').stat().st_size > 0
    print(f'PASS {job_id}: segments={len(result["transcript"]["segments"])}, words={len(words)}')
PY

for job_id in fast-polish light-recorder-noise; do
    uv run --locked python tools/phase0_score_transcript.py \
        "$EWP_STRESS_REFERENCE" "$EWP_STRESS_OUTPUT/${job_id}_results.json" \
        --output "$EWP_STRESS_EVIDENCE/${job_id}-quality.json"
done
```

Record both WER/CER reports. These synthetic cases are acceptance smoke tests, not new
corpus baselines. Any large degradation or hallucination requires review before checking
the material row.

## 5. Verify replay, cleanup, and evidence hashes

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_STRESS_INPUT" \
    --config "$EWP_STRESS_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_STRESS_OUTPUT" --non-interactive

test -z "$(find "$EWP_STRESS_WORK" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "stress-audio workdir cleanup: PASS"
sha256sum "$EWP_STRESS_OUTPUT"/*_results.json
sha256sum "$EWP_STRESS_EVIDENCE"/*.json
git status --short
```

The replay summary must report `completed=0 skipped=2 failed=0 cancelled=0`. Git status
should be empty. Do not copy or commit `LICENSE_SKETCH.TXT`.

