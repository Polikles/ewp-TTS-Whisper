# Measure Phase 2 channel fixtures

Use this runbook after the four known channel-topology fixtures are available. It measures features only; it does not classify, transcribe, alter, or copy the audio.

## 1. Update and verify the application environment

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
uv sync --locked
make check
```

Expected WSL baseline after commit `eb07d2b`: 55 tests pass, including the real FFmpeg/ffprobe integration test. On a machine without FFmpeg, 54 pass and that integration test is skipped.

## 2. Set external paths

Set the actual external test-data directory explicitly; do not place audio or reports in the application repository:

```bash
export EWP_CHANNEL_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/audio"
export EWP_CHANNEL_REPORT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/evidence/channel-metrics-v1.json"
mkdir -p "$(dirname "$EWP_CHANNEL_REPORT")"
```

If the local test-data repository has a different name, change only `EWP_CHANNEL_DATA` and `EWP_CHANNEL_REPORT`.

## 3. Confirm the four fixtures

```bash
for file in \
    p0-01-single-short.wav \
    p0-04-two-speakers-dual-mono.mp3 \
    p2-01-split-speakers.wav \
    p2-02-mixed-stereo.wav
do
    test -f "$EWP_CHANNEL_DATA/$file" && echo "present: $file"
done
```

Expected new-fixture hashes:

```text
p2-01-split-speakers.wav  868542600305d4cb7514b45130ec67e2cab94bc817e9fa9f6db451c0b999a0a3
p2-02-mixed-stereo.wav    79886d9fdf2d207b6175a0448911ec7067a70df347086ee82401b16978024cc1
```

Verify them:

```bash
sha256sum \
    "$EWP_CHANNEL_DATA/p2-01-split-speakers.wav" \
    "$EWP_CHANNEL_DATA/p2-02-mixed-stereo.wav"
```

## 4. Generate the sanitized metrics report

```bash
uv run --locked python tools/phase2_measure_channels.py \
    "$EWP_CHANNEL_DATA/p0-01-single-short.wav" \
    "$EWP_CHANNEL_DATA/p0-04-two-speakers-dual-mono.mp3" \
    "$EWP_CHANNEL_DATA/p2-01-split-speakers.wav" \
    "$EWP_CHANNEL_DATA/p2-02-mixed-stereo.wav" \
    --output "$EWP_CHANNEL_REPORT"
```

The tool decodes one audio stream to temporary in-memory 16 kHz signed-16-bit stereo PCM. Mono is duplicated to two analysis channels but remains identifiable through `original_channels=1`. It reports only filenames, hashes, stream metadata, correlation, normalized left/right difference, RMS levels, and 500 ms activity ratios. It does not print paths, samples, or transcript text.

## 5. Verify the report

```bash
test -s "$EWP_CHANNEL_REPORT" && echo "channel metrics report: present"
sha256sum "$EWP_CHANNEL_REPORT"
```

Send the complete report. It contains no transcript or audio content and is required to choose provisional classifier thresholds.

## Ground-truth topology notes

- P0-01: true one-channel mono.
- P0-04: two-channel near-identical lossy dual mono; both channels contain the same mix.
- P2-01: right-only from approximately 0–60 s, left-only from 60–135 s, overlap from 135–141 s, then right-only until approximately 142.4 s.
- P2-02: submitted as mixed stereo, with both speakers on both channels and no speaker overlap. The first measurement found near-identical channels, so it is retained as contrary evidence and another effective dual-mono case rather than accepted as mixed-stereo calibration.

These four cases are a proof-of-concept calibration set, not a representative final dataset. Record every selected threshold as provisional and rerun calibration after the larger manually verified corpus exists.
