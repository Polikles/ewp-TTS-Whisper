# Phase 0 test-media preparation

## Storage rule

Keep test recordings outside the EWP-transcripts application repository. Recommended local layout:

```text
/home/linuch/transkrypcje/ewp-transcripts-testdata/
  phase0/
    audio/
    references/
    notes/
```

Do not commit source recordings, generated transcripts, or derived working audio to the application repository.

## Required Phase 0 recordings

Prepare three excerpts from already published Polish podcast material.

### P0-01 — short single speaker

- duration: 60–90 seconds;
- one speaker only;
- Polish speech;
- clean, ordinary speaking pace;
- WAV, mono, 48 kHz, PCM 16-bit;
- no music when possible.

Purpose: fast repeated checks of model loading, ASR, alignment, CUDA, and offline replay.

Suggested filename:

```text
p0-01-single-short.wav
```

### P0-02 — representative single speaker

- duration: 4–6 minutes;
- one speaker only;
- Polish speech with natural punctuation, numbers, proper names, or occasional English terms when available;
- WAV, mono, 48 kHz, PCM 16-bit;
- representative edited podcast quality.

Purpose: compare ASR candidates, inspect alignment fallbacks, and collect preliminary timing and VRAM measurements.

Suggested filename:

```text
p0-02-single-representative.wav
```

### P0-03 — mixed two speakers

- duration: 5–8 minutes;
- two speakers mixed into one mono signal;
- several clear speaker changes;
- at least one natural overlap if the source contains one;
- WAV, mono, 48 kHz, PCM 16-bit;
- avoid a music-heavy intro or outro.

Purpose: diarization, chronological speaker normalization, overlap behavior, and offline model loading.

Suggested filename:

```text
p0-03-two-speakers-mixed.wav
```

## Optional retained source

Keep one original MP3 dual-mono podcast excerpt, where the left and right channels are identical and both contain the complete two-speaker mix:

```text
p0-04-two-speakers-dual-mono.mp3
```

This file is not required for the first dependency spike. It will become useful when channel classification and FFmpeg integration are implemented.

If “both speakers on one channel” means something other than both speakers mixed into each identical stereo channel, record the actual left/right layout in `notes/p0-04.md`.

## Export requirements

- Export from the edited project timeline without denoising or processing added solely for the test.
- Do not normalize different excerpts to artificial common loudness unless that is already part of the published edit.
- Do not convert MP3 back to WAV when an original lossless project export is available.
- Start and end on silence or natural boundaries when practical.
- Preserve natural repetitions, hesitations, self-corrections, and overlap.
- Record the source episode and exact timeline range in a local note.

Example FFmpeg inspection after export:

```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,channel_layout -show_entries format=duration -of default=noprint_wrappers=1 <audio-file>
```

## Reference transcripts

### Required now

Create a fully manually checked reference for `P0-01`. This is short enough to validate obvious ASR and alignment failures without delaying the spike.

### Required before model comparison

Create fully manually checked references for `P0-02` and `P0-03` before using them for WER, CER, or diarization-quality decisions.

An automatic draft from NotebookLM or a tested ASR model may be used as a starting point, but the final reference must be checked against the audio word by word. A candidate model's raw output is never ground truth.

For `P0-03`, use speaker-labelled turns:

```text
speaker_a: ...
speaker_b: ...
```

Also note audible overlaps and uncertain words. Precise word timestamps are not required for the first smoke test; timestamp annotations can be added later to a smaller selected subset.

## Later test lengths

Do not prepare these yet. Subsequent validation will use:

- 5–15 minute manually verified quality excerpts;
- approximately 30–40 minute realistic episode runs from the available corpus;
- a synthetic or concatenated 60-minute stability case if required by the MVP acceptance gate;
- longer 90-minute to 3-hour cases only during hardening, not Phase 0.

## Licensing note

Published audio is suitable for private local testing, but publication alone does not define redistribution rights. Before creating a public external test dataset, record ownership, contributor consent where applicable, and an explicit dataset/audio license.
