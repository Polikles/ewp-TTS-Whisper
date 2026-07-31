# Export Formats

## 1. Principle

An export is a deterministic transformation of `results.json`. Exporting must not run WhisperX, pyannote, or open source audio.

## 2. TXT

Filename:

```text
<job_id>_transcript.txt
```

Rules:

- no timestamps;
- UTF-8;
- one sentence per line;
- with multiple speakers, each block starts with `Name:`;
- a speaker change starts a new block;
- consecutive sentences by the same speaker remain in the same block;
- with one speaker, the label is omitted;
- no stylistic or LLM correction.

Example:

```text
Jan:
This is the first sentence.
This is the second sentence.

Anna:
This is Anna's reply.
```

## 3. Optional `segments.json`

Filename:

```text
<job_id>_segments.json
```

This is a lightweight derived format containing phrase-level and word-level timestamps, and speaker-change segments. It is not the source of truth and can be rebuilt from `results.json`. The purpose of this file is to be used as reference for future project of building a database for voice-recognition and voice-cloning.

## 4. SRT and VTT

Filenames:

```text
<job_id>_subtitles.srt
<job_id>_subtitles.vtt
```

The MVP produces plain-text subtitles without depending on colors or CSS. TODO: adding optional color settings for separate speakers

## 5. Default `youtube` cue preset

```toml
max_lines = 2
target_chars_per_line = 42
max_chars_per_line = 46
min_duration_ms = 1000
max_duration_ms = 7000
target_chars_per_second = 17
max_chars_per_second = 20
min_gap_ms = 80
max_merge_gap_ms = 300
speaker_labels = "on-change"
```

All values are configurable.

## 6. Segmentation rules

Preferred split boundaries, in order:

1. sentence end;
2. natural phrase boundary;
3. comma, semicolon, or dash;
4. before a conjunction;
5. character limit as a fallback.

The algorithm SHOULD NOT:

- split words;
- leave one short word alone on the second line;
- split proper names unnecessarily;
- exceed two lines;
- combine ordinary utterances from different speakers in one cue;
- extend a cue into the next speaker's speech.

## 7. Cue timing

Base timing:

```text
start = start of the first word
end = end of the last word
```

A cue shorter than `min_duration_ms` may be extended only into available silence, by at most 300 ms, and without overlapping the next cue.

Fast speech is divided into more cues. The previous cue is not extended at the expense of the next utterance.

## 8. Speaker labels

Modes:

- `on-change` — default;
- `always`;
- `never`.

`on-change` means:

- a label at the beginning when multiple speakers exist;
- a label after every speaker change;
- no repeated label in consecutive cues belonging to the same continuous turn.

An overlap exported as two lines should always include labels for both speakers.

## 9. Punctuation and sentences

TXT and subtitles use canonical transcript text. The sentence segmenter should:

- support common Polish and English abbreviations;
- use ASR punctuation;
- use a longer pause when punctuation is ambiguous;
- preserve interrupted sentences;
- not assume that a raw WhisperX segment is a sentence.

## 10. Validation

- no overlapping cues except explicit overlap handling;
- increasing timestamps;
- valid SRT numbering;
- `WEBVTT` header;
- no empty cues;
- limits are satisfied, or a warning is recorded when the physical speech rate makes compliance impossible.
