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

This is an override for sources whose filenames do not satisfy the automatic final-hyphen
rule but which the user knows share one episode timeline. Files such as
`S01E01-jan.wav` and `S01E01-anna.wav` do not need the override because they already
form an automatic group. An explicit group still undergoes sample-rate, duration,
decodability, speaker-assignment, and channel validation.

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

Channel count and channel topology are different concepts. A container or ffprobe layout reported as `stereo` proves only that the stream has two channels. It does not establish whether those channels are dual mono, split speakers, mixed stereo, or ambiguous. Speaker count is also independent: one mono channel may contain several speakers, while a two-channel file may contain the same single speaker twice.

| Mode | Channels | What is present in left/right | MVP processing |
|---|---:|---|---|
| `mono` | 1 | One waveform; it may contain one or many speakers | Process the single channel; use diarization when multiple speakers require it |
| `dual-mono` | 2 | Left and right are identical or near-identical copies of the same complete waveform | Use one channel; never transcribe both copies |
| `split-speakers` | 2 | Each channel is an isolated speaker/source; activity may alternate or overlap | Process channels independently and merge their timelines |
| `mixed-stereo` | 2 | The relevant speakers/mix occur in both channels, but left and right differ materially because of panning, level, room, effects, or other stereo information | Create one working downmix; use diarization when required |
| `ambiguous` | usually 2 | Measurements do not support any topology confidently | Warn and use one channel unless the user provides an explicit mode |

`auto` is a configuration request to run classification. It is not a detected topology.

### `mono`

Exactly one encoded audio channel, containing one or more speakers. Duplicating this channel during analysis or playback does not turn the source into dual mono; classification uses the original stream channel count.

### `dual_mono`

Two encoded channels containing identical or nearly identical copies of the same complete waveform. “Exact dual mono” is sample-identical; “near dual mono” permits small codec or export differences while remaining perceptually and operationally the same signal. The recording may contain any number of speakers. The application uses one channel because processing both would duplicate content.

A DAW export with all mono tracks center-panned commonly produces dual mono: the file is technically two-channel stereo, but left and right carry the same mix. P2-02 is the project example of this distinction.

### `split_speakers`

Each channel represents an isolated speaker or source. For example, speaker A is recorded only on the left and speaker B only on the right. Both channels may be active simultaneously during overlap. Channels are transcribed independently and merged chronologically; hard panning is not itself sufficient evidence unless the channel contents are actually isolated.

### `mixed_stereo`

Both channels contain the relevant speakers or program mix, but the waveforms differ materially. A speaker may be louder on one side because of moderate panning, yet remains audible on both. Natural stereo recordings, room microphones, stereo effects, and deliberately panned mixes also belong here. The MVP creates one working downmix and applies diarization when required.

P2-03 is the project example: both speakers remain in both channels, with one panned 30% left and the other 30% right. This differs from split speakers because neither speaker is isolated to one channel, and from dual mono because left and right are measurably different.

### `ambiguous`

This is a safety result, not a source-production format. Classification evidence is insufficient or contradictory, so the application:

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

CLI explicit labels use exact filenames. For example,
`--speaker-map S01E01-guest.wav=Marta` labels only that physical source. This
avoids unsafe matching by stem or partial path. A split-speaker stereo source
cannot receive one source-wide explicit label because its channels represent
different speakers; it retains channel-derived identities in the MVP.
