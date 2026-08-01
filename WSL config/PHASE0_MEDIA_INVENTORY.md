# Phase 0 media inventory

Recorded: **2026-08-01**.

The values below come from ffprobe and are authoritative over values embedded in filenames.

## Prepared files

| Current filename | ffprobe duration | Codec | Rate | Channels | Intended role | Status |
|---|---:|---|---:|---:|---|---|
| `p0-01-single-short.wav` | 95.376 s | PCM signed 16-bit LE | 48 kHz | 1 | P0-01 short single speaker | ready; reference transcript ready |
| `p0-02-single-representative.wav` | 276.170 s | PCM signed 16-bit LE | 48 kHz | 1 | P0-02 representative single speaker | ready |
| `p0-03-two-speakers-mixed-overlap.wav` | 489.448 s | PCM signed 16-bit LE | 48 kHz | 1 | P0-03 mixed two-speaker/overlap case | ready; three known overlaps |
| `p0-04-two-speakers-dual-mono.mp3` | 550.344 s | MP3 | 48 kHz | 2, stereo layout | P0-04 lossy near-identical dual-mono fixture | ready for later classifier calibration |

## Assessment

- P0-01 is five seconds above the suggested range, which is acceptable for the smoke test. The replacement export is true one-channel PCM mono.
- P0-02 meets the representative single-speaker requirements.
- P0-03 is approximately 8 minutes 9 seconds, slightly above the target range but suitable. It contains three known overlaps.
- P0-04 is approximately 9 minutes 10 seconds and is retained for later dual-mono classification work. Both channels contain the same complete two-speaker mix, but lossy MP3 encoding introduced a very quiet decoded difference.
- Durations in three current filenames do not match ffprobe. Test identity and manifests must use probed duration, never filename text.

## Stable names

```text
p0-01-single-short.wav
p0-02-single-representative.wav
p0-03-two-speakers-mixed-overlap.wav
p0-04-two-speakers-dual-mono.mp3
```

Stable case IDs should carry meaning; measured duration belongs in the future dataset manifest.

## Channel-identity result

P0-04 decoded left-minus-right residual:

```text
mean_volume: -71.1 dB
max_volume: -41.2 dB
```

It is not sample-identical dual mono after MP3 decoding. It is a known-source, near-identical lossy dual-mono case suitable for testing the configured correlation and RMS thresholds. A separate lossless exact-dual-mono synthetic fixture will still be required for deterministic classifier tests.

The subtraction filter is meaningful only for a two-channel input. P0-01's replacement export was independently confirmed as a one-channel stream, so its finite volume output is not a left/right difference measurement.

## Transcript state

The manually checked P0-01 reference transcript is ready. P0-02 and P0-03 references may follow after the initial dependency smoke test but are required before quality decisions.
