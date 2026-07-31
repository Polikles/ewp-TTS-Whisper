# Input, Grouping, and Channel Classification

## 1. Input types

### Single file

```text
D:/podcast/S01E01.wav
```

Creates one job with `job_id = S01E01`.

### Directory

```text
D:/podcast/season01
```

Creates jobs from files directly inside the directory. Subdirectories are ignored unless `--recursive` is used.

### Explicit group

Several paths supplied in one grouping operation create one episode. Explicit grouping takes precedence over filename conventions.

## 2. Supported formats

Official MVP test matrix:

- audio: WAV, MP3, FLAC, M4A/AAC, OGG/Vorbis, Opus;

Video containers and audio-stream selection are deferred until stage 2.

Other formats are supported on a best-effort basis when FFmpeg can decode them.

## 3. Speaker suffix rule

Separator: the final hyphen `-`.

```text
S01E01-jan.mp3
S01E01-anna.mp3
```

These form one group:

```text
job_id: S01E01
speakers: jan, anna
```

Underscores are part of the identifier:

```text
S01E01_mono_normalized-jan.mp3
S01E01_mono_normalized-anna.mp3
```

These form `job_id = S01E01_mono_normalized`.

### Single file containing a hyphen

```text
ai-ethics-introduction.mp3
```

The suffix is not interpreted as a speaker unless the user explicitly sets `speaker_count = 1`. Even then, the output name preserves the complete filename stem to avoid collisions:

```text
ai-ethics-introduction_results.json
```

### Base file plus suffixed file

```text
S01E01.mp3
S01E01-marta.mp3
```

These may form group `S01E01`. The unsuffixed file receives `Speaker1`, and the other receives `marta`, unless explicit labels override them.

## 4. Group validation

For every pair of sources, the application checks:

- duration;
- sample rate;
- decodability;
- common job ID;
- uniqueness of speaker assignment.

Duration policy:

| Difference | Behavior |
|---:|---|
| `<= 100 ms` | accept |
| `> 100 ms` and `<= 500 ms` | warn and process |
| `> 500 ms` | block the group |

Only `--allow-duration-mismatch` bypasses the block. `--force` controls result versioning, not source validation.

Different sample rates block a group in the MVP. Grouped sources are not resampled automatically.

## 5. Source identity

Every file receives a SHA-256 hash of its complete content. Selected stream and channel information are part of the source descriptor.

`episode_signature` is the SHA-256 of a canonical structure containing:

- SHA-256 of every source file;
- source order;
- channel index or channel mode;
- `speaker_id` and label assignment;
- job ID.

A path or filename alone is not a sufficient identity.

## 6. Channel classification

### `mono`

One channel, containing one or more speakers.

### `dual_mono`

Two identical or nearly identical channels. The application uses one channel. The recording may still contain multiple speakers.

### `split_speakers`

Each channel represents one speaker. Channels are transcribed independently and merged chronologically.

### `mixed_stereo`

Both channels contain substantially the same mix with stereo differences. The MVP creates one working downmix and applies diarization when required.

### `ambiguous`

Classification confidence is insufficient. The application:

1. records `CHANNEL_CLASSIFICATION_AMBIGUOUS`;
2. uses one channel;
3. suggests `--channel-mode split-speakers` when the user knows that channels represent separate speakers.

## 7. Classification heuristic

The implementation should evaluate:

- channel correlation and normalized error over representative windows;
- RMS and spectral similarity;
- VAD per channel;
- alternating activity and overlap.

Initial `dual_mono` candidate thresholds:

```text
correlation >= 0.995
absolute RMS difference <= 1.5 dB
```

Thresholds are configurable and must be calibrated against the test corpus. Ambiguity must not trigger automatic transcription of both channels followed by aggressive text deduplication in the MVP.

## 8. Speaker-label sources

Priority:

1. explicit user mapping;
2. filename suffix within a detected or explicit group;
3. semantic track/channel metadata;
4. `Speaker1`, `Speaker2`, and so on.

Standard channel-layout labels such as `FL` and `FR` are not person names.
