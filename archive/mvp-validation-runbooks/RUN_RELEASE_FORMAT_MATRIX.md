# Validate FLAC, M4A/AAC, and Opus inputs

This gate derives three non-WAV fixtures from the verified P0-01 source and proves the
complete offline single-speaker pipeline for every remaining advertised MVP audio format.
Generated media and results stay outside the repository.

## 0. Synchronize and create a sandbox

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_FORMAT_SOURCE="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_FORMAT_ROOT="$(mktemp -d "$EWP_TESTDATA/release-formats-XXXXXXXX")"
export EWP_FORMAT_INPUT="$EWP_FORMAT_ROOT/input"
export EWP_FORMAT_OUTPUT="$EWP_FORMAT_ROOT/output"
export EWP_FORMAT_WORK="$EWP_FORMAT_ROOT/work"
mkdir -p "$EWP_FORMAT_INPUT" "$EWP_FORMAT_OUTPUT" "$EWP_FORMAT_WORK"

test -s "$EWP_FORMAT_SOURCE" && echo "P0-01 source: present"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
printf 'sandbox=%s\n' "$EWP_FORMAT_ROOT"
```

Expected commit: `7085a1a` or later and 254 passing tests.

## 1. Derive the format fixtures

```bash
ffmpeg -v error -y -i "$EWP_FORMAT_SOURCE" -c:a flac \
    "$EWP_FORMAT_INPUT/flac_sample.flac"
ffmpeg -v error -y -i "$EWP_FORMAT_SOURCE" -c:a aac -b:a 192k \
    "$EWP_FORMAT_INPUT/m4a_sample.m4a"
ffmpeg -v error -y -i "$EWP_FORMAT_SOURCE" -c:a libopus -b:a 128k \
    "$EWP_FORMAT_INPUT/opus_sample.opus"

for path in "$EWP_FORMAT_INPUT"/*; do
    echo "FILE=$(basename "$path")"
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=format_name,duration \
        -of default=noprint_wrappers=1 "$path"
done
sha256sum "$EWP_FORMAT_INPUT"/*
```

Expected codecs are FLAC, AAC, and Opus. Each file must be mono, approximately 95.376
seconds, and independently decodable. Exact hashes depend on the installed FFmpeg build
and are recorded as evidence rather than prescribed in advance.

## 2. Configure isolated mutable storage and inspect

```bash
cat > "$EWP_FORMAT_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false
[runtime]
work_root = "$EWP_FORMAT_WORK"
EOF

uv run --locked transcriber inspect "$EWP_FORMAT_INPUT" \
    --config "$EWP_FORMAT_ROOT/transcriber.toml" \
    --json-output > "$EWP_FORMAT_ROOT/inspect.json"

uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ['EWP_FORMAT_ROOT'], 'inspect.json').read_text())
assert [episode['job_id'] for episode in report['episodes']] == [
    'flac_sample', 'm4a_sample', 'opus_sample'
]
assert len(report['episodes']) == 3
assert all(len(episode['sources']) == 1 for episode in report['episodes'])
assert all(episode['sources'][0]['channel_classification']['processing_mode'] == 'mono' for episode in report['episodes'])
print('format inspection matrix: PASS')
PY
```

## 3. Run the complete offline batch

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_FORMAT_INPUT" \
    --config "$EWP_FORMAT_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_FORMAT_OUTPUT" --non-interactive
```

The summary must report `completed=3 skipped=0 failed=0 cancelled=0`.

## 4. Validate canonical results and exports

```bash
uv run --locked python - <<'PY'
import json
import os
from pathlib import Path

output = Path(os.environ['EWP_FORMAT_OUTPUT'])
expected = {
    'flac_sample': ('flac', 'flac'),
    'm4a_sample': ('m4a', 'aac'),
    'opus_sample': ('opus', 'opus'),
}
for job_id, (container, codec) in expected.items():
    result = json.loads((output / f'{job_id}_results.json').read_text(encoding='utf-8'))
    source = result['sources'][0]
    assert result['status'] == 'completed'
    assert source['container'] == container
    assert source['codec'] == codec
    assert result['transcript']['segments']
    words = [word for segment in result['transcript']['segments'] for word in segment['words']]
    assert words
    for suffix in ('_transcript.txt', '_subtitles.srt', '_subtitles.vtt'):
        assert (output / f'{job_id}{suffix}').stat().st_size > 0
    print(f'PASS {job_id}: codec={codec}, segments={len(result["transcript"]["segments"])}, words={len(words)}')
PY
```

## 5. Verify duplicate replay and cleanup

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_FORMAT_INPUT" \
    --config "$EWP_FORMAT_ROOT/transcriber.toml" \
    --speaker-count 1 --output-dir "$EWP_FORMAT_OUTPUT" --non-interactive

test -z "$(find "$EWP_FORMAT_WORK" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "format matrix workdir cleanup: PASS"
sha256sum "$EWP_FORMAT_OUTPUT"/*
git status --short
```

The replay summary must report `completed=0 skipped=3 failed=0 cancelled=0`, and Git
status should be empty. Do not copy or commit `LICENSE_SKETCH.TXT`.
